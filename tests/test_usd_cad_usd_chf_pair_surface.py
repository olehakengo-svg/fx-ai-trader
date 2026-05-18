from __future__ import annotations

import json
from pathlib import Path

from flask import render_template


USD_CAD_USD_CHF_PAIRS = {"USD_CAD", "USD_CHF"}
REGRESSION_PAIRS = {
    "USD_JPY",
    "EUR_USD",
    "GBP_USD",
    "AUD_JPY",
    "NZD_JPY",
    "AUD_USD",
    "NZD_USD",
    "EUR_AUD",
}


def test_demo_trader_mode_config_contains_usd_cad_usd_chf_pairs():
    from modules.demo_trader import MODE_CONFIG, USD_CAD_USD_CHF_SURFACE_PAIRS

    configured = {cfg.get("instrument") for cfg in MODE_CONFIG.values()}

    assert set(USD_CAD_USD_CHF_SURFACE_PAIRS) == USD_CAD_USD_CHF_PAIRS
    assert USD_CAD_USD_CHF_PAIRS <= configured
    assert REGRESSION_PAIRS <= configured

    for mode, cfg in MODE_CONFIG.items():
        if cfg.get("instrument") in USD_CAD_USD_CHF_PAIRS:
            assert cfg.get("auto_start") is False, mode


def test_oanda_bridge_resolves_usd_cad_usd_chf_instrument_mapping():
    from modules.oanda_bridge import (
        OANDA_EXECUTION_ENABLED,
        SUPPORTED_INSTRUMENTS,
        resolve_instrument,
    )

    for pair in USD_CAD_USD_CHF_PAIRS | REGRESSION_PAIRS:
        assert SUPPORTED_INSTRUMENTS[pair] == pair
        assert resolve_instrument(pair) == pair

    for pair in USD_CAD_USD_CHF_PAIRS:
        assert pair in OANDA_EXECUTION_ENABLED


def test_pip_multiplier_treats_usd_cad_usd_chf_as_non_jpy_pairs():
    from modules.demo_db import pip_multiplier

    assert pip_multiplier("USD_CAD") == 10000.0
    assert pip_multiplier("USD_CHF") == 10000.0
    assert pip_multiplier("USD_JPY") == 100.0


def test_risk_analytics_aggregates_usd_cad_usd_chf_synthetic_positions():
    from modules.risk_analytics import compute_risk_dashboard

    trades = []
    for i, pair in enumerate(sorted(USD_CAD_USD_CHF_PAIRS)):
        trades.extend(
            [
                {
                    "trade_id": f"{pair}-win",
                    "instrument": pair,
                    "entry_type": "price_shock_reversion",
                    "pnl_pips": 6.0 + i,
                },
                {
                    "trade_id": f"{pair}-loss",
                    "instrument": pair,
                    "entry_type": "price_shock_reversion",
                    "pnl_pips": -2.0,
                },
            ]
        )

    dashboard = compute_risk_dashboard(trades, lot_multiplier=1.0)

    assert USD_CAD_USD_CHF_PAIRS <= set(dashboard["by_instrument"])
    assert dashboard["n_total_trades"] == 4
    assert "price_shock_reversion" in dashboard["strategy_kelly"]


def test_demo_status_api_exposes_usd_cad_usd_chf_pair_slots(flask_client):
    import time
    import app as app_mod

    app_mod._demo_trader._last_heal_time = time.time()

    response = flask_client.get("/api/demo/status")
    assert response.status_code == 200
    data = response.get_json()

    assert USD_CAD_USD_CHF_PAIRS <= set(data["pairs"])
    assert REGRESSION_PAIRS <= set(data["pairs"])
    mode_instruments = {m["instrument"] for m in data["modes"].values()}
    assert USD_CAD_USD_CHF_PAIRS <= mode_instruments


def test_dashboard_template_render_contains_usd_cad_usd_chf_pair_strings():
    import app as app_mod

    with app_mod.app.test_request_context("/demo-analysis"):
        html = render_template("demo_analysis.html")

    for pair in USD_CAD_USD_CHF_PAIRS:
        assert pair in html


def test_tier_master_snapshot_contains_usd_cad_usd_chf_phase_b1_pairs():
    path = Path("knowledge-base/wiki/tier-master.json")
    data = json.loads(path.read_text())

    pair_set = {
        pair
        for pairs in data["phase_b1_shadow_candidates"].values()
        for pair in pairs
    }
    assert USD_CAD_USD_CHF_PAIRS <= pair_set
    assert REGRESSION_PAIRS - {"USD_JPY", "EUR_USD", "GBP_USD"} <= pair_set


def test_flask_risk_dashboard_accepts_usd_cad_usd_chf_positions(tmp_path, flask_client):
    import app as app_mod
    from modules.demo_db import DemoDB

    old_db = app_mod._demo_db
    db = DemoDB(str(tmp_path / "usd_cad_usd_chf_demo.db"))
    try:
        for i, pair in enumerate(sorted(USD_CAD_USD_CHF_PAIRS)):
            entry = 1.0000 + (i * 0.1)
            exit_price = entry + 0.0006
            trade_id = db.open_trade(
                "BUY",
                entry,
                entry - 0.0020,
                entry + 0.0020,
                entry_type="price_shock_reversion",
                confidence=70 + i,
                tf="1h",
                mode=f"test_{pair.lower()}",
                instrument=pair,
            )
            db.close_trade(trade_id, exit_price, "TEST_CLOSE")

        app_mod._demo_db = db
        response = flask_client.get("/api/risk/dashboard?all_time=1")
    finally:
        app_mod._demo_db = old_db

    assert response.status_code == 200
    data = response.get_json()
    assert USD_CAD_USD_CHF_PAIRS <= set(data["by_instrument"])
