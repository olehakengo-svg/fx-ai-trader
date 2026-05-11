"""Regression tests for Monte Carlo ruin lot multiplier handling."""

from __future__ import annotations

import pytest

from modules.risk_analytics import monte_carlo_ruin


def _lossy_pnl_sample() -> list[float]:
    return [
        -12.0, -10.0, -9.0, -8.0, -7.0,
        4.0, 5.0, -11.0, -6.0, 3.0,
        -13.0, -9.0, -8.0, 6.0, -10.0,
        -7.0, -12.0, 4.0, -8.0, -9.0,
    ]


def _mc_kwargs() -> dict:
    return {
        "initial_capital": 1000.0,
        "ruin_dd_pct": 0.50,
        "n_simulations": 2000,
        "n_trades_forward": 300,
        "seed": 123,
    }


def test_monte_carlo_lot_multiplier_default_matches_legacy_one():
    pnl = _lossy_pnl_sample()

    legacy = monte_carlo_ruin(pnl, **_mc_kwargs())
    explicit = monte_carlo_ruin(pnl, lot_multiplier=1.0, **_mc_kwargs())

    assert explicit == legacy


def test_monte_carlo_defensive_lot_multiplier_reduces_ruin():
    pnl = _lossy_pnl_sample()

    full_lot = monte_carlo_ruin(pnl, lot_multiplier=1.0, **_mc_kwargs())
    defensive = monte_carlo_ruin(pnl, lot_multiplier=0.2, **_mc_kwargs())

    assert full_lot["ruin_probability"] > 0.25
    assert defensive["ruin_probability"] < full_lot["ruin_probability"]
    assert defensive["ruin_probability"] < 0.05


def test_monte_carlo_median_max_dd_scales_with_lot_multiplier():
    pnl = _lossy_pnl_sample()

    full_lot = monte_carlo_ruin(pnl, lot_multiplier=1.0, **_mc_kwargs())
    defensive = monte_carlo_ruin(pnl, lot_multiplier=0.2, **_mc_kwargs())

    expected = full_lot["median_max_dd"] * 0.2
    assert defensive["median_max_dd"] == pytest.approx(expected, rel=0.10)


def test_risk_dashboard_response_includes_lot_multiplier_applied(
    flask_client, monkeypatch
):
    import app as app_mod

    class FakeDemoDB:
        def get_all_closed(self, exclude_shadow=True):
            rows = []
            for i, pnl in enumerate(_lossy_pnl_sample()):
                rows.append({
                    "trade_id": f"t{i}",
                    "instrument": "USD_JPY",
                    "entry_type": "unit_test",
                    "pnl_pips": pnl,
                    "exit_time": "2026-05-10T00:00:00",
                })
            return rows

        def get_system_kv(self, key, default=""):
            values = {
                "eq_peak": "1000.0",
                "eq_current": "527.8",
                "dd_lot_mult": "0.2",
            }
            return values.get(key, default)

    monkeypatch.setattr(app_mod, "_demo_db", FakeDemoDB())

    response = flask_client.get("/api/risk/dashboard?all_time=1")

    assert response.status_code == 200
    data = response.get_json()
    assert data["monte_carlo"]["lot_multiplier_applied"] == 0.2
    assert data["dd_status"]["lot_multiplier"] == 0.2
