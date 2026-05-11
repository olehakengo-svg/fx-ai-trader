"""Session-boundary cross-pair mean reversion signal for Wave 1 BT.

This module is intentionally not registered into production routing.  It is a
pure, parameter-locked signal helper for the W6-MR-Cross Wave 1 feasibility BT.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import pandas as pd


DEFAULT_PARAMS = {
    "pair": "EUR_NZD",
    "window": "NY_LATE",
    "lookback_bars": 20,
    "fade_quantile": 0.10,
    "atr_period": 14,
    "sl_atr_mult": 1.5,
    "tp_atr_mult": 0.5,
    "max_hold_bars": 24,
    "entry_cost_pips": 0.6,
}


@dataclass(frozen=True)
class SessionMrSignal:
    side: str
    entry: float
    sl: float
    tp: float
    deadline: pd.Timestamp
    signal_ts: pd.Timestamp
    entry_ts: pd.Timestamp
    atr: float
    low_q: float
    high_q: float
    friction_pips: float
    friction_source: str


def _norm_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    out = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    required = {"Open", "High", "Low", "Close"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"missing OHLC columns: {sorted(missing)}")
    if not isinstance(out.index, pd.DatetimeIndex):
        out = out.copy()
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out = out.copy()
        out.index = out.index.tz_localize("UTC")
    else:
        out = out.copy()
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def in_session_window(ts: pd.Timestamp, window: str) -> bool:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    hour = ts.hour
    if window == "NY_LATE":
        return 19 <= hour < 23
    if window == "TOKYO_OPEN":
        return hour >= 22 or hour < 2
    raise ValueError(f"unsupported window: {window}")


def atr_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    data = _norm_ohlc(df)
    high = data["High"].astype(float)
    low = data["Low"].astype(float)
    close = data["Close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def friction_cost_pips(pair: str, window: str, hour_utc: int, fallback: float) -> tuple[float, str]:
    session = "NY" if window == "NY_LATE" else "Tokyo"
    try:
        from modules.friction_model_v2 import friction_for

        cost = friction_for(pair, mode="Scalp", session=session, hour_utc=hour_utc)
        value = float(cost.get("adjusted_rt_pips"))
        if value == value and 0 < value < 50:
            return value, "friction_model_v2"
    except Exception:
        pass
    return float(fallback), "params.entry_cost_pips_fallback"


def signal_session_mr_cross(
    df: pd.DataFrame,
    params: Mapping[str, object],
    *,
    signal_index: Optional[int] = None,
) -> Optional[SessionMrSignal]:
    """Return a locked Wave 1 MR signal for one bar, or None.

    `signal_index` points at the completed signal bar.  Entry is always the next
    bar open, so callers must pass data containing at least one following bar.
    """
    cfg = {**DEFAULT_PARAMS, **dict(params)}
    data = _norm_ohlc(df)
    i = len(data) - 2 if signal_index is None else int(signal_index)
    lookback = int(cfg["lookback_bars"])
    atr_period = int(cfg["atr_period"])
    if i < max(lookback, atr_period) or i + 1 >= len(data):
        return None

    ts = data.index[i]
    window = str(cfg["window"])
    if not in_session_window(ts, window):
        return None

    history = data.iloc[i - lookback : i]
    fade_q = float(cfg["fade_quantile"])
    low_q = float(history["Low"].quantile(fade_q))
    high_q = float(history["High"].quantile(1.0 - fade_q))
    atr = float(atr_series(data, atr_period).iloc[i])
    if not (atr == atr and atr > 0):
        return None

    close = float(data.iloc[i]["Close"])
    if close < low_q:
        side = "BUY"
    elif close > high_q:
        side = "SELL"
    else:
        return None

    entry = float(data.iloc[i + 1]["Open"])
    sl_mult = float(cfg["sl_atr_mult"])
    tp_mult = float(cfg["tp_atr_mult"])
    if side == "BUY":
        sl = entry - sl_mult * atr
        tp = entry + tp_mult * atr
    else:
        sl = entry + sl_mult * atr
        tp = entry - tp_mult * atr

    entry_ts = data.index[i + 1]
    deadline = entry_ts + pd.Timedelta(minutes=5 * int(cfg["max_hold_bars"]))
    friction, source = friction_cost_pips(
        str(cfg["pair"]),
        window,
        int(entry_ts.hour),
        float(cfg["entry_cost_pips"]),
    )
    return SessionMrSignal(
        side=side,
        entry=entry,
        sl=float(sl),
        tp=float(tp),
        deadline=deadline,
        signal_ts=ts,
        entry_ts=entry_ts,
        atr=atr,
        low_q=low_q,
        high_q=high_q,
        friction_pips=friction,
        friction_source=source,
    )
