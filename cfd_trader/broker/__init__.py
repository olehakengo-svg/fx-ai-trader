"""Broker abstraction for cfd-trader's LIVE path.

The protocol intentionally exposes only the operations cfd-trader's
runner needs (place a market order, close a position). It is NOT a
general-purpose OANDA/MT5 client — that scope creep is what made
``modules/oanda_bridge.py`` 850+ lines.

LIVE/SHADOW separation contract (Section 5.D):
- A broker call MUST return broker_trade_id ONLY on a true broker
  acceptance. ``status='rejected'`` or ``status='sent'`` MUST leave
  broker_trade_id as None.
- The audit writer uses that field to decide which bucket the row
  enters (LIVE vs unrouted). See cfd_trader/audit/oanda_audit.py.
"""
from cfd_trader.broker.protocol import BrokerClient, BrokerOrderResult
from cfd_trader.broker.null import NullBroker

__all__ = ["BrokerClient", "BrokerOrderResult", "NullBroker"]
