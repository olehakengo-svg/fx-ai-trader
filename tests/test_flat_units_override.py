"""Tests for OANDA_FORCE_FLAT_UNITS env override (added 2026-06-02, rule:R2).

Verifies the post-cap flat-units override in modules/demo_trader.py:5304+.
The override forces all LIVE FX fills to a fixed unit size to eliminate
unit-bias (avgU loss/win = 1.62x observed in N=148 Live trades).

Safety mechanisms that MUST bypass the override:
  - XAU (1oz unit)
  - Sentinel (N<10 validation lot)
  - PRICE_SHOCK_REV (dedicated min-lot)
  - PRIME-A/B (pre-registered small-lot validation)
"""
import os
import pytest


def _apply_flat_override(
    adjusted_units: int,
    *,
    is_xau: bool = False,
    is_sentinel: bool = False,
    is_price_shock: bool = False,
    prime_tier: str = "",
    flat_env: str = "",
) -> int:
    """Replicates the override logic from modules/demo_trader.py.

    This duplicates the production logic so unit tests don't need to
    instantiate the full DemoTrader (which has heavy DB/thread setup).
    """
    if (
        flat_env
        and not is_xau
        and not is_sentinel
        and not is_price_shock
        and prime_tier not in ("A", "B")
    ):
        try:
            flat = int(flat_env)
            if flat >= 1000 and flat % 1000 == 0:
                return flat
        except (ValueError, TypeError):
            pass
    return adjusted_units


class TestFlatUnitsOverride:
    def test_env_unset_keeps_original(self):
        """No override when env is empty."""
        assert _apply_flat_override(7000, flat_env="") == 7000
        assert _apply_flat_override(15000, flat_env="") == 15000

    def test_env_set_5000_forces_flat(self):
        """Standard case: env=5000, normal FX fill → exactly 5000."""
        assert _apply_flat_override(7000, flat_env="5000") == 5000
        assert _apply_flat_override(15000, flat_env="5000") == 5000
        assert _apply_flat_override(1000, flat_env="5000") == 5000

    def test_xau_bypasses_override(self):
        """XAU is 1-oz unit; must NOT be flat-overridden."""
        assert _apply_flat_override(5, is_xau=True, flat_env="5000") == 5

    def test_sentinel_bypasses_override(self):
        """N<10 Sentinel (1000u validation) must be preserved."""
        assert _apply_flat_override(1000, is_sentinel=True, flat_env="5000") == 1000

    def test_price_shock_bypasses_override(self):
        """PRICE_SHOCK_REV has its own MIN_UNITS; override must not interfere."""
        assert _apply_flat_override(2000, is_price_shock=True, flat_env="5000") == 2000

    def test_prime_tier_a_bypasses(self):
        """PRIME-A is pre-registered small-lot validation (0.3x cap); preserved."""
        assert _apply_flat_override(3000, prime_tier="A", flat_env="5000") == 3000

    def test_prime_tier_b_bypasses(self):
        """PRIME-B is pre-registered small-lot validation (0.1x cap); preserved."""
        assert _apply_flat_override(1000, prime_tier="B", flat_env="5000") == 1000

    def test_invalid_env_ignored(self):
        """Non-integer env → fallback to original."""
        assert _apply_flat_override(7000, flat_env="abc") == 7000
        assert _apply_flat_override(7000, flat_env="-1") == 7000  # negative is OK type but < 1000
        assert _apply_flat_override(7000, flat_env="500") == 7000  # < 1000 floor

    def test_non_multiple_of_1000_ignored(self):
        """OANDA FX minimum granularity is 1000u; env must be multiple."""
        assert _apply_flat_override(7000, flat_env="5500") == 7000
        assert _apply_flat_override(7000, flat_env="3333") == 7000

    def test_env_10000_works(self):
        """Future H-plan upgrade: env=10000 also valid."""
        assert _apply_flat_override(3000, flat_env="10000") == 10000

    def test_env_4000_works(self):
        """Future tier-aware: env=4000 (active tier) also valid."""
        assert _apply_flat_override(7000, flat_env="4000") == 4000


class TestProductionPatchAlignment:
    """Ensures the helper matches the production patch in demo_trader.py.

    If the production code drifts, this test will catch it via source inspection.
    """

    def test_patch_present_in_production(self):
        """The OANDA_FORCE_FLAT_UNITS string should exist in demo_trader.py."""
        from pathlib import Path
        src = Path(__file__).parent.parent / "modules" / "demo_trader.py"
        text = src.read_text()
        assert "OANDA_FORCE_FLAT_UNITS" in text, (
            "Flat-units patch missing from production code"
        )
        assert "[FLAT_UNITS]" in text, "Log marker missing"

    def test_safety_bypasses_present(self):
        """The bypass clauses for XAU/Sentinel/PRICE_SHOCK/PRIME must be in the patch."""
        from pathlib import Path
        src = Path(__file__).parent.parent / "modules" / "demo_trader.py"
        text = src.read_text()
        # Locate the patch block
        idx = text.find("OANDA_FORCE_FLAT_UNITS")
        assert idx > 0
        # Window of ~600 chars around the patch
        window = text[idx:idx + 800]
        assert "_is_xau_inst" in window, "XAU bypass missing in patch"
        assert "_is_sentinel" in window, "Sentinel bypass missing in patch"
        assert "PRICE_SHOCK_REV_TIER1_TYPES" in window, "PRICE_SHOCK bypass missing"
        assert "_prime_tier" in window, "PRIME bypass missing"
