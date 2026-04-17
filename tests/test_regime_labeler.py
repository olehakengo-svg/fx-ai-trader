"""Unit tests for regime_labeler — features + labels + trade join.

No OANDA API calls; uses synthetic OHLC data.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pytest

from research.edge_discovery.regime_labeler import (
    compute_slope_t,
    compute_adx,
    compute_atr_ratio,
    label_regimes,
    label_trades,
    RegimeConfig,
    _candles_to_df,
)


# ──────────────────────────────────────────────────────
# Slope/t-stat feature
# ──────────────────────────────────────────────────────
class TestSlopeT:
    def test_perfect_uptrend(self):
        """y = x → slope = 1, t very large."""
        s = pd.Series(np.arange(100, dtype=float))
        out = compute_slope_t(s, window=20)
        # Last value should be slope=1, t very large
        assert abs(out["slope"].iloc[-1] - 1.0) < 1e-9
        assert out["slope_t"].iloc[-1] > 100  # essentially infinite

    def test_flat_series(self):
        """Constant series → slope = 0, t undefined (sse=0 → skip)."""
        s = pd.Series([5.0] * 50)
        out = compute_slope_t(s, window=20)
        # slope ~0 and t ~0 (implementation returns 0 when se_b sane)
        last_slope = out["slope"].iloc[-1]
        assert last_slope is None or abs(last_slope) < 1e-9 or pd.isna(last_slope)

    def test_window_boundary_nan(self):
        """First (window-1) rows are NaN."""
        s = pd.Series(np.arange(50, dtype=float))
        out = compute_slope_t(s, window=10)
        assert pd.isna(out["slope"].iloc[8])
        assert not pd.isna(out["slope"].iloc[9])

    def test_downtrend_negative_t(self):
        s = pd.Series(np.arange(50, 0, -1, dtype=float))
        out = compute_slope_t(s, window=20)
        assert out["slope"].iloc[-1] < 0
        assert out["slope_t"].iloc[-1] < -100

    def test_no_lookahead(self):
        """Slope at index i uses only values in [i-window+1, i]."""
        # Create series where future values would change slope direction
        s = pd.Series([1, 2, 3, 4, 5, 100, 100, 100, 100, 100], dtype=float)
        out = compute_slope_t(s, window=5)
        # At i=4: y = [1,2,3,4,5], slope should be +1
        assert abs(out["slope"].iloc[4] - 1.0) < 1e-9
        # At i=9: y = [100,100,100,100,100], slope ~0


# ──────────────────────────────────────────────────────
# ADX
# ──────────────────────────────────────────────────────
class TestADX:
    def _make_ohlc(self, closes):
        """Build OHLC df from closes, with small h/l spread."""
        return pd.DataFrame({
            "open": closes,
            "high": [c + 0.01 for c in closes],
            "low": [c - 0.01 for c in closes],
            "close": closes,
        })

    def test_adx_strong_trend(self):
        """Monotone rise → ADX should go high (>25)."""
        closes = list(np.arange(1.0, 2.0, 0.01))  # 100 bars rising
        df = self._make_ohlc(closes)
        # Widen h/l to give TR some magnitude
        df["high"] = df["close"] + 0.02
        df["low"] = df["close"] - 0.01
        adx = compute_adx(df, period=14)
        # Non-NaN values should be meaningful
        last = adx.iloc[-1]
        assert not pd.isna(last)
        # Monotone trend should have sizeable ADX
        assert last > 20, f"expected ADX>20 for monotone trend, got {last}"

    def test_adx_flat_market(self):
        """Pure noise around mean → ADX low."""
        np.random.seed(42)
        closes = 1.0 + 0.001 * np.random.randn(200)
        df = self._make_ohlc(list(closes))
        df["high"] = df["close"] + 0.005
        df["low"] = df["close"] - 0.005
        adx = compute_adx(df, period=14)
        last = adx.iloc[-1]
        assert not pd.isna(last)
        assert last < 40, f"expected low ADX for noise, got {last}"

    def test_adx_insufficient_data(self):
        """fewer than 2*period bars → all NaN."""
        df = self._make_ohlc([1.0] * 10)
        adx = compute_adx(df, period=14)
        assert adx.isna().all()


# ──────────────────────────────────────────────────────
# ATR ratio
# ──────────────────────────────────────────────────────
class TestATRRatio:
    def test_basic(self):
        df = pd.DataFrame({
            "open": [100.0] * 50,
            "high": [101.0] * 50,
            "low": [99.0] * 50,
            "close": [100.0] * 50,
        })
        r = compute_atr_ratio(df, period=14)
        # Range/close ≈ 2/100 = 0.02
        assert abs(r.iloc[-1] - 0.02) < 0.01


# ──────────────────────────────────────────────────────
# Regime labeling
# ──────────────────────────────────────────────────────
class TestLabelRegimes:
    def _synth_trend(self, n=100, slope=0.01, noise=0.0):
        t = pd.date_range("2024-01-01", periods=n, freq="30min", tz="UTC")
        closes = 1.0 + slope * np.arange(n) + noise * np.random.randn(n)
        return pd.DataFrame({
            "time": t,
            "open": closes,
            "high": closes + 0.005,
            "low": closes - 0.005,
            "close": closes,
        })

    def test_uptrend_labeled(self):
        df = self._synth_trend(n=100, slope=0.005)
        out = label_regimes(df)
        # After enough bars, should be labeled up_trend
        labels_tail = out["regime"].iloc[-20:]
        assert (labels_tail == "up_trend").sum() >= 10, (
            f"uptrend synthetic should label up_trend for most tail bars, "
            f"got: {labels_tail.value_counts().to_dict()}"
        )

    def test_downtrend_labeled(self):
        df = self._synth_trend(n=100, slope=-0.005)
        out = label_regimes(df)
        labels_tail = out["regime"].iloc[-20:]
        assert (labels_tail == "down_trend").sum() >= 10

    def test_labels_are_valid(self):
        df = self._synth_trend(n=80)
        out = label_regimes(df)
        valid = {"up_trend", "down_trend", "range", "uncertain"}
        assert set(out["regime"].unique()) <= valid

    def test_uncertain_when_insufficient(self):
        """Very short series → regime all uncertain."""
        df = self._synth_trend(n=20)
        out = label_regimes(df)
        # First bars where features are NaN must be uncertain
        assert (out["regime"].iloc[:10] == "uncertain").all()

    def test_custom_config_strictness(self):
        """Stricter thresholds → more 'uncertain'."""
        df = self._synth_trend(n=100, slope=0.002)
        out_default = label_regimes(df)
        strict = RegimeConfig(slope_t_trend=10.0, adx_trend=50.0)
        out_strict = label_regimes(df, config=strict)
        assert (out_strict["regime"] == "uncertain").sum() >= (
            out_default["regime"] == "uncertain"
        ).sum()


# ──────────────────────────────────────────────────────
# Trade join
# ──────────────────────────────────────────────────────
class TestLabelTrades:
    def test_basic_join(self):
        # 5 candles, 30min each
        times = pd.date_range("2024-01-01", periods=5, freq="30min", tz="UTC")
        candles = pd.DataFrame({
            "time": times,
            "open": [1.0, 1.01, 1.02, 1.03, 1.04],
            "high": [1.005, 1.015, 1.025, 1.035, 1.045],
            "low": [0.995, 1.005, 1.015, 1.025, 1.035],
            "close": [1.0, 1.01, 1.02, 1.03, 1.04],
            "regime": ["uncertain", "up_trend", "up_trend", "up_trend", "up_trend"],
        })
        # 3 trades, all within the candle span
        trades = pd.DataFrame({
            "entry_time": [times[0] + pd.Timedelta(minutes=5),
                           times[2] + pd.Timedelta(minutes=10),
                           times[4] + pd.Timedelta(minutes=20)],
            "instrument": ["EUR_USD"] * 3,
            "pnl_pips": [1.0, -2.0, 3.0],
        })
        out = label_trades(trades, {"EUR_USD": candles})
        assert "regime_independent" in out.columns
        assert out["regime_independent"].tolist() == ["uncertain", "up_trend", "up_trend"]

    def test_unknown_instrument_uncertain(self):
        times = pd.date_range("2024-01-01", periods=3, freq="30min", tz="UTC")
        candles = pd.DataFrame({
            "time": times,
            "open": [1.0] * 3, "high": [1.01] * 3, "low": [0.99] * 3,
            "close": [1.0] * 3, "regime": ["range"] * 3,
        })
        trades = pd.DataFrame({
            "entry_time": [times[1]],
            "instrument": ["NOT_IN_DICT"],
            "pnl_pips": [1.0],
        })
        out = label_trades(trades, {"EUR_USD": candles})
        assert out["regime_independent"].iloc[0] == "uncertain"

    def test_trade_before_any_candle(self):
        times = pd.date_range("2024-01-01", periods=3, freq="30min", tz="UTC")
        candles = pd.DataFrame({
            "time": times,
            "open": [1.0] * 3, "high": [1.01] * 3, "low": [0.99] * 3,
            "close": [1.0] * 3, "regime": ["up_trend"] * 3,
        })
        trades = pd.DataFrame({
            "entry_time": [times[0] - pd.Timedelta(hours=1)],
            "instrument": ["EUR_USD"],
            "pnl_pips": [1.0],
        })
        out = label_trades(trades, {"EUR_USD": candles})
        assert out["regime_independent"].iloc[0] == "uncertain"

    def test_no_lookahead_in_join(self):
        """Trade at t uses candle at or before t, never future."""
        times = pd.date_range("2024-01-01", periods=3, freq="30min", tz="UTC")
        candles = pd.DataFrame({
            "time": times,
            "open": [1.0] * 3, "high": [1.01] * 3, "low": [0.99] * 3,
            "close": [1.0] * 3,
            "regime": ["uncertain", "range", "up_trend"],
        })
        # Trade at exactly times[1] should get regime from candle[1], not [2]
        trades = pd.DataFrame({
            "entry_time": [times[1]],
            "instrument": ["EUR_USD"],
            "pnl_pips": [1.0],
        })
        out = label_trades(trades, {"EUR_USD": candles})
        assert out["regime_independent"].iloc[0] == "range"


# ──────────────────────────────────────────────────────
# _candles_to_df (OANDA payload parsing)
# ──────────────────────────────────────────────────────
class TestCandlesToDF:
    def test_skips_incomplete(self):
        candles = [
            {"complete": False, "time": "2024-01-01T00:00:00Z",
             "mid": {"o": "1", "h": "1", "l": "1", "c": "1"}, "volume": 10},
            {"complete": True, "time": "2024-01-01T00:30:00Z",
             "mid": {"o": "1", "h": "1.01", "l": "0.99", "c": "1.005"},
             "volume": 100},
        ]
        df = _candles_to_df(candles)
        assert len(df) == 1
        assert df.iloc[0]["close"] == 1.005

    def test_empty(self):
        df = _candles_to_df([])
        assert df.empty
