from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools import vol_exhaustion_fade_bt as bt


def test_family_a_synthetic_extreme_fade_hits_tp(tmp_path):
    idx = pd.date_range("2026-01-01", periods=40, freq="5min", tz="UTC")
    rows = []
    price = 150.0
    for i in range(40):
        open_ = price
        close = price + 0.001
        high = max(open_, close) + 0.002
        low = min(open_, close) - 0.002
        rows.append({"Open": open_, "High": high, "Low": low, "Close": close})
        price = close
    rows[25] = {"Open": 150.025, "High": 150.030, "Low": 149.965, "Close": 149.970}
    rows[26] = {"Open": 149.970, "High": 150.020, "Low": 149.960, "Close": 150.015}
    df = bt.add_family_a_columns(pd.DataFrame(rows, index=idx))

    signals = bt.family_a_signal_indices(df, 3.0, "ALL")
    assert 25 in signals
    trades = bt.simulate_trades(df, [25], 3, bt.FAMILY_A)

    assert len(trades) == 1
    assert trades[0].direction == "BUY"
    assert trades[0].exit_reason == "TP"


def test_stats_gates_and_wf_shape_for_synthetic_cell():
    trades = [
        bt.Trade(i, i, i + 1, f"t{i}", f"t{i+1}", "BUY", pnl, pnl + bt.ROUND_TRIP_SPREAD_PIP, "TIME")
        for i, pnl in enumerate([3.0] * 12 + [-1.0] * 3 + [2.0] * 12 + [-0.5] * 3 + [1.5] * 12)
    ]
    row = bt.stats_for_cell(
        family=bt.FAMILY_A,
        k=3.0,
        horizon=3,
        session="ALL",
        trades=trades,
        period_start="2026-01-01T00:00:00+00:00",
        period_end="2026-01-02T00:00:00+00:00",
        generated_at="2026-05-15T00:00:00+00:00",
        source_path=Path("data/cache/massive/USD_JPY_5m.parquet"),
    )
    bt.bh_adjust([row])
    row["verdict"] = bt.classify(row)

    assert row["n"] == 42
    assert len(row["wf"]) == 3
    assert row["gates"]["G1_N"]
    assert row["gates"]["G3_EV"]


def test_integration_uses_real_massive_usdjpy_m5_parquet():
    cache_dir = Path("data/cache/massive")
    parquet = cache_dir / "USD_JPY_5m.parquet"
    assert parquet.exists(), "real MASSIVE parquet is required; mock-only test is forbidden"
    df, source_path = bt.load_usdjpy_m5(cache_dir)
    assert source_path == parquet
    assert len(df) > 100_000
    assert df.index.min().year <= 2014
    df_a = bt.add_family_a_columns(df)
    rows, _ = bt.compute_family_grid(df_a, source_path, bt.FAMILY_A, "2026-05-15T00:00:00+00:00")
    assert len(rows) == len(bt.K_VALUES) * len(bt.H_BARS) * len(bt.SESSIONS)
    assert {row["bt_data_source"] for row in rows} == {bt.DATA_SOURCE}
