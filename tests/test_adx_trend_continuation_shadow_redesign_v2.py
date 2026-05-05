from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.context import SignalContext
from strategies.base import Candidate
from strategies.daytrade.adx_trend_continuation import AdxTrendContinuation


def _df(*, n=20, signal_bar=True, pullback=True) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.1010)
    close = np.full(n, 1.1011)
    high = np.full(n, 1.1014)
    low = np.full(n, 1.1009)
    rsi = np.full(n, 50.0)

    if pullback:
        low[-2] = 1.1008
        rsi[-2] = 50.0
    else:
        low[-2] = 1.1013
        rsi[-2] = 60.0

    if signal_bar:
        open_[-1] = 1.1012
        close[-1] = 1.1018
        high[-1] = 1.1020
        low[-1] = 1.1011
        rsi[-1] = 52.0
    else:
        open_[-1] = 1.1018
        close[-1] = 1.1012
        high[-1] = 1.1020
        low[-1] = 1.1011
        rsi[-1] = 52.0

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": np.full(n, 1.1010),
            "ema21": np.full(n, 1.1000),
            "ema50": np.full(n, 1.0990),
            "ema200": np.full(n, 1.0980),
            "adx": np.full(n, 30.0),
            "adx_pos": np.full(n, 30.0),
            "adx_neg": np.full(n, 15.0),
            "rsi": rsi,
            "rsi5": rsi,
            "rsi9": rsi,
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 55.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.full(n, 0.0001),
            "bb_upper": np.full(n, 1.1040),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0960),
            "bb_pband": np.full(n, 0.75),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool, bar_time=None) -> SignalContext:
    row = df.iloc[-1]
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
        bbpb=float(row["bb_pband"]),
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "bull"},
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )


def test_v2_default_off_allows_existing_repeat(monkeypatch):
    monkeypatch.delenv("ADX_TREND_CONTINUATION_REDESIGN_V2", raising=False)
    AdxTrendContinuation.reset_dedup_state()
    s = AdxTrendContinuation()
    ctx = _ctx(_df(), backtest_mode=True, bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    assert s.evaluate(ctx) is not None
    assert s.evaluate(ctx) is not None


def test_v2_per_bar_dedup_blocks_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("ADX_TREND_CONTINUATION_REDESIGN_V2", "1")
    AdxTrendContinuation.reset_dedup_state()
    s = AdxTrendContinuation()
    ctx = _ctx(_df(), backtest_mode=True, bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    first = s.evaluate(ctx)
    second = s.evaluate(ctx)

    assert first is not None
    assert first.signal == "BUY"
    assert second is None


def test_v2_live_intrabar_without_bar_time_is_blocked(monkeypatch):
    monkeypatch.setenv("ADX_TREND_CONTINUATION_REDESIGN_V2", "1")
    AdxTrendContinuation.reset_dedup_state()
    s = AdxTrendContinuation()
    ctx = _ctx(_df(), backtest_mode=False, bar_time=None)

    assert s.evaluate(ctx) is None


def test_v2_live_closed_bar_with_bar_time_can_emit(monkeypatch):
    monkeypatch.setenv("ADX_TREND_CONTINUATION_REDESIGN_V2", "1")
    AdxTrendContinuation.reset_dedup_state()
    s = AdxTrendContinuation()
    bar_time = pd.Timestamp("2026-05-05 12:00", tz="UTC")
    ctx = _ctx(_df(), backtest_mode=False, bar_time=bar_time)

    cand = s.evaluate(ctx)

    assert cand is not None
    assert cand.signal == "BUY"


def test_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    from strategies.daytrade import DaytradeEngine

    engine = DaytradeEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["✅ best"], "xs_momentum", 5.0)
    adx = Candidate("BUY", 60, 1.0, 1.2, ["✅ adx"], "adx_trend_continuation", 4.5)

    monkeypatch.delenv("ADX_TREND_CONTINUATION_REDESIGN_V2", raising=False)
    monkeypatch.delenv("ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, adx], best) == []

    monkeypatch.setenv("ADX_TREND_CONTINUATION_REDESIGN_V2", "1")
    monkeypatch.setenv("ADX_TREND_CONTINUATION_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, adx], best) == [adx]
