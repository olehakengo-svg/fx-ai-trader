"""Regression tests for shadow-tracking audit block_reason fidelity."""

import pytest

from modules.demo_trader import (
    SHADOW_AUDIT_REASONS,
    SHADOW_TRACKING_BLOCK_REASON,
    _resolve_shadow_audit_block_reason,
    _shadow_audit_log_fragment,
)


LOCKED_SHADOW_CASES = [
    ("slot_bypass", "slot_full_shadow_overflow"),
    ("max_open_bypass", "max_open_global_cap_shadow"),
    ("active_hours_bypass", "out_of_active_hours_shadow_eligible"),
    ("alpha_scan", "alpha_scan_toxic_segment_shadow"),
    ("mtf_downgrade", "mtf_conflict_downgrade_non_elite"),
    ("regime_guardrail", "regime_guardrail_directional_shadow"),
    ("emergency_trip", "emergency_kill_switch_shadow"),
    ("q4_gate", "q4_paradox_non_elite_shadow"),
    ("not_promoted_safety_net", "not_promoted_safety_net_shadow"),
    ("phase0_tier_gate", "phase0_three_tier_routing_shadow"),
    ("post_gate_late_oanda_shield", "post_gate_late_oanda_shield_shadow"),
]


def _synthetic_shadow_audit_row(condition: str) -> dict:
    block_reason = _resolve_shadow_audit_block_reason(
        True, SHADOW_AUDIT_REASONS[condition]
    )
    return {
        "is_shadow": True,
        "bridge_status": "skipped",
        "block_reason": block_reason,
        "log_fragment": _shadow_audit_log_fragment(True, block_reason, "B"),
    }


@pytest.mark.parametrize(("condition", "expected"), LOCKED_SHADOW_CASES)
def test_shadow_subcondition_writes_specific_block_reason(condition, expected):
    row = _synthetic_shadow_audit_row(condition)

    assert row["block_reason"] == expected
    assert row["log_fragment"] == (
        f"is_shadow=true | block_reason={expected} | tier_state=B"
    )


def test_shadow_tracking_literal_remains_backward_compat_fallback():
    assert (
        _resolve_shadow_audit_block_reason(True, "")
        == SHADOW_TRACKING_BLOCK_REASON
    )
    assert SHADOW_TRACKING_BLOCK_REASON == "shadow_tracking"


def test_non_shadow_has_no_shadow_block_reason():
    assert (
        _resolve_shadow_audit_block_reason(False, "slot_full_shadow_overflow")
        == ""
    )
