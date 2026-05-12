"""Adapter over the Windows-only `MetaTrader5` package.

This module is the only place that imports the MT5 package — and it
does so lazily so the rest of the shim (and its tests) can run on
non-Windows machines.

The adapter exposes the operations the app needs and translates MT5's
retcode semantics into the shim's wire-protocol response shape:

  - Successful fill → {"status": "filled", broker_trade_id, fill_price, raw}
  - Anything else  → {"status": "rejected", reject_reason, raw}

The adapter is responsible for instrument-name translation
(SPX500_USD → US500) and for converting cfd-trader's "long"/"short"
into MT5's BUY/SELL order types.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

# OANDA's v20 names (used internally by cfd-trader and stored in
# oanda_audit.instrument) → MT5 symbol on OANDA Japan's CFD platform.
# Extend this map as new CFD strategies come online. Missing keys
# fall through as the v20 name, so an MT5 symbol that happens to
# match works without an explicit entry.
V20_TO_MT5_SYMBOL: dict[str, str] = {
    "SPX500_USD": "US500",
    "NAS100_USD": "USTEC",
    "US30_USD":   "US30",
    "XAU_USD":    "XAUUSD",
}


def to_mt5_symbol(v20_name: str) -> str:
    return V20_TO_MT5_SYMBOL.get(v20_name, v20_name)


@dataclass(frozen=True)
class FillResponse:
    status: str  # 'filled' | 'rejected'
    broker_trade_id: str | None
    fill_price: float | None
    reject_reason: str | None
    raw: dict[str, Any]


class MT5Adapter:
    """Real adapter — imports MetaTrader5 on first call.

    Tests construct a FakeMT5Adapter (in test_app.py) instead of
    importing this on macOS/Linux CI.
    """

    def __init__(self, *, magic_number: int = 270512) -> None:
        # magic_number tags orders so the shim can recognize "its own"
        # orders when querying open positions later. 270512 = today's
        # date; it has no functional meaning beyond uniqueness.
        self.magic_number = magic_number
        self._mt5 = None

    def _mt5_module(self):
        if self._mt5 is None:
            import MetaTrader5  # type: ignore[import-not-found]
            self._mt5 = MetaTrader5
            if not self._mt5.initialize():
                raise RuntimeError(
                    f"MetaTrader5.initialize failed: {self._mt5.last_error()!r}"
                )
        return self._mt5

    def place_market(
        self,
        *,
        instrument: str,
        side: str,
        units: int,
        signal_price: float,
        client_order_id: str,
    ) -> FillResponse:
        """Wrap MT5's order_send with one retry on disconnect."""
        mt5 = self._mt5_module()
        symbol = to_mt5_symbol(instrument)

        # Ensure the symbol is visible in MarketWatch. Without this,
        # order_send returns retcode 10018 (TRADE_RETCODE_MARKET_CLOSED)
        # even for tradeable symbols on first run after restart.
        if not mt5.symbol_select(symbol, True):
            return FillResponse(
                status="rejected", broker_trade_id=None, fill_price=None,
                reject_reason=f"symbol_select_failed: {mt5.last_error()!r}",
                raw={"symbol": symbol},
            )

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return FillResponse(
                status="rejected", broker_trade_id=None, fill_price=None,
                reject_reason="no_tick_available", raw={"symbol": symbol},
            )

        order_type = mt5.ORDER_TYPE_BUY if side == "long" else mt5.ORDER_TYPE_SELL
        price = tick.ask if side == "long" else tick.bid

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       symbol,
            "volume":       float(units),
            "type":         order_type,
            "price":        price,
            "deviation":    20,
            "magic":        self.magic_number,
            "comment":      f"cfd_trader:{client_order_id[:12]}",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None:
            # One retry on disconnect — MT5 occasionally drops.
            time.sleep(0.5)
            mt5.shutdown()
            if not mt5.initialize():
                return FillResponse(
                    status="rejected", broker_trade_id=None, fill_price=None,
                    reject_reason="mt5_reinit_failed", raw={},
                )
            result = mt5.order_send(request)
        if result is None:
            return FillResponse(
                status="rejected", broker_trade_id=None, fill_price=None,
                reject_reason="order_send_returned_none",
                raw={"last_error": str(mt5.last_error())},
            )

        retcode = int(result.retcode)
        raw = {
            "retcode": retcode,
            "deal": int(getattr(result, "deal", 0)),
            "order": int(getattr(result, "order", 0)),
            "volume": float(getattr(result, "volume", 0.0)),
            "price": float(getattr(result, "price", 0.0)),
            "comment": str(getattr(result, "comment", "")),
            "request_id": int(getattr(result, "request_id", 0)),
        }

        # TRADE_RETCODE_DONE (10009) and TRADE_RETCODE_DONE_PARTIAL (10010)
        # are the two "broker accepted" outcomes.
        if retcode in (10009, 10010) and raw["deal"]:
            return FillResponse(
                status="filled",
                broker_trade_id=str(raw["deal"]),
                fill_price=raw["price"],
                reject_reason=None,
                raw=raw,
            )

        return FillResponse(
            status="rejected", broker_trade_id=None, fill_price=None,
            reject_reason=f"retcode_{retcode}", raw=raw,
        )
