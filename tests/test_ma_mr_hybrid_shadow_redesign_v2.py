from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.ma_mr_hybrid import MaMrHybrid


def _ctx(*, m15_close: float = 156.00, m15_ema21: float = 156.00) -> SignalContext:
    idx = pd.date_range(end="2026-05-05 07:15", periods=3, freq="15min", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": [156.10, 156.08, 156.00],
            "High": [156.16, 156.11, 156.07],
            "Low": [156.04, 155.96, 155.92],
            "Close": [156.08, 156.00, 156.04],
        },
        index=idx,
    )
    return SignalContext(
        entry=156.04,
        open_price=156.00,
        atr=0.08,
        atr7=0.08,
        rsi=35.0,
        rsi5=35.0,
        stoch_k=30.0,
        stoch_d=25.0,
        adx=20.0,
        macdh=0.10,
        macdh_prev=-0.05,
        macdh_prev2=-0.10,
        bbpb=0.20,
        prev_close=156.00,
        prev_open=156.08,
        symbol="USDJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        df=df,
        htf={
            "m15": {"close": m15_close, "ema21": m15_ema21},
            "m5": {
                "bbpb": 0.20,
                "rsi14": 35.0,
                "stoch_k": 30.0,
                "stoch_d": 25.0,
            },
        },
        backtest_mode=True,
        bar_time=idx[-1],
        hour_utc=idx[-1].hour,
    )


def test_v2_default_off_preserves_m15_bias_hard_gate(monkeypatch):
    monkeypatch.delenv("MA_MR_HYBRID_REDESIGN_V2", raising=False)

    cand = MaMrHybrid().evaluate(_ctx(m15_close=156.00, m15_ema21=156.00))

    assert cand is None


def test_v2_removes_m15_bias_from_entry_gate(monkeypatch):
    monkeypatch.setenv("MA_MR_HYBRID_REDESIGN_V2", "1")

    cand = MaMrHybrid().evaluate(_ctx(m15_close=156.00, m15_ema21=156.00))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.entry_type == "ma_mr_hybrid"
    assert any("MA_MR_HYBRID_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_keeps_m15_bias_as_soft_score_feature(monkeypatch):
    monkeypatch.setenv("MA_MR_HYBRID_REDESIGN_V2", "1")

    neutral = MaMrHybrid().evaluate(_ctx(m15_close=156.00, m15_ema21=156.00))
    aligned = MaMrHybrid().evaluate(_ctx(m15_close=156.20, m15_ema21=156.00))

    assert neutral is not None
    assert aligned is not None
    assert aligned.score > neutral.score
    assert aligned.confidence >= neutral.confidence


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    ma_mr = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="ma_mr_hybrid",
        score=4.0,
    )
    engine = ScalperEngine()

    monkeypatch.setenv("MA_MR_HYBRID_REDESIGN_V2", "1")
    monkeypatch.delenv("MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, ma_mr], other) == []

    monkeypatch.setenv("MA_MR_HYBRID_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, ma_mr], other) == [ma_mr]
