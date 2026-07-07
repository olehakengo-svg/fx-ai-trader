from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from tools import hourly_bias_bt as bt


def _synthetic_frame() -> pd.DataFrame:
    idx = pd.date_range("2025-01-06 00:00", periods=7 * 24 * 12, freq="5min", tz="UTC")
    rows = []
    price = 150.0
    for ts in idx:
        open_ = price
        close = open_ + (0.002 if ts.hour == 11 and ts.weekday() == 0 else -0.0002)
        rows.append({"Open": open_, "High": max(open_, close) + 0.001, "Low": min(open_, close) - 0.001, "Close": close})
        price = close
    return pd.DataFrame(rows, index=idx)


def test_cell_grid_is_240():
    assert len(list(bt.iter_cells())) == 240
    assert bt.ALPHA == 0.05 / 240


def test_hourly_trades_are_weekday_cohorted_once_per_day_hour():
    trades = bt.hourly_trades(_synthetic_frame())
    target = [t for t in trades if t["hour"] == 11 and t["weekday"] == 0]
    assert len(target) == 1
    assert target[0]["bar_count"] == 12
    assert target[0]["long_pip"] > target[0]["short_pip"]


def test_family_a_stats_for_synthetic_hour_cell():
    rows, trade_map = bt.family_a_rows(bt.hourly_trades(_synthetic_frame()))
    row = [r for r in rows if r["cell_id"] == "h11_Mon_long"][0]
    assert row["n"] == 1
    assert row["mean_pip"] > 0
    assert math.isfinite(row["p_value"])
    assert trade_map[row["cell_id"]][0]["net_pip"] == row["mean_pip"]


def test_real_massive_usdjpy_m5_loads():
    from tests.conftest import require_data_file
    require_data_file("data/cache/massive/USD_JPY_5m.parquet", "MASSIVE M5 integration")
    df, source = bt.load_frame()
    assert source in bt.DATA_CANDIDATES
    assert Path(source).exists()
    assert len(df) > 100_000
    assert df.index.tz is not None
