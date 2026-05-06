from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.macdh import MacdhReversal


def _ctx(*, bbpb: float = 0.20, rsi5: float = 44.0) -> SignalContext:
    idx = pd.date_range(end="2026-05-05 15:15", periods=3, freq="15min", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": [1.1010, 1.1008, 1.1002],
            "High": [1.1013, 1.1010, 1.1006],
            "Low": [1.1005, 1.0998, 1.0996],
            "Close": [1.1008, 1.1002, 1.1000],
            "macd_hist": [-0.00010, -0.00020, -0.00005],
        },
        index=idx,
    )
    return SignalContext(
        entry=1.1000,
        open_price=1.1002,
        atr=0.0010,
        atr7=0.0010,
        rsi=45.0,
        rsi5=rsi5,
        stoch_k=35.0,
        stoch_d=30.0,
        adx=18.0,
        macdh=-0.00005,
        macdh_prev=-0.00020,
        macdh_prev2=-0.00010,
        bbpb=bbpb,
        bb_lower=1.0990,
        bb_mid=1.1010,
        bb_upper=1.1030,
        prev_close=1.1002,
        prev_open=1.1008,
        prev_high=1.1010,
        prev_low=1.0998,
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=True,
        bar_time=idx[-1],
        hour_utc=idx[-1].hour,
    )


def test_v2_default_off_preserves_existing_non_tier1_signal(monkeypatch):
    monkeypatch.delenv("MACDH_REDESIGN_V2", raising=False)

    cand = MacdhReversal().evaluate(_ctx())

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.tp, 4) == 1.1015
    assert round(cand.sl, 4) == 1.0990
    assert not any("MACDH_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_requires_tier1_bb_and_rsi_extreme(monkeypatch):
    monkeypatch.setenv("MACDH_REDESIGN_V2", "1")

    assert MacdhReversal().evaluate(_ctx(bbpb=0.20, rsi5=38.0)) is None
    assert MacdhReversal().evaluate(_ctx(bbpb=0.10, rsi5=44.0)) is None


def test_v2_uses_wider_mr_geometry_for_extreme_reversal(monkeypatch):
    monkeypatch.setenv("MACDH_REDESIGN_V2", "1")

    cand = MacdhReversal().evaluate(_ctx(bbpb=0.10, rsi5=38.0))

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.sl, 4) == 1.0985
    assert round(cand.tp, 4) == 1.1030
    assert any("MACDH_REDESIGN_V2" in reason for reason in cand.reasons)


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("SELL", 70, 1.2, 1.0, ["best"], "other", 7.0)
    macdh = Candidate("BUY", 60, 1.0, 1.2, ["macdh"], "macdh_reversal", 4.0)

    monkeypatch.setenv("MACDH_REDESIGN_V2", "1")
    monkeypatch.delenv("MACDH_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, macdh], best) == []

    monkeypatch.setenv("MACDH_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, macdh], best) == [macdh]
