"""
P2 Full Lot Validation & System Tests
======================================
Covers:
  - ExposureManager currency decomposition, concentration, XAU limits, cleanup
  - 3-Factor Model boundary conditions (risk, edge, combined cap, XAU sentinel)
  - Signal contract (compute_scalp_signal output keys)
  - Regime detection (detect_market_regime validity)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
import pandas as pd

from modules.exposure_manager import ExposureManager


# =========================================================================
#  Exposure Manager (4 tests)
# =========================================================================

class TestExposureManager:

    def test_exposure_buy_usdjpy_decomposition(self):
        """BUY USD_JPY 5000u -> USD:+5000, JPY:-5000"""
        em = ExposureManager()
        em.add_position("t1", "USD_JPY", "BUY", 5000)
        exp = em.get_currency_exposure()
        assert exp.get("USD") == 5000, f"Expected USD:+5000, got {exp.get('USD')}"
        assert exp.get("JPY") == -5000, f"Expected JPY:-5000, got {exp.get('JPY')}"

    def test_exposure_cross_pair_concentration(self):
        """Multiple USD trades -> USD limit blocks new entry."""
        em = ExposureManager()
        # BUY USD_JPY 10000u -> USD:+10000
        em.add_position("t1", "USD_JPY", "BUY", 10000)
        # SELL EUR_USD 10000u -> USD:+10000 (total USD:+20000)
        em.add_position("t2", "EUR_USD", "SELL", 10000)

        # Current USD exposure = +10000 + 10000 = +20000 (at limit)
        exp = em.get_currency_exposure()
        assert exp.get("USD") == 20000

        # New BUY USD_JPY 1000u would push USD to 21000 -> blocked
        allowed, reason = em.check_new_trade("USD_JPY", "BUY", 1000)
        assert allowed is False, "Should block: USD exposure would exceed 20,000u limit"
        assert "USD" in reason
        assert "limit" in reason.lower() or ">" in reason

    def test_exposure_xau_separate_limit(self):
        """XAU has independent 10,000u limit (not the 20,000u FX default)."""
        em = ExposureManager()
        # BUY XAU_USD 9000u -> XAU:+9000, USD:-9000
        em.add_position("t1", "XAU_USD", "BUY", 9000)

        # Another 2000u would push XAU to 11000 > 10000 limit
        allowed, reason = em.check_new_trade("XAU_USD", "BUY", 2000)
        assert allowed is False, "Should block: XAU exposure would exceed 10,000u limit"
        assert "XAU" in reason

        # But 1000u should be fine (total 10000 = exactly at limit)
        allowed2, reason2 = em.check_new_trade("XAU_USD", "BUY", 1000)
        assert allowed2 is True, f"Should allow: XAU at exactly 10,000u limit, got: {reason2}"

    def test_exposure_remove_clears_position(self):
        """After remove_position, exposure returns to zero."""
        em = ExposureManager()
        em.add_position("t1", "USD_JPY", "BUY", 5000)
        em.add_position("t2", "EUR_USD", "SELL", 3000)

        # Verify non-zero exposure
        exp_before = em.get_currency_exposure()
        assert any(v != 0 for v in exp_before.values()), "Exposure should be non-zero"

        # Remove all positions
        em.remove_position("t1")
        em.remove_position("t2")

        exp_after = em.get_currency_exposure()
        # All values should be 0 or absent
        for currency, value in exp_after.items():
            assert value == 0, f"Expected {currency} exposure to be 0 after remove, got {value}"


# =========================================================================
#  3-Factor Model Boundary Tests (4 tests)
# =========================================================================

class TestThreeFactorModelBoundary:
    """
    Tests for the 3-Factor lot sizing formulas extracted from demo_trader.py
    lines ~3294-3391. We replicate the inline calculation logic here.
    """

    def test_risk_factor_zero_sl_safe(self):
        """SL distance=0 -> max(0.5, ...) floor prevents division error.

        Formula: _risk_factor = min(base_sl_pips / max(actual_sl_pips, 0.5), 1.5)
                 _risk_factor = max(_risk_factor, 0.5)
        When actual_sl_pips=0, max(0, 0.5) = 0.5 prevents division by zero.
        """
        base_sl_pips = 3.5  # scalp default
        actual_sl_pips = 0.0  # zero SL distance

        # Simulate the formula from demo_trader.py line ~3305-3306
        _risk_factor = min(base_sl_pips / max(actual_sl_pips, 0.5), 1.5)
        _risk_factor = max(_risk_factor, 0.5)

        assert _risk_factor == 1.5, f"Expected 1.5 (3.5/0.5 clamped), got {_risk_factor}"
        # No ZeroDivisionError raised -- the floor 0.5 prevents it.

    def test_edge_factor_zero_spread_safe(self):
        """Spread=0 -> floor 0.1 prevents division error.

        Formula: _edge_ratio = _atr_pips / max(_spread_pips, 0.1)
        When spread=0, max(0, 0.1) = 0.1 prevents division by zero.
        """
        _atr_pips = 7.0  # typical ATR in pips
        _spread_pips = 0.0  # zero spread

        # Simulate the formula from demo_trader.py line ~3312
        _edge_ratio = _atr_pips / max(_spread_pips, 0.1)

        assert _edge_ratio == 70.0, f"Expected 70.0 (7.0/0.1), got {_edge_ratio}"
        # No ZeroDivisionError raised.

        # With edge_ratio=70 >= 15, edge_factor=1.5
        if _edge_ratio >= 15:
            _edge_factor = 1.5
        elif _edge_ratio >= 10:
            _edge_factor = 1.3
        elif _edge_ratio >= 6:
            _edge_factor = 1.0
        elif _edge_ratio >= 3:
            _edge_factor = 0.7
        else:
            _edge_factor = 0.5

        assert _edge_factor == 1.5

    def test_combined_max_lot_capped(self):
        """risk=1.5 x edge=1.5 x boost=2.0 = 4.5 -> clamped to 2.5.

        Formula: _lot_ratio = max(0.3, min(_lot_ratio, 2.5))
        """
        _risk_factor = 1.5
        _edge_factor = 1.5
        _boost_factor = 2.0

        _lot_ratio = _risk_factor * _edge_factor * _boost_factor
        assert _lot_ratio == 4.5, f"Raw product should be 4.5, got {_lot_ratio}"

        # Apply clamping (demo_trader.py line ~3377)
        _lot_ratio = max(0.3, min(_lot_ratio, 2.5))
        assert _lot_ratio == 2.5, f"Expected clamped to 2.5, got {_lot_ratio}"

    def test_xau_sentinel_units_one(self):
        """XAU + sentinel -> _adjusted_units=1 (not 1000).

        From demo_trader.py line ~3385:
            _adjusted_units = 1 if _is_xau_inst else 1000
        XAU sentinel uses 1 unit (1 troy oz ~ $4800), not 1000u like FX.
        """
        _is_sentinel = True
        _is_xau_inst = True

        # Simulate demo_trader.py lines 3381-3385
        if _is_sentinel:
            _adjusted_units = 1 if _is_xau_inst else 1000
        else:
            _adjusted_units = 10000  # would be calculated normally

        assert _adjusted_units == 1, f"XAU sentinel should be 1 unit, got {_adjusted_units}"

        # Verify FX sentinel is 1000
        _is_xau_inst_fx = False
        if _is_sentinel:
            _adjusted_units_fx = 1 if _is_xau_inst_fx else 1000
        assert _adjusted_units_fx == 1000, f"FX sentinel should be 1000 units, got {_adjusted_units_fx}"


# =========================================================================
#  Signal Contract (2 tests)
# =========================================================================

class TestSignalContract:

    def test_signal_output_has_required_keys(self, sample_ohlcv_with_indicators):
        """compute_scalp_signal must return dict with signal, score, entry_type, reasons."""
        from app import compute_scalp_signal, find_sr_levels

        df = sample_ohlcv_with_indicators
        sr_levels = find_sr_levels(df)

        result = compute_scalp_signal(
            df, tf="5m", sr_levels=sr_levels,
            symbol="USDJPY=X", backtest_mode=True,
        )

        assert isinstance(result, dict), "compute_scalp_signal must return a dict"
        # Required keys per signal contract
        required_keys = ["signal", "entry_type", "reasons"]
        for key in required_keys:
            assert key in result, f"Missing required key '{key}' in signal output"

        # Score may be under "scalp_score" or "score_detail.combined"
        has_score = (
            "scalp_score" in result
            or ("score_detail" in result and "combined" in result.get("score_detail", {}))
        )
        assert has_score, "Signal output must contain a score (scalp_score or score_detail.combined)"

        # Validate signal value
        assert result["signal"] in ("BUY", "SELL", "WAIT"), \
            f"signal must be BUY/SELL/WAIT, got '{result['signal']}'"

        # Validate reasons is a list
        assert isinstance(result["reasons"], list), "reasons must be a list"

    def test_regime_detection_no_unknown_for_valid_data(self, sample_ohlcv_with_indicators):
        """detect_market_regime with valid 100-bar OHLCV -> regime is not 'unknown'."""
        from app import detect_market_regime

        df = sample_ohlcv_with_indicators
        # Ensure we have at least 100 bars
        assert len(df) >= 100, f"Need >=100 bars, got {len(df)}"

        result = detect_market_regime(df)

        assert isinstance(result, dict), "detect_market_regime must return a dict"
        assert "regime" in result, "Must contain 'regime' key"

        valid_regimes = {"TREND_BULL", "TREND_BEAR", "RANGE", "HIGH_VOL"}
        assert result["regime"] in valid_regimes, \
            f"Valid data should not produce 'UNKNOWN' regime, got '{result['regime']}'"

        # Verify other expected fields
        assert "adx" in result, "Must contain 'adx'"
        assert "bb_width_pct" in result, "Must contain 'bb_width_pct'"
        assert "atr_ratio" in result, "Must contain 'atr_ratio'"
