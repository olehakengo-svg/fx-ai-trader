#!/usr/bin/env python3
"""Kalman D7 / ZZ Pivot v60 SR zero-fire diagnostic probe.

Reads fresh/local MASSIVE OHLCV parquet, evaluates the production strategy
filters over a UTC window, and prints first-fail histograms plus latest
telemetry per category.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.regime_classifier import REGIME_UP, classify_regime, is_regime_start
from strategies.context import SignalContext
from strategies.daytrade.kalman_d7_trend import (
    _kalman_d7_indicators,
    _kalman_d7_passes_filters,
)
from strategies.daytrade.zz_pivot_v60_sr import ZzPivotV60Sr

def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def _resample_m15(df: pd.DataFrame) -> pd.DataFrame:
    data = _normalize_ohlcv(df)
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    if "vwap" in data.columns:
        agg["vwap"] = "last"
    out = data.resample("15min", label="left", closed="left").agg(agg)
    out = out.dropna(subset=["Open", "High", "Low", "Close"])
    return out


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    return (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    high = out["High"].astype(float)
    low = out["Low"].astype(float)
    close = out["Close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    out["atr"] = tr.ewm(alpha=1.0 / 14, adjust=False).mean()
    out["atr7"] = tr.ewm(alpha=1.0 / 7, adjust=False).mean()
    for span in (9, 21, 50, 200):
        out[f"ema{span}"] = close.ewm(span=span, adjust=False).mean()
    out["rsi"] = _rsi(close, 14)
    out["rsi5"] = _rsi(close, 5)
    out["rsi9"] = _rsi(close, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    out["macd_hist"] = macd - signal
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std(ddof=0)
    out["bb_mid"] = bb_mid
    out["bb_upper"] = bb_mid + 2.0 * bb_std
    out["bb_lower"] = bb_mid - 2.0 * bb_std
    width = out["bb_upper"] - out["bb_lower"]
    out["bb_width"] = width / bb_mid
    out["bb_pband"] = ((close - out["bb_lower"]) / width).clip(-1.0, 2.0).fillna(0.5)
    out["adx"] = 25.0
    out["adx_pos"] = 25.0
    out["adx_neg"] = 25.0
    return out


def _ctx(df_slice: pd.DataFrame, symbol: str, ts: pd.Timestamp) -> SignalContext:
    row = df_slice.iloc[-1]
    ctx = SignalContext.from_df(
        df_slice,
        row,
        symbol=symbol,
        tf="15m",
        sr_levels=[],
        layer0={},
        layer1={},
        regime={},
        layer2={},
        layer3={},
        htf={},
        session={},
        backtest_mode=True,
        bar_time=ts,
    )
    ctx.regime_po = classify_regime(df_slice)
    ctx.regime_po_start_up = is_regime_start(df_slice, REGIME_UP)
    return ctx


def _kalman_category(reasons: list[str]) -> str:
    if not reasons:
        return "other"
    reason = reasons[0]
    if "Perfect Order UP not started" in reason:
        return "po_up_not_started"
    if "DIST" in reason:
        return "dist_out_of_range(>3 or <=0)"
    if "GAP" in reason:
        return "gap_too_wide(>=3)"
    if "ATR" in reason and "outside Q2-Q4" in reason:
        return "atr_outside_q2q4"
    if "RSI" in reason:
        return "rsi_overbought(>=70)"
    if "session UTC" in reason:
        return "session_excluded(OVL/DEAD)"
    return "other"


def _kalman_telemetry(ctx: SignalContext, ind: dict[str, Any] | None) -> dict[str, Any]:
    tel = {
        "bar_time": str(ctx.bar_time),
        "entry_price": round(float(ctx.entry), 5),
        "hour_utc": int(ctx.hour_utc),
        "rsi": round(float(ctx.rsi), 2),
    }
    if ind:
        atr = float(ind["atr"])
        tel.update({
            "ema200": round(float(ind["ema200"]), 5),
            "atr": round(atr, 5),
            "dist_atr": round((float(ctx.entry) - float(ind["ema200"])) / atr, 4) if atr > 0 else None,
            "gap_atr": round((float(ind["ema25"]) - float(ind["ema200"])) / atr, 4) if atr > 0 else None,
            "atr_p20": round(float(ind["atr_p20"]), 5),
            "atr_p80": round(float(ind["atr_p80"]), 5),
            "regime_po": ctx.regime_po,
            "regime_po_start_up": bool(ctx.regime_po_start_up),
        })
    return tel


def probe_kalman(df: pd.DataFrame, start: str, end: str) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    latest: dict[str, Any] = {}
    pass_events: list[dict[str, Any]] = []
    pass_count = 0
    bars = 0
    for ts in df.loc[start:end].index:
        hist = df.loc[:ts]
        if len(hist) < 211:
            continue
        bars += 1
        ctx = _ctx(hist, "USDJPY=X", ts)
        ind = _kalman_d7_indicators(ctx)
        if ind is None:
            cat = "indicator_unavailable"
            counts[cat] += 1
            latest[cat] = _kalman_telemetry(ctx, ind)
            continue
        ok, reasons = _kalman_d7_passes_filters(ctx, ind)
        if ok:
            pass_count += 1
            cat = "PASS"
            pass_events.append(_kalman_telemetry(ctx, ind))
        else:
            cat = _kalman_category(reasons)
        counts[cat] += 1
        latest[cat] = _kalman_telemetry(ctx, ind) | {"reason": reasons[0] if reasons else ""}
    return {
        "bars": bars,
        "pass_count": pass_count,
        "counts": dict(counts),
        "latest": latest,
        "pass_events": pass_events,
    }


def _zz_attempts(strat: ZzPivotV60Sr, ctx: SignalContext, features: dict[str, Any], df: pd.DataFrame) -> dict[str, bool]:
    return {
        "pA": strat._detect_peak(ctx, features, df) == "pA",
        "pB": strat._detect_peak(ctx, features, df) == "pB",
        "pE": strat._detect_peak(ctx, features, df) == "pE",
        "pF": strat._detect_peak(ctx, features, df) == "pF",
        "tA": strat._detect_trough(ctx, features, df) == "tA",
        "tB": strat._detect_trough(ctx, features, df) == "tB",
        "tD": strat._detect_trough(ctx, features, df) == "tD",
        "tF": strat._detect_trough(ctx, features, df) == "tF",
    }


def _zz_diagnose(strat: ZzPivotV60Sr, ctx: SignalContext) -> tuple[str, dict[str, Any]]:
    sym = ctx.symbol.upper().replace("=X", "").replace("/", "").replace("_", "")
    if sym not in strat._ALLOWED_SYMBOLS or ctx.tf not in strat._ALLOWED_TF:
        return "tf_filter_miss", {}
    if ctx.df is None or len(ctx.df) < max(strat.TREND_EMA_LEN, strat.ATR_BASELINE_LEN) + 30:
        return "df_too_short", {}
    df = ctx.df
    try:
        trend_ema = float(df["Close"].ewm(span=strat.TREND_EMA_LEN, adjust=False).mean().iloc[-1])
    except Exception as exc:
        return "feature_compute_error", {"error": f"trend_ema:{exc}"}
    uptrend = ctx.entry > trend_ema
    downtrend = ctx.entry < trend_ema
    if not (uptrend or downtrend):
        return "no_trend", {"trend_ema": trend_ema}
    try:
        atr_series = strat._compute_atr_series(df, 14)
        atr_baseline = float(atr_series.ewm(span=strat.ATR_BASELINE_LEN, adjust=False).mean().iloc[-1])
        atr_ratio = ctx.atr / atr_baseline if atr_baseline > 0 else 1.0
        features = strat._compute_features(df, ctx)
    except Exception as exc:
        return "feature_compute_error", {"trend_ema": trend_ema, "error": str(exc)}
    peak_type = strat._detect_peak(ctx, features, df) if uptrend else None
    trough_type = strat._detect_trough(ctx, features, df) if downtrend else None
    attempts = _zz_attempts(strat, ctx, features, df)
    tel = {
        "trend_ema": round(trend_ema, 5),
        "uptrend": bool(uptrend),
        "downtrend": bool(downtrend),
        "atr_ratio": round(float(atr_ratio), 4),
        "peak_type_attempts": attempts,
        "features": {
            k: round(float(v), 5) if isinstance(v, (float, int)) else v
            for k, v in features.items()
            if k in {
                "rsi_d5", "rci_d5", "bbp_d5", "clz_d5", "rci9",
                "rsi_accel", "up_streak", "dn_streak", "near_high",
                "near_low", "vol_z", "high_now", "low_now",
            }
        },
    }
    if peak_type is None and trough_type is None:
        return "no_peak_no_trough", tel
    if ctx.atr <= 0:
        return "feature_compute_error", tel | {"error": "atr<=0"}
    rr = strat.TP_ATR_MULT / strat.SL_ATR_MULT
    if rr < strat.MIN_RR:
        return "rr_below_min", tel | {"rr": rr}
    cand = strat.evaluate(ctx)
    if cand is not None:
        return "PASS", tel | {"entry_type": cand.entry_type, "signal": cand.signal}
    return "<other>", tel


def _zz_telemetry(ctx: SignalContext, extra: dict[str, Any]) -> dict[str, Any]:
    base = {
        "bar_time": str(ctx.bar_time),
        "entry_price": round(float(ctx.entry), 5),
        "ema200": round(float(ctx.ema200), 5),
        "atr": round(float(ctx.atr), 5),
        "rsi": round(float(ctx.rsi), 2),
        "hour_utc": int(ctx.hour_utc),
    }
    return base | extra


def probe_zz(df: pd.DataFrame, start: str, end: str) -> dict[str, Any]:
    strat = ZzPivotV60Sr()
    counts: Counter[str] = Counter()
    latest: dict[str, Any] = {}
    pass_events: list[dict[str, Any]] = []
    pass_count = 0
    bars = 0
    for ts in df.loc[start:end].index:
        hist = df.loc[:ts]
        bars += 1
        ctx = _ctx(hist, "EURUSD=X", ts)
        cat, extra = _zz_diagnose(strat, ctx)
        if cat == "PASS":
            pass_count += 1
            pass_events.append(_zz_telemetry(ctx, extra))
        counts[cat] += 1
        latest[cat] = _zz_telemetry(ctx, extra)
    return {
        "bars": bars,
        "pass_count": pass_count,
        "counts": dict(counts),
        "latest": latest,
        "pass_events": pass_events,
    }


def _percent_table(result: dict[str, Any]) -> list[dict[str, Any]]:
    bars = result["bars"] or 1
    return [
        {"first_filter_failed": k, "bars": v, "pct": round(v * 100.0 / bars, 2)}
        for k, v in sorted(result["counts"].items(), key=lambda item: (-item[1], item[0]))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usd-jpy", default="data/cache/massive/USD_JPY_5m_latest_tmp.parquet")
    parser.add_argument("--eur-usd", default="data/cache/massive/EUR_USD_5m_latest_tmp.parquet")
    parser.add_argument("--start", default="2026-05-26T00:00:00+00:00")
    parser.add_argument("--end", default="2026-06-02T23:59:59+00:00")
    args = parser.parse_args()

    usd = _enrich(_resample_m15(pd.read_parquet(ROOT / args.usd_jpy)))
    eur = _enrich(_resample_m15(pd.read_parquet(ROOT / args.eur_usd)))
    result = {
        "window": {"start": args.start, "end": args.end},
        "data_ranges": {
            "USD_JPY": {"start": usd.index.min().isoformat(), "end": usd.index.max().isoformat(), "bars": len(usd)},
            "EUR_USD": {"start": eur.index.min().isoformat(), "end": eur.index.max().isoformat(), "bars": len(eur)},
        },
        "kalman": probe_kalman(usd, args.start, args.end),
        "zz_pivot": probe_zz(eur, args.start, args.end),
    }
    result["kalman"]["table"] = _percent_table(result["kalman"])
    result["zz_pivot"]["table"] = _percent_table(result["zz_pivot"])
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
