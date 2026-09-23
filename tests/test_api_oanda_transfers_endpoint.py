"""/api/oanda/transfers (read-only、OANDA TRANSFER_FUNDS 入出金台帳の時間窓照会)。

2026-09-23 rule:R3 — F4 資金時計 (tools/nav_floor_projection.py) が edge 残差から
入出金を差し引くための broker 台帳読み手。live 挙動への影響なし (純 read)。
"""
from datetime import datetime, timezone

import app as app_mod


class _StubClient:
    def __init__(self, ok=True, data=None, configured=True):
        self._ok = ok
        self._data = data if data is not None else {"transactions": [
            {"id": "900001", "type": "TRANSFER_FUNDS", "amount": "100000.0000",
             "time": "2026-09-10T02:00:00.000000000Z", "fundingReason": "CLIENT_FUNDING"},
            {"id": "900002", "type": "TRANSFER_FUNDS_REJECT", "amount": "1.0000",
             "time": "2026-09-11T02:00:00.000000000Z"}], "pages": 1}
        self.configured = configured
        self.calls = []

    def list_transactions_full(self, from_time, to_time, types=None):
        self.calls.append((from_time, to_time, tuple(types or ())))
        return self._ok, self._data


class _StubBridge:
    def __init__(self, client):
        self._client = client


def _swap_client(monkeypatch, client):
    monkeypatch.setattr(app_mod._demo_trader, "_oanda", _StubBridge(client))


def test_transfers_success_filters_type_and_passes_rfc3339_window(flask_client, monkeypatch):
    stub = _StubClient()
    _swap_client(monkeypatch, stub)
    resp = flask_client.get("/api/oanda/transfers?from=2026-09-01&to=2026-09-23")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["type"] == "TRANSFER_FUNDS" and body["count"] == 1
    assert [t["id"] for t in body["transactions"]] == ["900001"]  # REJECT は除外
    assert body["from"] == "2026-09-01T00:00:00Z" and body["to"] == "2026-09-23T00:00:00Z"
    assert stub.calls == [("2026-09-01T00:00:00Z", "2026-09-23T00:00:00Z", ("TRANSFER_FUNDS",))]


def test_transfers_rejects_bad_dates_inverted_and_wide_window(flask_client, monkeypatch):
    stub = _StubClient()
    _swap_client(monkeypatch, stub)
    assert flask_client.get("/api/oanda/transfers").status_code == 400
    assert flask_client.get("/api/oanda/transfers?from=abc&to=2026-09-23").status_code == 400
    assert flask_client.get("/api/oanda/transfers?from=2026-09-23&to=2026-09-23").status_code == 400
    assert flask_client.get("/api/oanda/transfers?from=2026-09-24&to=2026-09-23").status_code == 400
    assert flask_client.get("/api/oanda/transfers?from=2024-01-01&to=2026-09-23").status_code == 400
    assert stub.calls == []


def test_transfers_clamps_future_to_bound_to_now(flask_client, monkeypatch):
    stub = _StubClient(data={"transactions": [], "pages": 0})
    _swap_client(monkeypatch, stub)
    today = datetime.now(timezone.utc).date()
    d_from = today.replace(day=1) if today.day > 1 else today.fromordinal(today.toordinal() - 1)
    d_to = today.fromordinal(today.toordinal() + 1)
    resp = flask_client.get(f"/api/oanda/transfers?from={d_from.isoformat()}&to={d_to.isoformat()}")
    assert resp.status_code == 200
    (_, to_time, _), = stub.calls
    to_dt = datetime.strptime(to_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert to_dt <= datetime.now(timezone.utc)
    assert to_dt.date() == today  # 明日ではなく「今」まで
    assert resp.get_json()["transactions"] == [] and resp.get_json()["count"] == 0


def test_transfers_upstream_error_returns_500_not_empty_list(flask_client, monkeypatch):
    _swap_client(monkeypatch, _StubClient(ok=False, data={"error": 401, "message": "x"}))
    resp = flask_client.get("/api/oanda/transfers?from=2026-09-01&to=2026-09-23")
    assert resp.status_code == 500
    assert "transactions" not in resp.get_json()  # 失敗を 0 件と偽らない


def test_transfers_unconfigured_client_returns_503(flask_client, monkeypatch):
    stub = _StubClient(configured=False)
    _swap_client(monkeypatch, stub)
    resp = flask_client.get("/api/oanda/transfers?from=2026-09-01&to=2026-09-23")
    assert resp.status_code == 503 and stub.calls == []
