"""Flask app: auth, routing, idempotency, JSON contract.

Uses a FakeAdapter so MT5 is never imported. Runs on macOS/Linux CI.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from services.mt5_shim.app import create_app
from services.mt5_shim.mt5_adapter import FillResponse


SECRET = b"shim-test-secret"


class _FakeAdapter:
    """Stand-in for MT5Adapter — returns canned FillResponses."""

    def __init__(self) -> None:
        self.responses: list[FillResponse] = []
        self.calls: list[dict] = []
        self.raise_on_call: Exception | None = None

    def queue(self, fill: FillResponse) -> None:
        self.responses.append(fill)

    def place_market(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_on_call is not None:
            raise self.raise_on_call
        return self.responses.pop(0)


@pytest.fixture
def client_and_adapter():
    adapter = _FakeAdapter()
    app = create_app(adapter=adapter, secret=SECRET)
    return app.test_client(), adapter


def _sig(ts: str, body: bytes, secret: bytes = SECRET) -> str:
    return hmac.new(secret, ts.encode() + b"." + body, hashlib.sha256).hexdigest()


def _post(client, payload: dict, *, ts: str | None = None, sig: str | None = None, secret: bytes = SECRET):
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if ts is None:
        ts = str(int(time.time()))
    if sig is None:
        sig = _sig(ts, body, secret=secret)
    return client.post(
        "/v1/orders/market",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Timestamp": ts,
            "X-Signature": sig,
        },
    )


def _valid_payload(client_order_id: str = "abc123") -> dict:
    return {
        "instrument": "US500", "side": "long",
        "units": 1, "signal_price": 5000.0,
        "client_order_id": client_order_id,
    }


def test_health_endpoint_no_auth_required(client_and_adapter) -> None:
    client, _ = client_and_adapter
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}


def test_filled_order_returns_200_with_ticket(client_and_adapter) -> None:
    client, adapter = client_and_adapter
    adapter.queue(FillResponse(
        status="filled", broker_trade_id="84212391",
        fill_price=5000.25, reject_reason=None,
        raw={"deal": 84212391, "retcode": 10009},
    ))
    r = _post(client, _valid_payload())
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "filled"
    assert body["broker_trade_id"] == "84212391"
    assert body["fill_price"] == 5000.25
    assert body["raw"]["retcode"] == 10009


def test_rejected_order_returns_200_without_ticket(client_and_adapter) -> None:
    client, adapter = client_and_adapter
    adapter.queue(FillResponse(
        status="rejected", broker_trade_id=None, fill_price=None,
        reject_reason="retcode_10006", raw={"retcode": 10006},
    ))
    r = _post(client, _valid_payload())
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "rejected"
    assert body["broker_trade_id"] is None
    assert body["fill_price"] is None
    assert body["reject_reason"] == "retcode_10006"


def test_bad_signature_returns_401(client_and_adapter) -> None:
    client, adapter = client_and_adapter
    r = _post(client, _valid_payload(), sig="ab" * 32)  # wrong
    assert r.status_code == 401
    body = r.get_json()
    assert body["status"] == "rejected"
    assert body["reject_reason"] == "auth:bad_signature"
    assert adapter.calls == []  # adapter must NEVER be reached


def test_stale_timestamp_returns_401(client_and_adapter) -> None:
    client, adapter = client_and_adapter
    r = _post(client, _valid_payload(), ts="1000000")  # ancient
    assert r.status_code == 401
    body = r.get_json()
    assert body["reject_reason"] == "auth:stale_timestamp"
    assert adapter.calls == []


def test_missing_required_field_returns_400(client_and_adapter) -> None:
    client, adapter = client_and_adapter
    bad = _valid_payload()
    del bad["client_order_id"]
    r = _post(client, bad)
    assert r.status_code == 400
    body = r.get_json()
    assert "missing_fields" in body["reject_reason"]
    assert "client_order_id" in body["reject_reason"]
    assert adapter.calls == []


def test_idempotency_same_client_order_id_returns_cached(client_and_adapter) -> None:
    """The second POST with the same client_order_id must NOT hit the adapter."""
    client, adapter = client_and_adapter
    adapter.queue(FillResponse(
        status="filled", broker_trade_id="84212391",
        fill_price=5000.25, reject_reason=None, raw={"deal": 84212391},
    ))

    r1 = _post(client, _valid_payload("dedup-key-001"))
    r2 = _post(client, _valid_payload("dedup-key-001"))

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.get_json() == r2.get_json()
    assert len(adapter.calls) == 1  # adapter saw only the first call


def test_idempotency_different_client_order_ids_both_processed(client_and_adapter) -> None:
    client, adapter = client_and_adapter
    adapter.queue(FillResponse(
        status="filled", broker_trade_id="1", fill_price=5000.0,
        reject_reason=None, raw={},
    ))
    adapter.queue(FillResponse(
        status="filled", broker_trade_id="2", fill_price=5000.5,
        reject_reason=None, raw={},
    ))

    r1 = _post(client, _valid_payload("k1"))
    r2 = _post(client, _valid_payload("k2"))

    assert r1.get_json()["broker_trade_id"] == "1"
    assert r2.get_json()["broker_trade_id"] == "2"
    assert len(adapter.calls) == 2


def test_adapter_exception_becomes_rejected_200(client_and_adapter) -> None:
    """An adapter crash must NOT 500 — it returns rejected with a reason."""
    client, adapter = client_and_adapter
    adapter.raise_on_call = RuntimeError("boom")
    r = _post(client, _valid_payload())
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "rejected"
    assert "adapter_exception:RuntimeError" in body["reject_reason"]


def test_app_refuses_to_start_without_secret(monkeypatch) -> None:
    monkeypatch.delenv("CFD_MT5_SHIM_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="CFD_MT5_SHIM_SECRET"):
        create_app(adapter=_FakeAdapter())


def test_adapter_receives_canonical_payload(client_and_adapter) -> None:
    """The adapter must be called with the parsed payload, ints as ints."""
    client, adapter = client_and_adapter
    adapter.queue(FillResponse(
        status="filled", broker_trade_id="T", fill_price=1.0,
        reject_reason=None, raw={},
    ))
    _post(client, {
        "instrument": "US500", "side": "short",
        "units": 3, "signal_price": 4995.5,
        "client_order_id": "canon-001",
    })
    assert len(adapter.calls) == 1
    call = adapter.calls[0]
    assert call["instrument"] == "US500"
    assert call["side"] == "short"
    assert call["units"] == 3
    assert isinstance(call["units"], int)
    assert call["signal_price"] == 4995.5
    assert call["client_order_id"] == "canon-001"
