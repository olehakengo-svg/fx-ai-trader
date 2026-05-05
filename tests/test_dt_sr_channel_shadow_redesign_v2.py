from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.dt_sr_channel import DtSrChannelReversal


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    n = 25
    idx = pd.date_range(end="2026-05-05 07:15", periods=n, freq="15min", tz="UTC")
    close = np.full(n, 100.20)
    open_ = np.full(n, 100.18)
    high = np.full(n, 100.25)
    low = np.full(n, 100.15)
    rsi = np.full(n, 50.0)
    macdh = np.full(n, -0.10)
    ema9 = np.full(n, 100.22)
    ema21 = np.full(n, 100.18)

    # Previous closed bar for MACD turn reference.
    close[-3] = 100.10
    open_[-3] = 100.12
    macdh[-3] = -0.10

    close[-2] = 100.00 if closed_signal else 100.20
    open_[-2] = 100.02
    high[-2] = close[-2] + 0.05
    low[-2] = close[-2] - 0.05
    rsi[-2] = 40.0 if closed_signal else 50.0
    macdh[-2] = 0.04 if closed_signal else -0.10

    close[-1] = 100.20 if current_signal else 100.05
    open_[-1] = 100.16
    high[-1] = close[-1] + 0.05
    low[-1] = close[-1] - 0.05
    rsi[-1] = 40.0 if current_signal else 50.0
    macdh[-1] = 0.08 if current_signal else -0.05

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "atr": np.full(n, 0.10),
            "atr7": np.full(n, 0.10),
            "rsi": rsi,
            "macd_hist": macdh,
            "ema9": ema9,
            "ema21": ema21,
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, sr_level: float, backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        rsi=float(row["rsi"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        symbol="USDJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        df=df,
        sr_levels=[sr_level],
        htf={"agreement": "mixed"},
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_current_bar_signal(monkeypatch):
    monkeypatch.delenv("DT_SR_CHANNEL_REDESIGN_V2", raising=False)

    cand = DtSrChannelReversal().evaluate(
        _ctx(_df(closed_signal=False, current_signal=True), sr_level=100.17)
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("DT_SR_CHANNEL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_signal_and_ignores_current_bar(monkeypatch):
    monkeypatch.setenv("DT_SR_CHANNEL_REDESIGN_V2", "1")

    cand = DtSrChannelReversal().evaluate(
        _ctx(_df(closed_signal=True, current_signal=False), sr_level=99.97)
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.sl < 99.97
    assert round(cand.tp, 2) == 100.15
    assert any("closed_bar_time=2026-05-05 07:00:00+00:00" in reason for reason in cand.reasons)
    assert any("MR geometry" in reason for reason in cand.reasons)


def test_v2_rejects_if_closed_bar_has_no_signal_even_when_current_bar_does(monkeypatch):
    monkeypatch.setenv("DT_SR_CHANNEL_REDESIGN_V2", "1")

    cand = DtSrChannelReversal().evaluate(
        _ctx(_df(closed_signal=False, current_signal=True), sr_level=100.17)
    )

    assert cand is None


def test_v2_live_dedups_same_symbol_signal_closed_bar(monkeypatch):
    monkeypatch.setenv("DT_SR_CHANNEL_REDESIGN_V2", "1")
    DtSrChannelReversal._v2_seen_closed_bar_keys.clear()
    strategy = DtSrChannelReversal()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), sr_level=99.97, backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    dt_sr = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="dt_sr_channel_reversal",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("DT_SR_CHANNEL_REDESIGN_V2", "1")
    monkeypatch.delenv("DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, dt_sr], other) == []

    monkeypatch.setenv("DT_SR_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, dt_sr], other) == [dt_sr]
