from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.engulfing_bb import EngulfingBB


def _ctx(df: pd.DataFrame) -> SignalContext:
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
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def _df_current_bar_only_bullish() -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=3, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [156.10, 156.08, 155.99],
            "High": [156.12, 156.09, 156.14],
            "Low": [156.06, 156.00, 155.96],
            "Close": [156.08, 156.01, 156.12],
            "atr": [0.08, 0.08, 0.08],
            "atr7": [0.08, 0.08, 0.08],
            "rsi": [40.0, 38.0, 32.0],
            "rsi5": [40.0, 38.0, 32.0],
            "stoch_k": [30.0, 28.0, 35.0],
            "stoch_d": [32.0, 30.0, 25.0],
            "bb_pband": [0.35, 0.35, 0.10],
        },
        index=idx,
    )


def _df_closed_bar_bullish() -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=3, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [156.10, 155.99, 156.12],
            "High": [156.12, 156.14, 156.13],
            "Low": [156.04, 155.96, 156.08],
            "Close": [156.02, 156.13, 156.10],
            "atr": [0.08, 0.08, 0.08],
            "atr7": [0.08, 0.08, 0.08],
            "rsi": [40.0, 32.0, 45.0],
            "rsi5": [40.0, 32.0, 45.0],
            "stoch_k": [30.0, 35.0, 30.0],
            "stoch_d": [32.0, 25.0, 35.0],
            "bb_pband": [0.35, 0.10, 0.45],
        },
        index=idx,
    )


def test_v2_default_off_preserves_legacy_current_bar_engulfing(monkeypatch):
    monkeypatch.delenv("ENGULFING_BB_REDESIGN_V2", raising=False)

    cand = EngulfingBB().evaluate(_ctx(_df_current_bar_only_bullish()))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("ENGULFING_BB_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_current_bar_only_engulfing_until_bar_closes(monkeypatch):
    monkeypatch.setenv("ENGULFING_BB_REDESIGN_V2", "1")

    cand = EngulfingBB().evaluate(_ctx(_df_current_bar_only_bullish()))

    assert cand is None


def test_v2_uses_closed_signal_bar_and_next_bar_entry_geometry(monkeypatch):
    monkeypatch.setenv("ENGULFING_BB_REDESIGN_V2", "1")

    cand = EngulfingBB().evaluate(_ctx(_df_closed_bar_bullish()))

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.tp, 3) == 156.220
    assert round(cand.sl, 3) == 155.948
    assert any("ENGULFING_BB_REDESIGN_V2" in reason for reason in cand.reasons)
    assert any("closed-bar BB" in reason for reason in cand.reasons)


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    engulfing = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="engulfing_bb",
        score=4.0,
    )
    engine = ScalperEngine()

    monkeypatch.setenv("ENGULFING_BB_REDESIGN_V2", "1")
    monkeypatch.delenv("ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, engulfing], other) == []

    monkeypatch.setenv("ENGULFING_BB_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, engulfing], other) == [engulfing]
