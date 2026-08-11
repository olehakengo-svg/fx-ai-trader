"""/api/oanda/transactions (read-only idrange 照会) の入力検証と成功経路。

2026-08-03 rule:R3 — wg 08-02 FOK 不成立の cancel reason 確定 (weekend-gap-fade
カード followup) 用の観測性エンドポイント。live 挙動への影響なし (純 read)。
"""
import app as app_mod


class _StubClient:
    def __init__(self, ok=True, data=None):
        self._ok = ok
        self._data = data or {"transactions": [{"id": "549257", "type": "MARKET_ORDER"}]}
        self.calls = []

    def get_transactions_id_range(self, from_id, to_id, types=None):
        self.calls.append((from_id, to_id))
        return self._ok, self._data


class _StubBridge:
    def __init__(self, client):
        self._client = client


def _swap_client(monkeypatch, client):
    monkeypatch.setattr(app_mod._demo_trader, "_oanda", _StubBridge(client))


def test_transactions_success_passes_range_through(flask_client, monkeypatch):
    stub = _StubClient()
    _swap_client(monkeypatch, stub)
    resp = flask_client.get("/api/oanda/transactions?from=549256&to=549260")
    assert resp.status_code == 200
    assert resp.get_json()["transactions"][0]["id"] == "549257"
    assert stub.calls == [("549256", "549260")]


def test_transactions_rejects_non_integer(flask_client, monkeypatch):
    _swap_client(monkeypatch, _StubClient())
    resp = flask_client.get("/api/oanda/transactions?from=abc&to=5")
    assert resp.status_code == 400


def test_transactions_rejects_inverted_or_missing_range(flask_client, monkeypatch):
    _swap_client(monkeypatch, _StubClient())
    assert flask_client.get("/api/oanda/transactions").status_code == 400
    assert flask_client.get(
        "/api/oanda/transactions?from=10&to=5").status_code == 400


def test_transactions_rejects_wide_range(flask_client, monkeypatch):
    stub = _StubClient()
    _swap_client(monkeypatch, stub)
    resp = flask_client.get("/api/oanda/transactions?from=1&to=200")
    assert resp.status_code == 400
    assert stub.calls == []


def test_transactions_upstream_error_returns_500(flask_client, monkeypatch):
    _swap_client(monkeypatch, _StubClient(ok=False, data={"error": 401}))
    resp = flask_client.get("/api/oanda/transactions?from=1&to=2")
    assert resp.status_code == 500
