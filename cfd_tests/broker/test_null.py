"""NullBroker must always reject, never carry a ticket."""
from __future__ import annotations

from cfd_trader.broker import NullBroker


def test_null_broker_always_rejects() -> None:
    b = NullBroker()
    r = b.place_market_order(
        instrument="SPX500_USD", side="long", units=1, signal_price=5000.0,
    )
    assert r.status == "rejected"
    assert r.broker_trade_id is None
    assert r.fill_price is None
    assert r.reject_reason == NullBroker.REJECT_REASON


def test_null_broker_preserves_request_in_raw() -> None:
    """The raw payload helps debugging when a strategy quietly stops trading."""
    b = NullBroker()
    r = b.place_market_order(
        instrument="US500", side="short", units=3, signal_price=4980.5,
    )
    assert r.raw["instrument"] == "US500"
    assert r.raw["side"] == "short"
    assert r.raw["units"] == 3
    assert r.raw["signal_price"] == 4980.5
