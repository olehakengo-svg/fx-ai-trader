"""Tests for strategies/daytrade/sr_anti_hunt_bounce.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from strategies.daytrade.sr_anti_hunt_bounce import SrAntiHuntBounce
from strategies.context import SignalContext


def _make_ctx(symbol="EURUSD=X", entry=1.1000, sr_levels=None, atr=0.0010,
              adx=20.0, open_price=None, df=None, bbpb=0.5):
    if open_price is None:
        open_price = entry - 0.0002  # default: bullish bar
    if sr_levels is None:
        sr_levels = []
    if df is None:
        # 5 quiet bars, no hunts
        df = pd.DataFrame({
            "Open": [entry - 0.0001] * 5,
            "High": [entry + 0.0001] * 5,
            "Low": [entry - 0.0002] * 5,
            "Close": [entry] * 5,
            "Volume": [1000] * 5,
        }, index=pd.date_range("2024-01-01", periods=5, freq="15min"))
    return SignalContext(
        entry=entry, open_price=open_price, atr=atr, adx=adx,
        bbpb=bbpb, sr_levels=sr_levels, df=df, symbol=symbol, tf="15m",
        is_jpy=("JPY" in symbol), pip_mult=100 if "JPY" in symbol else 10000,
    )


class TestSrAntiHuntBounce:
    def test_returns_none_for_disallowed_pair(self):
        s = SrAntiHuntBounce()
        ctx = _make_ctx(symbol="EURJPY=X", sr_levels=[1.1010])
        assert s.evaluate(ctx) is None

    def test_returns_none_when_no_sr_levels(self):
        s = SrAntiHuntBounce()
        ctx = _make_ctx(symbol="EURUSD=X", sr_levels=[])
        assert s.evaluate(ctx) is None

    def test_returns_none_when_strong_trend(self):
        s = SrAntiHuntBounce()
        ctx = _make_ctx(symbol="EURUSD=X", sr_levels=[1.0998], adx=35.0)
        assert s.evaluate(ctx) is None

    def test_returns_none_when_far_from_sr(self):
        s = SrAntiHuntBounce()
        # SR at 1.0900, entry at 1.1000, atr 0.0010 → distance = 0.01 = 10 ATR
        ctx = _make_ctx(symbol="EURUSD=X", entry=1.1000, sr_levels=[1.0900])
        assert s.evaluate(ctx) is None

    def test_returns_buy_at_support_with_bullish_bar(self):
        s = SrAntiHuntBounce()
        # Entry just above support level
        ctx = _make_ctx(symbol="EURUSD=X", entry=1.1002,
                        sr_levels=[1.1000], atr=0.0010,
                        open_price=1.1000)  # bullish bar
        cand = s.evaluate(ctx)
        assert cand is not None
        assert cand.signal == "BUY"
        assert cand.entry_type == "sr_anti_hunt_bounce"
        # SL must be below the level (anti-hunt → far below)
        assert cand.sl < 1.1000

    def test_returns_sell_at_resistance_with_bearish_bar(self):
        s = SrAntiHuntBounce()
        ctx = _make_ctx(symbol="EURUSD=X", entry=1.0998,
                        sr_levels=[1.1000], atr=0.0010,
                        open_price=1.1000)  # bearish bar
        cand = s.evaluate(ctx)
        assert cand is not None
        assert cand.signal == "SELL"
        # SL above the level (anti-hunt)
        assert cand.sl > 1.1000

    def test_sl_is_far_from_level_anti_hunt(self):
        """SL must be at least P90 wick excursion away from level (37 pip for EURUSD)."""
        s = SrAntiHuntBounce()
        ctx = _make_ctx(symbol="EURUSD=X", entry=1.1002,
                        sr_levels=[1.1000], atr=0.0010,
                        open_price=1.1000)
        cand = s.evaluate(ctx)
        assert cand is not None
        # P90 = 37 pip = 0.0037, SL_BUFFER = 0.5×ATR = 0.0005 → total 0.0042 below level
        sl_distance = 1.1000 - cand.sl
        assert sl_distance >= 0.0037, (
            f"SL too close to level — would be hunted! "
            f"distance={sl_distance}, expected >= 0.0037"
        )

    def test_skips_when_recent_hunt_in_progress(self):
        """If the recent bars show a hunt-style breach, skip entry."""
        s = SrAntiHuntBounce()
        # Build df with a recent hunt bar (high > level, close < level)
        bars = []
        for i in range(3):
            bars.append({"Open": 1.0995, "High": 1.0998, "Low": 1.0993, "Close": 1.0997,
                         "Volume": 1000})
        # Recent bar: hunt at level 1.1000
        bars.append({"Open": 1.0998, "High": 1.1015, "Low": 1.0996, "Close": 1.0997,
                     "Volume": 1000})
        bars.append({"Open": 1.0997, "High": 1.0999, "Low": 1.0993, "Close": 1.0998,
                     "Volume": 1000})  # current bar — bullish back at level
        df = pd.DataFrame(bars, index=pd.date_range("2024-01-01", periods=5, freq="15min"))
        ctx = _make_ctx(symbol="EURUSD=X", entry=1.0998,
                        sr_levels=[1.1000], atr=0.0010,
                        open_price=1.0997, df=df)
        # The hunt at level 1.1000 was just 1 bar ago → skip
        cand = s.evaluate(ctx)
        assert cand is None

    def test_rr_at_least_1_5(self):
        s = SrAntiHuntBounce()
        ctx = _make_ctx(symbol="EURUSD=X", entry=1.1002,
                        sr_levels=[1.1000], atr=0.0010,
                        open_price=1.1000)
        cand = s.evaluate(ctx)
        assert cand is not None
        risk = abs(ctx.entry - cand.sl)
        reward = abs(cand.tp - ctx.entry)
        assert reward / risk >= 1.5
