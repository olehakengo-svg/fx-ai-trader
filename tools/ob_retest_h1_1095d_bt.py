#!/usr/bin/env python3
"""Pre-registered 1095d BT for ObRetestH1.

LOCKED: this script changes only the validation period from the 365d first
attempt. Strategy parameters, pair set, friction, and verdict criteria remain
fixed by the 2026-05-18 pre-registration.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("BT_REQUIRE_MASSIVE_CACHE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")
sys.modules.setdefault("pytest", object())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from strategies.hourly.ob_retest import ObRetestH1  # noqa: E402


PAIRS = ("USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY")
START = pd.Timestamp("2023-05-15 13:00:00", tz="UTC")
END = pd.Timestamp("2026-05-15 13:00:00", tz="UTC")
OUTFILE = ROOT / "raw" / "bt-results" / "ob_retest_h1_1095d_2026_05_18.json"

SPREAD_PIPS = {
    "USD_JPY": 0.7,
    "EUR_USD": 0.6,
    "GBP_USD": 1.0,
    "EUR_JPY": 1.0,
    "GBP_JPY": 1.5,
}
SLIPPAGE_PIPS = 0.2
COMMISSION = 0
WILSON_Z = 1.959963984540054
WILSON_BF_Z = 2.5758293035489004


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        ts = value if isinstance(value, pd.Timestamp) else pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return ts.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return "inf" if value > 0 else "-inf"
    return value


def _load_frame(pair: str) -> tuple[pd.DataFrame, Path]:
    path = ROOT / "data" / "cache" / "massive" / f"{pair}_1h.parquet"
    if not path.exists():
        raise FileNotFoundError(f"missing MASSIVE parquet: {path.relative_to(ROOT)}")

    df = pd.read_parquet(path).copy()
    df.columns = [str(c).lower() for c in df.columns]
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    if not isinstance(df.index, pd.DatetimeIndex):
        for col in ("time", "timestamp", "datetime", "date"):
            if col in df.columns:
                df.index = pd.to_datetime(df[col], utc=True)
                break
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{path.relative_to(ROOT)} must have a DatetimeIndex or timestamp column")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    required = {"Open", "High", "Low", "Close"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path.relative_to(ROOT)} missing OHLC columns: {missing}")
    cols = ["Open", "High", "Low", "Close"] + (["Volume"] if "Volume" in df.columns else [])
    return df[cols].astype(float).sort_index().dropna(subset=["Open", "High", "Low", "Close"]), path


def _rsi_wilder(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    high = out["High"]
    low = out["Low"]
    close = out["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr"] = tr.rolling(14, min_periods=1).mean()
    out["atr7"] = tr.rolling(7, min_periods=1).mean()
    out["ema9"] = close.ewm(span=9, adjust=False).mean()
    out["ema21"] = close.ewm(span=21, adjust=False).mean()
    out["ema50"] = close.ewm(span=50, adjust=False).mean()
    out["ema200"] = close.ewm(span=200, adjust=False).mean()
    out["rsi"] = _rsi_wilder(close, 14)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    mid = close.rolling(20, min_periods=20).mean()
    sd = close.rolling(20, min_periods=20).std(ddof=0)
    out["bb_mid"] = mid
    out["bb_upper"] = mid + 2.0 * sd
    out["bb_lower"] = mid - 2.0 * sd
    out["bb_pband"] = ((close - out["bb_lower"]) / (out["bb_upper"] - out["bb_lower"]).replace(0, np.nan)).fillna(0.5)
    out["bb_width"] = ((out["bb_upper"] - out["bb_lower"]) / close.replace(0, np.nan)).fillna(0.01)
    return out


def _wilson_lower(wins: int, n: int, z: float = WILSON_Z) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def _pf(pnls: list[float]) -> float:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    if gross_loss <= 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _stats(trades: list[dict]) -> dict:
    pnls = [float(t["pnl_pips"]) for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    pf = _pf(pnls)
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n else 0.0,
        "Wilson_lo": round(_wilson_lower(wins, n, WILSON_Z), 4),
        "Wilson_bf_lo": round(_wilson_lower(wins, n, WILSON_BF_Z), 4),
        "EV_pips": round(sum(pnls) / n, 4) if n else 0.0,
        "PnL_pips": round(sum(pnls), 4),
        "PF": round(pf, 4) if math.isfinite(pf) else "inf",
    }


def _wf_stats(trades: list[dict]) -> dict[str, dict]:
    fold_days = (END - START) / 3
    folds = {
        "h1": (START, START + fold_days),
        "h2": (START + fold_days, START + 2 * fold_days),
        "h3": (START + 2 * fold_days, END + pd.Timedelta(nanoseconds=1)),
    }
    out: dict[str, dict] = {}
    for name, (fold_start, fold_end) in folds.items():
        fold_trades = [
            t for t in trades
            if fold_start <= pd.Timestamp(t["entry_time"]) < fold_end
        ]
        out[name] = _stats(fold_trades)
    return out


def _passes(summary: dict) -> bool:
    wf = summary["WF"]
    return (
        summary["N"] >= 200
        and summary["WR"] >= 0.44
        and summary["Wilson_lo"] >= 0.40
        and summary["EV_pips"] >= 0.20
        and (summary["PF"] == "inf" or summary["PF"] >= 1.10)
        and all(fold["EV_pips"] >= 0 for fold in wf.values())
    )


def _signal_at(arrays: dict[str, np.ndarray], i: int) -> dict | None:
    """Fast path equivalent of ObRetestH1.evaluate() for the locked BT."""
    open_values = arrays["Open"]
    high_values = arrays["High"]
    low_values = arrays["Low"]
    close_values = arrays["Close"]
    atr_values = arrays["atr"]
    ema_fast_values = arrays[f"ema{ObRetestH1.EMA_FAST}"]
    ema_slow_values = arrays[f"ema{ObRetestH1.EMA_SLOW}"]

    current_idx = i
    first_idx = max(0, current_idx - ObRetestH1.OB_LOOKBACK)
    last_candidate = current_idx - ObRetestH1.IMPULSE_MIN_BARS - 1
    if last_candidate < first_idx:
        return None

    blocks: list[tuple[str, float, float, int]] = []
    for idx in range(first_idx, last_candidate + 1):
        atr = float(atr_values[idx])
        if atr <= 0:
            continue
        ob_high = float(high_values[idx])
        ob_low = float(low_values[idx])
        ob_range = ob_high - ob_low
        if ob_range <= 0 or ob_range > atr * ObRetestH1.OB_MAX_WIDTH_ATR:
            continue

        age = current_idx - (idx + ObRetestH1.IMPULSE_MIN_BARS)
        if age > ObRetestH1.OB_FRESHNESS:
            continue

        impulse_slice = slice(idx + 1, idx + 1 + ObRetestH1.IMPULSE_MIN_BARS)
        impulse_range = float(high_values[impulse_slice].max() - low_values[impulse_slice].min())
        cand_open = float(open_values[idx])
        cand_close = float(close_values[idx])

        if cand_close < cand_open:
            all_bullish = bool((close_values[impulse_slice] > open_values[impulse_slice]).all())
            if all_bullish and impulse_range >= atr * ObRetestH1.IMPULSE_ATR_MULT:
                blocks.append(("BUY", ob_high, ob_low, age))

        if cand_close > cand_open:
            all_bearish = bool((close_values[impulse_slice] < open_values[impulse_slice]).all())
            if all_bearish and impulse_range >= atr * ObRetestH1.IMPULSE_ATR_MULT:
                blocks.append(("SELL", ob_high, ob_low, age))

    if not blocks:
        return None

    entry = float(close_values[i])
    open_price = float(open_values[i])
    close = float(close_values[i])
    high = float(high_values[i])
    low = float(low_values[i])
    atr = float(atr_values[i])
    ema_fast = float(ema_fast_values[i])
    ema_slow = float(ema_slow_values[i])
    if atr <= 0:
        return None

    buffer = ObRetestH1.RETEST_BUFFER_ATR * atr
    sl_buffer = ObRetestH1.SL_BUFFER_ATR * atr
    for side, ob_high, ob_low, age in sorted(blocks, key=lambda ob: (ob[3], ob[1] - ob[2])):
        if side == "BUY":
            touched = low <= ob_high + buffer and low >= ob_low - buffer
            confirmed = close > open_price and ema_fast > ema_slow and close > ema_slow
            if not (touched and confirmed):
                continue
            sl = ob_low - sl_buffer
            risk = entry - sl
            if risk <= 0:
                continue
            return {
                "signal": "BUY",
                "sl": sl,
                "tp": entry + risk * ObRetestH1.TP_R_MULT,
                "ob_age": age,
                "max_hold_bars": ObRetestH1.MAX_HOLD_BARS,
            }

        touched = high >= ob_low - buffer and high <= ob_high + buffer
        confirmed = close < open_price and ema_fast < ema_slow and close < ema_slow
        if not (touched and confirmed):
            continue
        sl = ob_high + sl_buffer
        risk = sl - entry
        if risk <= 0:
            continue
        return {
            "signal": "SELL",
            "sl": sl,
            "tp": entry - risk * ObRetestH1.TP_R_MULT,
            "ob_age": age,
            "max_hold_bars": ObRetestH1.MAX_HOLD_BARS,
        }

    return None


def _run_pair(pair: str) -> dict:
    raw, path = _load_frame(pair)
    requested = raw.loc[(raw.index >= START) & (raw.index <= END)]
    if requested.empty:
        raise ValueError(f"{pair} has no rows in requested period")

    df = _add_indicators(requested)
    pip_mult = 100 if "JPY" in pair else 10000
    friction_pips = SPREAD_PIPS[pair] + SLIPPAGE_PIPS + COMMISSION
    trades: list[dict] = []
    i = max(ObRetestH1.OB_LOOKBACK, 30)
    arrays = {col: df[col].to_numpy() for col in ("Open", "High", "Low", "Close", "atr", "ema9", "ema21")}

    while i < len(df) - 1:
        cand = _signal_at(arrays, i)
        if cand is None:
            i += 1
            continue

        entry = float(df.iloc[i]["Close"])
        max_exit = min(len(df) - 1, i + (cand["max_hold_bars"] or ObRetestH1.MAX_HOLD_BARS))
        exit_i = max_exit
        exit_price = float(df.iloc[max_exit]["Close"])
        exit_reason = "TIME_STOP"

        for j in range(i + 1, max_exit + 1):
            row = df.iloc[j]
            high = float(row["High"])
            low = float(row["Low"])
            if cand["signal"] == "BUY":
                if low <= cand["sl"]:
                    exit_i, exit_price, exit_reason = j, float(cand["sl"]), "SL"
                    break
                if high >= cand["tp"]:
                    exit_i, exit_price, exit_reason = j, float(cand["tp"]), "TP"
                    break
            else:
                if high >= cand["sl"]:
                    exit_i, exit_price, exit_reason = j, float(cand["sl"]), "SL"
                    break
                if low <= cand["tp"]:
                    exit_i, exit_price, exit_reason = j, float(cand["tp"]), "TP"
                    break

        raw_pips = (exit_price - entry) * pip_mult
        if cand["signal"] == "SELL":
            raw_pips = -raw_pips
        pnl_pips = raw_pips - friction_pips

        trades.append(
            {
                "entry_time": df.index[i].isoformat(),
                "exit_time": df.index[exit_i].isoformat(),
                "signal": cand["signal"],
                "entry": round(entry, 6),
                "sl": round(float(cand["sl"]), 6),
                "tp": round(float(cand["tp"]), 6),
                "exit": round(exit_price, 6),
                "exit_reason": exit_reason,
                "ob_age": cand["ob_age"],
                "raw_pips": round(raw_pips, 4),
                "friction_pips": friction_pips,
                "pnl_pips": round(pnl_pips, 4),
            }
        )
        i = exit_i + 1

    summary = {
        "pair": pair,
        "data_file": str(path.relative_to(ROOT)),
        "data_start": requested.index.min().isoformat(),
        "data_end": requested.index.max().isoformat(),
        "bars": int(len(requested)),
        **_stats(trades),
        "WF": _wf_stats(trades),
        "trades": trades,
    }
    summary["PASS"] = _passes(summary)
    return summary


def main() -> int:
    pairs = {pair: _run_pair(pair) for pair in PAIRS}
    verdict = "PASS" if any(result["PASS"] for result in pairs.values()) else "FAIL"
    result = {
        "strategy": "ob_retest_h1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_period": {
            "start": START.isoformat(),
            "end": END.isoformat(),
            "days": 1095,
        },
        "timeframe": "1h",
        "data_source": "data/cache/massive/*.parquet only",
        "friction_model": {
            "spread_pips": SPREAD_PIPS,
            "slippage_pips": SLIPPAGE_PIPS,
            "commission": COMMISSION,
        },
        "wf_folds": "3 chronological folds over requested 1095d period",
        "criteria": {
            "PASS": "At least 1 of 5 pairs has N>=200, WR>=44%, Wilson_lo>=0.40, EV>=+0.20 pip/trade, PF>=1.10, and h1/h2/h3 WF EV>=0",
            "Bonferroni_m": 5,
            "Wilson_lo_z": WILSON_Z,
            "Wilson_bf_lo_z": WILSON_BF_Z,
        },
        "verdict": verdict,
        "pairs": pairs,
    }
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(_jsonable(result), ensure_ascii=False, indent=2) + "\n")

    print(f"wrote {OUTFILE.relative_to(ROOT)}")
    print(f"verdict={verdict}")
    for pair, summary in pairs.items():
        wf_ev = ",".join(f"{k}:{v['EV_pips']:+.4f}" for k, v in summary["WF"].items())
        print(
            f"{pair} N={summary['N']} WR={summary['WR']:.2%} "
            f"Wilson_lo={summary['Wilson_lo']:.4f} EV={summary['EV_pips']:+.4f} "
            f"PF={summary['PF']} WF_EV={wf_ev} PASS={summary['PASS']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
