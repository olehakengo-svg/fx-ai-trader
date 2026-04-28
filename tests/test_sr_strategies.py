"""Tests for sr_anti_hunt_bounce and sr_liquidity_grab strategies."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from strategies.daytrade.sr_anti_hunt_bounce import SrAntiHuntBounce
from strategies.daytrade.sr_liquidity_grab import SrLiquidityGrab
from strategies.context import SignalContext


def _quiet_df(entry, n=5):
    return pd.DataFrame({
        "Open": [entry - 0.0001] * n,
        "High": [entry + 0.0001] * n,
        "Low": [entry - 0.0002] * n,
        "Close": [entry] * n,
        "Volume": [1000] * n,
    }, index=pd.date_range("2024-01-01", periods=n, freq="15min"))


class TestSrAntiHuntBounce:
    def test_buy_at_support_with_anti_hunt_sl(self):
        s = SrAntiHuntBounce()
        ctx = SignalContext(
            entry=1.1002, open_price=1.1000, atr=0.0010, adx=20.0,
            sr_levels=[1.1000], df=_quiet_df(1.1002),
            symbol="EURUSD=X", tf="15m", pip_mult=10000,
        )
        cand = s.evaluate(ctx)
        assert cand is not None
        assert cand.signal == "BUY"
        # SL must be far enough to avoid hunting (P90 ≈ 37 pip for EUR_USD)
        sl_distance = 1.1000 - cand.sl
        assert sl_distance >= 0.0037, f"SL too close: dist={sl_distance}"

    def test_supports_all_5_majors(self):
        """Shadow全走の確認 — 5 majors全部許可"""
        s = SrAntiHuntBounce()
        for sym in ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "GBPJPY=X"]:
            assert sym.replace("=X", "").replace("_", "") in s._ALLOWED_SYMBOLS

    def test_enabled_for_shadow_deployment(self):
        s = SrAntiHuntBounce()
        assert s.enabled is True

    def test_skips_in_strong_trend(self):
        s = SrAntiHuntBounce()
        ctx = SignalContext(
            entry=1.1002, open_price=1.1000, atr=0.0010, adx=35.0,
            sr_levels=[1.1000], df=_quiet_df(1.1002),
            symbol="EURUSD=X", tf="15m", pip_mult=10000,
        )
        assert s.evaluate(ctx) is None

    def test_skips_when_no_sr_levels(self):
        s = SrAntiHuntBounce()
        ctx = SignalContext(
            entry=1.1002, open_price=1.1000, atr=0.0010, adx=20.0,
            sr_levels=[], df=_quiet_df(1.1002),
            symbol="EURUSD=X", tf="15m", pip_mult=10000,
        )
        assert s.evaluate(ctx) is None


class TestSrLiquidityGrab:
    def test_supports_all_5_majors(self):
        s = SrLiquidityGrab()
        for sym in ["USDJPY", "EURUSD", "GBPUSD", "EURJPY", "GBPJPY"]:
            assert sym in s._ALLOWED_SYMBOLS

    def test_enabled_for_shadow_deployment(self):
        s = SrLiquidityGrab()
        assert s.enabled is True

    def test_returns_sell_after_resistance_hunt(self):
        s = SrLiquidityGrab()
        level = 1.1000
        atr = 0.0010
        # 3 quiet, 1 hunt (high above level, close back below), 1 current bearish bar
        bars = [{"Open": level + 0.0001, "High": level + 0.0002,
                 "Low": level - 0.0001, "Close": level + 0.0001,
                 "Volume": 1000}] * 3
        bars.append({"Open": level - 0.0005, "High": level + 0.0025,
                     "Low": level - 0.0010, "Close": level - 0.0008,
                     "Volume": 1000})
        # current bar: bearish, close just below level
        bars.append({"Open": level - 0.0001, "High": level - 0.00005,
                     "Low": level - 0.0005, "Close": level - 0.0003,
                     "Volume": 1000})
        df = pd.DataFrame(bars,
                          index=pd.date_range("2024-01-01", periods=5, freq="15min"))

        ctx = SignalContext(
            entry=level - 0.0003, open_price=level - 0.0001,
            atr=atr, adx=20.0,
            sr_levels=[level], df=df,
            symbol="EURUSD=X", tf="15m", pip_mult=10000,
        )
        cand = s.evaluate(ctx)
        assert cand is not None
        assert cand.signal == "SELL"
        # SL should be above the hunt high
        assert cand.sl > level
