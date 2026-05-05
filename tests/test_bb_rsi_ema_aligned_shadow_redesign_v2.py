from __future__ import annotations

import pytest
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.bb_rsi import BBRsiReversion
from strategies.scalp.bb_rsi_ema_aligned import BbRsiEmaAligned


def _ctx() -> SignalContext:
    idx = pd.date_range(end="2026-05-05 07:15", periods=4, freq="15min", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": [156.12, 156.10, 156.08, 156.00],
            "High": [156.18, 156.16, 156.11, 156.07],
            "Low": [156.06, 156.04, 155.96, 155.92],
            "Close": [156.10, 156.08, 156.00, 156.04],
            "stoch_k": [35.0, 25.0, 20.0, 30.0],
            "macd_hist": [0.00, 0.00, -0.10, 0.20],
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
        adx=35.0,
        macdh=0.20,
        macdh_prev=-0.10,
        macdh_prev2=0.00,
        bbpb=0.20,
        bb_lower=155.95,
        bb_mid=156.10,
        bb_upper=156.25,
        prev_close=156.00,
        prev_open=156.08,
        prev_high=156.11,
        prev_low=155.96,
        symbol="USDJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        df=df,
        regime={"regime": "RANGE"},
        backtest_mode=True,
        bar_time=idx[-1],
        hour_utc=idx[-1].hour,
    )


def test_v2_default_off_preserves_parent_geometry(monkeypatch):
    monkeypatch.delenv("BB_RSI_EMA_ALIGNED_REDESIGN_V2", raising=False)
    monkeypatch.delenv("BB_RSI_REDESIGN_V2", raising=False)
    ctx = _ctx()

    parent = BBRsiReversion().evaluate(ctx)
    aligned = BbRsiEmaAligned().evaluate(ctx)

    assert parent is not None
    assert aligned is not None
    assert aligned.entry_type == "bb_rsi_ema_aligned"
    assert aligned.signal == parent.signal == "BUY"
    assert aligned.sl == pytest.approx(parent.sl)
    assert aligned.tp == pytest.approx(parent.tp)
    assert not any("BB_RSI_EMA_ALIGNED_REDESIGN_V2" in reason for reason in aligned.reasons)


def test_v2_flag_applies_hybrid_rr3_geometry(monkeypatch):
    monkeypatch.setenv("BB_RSI_EMA_ALIGNED_REDESIGN_V2", "1")
    monkeypatch.delenv("BB_RSI_REDESIGN_V2", raising=False)
    ctx = _ctx()

    parent = BBRsiReversion().evaluate(ctx)
    aligned = BbRsiEmaAligned().evaluate(ctx)

    assert parent is not None
    assert aligned is not None
    sl_dist = abs(ctx.entry - ctx.bb_lower) + ctx.atr7 * 0.3
    assert aligned.sl == pytest.approx(ctx.entry - sl_dist)
    assert aligned.tp == pytest.approx(ctx.entry + sl_dist * 3.0)
    assert aligned.tp > parent.tp
    assert any("BB_RSI_EMA_ALIGNED_REDESIGN_V2" in reason for reason in aligned.reasons)


def test_v2_shadow_promote_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    aligned = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="bb_rsi_ema_aligned",
        score=4.0,
    )
    engine = ScalperEngine()

    monkeypatch.setenv("BB_RSI_EMA_ALIGNED_REDESIGN_V2", "1")
    monkeypatch.delenv("BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, aligned], other) == []

    monkeypatch.setenv("BB_RSI_EMA_ALIGNED_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, aligned], other) == [aligned]
