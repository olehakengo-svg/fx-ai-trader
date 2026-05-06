from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.ma_regime_switch import MaRegimeSwitch


def _ctx(*, bb_width_pct: float, m15_atr_pct: float) -> SignalContext:
    idx = pd.date_range(end="2026-05-05 07:15", periods=4, freq="5min", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": [156.00, 156.02, 156.04, 156.06],
            "High": [156.08, 156.10, 156.12, 156.16],
            "Low": [155.98, 156.00, 156.02, 156.04],
            "Close": [156.02, 156.04, 156.06, 156.12],
        },
        index=idx,
    )
    return SignalContext(
        entry=156.12,
        open_price=156.06,
        atr=0.08,
        atr7=0.08,
        adx=24.0,
        macdh=0.12,
        macdh_prev=0.02,
        bb_width_pct=bb_width_pct,
        symbol="USDJPY=X",
        tf="5m",
        is_jpy=True,
        pip_mult=100,
        df=df,
        htf={
            "m15": {
                "close": 156.10,
                "ema9": 156.11,
                "ema21": 156.06,
                "ema50": 156.00,
                "ema_slope": 0.03,
                "adx": 24.0,
                "atr_pct": m15_atr_pct,
            },
            "m5": {
                "close": 156.12,
                "prev_close": 156.04,
                "ema21": 156.08,
                "bbpb": 0.50,
                "rsi14": 50.0,
                "stoch_k": 50.0,
                "stoch_d": 50.0,
            },
        },
        backtest_mode=True,
        bar_time=idx[-1],
        hour_utc=idx[-1].hour,
    )


def test_v2_default_off_preserves_legacy_1m_bb_width_regime_proxy(monkeypatch):
    monkeypatch.delenv("MA_REGIME_SWITCH_REDESIGN_V2", raising=False)

    cand = MaRegimeSwitch().evaluate(_ctx(bb_width_pct=0.80, m15_atr_pct=20.0))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("MA_REGIME_SWITCH_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_m15_atr_percentile_instead_of_bb_width_proxy(monkeypatch):
    monkeypatch.setenv("MA_REGIME_SWITCH_REDESIGN_V2", "1")

    cand = MaRegimeSwitch().evaluate(_ctx(bb_width_pct=0.50, m15_atr_pct=80.0))

    assert cand is not None
    assert cand.signal == "BUY"
    assert any("MA_REGIME_SWITCH_REDESIGN_V2" in reason for reason in cand.reasons)
    assert any("atr_pct=80" in reason for reason in cand.reasons)


def test_v2_rejects_legacy_high_bb_width_when_m15_atr_is_low(monkeypatch):
    monkeypatch.setenv("MA_REGIME_SWITCH_REDESIGN_V2", "1")

    cand = MaRegimeSwitch().evaluate(_ctx(bb_width_pct=0.80, m15_atr_pct=20.0))

    assert cand is None


def test_v2_engine_registration_is_default_off(monkeypatch):
    monkeypatch.delenv("MA_REGIME_SWITCH_REDESIGN_V2", raising=False)

    assert ScalperEngine().get_strategy("ma_regime_switch") is None

    monkeypatch.setenv("MA_REGIME_SWITCH_REDESIGN_V2", "1")
    assert ScalperEngine().get_strategy("ma_regime_switch") is not None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    regime = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="ma_regime_switch",
        score=4.0,
    )
    engine = ScalperEngine()

    monkeypatch.setenv("MA_REGIME_SWITCH_REDESIGN_V2", "1")
    monkeypatch.delenv("MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, regime], other) == []

    monkeypatch.setenv("MA_REGIME_SWITCH_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, regime], other) == [regime]
