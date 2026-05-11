#!/usr/bin/env python3
"""SR weight-gate empirical audit v2.

MASSIVE-cache-only runner for the 2026-05-11 SR weight pre-registration.
The strategy evaluate() implementations are imported and called as-is; this
script only attaches post-hoc level weight metadata to emitted signals.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
import time
import types
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
PRIMARY_HEAVY_THRESHOLD = 5.0
EXPLORATORY_THRESHOLDS = [3.0, 4.0, 6.0, 8.0]
BONFERRONI_M = 5
BONF_ALPHA = 0.01
BOOTSTRAP_RESAMPLES = 10_000
TARGETS = [
    ("USD_JPY", "USDJPY=X"),
    ("EUR_USD", "EURUSD=X"),
    ("GBP_USD", "GBPUSD=X"),
    ("EUR_JPY", "EURJPY=X"),
    ("GBP_JPY", "GBPJPY=X"),
]
STRATEGIES = [
    "sr_anti_hunt_bounce",
    "sr_break_retest",
    "sr_fib_confluence",
    "sr_liquidity_grab",
    "sr_channel_reversal",
]
RUN_STRIDES = {
    "sr_anti_hunt_bounce": 1,
    "sr_break_retest": 8,
    "sr_fib_confluence": 2,
    "sr_liquidity_grab": 1,
    "sr_channel_reversal": 2,
}


@dataclass(frozen=True)
class StrategySpec:
    name: str
    cls_path: str
    min_bars: int


STRATEGY_SPECS = {
    "sr_anti_hunt_bounce": StrategySpec(
        "sr_anti_hunt_bounce", "strategies.daytrade.sr_anti_hunt_bounce:SrAntiHuntBounce", 40
    ),
    "sr_break_retest": StrategySpec(
        "sr_break_retest", "strategies.daytrade.sr_break_retest:SrBreakRetest", 120
    ),
    "sr_fib_confluence": StrategySpec(
        "sr_fib_confluence", "strategies.daytrade.sr_fib_confluence:SrFibConfluence", 120
    ),
    "sr_liquidity_grab": StrategySpec(
        "sr_liquidity_grab", "strategies.daytrade.sr_liquidity_grab:SrLiquidityGrab", 40
    ),
    "sr_channel_reversal": StrategySpec(
        "sr_channel_reversal", "strategies.scalp.sr_channel_reversal:SrChannelReversal", 120
    ),
}


def _install_app_stub_for_channel() -> None:
    if "app" in sys.modules:
        return
    import numpy as np

    app_stub = types.ModuleType("app")

    def find_parallel_channel(df, window=5, lookback=100):
        if len(df) < window * 4:
            return None
        fd = df.tail(lookback)
        highs = fd["High"].values
        lows = fd["Low"].values
        n = len(fd)
        swing_highs = []
        swing_lows = []
        for i in range(window, n - window):
            if highs[i] == highs[i - window:i + window + 1].max():
                swing_highs.append(i)
            if lows[i] == lows[i - window:i + window + 1].min():
                swing_lows.append(i)
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return None
        hm, hb = np.polyfit(swing_highs, highs[swing_highs], 1)
        lm, lb = np.polyfit(swing_lows, lows[swing_lows], 1)
        offset = len(df) - len(fd)
        ts_arr = [int(t.timestamp()) for t in df.index]
        upper, lower, middle = [], [], []
        for j, ts in enumerate(ts_arr):
            i = j - offset
            hv = round(float(hm * i + hb), 3)
            lv = round(float(lm * i + lb), 3)
            upper.append({"time": ts, "value": hv})
            lower.append({"time": ts, "value": lv})
            middle.append({"time": ts, "value": round((hv + lv) / 2, 3)})
        return {
            "upper": upper,
            "lower": lower,
            "middle": middle,
            "trend": "up" if (hm + lm) / 2 > 0 else "down",
        }

    app_stub.find_parallel_channel = find_parallel_channel
    sys.modules["app"] = app_stub


def _import_object(path: str):
    import importlib

    module_name, obj_name = path.split(":")
    return getattr(importlib.import_module(module_name), obj_name)


def pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def load_data(symbol: str, tf: str):
    import pandas as pd
    from modules.indicators import add_indicators

    pair = symbol.replace("=X", "")
    if "_" not in pair:
        pair = pair[:3] + "_" + pair[3:]
    path = ROOT / "data" / "cache" / "massive" / f"{pair}_{tf}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"MASSIVE parquet not found: {path.relative_to(ROOT)}")
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{path} must have DatetimeIndex")
    df = df.sort_index()
    end = df.index.max()
    df = df.loc[df.index >= end - pd.Timedelta(days=LOOKBACK_DAYS)].copy()
    if tf == "15m":
        df = add_indicators(df).dropna()
    return df


def resample_htf(df_1h, freq: str):
    ohlc = df_1h.resample(freq).agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    )
    return ohlc.dropna(subset=["Open", "High", "Low", "Close"])


def _atr_series(df, window: int = 14):
    import pandas as pd

    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()


def _touch_mask(df, level: float, tolerance: float):
    close_hit = (df["Close"].astype(float) - level).abs() <= tolerance
    cross_hit = (df["Low"].astype(float) <= level) & (df["High"].astype(float) >= level)
    band_hit = (df["Low"].astype(float) <= level + tolerance) & (
        df["High"].astype(float) >= level - tolerance
    )
    return (close_hit | cross_hit | band_hit).to_numpy()


def _touch_events(mask, min_gap_bars: int = 5) -> list[tuple[int, int]]:
    raw: list[tuple[int, int]] = []
    start = None
    for i, touched in enumerate(mask):
        if touched and start is None:
            start = i
        elif not touched and start is not None:
            raw.append((start, i - 1))
            start = None
    if start is not None:
        raw.append((start, len(mask) - 1))
    if not raw:
        return []
    merged = [raw[0]]
    for s, e in raw[1:]:
        ps, pe = merged[-1]
        if s - pe - 1 < min_gap_bars:
            merged[-1] = (ps, e)
        else:
            merged.append((s, e))
    return merged


def count_distinct_touches(df, level, tolerance, min_gap_bars: int = 5):
    return len(_touch_events(_touch_mask(df, float(level), float(tolerance)), min_gap_bars))


def median_rejection_size(df, level, tolerance, atr_series):
    import numpy as np

    mask = _touch_mask(df, float(level), float(tolerance))
    events = _touch_events(mask, min_gap_bars=5)
    values = []
    highs = df["High"].astype(float).to_numpy()
    lows = df["Low"].astype(float).to_numpy()
    opens = df["Open"].astype(float).to_numpy()
    closes = df["Close"].astype(float).to_numpy()
    atr = atr_series.astype(float).to_numpy()
    for s, e in events:
        local = []
        for i in range(s, e + 1):
            body_hi = max(opens[i], closes[i])
            body_lo = min(opens[i], closes[i])
            upper = max(0.0, highs[i] - max(float(level), body_hi))
            lower = max(0.0, min(float(level), body_lo) - lows[i])
            wick = max(upper, lower, highs[i] - lows[i] if lows[i] <= level <= highs[i] else 0.0)
            denom = max(float(atr[i]), 1e-12)
            local.append(wick / denom)
        if local:
            values.append(max(local))
    if not values:
        return 0.0
    return float(np.clip(np.median(values), 0.0, 2.0))


def round_score(price: float, pip: float) -> float:
    pip_units = float(price) / pip
    dist_100 = min(pip_units % 100, 100 - (pip_units % 100))
    dist_50 = min(pip_units % 50, 50 - (pip_units % 50))
    score = max(0.0, 1.0 - dist_50 / 25.0)
    if dist_100 < 5:
        score = min(1.0, score + 0.2)
    return float(score)


def composite_weight(level_meta: dict) -> float:
    return (
        1.0 * level_meta["own_touch"]
        + 3.0 * level_meta["d1_touch"]
        + 5.0 * level_meta["w1_touch"]
        + 2.0 * level_meta["round_score"]
        + 1.5 * level_meta["magnitude_score"]
    )


def _srlevel_price(level: Any) -> float:
    if isinstance(level, dict):
        return float(level["price"])
    return float(getattr(level, "price"))


def _srlevel_touch(level: Any) -> int:
    if isinstance(level, dict):
        return int(level.get("touch_count", level.get("touches", 0)) or 0)
    return int(getattr(level, "touch_count", 0) or 0)


def detect_sr_levels_with_weight(
    df,
    htf_df_d1,
    htf_df_w1,
    tolerance_pip: float,
    min_touches: int,
    symbol: str = "USDJPY=X",
) -> list[dict]:
    from modules.sr_detector import detect_sr_levels

    pip = pip_size(symbol)
    tolerance = tolerance_pip * pip
    atr_own = _atr_series(df)
    atr_d1 = _atr_series(htf_df_d1) if len(htf_df_d1) else atr_own
    atr_w1 = _atr_series(htf_df_w1) if len(htf_df_w1) else atr_own
    d1_tol_pip = max(float(atr_d1.median()) * 0.3 / pip, tolerance_pip)
    w1_tol_pip = max(float(atr_w1.median()) * 0.3 / pip, tolerance_pip)
    d1_match = max(float(atr_d1.median()) * 0.5, tolerance)

    own = detect_sr_levels(
        df,
        symbol,
        bandwidth_pips=max(5.0, tolerance_pip * 1.5),
        touch_tolerance_pips=tolerance_pip,
        min_touches=min_touches,
        max_levels=30,
    )
    d1 = detect_sr_levels(
        htf_df_d1,
        symbol,
        bandwidth_pips=max(5.0, d1_tol_pip * 1.5),
        touch_tolerance_pips=d1_tol_pip,
        min_touches=2,
        max_levels=20,
    ) if len(htf_df_d1) >= 5 else []
    w1 = detect_sr_levels(
        htf_df_w1,
        symbol,
        bandwidth_pips=max(5.0, w1_tol_pip * 1.5),
        touch_tolerance_pips=w1_tol_pip,
        min_touches=2,
        max_levels=20,
    ) if len(htf_df_w1) >= 5 else []

    levels = []
    for lv in own:
        price = _srlevel_price(lv)
        own_touch = count_distinct_touches(df, price, tolerance, min_gap_bars=5)
        if own_touch < min_touches:
            continue
        d1_hits = [x for x in d1 if abs(_srlevel_price(x) - price) <= d1_match]
        w1_hits = [x for x in w1 if abs(_srlevel_price(x) - price) <= d1_match]
        d1_touch = (
            count_distinct_touches(htf_df_d1, price, d1_tol_pip * pip, min_gap_bars=2)
            if d1_hits else 0
        )
        w1_touch = (
            count_distinct_touches(htf_df_w1, price, w1_tol_pip * pip, min_gap_bars=1)
            if w1_hits else 0
        )
        mag_raw = median_rejection_size(df, price, tolerance, atr_own)
        meta = {
            "price": float(price),
            "touch_count": int(_srlevel_touch(lv)),
            "own_touch": int(own_touch),
            "d1_touch": int(d1_touch),
            "w1_touch": int(w1_touch),
            "round_score": round_score(price, pip),
            "magnitude_score": float(min(1.0, mag_raw)),
            "magnitude_raw": float(mag_raw),
            "distinct_touch_events": int(own_touch),
            "strength": float(getattr(lv, "obviousness", 0.0)),
            "obviousness": float(getattr(lv, "obviousness", 0.0)),
        }
        meta["composite_weight"] = float(composite_weight(meta))
        meta["touches"] = meta["own_touch"]
        meta["is_strong"] = bool(meta["composite_weight"] >= PRIMARY_HEAVY_THRESHOLD)
        levels.append(meta)
    levels.sort(key=lambda x: (-x["composite_weight"], x["price"]))
    return levels


def _structured_layer3(df, sr_levels) -> dict:
    row = df.iloc[-1]
    close = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    layer3 = {
        "score": 0.0,
        "label": "sr_weight_gate_audit_v2 structured extractor",
        "components": {},
        "sr_weighted_levels": sr_levels,
    }
    if atr <= 0:
        return layer3
    if len(df) >= 100:
        sub = df.tail(100)
        swing_high = float(sub["High"].max())
        swing_low = float(sub["Low"].min())
        swing_range = swing_high - swing_low
        if swing_range > atr * 2:
            fib_levels = [
                ("fib_38.2_bull", swing_high - swing_range * 0.382),
                ("fib_50.0_bull", swing_high - swing_range * 0.500),
                ("fib_61.8_bull", swing_high - swing_range * 0.618),
                ("fib_38.2_bear", swing_low + swing_range * 0.382),
                ("fib_50.0_bear", swing_low + swing_range * 0.500),
                ("fib_61.8_bear", swing_low + swing_range * 0.618),
            ]
            fib_name, fib_level = min(fib_levels, key=lambda x: abs(close - x[1]))
            if abs(close - fib_level) <= atr * 0.35:
                layer3["fib_level"] = float(fib_level)
                layer3["confluence_type"] = fib_name
    if sr_levels:
        nearest = min(sr_levels, key=lambda x: abs(float(x["price"]) - close))
        sr_level = float(nearest["price"])
        if abs(close - sr_level) <= atr * 0.5:
            layer3["sr_level"] = sr_level
            layer3.setdefault("confluence_type", "sr_level")
    sub = df.tail(80)
    if len(sub) >= 20:
        opens = sub["Open"].to_numpy()
        highs = sub["High"].to_numpy()
        lows = sub["Low"].to_numpy()
        closes = sub["Close"].to_numpy()
        atrs = sub["atr"].to_numpy() if "atr" in sub else None
        for i in range(len(sub) - 3, 0, -1):
            imp_i = i + 1
            imp_atr = float(atrs[imp_i]) if atrs is not None and atrs[imp_i] > 0 else atr
            imp_body = abs(float(closes[imp_i]) - float(opens[imp_i]))
            if imp_body < 1.5 * imp_atr:
                continue
            bull_ob = closes[imp_i] > opens[imp_i] and closes[i] < opens[i]
            bear_ob = closes[imp_i] < opens[imp_i] and closes[i] > opens[i]
            if not (bull_ob or bear_ob):
                continue
            zone_low = float(lows[i])
            zone_high = float(highs[i])
            if zone_low <= close <= zone_high:
                layer3["ob_zone_low"] = min(zone_low, zone_high)
                layer3["ob_zone_high"] = max(zone_low, zone_high)
                layer3["confluence_type"] = "bull_ob_retest" if bull_ob else "bear_ob_retest"
                break
    reasons = []
    if layer3.get("fib_level") is not None:
        reasons.append(f"Fib structured audit level={float(layer3['fib_level']):.5f}")
    if layer3.get("ob_zone_low") is not None and layer3.get("ob_zone_high") is not None:
        reasons.append("OB structured audit zone")
    layer3["dt_reasons"] = reasons
    return layer3


def _build_ctx(df_window, symbol: str, sr_levels: list[dict], bar_time, strategy_name: str | None = None):
    from strategies.context import SignalContext

    row = df_window.iloc[-1]
    prev = df_window.iloc[-2] if len(df_window) >= 2 else row
    prev2 = df_window.iloc[-3] if len(df_window) >= 3 else prev
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    is_jpy = "JPY" in symbol.upper()
    layer3 = _structured_layer3(df_window, sr_levels)
    ctx_sr_levels = [float(lv["price"]) for lv in sr_levels] if strategy_name == "sr_channel_reversal" else sr_levels
    return SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=float(row.get("atr7", atr)),
        ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)),
        ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", entry)),
        ema9_prev=float(prev.get("ema9", entry)),
        ema21_prev=float(prev.get("ema21", entry)),
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
        symbol=symbol,
        tf="15m",
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df_window,
        sr_levels=ctx_sr_levels,
        layer3=layer3,
        regime={"regime": "RANGE"},
        htf={"agreement": "mixed"},
        backtest_mode=True,
        bar_time=bar_time,
        hour_utc=bar_time.hour if hasattr(bar_time, "hour") else 12,
    )


def _extract_level_price(candidate, entry: float, levels: list[dict]) -> float | None:
    text = " ".join(str(x) for x in (candidate.reasons or []))
    for pattern in (r"SR=([0-9]+\.[0-9]+)", r"SR[^0-9]*([0-9]+\.[0-9]+)"):
        m = re.search(pattern, text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    if levels:
        return float(min(levels, key=lambda x: abs(float(x["price"]) - entry))["price"])
    return None


def _nearest_level_meta(
    levels: list[dict],
    price: float | None,
    entry: float,
    df_window=None,
    symbol: str = "USDJPY=X",
) -> dict:
    if not levels:
        return {
            "level_price": None, "own_touch": 0, "d1_touch": 0, "w1_touch": 0,
            "round_score": 0.0, "magnitude_score": 0.0, "composite_weight": 0.0,
            "distinct_touch": 0,
        }
    ref = entry if price is None else price
    lv = min(levels, key=lambda x: abs(float(x["price"]) - float(ref)))
    own_touch = int(lv["own_touch"])
    d1_touch = int(lv["d1_touch"])
    w1_touch = int(lv["w1_touch"])
    magnitude = float(lv["magnitude_score"])
    rscore = float(lv["round_score"])
    if df_window is not None and len(df_window) >= 20:
        local = df_window.tail(16)
        pip = pip_size(symbol)
        local_atr = _atr_series(local) if "atr" not in local.columns else local["atr"].astype(float)
        tolerance = max(float(local_atr.median()) * 0.30, 3.0 * pip)
        own_touch = count_distinct_touches(local, float(lv["price"]), tolerance, min_gap_bars=5)
        magnitude = float(min(1.0, median_rejection_size(local, float(lv["price"]), tolerance, local_atr)))
        robust_htf = d1_touch >= 10 and w1_touch >= 3 and rscore > 0.5
        d1_touch = 1 if robust_htf else 0
        w1_touch = 0
        tmp = {
            "own_touch": own_touch,
            "d1_touch": d1_touch,
            "w1_touch": w1_touch,
            "round_score": rscore,
            "magnitude_score": magnitude,
        }
        cweight = composite_weight(tmp)
    else:
        cweight = float(lv["composite_weight"])
    return {
        "level_price": float(lv["price"]),
        "own_touch": int(own_touch),
        "d1_touch": int(d1_touch),
        "w1_touch": int(w1_touch),
        "round_score": rscore,
        "magnitude_score": magnitude,
        "composite_weight": float(cweight),
        "distinct_touch": int(own_touch),
    }


def _simulate_exit(df, entry_i: int, signal: str, entry: float, sl: float, tp: float, pip: float,
                   max_hold_bars: int = 12) -> dict:
    end_i = min(len(df) - 1, entry_i + max_hold_bars)
    for j in range(entry_i + 1, end_i + 1):
        high = float(df.iloc[j]["High"])
        low = float(df.iloc[j]["Low"])
        if signal == "BUY":
            hit_sl = low <= sl
            hit_tp = high >= tp
            if hit_sl and hit_tp:
                return {"pnl_pip": (sl - entry) / pip, "win": False, "exit_reason": "sl_first_ambiguous"}
            if hit_sl:
                return {"pnl_pip": (sl - entry) / pip, "win": False, "exit_reason": "sl"}
            if hit_tp:
                return {"pnl_pip": (tp - entry) / pip, "win": True, "exit_reason": "tp"}
        else:
            hit_sl = high >= sl
            hit_tp = low <= tp
            if hit_sl and hit_tp:
                return {"pnl_pip": (entry - sl) / pip, "win": False, "exit_reason": "sl_first_ambiguous"}
            if hit_sl:
                return {"pnl_pip": (entry - sl) / pip, "win": False, "exit_reason": "sl"}
            if hit_tp:
                return {"pnl_pip": (entry - tp) / pip, "win": True, "exit_reason": "tp"}
    close = float(df.iloc[end_i]["Close"])
    pnl = (close - entry) / pip if signal == "BUY" else (entry - close) / pip
    return {"pnl_pip": pnl, "win": pnl > 0, "exit_reason": "timeout"}


def _nearest_dist_to_levels(entry: float, levels: list[dict]) -> float:
    if not levels:
        return float("inf")
    return min(abs(float(lv["price"]) - entry) for lv in levels)


def _prefilter_strategy_bar(strategy_name: str, row, levels: list[dict], symbol: str) -> bool:
    entry = float(row["Close"])
    atr = max(float(row.get("atr", 0.0) or 0.0), 1e-12)
    adx = float(row.get("adx", 25.0) or 25.0)
    sym = symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
    if strategy_name in {"sr_anti_hunt_bounce", "sr_liquidity_grab"}:
        if sym not in {"USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY"} or adx >= 30:
            return False
        mult = 0.45 if strategy_name == "sr_anti_hunt_bounce" else 0.55
        return _nearest_dist_to_levels(entry, levels) <= atr * mult
    if strategy_name == "sr_break_retest":
        return (
            sym not in {"EURUSD", "EURGBP"}
            and adx >= 20
            and _nearest_dist_to_levels(entry, levels) <= atr * 0.80
        )
    if strategy_name == "sr_fib_confluence":
        return adx >= 20
    if strategy_name == "sr_channel_reversal":
        if not levels:
            return False
        rsi5 = float(row.get("rsi5", row.get("rsi", 50.0)) or 50.0)
        stoch_k = float(row.get("stoch_k", 50.0) or 50.0)
        stoch_d = float(row.get("stoch_d", 50.0) or 50.0)
        has_buy_sr = any(0 < entry - float(lv["price"]) < atr * 0.30 for lv in levels)
        has_sell_sr = any(0 < float(lv["price"]) - entry < atr * 0.30 for lv in levels)
        return (has_buy_sr and rsi5 < 45 and stoch_k > stoch_d) or (
            has_sell_sr and rsi5 > 55 and stoch_k < stoch_d
        )
    return True


def run_strategy_bt(
    strategy_name: str,
    df,
    levels: list[dict],
    symbol: str = "USDJPY=X",
    max_signals: int | None = None,
    stride: int = 1,
):
    import pandas as pd

    if strategy_name == "sr_channel_reversal":
        _install_app_stub_for_channel()
    spec = STRATEGY_SPECS[strategy_name]
    klass = _import_object(spec.cls_path)
    if hasattr(klass, "reset_dedup_state"):
        klass.reset_dedup_state()
    strategy = klass()
    rows = []
    pip = pip_size(symbol)
    for i in range(spec.min_bars, len(df) - 13, max(1, int(stride))):
        if not _prefilter_strategy_bar(strategy_name, df.iloc[i], levels, symbol):
            continue
        df_window = df.iloc[: i + 1]
        ctx = _build_ctx(df_window, symbol, levels, df.index[i], strategy_name=strategy_name)
        try:
            cand = strategy.evaluate(ctx)
        except Exception:
            continue
        if cand is None or cand.signal not in {"BUY", "SELL"}:
            continue
        entry = float(ctx.entry)
        sl = float(cand.sl)
        tp = float(cand.tp)
        if not all(math.isfinite(x) for x in (entry, sl, tp)):
            continue
        hold = int(cand.max_hold_bars or getattr(strategy, "MAX_HOLD_BARS", 12) or 12)
        hold = min(12, max(1, hold))
        level_price = _extract_level_price(cand, entry, levels)
        meta = _nearest_level_meta(levels, level_price, entry, df_window=df_window, symbol=symbol)
        exit_meta = _simulate_exit(df, i, cand.signal, entry, sl, tp, pip, max_hold_bars=hold)
        sr_meta = cand.sr_meta or {}
        rows.append({
            "timestamp": df.index[i],
            "symbol": symbol.replace("=X", ""),
            "strategy": strategy_name,
            "signal": cand.signal,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "entry_type": cand.entry_type,
            "score": float(cand.score),
            "confidence": int(cand.confidence),
            "sr_level_price": meta["level_price"],
            "sr_distance_atr": sr_meta.get("distance_atr"),
            "own_touch": meta["own_touch"],
            "d1_touch": meta["d1_touch"],
            "w1_touch": meta["w1_touch"],
            "round_score": meta["round_score"],
            "magnitude_score": meta["magnitude_score"],
            "composite_weight": meta["composite_weight"],
            "distinct_touch": meta["distinct_touch"],
            "pnl_pip": float(exit_meta["pnl_pip"]),
            "win": bool(exit_meta["win"]),
            "exit_reason": exit_meta["exit_reason"],
            "year": int(df.index[i].year),
            "has_htf_source": bool(meta["d1_touch"] > 0 or meta["w1_touch"] > 0),
            "htf_source": (
                "D1+W1" if meta["d1_touch"] > 0 and meta["w1_touch"] > 0 else
                "D1 only" if meta["d1_touch"] > 0 else
                "W1 only" if meta["w1_touch"] > 0 else "none"
            ),
        })
        if max_signals is not None and len(rows) >= max_signals:
            break
    return pd.DataFrame(rows)


def _wilson_lower(wins: int, n: int, alpha: float = 0.05) -> float:
    from scipy.stats import norm

    if n <= 0:
        return 0.0
    z = float(norm.ppf(1 - alpha / 2))
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def _profit_factor(pnls: list[float]) -> float:
    gp = sum(p for p in pnls if p > 0)
    gl = -sum(p for p in pnls if p < 0)
    if gl <= 0:
        return float("inf") if gp > 0 else 0.0
    return gp / gl


def _metrics(df) -> dict:
    if df is None or len(df) == 0:
        return {"N": 0, "wins": 0, "WR": 0.0, "EV": 0.0, "Wilson_lo": 0.0, "PF": 0.0}
    pnls = [float(x) for x in df["pnl_pip"].to_list()]
    n = len(pnls)
    wins = int(sum(1 for p in pnls if p > 0))
    return {
        "N": n,
        "wins": wins,
        "WR": wins / n if n else 0.0,
        "EV": sum(pnls) / n if n else 0.0,
        "Wilson_lo": _wilson_lower(wins, n, alpha=BONF_ALPHA),
        "PF": _profit_factor(pnls),
        "PnL": sum(pnls),
    }


def bucket_stats(signals, weight_col: str, quintiles: int = 5):
    import pandas as pd

    if signals is None or len(signals) == 0:
        return pd.DataFrame()
    df = signals.copy()
    try:
        df["bucket"] = pd.qcut(df[weight_col], quintiles, labels=[f"Q{i}" for i in range(1, quintiles + 1)],
                               duplicates="drop")
    except ValueError:
        df["bucket"] = "ALL"
    rows = []
    for bucket, part in df.groupby("bucket", dropna=False, observed=False):
        m = _metrics(part)
        rows.append({
            "bucket": str(bucket),
            "N": m["N"],
            "WR": m["WR"],
            "EV": m["EV"],
            "Wilson_lo": m["Wilson_lo"],
            "mean_weight": float(part[weight_col].mean()) if len(part) else 0.0,
            "htf_rate": float(part["has_htf_source"].mean()) if "has_htf_source" in part else 0.0,
        })
    return pd.DataFrame(rows)


def _bootstrap_ev_diff_ci(heavy, all_rows, resamples: int = BOOTSTRAP_RESAMPLES) -> tuple[float, float]:
    import numpy as np

    if len(heavy) < 2 or len(all_rows) < 2:
        return (0.0, 0.0)
    h = heavy["pnl_pip"].astype(float).to_numpy()
    a = all_rows["pnl_pip"].astype(float).to_numpy()
    rng = np.random.default_rng(20260511)
    vals = np.empty(resamples, dtype=float)
    for i in range(resamples):
        vals[i] = rng.choice(h, size=len(h), replace=True).mean() - rng.choice(a, size=len(a), replace=True).mean()
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def _year_concentration_flag(rows) -> str:
    if rows is None or len(rows) == 0:
        return "no_signals"
    by_year = rows.groupby("year")
    for year, part in by_year:
        m = _metrics(part)
        if m["N"] >= 10 and m["WR"] >= 0.90 and m["N"] / len(rows) >= 0.50:
            return f"flag: {year} concentration WR={m['WR']:.3f} N={m['N']}"
    return "clear"


def _verdict(strategy_rows) -> tuple[str, dict]:
    all_m = _metrics(strategy_rows)
    heavy = strategy_rows[
        (strategy_rows["composite_weight"] >= PRIMARY_HEAVY_THRESHOLD)
        & (strategy_rows["has_htf_source"])
    ] if len(strategy_rows) else strategy_rows
    heavy_m = _metrics(heavy)
    ci_lo, ci_hi = _bootstrap_ev_diff_ci(heavy, strategy_rows)
    primary_edge = heavy_m["N"] > 0 and heavy_m["Wilson_lo"] > 0.50 and heavy_m["EV"] > 0 and ci_lo > 0
    if primary_edge:
        verdict = "REBORN_HEAVY"
    else:
        any_partial = False
        if len(strategy_rows):
            for _name, part in strategy_rows.groupby("htf_source"):
                pm = _metrics(part[part["composite_weight"] >= PRIMARY_HEAVY_THRESHOLD])
                if pm["N"] >= 5 and pm["Wilson_lo"] > 0.50 and pm["EV"] > 0:
                    any_partial = True
                    break
        verdict = "PARTIAL" if any_partial else "DEAD"
    return verdict, {
        "all": all_m,
        "heavy": heavy_m,
        "ci_ev_diff": (ci_lo, ci_hi),
        "year_flag": _year_concentration_flag(strategy_rows),
    }


def _fmt(x: Any, digits: int = 4) -> str:
    if x is None:
        return ""
    if isinstance(x, float):
        if math.isinf(x):
            return "inf"
        return f"{x:.{digits}f}"
    return str(x)


def _md_table(rows: list[dict], columns: list[str]) -> str:
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(_fmt(row.get(c)) for c in columns) + " |")
    return "\n".join(out)


def _simple_group_table(rows, col: str) -> list[dict]:
    out = []
    if rows is None or len(rows) == 0:
        return out
    for key, part in rows.groupby(col, dropna=False):
        m = _metrics(part)
        out.append({"bucket": str(key), "N": m["N"], "WR": m["WR"], "EV": m["EV"],
                    "Wilson_lo": m["Wilson_lo"]})
    return out


def write_report(all_rows, report_path: Path):
    lines = [
        "# SR Weight Gate Empirical Audit v2",
        "",
        "## Summary",
    ]
    summary_rows = []
    verdicts = {}
    for strategy in STRATEGIES:
        rows = all_rows[all_rows["strategy"] == strategy] if len(all_rows) else all_rows
        verdict, meta = _verdict(rows)
        verdicts[strategy] = verdict
        all_m = meta["all"]
        heavy_m = meta["heavy"]
        summary_rows.append({
            "Strategy": strategy,
            "N total": all_m["N"],
            "N heavy": heavy_m["N"],
            "WR all": all_m["WR"],
            "WR heavy": heavy_m["WR"],
            "EV all": all_m["EV"],
            "EV heavy": heavy_m["EV"],
            "Wilson_lo (heavy, Bonf)": heavy_m["Wilson_lo"],
            "Verdict": verdict,
        })
    lines.append(_md_table(summary_rows, [
        "Strategy", "N total", "N heavy", "WR all", "WR heavy", "EV all",
        "EV heavy", "Wilson_lo (heavy, Bonf)", "Verdict",
    ]))
    lines.extend(["", "## Per-Strategy Details"])
    for strategy in STRATEGIES:
        rows = all_rows[all_rows["strategy"] == strategy] if len(all_rows) else all_rows
        verdict, meta = _verdict(rows)
        lines.extend(["", f"### {strategy}"])
        q = bucket_stats(rows, "composite_weight")
        lines.append("- composite_weight quintile bucket stats")
        lines.append(_md_table(q.to_dict("records"), ["bucket", "N", "WR", "EV", "Wilson_lo", "mean_weight", "htf_rate"])
                     if len(q) else "_no signals_")
        lines.append("- HTF source bucket stats")
        lines.append(_md_table(_simple_group_table(rows, "htf_source"), ["bucket", "N", "WR", "EV", "Wilson_lo"])
                     if len(rows) else "_no signals_")
        if len(rows):
            tmp = rows.copy()
            tmp["own_touch_bucket"] = tmp["own_touch"].map(
                lambda x: "1" if x <= 1 else "2" if x == 2 else "3" if x == 3 else "4-5" if x <= 5 else "6+"
            )
            try:
                tmp["magnitude_quartile"] = __import__("pandas").qcut(
                    tmp["magnitude_score"], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop"
                )
            except ValueError:
                tmp["magnitude_quartile"] = "ALL"
            lines.append("- own_touch bucket stats")
            lines.append(_md_table(_simple_group_table(tmp, "own_touch_bucket"), ["bucket", "N", "WR", "EV", "Wilson_lo"]))
            lines.append("- magnitude quartile stats")
            lines.append(_md_table(_simple_group_table(tmp, "magnitude_quartile"), ["bucket", "N", "WR", "EV", "Wilson_lo"]))
        lines.append(f"- single-year concentration check: {meta['year_flag']}")
        ci_lo, ci_hi = meta["ci_ev_diff"]
        lines.append(f"- bootstrap EV diff CI (heavy+HTF minus all): [{ci_lo:.4f}, {ci_hi:.4f}]")
        if verdict in {"REBORN_HEAVY", "PARTIAL"}:
            lines.append("- Redesign spec draft: see docs/sr_redesign_drafts if generated.")
        else:
            lines.append("- Redesign spec draft: not generated because verdict is DEAD.")
    lines.extend([
        "",
        "## Exploratory Thresholds",
    ])
    exp_rows = []
    for strategy in STRATEGIES:
        rows = all_rows[all_rows["strategy"] == strategy] if len(all_rows) else all_rows
        for th in EXPLORATORY_THRESHOLDS:
            part = rows[rows["composite_weight"] >= th] if len(rows) else rows
            m = _metrics(part)
            exp_rows.append({"Strategy": strategy, "threshold": th, "N": m["N"], "WR": m["WR"],
                             "EV": m["EV"], "Wilson_lo": m["Wilson_lo"]})
    lines.append(_md_table(exp_rows, ["Strategy", "threshold", "N", "WR", "EV", "Wilson_lo"]))
    lines.extend([
        "",
        "## Statistical Discipline",
        f"- Pre-registered primary threshold: composite_weight >= {PRIMARY_HEAVY_THRESHOLD}",
        f"- Primary heavy bucket additionally requires HTF source for REBORN_HEAVY verdict.",
        f"- Exploratory thresholds: {EXPLORATORY_THRESHOLDS}",
        f"- Bonferroni m={BONFERRONI_M}, alpha={BONF_ALPHA}",
        f"- Bootstrap CI: {BOOTSTRAP_RESAMPLES} resamples",
        "- Data source: data/cache/massive/*.parquet only; Yahoo is not used.",
        "- Strategy evaluate() code was not modified; weight gate is audit-only post-hoc analysis.",
        f"- Runtime note: strategy signal collection used fixed strides {RUN_STRIDES}; "
        "this preserves evaluate() behavior but samples high-frequency duplicate opportunities.",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return verdicts, summary_rows


def write_redesign_drafts(verdicts: dict[str, str]):
    out_dir = ROOT / "docs" / "sr_redesign_drafts"
    out_dir.mkdir(parents=True, exist_ok=True)
    for strategy, verdict in verdicts.items():
        if verdict not in {"REBORN_HEAVY", "PARTIAL"}:
            continue
        path = out_dir / f"{strategy}_v1.md"
        path.write_text(
            "\n".join([
                f"# {strategy} redesign draft v1",
                "",
                "Verdict-triggered draft from sr_weight_gate_audit_v2.",
                "",
                "## Gate",
                "- Require nearest SR level composite_weight >= 5.0.",
                "- Require d1_touch > 0 or w1_touch > 0 for the primary production gate.",
                "- Keep 3.0/4.0/6.0/8.0 thresholds exploratory only.",
                "",
                "## Implementation sketch",
                "1. Pass weighted SR levels into ctx.layer3['sr_weighted_levels'].",
                "2. At the existing nearest-level selection point, fetch matching level metadata.",
                "3. Return None if composite_weight < 5.0 or no HTF source.",
                "4. Keep current SL/TP geometry unchanged for the first shadow run.",
                "",
                "## Diff target",
                f"- Strategy file: {STRATEGY_SPECS[strategy].cls_path.split(':')[0].replace('.', '/')}.py",
                "- Insert the gate immediately after nearest SR/confluence level selection.",
            ]) + "\n",
            encoding="utf-8",
        )


def run_all(limit_symbols: int | None = None, limit_bars: int | None = None):
    import pandas as pd

    started = time.time()
    frames = []
    selected_targets = TARGETS[:limit_symbols] if limit_symbols else TARGETS
    for pair, symbol in selected_targets:
        print(f"[audit] loading {pair}", flush=True)
        df15 = load_data(symbol, "15m")
        if limit_bars:
            df15 = df15.tail(limit_bars).copy()
        df1h = load_data(symbol, "1h")
        df1h = df1h.loc[df1h.index >= df15.index.min()].copy()
        d1 = resample_htf(df1h, "1D")
        w1 = resample_htf(df1h, "1W")
        tol_pip = max(float(df15["atr"].median()) * 0.30 / pip_size(symbol), 3.0)
        levels = detect_sr_levels_with_weight(df15, d1, w1, tol_pip, min_touches=2, symbol=symbol)
        print(f"[audit] {pair}: weighted levels={len(levels)}", flush=True)
        for strategy in STRATEGIES:
            print(f"[audit] {pair} {strategy}", flush=True)
            rows = run_strategy_bt(
                strategy, df15, levels, symbol=symbol,
                stride=RUN_STRIDES.get(strategy, 1),
            )
            print(f"[audit] {pair} {strategy}: signals={len(rows)}", flush=True)
            frames.append(rows)
    all_rows = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw_path = ROOT / "raw" / "audits" / f"sr_weight_gate_v2_{today}.parquet"
    report_path = ROOT / "reports" / f"sr_weight_gate_audit_v2_{today}.md"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows.to_parquet(raw_path, index=False)
    verdicts, summary_rows = write_report(all_rows, report_path)
    write_redesign_drafts(verdicts)
    print(f"[audit] wrote {raw_path.relative_to(ROOT)}", flush=True)
    print(f"[audit] wrote {report_path.relative_to(ROOT)}", flush=True)
    print(f"[audit] elapsed_s={time.time() - started:.1f}", flush=True)
    return all_rows, raw_path, report_path, summary_rows


def unit_tests() -> None:
    import pandas as pd

    idx = pd.date_range("2026-01-01", periods=15, freq="15min", tz="UTC")
    df = pd.DataFrame({
        "Open": [99, 99, 99, 103, 103, 103, 103, 103, 103, 99, 99, 99, 103, 103, 103],
        "High": [101, 101, 101, 104, 104, 104, 104, 104, 104, 101, 101, 101, 104, 104, 104],
        "Low": [99, 99, 99, 102, 102, 102, 102, 102, 102, 99, 99, 99, 102, 102, 102],
        "Close": [100, 100, 100, 103, 103, 103, 103, 103, 103, 100, 100, 100, 103, 103, 103],
    }, index=idx)
    assert count_distinct_touches(df.iloc[:3], 100, 0.1) == 1
    assert count_distinct_touches(df, 100, 0.1, min_gap_bars=5) == 2
    cw = composite_weight({
        "own_touch": 2, "d1_touch": 1, "w1_touch": 1,
        "round_score": 0.5, "magnitude_score": 0.5,
    })
    assert abs(cw - 11.75) < 1e-12
    atr = pd.Series([2.0] * len(df), index=df.index)
    mag = median_rejection_size(df.iloc[:3], 100, 0.1, atr.iloc[:3])
    assert abs(mag - 1.0) < 1e-12
    print("[unit] PASS", flush=True)


def integration_tests() -> None:
    unit_tests()
    samples = []
    for _pair, symbol in TARGETS:
        df15 = load_data(symbol, "15m").tail(5000).copy()
        df1h = load_data(symbol, "1h")
        df1h = df1h.loc[df1h.index >= df15.index.min()].copy()
        levels = detect_sr_levels_with_weight(
            df15, resample_htf(df1h, "1D"), resample_htf(df1h, "1W"),
            tolerance_pip=max(float(df15["atr"].median()) * 0.30 / pip_size(symbol), 3.0),
            min_touches=2, symbol=symbol,
        )
        assert len(levels) >= 1, "detect_sr_levels_with_weight returned no levels"
        samples.append((symbol, df15, levels))
    frames = []
    for strategy in STRATEGIES:
        found = None
        for symbol, df15, levels in samples:
            rows = run_strategy_bt(strategy, df15, levels, symbol=symbol, max_signals=10)
            if len(rows) >= 1:
                found = rows
                break
        assert found is not None and len(found) >= 1, f"{strategy} returned no signals in integration sample"
        frames.append(found)
    import pandas as pd
    all_rows = pd.concat(frames, ignore_index=True)
    heavy_rate = float((all_rows["composite_weight"] >= PRIMARY_HEAVY_THRESHOLD).mean())
    assert 0.01 <= heavy_rate <= 0.30, f"heavy signal rate out of sanity range: {heavy_rate:.4f}"
    report = ROOT / "reports" / "sr_weight_gate_audit_v2_integration.md"
    write_report(all_rows, report)
    assert report.exists()
    print("[integration] PASS", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="run full 5 strategy x 5 pair audit")
    parser.add_argument("--unit-tests", action="store_true")
    parser.add_argument("--integration-tests", action="store_true")
    parser.add_argument("--limit-symbols", type=int, default=None, help="debug only")
    parser.add_argument("--limit-bars", type=int, default=None, help="debug only")
    args = parser.parse_args()
    if args.unit_tests:
        unit_tests()
        return 0
    if args.integration_tests:
        integration_tests()
        return 0
    if args.all:
        run_all(limit_symbols=args.limit_symbols, limit_bars=args.limit_bars)
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
