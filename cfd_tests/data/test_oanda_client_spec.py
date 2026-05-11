"""Verify SPX500 / US500 InstrumentSpec values match Phase 0 report Section 3b."""
from __future__ import annotations

from cfd_trader.data.oanda_client import InstrumentSpec, SPX500_USD_SPEC


def test_spx500_spec_is_frozen_dataclass() -> None:
    import dataclasses
    assert dataclasses.is_dataclass(InstrumentSpec)
    assert SPX500_USD_SPEC.__class__ is InstrumentSpec


def test_spx500_oanda_v20_name() -> None:
    assert SPX500_USD_SPEC.oanda_v20_name == "SPX500_USD"


def test_spx500_mt5_name() -> None:
    # MT5 / OANDA Japan lineup ticker
    assert SPX500_USD_SPEC.mt5_name == "US500"


def test_spx500_display_precision_and_point_unit() -> None:
    assert SPX500_USD_SPEC.display_precision == 1
    # tick / point unit = 10^(-display_precision)
    assert SPX500_USD_SPEC.point_unit == 0.1


def test_spx500_minimum_trade_size() -> None:
    assert SPX500_USD_SPEC.minimum_trade_size == 1


def test_spx500_trade_units_precision() -> None:
    # integer units (no fractional contracts)
    assert SPX500_USD_SPEC.trade_units_precision == 0


def test_spx500_margin_rate_and_leverage() -> None:
    assert SPX500_USD_SPEC.margin_rate == 0.10
    assert SPX500_USD_SPEC.leverage == 10


def test_spx500_max_orders_and_positions() -> None:
    assert SPX500_USD_SPEC.max_single_order_units == 2000
    assert SPX500_USD_SPEC.max_position_units == 2500
