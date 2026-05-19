from __future__ import annotations

from pathlib import Path

import pandas as pd

from tools import highvol_continuation_bt as bt


def test_family_a_synthetic_extreme_continuation_time_exit():
    idx = pd.date_range("2026-01-01 09:00", periods=40, freq="5min", tz="UTC")
    rows = []
    price = 150.0
    for _ in range(40):
        open_ = price
        close = price + 0.001
        high = max(open_, close) + 0.001
        low = min(open_, close) - 0.001
        rows.append({"Open": open_, "High": high, "Low": low, "Close": close})
        price = close
    rows[25] = {"Open": 150.025, "High": 150.082, "Low": 150.024, "Close": 150.080}
    rows[28] = {"Open": 150.082, "High": 150.095, "Low": 150.080, "Close": 150.092}
    df = bt.add_family_a_columns(pd.DataFrame(rows, index=idx))

    signals = bt.family_a_signal_indices(df, 3.0, "AGENT_9_11_15")
    assert 25 in signals
    trades = bt.simulate_trades(df, [25], 3, 0.5, bt.FAMILY_A)

    assert len(trades) == 1
    assert trades[0].direction == "BUY"
    assert trades[0].gross_pip > 0
    assert trades[0].pnl_pip == trades[0].gross_pip - 0.5


def test_stats_gates_include_direction_null():
    trades = [
        bt.Trade(i, i, i + 3, f"t{i}", f"t{i+3}", "BUY" if i % 2 == 0 else "SELL", pnl + 0.2, pnl)
        for i, pnl in enumerate([2.0] * 18 + [-0.5] * 4 + [1.5] * 18 + [-0.4] * 4)
    ]
    row = bt.stats_for_cell(
        family=bt.FAMILY_A,
        k=3.0,
        horizon=3,
        hourset="ALL",
        spread_pip=0.2,
        trades=trades,
        period_start="2026-01-01T00:00:00+00:00",
        period_end="2026-01-02T00:00:00+00:00",
        generated_at="2026-05-18T00:00:00+00:00",
        source_path=Path("data/cache/massive/USD_JPY_5m_2014_2026.parquet"),
    )
    bt.bh_adjust([row])
    row["verdict"] = bt.classify(row)

    assert row["n"] == 44
    assert row["gates"]["G1_N"]
    assert row["gates"]["G3_EV"]
    assert row["gates"]["G8_Direction_Null"]
    assert len(row["wf"]) == 3


def test_integration_uses_real_massive_usdjpy_m5_parquet():
    parquet = Path("data/cache/massive/USD_JPY_5m_2014_2026.parquet")
    assert parquet.exists(), "real MASSIVE parquet is required; mock-only test is forbidden"
    df, source_path = bt.load_usdjpy_m5(parquet)
    assert source_path == parquet
    assert len(df) > 900_000
    assert df.index.min().year <= 2014
    assert df.index.max().year >= 2026
    df_a = bt.add_family_a_columns(df)
    signals = bt.family_a_signal_indices(df_a, 3.5, "AGENT_9_11_15")
    trades = bt.simulate_trades(df_a, signals, 3, 0.5, bt.FAMILY_A)
    assert len(trades) >= 30
    row = bt.stats_for_cell(
        family=bt.FAMILY_A,
        k=3.5,
        horizon=3,
        hourset="AGENT_9_11_15",
        spread_pip=0.5,
        trades=trades,
        period_start=df.index.min().isoformat(),
        period_end=df.index.max().isoformat(),
        generated_at="2026-05-18T00:00:00+00:00",
        source_path=source_path,
    )
    assert row["bt_data_source"] == bt.DATA_SOURCE
    assert row["spread_pip_round_trip"] == 0.5
    assert row["n"] == len(trades)
