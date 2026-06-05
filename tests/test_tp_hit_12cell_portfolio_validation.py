import math

from tools.tp_hit_12cell_portfolio_validation import (
    FROZEN_CELLS,
    compute_cell_stats,
    compute_portfolio_stats,
)


def test_frozen_cell_registry_has_exact_pre_registered_cells():
    assert len(FROZEN_CELLS) == 12
    assert FROZEN_CELLS[0] == ("dt_bb_rsi_mr", "EUR_USD", "SELL")
    assert FROZEN_CELLS[-1] == ("rsk_gbpjpy_reversion", "GBP_JPY", "BUY")


def test_compute_cell_stats_reports_gates_wf_and_cohorts():
    rows = []
    for i in range(18):
        rows.append(
            {
                "exit_time": f"2026-05-{1 + i % 15:02d}T00:00:00",
                "pnl_pips": 3.0,
                "outcome": "WIN",
                "close_reason": "TP_HIT",
            }
        )
    for i in range(12):
        rows.append(
            {
                "exit_time": f"2026-05-{16 + i % 10:02d}T00:00:00",
                "pnl_pips": -1.0,
                "outcome": "LOSS",
                "close_reason": "STOP_LOSS",
            }
        )

    stats = compute_cell_stats("demo", "EUR_USD", "BUY", rows, n_boot=200, seed=7)

    assert stats["n"] == 30
    assert stats["wins"] == 18
    assert stats["tp_wins"] == 18
    assert stats["wr"] == 0.6
    assert stats["profit_factor"] == 4.5
    assert stats["kelly_fraction"] == 0.466667
    assert stats["h1_gate"]["pass"] is True
    assert stats["walk_forward"]["fold_count"] == 3
    assert stats["walk_forward"]["positive_ev_folds"] == 2
    assert stats["cohorts"]["before_2026_05_16"]["n"] == 18
    assert stats["cohorts"]["from_2026_05_16"]["n"] == 12


def test_compute_portfolio_stats_uses_inv_vol_daily_series():
    daily = {
        "cell_a": {"2026-05-01": 1.0, "2026-05-02": -1.0, "2026-05-03": 2.0},
        "cell_b": {"2026-05-01": 2.0, "2026-05-02": 2.0, "2026-05-03": -2.0},
    }

    stats = compute_portfolio_stats(daily)

    assert stats["cells"] == 2
    assert stats["days"] == 3
    assert set(stats["weights"]) == {"cell_a", "cell_b"}
    assert math.isclose(sum(stats["weights"].values()), 1.0, rel_tol=1e-9)
    assert "cell_a" in stats["daily_correlation"]
    assert stats["max_drawdown_pips"] >= 0.0
