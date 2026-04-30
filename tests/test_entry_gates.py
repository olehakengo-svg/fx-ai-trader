"""
Entry Gate Tests — C1/C2/H1/H2 audit fixes (2026-04-30)

Audit findings (see plans/shadow-open-position-cozy-quilt.md):
  C1 — ExposureManager bypass was gated on `_is_shadow_eligible`, allowing
       FORCE_DEMOTED strategies entering as Live to skip exposure caps.
  C2 — Cooldown key was `mode` only, blocking unrelated pairs and reverse
       directions on a single SL exit.
  H1 — Per-cell limits excluded shadow entirely, allowing duplicate
       observations on a single price process.
  H2 — Hedge bypass routed reverse-direction signals to shadow, polluting
       the score-max selection ranking.

These are unit-level regression tests on the affected helpers and gates.
Full integration via _tick_entry is covered by production-log monitoring.
"""

import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =====================================================================
#  C2 — Cooldown key independence
# =====================================================================

class TestCooldownKeyIndependence:
    """`_last_exit` must be keyed by (mode, instrument, direction, is_shadow)."""

    def _make_trader(self):
        from modules.demo_trader import DemoTrader
        from modules.demo_db import DemoDB
        db = DemoDB(":memory:")
        return DemoTrader(db)

    def test_cooldown_key_distinguishes_pair(self):
        """USD_JPY scalp SL must NOT block EUR_USD scalp."""
        t = self._make_trader()
        now = datetime.now(timezone.utc)
        k_usd = t._cooldown_key("scalp", "USD_JPY", "BUY", False)
        k_eur = t._cooldown_key("scalp", "EUR_USD", "BUY", False)
        t._last_exit[k_usd] = {"time": now, "outcome": "SL_HIT"}

        # Same pair/direction -> blocked
        age_usd = t._get_cooldown_age("scalp", "USD_JPY", "BUY", is_shadow=False)
        assert age_usd is not None and age_usd < 1, "Same pair must hit cooldown"
        # Different pair -> independent
        age_eur = t._get_cooldown_age("scalp", "EUR_USD", "BUY", is_shadow=False)
        assert age_eur is None, "Different pair must NOT inherit cooldown"

    def test_cooldown_key_distinguishes_direction(self):
        """BUY SL must NOT block SELL on same pair (consec_loss is direction-aware)."""
        t = self._make_trader()
        now = datetime.now(timezone.utc)
        t._last_exit[t._cooldown_key("scalp", "USD_JPY", "BUY", False)] = {
            "time": now, "outcome": "SL_HIT"
        }
        assert t._get_cooldown_age("scalp", "USD_JPY", "BUY", is_shadow=False) is not None
        assert t._get_cooldown_age("scalp", "USD_JPY", "SELL", is_shadow=False) is None

    def test_cooldown_key_distinguishes_shadow(self):
        """Shadow exit must NOT block Live entry, and vice-versa."""
        t = self._make_trader()
        now = datetime.now(timezone.utc)
        t._last_exit[t._cooldown_key("scalp", "USD_JPY", "BUY", True)] = {
            "time": now, "outcome": "SL_HIT"
        }
        # Shadow cooldown does not apply to Live entry
        assert t._get_cooldown_age("scalp", "USD_JPY", "BUY", is_shadow=False) is None
        # ...but applies to Shadow entry on the same key
        assert t._get_cooldown_age("scalp", "USD_JPY", "BUY", is_shadow=True) is not None

    def test_cooldown_age_returns_seconds(self):
        """Age must be a non-negative float in seconds."""
        t = self._make_trader()
        past = datetime.now(timezone.utc) - timedelta(seconds=42)
        t._last_exit[t._cooldown_key("daytrade", "GBP_USD", "SELL", False)] = {
            "time": past, "outcome": "SL_HIT"
        }
        age = t._get_cooldown_age("daytrade", "GBP_USD", "SELL", is_shadow=False)
        assert age is not None and 41 <= age <= 60


# =====================================================================
#  H1 — Per-cell shadow cap is finite
# =====================================================================

class TestPerCellShadowCap:
    """Shadow per-cell cap must be configured and < unbounded."""

    def test_shadow_per_cell_limits_present_for_main_modes(self):
        """The H1 patch defines per-cell shadow caps for all known modes."""
        # Read the source to confirm the dict is present (white-box assertion).
        # We do not import the runtime since exercising _tick_entry needs full
        # market data. The constant existence and values are the contract.
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "modules", "demo_trader.py",
        )
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        assert "_shadow_per_cell_limits" in src, (
            "H1 patch missing — _shadow_per_cell_limits dict not found"
        )
        # Values: scalp=4, scalp_5m=2, daytrade=2, daytrade_1h=2, swing=2
        for token in (
            '"scalp": 4', '"scalp_5m": 2', '"daytrade": 2',
            '"daytrade_1h": 2', '"swing": 2',
        ):
            assert token in src, f"H1 missing entry: {token}"


# =====================================================================
#  H2 — Hedge bypass removed
# =====================================================================

class TestHedgeBypassRemoved:
    """Hedge gate must always block; no shadow escape route."""

    def test_hedge_block_has_no_shadow_bypass(self):
        """The string `[SHADOW] Hedge bypass` must no longer be emitted."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "modules", "demo_trader.py",
        )
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        assert "[SHADOW] Hedge bypass" not in src, (
            "H2 patch missing — hedge bypass log line still present"
        )
        # `hedge_block(...)` _block call must remain
        assert "hedge_block(" in src, (
            "Hedge gate disappeared entirely — should still block, just no bypass"
        )


# =====================================================================
#  C1 — Exposure check runs for all Live entries
# =====================================================================

class TestExposureBypassNarrowed:
    """Exposure check must be gated on `_is_shadow`, not `_is_shadow_eligible`."""

    def test_exposure_check_uses_is_shadow_not_eligible(self):
        """The patched line must read `if not _is_shadow:` (no `_eligible` suffix)."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "modules", "demo_trader.py",
        )
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        # Find the exposure check block by anchoring on the comment
        anchor = "Cross-pair Exposure Check"
        idx = src.find(anchor)
        assert idx >= 0, "Exposure check block missing"
        block = src[idx:idx + 1200]
        assert "if not _is_shadow:" in block, (
            "C1 patch missing — bypass should be gated on `_is_shadow`"
        )
        assert "if not _is_shadow_eligible:" not in block, (
            "C1 patch incomplete — old `_is_shadow_eligible` gate still present"
        )
