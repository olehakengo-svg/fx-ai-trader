"""Regression tests for edge activation review findings."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


def test_turtle_s2_render_source_fetches_d1_without_local_parquet(monkeypatch):
    import tools.turtle_s2_d1_runner as runner

    dates = pd.date_range("2026-01-01", periods=150, freq="D", tz="UTC")
    fetched = pd.DataFrame(
        {
            "Open": [150.0] * len(dates),
            "High": [151.0] * len(dates),
            "Low": [149.0] * len(dates),
            "Close": [150.5] * len(dates),
            "Volume": [1000] * len(dates),
        },
        index=dates,
    )
    calls = []

    def fake_fetch_ohlcv(symbol, period, interval):
        calls.append((symbol, period, interval))
        return fetched

    monkeypatch.setattr(runner, "fetch_ohlcv", fake_fetch_ohlcv, raising=False)
    monkeypatch.setattr(
        runner,
        "REPO_ROOT",
        Path("/tmp/definitely-no-turtle-s2-parquet-cache"),
    )

    df = runner._load_d1_dataframe("USD_JPY", "render", lookback=120)

    assert calls == [("USDJPY=X", "160d", "1d")]
    assert len(df) == 120
    assert df.index.is_monotonic_increasing
    assert list(df.columns[:4]) == ["Open", "High", "Low", "Close"]


def test_pair_lot_boost_below_standard_floor_is_preserved():
    from modules.demo_trader import DemoTrader

    assert DemoTrader._lot_floor_ratio_for(
        entry_type="sr_channel_reversal",
        instrument="EUR_USD",
        configured_pair_boost=0.1,
        is_sentinel=False,
    ) == 0.1
    assert DemoTrader._lot_floor_ratio_for(
        entry_type="sr_channel_reversal",
        instrument="EUR_USD",
        configured_pair_boost=None,
        is_sentinel=False,
    ) == 0.3


def test_oanda_control_marks_turtle_s2_shadow_only_and_lists_tokyo(monkeypatch):
    os.environ["TESTING"] = "1"
    import app as app_mod

    class FakeDB:
        def get_shadow_trades_for_evaluation(self):
            return {"by_type": {}, "by_type_pair": {}}

    monkeypatch.setattr(app_mod._demo_trader, "_db", FakeDB())
    monkeypatch.setattr(
        app_mod._demo_trader._oanda,
        "get_strategy_overrides",
        lambda: {},
        raising=False,
    )

    strategies, instruments = app_mod._build_strategy_status_map()

    assert "tokyo_range_breakout_up" in strategies
    assert "USD_JPY" in instruments

    for unit in (
        "turtle_s2_unit_1",
        "turtle_s2_unit_2",
        "turtle_s2_unit_3",
        "turtle_s2_unit_4",
    ):
        assert unit in strategies
        assert strategies[unit]["effective"] is False
        assert strategies[unit]["auto_status"] == "shadow_only"
        assert strategies[unit]["pair_status"]["USD_JPY"]["lifecycle"] == "shadow_only"
        for inst, pair_status in strategies[unit]["pair_status"].items():
            if inst != "USD_JPY":
                assert pair_status["lifecycle"] == "unsupported"


def test_strategy_status_lists_turtle_s2_units_without_trade_history(monkeypatch, flask_client):
    import app as app_mod

    class FakeDemoDB:
        def get_stats(self, **kwargs):
            return {"by_type": {}, "total": 0, "wins": 0, "total_pnl": 0}

        def get_closed_trades(self, **kwargs):
            return []

    monkeypatch.setattr(app_mod, "_demo_db", FakeDemoDB())

    response = flask_client.get("/api/strategies/status")
    assert response.status_code == 200

    names = {s["name"] for s in response.get_json()["strategies"]}
    assert "tokyo_range_breakout_up" in names
    assert {"turtle_s2_unit_1", "turtle_s2_unit_2", "turtle_s2_unit_3", "turtle_s2_unit_4"} <= names


def test_internal_turtle_s2_endpoint_requires_secret_and_runs_in_web_process(monkeypatch, flask_client):
    import app as app_mod
    import tools.turtle_s2_d1_runner as runner

    calls = []

    def fake_run_once(pair, source):
        calls.append((pair, source))
        return {"action": "noop", "pair": pair, "source": source}

    monkeypatch.setenv("CRON_SECRET", "test-secret")
    monkeypatch.setattr(runner, "run_once", fake_run_once)

    blocked = flask_client.post("/api/internal/turtle_s2_d1/run")
    assert blocked.status_code == 401

    response = flask_client.post(
        "/api/internal/turtle_s2_d1/run",
        headers={"X-Cron-Secret": "test-secret"},
    )
    assert response.status_code == 200
    assert response.get_json()["result"]["action"] == "noop"
    assert calls == [("USD_JPY", "render")]
