from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.ema200_reversal import Ema200TrendReversal


@pytest.fixture(autouse=True)
def _clear_related_flags(monkeypatch):
    monkeypatch.delenv("EMA200_REVERSAL_REDESIGN_V2", raising=False)
    monkeypatch.delenv("EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    monkeypatch.delenv("EMA200_TREND_REVERSAL_REDESIGN_V2", raising=False)
    monkeypatch.delenv("EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)


def _df(*, hour=14, n=25) -> pd.DataFrame:
    idx = pd.date_range(end=f"2026-05-05 {hour:02d}:00", periods=n, freq="15min", tz="UTC")
    close = np.full(n, 150.16)
    open_ = np.full(n, 150.14)
    high = np.full(n, 150.20)
    low = np.full(n, 150.10)
    ema200 = np.full(n, 150.00)
    macdh = np.full(n, 0.01)

    close[-4] = 149.94
    close[-3] = 150.08
    close[-2] = 150.12
    close[-1] = 150.16
    macdh[-2] = 0.01
    macdh[-1] = 0.03

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "atr": np.full(n, 0.50),
            "atr7": np.full(n, 0.50),
            "ema9": np.full(n, 150.08),
            "ema21": np.full(n, 150.04),
            "ema50": np.full(n, 150.02),
            "ema200": ema200,
            "rsi": np.full(n, 52.0),
            "macd_hist": macdh,
            "adx": np.full(n, 20.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, symbol="USDJPY=X", bar_time=None, hour_utc=None) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    is_jpy = "JPY" in symbol.upper()
    if hour_utc is None:
        hour_utc = df.index[-1].hour
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        ema50=float(row["ema50"]),
        ema200=float(row["ema200"]),
        rsi=float(row["rsi"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        adx=float(row["adx"]),
        symbol=symbol,
        tf="15m",
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        backtest_mode=True,
        bar_time=bar_time,
        hour_utc=hour_utc,
    )


def test_trend_v2_default_off_preserves_existing_all_pair_signal(monkeypatch):
    monkeypatch.delenv("EMA200_TREND_REVERSAL_REDESIGN_V2", raising=False)

    cand = Ema200TrendReversal().evaluate(_ctx(_df(hour=20), symbol="EURJPY=X"))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("EMA200_TREND_REVERSAL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_trend_v2_routes_to_usd_jpy_only(monkeypatch):
    monkeypatch.setenv("EMA200_TREND_REVERSAL_REDESIGN_V2", "1")

    assert Ema200TrendReversal().evaluate(_ctx(_df(hour=14), symbol="EURJPY=X")) is None


def test_trend_v2_accepts_usd_jpy_overlap_session(monkeypatch):
    monkeypatch.setenv("EMA200_TREND_REVERSAL_REDESIGN_V2", "1")

    cand = Ema200TrendReversal().evaluate(_ctx(_df(hour=14), symbol="USDJPY=X"))

    assert cand is not None
    assert cand.signal == "BUY"
    assert any("EMA200_TREND_REVERSAL_REDESIGN_V2" in reason for reason in cand.reasons)
    assert any("hour_utc=14" in reason for reason in cand.reasons)


def test_trend_v2_blocks_usd_jpy_outside_overlap_session(monkeypatch):
    monkeypatch.setenv("EMA200_TREND_REVERSAL_REDESIGN_V2", "1")

    assert Ema200TrendReversal().evaluate(_ctx(_df(hour=11), symbol="USDJPY=X")) is None
    assert Ema200TrendReversal().evaluate(_ctx(_df(hour=16), symbol="USDJPY=X")) is None


def test_trend_v2_uses_bar_time_hour_fallback(monkeypatch):
    monkeypatch.setenv("EMA200_TREND_REVERSAL_REDESIGN_V2", "1")
    df = _df(hour=11)
    bar_time = pd.Timestamp("2026-05-05 13:00", tz="UTC")

    cand = Ema200TrendReversal().evaluate(
        _ctx(df, symbol="USDJPY=X", bar_time=bar_time, hour_utc=None)
    )

    assert cand is not None
    assert any("hour_utc=13" in reason for reason in cand.reasons)


def test_trend_v2_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    ema200 = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="ema200_trend_reversal",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("EMA200_TREND_REVERSAL_REDESIGN_V2", "1")
    monkeypatch.delenv("EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, ema200], other) == []

    monkeypatch.setenv("EMA200_TREND_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, ema200], other) == [ema200]
