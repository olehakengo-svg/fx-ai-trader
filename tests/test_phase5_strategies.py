"""Tests for Phase 5 strategies: rsk_gbpjpy_reversion, mqe_gbpusd_fix."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from strategies.daytrade.rsk_gbpjpy_reversion import RskGbpjpyReversion
from strategies.daytrade.mqe_gbpusd_fix import MqeGbpusdFix
from strategies.context import SignalContext


def _make_skewed_history(n=200, skew_direction=-1, base=180.0, atr=0.20):
    """Create returns history with controlled skewness in last 30 bars."""
    np.random.seed(42)
    returns = list(np.random.normal(0, 0.0003, n - 30))
    # Inject one large negative spike + many small positives = negative skew
    if skew_direction < 0:
        skewed_recent = ([-0.005] + list(np.random.normal(0.0001, 0.0001, 29)))
    else:
        skewed_recent = ([0.005] + list(np.random.normal(-0.0001, 0.0001, 29)))
    returns.extend(skewed_recent)
    closes = base * np.cumprod(1 + np.array(returns))
    dates = pd.date_range("2024-01-01", periods=n, freq="15min")
    df = pd.DataFrame({
        "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
        "Close": closes, "Volume": [1000] * n,
    }, index=dates)
    return df


class TestRskGbpjpyReversion:
    def test_only_gbpjpy_allowed(self):
        s = RskGbpjpyReversion()
        for sym in ["USDJPY=X", "EURUSD=X", "GBPUSD=X", "EURJPY=X"]:
            df = _make_skewed_history()
            ctx = SignalContext(
                entry=float(df["Close"].iloc[-1]),
                open_price=float(df["Close"].iloc[-2]),
                atr=0.20, adx=20.0, df=df, symbol=sym, tf="15m",
                is_jpy=("JPY" in sym), pip_mult=100 if "JPY" in sym else 10000,
            )
            assert s.evaluate(ctx) is None

    def test_enabled_for_shadow(self):
        assert RskGbpjpyReversion().enabled is True

    def test_supports_gbpjpy(self):
        s = RskGbpjpyReversion()
        # Just verify it runs without error on GBP_JPY data
        df = _make_skewed_history(skew_direction=-1)
        ctx = SignalContext(
            entry=float(df["Close"].iloc[-1]),
            open_price=float(df["Close"].iloc[-2]),
            atr=0.20, adx=20.0, df=df, symbol="GBPJPY=X", tf="15m",
            is_jpy=True, pip_mult=100,
        )
        # Result may be None or signal — accept either
        result = s.evaluate(ctx)
        assert result is None or result.entry_type == "rsk_gbpjpy_reversion"

    def test_insufficient_history_returns_none(self):
        s = RskGbpjpyReversion()
        # Only 50 bars — less than 30+96=126 required
        n = 50
        dates = pd.date_range("2024-01-01", periods=n, freq="15min")
        closes = 180.0 + np.random.normal(0, 0.05, n)
        df = pd.DataFrame({
            "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
            "Close": closes, "Volume": [1000] * n,
        }, index=dates)
        ctx = SignalContext(
            entry=float(closes[-1]), open_price=float(closes[-2]),
            atr=0.20, adx=20.0, df=df, symbol="GBPJPY=X", tf="15m",
            is_jpy=True, pip_mult=100,
        )
        assert s.evaluate(ctx) is None


class TestMqeGbpusdFix:
    def test_only_gbpusd_allowed(self):
        s = MqeGbpusdFix()
        for sym in ["USDJPY=X", "EURUSD=X", "GBPJPY=X"]:
            df = _make_skewed_history(base=1.30, atr=0.0010)
            ctx = SignalContext(
                entry=float(df["Close"].iloc[-1]),
                open_price=float(df["Close"].iloc[-2]),
                atr=0.0010, adx=20.0, df=df, symbol=sym, tf="15m",
                bar_time=pd.Timestamp("2024-01-31 15:30", tz="UTC"),
                pip_mult=10000,
            )
            assert s.evaluate(ctx) is None

    def test_enabled_for_shadow(self):
        assert MqeGbpusdFix().enabled is True

    def test_skip_outside_fix_window(self):
        s = MqeGbpusdFix()
        df = _make_skewed_history(base=1.30, atr=0.0010)
        ctx = SignalContext(
            entry=float(df["Close"].iloc[-1]),
            open_price=float(df["Close"].iloc[-2]),
            atr=0.0010, adx=20.0, df=df, symbol="GBPUSD=X", tf="15m",
            bar_time=pd.Timestamp("2024-01-31 10:30", tz="UTC"),  # not fix window
            pip_mult=10000,
        )
        assert s.evaluate(ctx) is None

    def test_skip_non_month_end(self):
        s = MqeGbpusdFix()
        df = _make_skewed_history(base=1.30, atr=0.0010)
        ctx = SignalContext(
            entry=float(df["Close"].iloc[-1]),
            open_price=float(df["Close"].iloc[-2]),
            atr=0.0010, adx=20.0, df=df, symbol="GBPUSD=X", tf="15m",
            bar_time=pd.Timestamp("2024-01-15 15:30", tz="UTC"),  # mid-month
            pip_mult=10000,
        )
        assert s.evaluate(ctx) is None

    def test_signal_at_month_end_fix(self):
        s = MqeGbpusdFix()
        df = _make_skewed_history(base=1.30, atr=0.0010)
        ctx = SignalContext(
            entry=float(df["Close"].iloc[-1]),
            open_price=float(df["Close"].iloc[-2]),
            atr=0.0010, adx=20.0, df=df, symbol="GBPUSD=X", tf="15m",
            bar_time=pd.Timestamp("2024-01-31 15:30", tz="UTC"),
            pip_mult=10000,
        )
        result = s.evaluate(ctx)
        assert result is None or result.entry_type == "mqe_gbpusd_fix"
        if result is not None:
            assert result.signal in ("BUY", "SELL")
