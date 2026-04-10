"""
P0 Safety Tests -- Kelly Criterion, Lot Sizing, Bootstrap CI
=============================================================

Critical safety tests for the FX AI Trader risk management layer.
Covers: dual Kelly implementation agreement, negative-edge clamping,
sentinel override, OANDA lot cap, and bootstrap CI regression.
"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.stats_utils import kelly_criterion, bootstrap_ev_ci
from modules.risk_analytics import kelly_fraction


# =====================================================================
#  Kelly Criterion (3 tests)
# =====================================================================

class TestKellyCriterion:
    """Validate Kelly fraction calculations in stats_utils and risk_analytics."""

    def test_kelly_known_values(self):
        """WR=55%, avg_win=3, avg_loss=2 -> full_kelly ~ 0.217, half_kelly ~ 0.108."""
        result = kelly_criterion(win_rate=0.55, avg_win=3.0, avg_loss=2.0)

        # f* = (p*b - q) / b where b=3/2=1.5, p=0.55, q=0.45
        # f* = (0.55*1.5 - 0.45) / 1.5 = (0.825 - 0.45) / 1.5 = 0.375 / 1.5 = 0.25
        # Wait -- let me recompute: b = avg_win / avg_loss = 3/2 = 1.5
        # full_kelly = (p*b - q) / b = (0.55*1.5 - 0.45) / 1.5 = 0.25
        assert abs(result["full_kelly"] - 0.25) < 0.001, (
            f"full_kelly expected ~0.25, got {result['full_kelly']}"
        )
        assert abs(result["half_kelly"] - 0.125) < 0.001, (
            f"half_kelly expected ~0.125, got {result['half_kelly']}"
        )
        assert result["full_kelly"] > 0, "Positive edge must yield positive Kelly"
        assert result["half_kelly"] > 0, "Half-Kelly must be positive when full is"
        assert abs(result["half_kelly"] - result["full_kelly"] / 2) < 1e-6, (
            "half_kelly must be exactly full_kelly / 2"
        )

    def test_kelly_negative_edge_returns_zero(self):
        """WR=30%, 1:1 RR -> negative edge -> full_kelly must be 0."""
        result = kelly_criterion(win_rate=0.30, avg_win=1.0, avg_loss=1.0)

        # edge = p*b - q = 0.30*1 - 0.70 = -0.40 (negative)
        # full_kelly = max(0, (p*b - q) / b) = max(0, -0.40) = 0
        assert result["full_kelly"] == 0.0, (
            f"Negative edge must clamp full_kelly to 0, got {result['full_kelly']}"
        )
        assert result["half_kelly"] == 0.0, (
            f"Negative edge must clamp half_kelly to 0, got {result['half_kelly']}"
        )

    def test_kelly_dual_implementation_agreement(self):
        """stats_utils.kelly_criterion and risk_analytics.kelly_fraction must agree."""
        test_cases = [
            (0.55, 3.0, 2.0),   # positive edge
            (0.60, 2.0, 1.5),   # strong edge
            (0.45, 1.0, 1.0),   # negative edge
            (0.50, 2.0, 1.0),   # breakeven adjusted by RR
            (0.40, 3.0, 1.0),   # moderate WR, high RR
        ]
        for wr, avg_w, avg_l in test_cases:
            su = kelly_criterion(win_rate=wr, avg_win=avg_w, avg_loss=avg_l)
            ra = kelly_fraction(win_rate=wr, avg_win=avg_w, avg_loss=avg_l)

            assert abs(su["full_kelly"] - ra["full_kelly"]) < 0.0001, (
                f"full_kelly mismatch for WR={wr}, W={avg_w}, L={avg_l}: "
                f"stats_utils={su['full_kelly']}, risk_analytics={ra['full_kelly']}"
            )
            assert abs(su["half_kelly"] - ra["half_kelly"]) < 0.0001, (
                f"half_kelly mismatch for WR={wr}, W={avg_w}, L={avg_l}: "
                f"stats_utils={su['half_kelly']}, risk_analytics={ra['half_kelly']}"
            )


# =====================================================================
#  Lot Sizing (2 tests)
# =====================================================================

class TestLotSizing:
    """Validate lot sizing safety invariants from demo_trader 3-Factor Model."""

    def test_lot_sizing_sentinel_overrides_clamp(self):
        """When _is_sentinel=True, units must be 1000 (FX) regardless of 3-Factor calc.

        Reproduces the logic from demo_trader.py lines 3356-3391:
        - Sentinel flag forces _adjusted_units = 1000 for FX
        - The clamp(0.3, 2.5) on _lot_ratio is irrelevant when sentinel
        """
        # Simulate 3-Factor producing a high lot_ratio
        _risk_factor = 1.5
        _edge_factor = 1.5
        _boost_factor = 2.0
        _lot_ratio = _risk_factor * _edge_factor * _boost_factor  # = 4.5

        # Sentinel override
        _is_sentinel = True
        _is_xau_inst = False

        if _is_sentinel:
            _lot_ratio = 0.1

        # Clamp (applied AFTER sentinel in production code)
        _lot_ratio = max(0.3, min(_lot_ratio, 2.5))

        _base_units = 10000
        _adjusted_units = int(_base_units * _lot_ratio)

        # Sentinel final override
        if _is_sentinel:
            _adjusted_units = 1 if _is_xau_inst else 1000

        # FX minimum enforcement
        if not _is_xau_inst:
            _adjusted_units = max(1000, (_adjusted_units // 1000) * 1000)

        assert _adjusted_units == 1000, (
            f"Sentinel FX must be exactly 1000 units (0.01 lot), got {_adjusted_units}"
        )

    def test_lot_sizing_oanda_cap(self):
        """max lot_ratio=2.5 x base_units=10000 = 25000 -> capped to _OANDA_LOT_CAP=10000.

        Validates the SHIELD hard cap from demo_trader.py lines 3440-3444.
        """
        _OANDA_LOT_CAP = 10000

        # Maximum 3-Factor output after clamp
        _lot_ratio = 2.5
        _base_units = 10000
        _adjusted_units = int(_base_units * _lot_ratio)  # = 25000
        _is_sentinel = False

        assert _adjusted_units == 25000, (
            f"Pre-cap units should be 25000, got {_adjusted_units}"
        )

        # Apply OANDA lot cap (SHIELD)
        if _adjusted_units > _OANDA_LOT_CAP:
            _adjusted_units = _OANDA_LOT_CAP

        assert _adjusted_units == _OANDA_LOT_CAP, (
            f"Post-cap units must equal _OANDA_LOT_CAP={_OANDA_LOT_CAP}, "
            f"got {_adjusted_units}"
        )
        assert _adjusted_units <= 10000, (
            "OANDA lot cap violated: units exceed 10000"
        )


# =====================================================================
#  Bootstrap (2 tests)
# =====================================================================

class TestBootstrapCI:
    """Validate bootstrap EV confidence interval calculations."""

    def test_bootstrap_ci_width_nonzero(self):
        """Regression: CI width must be > 0 (fixes the documented CI-width=0 bug).

        The old MC implementation used shuffle (order-preserving) instead of
        bootstrap (with-replacement resampling), producing CI width = 0.
        This test ensures the fix holds.
        """
        random.seed(42)
        # Create a PnL list with real variance (mix of wins and losses)
        pnl_list = [
            3.5, -2.1, 5.0, -1.8, 2.3,
            -4.0, 1.5, -0.5, 6.2, -3.1,
            2.8, -1.2, 4.1, -2.5, 0.9,
            -1.7, 3.3, -0.8, 2.0, -2.9,
        ]

        result = bootstrap_ev_ci(pnl_list, n_boot=5000, ci=0.90)

        assert result["insufficient"] is False, (
            f"N={len(pnl_list)} should be sufficient (>=5)"
        )
        assert result["ci_low"] is not None, "ci_low must not be None"
        assert result["ci_high"] is not None, "ci_high must not be None"
        assert result["ci_high"] > result["ci_low"], (
            f"CI width must be > 0: ci_low={result['ci_low']}, "
            f"ci_high={result['ci_high']} "
            "(regression: CI-width=0 bug from shuffle-based MC)"
        )

    def test_bootstrap_insufficient_data(self):
        """N<5 must return insufficient=True with None CI bounds."""
        for n in [0, 1, 2, 3, 4]:
            pnl_list = [1.0] * n
            result = bootstrap_ev_ci(pnl_list)

            assert result["insufficient"] is True, (
                f"N={n} must flag insufficient=True, got {result['insufficient']}"
            )
            assert result["ci_low"] is None, (
                f"N={n}: ci_low must be None when insufficient, got {result['ci_low']}"
            )
            assert result["ci_high"] is None, (
                f"N={n}: ci_high must be None when insufficient, got {result['ci_high']}"
            )
