from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from modules.price_shock_grid_db import DDL, connect, replace_cells
from tools import price_shock_reversion_bt as bt


def test_price_shock_db_applies_literal_table(tmp_path):
    db_path = tmp_path / "price_shock.db"
    conn = connect(db_path)
    conn.executescript(DDL)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(price_shock_grid_cells)").fetchall()]
    assert cols[:7] == [
        "cell_id",
        "pair",
        "tf",
        "direction",
        "percentile",
        "horizon_bars",
        "vol_quintile",
    ]
    assert "bh_fdr_pass" in cols
    assert "verdict" in cols


def test_price_shock_stats_for_synthetic_cell_next_bar_open():
    dates = pd.date_range("2025-01-01", periods=320, freq="h", tz="UTC")
    close = [100.0 + i * 0.01 for i in range(320)]
    close[260] = close[259] * 0.98
    close[261] = close[260] * 1.01
    df = pd.DataFrame(
        {
            "Open": close,
            "High": [c * 1.001 for c in close],
            "Low": [c * 0.999 for c in close],
            "Close": close,
        },
        index=dates,
    )
    loaded = bt.LoadedFrame(pair="EUR_USD", tf="H1", df=df, source_path=Path("synthetic.parquet"))
    rows = bt.compute_grid_for_frame(loaded, "2026-05-15T00:00:00+00:00")
    target = [
        row
        for row in rows
        if row["direction"] == "LONG_SHOCK"
        and row["percentile"] == 0.01
        and row["horizon_bars"] == 1
        and row["vol_quintile"] == "ALL"
    ][0]
    assert target["n_trades"] >= 1
    assert target["cell_id"] == "EUR_USD_H1_LONG_SHOCK_1_1_ALL"


def test_price_shock_integration_uses_real_massive_parquet():
    cache_dir = Path("data/cache/massive")
    parquet = cache_dir / "USD_JPY_1h.parquet"
    assert parquet.exists(), "real MASSIVE parquet is required; mock-only test is forbidden"
    loaded = bt.load_frame(cache_dir, "USD_JPY", "H1")
    assert loaded is not None
    assert loaded.source_path == parquet
    assert len(loaded.df) > bt.ROLLING_WINDOW["H1"] + max(bt.HORIZONS) + 1
    rows = bt.compute_grid_for_frame(loaded, "2026-05-15T00:00:00+00:00")
    assert len(rows) == len(bt.PERCENTILES) * len(bt.DIRECTIONS) * len(bt.HORIZONS) * len(bt.VOL_BUCKETS)
    assert {row["bt_data_source"] for row in rows} == {"MASSIVE_parquet"}


def test_price_shock_db_replace_cells_round_trip(tmp_path):
    row = bt.empty_cell(
        pair="USD_JPY",
        tf="H1",
        direction="LONG_SHOCK",
        pct=0.01,
        horizon=1,
        vol_q="ALL",
        period_start="2025-01-01T00:00:00+00:00",
        period_end="2025-12-31T00:00:00+00:00",
        generated_at="2026-05-15T00:00:00+00:00",
    )
    with connect(tmp_path / "cells.db") as conn:
        assert replace_cells(conn, [row]) == 1
        got = conn.execute("SELECT cell_id, verdict FROM price_shock_grid_cells").fetchone()
    assert tuple(got) == ("USD_JPY_H1_LONG_SHOCK_1_1_ALL", "REJECT")
