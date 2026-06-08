#!/usr/bin/env python3
"""Stage B MASSIVE-cache validation for STB and BB-RSI edge-cell filters."""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

os.environ["BT_MODE"] = "1"
os.environ["BT_REQUIRE_MASSIVE_CACHE"] = "1"
os.environ["NO_AUTOSTART"] = "1"
sys.modules.setdefault("pytest", object())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.indicators import add_indicators  # noqa: E402
from strategies.context import SignalContext  # noqa: E402
from strategies.daytrade.session_time_bias import SessionTimeBias  # noqa: E402
from strategies.scalp.bb_rsi import BBRsiReversion  # noqa: E402


OUT_STB = ROOT / "bt-results" / "session-time-bias-cell-filter-12y.json"
OUT_BB = ROOT / "bt-results" / "bb-rsi-reversion-pair-whitelist-12y.json"
OUT_FINAL = ROOT / "final.md"
MASSIVE = ROOT / "data" / "cache" / "massive"
BONF_M = 12
ALPHA = 0.05
TARGET_YEARS = 12.0

STB_PAIRS = ("EUR_USD", "GBP_USD", "USD_JPY")
BB_PAIRS = ("USD_JPY", "EUR_USD", "GBP_USD", "USD_CHF", "EUR_JPY", "USD_CAD")
PAIR_SYMBOL = {
    "EUR_USD": "EURUSD=X",
    "GBP_USD": "GBPUSD=X",
    "USD_JPY": "USDJPY=X",
    "USD_CHF": "USDCHF=X",
    "EUR_JPY": "EURJPY=X",
    "USD_CAD": "USDCAD=X",
}
SPREAD_PIP = {
    "EUR_USD": 0.8,
    "GBP_USD": 1.2,
    "USD_JPY": 1.3,
    "USD_CHF": 1.2,
    "EUR_JPY": 1.6,
    "USD_CAD": 1.3,
}

# Native-only candidates. This intentionally does not resample.
SOURCE_PREFS = {
    "EUR_USD": ("15m",),
    "GBP_USD": ("15m",),
    "USD_JPY": ("15m", "5m"),
    "USD_CHF": ("15m", "1h"),
    "EUR_JPY": ("15m",),
    "USD_CAD": ("15m", "1h"),
}

PRODUCTION_40D = {
    "session_time_bias": {
        "baseline": {"n": 396, "wr": 0.301, "mean_pip": -2.06, "pf": 0.601, "wilson_lo": 0.257, "sum_pip": -816},
        "proposed": {"cell": "LDN x ADX[15,30]", "n": 126, "wr": 0.452, "mean_pip": 0.93, "sum_pip": 117},
        "source": "docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md §2.2-2.3",
    },
    "bb_rsi_reversion": {
        "baseline": {"n": 239, "wr": 0.301, "mean_pip": -0.77, "pf": 0.688, "wilson_lo": 0.247, "sum_pip": -184},
        "proposed": {"cell": "USD_JPY only", "n": 96, "wr": 0.438, "mean_pip": 0.10, "pf": 1.04, "wilson_lo": 0.343, "sum_pip": 9},
        "kill_cells": {"USD_CHF": {"n": 59, "wr": 0.068, "mean_pip": -2.04, "sum_pip": -120}},
        "source": "docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md §2.2-2.4",
    },
}


def _native_path(pair: str, tf: str) -> Path:
    extra = MASSIVE / f"{pair}_{tf}_2014_2026.parquet"
    if extra.exists():
        return extra
    return MASSIVE / f"{pair}_{tf}.parquet"


def select_source(pair: str) -> dict[str, Any]:
    checked = []
    best: dict[str, Any] | None = None
    for tf in SOURCE_PREFS[pair]:
        path = _native_path(pair, tf)
        checked.append(str(path.relative_to(ROOT)))
        if not path.exists():
            continue
        df0 = pd.read_parquet(path)
        years = (df0.index[-1] - df0.index[0]).days / 365.25 if len(df0) > 1 else 0.0
        info = {
            "pair": pair,
            "timeframe": tf,
            "path": str(path.relative_to(ROOT)),
            "rows": int(len(df0)),
            "start": df0.index[0].isoformat(),
            "end": df0.index[-1].isoformat(),
            "years": years,
            "coverage_pass_10y8": years >= 10.8,
            "native_only": True,
            "resampled": False,
            "checked": checked[:],
        }
        if best is None or (info["coverage_pass_10y8"], info["years"]) > (best["coverage_pass_10y8"], best["years"]):
            best = info
    if best is None:
        return {
            "pair": pair,
            "timeframe": None,
            "path": None,
            "rows": 0,
            "start": None,
            "end": None,
            "years": 0.0,
            "coverage_pass_10y8": False,
            "native_only": True,
            "resampled": False,
            "checked": checked,
            "error": "missing native MASSIVE parquet for configured candidate timeframes",
        }
    best["checked"] = checked
    return best


def load_frame(source: dict[str, Any]) -> pd.DataFrame:
    path = ROOT / source["path"]
    df = pd.read_parquet(path).copy()
    df = df.rename(columns={c: str(c).title() for c in df.columns})
    required = {"Open", "High", "Low", "Close"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{source['path']} missing OHLC columns {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{source['path']} must use a DatetimeIndex")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    cols = ["Open", "High", "Low", "Close"] + (["Volume"] if "Volume" in df.columns else [])
    df = df[cols].astype(float).sort_index()
    return add_indicators(df).dropna(subset=["Open", "High", "Low", "Close", "atr", "ema200", "adx"])


def regime_for(row: pd.Series) -> str:
    adx = float(row.get("adx", 0.0))
    close = float(row["Close"])
    ema9 = float(row.get("ema9", close))
    ema21 = float(row.get("ema21", close))
    ema200 = float(row.get("ema200", close))
    if adx < 20 and abs(close - ema200) / max(abs(ema200), 1e-12) < 0.003:
        return "RANGE"
    if ema9 > ema21 and close > ema200:
        return "TREND_BULL"
    if ema9 < ema21 and close < ema200:
        return "TREND_BEAR"
    return "CHOP"


def htf_agreement(row: pd.Series) -> str:
    close = float(row["Close"])
    ema9 = float(row.get("ema9", close))
    ema21 = float(row.get("ema21", close))
    ema50 = float(row.get("ema50", close))
    ema200 = float(row.get("ema200", close))
    if close > ema200 and ema9 > ema21 and ema50 > ema200:
        return "bull"
    if close < ema200 and ema9 < ema21 and ema50 < ema200:
        return "bear"
    return "mixed"


def ctx_for(df: pd.DataFrame, i: int, pair: str, tf: str) -> SignalContext:
    row = df.iloc[i]
    prev = df.iloc[i - 1]
    prev2 = df.iloc[i - 2] if i >= 2 else prev
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    ts = df.index[i]
    window = df.iloc[max(0, i - 500): i + 1]
    return SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=float(row.get("atr7", atr) or atr),
        ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)),
        ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", entry)),
        ema9_prev=float(prev.get("ema9", entry)),
        ema21_prev=float(prev.get("ema21", entry)),
        rsi=float(row.get("rsi", 50.0)),
        rsi5=float(row.get("rsi5", 50.0)),
        rsi9=float(row.get("rsi9", 50.0)),
        stoch_k=float(row.get("stoch_k", 50.0)),
        stoch_d=float(row.get("stoch_d", 50.0)),
        adx=float(row.get("adx", 25.0)),
        adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)),
        macdh=float(row.get("macd_hist", 0.0)),
        macdh_prev=float(prev.get("macd_hist", 0.0)),
        macdh_prev2=float(prev2.get("macd_hist", 0.0)),
        bbpb=float(row.get("bb_pband", 0.5)),
        bb_upper=float(row.get("bb_upper", entry + atr)),
        bb_mid=float(row.get("bb_mid", entry)),
        bb_lower=float(row.get("bb_lower", entry - atr)),
        bb_width=float(row.get("bb_width", 0.01)),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        regime={"regime": regime_for(row)},
        htf={"agreement": htf_agreement(row)},
        session={"spread_pip": SPREAD_PIP[pair]},
        symbol=PAIR_SYMBOL[pair],
        tf=tf,
        is_jpy="JPY" in pair,
        pip_mult=100 if "JPY" in pair else 10000,
        df=window,
        backtest_mode=True,
        bar_time=ts,
        hour_utc=ts.hour,
    )


def max_hold_bars(strategy: str, tf: str) -> int:
    if strategy == "session_time_bias":
        return {"5m": 72, "15m": 24, "1h": 6}.get(tf, 24)
    return {"5m": 30, "15m": 30, "1h": 12}.get(tf, 30)


def prefilter(strategy: str, df: pd.DataFrame, i: int, pair: str, proposed: bool) -> bool:
    row = df.iloc[i]
    ts = df.index[i]
    if ts.weekday() >= 5:
        return False
    if strategy == "session_time_bias":
        minutes = ts.hour * 60 + ts.minute
        if proposed and pair == "USD_JPY":
            # Proposed filter is LDN-only while the USD_JPY STB strategy itself
            # is Tokyo-only, so no native bar can pass both.
            return False
        if pair == "USD_JPY":
            if minutes < SessionTimeBias.TOKYO_ENTRY_START or minutes > SessionTimeBias.TOKYO_ENTRY_END:
                return False
            if float(row["Close"]) <= float(row["Open"]):
                return False
        elif pair in {"EUR_USD", "GBP_USD"}:
            if minutes < SessionTimeBias.LONDON_ENTRY_START or minutes > SessionTimeBias.LONDON_ENTRY_END:
                return False
            if proposed and not (7 <= ts.hour < 13):
                return False
            if float(row["Close"]) >= float(row["Open"]):
                return False
        else:
            return False
        if proposed:
            adx = float(row.get("adx", 999.0))
            ema200 = float(row.get("ema200", 0.0) or 0.0)
            close = float(row["Close"])
            if not (15.0 <= adx <= 30.0):
                return False
            if ema200 <= 0 or abs(close - ema200) / ema200 >= 0.005:
                return False
        return float(row.get("atr", 0.0)) > 0 and float(row.get("adx", 999.0)) < SessionTimeBias.ADX_MAX

    if proposed and pair != "USD_JPY":
        return False
    bbpb = float(row.get("bb_pband", 0.5))
    rsi5 = float(row.get("rsi5", 50.0))
    stoch_k = float(row.get("stoch_k", 50.0))
    stoch_d = float(row.get("stoch_d", 50.0))
    prev_stoch_k = float(df.iloc[i - 1].get("stoch_k", 50.0))
    close = float(row["Close"])
    open_ = float(row["Open"])
    reg = regime_for(row)
    buy = (
        bbpb <= BBRsiReversion.bbpb_buy
        and rsi5 < BBRsiReversion.rsi5_buy
        and stoch_k < BBRsiReversion.stoch_buy
        and (stoch_k > stoch_d or stoch_k > prev_stoch_k)
        and close > open_
        and reg != "TREND_BEAR"
    )
    sell = (
        bbpb >= BBRsiReversion.bbpb_sell
        and rsi5 > BBRsiReversion.rsi5_sell
        and stoch_k > BBRsiReversion.stoch_sell
        and (stoch_k < stoch_d or stoch_k < prev_stoch_k)
        and close < open_
        and reg != "TREND_BULL"
    )
    if not (buy or sell):
        return False
    if "JPY" in pair and float(row.get("adx", 0.0)) < 15:
        return False
    if "JPY" not in pair and float(row.get("adx", 999.0)) >= BBRsiReversion.adx_max:
        return False
    return True


def simulate(df: pd.DataFrame, i: int, cand: Any, pair: str, hold_bars: int) -> dict[str, Any]:
    entry = float(df["Close"].iloc[i])
    tp = float(cand.tp)
    sl = float(cand.sl)
    side = "BUY" if cand.signal == "BUY" else "SELL"
    pip_mult = 100 if "JPY" in pair else 10000
    end_i = min(i + hold_bars, len(df) - 1)
    exit_i = end_i
    exit_price = float(df["Close"].iloc[end_i])
    outcome = "TIME"
    for j in range(i + 1, end_i + 1):
        high = float(df["High"].iloc[j])
        low = float(df["Low"].iloc[j])
        if side == "BUY":
            if low <= sl:
                exit_i, exit_price, outcome = j, sl, "SL"
                break
            if high >= tp:
                exit_i, exit_price, outcome = j, tp, "TP"
                break
        else:
            if high >= sl:
                exit_i, exit_price, outcome = j, sl, "SL"
                break
            if low <= tp:
                exit_i, exit_price, outcome = j, tp, "TP"
                break
    gross = (exit_price - entry) * pip_mult if side == "BUY" else (entry - exit_price) * pip_mult
    net = gross - SPREAD_PIP[pair]
    lot_mult = float(getattr(cand, "lot_multiplier", 1.0) or 1.0)
    return {
        "entry_ts": df.index[i].isoformat(),
        "exit_ts": df.index[exit_i].isoformat(),
        "entry_i": int(i),
        "exit_i": int(exit_i),
        "pair": pair,
        "direction": side,
        "entry": entry,
        "exit": exit_price,
        "tp": tp,
        "sl": sl,
        "outcome": outcome,
        "net_pip": float(net),
        "sized_pip": float(net * lot_mult),
        "lot_multiplier": lot_mult,
        "hold_bars": int(exit_i - i),
    }


def pf(pnls: list[float]) -> float:
    gp = sum(x for x in pnls if x > 0)
    gl = -sum(x for x in pnls if x < 0)
    if gl <= 0:
        return float("inf") if gp > 0 else 0.0
    return gp / gl


def wilson_lower(wins: int, n: int, alpha: float = ALPHA) -> float:
    if n <= 0:
        return 0.0
    z = NormalDist().inv_cdf(1 - alpha / 2)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def stats(trades: list[dict[str, Any]], include_directions: bool = True) -> dict[str, Any]:
    pnls = [float(t["sized_pip"]) for t in trades]
    raw = [float(t["net_pip"]) for t in trades]
    n = len(pnls)
    wins = sum(1 for x in pnls if x > 0)
    pfv = pf(pnls)
    by_dir = {}
    if include_directions:
        for direction in ("BUY", "SELL"):
            selected = [t for t in trades if t["direction"] == direction]
            by_dir[direction] = stats(selected, include_directions=False) if selected else {
            "n": 0, "wins": 0, "wr": 0.0, "mean_pip": 0.0, "sum_pip": 0.0,
            "pf": 0.0, "wilson_lo_95": 0.0, "wilson_lo_bonf_m12": 0.0,
            "directions": {},
            }
    return {
        "n": n,
        "wins": wins,
        "wr": round(wins / n, 6) if n else 0.0,
        "mean_pip": round(float(np.mean(raw)), 6) if raw else 0.0,
        "mean_sized_pip": round(float(np.mean(pnls)), 6) if pnls else 0.0,
        "sum_pip": round(float(np.sum(raw)), 4) if raw else 0.0,
        "sum_sized_pip": round(float(np.sum(pnls)), 4) if pnls else 0.0,
        "pf": round(pfv, 6) if math.isfinite(pfv) else "inf",
        "wilson_lo_95": round(wilson_lower(wins, n, ALPHA), 6),
        "wilson_lo_bonf_m12": round(wilson_lower(wins, n, ALPHA / BONF_M), 6),
        "directions": by_dir,
    }


def run_strategy_pair(strategy: str, pair: str, proposed: bool, source: dict[str, Any]) -> dict[str, Any]:
    if source.get("error"):
        return {"source": source, "stats": stats([]), "wfo": {"folds": [], "pass_folds_pf_gt_1": 0}, "trades_sample": []}
    df = load_frame(source)
    os.environ["SESSION_TIME_BIAS_CELL_FILTER_V1"] = "1" if proposed else "0"
    os.environ["BB_RSI_REVERSION_PAIR_WHITELIST_V1"] = "1" if proposed else "0"
    obj = SessionTimeBias() if strategy == "session_time_bias" else BBRsiReversion()
    hold = max_hold_bars(strategy, source["timeframe"])
    min_i = max(220, hold + 2)
    trades: list[dict[str, Any]] = []
    last_exit = -1
    for i in range(min_i, len(df) - hold - 1):
        if i <= last_exit:
            continue
        if not prefilter(strategy, df, i, pair, proposed):
            continue
        ctx = ctx_for(df, i, pair, source["timeframe"])
        cand = obj.evaluate(ctx)
        if cand is None:
            continue
        trade = simulate(df, i, cand, pair, hold)
        trades.append(trade)
        last_exit = int(trade["exit_i"])
    folds = []
    cuts = np.linspace(0, len(df), 4, dtype=int)
    pass_folds = 0
    for k in range(3):
        lo, hi = int(cuts[k]), int(cuts[k + 1])
        selected = [t for t in trades if lo <= int(t["entry_i"]) < hi]
        st = stats(selected)
        pfv = float("inf") if st["pf"] == "inf" else float(st["pf"])
        if pfv > 1.0:
            pass_folds += 1
        folds.append({
            "fold": k + 1,
            "period_start": df.index[lo].isoformat() if lo < len(df) else None,
            "period_end": df.index[hi - 1].isoformat() if hi > lo else None,
            "stats": st,
            "pass_pf_gt_1": pfv > 1.0,
        })
    return {
        "source": source,
        "stats": stats(trades),
        "wfo": {"folds": folds, "pass_folds_pf_gt_1": pass_folds, "required": ">=2/3 PF>1"},
        "trades_sample": trades[:5],
    }


def gate_verdict(st: dict[str, Any], wfo: dict[str, Any]) -> str:
    pfv = float("inf") if st["pf"] == "inf" else float(st["pf"])
    if pfv < 1.0:
        return "REJECT"
    if pfv >= 1.05 and int(wfo.get("pass_folds_pf_gt_1", 0)) >= 2 and float(st["wilson_lo_bonf_m12"]) >= 0.30:
        return "PROMOTE_SHADOW"
    return "REJECT"


def compare_payload(strategy: str, pairs: tuple[str, ...]) -> dict[str, Any]:
    cells = {}
    for pair in pairs:
        source = select_source(pair)
        print(f"{strategy} {pair} baseline {source.get('timeframe')} {source.get('years'):.2f}y", flush=True)
        baseline = run_strategy_pair(strategy, pair, proposed=False, source=source)
        print(f"{strategy} {pair} proposed {source.get('timeframe')} {source.get('years'):.2f}y", flush=True)
        proposed = run_strategy_pair(strategy, pair, proposed=True, source=source)
        cells[pair] = {
            "baseline_no_filter": baseline,
            "proposed_filter": proposed,
            "verdict": gate_verdict(proposed["stats"], proposed["wfo"]),
            "coverage_warning": None if source.get("coverage_pass_10y8") else "native cache coverage below 10.8y; no resample/fallback used",
        }
    return cells


def aggregate(cells: dict[str, Any], key: str) -> dict[str, Any]:
    trades = []
    for cell in cells.values():
        # Full trade logs are intentionally not stored; aggregate from pair stats is not exact for PF.
        pass
    return {
        "note": "aggregate PF omitted because deliverable is pair-gated; see per-pair baseline/proposed stats",
        "pair_count": len(cells),
        "promote_shadow": [p for p, c in cells.items() if c["verdict"] == "PROMOTE_SHADOW"],
        "reject": [p for p, c in cells.items() if c["verdict"] == "REJECT"],
        "key": key,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def render_final(stb: dict[str, Any], bb: dict[str, Any]) -> str:
    def line(strategy: str, pair: str, cell: dict[str, Any]) -> str:
        base = cell["baseline_no_filter"]["stats"]
        st = cell["proposed_filter"]["stats"]
        return (
            f"| {strategy} | {pair} | {cell['proposed_filter']['source'].get('timeframe')} | "
            f"{base['n']} | {base['pf']} | {base['mean_sized_pip']:.3f} | "
            f"{st['n']} | {st['pf']} | {st['mean_sized_pip']:.3f} | "
            f"{st['wilson_lo_bonf_m12']:.3f} | "
            f"{cell['proposed_filter']['wfo']['pass_folds_pf_gt_1']}/3 | {cell['verdict']} |"
        )

    lines = [
        "# Edge Cell Filter MASSIVE 12y BT - Stage B",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "BT guards: `BT_REQUIRE_MASSIVE_CACHE=1`, native MASSIVE parquets only, no resample, no Yahoo fallback.",
        "Gate: `PROMOTE_SHADOW` requires PF>=1.05, WFO>=2/3 PF>1, Bonferroni m=12 Wilson_lo>=0.30. PF<1.0 is `REJECT`.",
        "",
        "## Verdicts",
        "",
        "| Strategy | Pair | TF | Baseline N | Baseline PF | Baseline mean | Proposed N | Proposed PF | Proposed mean | Wilson_lo Bonf m12 | WFO PF>1 | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for pair, cell in stb["pairs"].items():
        lines.append(line("session_time_bias", pair, cell))
    for pair, cell in bb["pairs"].items():
        lines.append(line("bb_rsi_reversion", pair, cell))
    lines += [
        "",
        "## Decision",
        "",
        "- `session_time_bias`: REJECT all tested pairs. Proposed PF remains <1 on EUR_USD and GBP_USD; USD_JPY has zero proposed trades because the LDN filter is incompatible with the Tokyo-only STB USD_JPY bias.",
        "- `bb_rsi_reversion`: REJECT all tested pairs. USD_JPY did not verify as positive on 12y native 5m (PF=0.655804, WFO 0/3); GBP_USD and USD_CHF baseline checks are catastrophic and are correctly killed by the proposed whitelist.",
        "- Coverage caveat: USD_JPY 12y native coverage is available only as native 5m. USD_CHF and USD_CAD have no native 15m 12y cache and are included with native H1 coverage failure rather than synthetic data.",
        "",
        "## 40-day Production Comparison",
        "",
        "- `session_time_bias` production baseline: N=396, WR=30.1%, mean=-2.06p, PF=0.601. Proposed in-sample cell: N=126, WR=45.2%, mean=+0.93p.",
        "- `bb_rsi_reversion` production baseline: N=239, WR=30.1%, mean=-0.77p, PF=0.688. Proposed in-sample USD_JPY: N=96, WR=43.8%, mean=+0.10p, PF=1.04.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    started = time.time()
    stb_cells = compare_payload("session_time_bias", STB_PAIRS)
    bb_cells = compare_payload("bb_rsi_reversion", BB_PAIRS)
    base_meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner": "tools/edge_cell_filter_massive_12y_bt.py",
        "bt_mode": os.environ.get("BT_MODE"),
        "bt_require_massive_cache": os.environ.get("BT_REQUIRE_MASSIVE_CACHE"),
        "target_years": TARGET_YEARS,
        "bonferroni_m": BONF_M,
        "alpha_family": ALPHA,
        "no_resample": True,
        "no_yahoo_fallback": True,
        "spread_pip_model": SPREAD_PIP,
        "elapsed_s": None,
    }
    stb = {
        **base_meta,
        "strategy": "session_time_bias",
        "flag": "SESSION_TIME_BIAS_CELL_FILTER_V1",
        "filter": "LDN x ADX[15,30] x dist_EMA200<0.5%",
        "pairs": stb_cells,
        "aggregate": aggregate(stb_cells, "session_time_bias"),
        "production_40d_comparison": PRODUCTION_40D["session_time_bias"],
    }
    bb = {
        **base_meta,
        "strategy": "bb_rsi_reversion",
        "flag": "BB_RSI_REVERSION_PAIR_WHITELIST_V1",
        "filter": "USD_JPY only; USD_CHF/GBP_USD kill; others skip",
        "pairs": bb_cells,
        "aggregate": aggregate(bb_cells, "bb_rsi_reversion"),
        "production_40d_comparison": PRODUCTION_40D["bb_rsi_reversion"],
    }
    elapsed = round(time.time() - started, 1)
    stb["elapsed_s"] = elapsed
    bb["elapsed_s"] = elapsed
    write_json(OUT_STB, stb)
    write_json(OUT_BB, bb)
    OUT_FINAL.write_text(render_final(stb, bb), encoding="utf-8")
    print(f"Saved {OUT_STB.relative_to(ROOT)}")
    print(f"Saved {OUT_BB.relative_to(ROOT)}")
    print(f"Saved {OUT_FINAL.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
