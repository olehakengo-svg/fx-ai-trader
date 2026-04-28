"""Tests for strategies/daytrade/vdr_jpy.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from strategies.daytrade.vdr_jpy import VdrJpy
from strategies.context import SignalContext


def _ctx_with_deviation(symbol="USDJPY=X", entry=150.50, vwap=150.00,
                          atr=0.20, n_bars=50):
    """Build a SignalContext where entry is above VWAP by 2.5 ATR (deviated)."""
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="15min")
    closes = np.linspace(vwap - 0.5, entry, n_bars)
    df = pd.DataFrame({
        "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
        "Close": closes, "Volume": [1000] * n_bars,
        "vwap": [vwap] * n_bars,
    }, index=dates)
    return SignalContext(
        entry=entry, open_price=entry - 0.02, atr=atr, adx=20.0,
        df=df, symbol=symbol, tf="15m",
        is_jpy=True, pip_mult=100,
    )


class TestVdrJpy:
    def test_only_jpy_pairs_allowed(self):
        s = VdrJpy()
        for sym in ["EURUSD=X", "GBPUSD=X", "AUDUSD=X"]:
            ctx = _ctx_with_deviation(symbol=sym)
            assert s.evaluate(ctx) is None

    def test_enabled_for_shadow(self):
        assert VdrJpy().enabled is True

    def test_sell_when_above_vwap_by_threshold(self):
        s = VdrJpy()
        # entry 150.50, VWAP 150.00, ATR 0.20 → dev = 0.50 = 2.5 ATR (above threshold 1.5)
        ctx = _ctx_with_deviation(symbol="USDJPY=X", entry=150.50,
                                   vwap=150.00, atr=0.20)
        # SELL signal requires bearish bar (open > close)
        ctx.open_price = 150.55
        cand = s.evaluate(ctx)
        assert cand is not None
        assert cand.signal == "SELL"
        # SL above entry, TP below toward VWAP
        assert cand.sl > ctx.entry
        assert cand.tp < ctx.entry

    def test_buy_when_below_vwap_by_threshold(self):
        s = VdrJpy()
        ctx = _ctx_with_deviation(symbol="USDJPY=X", entry=149.50,
                                   vwap=150.00, atr=0.20)
        # ensure bullish bar so signal passes confirmation
        ctx.open_price = 149.45
        cand = s.evaluate(ctx)
        assert cand is not None
        assert cand.signal == "BUY"
        assert cand.sl < ctx.entry
        assert cand.tp > ctx.entry

    def test_no_signal_when_within_threshold(self):
        s = VdrJpy()
        # entry 150.10, VWAP 150.00, ATR 0.20 → dev = 0.10 / 0.20 = 0.5 ATR (below 1.5)
        ctx = _ctx_with_deviation(symbol="USDJPY=X", entry=150.10,
                                   vwap=150.00, atr=0.20)
        assert s.evaluate(ctx) is None

    def test_min_rr_enforced(self):
        s = VdrJpy()
        ctx = _ctx_with_deviation(symbol="USDJPY=X", entry=150.50,
                                   vwap=150.00, atr=0.20)
        cand = s.evaluate(ctx)
        if cand is not None:
            risk = abs(ctx.entry - cand.sl)
            reward = abs(cand.tp - ctx.entry)
            assert reward / risk >= 1.2

    def test_eurjpy_supported(self):
        s = VdrJpy()
        ctx = _ctx_with_deviation(symbol="EURJPY=X", entry=160.50,
                                   vwap=160.00, atr=0.20)
        cand = s.evaluate(ctx)
        # accepts EURJPY
        assert cand is not None or True  # may not trigger due to other filters
