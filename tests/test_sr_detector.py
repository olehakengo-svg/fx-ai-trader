"""Tests for modules/sr_detector.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from modules.sr_detector import (
    SRLevel, detect_sr_levels, score_obviousness, kde_cluster_levels,
)


def _make_df_with_concentrated_levels(levels, n_per_level=20, noise=0.05, base=150.0):
    np.random.seed(42)
    rows = []
    for level in levels:
        for _ in range(n_per_level):
            close = level + np.random.normal(0, noise)
            high = close + abs(np.random.normal(0, noise * 0.5))
            low = close - abs(np.random.normal(0, noise * 0.5))
            open_ = close + np.random.normal(0, noise * 0.3)
            rows.append({"Open": open_, "High": high, "Low": low,
                         "Close": close, "Volume": 1000})
    dates = pd.date_range("2024-01-01", periods=len(rows), freq="15min")
    return pd.DataFrame(rows, index=dates)


class TestKdeClusterLevels:
    def test_finds_known_concentration_levels(self):
        df = _make_df_with_concentrated_levels([149.50, 150.00, 150.50])
        peaks = kde_cluster_levels(df, bandwidth=0.05)
        for known in [149.50, 150.00, 150.50]:
            matched = any(abs(p - known) < 0.10 for p in peaks)
            assert matched, f"KDE missed level {known}; got {peaks}"


class TestScoreObviousness:
    def test_round_number_increases_obviousness(self):
        score_round = score_obviousness(price=150.000, touch_count=3,
                                        age_bars=100, pip_size=0.01)
        score_random = score_obviousness(price=150.137, touch_count=3,
                                         age_bars=100, pip_size=0.01)
        assert score_round > score_random

    def test_higher_touch_count_increases_obviousness(self):
        score_low = score_obviousness(price=150.137, touch_count=2,
                                      age_bars=100, pip_size=0.01)
        score_high = score_obviousness(price=150.137, touch_count=8,
                                       age_bars=100, pip_size=0.01)
        assert score_high > score_low

    def test_score_in_unit_interval(self):
        for price in [150.0, 150.137, 1.23456]:
            for touches in [1, 5, 20]:
                for age in [10, 100, 1000]:
                    s = score_obviousness(price=price, touch_count=touches,
                                          age_bars=age, pip_size=0.01)
                    assert 0.0 <= s <= 1.0


class TestDetectSrLevels:
    def test_returns_list_of_sr_level(self):
        df = _make_df_with_concentrated_levels([149.50, 150.00, 150.50])
        levels = detect_sr_levels(df, instrument="USD_JPY")
        assert isinstance(levels, list)
        assert all(isinstance(lv, SRLevel) for lv in levels)
        assert len(levels) >= 1

    def test_sr_level_has_required_fields(self):
        df = _make_df_with_concentrated_levels([150.00])
        levels = detect_sr_levels(df, instrument="USD_JPY")
        assert len(levels) >= 1
        lv = levels[0]
        assert hasattr(lv, "price")
        assert hasattr(lv, "touch_count")
        assert hasattr(lv, "age_bars")
        assert hasattr(lv, "obviousness")
        assert hasattr(lv, "kde_density")
        assert 0.0 <= lv.obviousness <= 1.0
        assert lv.touch_count >= 1
        assert lv.kde_density > 0

    def test_finds_round_number_with_high_obviousness(self):
        df = _make_df_with_concentrated_levels([150.000], n_per_level=30)
        levels = detect_sr_levels(df, instrument="USD_JPY")
        best = min(levels, key=lambda lv: abs(lv.price - 150.00))
        assert abs(best.price - 150.00) < 0.10
        assert best.obviousness > 0.5

    def test_handles_eur_pair_pip_size(self):
        df = _make_df_with_concentrated_levels(
            [1.0850, 1.0900, 1.0950],
            n_per_level=20, noise=0.0005, base=1.09)
        levels = detect_sr_levels(df, instrument="EUR_USD")
        assert len(levels) >= 1
        round_match = any(abs(lv.price - 1.0900) < 0.001 for lv in levels)
        assert round_match
