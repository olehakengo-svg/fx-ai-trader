"""Tests for strategies/daytrade/pd_eurjpy_h20_bbpb3_sell.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from strategies.context import SignalContext
from strategies.daytrade.pd_eurjpy_h20_bbpb3_sell import PdEurJpyH20Bbpb3Sell


def _make_ctx(symbol="EURJPY=X", entry=160.000, atr=0.30, bbpb=0.7,
              hour_utc=20, tf="15m", is_friday=False, rsi=55.0):
    df = pd.DataFrame({
        "Open": [entry] * 5,
        "High": [entry + 0.05] * 5,
        "Low": [entry - 0.05] * 5,
        "Close": [entry] * 5,
        "Volume": [1000] * 5,
    }, index=pd.date_range("2026-04-28 19:00", periods=5, freq="15min"))
    return SignalContext(
        entry=entry, atr=atr, bbpb=bbpb, rsi=rsi,
        symbol=symbol, tf=tf, hour_utc=hour_utc, is_friday=is_friday,
        is_jpy=("JPY" in symbol), pip_mult=100, df=df,
    )


class TestPdEurJpyH20Bbpb3Sell:
    def test_returns_none_for_wrong_pair(self):
        s = PdEurJpyH20Bbpb3Sell()
        assert s.evaluate(_make_ctx(symbol="USDJPY=X")) is None
        assert s.evaluate(_make_ctx(symbol="GBPJPY=X")) is None
        assert s.evaluate(_make_ctx(symbol="EURUSD=X")) is None

    def test_returns_none_for_wrong_tf(self):
        s = PdEurJpyH20Bbpb3Sell()
        assert s.evaluate(_make_ctx(tf="5m")) is None
        assert s.evaluate(_make_ctx(tf="1h")) is None

    def test_returns_none_for_wrong_hour(self):
        s = PdEurJpyH20Bbpb3Sell()
        assert s.evaluate(_make_ctx(hour_utc=19)) is None
        assert s.evaluate(_make_ctx(hour_utc=21)) is None

    def test_returns_none_when_bbpb_outside_window(self):
        s = PdEurJpyH20Bbpb3Sell()
        # Below 0.6 (lower bound exclusive)
        assert s.evaluate(_make_ctx(bbpb=0.6)) is None
        assert s.evaluate(_make_ctx(bbpb=0.55)) is None
        # Above 0.8 (upper bound inclusive)
        assert s.evaluate(_make_ctx(bbpb=0.85)) is None

    def test_returns_none_on_friday(self):
        s = PdEurJpyH20Bbpb3Sell()
        assert s.evaluate(_make_ctx(is_friday=True)) is None

    def test_returns_none_for_zero_atr(self):
        s = PdEurJpyH20Bbpb3Sell()
        assert s.evaluate(_make_ctx(atr=0.0)) is None

    def test_returns_sell_in_window(self):
        s = PdEurJpyH20Bbpb3Sell()
        cand = s.evaluate(_make_ctx(bbpb=0.7))
        assert cand is not None
        assert cand.signal == "SELL"
        assert cand.entry_type == "pd_eurjpy_h20_bbpb3_sell"
        # SL above entry, TP below entry
        assert cand.sl > 160.000
        assert cand.tp < 160.000
        # RR ratio ~ 1.5 (TP_d / SL_d)
        sl_d = cand.sl - 160.000
        tp_d = 160.000 - cand.tp
        assert abs(tp_d / sl_d - 1.5) < 1e-6

    def test_bbpb_lower_boundary_excluded(self):
        s = PdEurJpyH20Bbpb3Sell()
        # 0.6 itself is excluded (open lower bound)
        assert s.evaluate(_make_ctx(bbpb=0.6)) is None
        # 0.6001 is included
        cand = s.evaluate(_make_ctx(bbpb=0.6001))
        assert cand is not None

    def test_bbpb_upper_boundary_included(self):
        s = PdEurJpyH20Bbpb3Sell()
        # 0.8 is included (closed upper bound)
        cand = s.evaluate(_make_ctx(bbpb=0.8))
        assert cand is not None

    def test_rsi_alignment_boost_in_reasons(self):
        s = PdEurJpyH20Bbpb3Sell()
        cand = s.evaluate(_make_ctx(rsi=65.0))
        assert cand is not None
        assert any("RSI" in r and "60" in r for r in cand.reasons)

    def test_strategy_attributes(self):
        s = PdEurJpyH20Bbpb3Sell()
        assert s.name == "pd_eurjpy_h20_bbpb3_sell"
        assert s.mode == "daytrade"
        assert s.enabled is True
        assert s.strategy_type == "reversal"
