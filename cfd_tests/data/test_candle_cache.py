"""candle_cache: parquet round-trip + OANDA paginator chunk math."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from cfd_trader.data.candle_cache import (
    cache_path,
    read_parquet_candles,
    write_parquet_candles,
    plan_oanda_windows,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": pd.to_datetime(
                ["2026-05-01T00:00:00Z", "2026-05-01T00:05:00Z"], utc=True
            ),
            "open":   [5000.0, 5001.0],
            "high":   [5005.0, 5002.0],
            "low":    [4998.0, 5000.0],
            "close":  [5001.0, 5001.5],
            "volume": [123, 45],
            "complete": [True, False],
        }
    )


def test_cache_path_is_deterministic(tmp_path: Path) -> None:
    p1 = cache_path(
        tmp_path, instrument="SPX500_USD", tf="M5",
        start_iso="2026-05-01", end_iso="2026-05-02", source="oanda",
    )
    p2 = cache_path(
        tmp_path, instrument="SPX500_USD", tf="M5",
        start_iso="2026-05-01", end_iso="2026-05-02", source="oanda",
    )
    assert p1 == p2
    assert p1.suffix == ".parquet"
    assert "SPX500_USD" in p1.name
    assert "M5" in p1.name


def test_parquet_round_trip_preserves_columns_and_dtypes(
    tmp_path: Path, sample_df: pd.DataFrame
) -> None:
    p = cache_path(
        tmp_path, instrument="SPX500_USD", tf="M5",
        start_iso="2026-05-01", end_iso="2026-05-02", source="oanda",
    )
    write_parquet_candles(p, sample_df)
    out = read_parquet_candles(p)
    assert list(out.columns) == list(sample_df.columns)
    assert len(out) == len(sample_df)
    assert out["time"].dtype.kind == "M"


def test_plan_oanda_windows_splits_90_days_M5_into_chunks_of_500() -> None:
    start = datetime(2026, 2, 11, 0, 0, 0, tzinfo=timezone.utc)
    end   = datetime(2026, 5, 11, 0, 0, 0, tzinfo=timezone.utc)
    windows = plan_oanda_windows(start=start, end=end, granularity="M5", chunk_size=500)
    # Expected: ~25,920 bars / 500 ~= 52 windows. Allow +/-1 for boundary effects.
    assert 50 <= len(windows) <= 55
    # First window starts at `start`.
    assert windows[0][0] == start
    # Windows are contiguous and non-overlapping.
    for prev, nxt in zip(windows, windows[1:]):
        assert nxt[0] == prev[1]
    # Last window ends at or after `end`.
    assert windows[-1][1] >= end


def test_plan_oanda_windows_handles_short_range() -> None:
    start = datetime(2026, 5, 11, 0, 0, 0, tzinfo=timezone.utc)
    end   = datetime(2026, 5, 11, 1, 0, 0, tzinfo=timezone.utc)  # 12 M5 bars
    windows = plan_oanda_windows(start=start, end=end, granularity="M5", chunk_size=500)
    assert len(windows) == 1
    assert windows[0][0] == start
    assert windows[0][1] >= end
