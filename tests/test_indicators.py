"""Tests for indicator functions in app.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import pytest

from app import add_indicators, find_sr_levels, detect_order_blocks


class TestAddIndicators:
    def test_returns_dataframe(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        assert isinstance(result, pd.DataFrame)

    def test_adds_ema_columns(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        for col in ("ema9", "ema21", "ema50", "ema100", "ema200"):
            assert col in result.columns, f"Missing column '{col}'"

    def test_adds_rsi_columns(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        for col in ("rsi", "rsi5", "rsi9"):
            assert col in result.columns, f"Missing column '{col}'"

    def test_adds_macd_columns(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        for col in ("macd", "macd_sig", "macd_hist"):
            assert col in result.columns, f"Missing column '{col}'"

    def test_adds_bollinger_band_columns(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        for col in ("bb_upper", "bb_mid", "bb_lower", "bb_pband", "bb_width"):
            assert col in result.columns, f"Missing column '{col}'"

    def test_adds_atr_columns(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        for col in ("atr", "atr7"):
            assert col in result.columns, f"Missing column '{col}'"

    def test_adds_adx_columns(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        for col in ("adx", "adx_pos", "adx_neg"):
            assert col in result.columns, f"Missing column '{col}'"

    def test_adds_stochastic_columns(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        for col in ("stoch_k", "stoch_d"):
            assert col in result.columns, f"Missing column '{col}'"

    def test_adds_donchian_columns(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        for col in ("don_high20", "don_low20", "don_mid20", "don_pct"):
            assert col in result.columns, f"Missing column '{col}'"

    def test_no_nan_in_core_cols_after_dropna(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        # add_indicators calls dropna(subset=core_cols) to preserve data
        # Core columns (ema9, ema21, rsi, macd, atr, bb_upper) should have no NaN
        core_cols = ["ema9", "ema21", "rsi", "macd", "atr", "bb_upper"]
        for col in core_cols:
            assert not result[col].isnull().any(), f"NaN found in core column '{col}'"

    def test_fewer_rows_after_indicators(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        # EMA200 needs at least 200 rows warmup, so output should be shorter
        assert len(result) < len(sample_ohlcv)
        assert len(result) > 0

    def test_rsi_in_valid_range(self, sample_ohlcv):
        result = add_indicators(sample_ohlcv)
        assert (result["rsi"] >= 0).all() and (result["rsi"] <= 100).all()

    def test_ema_ordering(self, sample_ohlcv):
        """EMA values should all be in the same ballpark as close price."""
        result = add_indicators(sample_ohlcv)
        close_mean = result["Close"].mean()
        for col in ("ema9", "ema21", "ema50"):
            ema_mean = result[col].mean()
            # Should be within 2% of close price mean
            assert abs(ema_mean - close_mean) / close_mean < 0.02, \
                f"{col} mean {ema_mean} too far from close mean {close_mean}"


class TestFindSrLevels:
    def test_returns_list(self, sample_ohlcv):
        levels = find_sr_levels(sample_ohlcv)
        assert isinstance(levels, list)

    def test_returns_floats(self, sample_ohlcv):
        levels = find_sr_levels(sample_ohlcv)
        for lvl in levels:
            assert isinstance(lvl, float), f"Level {lvl} is not a float"

    def test_respects_max_levels(self, sample_ohlcv):
        levels = find_sr_levels(sample_ohlcv, max_levels=5)
        assert len(levels) <= 5

    def test_levels_near_price_range(self, sample_ohlcv):
        levels = find_sr_levels(sample_ohlcv)
        if levels:
            price_min = sample_ohlcv["Low"].min()
            price_max = sample_ohlcv["High"].max()
            for lvl in levels:
                assert price_min * 0.99 <= lvl <= price_max * 1.01, \
                    f"Level {lvl} outside price range [{price_min}, {price_max}]"

    def test_empty_on_tiny_df(self):
        """Very small DataFrame should return empty list."""
        df = pd.DataFrame({
            "Open": [150.0, 150.1],
            "High": [150.5, 150.6],
            "Low": [149.5, 149.6],
            "Close": [150.2, 150.3],
            "Volume": [1000, 1000],
        })
        levels = find_sr_levels(df, window=5)
        assert levels == []

    def test_custom_window_and_tolerance(self, sample_ohlcv):
        levels_tight = find_sr_levels(sample_ohlcv, window=3, tolerance_pct=0.001)
        levels_loose = find_sr_levels(sample_ohlcv, window=3, tolerance_pct=0.01)
        # Loose tolerance should cluster more, returning fewer or equal levels
        assert isinstance(levels_tight, list)
        assert isinstance(levels_loose, list)


class TestDetectOrderBlocks:
    def test_returns_tuple(self, sample_ohlcv_with_indicators):
        result = detect_order_blocks(sample_ohlcv_with_indicators)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_score_in_range(self, sample_ohlcv_with_indicators):
        score, zones = detect_order_blocks(sample_ohlcv_with_indicators)
        assert -1.0 <= score <= 1.0, f"Score {score} out of [-1, 1]"

    def test_zones_is_list(self, sample_ohlcv_with_indicators):
        score, zones = detect_order_blocks(sample_ohlcv_with_indicators)
        assert isinstance(zones, list)

    def test_zone_structure(self, sample_ohlcv_with_indicators):
        score, zones = detect_order_blocks(sample_ohlcv_with_indicators)
        for zone in zones:
            assert isinstance(zone, dict)
            assert "type" in zone
            assert zone["type"] in ("bull", "bear")
            assert "high" in zone
            assert "low" in zone
            assert "time" in zone
            assert "label" in zone
            assert isinstance(zone["high"], float)
            assert isinstance(zone["low"], float)
            assert zone["high"] >= zone["low"]

    def test_small_df_returns_zero_score(self):
        """DataFrame with fewer than 20 rows should return (0.0, [])."""
        df = pd.DataFrame({
            "Open": [150.0] * 10,
            "High": [151.0] * 10,
            "Low": [149.0] * 10,
            "Close": [150.5] * 10,
            "Volume": [1000] * 10,
            "atr": [0.5] * 10,
        })
        score, zones = detect_order_blocks(df)
        assert score == 0.0
        assert zones == []

    def test_max_zones_limited(self, sample_ohlcv_with_indicators):
        score, zones = detect_order_blocks(sample_ohlcv_with_indicators)
        # Code limits to last 10 zones
        assert len(zones) <= 10
