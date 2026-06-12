"""End-to-end: strategy → Candidate.lot_multiplier → demo_trader.

Verify the SIZE lever reaches the final units number used for OANDA call.
"""
import datetime as dt
import pytest

from strategies.daytrade.session_time_bias import SessionTimeBias
from strategies.scalp.bb_rsi import BBRsiReversion
from strategies.context import SignalContext
from strategies.base import Candidate


@pytest.fixture(autouse=True)
def _clear_env_flags(monkeypatch):
    """Prevent shell env from contaminating cross-strategy tests."""
    monkeypatch.delenv("SESSION_TIME_BIAS_CELL_FILTER_V1", raising=False)
    monkeypatch.delenv("BB_RSI_REVERSION_PAIR_WHITELIST_V1", raising=False)


def test_session_time_bias_core_emits_lot_multiplier_1_0():
    """At LDN × ADX 27 × range, edge cell passes but SIZE boost stays 1.0x.

    2026-06-11 (417e17f4): 12y MASSIVE BT REJECT neutralized the 1.5x boost;
    the cell filter is retained as defence only.
    """
    strat = SessionTimeBias()
    edge, mult = strat._edge_cell(_ctx(hour_utc=10, adx=27, ema_dist_pct=0.002,
                                       regime="CHOP", symbol="EUR_USD"))
    assert (edge, mult) == (True, 1.0)


def test_bb_rsi_usdjpy_ldn_emits_lot_multiplier_1_0():
    strat = BBRsiReversion()
    edge, mult = strat._edge_cell(_ctx(hour_utc=10, symbol="USD_JPY"))
    assert (edge, mult) == (True, 1.0)


def test_bb_rsi_usdjpy_asn_emits_lot_multiplier_0_5():
    strat = BBRsiReversion()
    edge, mult = strat._edge_cell(_ctx(hour_utc=3, symbol="USD_JPY"))
    assert (edge, mult) == (True, 0.5)


def test_candidate_with_multiplier_reaches_demo_trader_lot():
    """Wire-through test: lot_multiplier on Candidate → demo_trader applies it."""
    from modules.demo_db import DemoDB
    from modules.demo_trader import DemoTrader
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        trader = DemoTrader(DemoDB(f"{td}/t.db"))
        cand = Candidate(signal="SELL", confidence=70, sl=160.5, tp=159.5,
                         reasons=["t"], entry_type="bb_rsi_reversion",
                         score=1.0, lot_multiplier=1.5)
        result = trader._apply_candidate_lot_multiplier(5000, cand)
        assert result == 7500


def _ctx(hour_utc, *, adx=20.0, ema_dist_pct=0.002, regime="RANGE",
         symbol="EUR_USD"):
    ctx = SignalContext()
    ctx.symbol = symbol
    ctx.entry = 1.1000
    ctx.ema200 = 1.1000 - 1.1000 * ema_dist_pct  # adjust so dist = ema_dist_pct
    ctx.adx = adx
    ctx.regime = {"regime": regime}
    ctx.entry_time_utc = dt.datetime(2026, 6, 8, hour_utc, 30, 0,
                                     tzinfo=dt.timezone.utc)
    return ctx
