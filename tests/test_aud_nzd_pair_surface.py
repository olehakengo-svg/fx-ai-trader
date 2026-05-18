from __future__ import annotations

import json
from pathlib import Path

from flask import render_template


AUD_NZD_PAIRS = {"AUD_JPY", "NZD_JPY", "AUD_USD", "NZD_USD", "EUR_AUD"}


def test_demo_trader_mode_config_contains_aud_nzd_pairs():
    from modules.demo_trader import AUD_NZD_SURFACE_PAIRS, MODE_CONFIG

    configured = {cfg.get("instrument") for cfg in MODE_CONFIG.values()}

    assert set(AUD_NZD_SURFACE_PAIRS) == AUD_NZD_PAIRS
    assert AUD_NZD_PAIRS <= configured

    for mode, cfg in MODE_CONFIG.items():
        if cfg.get("instrument") in AUD_NZD_PAIRS:
            assert cfg.get("auto_start") is False, mode


def test_oanda_bridge_resolves_aud_nzd_instrument_mapping():
    from modules.oanda_bridge import (
        OANDA_EXECUTION_ENABLED,
        SUPPORTED_INSTRUMENTS,
        resolve_instrument,
    )

    for pair in AUD_NZD_PAIRS:
        assert SUPPORTED_INSTRUMENTS[pair] == pair
        assert resolve_instrument(pair) == pair
        assert pair in OANDA_EXECUTION_ENABLED


def test_risk_analytics_aggregates_aud_nzd_synthetic_positions():
    from modules.risk_analytics import compute_risk_dashboard

    trades = []
    for i, pair in enumerate(sorted(AUD_NZD_PAIRS)):
        trades.extend(
            [
                {
                    "trade_id": f"{pair}-win",
                    "instrument": pair,
                    "entry_type": "price_shock_reversion",
                    "pnl_pips": 4.0 + i,
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

    assert AUD_NZD_PAIRS <= set(dashboard["by_instrument"])
    assert dashboard["n_total_trades"] == 10
    assert "price_shock_reversion" in dashboard["strategy_kelly"]


def test_demo_status_api_exposes_aud_nzd_pair_slots(flask_client):
    import time
    import app as app_mod

    app_mod._demo_trader._last_heal_time = time.time()

    response = flask_client.get("/api/demo/status")
    assert response.status_code == 200
    data = response.get_json()

    assert AUD_NZD_PAIRS <= set(data["pairs"])
    mode_instruments = {m["instrument"] for m in data["modes"].values()}
    assert AUD_NZD_PAIRS <= mode_instruments


def test_dashboard_template_render_contains_aud_nzd_pair_strings():
    import app as app_mod

    with app_mod.app.test_request_context("/demo-analysis"):
        html = render_template("demo_analysis.html")

    for pair in AUD_NZD_PAIRS:
        assert pair in html


def test_tier_master_snapshot_contains_aud_nzd_phase_b1_pairs():
    path = Path("knowledge-base/wiki/tier-master.json")
    data = json.loads(path.read_text())

    pair_set = {
        pair
        for pairs in data["phase_b1_shadow_candidates"].values()
        for pair in pairs
    }
    assert AUD_NZD_PAIRS <= pair_set


def test_flask_risk_dashboard_accepts_aud_nzd_positions(tmp_path, flask_client):
    import app as app_mod
    from modules.demo_db import DemoDB

    old_db = app_mod._demo_db
    db = DemoDB(str(tmp_path / "aud_nzd_demo.db"))
    try:
        for i, pair in enumerate(sorted(AUD_NZD_PAIRS)):
            entry = 100.0 if "JPY" in pair else 1.0000
            exit_price = entry + (0.05 if "JPY" in pair else 0.0005)
            trade_id = db.open_trade(
                "BUY",
                entry,
                entry - (0.20 if "JPY" in pair else 0.0020),
                entry + (0.20 if "JPY" in pair else 0.0020),
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
    assert AUD_NZD_PAIRS <= set(data["by_instrument"])
