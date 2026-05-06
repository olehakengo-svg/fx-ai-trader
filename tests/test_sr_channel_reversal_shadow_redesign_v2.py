from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.sr_channel_reversal import SrChannelReversal


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    n = 25
    idx = pd.date_range(end="2026-05-05 07:15", periods=n, freq="15min", tz="UTC")
    close = np.full(n, 100.20)
    open_ = np.full(n, 100.18)
    high = np.full(n, 100.25)
    low = np.full(n, 100.15)
    rsi = np.full(n, 50.0)
    rsi5 = np.full(n, 50.0)
    stoch_k = np.full(n, 45.0)
    stoch_d = np.full(n, 50.0)
    macdh = np.full(n, -0.10)

    close[-3] = 100.10
    open_[-3] = 100.12
    stoch_k[-3] = 20.0
    stoch_d[-3] = 30.0
    macdh[-3] = -0.10

    close[-2] = 100.00 if closed_signal else 100.20
    open_[-2] = 99.98
    high[-2] = close[-2] + 0.05
    low[-2] = close[-2] - 0.05
    rsi[-2] = 40.0 if closed_signal else 50.0
    rsi5[-2] = 40.0 if closed_signal else 50.0
    stoch_k[-2] = 35.0 if closed_signal else 45.0
    stoch_d[-2] = 25.0 if closed_signal else 50.0
    macdh[-2] = 0.04 if closed_signal else -0.10

    close[-1] = 100.20 if current_signal else 100.05
    open_[-1] = 100.16
    high[-1] = close[-1] + 0.05
    low[-1] = close[-1] - 0.05
    rsi[-1] = 40.0 if current_signal else 50.0
    rsi5[-1] = 40.0 if current_signal else 50.0
    stoch_k[-1] = 35.0 if current_signal else 45.0
    stoch_d[-1] = 25.0 if current_signal else 50.0
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
            "rsi5": rsi5,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "macd_hist": macdh,
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
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        symbol="USDJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        df=df,
        sr_levels=[sr_level],
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_current_bar_signal(monkeypatch):
    monkeypatch.delenv("SR_CHANNEL_REVERSAL_REDESIGN_V2", raising=False)

    cand = SrChannelReversal().evaluate(
        _ctx(_df(closed_signal=False, current_signal=True), sr_level=100.18)
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("SR_CHANNEL_REVERSAL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_signal_and_ignores_current_bar(monkeypatch):
    monkeypatch.setenv("SR_CHANNEL_REVERSAL_REDESIGN_V2", "1")

    cand = SrChannelReversal().evaluate(
        _ctx(_df(closed_signal=True, current_signal=False), sr_level=99.98)
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.sl, 2) == 99.85
    assert round(cand.tp, 2) == 100.14
    assert any("closed_bar_time=2026-05-05 07:00:00+00:00" in reason for reason in cand.reasons)
    assert any("MR geometry" in reason for reason in cand.reasons)


def test_v2_rejects_if_closed_bar_has_no_signal_even_when_current_bar_does(monkeypatch):
    monkeypatch.setenv("SR_CHANNEL_REVERSAL_REDESIGN_V2", "1")

    cand = SrChannelReversal().evaluate(
        _ctx(_df(closed_signal=False, current_signal=True), sr_level=100.18)
    )

    assert cand is None


def test_v2_live_dedups_same_symbol_signal_closed_bar(monkeypatch):
    monkeypatch.setenv("SR_CHANNEL_REVERSAL_REDESIGN_V2", "1")
    SrChannelReversal._v2_seen_closed_bar_keys.clear()
    strategy = SrChannelReversal()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), sr_level=99.98, backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    sr = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="sr_channel_reversal",
        score=4.0,
    )
    engine = ScalperEngine()

    monkeypatch.setenv("SR_CHANNEL_REVERSAL_REDESIGN_V2", "1")
    monkeypatch.delenv("SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, sr], other) == []

    monkeypatch.setenv("SR_CHANNEL_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, sr], other) == [sr]
