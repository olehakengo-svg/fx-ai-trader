"""Phase-0 literal H1 regime classifier for regime-gate audits."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "massive"
REGIMES = ("TRENDING", "RANGING", "CHOP")


def _pair_key(instrument: str) -> str:
    value = instrument.upper().replace("/", "_").replace("-", "_")
    if value.endswith("=X"):
        value = value[:-2]
    value = value.replace("_", "")
    if len(value) == 6:
        return f"{value[:3]}_{value[3:]}"
    return value


def _cache_path(instrument: str) -> Path:
    return CACHE_DIR / f"{_pair_key(instrument)}_1h.parquet"


def _to_utc_timestamp(ts: pd.Timestamp) -> pd.Timestamp:
    out = pd.Timestamp(ts)
    if out.tzinfo is None:
        return out.tz_localize("UTC")
    return out.tz_convert("UTC")


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {c: c.lower() for c in df.columns}
    out = df.rename(columns=renamed)
    required = {"high", "low", "close"}
    if not required.issubset(out.columns):
        missing = ",".join(sorted(required - set(out.columns)))
        raise ValueError(f"missing OHLC columns: {missing}")
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def _wilder_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_smoothed = plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    minus_smoothed = minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    plus_di = 100 * plus_smoothed / atr.replace(0, pd.NA)
    minus_di = 100 * minus_smoothed / atr.replace(0, pd.NA)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _efficiency_ratio(close: pd.Series, lookback: int = 20) -> pd.Series:
    direction = (close - close.shift(lookback)).abs()
    volatility = close.diff().abs().rolling(lookback).sum()
    return direction / volatility.replace(0, pd.NA)


def _bb_width(close: pd.Series, period: int = 20, n_std: float = 2.0) -> pd.Series:
    mid = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    upper = mid + n_std * std
    lower = mid - n_std * std
    return (upper - lower) / mid.replace(0, pd.NA)


def _classify_frame(df: pd.DataFrame) -> str | None:
    data = _normalize_ohlc(df)
    if len(data) < 21:
        return None

    close = data["close"].astype(float)
    adx = _wilder_adx(data, 14).iloc[-1]
    er = _efficiency_ratio(close, 20).iloc[-1]
    _ = _bb_width(close, 20, 2.0).iloc[-1]

    if pd.isna(adx) or pd.isna(er):
        return None
    adx = float(adx)
    er = float(er)

    if adx >= 25.0 and er >= 0.30:
        return "TRENDING"
    if adx < 20.0 and er < 0.20:
        return "RANGING"
    return "CHOP"


def classify_regime(instrument: str, ts: pd.Timestamp) -> str | None:
    """Classify the H1 regime at ``ts`` from local MASSIVE parquet cache."""

    path = _cache_path(instrument)
    if not path.exists():
        return None
    try:
        df = _normalize_ohlc(pd.read_parquet(path))
    except Exception:
        return None

    asof = _to_utc_timestamp(pd.Timestamp(ts))
    window = df[df.index <= asof].tail(80)
    if len(window) < 21:
        return None
    return _classify_frame(window)
