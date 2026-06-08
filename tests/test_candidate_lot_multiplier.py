"""Test Candidate.lot_multiplier field for edge cell SIZE lever.

Added 2026-06-08 per docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md
"""
from strategies.base import Candidate


def _make_candidate(**overrides):
    """Helper: minimal valid Candidate."""
    defaults = dict(
        signal="BUY", confidence=70, sl=1.1000, tp=1.1050,
        reasons=["test"], entry_type="bb_rsi_reversion", score=1.0,
    )
    defaults.update(overrides)
    return Candidate(**defaults)


def test_lot_multiplier_default_is_1():
    c = _make_candidate()
    assert c.lot_multiplier == 1.0, "default must be 1.0 (no SIZE change)"


def test_lot_multiplier_can_be_set_to_1_5():
    c = _make_candidate(lot_multiplier=1.5)
    assert c.lot_multiplier == 1.5


def test_lot_multiplier_can_be_set_to_0_5():
    c = _make_candidate(lot_multiplier=0.5)
    assert c.lot_multiplier == 0.5


def test_lot_multiplier_can_be_zero_signals_skip():
    c = _make_candidate(lot_multiplier=0.0)
    assert c.lot_multiplier == 0.0


def test_as_tuple_unchanged_backward_compat():
    """as_tuple() must not break — backward compat with legacy callers."""
    c = _make_candidate(lot_multiplier=1.5)
    t = c.as_tuple()
    assert t == ("BUY", 70, 1.1000, 1.1050, ["test"], "bb_rsi_reversion", 1.0)


def test_lot_multiplier_negative_allowed_but_treated_by_caller():
    """We do NOT validate at dataclass level. Caller (demo_trader) clamps."""
    c = _make_candidate(lot_multiplier=-0.5)
    assert c.lot_multiplier == -0.5  # raw value preserved; clamping is caller's job
