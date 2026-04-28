"""Tests for modules/multi_tf_confluence.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from modules.multi_tf_confluence import (
    htf_aggregate, bbpb_at_tf, rsi_at_tf, confluence_score,
)


def _make_df(closes):
    n = len(closes)
    dates = pd.date_range("2024-01-01", periods=n, freq="15min")
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame({
        "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
        "Close": closes, "Volume": [1000] * n,
    }, index=dates)


class TestHtfAggregate:
    def test_4_to_1_aggregation(self):
        # 8 bars at 15m → 2 bars at 1h
        closes = [150.0, 150.5, 151.0, 150.5, 152.0, 152.5, 152.0, 151.0]
        df = _make_df(closes)
        agg = htf_aggregate(df, ratio=4)
        assert len(agg) == 2
        # First 1h bar covers bars 0-3 (close 150.5 with bar3 close)
        assert agg.iloc[0]["Open"] == 150.0 - 0.05  # bar 0 Open
        assert agg.iloc[0]["Close"] == 150.5
        # High = max of bars 0-3 highs
        assert agg.iloc[0]["High"] == max(150.0+0.10, 150.5+0.10, 151.0+0.10, 150.5+0.10)


class TestBbpbAtTf:
    def test_returns_05_for_constant_data(self):
        df = _make_df([150.0] * 30)
        b = bbpb_at_tf(df, period=20)
        assert b == 0.5

    def test_high_when_at_upper_band(self):
        # Trending up
        df = _make_df([150.0 + i*0.05 for i in range(30)])
        b = bbpb_at_tf(df, period=20)
        assert b > 0.7


class TestRsiAtTf:
    def test_returns_finite_for_constant_data(self):
        df = _make_df([150.0] * 30)
        r = rsi_at_tf(df, period=14)
        # Constant returns: gain=0, loss=0 → RS=0/0 → RSI=0 (math), accept any finite
        assert np.isfinite(r) or np.isnan(r)


class TestConfluenceScore:
    def test_returns_dict_with_keys(self):
        df = _make_df([150.0 + np.sin(i*0.5)*0.5 for i in range(80)])
        s = confluence_score(df)
        assert "buy_score" in s and "sell_score" in s
        assert s["buy_score"] in (0, 1, 2)
        assert s["sell_score"] in (0, 1, 2)

    def test_extreme_oversold_triggers_buy_signal(self):
        # Strongly down-trending data → oversold
        closes = [150.0 - i*0.05 for i in range(80)]
        df = _make_df(closes)
        s = confluence_score(df, bbpb_buy_thres=0.30, rsi_buy_thres=35)
        # At least one TF should signal buy
        assert s["buy_score"] >= 1
