from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.three_bar_reversal import ThreeBarReversal


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True) -> SignalContext:
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
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def _buy_df(*, breakout: bool = False) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=5, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [100.60, 100.50, 100.36, 100.22, 100.14],
            "High": [100.64, 100.52, 100.38, 100.30, 100.24 if breakout else 100.22],
            "Low": [100.44, 100.32, 100.18, 99.96, 100.10],
            "Close": [100.50, 100.36, 100.22, 100.00, 100.32 if breakout else 100.23],
            "atr": [0.10] * 5,
            "atr7": [0.10] * 5,
            "rsi": [50.0, 48.0, 46.0, 44.0, 44.0],
            "rsi5": [50.0, 48.0, 46.0, 44.0, 44.0],
            "stoch_k": [30.0, 28.0, 24.0, 22.0, 35.0],
            "stoch_d": [35.0, 32.0, 30.0, 28.0, 25.0],
            "bb_pband": [0.50, 0.45, 0.40, 0.36, 0.38],
        },
        index=idx,
    )


def _sell_df() -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=5, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [100.00, 100.10, 100.24, 100.38, 100.46],
            "High": [100.16, 100.28, 100.42, 100.64, 100.50],
            "Low": [99.96, 100.08, 100.22, 100.30, 100.34],
            "Close": [100.10, 100.24, 100.38, 100.60, 100.36],
            "atr": [0.10] * 5,
            "atr7": [0.10] * 5,
            "rsi": [50.0, 52.0, 54.0, 56.0, 56.0],
            "rsi5": [50.0, 52.0, 54.0, 56.0, 56.0],
            "stoch_k": [70.0, 72.0, 76.0, 78.0, 65.0],
            "stoch_d": [65.0, 68.0, 70.0, 72.0, 75.0],
            "bb_pband": [0.50, 0.55, 0.60, 0.64, 0.62],
        },
        index=idx,
    )


def test_v2_default_off_preserves_legacy_breakout_requirement(monkeypatch):
    monkeypatch.delenv("THREE_BAR_REVERSAL_REDESIGN_V2", raising=False)

    cand = ThreeBarReversal().evaluate(_ctx(_buy_df(breakout=False)))

    assert cand is None


def test_legacy_still_fires_when_default_off_and_breakout_present(monkeypatch):
    monkeypatch.delenv("THREE_BAR_REVERSAL_REDESIGN_V2", raising=False)
    df = _buy_df(breakout=True)
    df.loc[df.index[-1], "bb_pband"] = 0.34
    df.loc[df.index[-1], "rsi5"] = 41.0

    cand = ThreeBarReversal().evaluate(_ctx(df))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("THREE_BAR_REVERSAL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_buy_uses_prev_open_reclaim_instead_of_prev_high_breakout(monkeypatch):
    monkeypatch.setenv("THREE_BAR_REVERSAL_REDESIGN_V2", "1")

    cand = ThreeBarReversal().evaluate(_ctx(_buy_df(breakout=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.tp, 3) == 100.380
    assert round(cand.sl, 3) == 99.945
    assert any("THREE_BAR_REVERSAL_REDESIGN_V2" in reason for reason in cand.reasons)
    assert any("前足Open100.220回復" in reason for reason in cand.reasons)


def test_v2_sell_uses_prev_open_break_instead_of_prev_low_breakout(monkeypatch):
    monkeypatch.setenv("THREE_BAR_REVERSAL_REDESIGN_V2", "1")

    cand = ThreeBarReversal().evaluate(_ctx(_sell_df()))

    assert cand is not None
    assert cand.signal == "SELL"
    assert round(cand.tp, 3) == 100.210
    assert round(cand.sl, 3) == 100.655
    assert any("前足Open100.380割れ" in reason for reason in cand.reasons)


def test_v2_live_dedups_same_symbol_bar_signal(monkeypatch):
    monkeypatch.setenv("THREE_BAR_REVERSAL_REDESIGN_V2", "1")
    ThreeBarReversal._v2_seen_bar_keys.clear()
    strategy = ThreeBarReversal()
    ctx = _ctx(_buy_df(breakout=False), backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    three_bar = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="three_bar_reversal",
        score=4.0,
    )
    engine = ScalperEngine()

    monkeypatch.setenv("THREE_BAR_REVERSAL_REDESIGN_V2", "1")
    monkeypatch.delenv("THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, three_bar], other) == []

    monkeypatch.setenv("THREE_BAR_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, three_bar], other) == [three_bar]
