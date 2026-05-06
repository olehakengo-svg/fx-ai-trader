from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.tokyo_range_breakout import TokyoRangeBreakout


def _df(*, final_close: float = 150.315, london_low: float = 150.28,
        tokyo_low: float = 150.05, tokyo_high: float = 150.30,
        end: str = "2026-05-06 08:15") -> pd.DataFrame:
    idx = pd.date_range(end=end, periods=58, freq="15min", tz="UTC")
    n = len(idx)
    open_ = np.full(n, 150.18)
    high = np.full(n, 150.22)
    low = np.full(n, 150.12)
    close = np.full(n, 150.18)

    tokyo_mask = idx.hour < 7
    high[tokyo_mask] = tokyo_high - 0.02
    low[tokyo_mask] = tokyo_low + 0.02
    close[tokyo_mask] = (tokyo_high + tokyo_low) / 2
    open_[tokyo_mask] = close[tokyo_mask]
    today_tokyo_idx = np.flatnonzero(tokyo_mask)
    high[today_tokyo_idx[1]] = tokyo_high
    low[today_tokyo_idx[2]] = tokyo_low

    london_mask = idx.hour == 7
    open_[london_mask] = tokyo_high - 0.03
    high[london_mask] = tokyo_high - 0.01
    low[london_mask] = tokyo_low + 0.04
    close[london_mask] = tokyo_high - 0.02

    open_[-1] = 150.289
    high[-1] = max(final_close + 0.01, tokyo_high + 0.02)
    low[-1] = london_low
    close[-1] = final_close

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.10),
            "atr7": np.full(n, 0.10),
            "ema9": np.full(n, 150.24),
            "ema21": np.full(n, 150.20),
            "ema50": np.full(n, 150.15),
            "ema200": np.full(n, 150.00),
            "adx": np.full(n, 24.0),
            "adx_pos": np.full(n, 25.0),
            "adx_neg": np.full(n, 20.0),
            "rsi": np.full(n, 56.0),
            "rsi5": np.full(n, 56.0),
            "rsi9": np.full(n, 56.0),
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 50.0),
            "macd_hist": np.zeros(n),
            "bb_pband": np.full(n, 0.55),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, htf_agreement: str = "mixed") -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        ema50=float(row["ema50"]),
        ema200=float(row["ema200"]),
        adx=float(row["adx"]),
        adx_pos=float(row["adx_pos"]),
        adx_neg=float(row["adx_neg"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        rsi9=float(row["rsi9"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        bbpb=float(row["bb_pband"]),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="USDJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        df=df,
        htf={"agreement": htf_agreement},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_legacy_unbuffered_breakout(monkeypatch):
    monkeypatch.delenv("TOKYO_RANGE_BREAKOUT_REDESIGN_V2", raising=False)
    TokyoRangeBreakout.reset_dedup_state()

    cand = TokyoRangeBreakout().evaluate(_ctx(_df(final_close=150.302)))

    assert cand is not None
    assert cand.entry_type == "tokyo_range_breakout_up"
    assert cand.max_hold_bars is None
    assert not any("TOKYO_RANGE_BREAKOUT_REDESIGN_V2" in r for r in cand.reasons)


def test_v2_requires_buffered_bar_close(monkeypatch):
    monkeypatch.setenv("TOKYO_RANGE_BREAKOUT_REDESIGN_V2", "1")
    TokyoRangeBreakout.reset_dedup_state()

    assert TokyoRangeBreakout().evaluate(_ctx(_df(final_close=150.302))) is None

    cand = TokyoRangeBreakout().evaluate(_ctx(_df(final_close=150.315)))
    assert cand is not None
    assert any("bar-close buffered breakout" in r for r in cand.reasons)


def test_v2_blocks_overwide_tokyo_range_and_uses_invalidation_exit(monkeypatch):
    monkeypatch.setenv("TOKYO_RANGE_BREAKOUT_REDESIGN_V2", "1")
    TokyoRangeBreakout.reset_dedup_state()

    assert TokyoRangeBreakout().evaluate(
        _ctx(_df(tokyo_low=149.80, tokyo_high=150.30, final_close=150.315))
    ) is None

    TokyoRangeBreakout.reset_dedup_state()
    cand = TokyoRangeBreakout().evaluate(
        _ctx(_df(tokyo_low=150.05, tokyo_high=150.30, final_close=150.315, london_low=150.29))
    )

    assert cand is not None
    assert cand.max_hold_bars == TokyoRangeBreakout.MAX_HOLD_BARS
    assert cand.sl < 150.30
    assert round((cand.tp - 150.315) / (150.315 - cand.sl), 2) == 2.0
    assert any("Tokyo compression" in r for r in cand.reasons)


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 151.0, 150.0, [], "other", 9.0)
    trb = Candidate("BUY", 70, 150.0, 151.0, [], "tokyo_range_breakout_up", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("TOKYO_RANGE_BREAKOUT_REDESIGN_V2", "1")
    monkeypatch.delenv("TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, trb], other) == []

    monkeypatch.setenv("TOKYO_RANGE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, trb], other) == [trb]
