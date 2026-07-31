"""/api/demo/live-enable-flags — LIVE 例外レバー観測エンドポイントの回帰固定。

Render dashboard の env 実値が外部から読めない問題 (2026-07-06 未解決事項) の
恒久解決として追加。effective (import 時 class attr) と env_now (現在値) の
突合で「env 変更後に再起動していない」ドリフトも検出できる契約を固定する。
"""

import json


def test_live_enable_flags_shape(flask_client):
    resp = flask_client.get("/api/demo/live-enable-flags")
    assert resp.status_code == 200
    body = json.loads(resp.data)

    assert set(body.keys()) == {"env_levers", "code_pins", "removed_levers"}

    for key in ("USDJPY_CARRY_DIP_LIVE_ENABLE", "KALMAN_D7_LIVE_ENABLE"):
        lever = body["env_levers"][key]
        assert set(lever.keys()) == {"effective", "env_now", "drift"}
        assert isinstance(lever["effective"], bool)
        assert isinstance(lever["drift"], bool)


def test_code_pins_report_false(flask_client):
    """T8 R2 STOP の code pin 報告: hull は False 固定のまま、sweep は
    P-S1(a) Option B (user 条件付き承認 2026-07-24) で True へ解除。"""
    body = json.loads(flask_client.get("/api/demo/live-enable-flags").data)
    assert body["code_pins"]["HULL_DONCHIAN_FADE_LIVE_ENABLE"] is False
    assert body["code_pins"]["SWEEP_REVERSION_EURGBP_LIVE_ENABLE"] is True


def test_removed_bb_rsi_levers_are_dead_in_app_source():
    """BB_RSI_EMA_ALIGNED_REDESIGN_V2 の env-gated shadow-emit が app.py に
    復活していないことを固定 (T10 KILL 再試行禁止の code 面 enforcement)。"""
    import inspect
    import app as app_module

    src = inspect.getsource(app_module)
    assert 'os.environ.get("BB_RSI_EMA_ALIGNED_REDESIGN_V2")' not in src
    body_keys = json.loads(
        app_module.app.test_client().get("/api/demo/live-enable-flags").data
    )["removed_levers"]
    assert "BB_RSI_EMA_ALIGNED_REDESIGN_V2" in body_keys
