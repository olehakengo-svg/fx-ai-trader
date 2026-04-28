"""STRATEGY_PROFILES wiring — promotion-gate threshold tests (P0#3 audit fix).

Validates that ``DemoTrader._decide_promotion_status`` consults
``STRATEGY_PROFILES`` (kpi_wr / kpi_ev) per strategy mode, while
unmapped strategies fall back to the legacy hardcoded thresholds.

Mode A (Trend Following — e.g. bb_rsi_reversion / scalp系):
    N>=20, WR>=kpi_wr*100 (=30), EV>=max(friction, kpi_ev)
Mode B (Mean Reversion — e.g. sr_fib_confluence / dt系):
    N>=30, WR>=kpi_wr*100 (=55), EV>=max(friction, kpi_ev)
Unmapped:
    Legacy fast (N>=20 & WR>=60) or normal (N>=30) gate.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.config import (  # noqa: E402
    STRATEGY_PROFILES,
    STRATEGY_PROFILE_MODE_A,
    STRATEGY_PROFILE_MODE_B,
    get_strategy_profile_mode,
)
from modules.demo_trader import DemoTrader  # noqa: E402


_FRICTION = 1.0  # default friction (matches _BT_COST_PER_TRADE)


def _gate(et, n, wr, ev, *, wilson_pass=True, kelly_block=False, old="pending",
          stats=None):
    """Thin wrapper around the static gate decision."""
    return DemoTrader._decide_promotion_status(
        et, n, wr, ev, _FRICTION,
        wilson_pass, kelly_block, old, stats or {},
    )


# =====================================================================
#  Mapping sanity
# =====================================================================

def test_mode_mapping_known_strategies():
    """Known scalp/dt entries resolve to A / B respectively."""
    assert get_strategy_profile_mode("bb_rsi_reversion") == "A"
    assert get_strategy_profile_mode("sr_fib_confluence") == "B"
    assert get_strategy_profile_mode("dt_fib_reversal") == "B"


def test_mode_mapping_unknown_returns_none():
    """Unmapped entry types return None (→ legacy gate path)."""
    assert get_strategy_profile_mode("not_a_real_strategy_xyz") is None


def test_mode_a_and_b_sets_disjoint():
    """A and B sets must not overlap — would make get_strategy_profile_mode
    order-dependent."""
    assert STRATEGY_PROFILE_MODE_A.isdisjoint(STRATEGY_PROFILE_MODE_B)


def test_strategy_profiles_kpi_keys_present():
    """Sanity: STRATEGY_PROFILES still exposes kpi_wr / kpi_ev for both modes."""
    for k in ("A", "B"):
        assert "kpi_wr" in STRATEGY_PROFILES[k]
        assert "kpi_ev" in STRATEGY_PROFILES[k]


# =====================================================================
#  Mode A — promote at WR=35% (>=kpi_wr=30%) with N>=20
# =====================================================================

def test_mode_a_promotes_at_low_wr():
    """Mode A: WR=35% (>30% kpi) at N=22, EV=2.0 (>friction 1.0) → promote."""
    status, reason, meta = _gate("bb_rsi_reversion", n=22, wr=35.0, ev=2.0)
    assert status == "promoted", f"reason={reason}"
    assert meta["mode"] == "A"
    assert meta["kpi_wr_threshold"] == 30.0
    assert meta["n_min"] == 20
    assert "mode_A_promote" in reason


def test_mode_a_blocked_below_wr_threshold():
    """Mode A: WR=25% (<30% kpi) → no promote (falls through to no_change)."""
    status, _reason, meta = _gate("bb_rsi_reversion", n=50, wr=25.0, ev=2.0)
    assert status == "pending"
    assert meta["mode"] == "A"


def test_mode_a_blocked_below_n_min():
    """Mode A: N=15 (<20) → no promote even if WR / EV high."""
    status, _reason, meta = _gate("bb_rsi_reversion", n=15, wr=70.0, ev=3.0)
    assert status == "pending"
    assert meta["mode"] == "A"


def test_mode_a_blocked_by_kelly_negative():
    """Kelly<0 must block Mode A promote (P0#3 guard preserved)."""
    status, _reason, _meta = _gate(
        "bb_rsi_reversion", n=30, wr=40.0, ev=2.0, kelly_block=True,
    )
    assert status == "pending"


def test_mode_a_blocked_by_wilson_fail():
    """Wilson_BF lower-bound failure must block Mode A promote."""
    status, _reason, _meta = _gate(
        "bb_rsi_reversion", n=30, wr=40.0, ev=2.0, wilson_pass=False,
    )
    assert status == "pending"


# =====================================================================
#  Mode B — must clear higher 55% bar
# =====================================================================

def test_mode_b_blocked_at_wr_below_kpi():
    """Mode B: WR=50% (<55% kpi) at N=40 → no promote (kpi_wr=0.55)."""
    status, _reason, meta = _gate("sr_fib_confluence", n=40, wr=50.0, ev=2.0)
    assert status == "pending", (
        f"expected pending — Mode B requires WR>=55%, got status={status}"
    )
    assert meta["mode"] == "B"
    assert meta["kpi_wr_threshold"] == 55.0
    assert meta["n_min"] == 30


def test_mode_b_promotes_at_kpi_satisfied():
    """Mode B: WR=58% (>55%) at N=40 → promote."""
    status, reason, meta = _gate("sr_fib_confluence", n=40, wr=58.0, ev=2.0)
    assert status == "promoted", f"reason={reason}"
    assert meta["mode"] == "B"


def test_mode_b_blocked_below_n_min():
    """Mode B requires N>=30 even when WR/EV pass."""
    status, _reason, _meta = _gate("sr_fib_confluence", n=25, wr=60.0, ev=2.0)
    assert status == "pending"


# =====================================================================
#  Unmapped strategy — legacy gate path
# =====================================================================

def test_unmapped_uses_legacy_fast_track():
    """Unmapped strategy: legacy fast-track (N>=20 & WR>=60%) still applies."""
    status, reason, meta = _gate(
        "totally_unknown_strategy", n=22, wr=65.0, ev=2.0,
    )
    assert status == "promoted"
    assert meta["mode"] is None
    assert "legacy_fast_promote" in reason


def test_unmapped_legacy_fast_track_blocked_below_60():
    """Unmapped: WR=55% (<60% legacy threshold), N=20 → not fast-promoted."""
    status, _reason, _meta = _gate(
        "totally_unknown_strategy", n=22, wr=55.0, ev=2.0,
    )
    assert status == "pending"


def test_unmapped_uses_legacy_normal_track():
    """Unmapped: legacy normal-track (N>=30, no WR floor) applies."""
    status, reason, meta = _gate(
        "totally_unknown_strategy", n=35, wr=45.0, ev=2.0,
    )
    assert status == "promoted"
    assert meta["mode"] is None
    assert "legacy_normal_promote" in reason


# =====================================================================
#  Demote / recovery gates remain mode-agnostic
# =====================================================================

def test_demote_low_ev_applies_to_mode_a():
    """Mode A strategy with EV=-0.8 (<-0.5) at N=25 still demotes."""
    status, reason, _meta = _gate(
        "bb_rsi_reversion", n=25, wr=20.0, ev=-0.8,
    )
    assert status == "demoted"
    assert "auto_demote" in reason


def test_demote_low_ev_applies_to_mode_b():
    """Mode B strategy with EV=-0.8 at N=25 demotes (gate is mode-agnostic)."""
    status, reason, _meta = _gate(
        "sr_fib_confluence", n=25, wr=20.0, ev=-0.8,
    )
    assert status == "demoted"
    assert "auto_demote" in reason


def test_demoted_recovery_n30_ev_positive():
    """old=demoted with N>=30 & EV>0 → pending (recovery)."""
    status, reason, _meta = _gate(
        "sr_fib_confluence", n=35, wr=40.0, ev=0.3, old="demoted",
    )
    assert status == "pending"
    assert "demoted_recovery" in reason


def test_no_data_keeps_existing_status():
    """Low-N pending strategy with no signal stays pending."""
    status, reason, _meta = _gate(
        "bb_rsi_reversion", n=5, wr=50.0, ev=0.5, old="pending",
    )
    assert status == "pending"
    assert reason == "no_change"


# =====================================================================
#  EV threshold = max(friction, kpi_ev)
# =====================================================================

def test_mode_a_ev_below_friction_blocks_even_with_kpi_ev_passed():
    """EV must clear friction (1.0) — kpi_ev=0.08 alone is insufficient."""
    status, _reason, _meta = DemoTrader._decide_promotion_status(
        "bb_rsi_reversion", 30, 40.0, 0.5, _FRICTION,
        True, False, "pending", {},
    )
    # 0.5 < friction 1.0 → blocked
    assert status == "pending"
