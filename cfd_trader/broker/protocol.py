"""Broker protocol — the contract every concrete broker must satisfy.

Runner code depends on this Protocol, not on a concrete class. Tests
build fakes against this contract; production wires NullBroker or
MT5RemoteBroker.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

BrokerStatus = Literal["filled", "sent", "rejected"]


@dataclass(frozen=True)
class BrokerOrderResult:
    """Outcome of a place_market_order call.

    Invariant: ``broker_trade_id`` is non-empty IFF ``status == 'filled'``.
    The audit writer relies on this — a non-empty broker_trade_id is
    the truth-set membership predicate for the LIVE bucket. Concrete
    brokers MUST NOT leak a placeholder/empty string for a non-filled
    order, nor leave the field None when status is filled.
    """
    status: BrokerStatus
    broker_trade_id: str | None
    fill_price: float | None
    reject_reason: str | None
    raw: dict[str, Any]

    def __post_init__(self) -> None:
        if self.status == "filled":
            if not self.broker_trade_id:
                raise ValueError(
                    "filled order must carry a non-empty broker_trade_id"
                )
            if self.fill_price is None:
                raise ValueError("filled order must carry fill_price")
        else:
            if self.broker_trade_id:
                raise ValueError(
                    f"status={self.status!r} must have empty broker_trade_id; "
                    f"got {self.broker_trade_id!r}. This would pollute the "
                    f"LIVE bucket."
                )


class BrokerClient(Protocol):
    """Minimal broker surface used by cfd_trader.shadow.runner.

    Implementations live in cfd_trader/broker/{null,mt5_remote}.py.
    Anything richer (close position, modify SL, account info) is
    deferred until a strategy actually needs it — cfd-trader's
    Phase 2 strategies are flat-by-bar so closing happens at the
    bar boundary via a separate exit signal, not an API call.
    """

    def place_market_order(
        self,
        *,
        instrument: str,
        side: str,           # 'long' | 'short'
        units: int,
        signal_price: float,
    ) -> BrokerOrderResult:
        ...
