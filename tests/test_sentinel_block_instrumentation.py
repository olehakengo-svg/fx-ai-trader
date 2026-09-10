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
    # 2026-09-11 P8: 永続面 (gate_block_daily) を "persisted" として併載。
    # legacy キーの形は不変 (in-memory、再起動で消える方)。
    persisted = payload.pop("persisted")
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
    # persisted は query 成功 (キー形が in-memory と diff 可能) か、
    # fail-loud の error 文字列のどちらか — 黙って欠落しない
    assert ("error" in persisted) or (
        {"counts", "per_strategy_counts", "per_cell_counts",
         "total", "days"} <= set(persisted)
    )
    assert persisted.get("days") == 7


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
