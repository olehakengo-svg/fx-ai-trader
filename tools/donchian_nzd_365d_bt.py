#!/usr/bin/env python3
"""365d MASSIVE BT for donchian_momentum_breakout NZD pair pre-reg evidence."""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LOOKBACK_DAYS = 365
INTERVAL = "15m"
STRATEGY = "donchian_momentum_breakout"
TARGET_PAIRS = ("NZD_JPY", "NZD_USD")
CONTROL_PAIRS = ("AUD_JPY", "USD_CAD")
ALL_PAIRS = TARGET_PAIRS + CONTROL_PAIRS
BONFERRONI_M = 9
BONF_ALPHA = 0.05 / BONFERRONI_M
BONF_Z = NormalDist().inv_cdf(1 - BONF_ALPHA)
WILSON_Z_95 = NormalDist().inv_cdf(0.975)
BOOTSTRAP_RESAMPLES = 10_000
REPORT_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
OUTFILE = ROOT / "raw" / "bt-results" / f"{REPORT_DATE}-donchian-nzd-365d.md"

SHADOW_BASELINE = {
    "NZD_JPY": {"N": 14, "WR": 0.714, "EV": 20.49, "Total": 287, "Wlo95": 0.453, "BFlo": 0.388},
    "NZD_USD": {"N": 16, "WR": 0.688, "EV": 15.52, "Total": 248, "Wlo95": 0.445, "BFlo": 0.384},
    "AUD_JPY": {"N": 10, "WR": 0.100, "EV": -12.18, "Total": -122, "Wlo95": 0.018, "BFlo": 0.012},
    "USD_CAD": {"N": 11, "WR": 0.273, "EV": -9.05, "Total": -100, "Wlo95": 0.098, "BFlo": 0.075},
}


def _push_bt_env() -> dict[str, str | None]:
    keys = ("BT_MODE", "BT_REQUIRE_MASSIVE_CACHE", "NO_AUTOSTART")
    old = {key: os.environ.get(key) for key in keys}
    os.environ["BT_MODE"] = "1"
    os.environ["BT_REQUIRE_MASSIVE_CACHE"] = "1"
    os.environ["NO_AUTOSTART"] = "1"
    return old


def _pop_bt_env(old: dict[str, str | None]) -> None:
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@dataclass(frozen=True)
class Trade:
    pair: str
    direction: str
    session: str
    entry_time: Any
    exit_time: Any
    pnl_pips: float
    entry: float
    exit: float
    bars_held: int
    exit_reason: str


def symbol_for_pair(pair: str) -> str:
    return f"{pair.replace('_', '')}=X"


def pip_mult(pair_or_symbol: str) -> int:
    return 100 if "JPY" in pair_or_symbol.upper() else 10000


def cache_path(pair: str) -> Path:
    return ROOT / "data" / "cache" / "massive" / f"{pair}_{INTERVAL}.parquet"


def session_for_hour(hour: int) -> str:
    if 0 <= hour < 7:
        return "Asia"
    if 7 <= hour < 12:
        return "London"
    if 12 <= hour < 16:
        return "Overlap"
    return "NY"


def load_massive_15m(pair: str, *, now: datetime | None = None):
    import pandas as pd
    from modules.indicators import add_indicators

    path = cache_path(pair)
    if not path.exists():
        raise FileNotFoundError(f"MASSIVE parquet not found: {path.relative_to(ROOT)}")
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{path.relative_to(ROOT)} must have DatetimeIndex")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.sort_index()
    end = pd.Timestamp(now or datetime.now(timezone.utc))
    cutoff = end - pd.Timedelta(days=LOOKBACK_DAYS)
    df = df.loc[(df.index >= cutoff) & (df.index <= end)].copy()
    if len(df) < 100:
        raise ValueError(f"insufficient MASSIVE bars for {pair}: {len(df)}")
    return add_indicators(df).dropna()


def _ctx_from_df(df, pair: str, bar_time, htf: dict):
    from strategies.context import SignalContext

    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else row
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0))
    symbol = symbol_for_pair(pair)
    return SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=float(row.get("atr7", atr)),
        ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)),
        ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", row.get("ema50", entry))),
        rsi=float(row.get("rsi", 50.0)),
        rsi5=float(row.get("rsi5", row.get("rsi", 50.0))),
        rsi9=float(row.get("rsi9", row.get("rsi", 50.0))),
        stoch_k=float(row.get("stoch_k", 50.0)),
        stoch_d=float(row.get("stoch_d", 50.0)),
        adx=float(row.get("adx", 25.0)),
        adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)),
        macdh=float(row.get("macd_hist", 0.0)),
        macdh_prev=float(prev.get("macd_hist", 0.0)),
        macdh_prev2=float(df.iloc[-3].get("macd_hist", 0.0)) if len(df) >= 3 else 0.0,
        bbpb=float(row.get("bb_pband", 0.5)),
        bb_upper=float(row.get("bb_upper", entry + atr)),
        bb_mid=float(row.get("bb_mid", entry)),
        bb_lower=float(row.get("bb_lower", entry - atr)),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        layer0={"prohibited": False},
        layer1={},
        regime={},
        layer2={},
        layer3={},
        htf=htf,
        session={},
        symbol=symbol,
        tf=INTERVAL,
        is_jpy="JPY" in pair,
        pip_mult=pip_mult(pair),
        df=df,
        sr_levels=[],
        backtest_mode=True,
        bar_time=bar_time,
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )


def _d1_ema50_falling(df_past) -> bool:
    d1 = df_past.resample("1D").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    ).dropna()
    if len(d1) < 55:
        return False
    ema50 = d1["Close"].ewm(span=50).mean()
    return float(ema50.iloc[-1]) < float(ema50.iloc[-5])


def _htf_at(app_mod, df, bar_idx: int) -> dict:
    htf = app_mod._compute_bt_htf_bias(df, bar_idx, mode="daytrade")
    htf["d1_ema50_falling"] = _d1_ema50_falling(df.iloc[: bar_idx + 1])
    return htf


def run_pair_bt(pair: str, *, now: datetime | None = None) -> dict:
    old_env = _push_bt_env()
    try:
        import app as app_mod
        from strategies.hourly.donchian_momentum_breakout import DonchianMomentumBreakout

        df = load_massive_15m(pair, now=now)
        symbol = symbol_for_pair(pair)
        pm = pip_mult(pair)
        strategy = DonchianMomentumBreakout()
        DonchianMomentumBreakout.reset_dedup_state()
        trades: list[Trade] = []
        last_exit_i = -10_000
        htf = _htf_at(app_mod, df, min(500, len(df) - 1))
        last_htf_i = 0
        max_hold = int(getattr(strategy, "MAX_HOLD_BARS", 24))

        for i in range(240, len(df) - max_hold - 2):
            if i <= last_exit_i:
                continue
            if i - last_htf_i >= 80:
                htf = _htf_at(app_mod, df, i)
                last_htf_i = i
            bar_time = df.index[i]
            ctx = _ctx_from_df(df.iloc[max(0, i - 3500) : i + 1], pair, bar_time, htf)
            cand = strategy.evaluate(ctx)
            if cand is None or cand.entry_type != STRATEGY:
                continue
            if cand.signal not in {"BUY", "SELL"}:
                continue

            entry_bar = df.iloc[i + 1]
            raw_entry = float(entry_bar["Open"])
            spread = app_mod._bt_spread(bar_time, symbol)
            slip = app_mod._bt_get_slippage(symbol)
            entry = raw_entry + (spread / 2 + slip) if cand.signal == "BUY" else raw_entry - (spread / 2 + slip)
            sig_entry = float(ctx.entry)
            shift = entry - sig_entry
            sl = float(cand.sl) + shift
            tp = float(cand.tp) + shift
            exit_friction = spread / 2 + slip
            exit_price = None
            exit_reason = "time_exit"
            bars_held = max_hold
            exit_time = df.index[min(i + 1 + max_hold, len(df) - 1)]

            for j in range(1, max_hold + 1):
                fut_i = i + 1 + j
                if fut_i >= len(df):
                    break
                fut = df.iloc[fut_i]
                hi = float(fut["High"])
                lo = float(fut["Low"])
                close = float(fut["Close"])
                if cand.signal == "BUY":
                    hit_tp = hi >= tp
                    hit_sl = lo <= sl
                    if hit_tp and hit_sl:
                        exit_price = tp if close >= entry else sl
                        exit_reason = "tp_first_tiebreak" if close >= entry else "sl_first_tiebreak"
                        bars_held = j
                        exit_time = df.index[fut_i]
                        break
                    if hit_tp:
                        exit_price = tp
                        exit_reason = "tp"
                        bars_held = j
                        exit_time = df.index[fut_i]
                        break
                    if hit_sl:
                        exit_price = sl
                        exit_reason = "sl"
                        bars_held = j
                        exit_time = df.index[fut_i]
                        break
                else:
                    hit_tp = lo <= tp
                    hit_sl = hi >= sl
                    if hit_tp and hit_sl:
                        exit_price = tp if close <= entry else sl
                        exit_reason = "tp_first_tiebreak" if close <= entry else "sl_first_tiebreak"
                        bars_held = j
                        exit_time = df.index[fut_i]
                        break
                    if hit_tp:
                        exit_price = tp
                        exit_reason = "tp"
                        bars_held = j
                        exit_time = df.index[fut_i]
                        break
                    if hit_sl:
                        exit_price = sl
                        exit_reason = "sl"
                        bars_held = j
                        exit_time = df.index[fut_i]
                        break

            if exit_price is None:
                fut = df.iloc[min(i + 1 + max_hold, len(df) - 1)]
                close = float(fut["Close"])
                exit_price = close - exit_friction if cand.signal == "BUY" else close + exit_friction
            else:
                exit_price = exit_price - exit_friction if cand.signal == "BUY" else exit_price + exit_friction

            pnl_pips = (exit_price - entry) * pm if cand.signal == "BUY" else (entry - exit_price) * pm
            trades.append(
                Trade(
                    pair=pair,
                    direction=cand.signal,
                    session=session_for_hour(bar_time.hour),
                    entry_time=bar_time,
                    exit_time=exit_time,
                    pnl_pips=round(float(pnl_pips), 4),
                    entry=round(float(entry), 5 if pm == 10000 else 3),
                    exit=round(float(exit_price), 5 if pm == 10000 else 3),
                    bars_held=bars_held,
                    exit_reason=exit_reason,
                )
            )
            last_exit_i = i + 1 + bars_held

        return {
            "pair": pair,
            "symbol": symbol,
            "pip_mult": pm,
            "source": str(cache_path(pair).relative_to(ROOT)),
            "bars": len(df),
            "from": df.index.min().isoformat(),
            "to": df.index.max().isoformat(),
            "trades": trades,
        }
    finally:
        _pop_bt_env(old_env)


def wilson_lower(wins: int, n: int, z: float) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def pf(pnls: list[float]) -> float:
    gp = sum(p for p in pnls if p > 0)
    gl = -sum(p for p in pnls if p < 0)
    if gl <= 0:
        return float("inf") if gp > 0 else 0.0
    return gp / gl


def max_dd(pnls: list[float]) -> float:
    eq = 0.0
    peak = 0.0
    dd = 0.0
    for pnl in pnls:
        eq += pnl
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def bootstrap_ci(pnls: list[float], *, resamples: int = BOOTSTRAP_RESAMPLES) -> tuple[float, float]:
    import numpy as np

    if not pnls:
        return (0.0, 0.0)
    rng = np.random.default_rng(20260531 + len(pnls))
    arr = np.asarray(pnls, dtype=float)
    means = rng.choice(arr, size=(resamples, len(arr)), replace=True).mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return (float(lo), float(hi))


def kelly(pnls: list[float]) -> float:
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    if not pnls or not wins or not losses:
        return 0.0
    p = len(wins) / len(pnls)
    b = (sum(wins) / len(wins)) / (sum(losses) / len(losses))
    return p - (1 - p) / b


def stats_for(trades: list[Trade]) -> dict:
    pnls = [t.pnl_pips for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    pfx = pf(pnls)
    mean = sum(pnls) / n if n else 0.0
    std = math.sqrt(sum((p - mean) ** 2 for p in pnls) / (n - 1)) if n > 1 else 0.0
    ci = bootstrap_ci(pnls) if n else (0.0, 0.0)
    raw_kelly = kelly(pnls)
    return {
        "N": n,
        "wins": wins,
        "WR": wins / n if n else 0.0,
        "EV": mean,
        "Total": sum(pnls),
        "PF": pfx,
        "MaxDD": max_dd(pnls),
        "Sharpe": (mean / std * math.sqrt(n)) if std > 0 and n > 1 else 0.0,
        "Wilson_lo": wilson_lower(wins, n, WILSON_Z_95),
        "BFlo": wilson_lower(wins, n, BONF_Z),
        "Kelly": raw_kelly,
        "HalfKelly": raw_kelly / 2,
        "BootCI": ci,
    }


def walk_forward(trades: list[Trade], folds: int = 3) -> dict:
    if not trades:
        return {"folds": [], "positive": 0, "p_value": 1.0}
    ordered = sorted(trades, key=lambda t: t.entry_time)
    chunks = []
    for i in range(folds):
        start = round(i * len(ordered) / folds)
        end = round((i + 1) * len(ordered) / folds)
        chunk = ordered[start:end]
        st = stats_for(chunk)
        chunks.append({"fold": i + 1, "N": st["N"], "EV": st["EV"], "BUY_EV": stats_for([t for t in chunk if t.direction == "BUY"])["EV"], "SELL_EV": stats_for([t for t in chunk if t.direction == "SELL"])["EV"]})
    positive = sum(1 for c in chunks if c["N"] > 0 and c["EV"] > 0)
    n = sum(1 for c in chunks if c["N"] > 0)
    p_value = sum(math.comb(n, k) * 0.5**n for k in range(positive, n + 1)) if n else 1.0
    return {"folds": chunks, "positive": positive, "p_value": p_value}


def fmt_num(value: float, digits: int = 2) -> str:
    if isinstance(value, float) and math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def verdict_for(st: dict, wf: dict | None = None) -> str:
    ci_lo, ci_hi = st["BootCI"]
    wf_positive = (wf or {}).get("positive")
    wf_ok = wf_positive == 3 if wf is not None else True
    wf_mid = wf_positive == 2 if wf is not None else False
    if st["N"] == 0:
        return "BLOCKED_DATA"
    if st["BFlo"] > 0.50 and wf_ok and ci_lo > 0:
        return "PROMOTE_CONFIRMED"
    if st["BFlo"] < 0.40 or (wf is not None and wf_positive <= 1) or ci_lo <= 0 <= ci_hi:
        return "PRE_REG_FAIL"
    if 0.40 <= st["BFlo"] <= 0.50 or wf_mid or abs(ci_lo) < 1.0:
        return "NEEDS_MORE_LIVE_N"
    return "NEEDS_MORE_LIVE_N"


def row_for(label: str, st: dict) -> str:
    return (
        f"| {label} | {st['N']} | {fmt_pct(st['WR'])} | {fmt_num(st['EV'])} | "
        f"{fmt_num(st['PF'])} | {fmt_num(st['Wilson_lo'], 3)} | {fmt_num(st['BFlo'], 3)} | "
        f"{fmt_num(st['Kelly'], 3)} | {fmt_num(st['HalfKelly'], 3)} | {fmt_num(st['MaxDD'])} | "
        f"[{fmt_num(st['BootCI'][0])}, {fmt_num(st['BootCI'][1])}] |"
    )


def best_cell(pair_trades: list[Trade]) -> tuple[str, dict]:
    cells = []
    for direction in ("BUY", "SELL"):
        for session in ("Asia", "London", "Overlap", "NY"):
            label = f"{direction} {session}"
            st = stats_for([t for t in pair_trades if t.direction == direction and t.session == session])
            if st["N"] > 0:
                cells.append((label, st))
    if not cells:
        return ("NONE", stats_for([]))
    cells.sort(key=lambda item: (item[1]["EV"], item[1]["N"]), reverse=True)
    return cells[0]


def render_report(results: dict[str, dict]) -> str:
    lines = [
        f"# Donchian x NZD pair 365d BT pre-reg evidence ({REPORT_DATE})",
        "",
        f"- Strategy: `{STRATEGY}` via production `DonchianMomentumBreakout.evaluate(... backtest_mode=True)`.",
        "- Data source: `data/cache/massive/{PAIR}_15m.parquet` only; Yahoo fallback is not used.",
        f"- Lookback request: `utcnow - {LOOKBACK_DAYS}d` to `utcnow`; available MASSIVE bars end at each cache's latest timestamp.",
        f"- Bonferroni: m={BONFERRONI_M}, alpha={BONF_ALPHA:.6f}, z={BONF_Z:.3f}. Bootstrap EV CI uses {BOOTSTRAP_RESAMPLES:,} resamples.",
        "",
        "## Source coverage",
        "",
        "| Pair | Source | Bars | From | To | pip_mult |",
        "|---|---|---:|---|---|---:|",
    ]
    for pair in ALL_PAIRS:
        r = results[pair]
        lines.append(f"| {pair} | `{r['source']}` | {r['bars']} | {r['from']} | {r['to']} | {r['pip_mult']} |")

    lines.extend([
        "",
        "## Overall and direction split",
        "",
        "| Pair/Cohort | N | WR | EV(pips) | PF | Wilson_lo | BFlo | Kelly | HalfKelly | MaxDD(pips) | Bootstrap EV 95% CI |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    pair_stats = {}
    pair_wf = {}
    for pair in ALL_PAIRS:
        trades = results[pair]["trades"]
        pair_stats[(pair, "Overall")] = stats_for(trades)
        pair_wf[pair] = walk_forward(trades)
        lines.append(row_for(f"{pair} Overall", pair_stats[(pair, "Overall")]))
        for direction in ("BUY", "SELL"):
            lines.append(row_for(f"{pair} {direction}", stats_for([t for t in trades if t.direction == direction])))

    lines.extend([
        "",
        "## Direction x session cells",
        "",
        "| Pair/Cell | N | WR | EV(pips) | PF | Wilson_lo | BFlo | Kelly | HalfKelly | MaxDD(pips) | Bootstrap EV 95% CI |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for pair in ALL_PAIRS:
        trades = results[pair]["trades"]
        for direction in ("BUY", "SELL"):
            for session in ("Asia", "London", "Overlap", "NY"):
                cohort = [t for t in trades if t.direction == direction and t.session == session]
                lines.append(row_for(f"{pair} {direction} {session}", stats_for(cohort)))

    lines.extend([
        "",
        "## Walk-forward 3-fold",
        "",
        "| Pair | Fold | N | EV | BUY_EV | SELL_EV |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for pair in ALL_PAIRS:
        for fold in pair_wf[pair]["folds"]:
            lines.append(
                f"| {pair} | {fold['fold']} | {fold['N']} | {fmt_num(fold['EV'])} | "
                f"{fmt_num(fold['BUY_EV'])} | {fmt_num(fold['SELL_EV'])} |"
            )
        lines.append(
            f"| {pair} | sign-test | {pair_wf[pair]['positive']}/3 positive folds | "
            f"p={pair_wf[pair]['p_value']:.3f} |  |  |"
        )

    lines.extend([
        "",
        "## Control comparison",
        "",
        "| Pair | Role | N | WR | EV(pips) | Total(pips) | BFlo | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ])
    for pair in ALL_PAIRS:
        st = pair_stats[(pair, "Overall")]
        role = "LIVE target" if pair in TARGET_PAIRS else "control"
        lines.append(
            f"| {pair} | {role} | {st['N']} | {fmt_pct(st['WR'])} | {fmt_num(st['EV'])} | "
            f"{fmt_num(st['Total'])} | {fmt_num(st['BFlo'], 3)} | {verdict_for(st, pair_wf[pair])} |"
        )

    lines.extend([
        "",
        "## Shadow vs BT degradation",
        "",
        "| Pair | Shadow N | Shadow WR | Shadow EV | Shadow Total | BT N | BT WR | BT EV | BT Total | EV delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for pair in ALL_PAIRS:
        sh = SHADOW_BASELINE[pair]
        st = pair_stats[(pair, "Overall")]
        lines.append(
            f"| {pair} | {sh['N']} | {fmt_pct(sh['WR'])} | {fmt_num(sh['EV'])} | {fmt_num(sh['Total'])} | "
            f"{st['N']} | {fmt_pct(st['WR'])} | {fmt_num(st['EV'])} | {fmt_num(st['Total'])} | "
            f"{fmt_num(st['EV'] - sh['EV'])} |"
        )

    lines.extend([
        "",
        "## Final verdict cells",
        "",
        "| Cell | N | WR | EV | BFlo | WF | Bootstrap CI | Verdict | Action proposal |",
        "|---|---:|---:|---:|---:|---|---|---|---|",
    ])
    for pair in TARGET_PAIRS:
        overall = pair_stats[(pair, "Overall")]
        wf = pair_wf[pair]
        overall_verdict = verdict_for(overall, wf)
        action = {
            "PROMOTE_CONFIRMED": "continue LIVE 1.0x; consider relaxing withdrawal only after Live N>=30",
            "NEEDS_MORE_LIVE_N": "continue LIVE 1.0x but keep strict withdrawal until Live N=30",
            "PRE_REG_FAIL": "propose immediate demote to 0.05x and trigger Live N=10 withdrawal check",
            "BLOCKED_DATA": "separate data prep task",
        }[overall_verdict]
        lines.append(
            f"| {pair} overall | {overall['N']} | {fmt_pct(overall['WR'])} | {fmt_num(overall['EV'])} | "
            f"{fmt_num(overall['BFlo'], 3)} | {wf['positive']}/3 p={wf['p_value']:.3f} | "
            f"[{fmt_num(overall['BootCI'][0])}, {fmt_num(overall['BootCI'][1])}] | {overall_verdict} | {action} |"
        )
        label, cell_st = best_cell(results[pair]["trades"])
        cell_verdict = verdict_for(cell_st, None)
        cell_action = "best-cell only; do not change LIVE routing without new pre-reg"
        lines.append(
            f"| {pair} best-cell ({label}) | {cell_st['N']} | {fmt_pct(cell_st['WR'])} | {fmt_num(cell_st['EV'])} | "
            f"{fmt_num(cell_st['BFlo'], 3)} | n/a | [{fmt_num(cell_st['BootCI'][0])}, {fmt_num(cell_st['BootCI'][1])}] | "
            f"{cell_verdict} | {cell_action} |"
        )

    lines.extend([
        "",
        "## Notes",
        "",
        "- `BT_REQUIRE_MASSIVE_CACHE=1` is set before imports; if a required parquet is absent, the runner raises instead of falling back to Yahoo.",
        "- The generic `app.run_daytrade_backtest` path is not used because its DT whitelist does not include `donchian_momentum_breakout`; this runner calls the production strategy evaluator directly with `backtest_mode=True` and uses app spread/slippage helpers.",
        "- Controls are sanity floors only. They are not candidates for LIVE changes in this task.",
        "",
    ])
    return "\n".join(lines)


def run_all() -> dict[str, dict]:
    return {pair: run_pair_bt(pair) for pair in ALL_PAIRS}


def main() -> int:
    missing = [str(cache_path(pair).relative_to(ROOT)) for pair in ALL_PAIRS if not cache_path(pair).exists()]
    if missing:
        raise FileNotFoundError("missing required MASSIVE parquet cache(s): " + ", ".join(missing))
    results = run_all()
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(render_report(results), encoding="utf-8")
    print(f"Saved: {OUTFILE.relative_to(ROOT)}")
    for pair, result in results.items():
        st = stats_for(result["trades"])
        print(f"{pair}: N={st['N']} WR={fmt_pct(st['WR'])} EV={fmt_num(st['EV'])} BFlo={fmt_num(st['BFlo'], 3)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
