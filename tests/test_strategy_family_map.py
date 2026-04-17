"""v9.3 P0: Strategy family map + alignment tests."""
import pytest

from research.edge_discovery.strategy_family_map import (
    STRATEGY_FAMILY, REGIME_ADAPTIVE_FAMILY,
    strategy_aware_alignment, effective_family,
)


class TestFamilyMap:
    def test_p0_reclassifications_applied(self):
        """P0 diagnostic-driven re-classifications are present."""
        assert STRATEGY_FAMILY["macdh_reversal"] == "TF"
        assert STRATEGY_FAMILY["engulfing_bb"] == "TF"
        assert STRATEGY_FAMILY["ema_cross"] == "MR"

    def test_known_families_present(self):
        for s in ("ema_trend_scalp", "bb_rsi_reversion",
                  "bb_squeeze_breakout", "session_time_bias"):
            assert s in STRATEGY_FAMILY


class TestAlignment:
    def test_tf_up_trend_buy_aligned(self):
        r = strategy_aware_alignment(
            "ema_trend_scalp", "trend_up_weak", "BUY", "USD_JPY"
        )
        assert r == "aligned"

    def test_tf_up_trend_sell_conflict(self):
        r = strategy_aware_alignment(
            "ema_trend_scalp", "trend_up_weak", "SELL", "USD_JPY"
        )
        assert r == "conflict"

    def test_tf_range_conflict(self):
        r = strategy_aware_alignment(
            "ema_trend_scalp", "range_tight", "BUY", "EUR_USD"
        )
        assert r == "conflict"

    def test_mr_up_trend_sell_aligned(self):
        # sr_channel_reversal は非 adaptive (常に MR)
        r = strategy_aware_alignment(
            "sr_channel_reversal", "trend_up_weak", "SELL", "EUR_USD"
        )
        assert r == "aligned"

    def test_mr_up_trend_buy_conflict(self):
        r = strategy_aware_alignment(
            "sr_channel_reversal", "trend_up_weak", "BUY", "EUR_USD"
        )
        assert r == "conflict"

    def test_mr_range_aligned(self):
        r = strategy_aware_alignment(
            "sr_channel_reversal", "range_tight", "BUY", "EUR_USD"
        )
        assert r == "aligned"

    def test_mr_jpy_exception_up_strong(self):
        """JPY carry継続: strong_up × SELL = conflict (not aligned)"""
        r = strategy_aware_alignment(
            "sr_channel_reversal", "trend_up_strong", "SELL", "USD_JPY"
        )
        assert r == "conflict"

    def test_tf_non_jpy_strong_up_exhaustion(self):
        """non-JPY trend_up_strong = exhaustion, TF BUY conflict"""
        r = strategy_aware_alignment(
            "ema_trend_scalp", "trend_up_strong", "BUY", "EUR_USD"
        )
        assert r == "conflict"

    def test_bo_range_wide_aligned(self):
        r = strategy_aware_alignment(
            "bb_squeeze_breakout", "range_wide", "BUY", "GBP_USD"
        )
        assert r == "aligned"

    def test_se_neutral(self):
        r = strategy_aware_alignment(
            "session_time_bias", "trend_up_weak", "BUY", "USD_JPY"
        )
        assert r == "neutral"

    def test_uncertain_regime_neutral(self):
        r = strategy_aware_alignment(
            "sr_channel_reversal", "uncertain", "BUY", "USD_JPY"
        )
        assert r == "neutral"

    def test_unknown_strategy_unknown(self):
        r = strategy_aware_alignment(
            "nonexistent_strategy_xyz", "trend_up_weak", "BUY", "USD_JPY"
        )
        assert r == "unknown"

    def test_p0_macdh_reversal_now_tf(self):
        """P0: macdh_reversal behaves as TF (reclassified from MR)"""
        # TF aligned: trend_up × BUY (JPY) or trend_up_weak × BUY (non-JPY)
        r = strategy_aware_alignment(
            "macdh_reversal", "trend_up_weak", "BUY", "USD_JPY"
        )
        assert r == "aligned"
        r = strategy_aware_alignment(
            "macdh_reversal", "trend_up_weak", "SELL", "USD_JPY"
        )
        assert r == "conflict"

    def test_p0_ema_cross_now_mr(self):
        """P0: ema_cross behaves as MR (reclassified from TF)"""
        # MR aligned: trend_up_weak × SELL (fade)
        r = strategy_aware_alignment(
            "ema_cross", "trend_up_weak", "SELL", "EUR_USD"
        )
        assert r == "aligned"
        r = strategy_aware_alignment(
            "ema_cross", "trend_up_weak", "BUY", "EUR_USD"
        )
        assert r == "conflict"


class TestRegimeAdaptive:
    def test_adaptive_map_present(self):
        assert "bb_rsi_reversion" in REGIME_ADAPTIVE_FAMILY
        assert "fib_reversal" in REGIME_ADAPTIVE_FAMILY

    def test_bb_rsi_reversion_uptrend_is_tf(self):
        """P2: bb_rsi_reversion acts as TF in uptrend (BUY > SELL WR)"""
        assert effective_family("bb_rsi_reversion", "trend_up_weak") == "TF"
        # TF in uptrend: BUY aligned, SELL conflict
        r = strategy_aware_alignment(
            "bb_rsi_reversion", "trend_up_weak", "BUY", "EUR_USD"
        )
        assert r == "aligned"
        r = strategy_aware_alignment(
            "bb_rsi_reversion", "trend_up_weak", "SELL", "EUR_USD"
        )
        assert r == "conflict"

    def test_bb_rsi_reversion_downtrend_is_mr(self):
        """P2: bb_rsi_reversion acts as MR in downtrend (BUY > SELL WR)"""
        assert effective_family("bb_rsi_reversion", "trend_down_weak") == "MR"
        # MR in downtrend: BUY aligned (fade), SELL conflict
        r = strategy_aware_alignment(
            "bb_rsi_reversion", "trend_down_weak", "BUY", "EUR_USD"
        )
        assert r == "aligned"
        r = strategy_aware_alignment(
            "bb_rsi_reversion", "trend_down_weak", "SELL", "EUR_USD"
        )
        assert r == "conflict"

    def test_bb_rsi_reversion_range_defaults_to_mr(self):
        """P2: range is not in adaptive map, falls back to default MR"""
        assert effective_family("bb_rsi_reversion", "range_tight") == "MR"
        r = strategy_aware_alignment(
            "bb_rsi_reversion", "range_tight", "BUY", "EUR_USD"
        )
        assert r == "aligned"

    def test_fib_reversal_uptrend_is_mr(self):
        """P2: fib_reversal acts as MR in uptrend (SELL > BUY WR, fade)"""
        assert effective_family("fib_reversal", "trend_up_weak") == "MR"
        r = strategy_aware_alignment(
            "fib_reversal", "trend_up_weak", "SELL", "EUR_USD"
        )
        assert r == "aligned"

    def test_fib_reversal_downtrend_is_tf(self):
        """P2: fib_reversal acts as TF in downtrend (SELL > BUY WR)"""
        assert effective_family("fib_reversal", "trend_down_weak") == "TF"
        r = strategy_aware_alignment(
            "fib_reversal", "trend_down_weak", "SELL", "EUR_USD"
        )
        assert r == "aligned"

    def test_non_adaptive_strategy_unchanged(self):
        """Strategies not in REGIME_ADAPTIVE_FAMILY use default STRATEGY_FAMILY"""
        assert effective_family("ema_trend_scalp", "trend_up_weak") == "TF"
        assert effective_family("sr_channel_reversal", "trend_up_weak") == "MR"
