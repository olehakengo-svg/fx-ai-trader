"""MT5RemoteBroker — HMAC signing, response parsing, defensive demotion.

No real HTTP; a FakeSession captures the outgoing request and returns
canned responses. The signature is recomputed in the test to assert
it's correct.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import pytest
import requests

from cfd_trader.broker.mt5_remote import MT5RemoteBroker


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | str | None = None) -> None:
        self.status_code = status_code
        if isinstance(payload, dict):
            self._payload = payload
            self.text = json.dumps(payload)
        elif isinstance(payload, str):
            self._payload = None
            self.text = payload
        else:
            self._payload = None
            self.text = ""

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class _FakeSession:
    """Captures the last post() call and returns a queued response."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.next_response: _FakeResponse | None = None
        self.raise_on_post: Exception | None = None

    def post(self, url: str, *, data: bytes, headers: dict[str, str], timeout: float) -> _FakeResponse:
        self.calls.append({
            "url": url, "data": data, "headers": headers, "timeout": timeout,
        })
        if self.raise_on_post is not None:
            raise self.raise_on_post
        assert self.next_response is not None, "test forgot to queue a response"
        return self.next_response


SECRET = "test-secret-do-not-leak"


def _make_broker(session: _FakeSession) -> MT5RemoteBroker:
    return MT5RemoteBroker(
        base_url="https://mt5.example.test",
        secret=SECRET,
        timeout_s=2.0,
        session=session,  # type: ignore[arg-type]
    )


def _verify_signature(call: dict[str, Any]) -> None:
    ts = call["headers"]["X-Timestamp"]
    sig = call["headers"]["X-Signature"]
    msg = ts.encode() + b"." + call["data"]
    expected = hmac.new(SECRET.encode(), msg, hashlib.sha256).hexdigest()
    assert sig == expected, "HMAC signature does not match"


def test_filled_response_returns_filled_result() -> None:
    s = _FakeSession()
    s.next_response = _FakeResponse(200, {
        "status": "filled",
        "broker_trade_id": "84212391",
        "fill_price": 5000.25,
        "raw": {"deal": 84212391, "retcode": 10009},
    })
    b = _make_broker(s)

    r = b.place_market_order(
        instrument="US500", side="long", units=1, signal_price=5000.0,
    )

    assert r.status == "filled"
    assert r.broker_trade_id == "84212391"
    assert r.fill_price == 5000.25
    assert r.reject_reason is None

    assert len(s.calls) == 1
    call = s.calls[0]
    assert call["url"] == "https://mt5.example.test/v1/orders/market"
    assert call["timeout"] == 2.0
    _verify_signature(call)

    body = json.loads(call["data"])
    assert body["instrument"] == "US500"
    assert body["side"] == "long"
    assert body["units"] == 1
    assert body["signal_price"] == 5000.0
    assert "client_order_id" in body and len(body["client_order_id"]) >= 16


def test_rejected_response_returns_rejected_result() -> None:
    s = _FakeSession()
    s.next_response = _FakeResponse(200, {
        "status": "rejected",
        "broker_trade_id": None,
        "fill_price": None,
        "reject_reason": "TRADE_RETCODE_REJECT",
        "raw": {"retcode": 10006},
    })
    b = _make_broker(s)

    r = b.place_market_order(
        instrument="US500", side="short", units=1, signal_price=5000.0,
    )

    assert r.status == "rejected"
    assert r.broker_trade_id is None
    assert r.fill_price is None
    assert r.reject_reason == "TRADE_RETCODE_REJECT"


def test_network_error_returns_rejected() -> None:
    s = _FakeSession()
    s.raise_on_post = requests.ConnectionError("VPS unreachable")
    b = _make_broker(s)

    r = b.place_market_order(
        instrument="US500", side="long", units=1, signal_price=5000.0,
    )

    assert r.status == "rejected"
    assert r.broker_trade_id is None
    assert "network_error" in (r.reject_reason or "")
    assert "ConnectionError" in (r.reject_reason or "")


def test_http_5xx_returns_rejected() -> None:
    s = _FakeSession()
    s.next_response = _FakeResponse(503, "Service Unavailable")
    b = _make_broker(s)

    r = b.place_market_order(
        instrument="US500", side="long", units=1, signal_price=5000.0,
    )

    assert r.status == "rejected"
    assert r.reject_reason == "http_503"


def test_invalid_json_response_returns_rejected() -> None:
    s = _FakeSession()
    s.next_response = _FakeResponse(200, "<html>oops</html>")
    b = _make_broker(s)

    r = b.place_market_order(
        instrument="US500", side="long", units=1, signal_price=5000.0,
    )

    assert r.status == "rejected"
    assert r.reject_reason == "invalid_json_response"


def test_filled_without_ticket_is_demoted_to_rejected() -> None:
    """If the shim says filled but omits the ticket, we MUST NOT trust it.

    A LIVE bucket entry with broker_trade_id=None is exactly the bug
    the schema invariant is designed to prevent. We collapse to
    rejected so the row routes to the unrouted bucket for forensics.
    """
    s = _FakeSession()
    s.next_response = _FakeResponse(200, {
        "status": "filled",
        "broker_trade_id": None,
        "fill_price": 5000.0,
        "raw": {},
    })
    b = _make_broker(s)

    r = b.place_market_order(
        instrument="US500", side="long", units=1, signal_price=5000.0,
    )

    assert r.status == "rejected"
    assert r.broker_trade_id is None
    assert r.reject_reason == "shim_filled_without_ticket_or_price"


def test_filled_without_fill_price_is_demoted_to_rejected() -> None:
    s = _FakeSession()
    s.next_response = _FakeResponse(200, {
        "status": "filled",
        "broker_trade_id": "84212391",
        "fill_price": None,
        "raw": {},
    })
    b = _make_broker(s)

    r = b.place_market_order(
        instrument="US500", side="long", units=1, signal_price=5000.0,
    )

    assert r.status == "rejected"
    assert r.reject_reason == "shim_filled_without_ticket_or_price"


def test_status_sent_is_collapsed_to_rejected() -> None:
    """cfd-trader has no async-fill pipeline; 'sent' must not be LIVE."""
    s = _FakeSession()
    s.next_response = _FakeResponse(200, {
        "status": "sent",
        "broker_trade_id": None,
        "fill_price": None,
        "raw": {"order": 84212390},
    })
    b = _make_broker(s)

    r = b.place_market_order(
        instrument="US500", side="long", units=1, signal_price=5000.0,
    )

    assert r.status == "rejected"
    assert "non_filled:sent" in (r.reject_reason or "")


def test_constructor_requires_url_and_secret() -> None:
    with pytest.raises(ValueError, match="base_url"):
        MT5RemoteBroker(base_url="", secret="x")
    with pytest.raises(ValueError, match="secret"):
        MT5RemoteBroker(base_url="https://x", secret="")
