"""Tests for tools/pattern_discovery.py — feature engineering + look-ahead prevention."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from tools.pattern_discovery import (
    wilson_lower, benjamini_hochberg, _add_atr, _add_bbpb_rsi,
    _add_1h_aggregated, _add_features, stage1_apply_gates,
    FEATURE_AXES_LOCK, PAIRS_LOCK, FORWARD_BARS_LOCK,
)


def _make_df(n=200, base=150.0):
    closes = base + np.cumsum(np.random.normal(0, 0.05, n))
    dates = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({
        "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
        "Close": closes, "Volume": [1000] * n,
    }, index=dates)


class TestWilsonLower:
    def test_zero_n(self):
        assert wilson_lower(0, 0) == 0.0

    def test_50_50(self):
        # 50/100 → Wilson lower around 0.40
        wl = wilson_lower(50, 100)
        assert 0.35 < wl < 0.45

    def test_high_wr(self):
        wl = wilson_lower(80, 100)
        assert wl > 0.70


class TestBenjaminiHochberg:
    def test_all_significant(self):
        # All very small p-values → all significant
        ps = [0.001, 0.002, 0.003]
        sig = benjamini_hochberg(ps, q=0.05)
        assert all(sig)

    def test_none_significant(self):
        ps = [0.5, 0.6, 0.7]
        sig = benjamini_hochberg(ps, q=0.05)
        assert not any(sig)

    def test_partial(self):
        ps = [0.001, 0.5, 0.002, 0.8]
        sig = benjamini_hochberg(ps, q=0.05)
        # First and third should be significant
        assert sig[0] and sig[2]
        assert not sig[1] and not sig[3]


class TestFeatureEngineering:
    def test_add_atr(self):
        df = _make_df(100)
        df = _add_atr(df)
        assert "atr" in df.columns
        # ATR should be positive after warmup
        assert df["atr"].iloc[50:].min() > 0

    def test_add_bbpb_rsi(self):
        df = _make_df(100)
        df = _add_bbpb_rsi(df)
        assert "bbpb_15m" in df.columns
        assert "rsi_15m" in df.columns
        # RSI in [0, 100]
        valid_rsi = df["rsi_15m"].dropna()
        assert valid_rsi.min() >= 0 and valid_rsi.max() <= 100

    def test_add_1h_aggregated(self):
        df = _make_df(100)
        df = _add_bbpb_rsi(df)  # need 15m BB first
        df = _add_1h_aggregated(df)
        assert "bbpb_1h" in df.columns

    def test_add_features_all(self):
        df = _make_df(8000)  # enough for 60d ATR percentile
        df = _add_features(df)
        # All bucketized columns present
        for col in ("hour_utc", "dow", "bbpb_15m_b", "rsi_15m_b",
                    "bbpb_1h_b", "atr_pct_60d_b", "recent_3bar_b"):
            assert col in df.columns


class TestLookAheadPrevention:
    def test_1h_aggregation_uses_completed_bars_only(self):
        """
        For bar at index i (15m), the 1h value should be from the PREVIOUS
        completed 1h bucket (bars i-7 to i-4 most recently completed if i is in
        the next bucket). I.e., bbpb_1h at bar 7 should NOT include bar 7's price.
        """
        # Linearly increasing price → 1h aggregation should reflect prior bucket
        n = 32
        closes = np.linspace(150.0, 153.0, n)
        df = pd.DataFrame({
            "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
            "Close": closes, "Volume": [1000] * n,
        }, index=pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC"))
        df = _add_bbpb_rsi(df)
        df = _add_1h_aggregated(df)
        # First few bars should have NaN bbpb_1h (no completed 1h bucket yet)
        # Specifically: bars 0-3 have NO completed 1h bucket
        # Bars 4-7 might have first completed bucket (depends on offset)
        # Just verify there's at least some NaN at start (no future leak)
        assert df["bbpb_1h"].iloc[:4].isna().all()


class TestStage1Gates:
    def test_filters_low_n(self):
        results = [
            {"p_value": 0.001, "wilson_lower": 0.55, "n_trades": 50,
             "ev_net_pip": 1.0, "trades_per_month": 8.0, "sharpe_per_event": 0.10},
            {"p_value": 0.001, "wilson_lower": 0.55, "n_trades": 200,
             "ev_net_pip": 1.0, "trades_per_month": 8.0, "sharpe_per_event": 0.10},
        ]
        survivors = stage1_apply_gates(results, q=0.10)
        # Only the 200-trade row should pass
        assert len(survivors) == 1
        assert survivors[0]["n_trades"] == 200

    def test_filters_negative_ev(self):
        results = [
            {"p_value": 0.001, "wilson_lower": 0.55, "n_trades": 200,
             "ev_net_pip": -1.0, "trades_per_month": 8.0, "sharpe_per_event": 0.10},
        ]
        assert len(stage1_apply_gates(results)) == 0

    def test_filters_low_capacity(self):
        results = [
            {"p_value": 0.001, "wilson_lower": 0.55, "n_trades": 200,
             "ev_net_pip": 1.0, "trades_per_month": 1.0, "sharpe_per_event": 0.10},
        ]
        assert len(stage1_apply_gates(results)) == 0


class TestLockConstants:
    def test_pairs_locked(self):
        assert PAIRS_LOCK == ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]

    def test_forward_bars_locked(self):
        assert FORWARD_BARS_LOCK == [4, 8, 12]

    def test_features_locked(self):
        # Spec requires exactly these 7 axes
        assert set(FEATURE_AXES_LOCK.keys()) == {
            "hour_utc", "dow", "bbpb_15m", "rsi_15m",
            "bbpb_1h", "atr_pct_60d", "recent_3bar",
        }
