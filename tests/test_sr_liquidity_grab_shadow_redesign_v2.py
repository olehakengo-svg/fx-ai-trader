from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.sr_liquidity_grab import SrLiquidityGrab

LEVEL = 1.1010


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row.get("atr", 0.0010)),
        adx=float(row.get("adx", 20.0)),
        sr_levels=[LEVEL, 1.0940],
        df=df,
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def _legacy_df(*, current_signal: bool) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=5, freq="15min", tz="UTC")
    quiet = [
        {"Open": 1.1008, "High": 1.1011, "Low": 1.1006, "Close": 1.1009},
        {"Open": 1.1009, "High": 1.1011, "Low": 1.1007, "Close": 1.1008},
        {"Open": 1.1008, "High": 1.1010, "Low": 1.1005, "Close": 1.1007},
    ]
    hunt = {"Open": 1.1005, "High": 1.1035, "Low": 1.1000, "Close": 1.1002}
    if current_signal:
        current = {"Open": 1.1012, "High": 1.1013, "Low": 1.1004, "Close": 1.1006}
    else:
        current = {"Open": 1.1004, "High": 1.1013, "Low": 1.1003, "Close": 1.1006}
    df = pd.DataFrame(quiet[:3] + [hunt, current], index=idx)
    df["atr"] = 0.0010
    df["adx"] = 20.0
    return df


def _v2_df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=6, freq="15min", tz="UTC")
    quiet = [
        {"Open": 1.1008, "High": 1.1011, "Low": 1.1006, "Close": 1.1009},
        {"Open": 1.1009, "High": 1.1011, "Low": 1.1007, "Close": 1.1008},
        {"Open": 1.1008, "High": 1.1010, "Low": 1.1005, "Close": 1.1007},
    ]
    hunt = {"Open": 1.1005, "High": 1.1035, "Low": 1.1000, "Close": 1.1002}
    if closed_signal:
        signal = {"Open": 1.1012, "High": 1.1013, "Low": 1.1004, "Close": 1.1006}
    else:
        signal = {"Open": 1.1004, "High": 1.1013, "Low": 1.1003, "Close": 1.1006}
    if current_signal:
        current = {"Open": 1.1012, "High": 1.1013, "Low": 1.1004, "Close": 1.1006}
    else:
        current = {"Open": 1.1004, "High": 1.1013, "Low": 1.1003, "Close": 1.1006}
    df = pd.DataFrame(quiet + [hunt, signal, current], index=idx)
    df["atr"] = 0.0010
    df["adx"] = 20.0
    return df


def test_v2_default_off_preserves_current_bar_reversal(monkeypatch):
    monkeypatch.delenv("SR_LIQUIDITY_GRAB_REDESIGN_V2", raising=False)

    cand = SrLiquidityGrab().evaluate(_ctx(_legacy_df(current_signal=True)))

    assert cand is not None
    assert cand.signal == "SELL"
    assert not any("SR_LIQUIDITY_GRAB_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_signal_and_ignores_current_bar(monkeypatch):
    monkeypatch.setenv("SR_LIQUIDITY_GRAB_REDESIGN_V2", "1")

    cand = SrLiquidityGrab().evaluate(
        _ctx(_v2_df(closed_signal=True, current_signal=False))
    )

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.sl > 1.1035
    assert cand.tp < 1.1006
    assert any("closed_bar_time=2026-05-05 07:00:00+00:00" in reason for reason in cand.reasons)


def test_v2_rejects_if_closed_bar_has_no_signal_even_when_current_bar_does(monkeypatch):
    monkeypatch.setenv("SR_LIQUIDITY_GRAB_REDESIGN_V2", "1")

    cand = SrLiquidityGrab().evaluate(
        _ctx(_v2_df(closed_signal=False, current_signal=True))
    )

    assert cand is None


def test_v2_live_dedups_same_symbol_signal_closed_bar(monkeypatch):
    monkeypatch.setenv("SR_LIQUIDITY_GRAB_REDESIGN_V2", "1")
    SrLiquidityGrab._v2_seen_closed_bar_keys.clear()
    strategy = SrLiquidityGrab()
    ctx = _ctx(_v2_df(closed_signal=True, current_signal=False), backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="BUY", confidence=80, sl=1.0, tp=2.0, reasons=[], entry_type="other", score=9.0)
    sr_liq = Candidate(
        signal="SELL",
        confidence=70,
        sl=2.0,
        tp=1.0,
        reasons=[],
        entry_type="sr_liquidity_grab",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("SR_LIQUIDITY_GRAB_REDESIGN_V2", "1")
    monkeypatch.delenv("SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, sr_liq], other) == []

    monkeypatch.setenv("SR_LIQUIDITY_GRAB_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, sr_liq], other) == [sr_liq]
