#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and os.environ.get("FX_NEXUS_VENV_REEXEC") != "1":
    os.environ["FX_NEXUS_VENV_REEXEC"] = "1"
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), __file__, *sys.argv[1:]])

import numpy as np
import pandas as pd
from scipy import stats

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.currency_strength import PAIR_MAP, basket_strength
from modules.fx_graph import (
    REQUIRED_5PAIR_COLUMNS,
    compute_currency_value,
    fx_graph_condition_number,
    triangular_residual,
)
from modules.stats_utils import profit_factor
from tools.phase3_bt import wilson_lower


YF_SYMBOLS = {
    "USD_JPY": "USDJPY=X",
    "EUR_USD": "EURUSD=X",
    "GBP_USD": "GBPUSD=X",
    "EUR_JPY": "EURJPY=X",
    "GBP_JPY": "GBPJPY=X",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FX Nexus Step 1 shadow audit")
    parser.add_argument("--pairs", default=",".join(REQUIRED_5PAIR_COLUMNS))
    parser.add_argument("--start", default="2025-05-01")
    parser.add_argument("--end", default="2026-05-01")
    parser.add_argument("--horizon", default="H1", choices=["H1"])
    parser.add_argument(
        "--output",
        default="knowledge-base/wiki/decisions/fx-nexus-step1-audit-2026-05-04.md",
    )
    parser.add_argument("--jitter", type=float, default=0.5)
    parser.add_argument("--bt-lookback-days", type=int, default=365)
    return parser.parse_args()


def _days_between(start: str, end: str) -> int:
    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC")
    return max(30, int((hi - lo).days) + 7)


def _read_cache(pair: str) -> pd.DataFrame | None:
    path = PROJECT_ROOT / "data" / "cache" / "massive" / f"{pair}_1h.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    return _normalize_ohlcv(df)


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    })
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    elif df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df.sort_index()


def load_ohlcv(pair: str, start: str, end: str) -> pd.DataFrame:
    cached = _read_cache(pair)
    if cached is not None and not cached.empty:
        df = cached
    else:
        from modules.data import fetch_ohlcv

        days = _days_between(start, end)
        df = fetch_ohlcv(YF_SYMBOLS[pair], period=f"{days}d", interval="1h")
        df = _normalize_ohlcv(df)

    lo = pd.Timestamp(start, tz="UTC")
    hi = pd.Timestamp(end, tz="UTC")
    df = df[(df.index >= lo) & (df.index < hi)]
    if df.empty:
        raise RuntimeError(f"no H1 OHLCV rows for {pair} in {start}..{end}")
    return df


def load_aligned_ohlcv(pairs: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    frames = {pair: load_ohlcv(pair, start, end) for pair in pairs}
    common = None
    for df in frames.values():
        common = df.index if common is None else common.intersection(df.index)
    if common is None or len(common) < 10:
        raise RuntimeError("aligned 5-pair H1 OHLCV sample is too small")
    return {pair: df.loc[common].copy() for pair, df in frames.items()}


def build_log_prices(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.DataFrame(
        {pair: np.log(df["Close"].astype(float)) for pair, df in frames.items()}
    ).dropna()


def binom_p(successes: int, n: int) -> float:
    if n <= 0:
        return 1.0
    return float(stats.binomtest(successes, n, p=0.5, alternative="greater").pvalue)


def verdict_band(value: float, accept: bool, needs: bool) -> str:
    if accept:
        return "ACCEPT"
    if needs:
        return "NEEDS_MORE"
    return "REJECT"


def h1_stats(log_prices: pd.DataFrame, log_v: pd.DataFrame) -> dict[str, Any]:
    pair_returns = log_prices.diff().dropna()
    strength = basket_strength({pair: pair_returns[pair] for pair in pair_returns.columns})
    strength_df = pd.DataFrame(strength).reindex(pair_returns.index)
    v_returns = log_v.diff().reindex(pair_returns.index)
    corr = float(v_returns.stack().corr(strength_df.stack()))

    signal_values = []
    next_returns = []
    for pair in REQUIRED_5PAIR_COLUMNS:
        base, quote = PAIR_MAP[pair]
        mle_pair = v_returns[base] - v_returns[quote]
        basket_pair = strength_df[base] - strength_df[quote]
        signal = (mle_pair - basket_pair).shift(0)
        nxt = pair_returns[pair].shift(-1)
        tmp = pd.concat([signal, nxt], axis=1).dropna()
        signal_values.extend(tmp.iloc[:, 0].tolist())
        next_returns.extend(tmp.iloc[:, 1].tolist())

    sig = np.asarray(signal_values, dtype=float)
    nxt = np.asarray(next_returns, dtype=float)
    mask = (sig != 0) & (nxt != 0)
    wins = int((np.sign(sig[mask]) * nxt[mask] > 0).sum())
    n = int(mask.sum())
    wlo = wilson_lower(wins, n) / 100.0
    cond = fx_graph_condition_number()

    return {
        "condition_number": cond,
        "basket_corr": corr,
        "predictive_wilson_lower": wlo,
        "n": n,
        "verdict": verdict_band(
            wlo,
            cond < 1e6 and 0.7 <= corr <= 0.99 and wlo >= 0.51 and n >= 4000,
            cond <= 1e9 and 2000 <= n < 4000 or 0.49 <= wlo < 0.51,
        ),
    }


def h2_stats(
    alpha: pd.DataFrame,
    log_prices: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    trades: pd.DataFrame,
) -> dict[str, Any]:
    next_ret = log_prices.diff().shift(-1)
    rows = []
    for pair in REQUIRED_5PAIR_COLUMNS:
        tmp = pd.concat([alpha[pair], next_ret[pair]], axis=1).dropna()
        tmp.columns = ["alpha", "next_ret"]
        mask = (tmp["alpha"] != 0) & (tmp["next_ret"] != 0)
        successes = int((-np.sign(tmp.loc[mask, "alpha"]) * tmp.loc[mask, "next_ret"] > 0).sum())
        n = int(mask.sum())
        p = binom_p(successes, n)
        rows.append({
            "pair": pair,
            "n": n,
            "success_rate": successes / n if n else 0.0,
            "p": p,
            "bonferroni_p": min(1.0, p * 5),
        })

    spread_corrs = []
    for pair, df in frames.items():
        proxy = ((df["High"].astype(float) - df["Low"].astype(float)) / df["Close"].astype(float)).reindex(alpha.index)
        spread_corrs.append(abs(alpha[pair]).corr(proxy))
    spread_corr = float(pd.Series(spread_corrs).dropna().mean()) if spread_corrs else math.nan
    autocorr = float(alpha.apply(lambda s: s.autocorr(lag=1)).mean())

    kw_p = live_entry_kruskal(alpha, trades)
    sig_pairs = sum(1 for row in rows if row["bonferroni_p"] < 0.01)
    if sig_pairs == 5:
        verdict = "ACCEPT"
    elif sig_pairs >= 1:
        verdict = "NEEDS_MORE"
    else:
        verdict = "REJECT"

    return {
        "pair_rows": rows,
        "significant_pairs": sig_pairs,
        "spread_corr": spread_corr,
        "autocorr_lag1": autocorr,
        "live_entry_kruskal_p": kw_p,
        "verdict": verdict,
    }


def fetch_live_trades(start: str, end: str) -> pd.DataFrame:
    try:
        from research.edge_discovery.production_fetcher import fetch_closed_trades

        df = fetch_closed_trades(
            date_from=start,
            date_to=end,
            limit=10000,
            include_xau=False,
            include_shadow=False,
            timeout_sec=60,
        )
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    if "oanda_trade_id" in df.columns:
        df = df[df["oanda_trade_id"].fillna("").astype(str) != ""]
    if "is_shadow" in df.columns:
        df = df[df["is_shadow"].fillna(0).astype(int) == 0]
    return df


def _pair_from_instrument(value: Any) -> str | None:
    text = str(value or "").upper().replace("/", "_").replace("=X", "")
    if "_" not in text and len(text) == 6:
        text = text[:3] + "_" + text[3:]
    return text if text in REQUIRED_5PAIR_COLUMNS else None


def live_entry_kruskal(alpha: pd.DataFrame, trades: pd.DataFrame) -> float:
    if trades.empty or "entry_time" not in trades.columns:
        return 1.0
    groups: dict[str, list[float]] = {}
    for _, row in trades.iterrows():
        pair = _pair_from_instrument(row.get("instrument"))
        if pair is None:
            continue
        ts = pd.to_datetime(row.get("entry_time"), utc=True, errors="coerce")
        if pd.isna(ts):
            continue
        loc = alpha.index.get_indexer([ts.floor("h")], method="nearest")
        if loc.size == 0 or loc[0] < 0:
            continue
        key = f"{row.get('entry_type', 'unknown')}:{row.get('sig', row.get('signal', 'NA'))}"
        groups.setdefault(key, []).append(float(alpha.iloc[loc[0]][pair]))
    samples = [v for v in groups.values() if len(v) >= 2]
    if len(samples) < 2:
        return 1.0
    return float(stats.kruskal(*samples).pvalue)


def _pnl_from_trade(t: dict[str, Any]) -> float:
    ef = float(t.get("exit_friction_m", 0) or 0)
    if t.get("outcome") == "WIN":
        return float(t.get("tp_m", 1.5) or 1.5) - ef
    return -(float(t.get("actual_sl_m", t.get("sl_m", 1.0)) or 1.0) + ef)


def strategy_pf(strategy: str, symbol: str, lookback_days: int, jitter: float) -> tuple[float, int, str | None]:
    try:
        os.environ.setdefault("NO_AUTOSTART", "1")
        import app

        if hasattr(app, "_dt_bt_cache"):
            app._dt_bt_cache.clear()
        result = app.run_daytrade_backtest(
            symbol=symbol,
            lookback_days=lookback_days,
            interval="15m",
            exec_lag_jitter=jitter,
        )
        if result.get("error") and not result.get("trade_log"):
            return 0.0, 0, str(result.get("error"))
        trades = [t for t in result.get("trade_log", []) if t.get("entry_type") == strategy]
        return profit_factor([_pnl_from_trade(t) for t in trades]), len(trades), None
    except Exception as exc:
        return 0.0, 0, str(exc)


def h3_stats(lookback_days: int, jitter: float) -> dict[str, Any]:
    s_off, s_n_off, s_err_off = strategy_pf("squeeze_release_momentum", "EURUSD=X", lookback_days, 0.0)
    s_on, s_n_on, s_err_on = strategy_pf("squeeze_release_momentum", "EURUSD=X", lookback_days, jitter)
    h_off, h_n_off, h_err_off = strategy_pf("asia_range_fade_v1", "USDJPY=X", lookback_days, 0.0)
    h_on, h_n_on, h_err_on = strategy_pf("asia_range_fade_v1", "USDJPY=X", lookback_days, jitter)
    s_drop = s_off - s_on
    h_drop = abs(h_off - h_on)

    if s_err_off or s_err_on or h_err_off or h_err_on or min(s_n_off, s_n_on, h_n_off, h_n_on) == 0:
        verdict = "NEEDS_MORE"
    elif s_drop >= 0.30 and h_drop < 0.05:
        verdict = "ACCEPT"
    elif s_drop >= 0.10 or h_drop < 0.10:
        verdict = "NEEDS_MORE"
    else:
        verdict = "REJECT"

    return {
        "squeeze_pf_off": s_off,
        "squeeze_pf_on": s_on,
        "squeeze_n_off": s_n_off,
        "squeeze_n_on": s_n_on,
        "healthy_pf_off": h_off,
        "healthy_pf_on": h_on,
        "healthy_n_off": h_n_off,
        "healthy_n_on": h_n_on,
        "squeeze_drop": s_drop,
        "healthy_drop": h_drop,
        "errors": [e for e in [s_err_off, s_err_on, h_err_off, h_err_on] if e],
        "verdict": verdict,
    }


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        if math.isnan(value):
            return "NA"
        if math.isinf(value):
            return "inf"
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(args: argparse.Namespace, h1: dict[str, Any], h2: dict[str, Any], h3: dict[str, Any]) -> str:
    lines = [
        "# FX Nexus Step 1 Shadow Audit",
        "",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Window: `{args.start}` to `{args.end}`",
        f"- Pairs: `{args.pairs}`",
        "- Scope: shadow measurement only; no LIVE intervention.",
        "",
        "## Verdict Summary",
        "",
        "| Hypothesis | Verdict | Key metric |",
        "|---|---:|---|",
        f"| H1 V_ti | {h1['verdict']} | Wilson lower={fmt(h1['predictive_wilson_lower'])}, corr={fmt(h1['basket_corr'])}, N={h1['n']} |",
        f"| H2 alpha residual | {h2['verdict']} | significant pairs={h2['significant_pairs']}/5, KW p={fmt(h2['live_entry_kruskal_p'])} |",
        f"| H3 exec jitter | {h3['verdict']} | SRM PF drop={fmt(h3['squeeze_drop'])}, healthy PF drop={fmt(h3['healthy_drop'])} |",
        "",
        "## H1 Currency Value",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| condition number | {fmt(h1['condition_number'])} |",
        f"| basket_strength correlation | {fmt(h1['basket_corr'])} |",
        f"| H1 next-bar predictive Wilson lower | {fmt(h1['predictive_wilson_lower'])} |",
        f"| N | {h1['n']} |",
        "",
        "## H2 Alpha Residual",
        "",
        "| Pair | N | MR success rate | p | Bonferroni p |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in h2["pair_rows"]:
        lines.append(
            f"| {row['pair']} | {row['n']} | {fmt(row['success_rate'])} | "
            f"{fmt(row['p'])} | {fmt(row['bonferroni_p'])} |"
        )
    lines.extend([
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| alpha magnitude vs spread proxy correlation | {fmt(h2['spread_corr'])} |",
        f"| alpha autocorrelation lag1 | {fmt(h2['autocorr_lag1'])} |",
        f"| LIVE entry Kruskal-Wallis p | {fmt(h2['live_entry_kruskal_p'])} |",
        "",
        "## H3 Tau Exec Jitter",
        "",
        "| Strategy | PF off | PF on | N off | N on |",
        "|---|---:|---:|---:|---:|",
        f"| squeeze_release_momentum | {fmt(h3['squeeze_pf_off'])} | {fmt(h3['squeeze_pf_on'])} | {h3['squeeze_n_off']} | {h3['squeeze_n_on']} |",
        f"| asia_range_fade_v1 | {fmt(h3['healthy_pf_off'])} | {fmt(h3['healthy_pf_on'])} | {h3['healthy_n_off']} | {h3['healthy_n_on']} |",
    ])
    if h3["errors"]:
        lines.extend(["", "H3 errors/warnings:"] + [f"- {e}" for e in h3["errors"]])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]
    if pairs != REQUIRED_5PAIR_COLUMNS:
        raise SystemExit(f"pairs must be exactly {REQUIRED_5PAIR_COLUMNS}")

    frames = load_aligned_ohlcv(pairs, args.start, args.end)
    log_prices = build_log_prices(frames)
    log_v = compute_currency_value(log_prices)
    alpha = triangular_residual(log_prices, log_v)
    trades = fetch_live_trades(args.start, args.end)

    h1 = h1_stats(log_prices, log_v)
    h2 = h2_stats(alpha, log_prices, frames, trades)
    h3 = h3_stats(args.bt_lookback_days, args.jitter)

    out = PROJECT_ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(args, h1, h2, h3), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"H1={h1['verdict']} H2={h2['verdict']} H3={h3['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
