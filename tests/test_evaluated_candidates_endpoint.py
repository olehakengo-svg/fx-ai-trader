"""/api/demo/evaluated-candidates — C1 candidate-funnel 読み出しの契約固定。

2026-08-24 (rule:R3): evaluated_candidates は 2026-04-28 から毎バー書かれて
いたが **読み出し経路がゼロ** だった (route 無し / query_candidate_summary は
自身の unit test からしか呼ばれない)。その結果「候補は出たが trade にならない」
funnel 段が本番で観測不能になり、hull_donchian_fade の発火率ギャップ
(offline replay 12.6 signal/週 vs live 1.62 trade/週) が 49 日間未診断で滞留した。

本 test は読み出し契約 (view=summary/rows/meta) を固定する。
"""

import json


def test_summary_view_shape(flask_client):
    resp = flask_client.get("/api/demo/evaluated-candidates")
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["view"] == "summary"
    assert body["days"] == 7
    assert isinstance(body["summary"], dict)
    assert body["n_strategies"] == len(body["summary"])


def test_meta_view_exposes_row_count(flask_client):
    """行数を露出させる — retention job が無いため無制限成長を可視化する。"""
    body = json.loads(
        flask_client.get("/api/demo/evaluated-candidates?view=meta").data)
    assert body["view"] == "meta"
    assert set(body["meta"].keys()) == {
        "rows", "first_created", "last_created", "n_strategies"}
    assert isinstance(body["meta"]["rows"], int)


def test_rows_view_shape_and_filters(flask_client):
    body = json.loads(flask_client.get(
        "/api/demo/evaluated-candidates"
        "?view=rows&strategy=hull_donchian_fade&days=30&limit=5").data)
    assert body["view"] == "rows"
    assert body["strategy"] == "hull_donchian_fade"
    assert body["days"] == 30
    assert body["count"] == len(body["rows"])
    assert body["count"] <= 5


def test_bad_numeric_params_fall_back_to_defaults(flask_client):
    body = json.loads(
        flask_client.get("/api/demo/evaluated-candidates?days=abc").data)
    assert body["days"] == 7


def test_route_is_registered_and_read_only():
    """POST を受けない = 観測専用エンドポイントであることを固定。"""
    import app as app_module

    rules = {r.rule: r for r in app_module.app.url_map.iter_rules()}
    assert "/api/demo/evaluated-candidates" in rules
    assert set(rules["/api/demo/evaluated-candidates"].methods) >= {"GET"}
    assert "POST" not in rules["/api/demo/evaluated-candidates"].methods
