"""Parquet candle cache + OANDA v20 history paginator.

Cache key components: (instrument, timeframe, start_iso, end_iso, source).
Two files with the same key collide; that's intentional — callers should treat
the file as the canonical snapshot for that exact window.

The paginator is pure planning: it returns a list of (start, end) tuples
that fit the OANDA v20 candle count cap (~500 per request). The actual HTTP
calls live in OandaClient.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

GRANULARITY_SECONDS: dict[str, int] = {
    "S5":  5,
    "S10": 10,
    "S15": 15,
    "S30": 30,
    "M1":  60,
    "M2":  120,
    "M5":  300,
    "M15": 900,
    "M30": 1800,
    "H1":  3600,
    "H4":  14400,
    "D":   86400,
}


def cache_path(
    base_dir: Path,
    *,
    instrument: str,
    tf: str,
    start_iso: str,
    end_iso: str,
    source: str,
) -> Path:
    safe_start = start_iso.replace(":", "").replace("-", "")
    safe_end   = end_iso.replace(":", "").replace("-", "")
    name = f"{source}_{instrument}_{tf}_{safe_start}_{safe_end}.parquet"
    return base_dir / name


def write_parquet_candles(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def read_parquet_candles(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "time" in df.columns and df["time"].dtype.kind != "M":
        df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def plan_oanda_windows(
    *,
    start: datetime,
    end: datetime,
    granularity: str,
    chunk_size: int = 500,
) -> list[tuple[datetime, datetime]]:
    if granularity not in GRANULARITY_SECONDS:
        raise ValueError(f"unsupported granularity: {granularity}")
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start/end must be timezone-aware")
    if end <= start:
        raise ValueError("end must be after start")

    chunk_seconds = GRANULARITY_SECONDS[granularity] * chunk_size
    delta = timedelta(seconds=chunk_seconds)
    windows: list[tuple[datetime, datetime]] = []
    cur = start
    while cur < end:
        nxt = cur + delta
        windows.append((cur, nxt))
        cur = nxt
    return windows
