from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.sr_anti_hunt_bounce import SrAntiHuntBounce


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    n = 8
    idx = pd.date_range(end="2026-05-05 07:15", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.1000)
    close = np.full(n, 1.1002)
    high = np.full(n, 1.1003)
    low = np.full(n, 1.0999)
    bbpb = np.full(n, 0.5)

    open_[-2] = 1.1000 if closed_signal else 1.1003
    close[-2] = 1.1002
    high[-2] = 1.1003
    low[-2] = 1.0999
    bbpb[-2] = 0.20 if closed_signal else 0.50

    open_[-1] = 1.1000 if current_signal else 1.1003
    close[-1] = 1.10025
    high[-1] = 1.10035
    low[-1] = 1.09995
    bbpb[-1] = 0.80

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "adx": np.full(n, 20.0),
            "bb_pband": bbpb,
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        adx=float(row["adx"]),
        bbpb=float(row["bb_pband"]),
        sr_levels=[1.1000, 1.1110],
        df=df,
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_current_bar_reversal(monkeypatch):
    monkeypatch.delenv("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2", raising=False)

    cand = SrAntiHuntBounce().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_signal_and_ignores_current_bar(monkeypatch):
    monkeypatch.setenv("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2", "1")

    cand = SrAntiHuntBounce().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.sl < 1.1000
    assert cand.tp > cand.sl
    assert any("closed_bar_time=2026-05-05 07:00:00+00:00" in reason for reason in cand.reasons)
    assert any("closed BB%B=0.20" in reason for reason in cand.reasons)


def test_v2_rejects_if_closed_bar_has_no_signal_even_when_current_bar_does(monkeypatch):
    monkeypatch.setenv("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2", "1")

    cand = SrAntiHuntBounce().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_live_dedups_same_symbol_signal_closed_bar(monkeypatch):
    monkeypatch.setenv("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2", "1")
    SrAntiHuntBounce._v2_seen_closed_bar_keys.clear()
    strategy = SrAntiHuntBounce()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    sr_anti_hunt = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="sr_anti_hunt_bounce",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2", "1")
    monkeypatch.delenv("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, sr_anti_hunt], other) == []

    monkeypatch.setenv("SR_ANTI_HUNT_BOUNCE_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, sr_anti_hunt], other) == [sr_anti_hunt]
