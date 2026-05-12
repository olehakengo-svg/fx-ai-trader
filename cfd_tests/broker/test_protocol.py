"""BrokerOrderResult contract tests.

The invariant — non-empty broker_trade_id IFF status='filled' — is the
root predicate of the LIVE bucket. If this leaks, Live N is polluted.
"""
from __future__ import annotations

import pytest

from cfd_trader.broker.protocol import BrokerOrderResult


def test_filled_must_have_broker_trade_id() -> None:
    with pytest.raises(ValueError, match="non-empty broker_trade_id"):
        BrokerOrderResult(
            status="filled",
            broker_trade_id=None,
            fill_price=5000.0,
            reject_reason=None,
            raw={},
        )


def test_filled_must_have_fill_price() -> None:
    with pytest.raises(ValueError, match="fill_price"):
        BrokerOrderResult(
            status="filled",
            broker_trade_id="MT5#1",
            fill_price=None,
            reject_reason=None,
            raw={},
        )


def test_rejected_must_not_have_broker_trade_id() -> None:
    with pytest.raises(ValueError, match="pollute the LIVE bucket"):
        BrokerOrderResult(
            status="rejected",
            broker_trade_id="MT5#1",
            fill_price=None,
            reject_reason="anything",
            raw={},
        )


def test_sent_must_not_have_broker_trade_id() -> None:
    with pytest.raises(ValueError, match="pollute the LIVE bucket"):
        BrokerOrderResult(
            status="sent",
            broker_trade_id="MT5#1",
            fill_price=None,
            reject_reason=None,
            raw={},
        )


def test_valid_filled_result() -> None:
    r = BrokerOrderResult(
        status="filled",
        broker_trade_id="MT5#84212391",
        fill_price=5000.25,
        reject_reason=None,
        raw={"deal": 84212391},
    )
    assert r.status == "filled"
    assert r.broker_trade_id == "MT5#84212391"


def test_valid_rejected_result() -> None:
    r = BrokerOrderResult(
        status="rejected",
        broker_trade_id=None,
        fill_price=None,
        reject_reason="bad_market",
        raw={},
    )
    assert r.status == "rejected"
    assert r.broker_trade_id is None
