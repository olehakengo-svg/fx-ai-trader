from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.ma_trend_perfect import MaTrendPerfect


def _df(*, closed_bull: bool = False) -> pd.DataFrame:
    idx = pd.date_range("2026-05-05 00:00", periods=3, freq="min", tz="UTC")
    rows = [
        {
            "Open": 151.000,
            "High": 151.120,
            "Low": 150.980,
            "Close": 151.040,
            "macd_hist": 0.0001,
        },
        {
            "Open": 151.050 if closed_bull else 151.120,
            "High": 151.180,
            "Low": 151.020,
            "Close": 151.130 if closed_bull else 151.060,
            "macd_hist": 0.0003 if closed_bull else 0.0000,
        },
        {
            "Open": 151.070,
            "High": 151.240,
            "Low": 151.060,
            "Close": 151.200,
            "macd_hist": 0.0004,
        },
    ]
    df = pd.DataFrame(rows, index=idx)
    for col, val in {
        "atr": 0.080,
        "atr7": 0.070,
        "ema9": 151.15,
        "ema21": 151.00,
        "ema50": 150.80,
        "ema200": 150.20,
        "rsi": 55.0,
        "rsi5": 55.0,
        "rsi9": 55.0,
        "adx": 26.0,
        "adx_pos": 31.0,
        "adx_neg": 13.0,
        "bb_pband": 0.58,
    }.items():
        df[col] = val
    return df


def _htf(*, m5_closed=True) -> dict:
    return {
        "h1": {"close": 151.20, "ema200": 150.80},
        "m15": {
            "close": 151.18,
            "ema9": 151.16,
            "ema21": 151.00,
            "ema50": 150.70,
            "ema_slope": 0.04,
            "adx": 29.0,
            "is_closed": True,
        },
        "m5": {
            "close": 151.08,
            "prev_close": 150.96,
            "ema21": 151.00,
            "is_closed": m5_closed,
        },
    }


def _ctx(*, closed_bull: bool = False, backtest_mode: bool = True, m5_closed=True) -> SignalContext:
    df = _df(closed_bull=closed_bull)
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
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        bbpb=float(row["bb_pband"]),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="USDJPY=X",
        tf="1m",
        is_jpy=True,
        pip_mult=100,
        htf=_htf(m5_closed=m5_closed),
        df=df,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
    )


def test_v2_default_off_keeps_current_bar_confirmation(monkeypatch):
    monkeypatch.delenv("MA_TREND_PERFECT_REDESIGN_V2", raising=False)

    cand = MaTrendPerfect().evaluate(_ctx(closed_bull=False))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("MA_TREND_PERFECT_REDESIGN_V2" in r for r in cand.reasons)


def test_v2_uses_closed_1m_signal_bar_not_current_bar(monkeypatch):
    monkeypatch.setenv("MA_TREND_PERFECT_REDESIGN_V2", "1")

    assert MaTrendPerfect().evaluate(_ctx(closed_bull=False)) is None
    cand = MaTrendPerfect().evaluate(_ctx(closed_bull=True))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.sl < _ctx(closed_bull=True).entry < cand.tp
    assert any("closed 1m BUY signal_bar=2026-05-05 00:01:00+00:00" in r for r in cand.reasons)
    assert any("次バー以降で約定" in r for r in cand.reasons)


def test_v2_requires_closed_m5_snapshot(monkeypatch):
    monkeypatch.setenv("MA_TREND_PERFECT_REDESIGN_V2", "1")

    cand = MaTrendPerfect().evaluate(_ctx(closed_bull=True, m5_closed=False))

    assert cand is None


def test_v2_live_per_bar_dedup(monkeypatch):
    monkeypatch.setenv("MA_TREND_PERFECT_REDESIGN_V2", "1")
    MaTrendPerfect.reset_dedup_state()

    first = MaTrendPerfect().evaluate(_ctx(closed_bull=True, backtest_mode=False))
    second = MaTrendPerfect().evaluate(_ctx(closed_bull=True, backtest_mode=False))

    assert first is not None
    assert second is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("SELL", 70, 1.2, 1.0, ["best"], "other", 7.0)
    mtp = Candidate("BUY", 65, 1.0, 1.2, ["mtp"], "ma_trend_perfect", 4.0)

    monkeypatch.setenv("MA_TREND_PERFECT_REDESIGN_V2", "1")
    monkeypatch.delenv("MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, mtp], best) == []

    monkeypatch.setenv("MA_TREND_PERFECT_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, mtp], best) == [mtp]
