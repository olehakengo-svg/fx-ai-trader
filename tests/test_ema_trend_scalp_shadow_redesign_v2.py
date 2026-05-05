from __future__ import annotations

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.ema_trend_scalp import EmaTrendScalp


def _ctx(*, adx: float = 30.0) -> SignalContext:
    return SignalContext(
        entry=1.1010,
        open_price=1.1008,
        atr=0.0010,
        atr7=0.0010,
        ema9=1.1012,
        ema21=1.1005,
        ema50=1.1000,
        ema200=1.0990,
        adx=adx,
        adx_pos=32.0,
        adx_neg=14.0,
        rsi=52.0,
        rsi5=52.0,
        rsi9=52.0,
        stoch_k=55.0,
        stoch_d=50.0,
        macdh=0.0002,
        macdh_prev=0.0001,
        bbpb=0.55,
        prev_close=1.1007,
        prev_open=1.1009,
        prev_high=1.1012,
        prev_low=1.1003,
        symbol="GBPJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        backtest_mode=True,
    )


def test_v2_default_off_preserves_strong_adx_signal_and_bonus(monkeypatch):
    monkeypatch.delenv("EMA_TREND_SCALP_REDESIGN_V2", raising=False)

    cand = EmaTrendScalp().evaluate(_ctx(adx=35.0))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.score >= 3.5
    assert any("ADX=35.0>=30" in reason for reason in cand.reasons)
    assert not any("EMA_TREND_SCALP_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_adx_above_moderate_trend_gate(monkeypatch):
    monkeypatch.setenv("EMA_TREND_SCALP_REDESIGN_V2", "1")

    cand = EmaTrendScalp().evaluate(_ctx(adx=31.1))

    assert cand is None


def test_v2_removes_adx_strength_bonus_inside_gate(monkeypatch):
    monkeypatch.setenv("EMA_TREND_SCALP_REDESIGN_V2", "1")

    cand = EmaTrendScalp().evaluate(_ctx(adx=30.5))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.score == 4.5
    assert not any("ADX=30.5>=30" in reason for reason in cand.reasons)
    assert any("EMA_TREND_SCALP_REDESIGN_V2 moderate ADX gate" in reason for reason in cand.reasons)


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("SELL", 70, 1.2, 1.0, ["best"], "other", 7.0)
    ema = Candidate("BUY", 65, 1.0, 1.2, ["ema"], "ema_trend_scalp", 4.0)

    monkeypatch.setenv("EMA_TREND_SCALP_REDESIGN_V2", "1")
    monkeypatch.delenv("EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, ema], best) == []

    monkeypatch.setenv("EMA_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, ema], best) == [ema]
