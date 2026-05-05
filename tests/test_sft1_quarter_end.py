from __future__ import annotations

import pandas as pd
import pytest

from tools.bt.sft1_month_end_usd_rebalance import assert_locked_grid
from tools.bt.sft1_quarter_end_jpy_repat import (
    PRIMARY_CELL,
    QUARTER_GRID,
    _last_jp_business_days,
    run_quarter_end_cell,
)
from tools.data.build_structural_events import build_structural_events


def _bars(start: str, end: str) -> pd.DataFrame:
    idx = pd.date_range(start, end, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": 150.0, "high": 150.0, "low": 150.0, "close": 150.0}, index=idx)
    df.loc[pd.Timestamp("2024-03-29 17:00", tz="UTC"), "close"] = 149.00
    return df


def test_quarter_end_setup_detection_uses_mar_sep_jp_month_end() -> None:
    calendar = build_structural_events("2024-03-01", "2024-03-31")
    trades = run_quarter_end_cell(calendar, {"USDJPY": _bars("2024-03-20", "2024-03-29 18:00")}, PRIMARY_CELL, 1.0)
    assert len(trades) == 1
    assert trades[0].event_date == "2024-03-29"


def test_quarter_end_entry_exit_timing_primary_cell() -> None:
    calendar = build_structural_events("2024-03-01", "2024-03-31")
    trade = run_quarter_end_cell(calendar, {"USDJPY": _bars("2024-03-20", "2024-03-29 18:00")}, PRIMARY_CELL, 1.0)[0]
    assert trade.entry_ts_utc == pd.Timestamp("2024-03-25 00:00", tz="UTC")
    assert trade.exit_ts_utc == pd.Timestamp("2024-03-29 17:00", tz="UTC")


def test_quarter_end_locked_grid_tamper_guard() -> None:
    with pytest.raises(AssertionError):
        assert_locked_grid({"entry_days": 4, "exit_hour_utc": 17}, QUARTER_GRID)


def test_quarter_end_holiday_weekend_excluded_from_entry_window() -> None:
    calendar = build_structural_events("2024-03-01", "2024-03-31")
    days = _last_jp_business_days(calendar, pd.Timestamp("2024-03-29", tz="UTC"), 5)
    iso_days = [d.date().isoformat() for d in days]
    assert "2024-03-20" not in iso_days
    assert "2024-03-23" not in iso_days
    assert iso_days == ["2024-03-25", "2024-03-26", "2024-03-27", "2024-03-28", "2024-03-29"]
