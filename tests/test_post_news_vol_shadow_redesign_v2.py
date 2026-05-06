from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.post_news_vol import PostNewsVol


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    n = 40
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.1000)
    close = np.full(n, 1.1001)
    high = np.full(n, 1.1003)
    low = np.full(n, 1.0999)

    spike_idx = -4 if closed_signal else -3
    open_[spike_idx] = 1.1000
    close[spike_idx] = 1.1025
    high[spike_idx] = 1.1030
    low[spike_idx] = 1.0990

    if closed_signal:
        open_[-2] = 1.1026
        close[-2] = 1.1036
        high[-2] = 1.1038
        low[-2] = 1.1024

    if current_signal:
        open_[-1] = 1.1026
        close[-1] = 1.1037
        high[-1] = 1.1039
        low[-1] = 1.1024
    else:
        open_[-1] = 1.1035
        close[-1] = 1.10355
        high[-1] = 1.1037
        low[-1] = 1.1033

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
            "ema21": np.full(n, 1.1005),
            "ema50": np.full(n, 1.1000),
            "ema200": np.full(n, 1.0995),
            "adx": np.full(n, 24.0),
            "adx_pos": np.full(n, 30.0),
            "adx_neg": np.full(n, 18.0),
            "rsi": np.full(n, 55.0),
            "rsi5": np.full(n, 55.0),
            "rsi9": np.full(n, 55.0),
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 45.0),
            "macd_hist": np.full(n, 0.10),
            "bb_upper": np.full(n, 1.1020),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0980),
            "bb_pband": np.full(n, 0.60),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, event: bool = True) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    spike_time = df.index[-4]
    session = {}
    if event:
        session["high_impact_calendar_events"] = [
            {
                "time_utc": spike_time - timedelta(minutes=5),
                "impact": "high",
                "currency": "USD",
                "name": "US high impact release",
            }
        ]
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
        bb_upper=float(row["bb_upper"]),
        bb_mid=float(row["bb_mid"]),
        bb_lower=float(row["bb_lower"]),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        session=session,
        htf={"agreement": "bull"},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=12,
    )


def test_v2_default_off_preserves_legacy_current_bar_signal(monkeypatch):
    monkeypatch.delenv("POST_NEWS_VOL_REDESIGN_V2", raising=False)
    PostNewsVol.reset_dedup_state()

    cand = PostNewsVol().evaluate(_ctx(_df(closed_signal=False, current_signal=True), event=False))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("POST_NEWS_VOL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_current_bar_only_signal(monkeypatch):
    monkeypatch.setenv("POST_NEWS_VOL_REDESIGN_V2", "1")
    PostNewsVol.reset_dedup_state()

    cand = PostNewsVol().evaluate(_ctx(_df(closed_signal=False, current_signal=True), event=True))

    assert cand is None


def test_v2_requires_high_impact_event_window(monkeypatch):
    monkeypatch.setenv("POST_NEWS_VOL_REDESIGN_V2", "1")
    PostNewsVol.reset_dedup_state()

    cand = PostNewsVol().evaluate(_ctx(_df(closed_signal=True, current_signal=False), event=False))

    assert cand is None


def test_v2_uses_event_window_and_closed_signal_bar(monkeypatch):
    monkeypatch.setenv("POST_NEWS_VOL_REDESIGN_V2", "1")
    PostNewsVol.reset_dedup_state()

    cand = PostNewsVol().evaluate(_ctx(_df(closed_signal=True, current_signal=False), event=True))

    assert cand is not None
    assert cand.signal == "BUY"
    assert any("POST_NEWS_VOL_REDESIGN_V2" in reason for reason in cand.reasons)
    assert any("closed-bar follow-through" in reason for reason in cand.reasons)


def test_v2_per_spike_signal_dedup_blocks_repeat(monkeypatch):
    monkeypatch.setenv("POST_NEWS_VOL_REDESIGN_V2", "1")
    PostNewsVol.reset_dedup_state()
    strategy = PostNewsVol()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), event=True)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    pnv = Candidate("BUY", 70, 1.0, 2.0, [], "post_news_vol", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("POST_NEWS_VOL_REDESIGN_V2", "1")
    monkeypatch.delenv("POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, pnv], other) == []

    monkeypatch.setenv("POST_NEWS_VOL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, pnv], other) == [pnv]
