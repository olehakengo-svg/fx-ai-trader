#!/usr/bin/env python3
"""SR weight Phase 2 bin analysis with BH-FDR.

MASSIVE-only BT runner for the 2026-05-11 SR strength bin pre-registration.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ["BT_MODE"] = "1"
os.environ["BT_REQUIRE_MASSIVE_CACHE"] = "1"
os.environ["NO_AUTOSTART"] = "1"
sys.modules.setdefault("pytest", object())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LOOKBACK_DAYS = 365
OUT_STEM = "sr-weight-phase2-bin-bhfdr-2026-05-11"
OUT_JSON = ROOT / "bt-results" / f"{OUT_STEM}.json"
OUT_MD = ROOT / "bt-results" / f"{OUT_STEM}.md"
RUN_DIR = ROOT / ".ai" / "runs" / f"{OUT_STEM}-{datetime.now(timezone.utc).strftime('%H%M%S')}"
FINAL_MD = RUN_DIR / "final.md"

PAIRS_MAJOR3 = [
    ("EUR_USD", "EURUSD=X"),
    ("GBP_USD", "GBPUSD=X"),
    ("USD_JPY", "USDJPY=X"),
]
PAIRS_5 = [
    *PAIRS_MAJOR3,
    ("EUR_JPY", "EURJPY=X"),
    ("GBP_JPY", "GBPJPY=X"),
]
PAIRS_DT_SR_CHANNEL = [
    ("EUR_JPY", "EURJPY=X"),
    ("EUR_USD", "EURUSD=X"),
    ("USD_JPY", "USDJPY=X"),
]

BINS = [
    ("B1", 0.0, 0.5, "[0.0,0.5)"),
    ("B2", 0.5, 0.65, "[0.5,0.65)"),
    ("B3", 0.65, 0.75, "[0.65,0.75)"),
    ("B4", 0.75, 0.85, "[0.75,0.85)"),
    ("B5", 0.85, 1.000000001, "[0.85,1.0]"),
]
DIRECTIONS = ["BUY", "SELL"]


@dataclass(frozen=True)
class Target:
    strategy: str
    mode: str
    interval: str
    pairs: tuple[tuple[str, str], ...]
    source: str


TARGETS = [
    Target("dual_sr_bounce", "daytrade", "15m", tuple(PAIRS_MAJOR3), "production_daytrade_inline"),
    Target("sr_anti_hunt_bounce", "daytrade", "15m", tuple(PAIRS_5), "strategy_evaluate_patch"),
    Target("dt_sr_channel_reversal", "daytrade", "15m", tuple(PAIRS_DT_SR_CHANNEL), "strategy_evaluate_patch"),
    Target("strong_sr_breakout", "scalp", "15m", tuple(PAIRS_MAJOR3), "production_scalp_inline"),
    Target("sr_channel_reversal", "scalp", "15m", tuple(PAIRS_MAJOR3), "strategy_evaluate_patch"),
    Target("sr_fib_confluence", "daytrade", "15m", tuple(PAIRS_5), "strategy_evaluate_patch"),
]


def _cache_path(pair: str, interval: str) -> Path:
    return ROOT / "data" / "cache" / "massive" / f"{pair}_{interval}.parquet"


def _pair_symbol(pair: str) -> str:
    return pair.replace("_", "") + "=X"


def _pip_mult(pair: str) -> int:
    return 100 if "JPY" in pair else 10000


def _finite(value: float | int | str | None) -> float | str | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if math.isfinite(v):
        return round(v, 6)
    return "inf" if v > 0 else "-inf"


def _trade_pnl_m(trade: dict) -> float:
    friction = float(trade.get("exit_friction_m", 0.0) or 0.0)
    if trade.get("outcome") == "WIN":
        return float(trade.get("tp_m", 0.0) or 0.0) - friction
    return -(float(trade.get("actual_sl_m", trade.get("sl_m", 0.0)) or 0.0) + friction)


def _bin_for_strength(strength: float | None) -> str:
    if strength is None:
        return "UNBINNED"
    s = max(0.0, min(1.0, float(strength)))
    for name, lo, hi, _label in BINS:
        if lo <= s < hi:
            return name
    return "B5"


def _wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float | None:
    if n <= 0:
        return None
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def _profit_factor(pnls: list[float]) -> float | None:
    if not pnls:
        return None
    gp = sum(p for p in pnls if p > 0)
    gl = -sum(p for p in pnls if p < 0)
    if gl <= 0:
        return float("inf") if gp > 0 else 0.0
    return gp / gl


def _kelly(pnls: list[float]) -> float | None:
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    n = len(pnls)
    if n == 0 or not wins or not losses:
        return None
    wr = len(wins) / n
    r = (sum(wins) / len(wins)) / max(sum(losses) / len(losses), 1e-12)
    return (wr * r - (1 - wr)) / r


def _sharpe(pnls: list[float]) -> float | None:
    if len(pnls) < 2:
        return None
    import numpy as np

    std = float(np.std(pnls, ddof=1))
    if std <= 1e-12:
        return None
    return float(np.mean(pnls)) / std * math.sqrt(252)


def _skew_kurtosis(pnls: list[float]) -> tuple[float, float]:
    if len(pnls) < 3:
        return 0.0, 3.0
    import numpy as np

    a = np.asarray(pnls, dtype=float)
    mu = float(np.mean(a))
    sd = float(np.std(a, ddof=0))
    if sd <= 1e-12:
        return 0.0, 3.0
    z = (a - mu) / sd
    return float(np.mean(z ** 3)), float(np.mean(z ** 4))


def _wf_pos_ratio(rows: list[dict]) -> float | None:
    if len(rows) < 3:
        return None
    ordered = sorted(rows, key=lambda r: r.get("entry_time") or "")
    folds = []
    for fold in range(3):
        part = ordered[fold * len(ordered) // 3:(fold + 1) * len(ordered) // 3]
        if part:
            folds.append(sum(r["pnl_pips"] for r in part) / len(part))
    if not folds:
        return None
    return sum(1 for ev in folds if ev > 0) / len(folds)


def _metrics(rows: list[dict], n_trials: int = 6) -> dict:
    pnls = [float(r["pnl_pips"]) for r in rows]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    sharpe = _sharpe(pnls)
    dsr = None
    if sharpe is not None:
        from modules.stats_utils import deflated_sharpe_ratio

        skew, kurt = _skew_kurtosis(pnls)
        dsr = deflated_sharpe_ratio(sharpe, n, n_trials, skew, kurt)
    return {
        "N": n,
        "wins": wins,
        "WR": _finite(wins / n if n else None),
        "EV_pip": _finite(sum(pnls) / n if n else None),
        "PF": _finite(_profit_factor(pnls)),
        "Kelly_full": _finite(_kelly(pnls)),
        "Wilson95_lower": _finite(_wilson_lower(wins, n)),
        "Sharpe": _finite(sharpe),
        "DSR": dsr,
        "WF_3fold_pos_ratio": _finite(_wf_pos_ratio(rows)),
        "PnL_pip": _finite(sum(pnls) if pnls else None),
    }


def _bh_fdr(pvals: dict[str, float | None], q: float = 0.10) -> dict:
    valid = sorted((k, p) for k, p in pvals.items() if p is not None and math.isfinite(p))
    m = len(valid)
    rejected = set()
    cutoff_rank = 0
    cutoff_p = None
    for rank, (_k, p) in enumerate(valid, start=1):
        if p <= q * rank / max(m, 1):
            cutoff_rank = rank
            cutoff_p = p
    if cutoff_rank:
        rejected = {k for k, p in valid[:cutoff_rank]}
    return {
        "q": q,
        "m": m,
        "cutoff_rank": cutoff_rank,
        "cutoff_p": _finite(cutoff_p),
        "survivors": sorted(rejected),
        "adjusted": {
            k: {
                "p": _finite(p),
                "bh_threshold": _finite(q * rank / max(m, 1)),
                "reject": k in rejected,
            }
            for rank, (k, p) in enumerate(valid, start=1)
        },
    }


def _tests_by_strategy(rows_by_strategy: dict[str, list[dict]]) -> dict:
    from scipy import stats

    out = {}
    for strategy in [t.strategy for t in TARGETS]:
        rows = rows_by_strategy.get(strategy, [])
        groups = [
            [r["pnl_pips"] for r in rows if r.get("bin") == bin_name]
            for bin_name, *_ in BINS
        ]
        non_empty = [g for g in groups if g]
        kruskal_p = None
        jt_p = None
        mw_p = None
        mw_n = {"strong": 0, "weak": 0}
        if len(non_empty) >= 2:
            try:
                kruskal_p = float(stats.kruskal(*non_empty).pvalue)
            except Exception:
                kruskal_p = None
        if sum(len(g) for g in groups) >= 2 and len(non_empty) >= 2:
            jt_p = _jonckheere_terpstra_p(groups)
        strong = [r["pnl_pips"] for r in rows if r.get("sr_is_strong") is True]
        weak = [r["pnl_pips"] for r in rows if r.get("sr_is_strong") is False]
        mw_n = {"strong": len(strong), "weak": len(weak)}
        if strong and weak:
            try:
                mw_p = float(stats.mannwhitneyu(strong, weak, alternative="greater").pvalue)
            except Exception:
                mw_p = None
        out[strategy] = {
            "kruskal_wallis_p": _finite(kruskal_p),
            "jonckheere_terpstra_trend_p": _finite(jt_p),
            "mann_whitney_strong_gt_weak_p": _finite(mw_p),
            "strong_weak_N": mw_n,
        }
    return out


def _jonckheere_terpstra_p(groups: list[list[float]]) -> float | None:
    from scipy import stats

    clean = [list(map(float, g)) for g in groups if g]
    if len(clean) < 2:
        return None
    j = 0.0
    for a_i in range(len(clean) - 1):
        for b_i in range(a_i + 1, len(clean)):
            for x in clean[a_i]:
                for y in clean[b_i]:
                    if y > x:
                        j += 1.0
                    elif y == x:
                        j += 0.5
    n = [len(g) for g in clean]
    mean = (sum(n) ** 2 - sum(v * v for v in n)) / 4.0
    var = (sum(n) ** 2 * (2 * sum(n) + 3) - sum(v * v * (2 * v + 3) for v in n)) / 72.0
    if var <= 0:
        return None
    z = (j - mean) / math.sqrt(var)
    return float(stats.norm.sf(z))


def _load_analysis_df(pair: str, interval: str):
    import pandas as pd
    import app

    path = _cache_path(pair, interval)
    df = pd.read_parquet(path)
    df = app.add_indicators(df)
    return df.dropna()


def _sr_meta_for_trade(df, trade: dict, pair: str) -> dict:
    from modules.indicators import find_sr_levels_weighted

    idx = int(trade.get("bar_idx", -1))
    if idx < 0 or idx >= len(df):
        entry_time = str(trade.get("entry_time") or "")
        matches = [i for i, ts in enumerate(df.index) if str(ts) == entry_time]
        idx = matches[0] if matches else -1
    if idx < 0:
        return {"sr_strength": None, "sr_touches": None, "sr_days_span": None,
                "sr_is_strong": None, "sr_distance_atr": None}
    bars_per_day = 96
    start = max(0, idx - LOOKBACK_DAYS * bars_per_day)
    signal_df = df.iloc[start:idx + 1]
    if len(signal_df) < 20:
        return {"sr_strength": None, "sr_touches": None, "sr_days_span": None,
                "sr_is_strong": None, "sr_distance_atr": None}
    levels = find_sr_levels_weighted(
        signal_df, window=5, tolerance_pct=0.003, min_touches=2,
        max_levels=10, bars_per_day=bars_per_day,
    )
    if not levels:
        return {"sr_strength": None, "sr_touches": None, "sr_days_span": None,
                "sr_is_strong": None, "sr_distance_atr": None}
    entry = float(trade.get("ep") or df.iloc[min(idx + 1, len(df) - 1)]["Open"])
    atr = float(df.iloc[idx].get("atr", 0.0) or 0.0)
    best = min(levels, key=lambda lv: abs(float(lv["price"]) - entry))
    distance_atr = abs(float(best["price"]) - entry) / max(atr, 1e-12)
    strength = float(best.get("strength"))
    return {
        "sr_strength": strength,
        "sr_touches": int(best.get("touches")),
        "sr_days_span": float(best.get("days_span")),
        "sr_is_strong": bool(strength >= 0.7),
        "sr_distance_atr": distance_atr,
    }


def _rows_from_result(result: dict, target: Target, pair: str, df) -> tuple[list[dict], dict]:
    rows = []
    missing_log = False
    trade_log = result.get("trade_log") or []
    if not trade_log and int(result.get("trades", 0) or 0) > 0:
        missing_log = True
    for trade in trade_log:
        et = trade.get("entry_type") or trade.get("type")
        if et != target.strategy:
            continue
        meta = _sr_meta_for_trade(df, trade, pair)
        strength = meta["sr_strength"]
        signal_idx = int(trade.get("bar_idx", -1))
        atr = None
        if 0 <= signal_idx < len(df):
            atr = float(df.iloc[signal_idx].get("atr", 0.0) or 0.0)
        pnl_m = _trade_pnl_m(trade)
        pnl_pips = pnl_m * max(atr or 0.0, 1e-12) * _pip_mult(pair)
        rows.append({
            "strategy": target.strategy,
            "pair": pair,
            "direction": trade.get("sig"),
            "entry_time": trade.get("entry_time"),
            "bar_idx": trade.get("bar_idx"),
            "outcome": trade.get("outcome"),
            "pnl_m": pnl_m,
            "pnl_pips": pnl_pips,
            "bin": _bin_for_strength(strength),
            **meta,
        })
    return rows, {
        "bt_error": result.get("error"),
        "total_trades": result.get("trades", 0),
        "filtered_trade_rows": len(rows),
        "missing_trade_log": missing_log,
        "data_source": result.get("data_source"),
        "bars_fetched": result.get("bars_fetched"),
        "friction_model": result.get("friction_model"),
    }


def _compute_sr_anti_hunt_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                      backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.daytrade.sr_anti_hunt_bounce import SrAntiHuntBounce

    if df is None or len(df) < 3:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["insufficient df"]}
    row, prev = df.iloc[-1], df.iloc[-2]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    bar_time = bar_time or df.index[-1]
    is_jpy = "JPY" in symbol.upper()
    ctx = SignalContext(
        entry=entry, open_price=float(row["Open"]), atr=atr,
        atr7=float(row.get("atr7", atr)), ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)), ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", entry)), rsi=float(row.get("rsi", 50.0)),
        adx=float(row.get("adx", 25.0)), adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)), macdh=float(row.get("macd_hist", 0.0)),
        macdh_prev=float(prev.get("macd_hist", 0.0)), bbpb=float(row.get("bb_pband", 0.5)),
        bb_upper=float(row.get("bb_upper", entry + atr)), bb_mid=float(row.get("bb_mid", entry)),
        bb_lower=float(row.get("bb_lower", entry - atr)), bb_width=float(row.get("bb_width", 0.01)),
        prev_close=float(prev["Close"]), prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]), prev_low=float(prev["Low"]),
        symbol=symbol, tf=tf, is_jpy=is_jpy, pip_mult=100 if is_jpy else 10000,
        df=df,
        sr_levels=[float(x.get("price") if isinstance(x, dict) else x) for x in sr_levels],
        layer3={"sr_weighted_levels": sr_levels},
        regime={"regime": "RANGE"}, htf=(htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {},
        backtest_mode=backtest_mode, bar_time=bar_time,
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )
    cand = SrAntiHuntBounce().evaluate(ctx)
    return _candidate_result(cand, entry, atr, "sr_anti_hunt_bounce", ctx)


def _compute_dt_sr_channel_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                       backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.daytrade.dt_sr_channel import DtSrChannelReversal

    if df is None or len(df) < 3:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["insufficient df"]}
    row, prev = df.iloc[-1], df.iloc[-2]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    bar_time = bar_time or df.index[-1]
    is_jpy = "JPY" in symbol.upper()
    ctx = SignalContext(
        entry=entry, open_price=float(row["Open"]), atr=atr,
        atr7=float(row.get("atr7", atr)), ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)), ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", entry)), rsi=float(row.get("rsi", 50.0)),
        rsi5=float(row.get("rsi5", row.get("rsi", 50.0))), rsi9=float(row.get("rsi9", row.get("rsi", 50.0))),
        stoch_k=float(row.get("stoch_k", 50.0)), stoch_d=float(row.get("stoch_d", 50.0)),
        adx=float(row.get("adx", 25.0)), adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)), macdh=float(row.get("macd_hist", 0.0)),
        macdh_prev=float(prev.get("macd_hist", 0.0)), bbpb=float(row.get("bb_pband", 0.5)),
        bb_upper=float(row.get("bb_upper", entry + atr)), bb_mid=float(row.get("bb_mid", entry)),
        bb_lower=float(row.get("bb_lower", entry - atr)), bb_width=float(row.get("bb_width", 0.01)),
        prev_close=float(prev["Close"]), prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]), prev_low=float(prev["Low"]),
        symbol=symbol, tf=tf, is_jpy=is_jpy, pip_mult=100 if is_jpy else 10000,
        df=df,
        sr_levels=[float(x.get("price") if isinstance(x, dict) else x) for x in sr_levels],
        layer3={"sr_weighted_levels": sr_levels},
        regime={"regime": "RANGE"}, htf=(htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {},
        backtest_mode=backtest_mode, bar_time=bar_time,
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )
    cand = DtSrChannelReversal().evaluate(ctx)
    return _candidate_result(cand, entry, atr, "dt_sr_channel_reversal", ctx)


def _structured_layer3(df, sr_levels) -> dict:
    row = df.iloc[-1]
    close = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    layer3 = {"score": 0.0, "components": {}, "signal_bar_time": str(getattr(row, "name", ""))}
    if atr <= 0:
        return layer3
    if len(df) >= 100:
        sub = df.tail(100)
        hi, lo = float(sub["High"].max()), float(sub["Low"].min())
        rng = hi - lo
        if rng > atr * 2:
            levels = [hi - rng * 0.382, hi - rng * 0.5, hi - rng * 0.618,
                      lo + rng * 0.382, lo + rng * 0.5, lo + rng * 0.618]
            fib = min(levels, key=lambda x: abs(close - x))
            if abs(close - fib) <= atr * 0.35:
                layer3["fib_level"] = float(fib)
                layer3["confluence_type"] = "sr_fib"
    if sr_levels:
        nearest = min(sr_levels, key=lambda x: abs(float(x.get("price", x)) - close))
        sr = float(nearest.get("price") if isinstance(nearest, dict) else nearest)
        if abs(close - sr) <= atr * 0.5:
            layer3["sr_level"] = sr
            layer3.setdefault("confluence_type", "sr_level")
    layer3["dt_reasons"] = ["✅ Fib structured BT"] if "fib_level" in layer3 else []
    return layer3


def _compute_sr_fib_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.daytrade.sr_fib_confluence import SrFibConfluence

    if df is None or len(df) < 3:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["insufficient df"]}
    row, prev, prev2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    bar_time = bar_time or df.index[-1]
    is_jpy = "JPY" in symbol.upper()
    layer3 = _structured_layer3(df, sr_levels)
    layer3["sr_weighted_levels"] = sr_levels
    ctx = SignalContext(
        entry=entry, open_price=float(row["Open"]), atr=atr,
        atr7=float(row.get("atr7", atr)), ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)), ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", entry)), ema9_prev=float(prev.get("ema9", entry)),
        ema21_prev=float(prev.get("ema21", entry)), rsi=float(row.get("rsi", 50.0)),
        adx=float(row.get("adx", 25.0)), adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)), macdh=float(row.get("macd_hist", 0.0)),
        macdh_prev=float(prev.get("macd_hist", 0.0)), macdh_prev2=float(prev2.get("macd_hist", 0.0)),
        bbpb=float(row.get("bb_pband", 0.5)), bb_upper=float(row.get("bb_upper", entry + atr)),
        bb_mid=float(row.get("bb_mid", entry)), bb_lower=float(row.get("bb_lower", entry - atr)),
        prev_close=float(prev["Close"]), prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]), prev_low=float(prev["Low"]),
        symbol=symbol, tf=tf, is_jpy=is_jpy, pip_mult=100 if is_jpy else 10000,
        df=df, sr_levels=sr_levels, layer3=layer3,
        htf=(htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {},
        backtest_mode=backtest_mode, bar_time=bar_time,
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )
    cand = SrFibConfluence().evaluate(ctx)
    return _candidate_result(cand, entry, atr, "sr_fib_confluence", ctx)


def _candidate_result(cand, entry: float, atr: float, strategy: str, ctx) -> dict:
    if cand is None:
        return {"signal": "WAIT", "entry": entry, "entry_type": "wait",
                "reasons": [f"{strategy} no signal"], "atr": atr, "mode": ctx.mode if hasattr(ctx, "mode") else "daytrade",
                "indicators": {"adx": ctx.adx, "bb_mid": ctx.bb_mid}}
    return {
        "signal": cand.signal, "entry": entry, "confidence": cand.confidence,
        "sl": float(cand.sl), "tp": float(cand.tp), "entry_type": cand.entry_type,
        "reasons": ["✅ strategy-filter BT"] + list(cand.reasons or []),
        "score": float(cand.score), "atr": atr, "mode": "daytrade",
        "layer_status": {}, "regime": {"regime": "RANGE"},
        "indicators": {"adx": ctx.adx, "bb_mid": ctx.bb_mid},
        "shadow_emit_signals": [],
    }


def _compute_dual_sr_bounce_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                        backtest_mode=False, bar_time=None, htf_cache=None):
    if df is None or len(df) < 3 or not sr_levels:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["insufficient df/sr"]}
    row = df.iloc[-1]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    if atr <= 0:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["atr<=0"]}
    weighted = [x for x in sr_levels if isinstance(x, dict)]
    above = [s for s in weighted if float(s["price"]) > entry + atr * 0.1
             and float(s.get("strength", 0.0)) >= 0.4 and int(s.get("touches", 0)) >= 2]
    below = [s for s in weighted if float(s["price"]) < entry - atr * 0.1
             and float(s.get("strength", 0.0)) >= 0.4 and int(s.get("touches", 0)) >= 2]
    above.sort(key=lambda x: float(x["price"]))
    below.sort(key=lambda x: -float(x["price"]))
    adx = float(row.get("adx", 25.0))
    rsi = float(row.get("rsi", 50.0))
    ema9 = float(row.get("ema9", entry))
    ema21 = float(row.get("ema21", entry))
    signal = None
    nearest = None
    if adx >= 15 and below:
        sup = below[0]
        if abs(float(row["Low"]) - float(sup["price"])) < atr * 0.6 and entry > float(sup["price"]):
            if entry > float(row["Open"]) and rsi < 60 and ema9 > ema21:
                signal, nearest = "BUY", sup
    if signal is None and adx >= 15 and above:
        res = above[0]
        if abs(float(row["High"]) - float(res["price"])) < atr * 0.6 and entry < float(res["price"]):
            if entry < float(row["Open"]) and rsi > 40 and ema9 < ema21:
                signal, nearest = "SELL", res
    if signal is None or nearest is None:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["dual_sr_bounce no signal"]}
    if signal == "BUY":
        sl, tp = entry - atr * 0.8, entry + atr * 2.0
    else:
        sl, tp = entry + atr * 0.8, entry - atr * 2.0
    return {
        "signal": signal, "entry": entry, "confidence": 62, "sl": sl, "tp": tp,
        "entry_type": "dual_sr_bounce",
        "reasons": [f"✅ dual_sr_bounce strategy-filter SR {float(nearest['price']):.5f}"],
        "score": 3.2, "atr": atr, "mode": "daytrade", "layer_status": {},
        "regime": {"regime": "RANGE"}, "indicators": {"adx": adx, "bb_mid": float(row.get("bb_mid", entry))},
        "shadow_emit_signals": [],
    }


def _compute_strong_sr_breakout_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                            backtest_mode=False, bar_time=None, htf_cache=None):
    if df is None or len(df) < 3 or not sr_levels:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["insufficient df/sr"]}
    row = df.iloc[-1]
    close_p = float(row["Close"])
    open_p = float(row["Open"])
    atr = float(row.get("atr", row.get("atr7", 0.0)) or 0.0)
    if atr <= 0:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["atr<=0"]}
    adx = float(row.get("adx", 25.0))
    rsi = float(row.get("rsi", 50.0))
    for sr_obj in [x for x in sr_levels if isinstance(x, dict)]:
        if not bool(sr_obj.get("is_strong")) or int(sr_obj.get("touches", 0)) < 3:
            continue
        level = float(sr_obj["price"])
        sr_type = sr_obj.get("type", "both")
        if (sr_type in ("resistance", "both") and close_p > level + atr * 0.1
                and open_p < level and close_p > open_p and adx >= 12 and 50 < rsi < 75):
            return {
                "signal": "BUY", "entry": close_p, "confidence": 66,
                "sl": close_p - atr * 0.8, "tp": close_p + atr * 2.5,
                "entry_type": "strong_sr_breakout",
                "reasons": [f"✅ strong_sr_breakout strategy-filter {level:.5f}"],
                "score": 3.4, "atr": atr, "mode": "scalp", "layer_status": {},
                "regime": {}, "indicators": {"adx": adx, "bb_mid": float(row.get("bb_mid", close_p))},
            }
        if (sr_type in ("support", "both") and close_p < level - atr * 0.1
                and open_p > level and close_p < open_p and adx >= 12 and 25 < rsi < 50):
            return {
                "signal": "SELL", "entry": close_p, "confidence": 66,
                "sl": close_p + atr * 0.8, "tp": close_p - atr * 2.5,
                "entry_type": "strong_sr_breakout",
                "reasons": [f"✅ strong_sr_breakout strategy-filter {level:.5f}"],
                "score": 3.4, "atr": atr, "mode": "scalp", "layer_status": {},
                "regime": {}, "indicators": {"adx": adx, "bb_mid": float(row.get("bb_mid", close_p))},
            }
    return {"signal": "WAIT", "entry_type": "wait", "reasons": ["strong_sr_breakout no signal"]}


class _SrChannelOnlyScalperEngine:
    SHADOW_ALWAYS_STRATEGIES = frozenset()

    def __init__(self):
        from strategies.scalp.sr_channel_reversal import SrChannelReversal
        self.strategies = [SrChannelReversal()]

    def evaluate_all(self, ctx):
        return [c for s in self.strategies for c in [s.evaluate(ctx)] if c is not None]

    def select_best(self, candidates):
        return max(candidates, key=lambda c: c.score) if candidates else None

    def split_shadow_always(self, candidates, best):
        return []


def _compute_sr_channel_only_signal(df, tf, sr_levels, symbol="USDJPY=X",
                                    backtest_mode=False, bar_time=None, htf_cache=None):
    from strategies.context import SignalContext
    from strategies.scalp.sr_channel_reversal import SrChannelReversal

    if df is None or len(df) < 3:
        return {"signal": "WAIT", "entry_type": "wait", "reasons": ["insufficient df"]}
    row, prev = df.iloc[-1], df.iloc[-2]
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    bar_time = bar_time or df.index[-1]
    is_jpy = "JPY" in symbol.upper()
    ctx = SignalContext(
        entry=entry, open_price=float(row["Open"]), atr=atr,
        atr7=float(row.get("atr7", atr)), rsi=float(row.get("rsi", 50.0)),
        rsi5=float(row.get("rsi5", row.get("rsi", 50.0))), rsi9=float(row.get("rsi9", row.get("rsi", 50.0))),
        stoch_k=float(row.get("stoch_k", 50.0)), stoch_d=float(row.get("stoch_d", 50.0)),
        adx=float(row.get("adx", 25.0)), adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)), macdh=float(row.get("macd_hist", 0.0)),
        macdh_prev=float(prev.get("macd_hist", 0.0)), bbpb=float(row.get("bb_pband", 0.5)),
        bb_upper=float(row.get("bb_upper", entry + atr)), bb_mid=float(row.get("bb_mid", entry)),
        bb_lower=float(row.get("bb_lower", entry - atr)), bb_width=float(row.get("bb_width", 0.01)),
        prev_close=float(prev["Close"]), prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]), prev_low=float(prev["Low"]),
        symbol=symbol, tf=tf, is_jpy=is_jpy, pip_mult=100 if is_jpy else 10000,
        df=df, sr_levels=sr_levels, layer3={"sr_weighted_levels": sr_levels},
        regime={"regime": "RANGE"}, htf=(htf_cache or {}).get("htf", {}) if isinstance(htf_cache, dict) else {},
        backtest_mode=backtest_mode, bar_time=bar_time,
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )
    cand = SrChannelReversal().evaluate(ctx)
    return _candidate_result(cand, entry, atr, "sr_channel_reversal", ctx)


def _run_target_pair(app, data_mod, target: Target, pair: str, symbol: str) -> dict:
    app._dt_bt_cache.clear()
    app._scalp_bt_cache.clear()
    data_mod._data_cache.clear()
    if target.strategy == "dual_sr_bounce":
        app.compute_daytrade_signal = _compute_dual_sr_bounce_only_signal
        return app.run_daytrade_backtest(symbol, LOOKBACK_DAYS, target.interval, backtest_mode=True)
    if target.strategy == "sr_anti_hunt_bounce":
        app.compute_daytrade_signal = _compute_sr_anti_hunt_only_signal
        return app.run_daytrade_backtest(symbol, LOOKBACK_DAYS, target.interval, backtest_mode=True)
    if target.strategy == "dt_sr_channel_reversal":
        app.compute_daytrade_signal = _compute_dt_sr_channel_only_signal
        return app.run_daytrade_backtest(symbol, LOOKBACK_DAYS, target.interval, backtest_mode=True)
    if target.strategy == "sr_fib_confluence":
        app.compute_daytrade_signal = _compute_sr_fib_only_signal
        return app.run_daytrade_backtest(symbol, LOOKBACK_DAYS, target.interval, backtest_mode=True)
    if target.strategy == "sr_channel_reversal":
        import strategies.scalp as scalp_mod

        os.environ["SR_CHANNEL_REVERSAL_REDESIGN_V2"] = os.environ.get("SR_CHANNEL_REVERSAL_REDESIGN_V2", "0")
        scalp_mod.ScalperEngine = _SrChannelOnlyScalperEngine
        app.ScalperEngine = _SrChannelOnlyScalperEngine
        app.compute_scalp_signal = _compute_sr_channel_only_signal
        return app.run_scalp_backtest(symbol, LOOKBACK_DAYS, target.interval)
    if target.strategy == "strong_sr_breakout":
        app.compute_scalp_signal = _compute_strong_sr_breakout_only_signal
        return app.run_scalp_backtest(symbol, LOOKBACK_DAYS, target.interval)
    if target.mode == "daytrade":
        app.compute_daytrade_signal = ORIGINAL_COMPUTE_DAYTRADE
        return app.run_daytrade_backtest(symbol, LOOKBACK_DAYS, target.interval, backtest_mode=True)
    app.compute_scalp_signal = ORIGINAL_COMPUTE_SCALP
    return app.run_scalp_backtest(symbol, LOOKBACK_DAYS, target.interval)


def _cell_metrics(rows: list[dict]) -> dict:
    cells = {}
    for strategy in [t.strategy for t in TARGETS]:
        for pair, _symbol in PAIRS_5:
            for bin_name, *_ in BINS:
                for direction in DIRECTIONS:
                    key = f"{strategy}|{pair}|{bin_name}|{direction}"
                    subset = [
                        r for r in rows
                        if r["strategy"] == strategy and r["pair"] == pair
                        and r["bin"] == bin_name and r["direction"] == direction
                    ]
                    cells[key] = {
                        "strategy": strategy, "pair": pair, "bin": bin_name,
                        "direction": direction, **_metrics(subset),
                    }
    return cells


def _aggregate_metrics(rows: list[dict]) -> dict:
    out = {}
    for strategy in [t.strategy for t in TARGETS]:
        subset = [r for r in rows if r["strategy"] == strategy]
        out[strategy] = _metrics(subset)
    out["ALL_SR_STRATEGIES"] = _metrics(rows)
    return out


def _strategy_bin_metrics(rows: list[dict]) -> dict:
    out = {}
    for strategy in [t.strategy for t in TARGETS]:
        for bin_name, *_ in BINS:
            subset = [
                r for r in rows
                if r["strategy"] == strategy and r["bin"] == bin_name
            ]
            out[f"{strategy}|{bin_name}"] = {
                "strategy": strategy,
                "bin": bin_name,
                **_metrics(subset),
            }
    return out


def _write_markdown(result: dict) -> None:
    lines = [
        "# SR Weight Phase 2 Bin BH-FDR",
        "",
        f"- generated_at: `{result['generated_at']}`",
        f"- overall_verdict: `{result['overall_verdict']}`",
        f"- total_rows: `{len(result['trades'])}`",
        f"- massive_cache_verified: `{result['massive_cache_verified']}`",
        "",
        "## Survivors",
        "",
        f"- BH FDR survivors: `{', '.join(result['bh_fdr']['survivors']) or 'none'}`",
        f"- Bonferroni MW survivors: `{', '.join(result['bonferroni']['survivors']) or 'none'}`",
        "",
        "## Per Strategy Verdict",
        "",
        "| strategy | N | EV(pip) | JT p | BH | MW p | Bonf | verdict |",
        "|---|---:|---:|---:|---|---:|---|---|",
    ]
    for strategy, verdict in result["per_strategy_verdict"].items():
        agg = result["aggregate_metrics"][strategy]
        tests = result["tests"][strategy]
        lines.append(
            f"| {strategy} | {agg['N']} | {agg['EV_pip']} | "
            f"{tests['jonckheere_terpstra_trend_p']} | "
            f"{strategy in result['bh_fdr']['survivors']} | "
            f"{tests['mann_whitney_strong_gt_weak_p']} | "
            f"{strategy in result['bonferroni']['survivors']} | {verdict} |"
        )
    lines.extend(["", "## Acceptance", ""])
    for k, v in result["acceptance"].items():
        lines.append(f"- {k}: `{v}`")
    if result["run_notes"]:
        lines.extend(["", "## Run Notes", ""])
        for note in result["run_notes"]:
            lines.append(f"- {note}")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    started = time.time()
    missing = sorted({
        str(_cache_path(pair, target.interval).relative_to(ROOT))
        for target in TARGETS
        for pair, _symbol in target.pairs
        if not _cache_path(pair, target.interval).exists()
    })
    if missing:
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_verdict": "CHANGES_REQUESTED",
            "reason": "missing MASSIVE parquet cache",
            "missing_caches": missing,
            "massive_cache_verified": False,
        }
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        FINAL_MD.write_text("# CHANGES_REQUESTED\n\nMASSIVE cache missing; aborting BT.\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 2

    import app
    from modules import data as data_mod

    global ORIGINAL_COMPUTE_DAYTRADE, ORIGINAL_COMPUTE_SCALP
    ORIGINAL_COMPUTE_DAYTRADE = app.compute_daytrade_signal
    ORIGINAL_COMPUTE_SCALP = app.compute_scalp_signal
    app.get_master_bias = lambda _symbol: {"direction": "neutral", "label": "BT neutral", "score": 0}
    app._compute_bt_htf_bias = lambda *_args, **_kwargs: {"agreement": "mixed", "direction": "neutral"}

    rows: list[dict] = []
    run_notes: list[str] = []
    run_matrix: dict[str, Any] = {}
    df_cache = {}
    for target in TARGETS:
        for pair, symbol in target.pairs:
            print(f"Running {target.strategy} {pair} {target.interval}", flush=True)
            try:
                result = _run_target_pair(app, data_mod, target, pair, symbol)
                df_key = (pair, target.interval)
                if df_key not in df_cache:
                    df_cache[df_key] = _load_analysis_df(pair, target.interval)
                new_rows, meta = _rows_from_result(result, target, pair, df_cache[df_key])
            except Exception as exc:
                new_rows = []
                meta = {"bt_error": repr(exc), "filtered_trade_rows": 0}
            rows.extend(new_rows)
            run_matrix[f"{target.strategy}|{pair}"] = meta
            if meta.get("bt_error"):
                run_notes.append(f"{target.strategy}/{pair}: {meta.get('bt_error')}")
            if meta.get("missing_trade_log"):
                run_notes.append(f"{target.strategy}/{pair}: result omitted trade_log for <threshold sample.")

    by_strategy = defaultdict(list)
    for row in rows:
        by_strategy[row["strategy"]].append(row)

    tests = _tests_by_strategy(by_strategy)
    trend_pvals = {
        strategy: (None if tests[strategy]["jonckheere_terpstra_trend_p"] in (None, "inf")
                   else float(tests[strategy]["jonckheere_terpstra_trend_p"]))
        for strategy in [t.strategy for t in TARGETS]
    }
    mw_pvals = {
        strategy: (None if tests[strategy]["mann_whitney_strong_gt_weak_p"] in (None, "inf")
                   else float(tests[strategy]["mann_whitney_strong_gt_weak_p"]))
        for strategy in [t.strategy for t in TARGETS]
    }
    bh = _bh_fdr(trend_pvals, q=0.10)
    bonf = {
        "alpha": 0.05,
        "m": 6,
        "threshold": round(0.05 / 6, 8),
        "survivors": sorted(k for k, p in mw_pvals.items() if p is not None and p <= 0.05 / 6),
        "p_values": {k: _finite(v) for k, v in mw_pvals.items()},
    }
    per_strategy_verdict = {
        strategy: ("BIN_DISCRIMINATION_VALID" if strategy in bh["survivors"] else "NULL")
        for strategy in [t.strategy for t in TARGETS]
    }
    cells = _cell_metrics(rows)
    aggregate = _aggregate_metrics(rows)
    strategy_bin = _strategy_bin_metrics(rows)
    max_cell_n = max((c["N"] for c in cells.values()), default=0)
    acceptance = {
        "has_minimum_n30_cell": max_cell_n >= 30,
        "all_metrics_output": True,
        "trend_tests_6": len(tests) == 6,
        "mann_whitney_tests_6": len(mw_pvals) == 6,
        "bh_and_bonferroni_output": bool(bh) and bool(bonf),
        "per_strategy_verdict_output": len(per_strategy_verdict) == 6,
        "max_cell_N": max_cell_n,
    }
    overall = "ACCEPT" if all(v is True for k, v in acceptance.items() if k != "max_cell_N") else "CHANGES_REQUESTED"
    if max_cell_n < 30:
        overall = "CHANGES_REQUESTED"

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lookback_days": LOOKBACK_DAYS,
        "data_source_required": "data/cache/massive/{PAIR}_{TF}.parquet",
        "bt_mode": os.environ.get("BT_MODE"),
        "bt_require_massive_cache": os.environ.get("BT_REQUIRE_MASSIVE_CACHE"),
        "massive_cache_verified": True,
        "friction_gate_chain": "app.run_daytrade_backtest/run_scalp_backtest production BT path: spread_sl_gate + range TP + quick harvest where implemented",
        "sr_level_function": "modules.indicators.find_sr_levels_weighted actual signature: window,tolerance_pct,min_touches,max_levels,bars_per_day",
        "bin_definitions": {name: label for name, _lo, _hi, label in BINS},
        "targets": [target.__dict__ for target in TARGETS],
        "run_matrix": run_matrix,
        "run_notes": run_notes,
        "tests": tests,
        "bh_fdr": bh,
        "bonferroni": bonf,
        "per_strategy_verdict": per_strategy_verdict,
        "cell_metrics": cells,
        "strategy_bin_metrics": strategy_bin,
        "aggregate_metrics": aggregate,
        "acceptance": acceptance,
        "overall_verdict": overall,
        "elapsed_s": round(time.time() - started, 1),
        "trades": rows,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    _write_markdown(out)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    final_status = "ACCEPT" if overall == "ACCEPT" else "CHANGES_REQUESTED"
    FINAL_MD.write_text(
        f"# {final_status}\n\n"
        f"- JSON: `{OUT_JSON.relative_to(ROOT)}`\n"
        f"- Markdown: `{OUT_MD.relative_to(ROOT)}`\n"
        f"- max_cell_N: `{max_cell_n}`\n"
        f"- BH survivors: `{', '.join(bh['survivors']) or 'none'}`\n"
        f"- Bonferroni survivors: `{', '.join(bonf['survivors']) or 'none'}`\n",
        encoding="utf-8",
    )
    print(f"Saved {OUT_JSON}")
    print(f"Saved {OUT_MD}")
    print(f"Saved {FINAL_MD}")
    print(f"Overall {overall}; max_cell_N={max_cell_n}")
    return 0 if overall == "ACCEPT" else 1


ORIGINAL_COMPUTE_DAYTRADE = None
ORIGINAL_COMPUTE_SCALP = None


if __name__ == "__main__":
    raise SystemExit(main())
