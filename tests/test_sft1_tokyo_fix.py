from __future__ import annotations

import pandas as pd
import pytest

from tools.bt.sft1_month_end_usd_rebalance import assert_locked_grid
from tools.bt.sft1_tokyo_fix_955 import PRIMARY_CELL, TOKYO_GRID, run_tokyo_fix_cell
from tools.data.build_structural_events import build_structural_events


def _bars(start: str, end: str) -> pd.DataFrame:
    idx = pd.date_range(start, end, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": 150.0, "high": 150.0, "low": 150.0, "close": 150.0}, index=idx)
    df.loc[pd.Timestamp("2024-01-04 01:25", tz="UTC"), "close"] = 149.80
    return df


def test_tokyo_fix_setup_detection_uses_jp_business_day() -> None:
    calendar = build_structural_events("2024-01-04", "2024-01-04")
    trades = run_tokyo_fix_cell(calendar, {"USDJPY": _bars("2024-01-04 00:00", "2024-01-04 02:00")}, PRIMARY_CELL, 1.0)
    assert len(trades) == 1
    assert trades[0].event_date == "2024-01-04"


def test_tokyo_fix_entry_exit_timing_primary_cell() -> None:
    calendar = build_structural_events("2024-01-04", "2024-01-04")
    trade = run_tokyo_fix_cell(calendar, {"USDJPY": _bars("2024-01-04 00:00", "2024-01-04 02:00")}, PRIMARY_CELL, 1.0)[0]
    assert trade.entry_ts_utc == pd.Timestamp("2024-01-04 00:25", tz="UTC")
    assert trade.exit_ts_utc == pd.Timestamp("2024-01-04 01:25", tz="UTC")


def test_tokyo_fix_locked_grid_tamper_guard() -> None:
    with pytest.raises(AssertionError):
        assert_locked_grid({"entry_offset_min": -30, "exit_min": 75}, TOKYO_GRID)


def test_tokyo_fix_holiday_and_weekend_excluded() -> None:
    calendar = build_structural_events("2024-01-01", "2024-01-07")
    bars = _bars("2024-01-01 00:00", "2024-01-07 02:00")
    trades = run_tokyo_fix_cell(calendar, {"USDJPY": bars}, PRIMARY_CELL, 1.0)
    dates = {t.event_date for t in trades}
    assert "2024-01-01" not in dates
    assert "2024-01-06" not in dates
    assert "2024-01-04" in dates
