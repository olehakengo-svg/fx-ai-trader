"""Kelly<=0 promotion-gate regression tests (P0#3, 2026-04-27 audit).

Validates two pieces of behaviour:

1. ``DemoTrader._get_strategy_kelly_clean`` mirrors the aggregate-Kelly trade
   filter (CLOSED, ``is_shadow == 0``, XAU excluded, ``exit_time >=
   FIDELITY_CUTOFF``) but scoped to a single ``entry_type``.
2. The promotion-gate decision built from that helper blocks promotion when
   Kelly is non-positive, lets it through when Kelly is positive, and does
   not block when there is too little data to estimate Kelly.

Tests use a minimal harness (mirroring ``test_signal_dedup.py``) so we don't
need to spin up a full ``DemoTrader`` with DB / OANDA / threads.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.demo_trader import DemoTrader


class _FakeDB:
    def __init__(self, closed_trades):
        self._closed = closed_trades

    def get_all_closed(self):
        return list(self._closed)


class _KellyHarness:
    """Bare-minimum object exposing the attributes ``_get_strategy_kelly_clean``
    actually reads. The method is bound from the real DemoTrader class so the
    code under test is the production implementation."""

    _get_strategy_kelly_clean = DemoTrader._get_strategy_kelly_clean

    def __init__(self, trades, cutoff="2026-04-01T00:00:00Z"):
        self._db = _FakeDB(trades)
        self._FIDELITY_CUTOFF = cutoff


def _trade(entry_type, pnl, *, is_shadow=False, instrument="USD_JPY",
           status="CLOSED", exit_time="2026-04-20T00:00:00Z"):
    return {
        "entry_type": entry_type,
        "pnl_pips": pnl,
        "is_shadow": 1 if is_shadow else 0,
        "instrument": instrument,
        "status": status,
        "exit_time": exit_time,
    }


# =====================================================================
#  _get_strategy_kelly_clean — filter parity with _get_aggregate_kelly
# =====================================================================

def test_kelly_clean_returns_none_when_below_min_trades():
    """<10 clean trades → None (do not block promotion on thin data)."""
    trades = [_trade("foo", 5.0) for _ in range(9)]
    h = _KellyHarness(trades)
    assert h._get_strategy_kelly_clean("foo") is None


def test_kelly_clean_excludes_shadow_trades():
    """Shadow trades must not enter the Kelly base — even if abundant."""
    # 20 winning shadow trades (would yield positive Kelly if counted) +
    # 0 non-shadow → insufficient data → None.
    trades = [_trade("foo", 10.0, is_shadow=True) for _ in range(20)]
    h = _KellyHarness(trades)
    assert h._get_strategy_kelly_clean("foo") is None


def test_kelly_clean_excludes_xau_and_pre_cutoff():
    """XAU instrument and pre-cutoff trades are filtered out."""
    pre_cutoff = "2026-03-01T00:00:00Z"
    trades = (
        [_trade("foo", 10.0, instrument="XAU_USD") for _ in range(10)]
        + [_trade("foo", 10.0, exit_time=pre_cutoff) for _ in range(10)]
    )
    h = _KellyHarness(trades)
    assert h._get_strategy_kelly_clean("foo") is None


def test_kelly_clean_negative_for_losing_strategy():
    """Strategy losing more than it wins → full_kelly clamps to 0
    (kelly_criterion clamps negative edge to 0). Either way, the gate must
    treat this as non-positive."""
    # 3 wins of +1, 7 losses of -3 → strongly negative edge
    trades = [_trade("foo", 1.0) for _ in range(3)] + [
        _trade("foo", -3.0) for _ in range(7)
    ]
    h = _KellyHarness(trades)
    k = h._get_strategy_kelly_clean("foo")
    assert k is not None
    assert k <= 0, f"Expected non-positive Kelly for losing strategy, got {k}"


def test_kelly_clean_positive_for_winning_strategy():
    """Strategy with clear positive edge → full_kelly > 0."""
    # 7 wins of +3, 3 losses of -1 → positive edge
    trades = [_trade("foo", 3.0) for _ in range(7)] + [
        _trade("foo", -1.0) for _ in range(3)
    ]
    h = _KellyHarness(trades)
    k = h._get_strategy_kelly_clean("foo")
    assert k is not None and k > 0, f"Expected positive Kelly, got {k}"


def test_kelly_clean_scoped_to_entry_type():
    """Other strategies' trades must not bleed into the requested scope."""
    trades = (
        [_trade("foo", 3.0) for _ in range(7)]
        + [_trade("foo", -1.0) for _ in range(3)]
        + [_trade("bar", -10.0) for _ in range(20)]  # noise
    )
    h = _KellyHarness(trades)
    k_foo = h._get_strategy_kelly_clean("foo")
    k_bar = h._get_strategy_kelly_clean("bar")
    assert k_foo is not None and k_foo > 0
    # k_bar: all losses, no wins → None (no win/loss ratio defined)
    assert k_bar is None


# =====================================================================
#  Promotion-gate decision — _kelly_block semantics
# =====================================================================

def _gate_block(kelly_f):
    """Mirror the promotion-gate predicate from _evaluate_promotions L5189-5196."""
    return kelly_f is not None and kelly_f <= 0


def test_gate_blocks_when_kelly_negative():
    assert _gate_block(-0.05) is True


def test_gate_blocks_when_kelly_zero():
    """Spec: 'Kelly が負またはゼロの戦略は promoted に昇格させない'."""
    assert _gate_block(0.0) is True


def test_gate_allows_when_kelly_positive():
    assert _gate_block(0.12) is False


def test_gate_allows_when_kelly_none():
    """Insufficient data → don't block (other gates carry the load)."""
    assert _gate_block(None) is False


# =====================================================================
#  End-to-end: losing strategy → gate blocks promotion
# =====================================================================

def test_losing_strategy_gate_blocks_promotion():
    """Wire the helper into the gate predicate exactly as production does."""
    trades = [_trade("loser", 1.0) for _ in range(3)] + [
        _trade("loser", -3.0) for _ in range(7)
    ]
    h = _KellyHarness(trades)
    k = h._get_strategy_kelly_clean("loser")
    assert _gate_block(k) is True


def test_winning_strategy_gate_allows_promotion():
    trades = [_trade("winner", 3.0) for _ in range(7)] + [
        _trade("winner", -1.0) for _ in range(3)
    ]
    h = _KellyHarness(trades)
    k = h._get_strategy_kelly_clean("winner")
    assert _gate_block(k) is False
