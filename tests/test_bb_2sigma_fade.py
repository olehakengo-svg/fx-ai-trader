from __future__ import annotations

import math

import pandas as pd

from tools import bb_2sigma_fade_bt as bt


def _synthetic_frame() -> pd.DataFrame:
    idx = pd.date_range("2025-01-01 07:00", periods=80, freq="5min", tz="UTC")
    close = [100.0] * 80
    close[30] = 98.0
    close[31] = 98.6
    close[32] = 99.1
    rows = []
    for c in close:
        rows.append({"Open": c, "High": c + 0.25, "Low": c - 0.25, "Close": c})
    return pd.DataFrame(rows, index=idx)


def test_cell_grid_is_64_for_family_a():
    assert len(list(bt.iter_cells("A"))) == 64


def test_family_a_long_signal_and_trade_stats_on_synthetic_data():
    df = bt.add_indicators(_synthetic_frame())
    cell = bt.Cell("A", "long", 20, 2.0, 30, 6, "LONDON_07-14_UTC")
    signals = bt.signal_indices_family_a(df, cell)
    assert 30 in set(signals)

    trades = bt.simulate_trades(df, signals, cell)
    assert trades
    stat = bt.stats_for_trades(cell, trades)
    assert stat["n"] >= 1
    assert math.isfinite(stat["mean_pip"])
    assert stat["cell_id"].startswith("A_long_L20_M2p0_R30_H6_")


def test_bonferroni_alpha_matches_64_cells():
    assert bt.ALPHA == 0.05 / 64
