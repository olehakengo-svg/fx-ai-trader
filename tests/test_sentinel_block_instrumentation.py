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
    # 2026-09-21 (rule:R3): gate block の magnitude (spread_wide(4.2pip>3.0) の 4.2 等)
    # を top-level にも明示露出。persisted 経由の dict 透過だけだと読み手が
    # コード上のどこにも名前で現れず estimand 宣言の reader 配線検査にも掛からない
    # (= 暗黙の読み手 = write-only の再発形)。露出が persisted の忠実な鏡である
    # ことまで pin する — 別物を返すようになったらここが落ちる。
    per_cell_metrics = payload.pop("per_cell_metrics")
    assert isinstance(per_cell_metrics, dict)
    if "error" not in persisted:
        assert per_cell_metrics == (persisted.get("per_cell_metrics") or {})
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
         "per_cell_metrics", "total", "days"} <= set(persisted)
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
