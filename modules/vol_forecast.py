"""HAR-RV realized-volatility forecast utilities.

This module intentionally avoids live data access. The only I/O path is the
optional local parquet cache used by ``vol_forecast_mult``.
"""

from __future__ import annotations

import os
import pickle
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

_VOL_FORECAST_CACHE: dict[tuple[Any, ...], float] = {}
_CACHE_STATS = {"hits": 0, "misses": 0}

_INSTRUMENT_ALIASES = {
    "USDJPY=X": "USD_JPY",
    "JPY=X": "USD_JPY",
    "USDJPY": "USD_JPY",
    "USD_JPY": "USD_JPY",
    "EURUSD=X": "EUR_USD",
    "EURUSD": "EUR_USD",
    "EUR_USD": "EUR_USD",
    "EURJPY=X": "EUR_JPY",
    "EURJPY": "EUR_JPY",
    "EUR_JPY": "EUR_JPY",
    "GBPUSD=X": "GBP_USD",
    "GBPUSD": "GBP_USD",
    "GBP_USD": "GBP_USD",
    "GBPJPY=X": "GBP_JPY",
    "GBPJPY": "GBP_JPY",
    "GBP_JPY": "GBP_JPY",
    "EURGBP=X": "EUR_GBP",
    "EURGBP": "EUR_GBP",
    "EUR_GBP": "EUR_GBP",
}

_TIMEFRAME_TO_RULE = {
    "M5": "5min",
    "5M": "5min",
    "5MIN": "5min",
    "5m": "5min",
    "H1": "1h",
    "1H": "1h",
    "1h": "1h",
    "D1": "1D",
    "1D": "1D",
    "1d": "1D",
}

_TIMEFRAME_TO_SUFFIX = {
    "M5": "5m",
    "5M": "5m",
    "5MIN": "5m",
    "5m": "5m",
    "H1": "1h",
    "1H": "1h",
    "1h": "1h",
    "D1": "1d",
    "1D": "1d",
    "1d": "1d",
}


def clear_vol_forecast_cache() -> None:
    """Clear process-local forecast cache and stats."""
    _VOL_FORECAST_CACHE.clear()
    _CACHE_STATS["hits"] = 0
    _CACHE_STATS["misses"] = 0


def get_vol_forecast_cache_stats() -> dict[str, int]:
    """Return process-local cache hit/miss counters."""
    return dict(_CACHE_STATS)


def realized_vol_from_returns(returns: pd.Series, window: int) -> pd.Series:
    """Compute realized volatility as sqrt(sum(r^2)) over a rolling window."""
    if window <= 0:
        raise ValueError("window must be positive")
    numeric = pd.to_numeric(returns, errors="coerce").astype(float)
    rv = np.sqrt(numeric.pow(2).rolling(window=window, min_periods=window).sum())
    return rv.dropna()


def _clean_rv(rv_series: pd.Series) -> pd.Series:
    rv = pd.to_numeric(rv_series, errors="coerce").astype(float)
    rv = rv.replace([np.inf, -np.inf], np.nan).dropna()
    return rv[rv > 0]


def _har_design(rv_series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    rv = _clean_rv(rv_series)
    daily = rv.shift(1)
    weekly = rv.shift(1).rolling(window=5, min_periods=5).mean()
    monthly = rv.shift(1).rolling(window=22, min_periods=22).mean()
    frame = pd.DataFrame(
        {
            "y": rv,
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly,
        }
    ).dropna()
    if len(frame) < 4:
        raise ValueError("insufficient HAR-RV observations")
    x = np.column_stack(
        [
            np.ones(len(frame)),
            frame["daily"].to_numpy(dtype=float),
            frame["weekly"].to_numpy(dtype=float),
            frame["monthly"].to_numpy(dtype=float),
        ]
    )
    y = frame["y"].to_numpy(dtype=float)
    return x, y


def fit_har_rv(rv_series: pd.Series) -> dict[str, float]:
    """Estimate HAR-RV beta0, beta_d, beta_w, beta_m using OLS."""
    x, y = _har_design(rv_series)
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    return {
        "beta0": float(beta[0]),
        "beta_d": float(beta[1]),
        "beta_w": float(beta[2]),
        "beta_m": float(beta[3]),
    }


def _as_utc_timestamp(value: datetime | pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts


def _guard_closed_bar(params: dict[str, float], rv_history: pd.Series) -> None:
    asof_ts = params.get("_asof_ts")
    if asof_ts is None or len(rv_history) == 0:
        return
    if not isinstance(rv_history.index, pd.DatetimeIndex):
        return
    last = _as_utc_timestamp(rv_history.index[-1])
    asof = pd.Timestamp(float(asof_ts), unit="s", tz="UTC")
    if last >= asof:
        raise ValueError(
            "closed-bar violation: rv_history contains bars at or after asof_utc"
        )


def predict_har_rv(params: dict[str, float], rv_history: pd.Series) -> float:
    """Return a one-step-ahead sigma forecast from closed-bar RV history."""
    _guard_closed_bar(params, rv_history)
    rv = _clean_rv(rv_history)
    if len(rv) < 22:
        return 1.0
    daily = float(rv.iloc[-1])
    weekly = float(rv.iloc[-5:].mean())
    monthly = float(rv.iloc[-22:].mean())
    forecast = (
        float(params.get("beta0", 0.0))
        + float(params.get("beta_d", 0.0)) * daily
        + float(params.get("beta_w", 0.0)) * weekly
        + float(params.get("beta_m", 0.0)) * monthly
    )
    if not np.isfinite(forecast) or forecast <= 0:
        return 1.0
    return float(forecast)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_parquet(path: Path) -> pd.DataFrame:
    try:
        return pd.read_parquet(path)
    except ImportError as exc:
        venv_python = _repo_root() / ".venv" / "bin" / "python"
        if not venv_python.exists() or Path(sys.executable).absolute() == venv_python.absolute():
            raise
        code = (
            "import pickle, sys; "
            "import pandas as pd; "
            "df = pd.read_parquet(sys.argv[1]); "
            "idx = pd.DatetimeIndex(df.index); "
            "idx = idx.tz_localize('UTC') if idx.tz is None else idx.tz_convert('UTC'); "
            "payload = {'columns': list(df.columns), 'index_ns': idx.view('int64'), "
            "'data': df.to_numpy(dtype='float64')}; "
            "sys.stdout.buffer.write(pickle.dumps(payload, protocol=4))"
        )
        proc = subprocess.run(
            [str(venv_python), "-c", code, str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise exc
        payload = pickle.loads(proc.stdout)
        index = pd.to_datetime(payload["index_ns"], utc=True)
        return pd.DataFrame(payload["data"], columns=payload["columns"], index=index)


def _normalize_instrument(instrument: str) -> str:
    return _INSTRUMENT_ALIASES.get(instrument, instrument.replace("/", "_").upper())


def _normalize_timeframe(timeframe: str) -> str:
    tf = timeframe.strip()
    if tf not in _TIMEFRAME_TO_RULE:
        tf = tf.upper()
    if tf not in _TIMEFRAME_TO_RULE:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    return tf


def _normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    if not isinstance(renamed.index, pd.DatetimeIndex):
        renamed.index = pd.to_datetime(renamed.index, utc=True)
    elif renamed.index.tz is None:
        renamed.index = renamed.index.tz_localize("UTC")
    else:
        renamed.index = renamed.index.tz_convert("UTC")
    return renamed.sort_index().dropna(subset=["Close"])


def load_cached_ohlcv(
    instrument: str,
    timeframe: str,
    *,
    cache_dir: str | None = None,
) -> pd.DataFrame:
    """Load local cached OHLCV, resampling from M5 when higher TF files are absent."""
    norm_instrument = _normalize_instrument(instrument)
    norm_tf = _normalize_timeframe(timeframe)
    suffix = _TIMEFRAME_TO_SUFFIX[norm_tf]
    base_dir = Path(cache_dir) if cache_dir else _repo_root() / "data" / "cache" / "massive"

    path = base_dir / f"{norm_instrument}_{suffix}.parquet"
    if path.exists():
        return _normalize_ohlcv_columns(_read_parquet(path))

    m5_path = base_dir / f"{norm_instrument}_5m.parquet"
    if not m5_path.exists():
        raise FileNotFoundError(f"no local cache for {norm_instrument} {timeframe}")
    m5 = _normalize_ohlcv_columns(_read_parquet(m5_path))
    if suffix == "5m":
        return m5
    rule = _TIMEFRAME_TO_RULE[norm_tf]
    return (
        m5.resample(rule)
        .agg(
            Open=("Open", "first"),
            High=("High", "max"),
            Low=("Low", "min"),
            Close=("Close", "last"),
            Volume=("Volume", "sum"),
        )
        .dropna(subset=["Open", "High", "Low", "Close"])
    )


def _history_to_rv(df: pd.DataFrame, asof_utc: datetime, window: int = 22) -> pd.Series:
    asof = _as_utc_timestamp(asof_utc)
    closed = df[df.index < asof]
    if len(closed) < window + 2:
        return pd.Series(dtype=float)
    close = pd.to_numeric(closed["Close"], errors="coerce").astype(float)
    returns = np.log(close).diff().dropna()
    return realized_vol_from_returns(returns, window=window)


def vol_forecast_mult(
    instrument: str,
    timeframe: str,
    asof_utc: datetime,
    *,
    target_realized_vol: float | None = None,
    floor: float = 0.30,
    ceiling: float = 1.50,
    cache_dir: str | None = None,
) -> float:
    """Return clipped target-vol/forecast-vol multiplier from local cached OHLCV."""
    if floor <= 0 or ceiling <= 0 or floor > ceiling:
        raise ValueError("floor and ceiling must be positive with floor <= ceiling")

    asof = _as_utc_timestamp(asof_utc).floor("min")
    cache_key = (
        _normalize_instrument(instrument),
        _normalize_timeframe(timeframe),
        asof.isoformat(),
        None if target_realized_vol is None else round(float(target_realized_vol), 12),
        float(floor),
        float(ceiling),
        os.path.abspath(cache_dir) if cache_dir else None,
    )
    if cache_key in _VOL_FORECAST_CACHE:
        _CACHE_STATS["hits"] += 1
        return _VOL_FORECAST_CACHE[cache_key]
    _CACHE_STATS["misses"] += 1

    df = load_cached_ohlcv(instrument, timeframe, cache_dir=cache_dir)
    rv = _history_to_rv(df, asof.to_pydatetime())
    if len(rv) < 60:
        multiplier = 1.0
    else:
        params = fit_har_rv(rv)
        params["_asof_ts"] = float(asof.timestamp())
        forecast = predict_har_rv(params, rv)
        if forecast == 1.0:
            multiplier = 1.0
        else:
            target = (
                float(target_realized_vol)
                if target_realized_vol is not None
                else float(rv.iloc[-252:].median())
            )
            if not np.isfinite(target) or target <= 0:
                multiplier = 1.0
            else:
                multiplier = float(np.clip(target / forecast, floor, ceiling))

    _VOL_FORECAST_CACHE[cache_key] = float(multiplier)
    return float(multiplier)
