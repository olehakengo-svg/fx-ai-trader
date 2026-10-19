"""/api/oanda/trades_remote (read-only、OANDA v20 closed trades の live proxy)。

2026-10-19 rule:R3 — D11 両基準併記 (tools/m1_clean_live_monitor.py --strong) の
broker realized 読み手。ローカル同期表 oanda_trades は 2026-09-24 で停止しているため、
OANDA から直接 trades 一覧を引く純 read 経路。live 挙動への影響なし。
"""
import app as app_mod


class _StubClient:
    def __init__(self, ok=True, data=None):
        self._ok = ok
        self._data = data if data is not None else {
            "trades": [
                {"id": "1254229", "instrument": "USD_JPY", "price": "157.918",
                 "initialUnits": "1000", "state": "CLOSED", "realizedPL": "8.0000",
                 "financing": "0.0000", "averageClosePrice": "157.926",
                 "closeTime": "2026-10-16T07:22:36.000000000Z"},
            ],
            "lastTransactionID": "1324445",
        }
        self.calls = []

    def get_trades(self, state="ALL", count=500, instrument=None, before_id=None):
        self.calls.append((state, count, instrument, before_id))
        return self._ok, self._data


class _StubBridge:
    def __init__(self, client):
        self._client = client


def _swap_client(monkeypatch, client):
    monkeypatch.setattr(app_mod._demo_trader, "_oanda", _StubBridge(client))


def test_trades_remote_defaults_to_closed_500_and_passes_payload_through(flask_client, monkeypatch):
    stub = _StubClient()
    _swap_client(monkeypatch, stub)
    resp = flask_client.get("/api/oanda/trades_remote")
    assert resp.status_code == 200
    body = resp.get_json()
    assert [t["id"] for t in body["trades"]] == ["1254229"]
    assert body["lastTransactionID"] == "1324445"
    assert stub.calls == [("CLOSED", 500, None, None)]


def test_trades_remote_forwards_before_id_count_and_instrument(flask_client, monkeypatch):
    stub = _StubClient()
    _swap_client(monkeypatch, stub)
    resp = flask_client.get("/api/oanda/trades_remote?state=closed&count=50&before_id=893189&instrument=USD_JPY")
    assert resp.status_code == 200
    assert stub.calls == [("CLOSED", 50, "USD_JPY", "893189")]


def test_trades_remote_rejects_bad_params_without_calling_broker(flask_client, monkeypatch):
    stub = _StubClient()
    _swap_client(monkeypatch, stub)
    assert flask_client.get("/api/oanda/trades_remote?state=BOGUS").status_code == 400
    assert flask_client.get("/api/oanda/trades_remote?count=0").status_code == 400
    assert flask_client.get("/api/oanda/trades_remote?count=501").status_code == 400
    assert flask_client.get("/api/oanda/trades_remote?before_id=abc").status_code == 400
    assert flask_client.get("/api/oanda/trades_remote?before_id=-5").status_code == 400
    assert stub.calls == []


def test_trades_remote_upstream_error_returns_500_not_empty_list(flask_client, monkeypatch):
    _swap_client(monkeypatch, _StubClient(ok=False, data={"error": 401, "message": "x"}))
    resp = flask_client.get("/api/oanda/trades_remote")
    assert resp.status_code == 500
    assert "trades" not in resp.get_json()  # 失敗を 0 件と偽らない
