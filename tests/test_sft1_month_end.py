from __future__ import annotations

import pandas as pd
import pytest

from tools.bt.sft1_month_end_usd_rebalance import (
    MONTH_GRID,
    PRIMARY_CELL,
    assert_locked_grid,
    run_month_end_cell,
)
from tools.data.build_structural_events import build_structural_events


def _bars(start: str, end: str) -> pd.DataFrame:
    idx = pd.date_range(start, end, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": 150.0, "high": 150.0, "low": 150.0, "close": 150.0}, index=idx)
    df.loc[pd.Timestamp("2024-01-31 16:30", tz="UTC"), "close"] = 149.50
    return df


def test_month_end_calendar_row_count_smoke() -> None:
    df = build_structural_events("2014-01-01", "2026-04-30")
    assert len(df) == 4503
    assert df["month_end_us"].sum() == 148


def test_month_end_setup_detection_uses_us_business_month_end() -> None:
    calendar = build_structural_events("2024-01-01", "2024-01-31")
    trades = run_month_end_cell(calendar, {"USDJPY": _bars("2024-01-31 15:00", "2024-01-31 17:00")}, PRIMARY_CELL, 1.0)
    assert len(trades) == 1
    assert trades[0].event_date == "2024-01-31"


def test_month_end_entry_exit_timing_primary_cell() -> None:
    calendar = build_structural_events("2024-01-01", "2024-01-31")
    trade = run_month_end_cell(calendar, {"USDJPY": _bars("2024-01-31 15:00", "2024-01-31 17:00")}, PRIMARY_CELL, 1.0)[0]
    assert trade.entry_ts_utc == pd.Timestamp("2024-01-31 15:30", tz="UTC")
    assert trade.exit_ts_utc == pd.Timestamp("2024-01-31 16:30", tz="UTC")


def test_month_end_locked_grid_tamper_guard() -> None:
    with pytest.raises(AssertionError):
        assert_locked_grid({"entry_offset_min": -25, "exit_min": 60}, MONTH_GRID)


def test_month_end_weekend_excluded_from_month_end_us() -> None:
    calendar = build_structural_events("2024-08-01", "2024-08-31")
    assert not bool(calendar.loc[calendar["date_utc"] == pd.Timestamp("2024-08-31", tz="UTC"), "month_end_us"].iloc[0])
    assert bool(calendar.loc[calendar["date_utc"] == pd.Timestamp("2024-08-30", tz="UTC"), "month_end_us"].iloc[0])
