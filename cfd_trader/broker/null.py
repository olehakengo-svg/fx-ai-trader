"""NullBroker — always rejects. Used pre-VPS and in shadow-only mode.

This is the production default until an MT5 shim URL is configured.
By construction, every order routes to "rejected" with
broker_trade_id=None, so the audit row lands in the *unrouted* bucket
(or stays SHADOW if is_shadow=1) — it can NEVER inflate Live N.
"""
from __future__ import annotations

from cfd_trader.broker.protocol import BrokerOrderResult


class NullBroker:
    """No-op broker: refuses every order.

    The runner can call ``place_market_order`` unconditionally; the
    LIVE gate logic upstream is what decides whether to issue the call
    at all. If the call is issued and we're configured with NullBroker,
    we record a rejection — which is the right thing: there is no
    broker, so the order did not reach one.
    """

    REJECT_REASON = "null_broker_not_configured"

    def place_market_order(
        self,
        *,
        instrument: str,
        side: str,
        units: int,
        signal_price: float,
    ) -> BrokerOrderResult:
        return BrokerOrderResult(
            status="rejected",
            broker_trade_id=None,
            fill_price=None,
            reject_reason=self.REJECT_REASON,
            raw={
                "instrument": instrument, "side": side,
                "units": units, "signal_price": signal_price,
            },
        )
