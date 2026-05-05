from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.htf_false_breakout import HtfFalseBreakout


def _base_df(*, end: str = "2026-05-05 12:15", periods: int = 97) -> pd.DataFrame:
    idx = pd.date_range(end=end, periods=periods, freq="15min", tz="UTC")
    open_ = np.full(periods, 1.0950)
    high = np.full(periods, 1.1000)
    low = np.full(periods, 1.0900)
    close = np.full(periods, 1.0950)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(periods, 1000.0),
            "atr": np.full(periods, 0.0010),
            "rsi": np.full(periods, 50.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        rsi=float(row["rsi"]),
        ema9=1.0940,
        ema21=1.0960,
        adx=18.0,
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "mixed"},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_legacy_15m_pseudo_h1_breakout(monkeypatch):
    monkeypatch.delenv("HTF_FALSE_BREAKOUT_REDESIGN_V2", raising=False)
    df = _base_df()
    df.loc[pd.Timestamp("2026-05-05 11:30", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.0990,
        1.1020,
        1.0985,
        1.1015,
    ]
    df.loc[pd.Timestamp("2026-05-05 12:00", tz="UTC"), "Close"] = 1.0995
    df.loc[pd.Timestamp("2026-05-05 12:15", tz="UTC"), "Close"] = 1.0995

    cand = HtfFalseBreakout().evaluate(_ctx(df))

    assert cand is not None
    assert cand.signal == "SELL"


def test_v2_requires_closed_h1_close_breakout_and_rejects_15m_only_breakout(monkeypatch):
    monkeypatch.setenv("HTF_FALSE_BREAKOUT_REDESIGN_V2", "1")
    df = _base_df()
    df.loc[pd.Timestamp("2026-05-05 11:30", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.0990,
        1.1020,
        1.0985,
        1.1015,
    ]
    df.loc[pd.Timestamp("2026-05-05 12:00", tz="UTC"), "Close"] = 1.0995
    df.loc[pd.Timestamp("2026-05-05 12:15", tz="UTC"), "Close"] = 1.0995

    cand = HtfFalseBreakout().evaluate(_ctx(df))

    assert cand is None


def test_v2_accepts_closed_h1_breakout_then_first_15m_reentry(monkeypatch):
    monkeypatch.setenv("HTF_FALSE_BREAKOUT_REDESIGN_V2", "1")
    df = _base_df()
    df.loc[pd.Timestamp("2026-05-05 11:15", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.0990,
        1.1005,
        1.0980,
        1.1002,
    ]
    df.loc[pd.Timestamp("2026-05-05 11:30", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.1002,
        1.1014,
        1.0998,
        1.1008,
    ]
    df.loc[pd.Timestamp("2026-05-05 11:45", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.1008,
        1.1018,
        1.1004,
        1.1012,
    ]
    df.loc[pd.Timestamp("2026-05-05 12:00", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.1012,
        1.1020,
        1.1006,
        1.1015,
    ]
    df.loc[pd.Timestamp("2026-05-05 12:15", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.1010,
        1.1012,
        1.0990,
        1.0995,
    ]

    cand = HtfFalseBreakout().evaluate(_ctx(df))

    assert cand is not None
    assert cand.signal == "SELL"
    assert round(cand.sl, 5) == 1.10230
    assert any("HTF_FALSE_BREAKOUT_REDESIGN_V2" in reason for reason in cand.reasons)
    assert any("closed_h1_break_time=2026-05-05 12:00:00+00:00" in reason for reason in cand.reasons)


def test_v2_rejects_late_second_reentry(monkeypatch):
    monkeypatch.setenv("HTF_FALSE_BREAKOUT_REDESIGN_V2", "1")
    df = _base_df(end="2026-05-05 12:30", periods=98)
    df.loc[pd.Timestamp("2026-05-05 11:15", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.0990,
        1.1005,
        1.0980,
        1.1002,
    ]
    df.loc[pd.Timestamp("2026-05-05 11:30", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.1002,
        1.1014,
        1.0998,
        1.1008,
    ]
    df.loc[pd.Timestamp("2026-05-05 11:45", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.1008,
        1.1018,
        1.1004,
        1.1012,
    ]
    df.loc[pd.Timestamp("2026-05-05 12:00", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.1012,
        1.1020,
        1.1006,
        1.1015,
    ]
    df.loc[pd.Timestamp("2026-05-05 12:15", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.1010,
        1.1012,
        1.0990,
        1.0995,
    ]
    df.loc[pd.Timestamp("2026-05-05 12:30", tz="UTC"), ["Open", "High", "Low", "Close"]] = [
        1.0997,
        1.1001,
        1.0988,
        1.0996,
    ]

    cand = HtfFalseBreakout().evaluate(_ctx(df))

    assert cand is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="BUY", confidence=80, sl=1.0, tp=2.0, reasons=[], entry_type="other", score=9.0)
    hfb = Candidate(
        signal="SELL",
        confidence=70,
        sl=2.0,
        tp=1.0,
        reasons=[],
        entry_type="htf_false_breakout",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("HTF_FALSE_BREAKOUT_REDESIGN_V2", "1")
    monkeypatch.delenv("HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, hfb], other) == []

    monkeypatch.setenv("HTF_FALSE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, hfb], other) == [hfb]
