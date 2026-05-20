from __future__ import annotations

from pathlib import Path

import pandas as pd

from modules.bigbeluga_grid_db import DDL, connect, replace_cells
from tools import bigbeluga_displacement_delta_bt as bt


def test_bigbeluga_db_applies_literal_table(tmp_path):
    conn = connect(tmp_path / "bigbeluga.db")
    conn.executescript(DDL)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(bigbeluga_disp_delta_cells)").fetchall()]
    assert cols[:9] == [
        "cell_id",
        "pair",
        "tf",
        "intrabar_tf",
        "hypothesis",
        "vol_mult",
        "body_pct",
        "horizon_bars",
        "cohort",
    ]
    assert "g7_delta_incremental" in cols
    assert "bt_data_source" in cols


def test_h1_features_use_prior_volume_sma_and_intrabar_delta():
    idx = pd.date_range("2025-01-01 00:00", periods=22 * 12, freq="5min", tz="UTC")
    rows = []
    for i, ts in enumerate(idx):
        hour = i // 12
        base = 100.0 + hour * 0.01
        if hour == 21:
            open_ = base
            close = base + 0.02 if i % 2 == 0 else base - 0.01
            volume = 12.0 if i % 2 == 0 else 4.0
        else:
            open_ = base
            close = base + 0.001
            volume = 5.0
        rows.append({"Open": open_, "High": max(open_, close) + 0.001, "Low": min(open_, close) - 0.001, "Close": close, "Volume": volume})
    h1 = bt.build_h1_features(pd.DataFrame(rows, index=idx))
    assert len(h1) == 22
    assert h1["avgVol20_prior"].iloc[20] == 60.0
    assert h1["avgVol20_prior"].iloc[21] == 60.0
    assert h1["deltaRatio"].iloc[21] > 0.0


def test_stats_entry_is_next_h1_open_and_exit_is_t_plus_one_plus_horizon():
    idx = pd.date_range("2025-01-01", periods=40, freq="h", tz="UTC")
    h1 = pd.DataFrame(
        {
            "Open": [100.0] * 40,
            "High": [101.0] * 40,
            "Low": [99.0] * 40,
            "Close": [100.0] * 40,
            "Volume": [100.0] * 40,
            "buyVol": [60.0] * 40,
            "sellVol": [40.0] * 40,
            "n_m5": [12] * 40,
            "deltaRatio": [0.2] * 40,
            "avgVol20_prior": [100.0] * 40,
            "bodyRatio": [0.6] * 40,
            "bullBody": [True] * 40,
            "bearBody": [False] * 40,
        },
        index=idx,
    )
    h1.loc[idx[11], "Open"] = 111.0
    h1.loc[idx[13], "Close"] = 112.0
    row = bt.stats_for_cell(
        h1=h1,
        idx=pd.Index([10]).to_numpy(),
        side=pd.Index([1]).to_numpy(),
        pair="USD_JPY",
        hypothesis="H-A",
        vol_mult=2.0,
        body_pct=0.50,
        horizon=2,
        cohort="primary_12y",
        period_start=idx[0].isoformat(),
        period_end=idx[-1].isoformat(),
        generated_at="2026-05-20T00:00:00+00:00",
    )
    assert row["n_trades"] == 1
    assert round(row["ev_pip"], 6) == 100.0


def test_bigbeluga_integration_uses_real_massive_m5_parquet():
    cache_dir = Path("data/cache/massive")
    parquet = cache_dir / "USD_JPY_5m.parquet"
    assert parquet.exists(), "real MASSIVE M5 parquet is required; mock-only test is forbidden"
    loaded = bt.load_m5(cache_dir, "USD_JPY")
    assert loaded.source_path == parquet
    assert loaded.schema == "lower"
    assert len(loaded.df) > 100_000
    rows = bt.compute_grid_for_loaded(loaded, "secondary_1y", "2026-05-20T00:00:00+00:00")
    assert len(rows) == len(bt.VOL_MULTS_SECONDARY) * len(bt.BODY_PCTS_SECONDARY) * len(bt.HYPOTHESES) * len(bt.HORIZONS)
    assert {row["bt_data_source"] for row in rows} == {"MASSIVE_parquet"}
    assert all(row["tf"] == "H1" and row["intrabar_tf"] == "M5" for row in rows)


def test_bigbeluga_db_replace_cells_round_trip(tmp_path):
    row = bt.empty_cell(
        pair="USD_JPY",
        hypothesis="H-C",
        vol_mult=2.0,
        body_pct=0.50,
        horizon=1,
        cohort="primary_12y",
        period_start="2025-01-01T00:00:00+00:00",
        period_end="2025-12-31T00:00:00+00:00",
        generated_at="2026-05-20T00:00:00+00:00",
    )
    with connect(tmp_path / "cells.db") as conn:
        assert replace_cells(conn, [row]) == 1
        got = conn.execute("SELECT cell_id, verdict, bt_data_source FROM bigbeluga_disp_delta_cells").fetchone()
    assert tuple(got) == ("USD_JPY_H-C_2_0.50_1", "REJECT", "MASSIVE_parquet")
