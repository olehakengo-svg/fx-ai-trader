"""End-to-end: cfd_trader.MT5RemoteBroker → mt5_shim.app.

This is the wire-contract pinning test. If either side changes
canonicalization, headers, signing, or response shape, this breaks.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from cfd_trader.broker.mt5_remote import MT5RemoteBroker
from services.mt5_shim.app import create_app
from services.mt5_shim.mt5_adapter import FillResponse


SECRET = "round-trip-secret"


class _FakeAdapter:
    def __init__(self) -> None:
        self.responses: list[FillResponse] = []
        self.calls: list[dict] = []

    def queue(self, fill: FillResponse) -> None:
        self.responses.append(fill)

    def place_market(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


@dataclass
class _AdaptedResponse:
    """Bridge Flask's TestClient response to requests.Response shape."""
    status_code: int
    text: str

    def json(self):
        import json
        return json.loads(self.text)


class _FlaskBridgeSession:
    """Pretends to be a requests.Session, routes to Flask test client."""

    def __init__(self, flask_client) -> None:
        self._fc = flask_client

    def post(self, url: str, *, data, headers, timeout):  # noqa: ARG002
        # Strip the scheme+host the broker prepended; the Flask test
        # client takes path+query only.
        from urllib.parse import urlparse
        path = urlparse(url).path
        resp = self._fc.post(path, data=data, headers=headers)
        return _AdaptedResponse(
            status_code=resp.status_code,
            text=resp.get_data(as_text=True),
        )


@pytest.fixture
def round_trip():
    adapter = _FakeAdapter()
    app = create_app(adapter=adapter, secret=SECRET.encode("utf-8"))
    fc = app.test_client()
    broker = MT5RemoteBroker(
        base_url="https://shim.test.invalid",
        secret=SECRET,
        timeout_s=1.0,
        session=_FlaskBridgeSession(fc),  # type: ignore[arg-type]
    )
    return broker, adapter


def test_round_trip_filled(round_trip) -> None:
    broker, adapter = round_trip
    adapter.queue(FillResponse(
        status="filled", broker_trade_id="84212391",
        fill_price=5000.25, reject_reason=None,
        raw={"deal": 84212391, "retcode": 10009},
    ))

    r = broker.place_market_order(
        instrument="US500", side="long", units=1, signal_price=5000.0,
    )

    assert r.status == "filled"
    assert r.broker_trade_id == "84212391"
    assert r.fill_price == 5000.25
    assert len(adapter.calls) == 1


def test_round_trip_rejected(round_trip) -> None:
    broker, adapter = round_trip
    adapter.queue(FillResponse(
        status="rejected", broker_trade_id=None, fill_price=None,
        reject_reason="retcode_10006", raw={"retcode": 10006},
    ))

    r = broker.place_market_order(
        instrument="US500", side="short", units=1, signal_price=4998.0,
    )

    assert r.status == "rejected"
    assert r.broker_trade_id is None
    assert r.reject_reason == "retcode_10006"


def test_round_trip_secret_mismatch_returns_rejected_not_crash(round_trip) -> None:
    """Client signs with a different secret → shim 401s → broker reports rejected."""
    _, adapter = round_trip
    adapter.queue(FillResponse(
        status="filled", broker_trade_id="X", fill_price=1.0,
        reject_reason=None, raw={},
    ))
    # Build a broker with the WRONG secret, but reuse the test-client session
    app = create_app(adapter=adapter, secret=SECRET.encode("utf-8"))
    bad_broker = MT5RemoteBroker(
        base_url="https://shim.test.invalid",
        secret="not-" + SECRET,
        timeout_s=1.0,
        session=_FlaskBridgeSession(app.test_client()),  # type: ignore[arg-type]
    )
    r = bad_broker.place_market_order(
        instrument="US500", side="long", units=1, signal_price=5000.0,
    )
    assert r.status == "rejected"
    assert r.reject_reason == "http_401"
    assert adapter.calls == []  # adapter never reached
