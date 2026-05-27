import app as app_mod


def test_api_demo_block_counts_returns_mode_and_strategy_counts(flask_client, monkeypatch):
    monkeypatch.setattr(app_mod._demo_trader, "_block_counts", {
        "daytrade_eurgbp:session_pair": 3,
        "scalp:hedge_block": 2,
    }, raising=False)
    monkeypatch.setattr(app_mod._demo_trader, "_block_counts_per_strategy", {
        "eurgbp_daily_mr:session_pair": 3,
        "bb_rsi_ema_aligned:hedge_block": 2,
    }, raising=False)

    response = flask_client.get("/api/demo/block-counts")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload == {
        "counts": {
            "daytrade_eurgbp:session_pair": 3,
            "scalp:hedge_block": 2,
        },
        "per_strategy_counts": {
            "eurgbp_daily_mr:session_pair": 3,
            "bb_rsi_ema_aligned:hedge_block": 2,
        },
        "strategy": None,
        "total": 5,
        "per_strategy_total": 5,
    }


def test_api_demo_block_counts_strategy_filter(flask_client, monkeypatch):
    monkeypatch.setattr(app_mod._demo_trader, "_block_counts", {
        "daytrade_eurgbp:session_pair": 3,
        "scalp:hedge_block": 2,
    }, raising=False)
    monkeypatch.setattr(app_mod._demo_trader, "_block_counts_per_strategy", {
        "eurgbp_daily_mr:session_pair": 3,
        "eurgbp_daily_mr:recent_emit": 1,
        "bb_rsi_ema_aligned:hedge_block": 2,
    }, raising=False)

    response = flask_client.get("/api/demo/block-counts?strategy=eurgbp_daily_mr")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["counts"] == {
        "daytrade_eurgbp:session_pair": 3,
        "scalp:hedge_block": 2,
    }
    assert payload["per_strategy_counts"] == {
        "eurgbp_daily_mr:session_pair": 3,
        "eurgbp_daily_mr:recent_emit": 1,
    }
    assert payload["strategy"] == "eurgbp_daily_mr"
    assert payload["total"] == 5
    assert payload["per_strategy_total"] == 4
