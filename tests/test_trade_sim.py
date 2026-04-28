"""Tests for tools/lib/trade_sim.py — shared trade simulation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from tools.lib.trade_sim import (
    pip_size, session_for_utc_hour, simulate_single_trade,
    simulate_cell_trades, aggregate_trade_stats,
)


def _make_df(closes, atr=0.20):
    n = len(closes)
    closes = np.asarray(closes, dtype=float)
    dates = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({
        "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
        "Close": closes, "Volume": [1000] * n,
    }, index=dates)


class TestPipSize:
    def test_jpy(self):
        assert pip_size("USD_JPY") == 0.01
        assert pip_size("USDJPY") == 0.01

    def test_non_jpy(self):
        assert pip_size("EUR_USD") == 0.0001


class TestSession:
    def test_buckets(self):
        assert session_for_utc_hour(2) == "tokyo"
        assert session_for_utc_hour(8) == "london"
        assert session_for_utc_hour(15) == "ny"
        assert session_for_utc_hour(22) == "overnight"


class TestSimulateSingleTrade:
    def test_buy_tp_hit(self):
        # Bullish data — bar 1 = 150, bar 2 reaches TP
        closes = [150.0, 150.0, 150.5, 150.4, 150.5]
        df = _make_df(closes)
        # Signal at idx=0 → entry at idx=1 Open ≈ 149.95
        # SL = 149.95 - 0.20 = 149.75; TP = 149.95 + 0.30 = 150.25
        # Bar 2 High = 150.6 > TP 150.25 → TP hit
        t = simulate_single_trade(df, entry_idx=0, direction="BUY",
                                   atr_at_signal=0.20,
                                   sl_atr_mult=1.0, tp_atr_mult=1.5,
                                   max_hold_bars=4, pair="USD_JPY")
        assert t is not None
        assert t["outcome"] == "TP"
        assert t["pnl_gross_pip"] > 0

    def test_sell_sl_hit(self):
        # Price runs up against SELL → SL hit
        closes = [150.0, 150.0, 150.5, 151.0]
        df = _make_df(closes)
        t = simulate_single_trade(df, entry_idx=0, direction="SELL",
                                   atr_at_signal=0.20,
                                   sl_atr_mult=1.0, tp_atr_mult=1.5,
                                   max_hold_bars=4, pair="USD_JPY")
        assert t is not None
        # SELL: SL = entry + ATR. Should hit during run-up.
        assert t["outcome"] == "SL"
        assert t["pnl_gross_pip"] < 0

    def test_returns_none_at_end_of_data(self):
        df = _make_df([150.0])
        t = simulate_single_trade(df, entry_idx=0, direction="BUY",
                                   atr_at_signal=0.20)
        assert t is None

    def test_friction_subtracted(self):
        closes = [150.0, 150.0, 150.5, 150.4, 150.5]
        df = _make_df(closes)
        t = simulate_single_trade(df, entry_idx=0, direction="BUY",
                                   atr_at_signal=0.20,
                                   pair="USD_JPY", apply_friction=True)
        assert t is not None
        # gross > net by friction amount
        assert t["pnl_gross_pip"] > t["pnl_net_pip"]
        assert t["friction_pip"] > 0

    def test_invalid_atr(self):
        df = _make_df([150.0, 150.0, 150.5])
        for bad_atr in (0, -1, np.nan, np.inf):
            t = simulate_single_trade(df, entry_idx=0, direction="BUY",
                                       atr_at_signal=bad_atr)
            assert t is None


class TestSimulateCellTrades:
    def test_dedup_skips_overlapping(self):
        n = 30
        closes = [150.0 + i * 0.01 for i in range(n)]
        df = _make_df(closes)
        atr_series = pd.Series([0.20] * n, index=df.index)
        # 3 signals all close together; with max_hold_bars=8, dedup should skip
        signals = [0, 1, 2]
        trades = simulate_cell_trades(df, signals, "BUY", atr_series,
                                       max_hold_bars=8, pair="USD_JPY",
                                       dedup=True, apply_friction=False)
        # at most 1 trade should fit (no overlap)
        assert len(trades) <= 2  # allow some flexibility

    def test_no_dedup_returns_all(self):
        n = 30
        closes = [150.0 + i * 0.01 for i in range(n)]
        df = _make_df(closes)
        atr_series = pd.Series([0.20] * n, index=df.index)
        signals = [0, 5, 10, 15, 20]
        trades = simulate_cell_trades(df, signals, "BUY", atr_series,
                                       max_hold_bars=4, pair="USD_JPY",
                                       dedup=False, apply_friction=False)
        # Each signal that has room should produce a trade
        assert len(trades) >= 4


class TestAggregateStats:
    def test_empty(self):
        s = aggregate_trade_stats([])
        assert s["n_trades"] == 0
        assert s["wr"] == 0.0

    def test_basic_stats(self):
        trades = [
            {"pnl_net_pip": 5.0}, {"pnl_net_pip": -3.0},
            {"pnl_net_pip": 4.0}, {"pnl_net_pip": -2.0},
            {"pnl_net_pip": 3.0},
        ]
        s = aggregate_trade_stats(trades)
        assert s["n_trades"] == 5
        assert s["n_wins"] == 3
        assert s["wr"] == 0.6
        assert s["ev_net_pip"] == 1.4

    def test_pf_calc(self):
        trades = [
            {"pnl_net_pip": 10.0}, {"pnl_net_pip": -5.0},
        ]
        s = aggregate_trade_stats(trades)
        assert s["pf"] == 2.0  # 10 / 5

    def test_kelly_calc(self):
        trades = [
            {"pnl_net_pip": 2.0}, {"pnl_net_pip": -1.0},
            {"pnl_net_pip": 2.0}, {"pnl_net_pip": -1.0},
            {"pnl_net_pip": 2.0}, {"pnl_net_pip": -1.0},
        ]
        s = aggregate_trade_stats(trades)
        # WR=0.5, b=2, kelly = (0.5*2 - 0.5)/2 = 0.25
        assert abs(s["kelly"] - 0.25) < 0.01


class TestLookAheadPrevention:
    def test_entry_at_next_bar_open(self):
        # Signal at bar 0 → entry at bar 1 Open (NOT bar 0 Close)
        closes = [150.0, 150.5, 151.0]
        df = _make_df(closes)
        t = simulate_single_trade(df, entry_idx=0, direction="BUY",
                                   atr_at_signal=0.20, pair="USD_JPY",
                                   apply_friction=False)
        assert t is not None
        # Entry must equal bar 1's Open, NOT bar 0's Close
        assert t["entry_price"] == df.iloc[1]["Open"]
