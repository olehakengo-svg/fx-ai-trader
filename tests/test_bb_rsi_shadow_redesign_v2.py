from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.bb_rsi import BBRsiReversion


def _ctx(*, symbol: str = "USDJPY=X", adx: float = 35.0) -> SignalContext:
    idx = pd.date_range(end="2026-05-05 07:15", periods=3, freq="15min", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": [156.10, 156.08, 156.00],
            "High": [156.16, 156.11, 156.07],
            "Low": [156.04, 155.96, 155.92],
            "Close": [156.08, 156.00, 156.04],
            "stoch_k": [25.0, 20.0, 30.0],
            "macd_hist": [0.00, -0.10, 0.20],
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
        adx=adx,
        macdh=0.20,
        macdh_prev=-0.10,
        macdh_prev2=0.00,
        bbpb=0.20,
        bb_lower=155.95,
        bb_mid=156.10,
        bb_upper=156.25,
        prev_close=156.00,
        prev_open=156.08,
        symbol=symbol,
        tf="15m",
        is_jpy="JPY" in symbol,
        pip_mult=100 if "JPY" in symbol else 10000,
        df=df,
        regime={"regime": "RANGE"},
        backtest_mode=True,
        bar_time=idx[-1],
        hour_utc=idx[-1].hour,
    )


def test_v2_default_off_preserves_jpy_high_adx_mr_penalty(monkeypatch):
    monkeypatch.delenv("BB_RSI_REDESIGN_V2", raising=False)

    cand = BBRsiReversion().evaluate(_ctx())

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.confidence == 56
    assert any("MR anti-trend" in reason for reason in cand.reasons)
    assert not any("BB_RSI_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_bypasses_mr_penalty_only_for_jpy_high_adx_tail(monkeypatch):
    monkeypatch.setenv("BB_RSI_REDESIGN_V2", "1")

    cand = BBRsiReversion().evaluate(_ctx())

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.confidence == 76
    assert any("BB_RSI_REDESIGN_V2" in reason for reason in cand.reasons)
    assert not any("conf 76" in reason for reason in cand.reasons)


def test_v2_non_jpy_range_mr_keeps_existing_penalty_path(monkeypatch):
    monkeypatch.setenv("BB_RSI_REDESIGN_V2", "1")
    # 2026-06-08 edge cell redesign: BB_RSI_REVERSION_PAIR_WHITELIST_V1 blocks
    # all non-USDJPY pairs by default (Task 4). This test verifies the v2
    # redesign penalty path which is ORTHOGONAL to the pair whitelist —
    # disable the whitelist so the v2 code path is reachable for EURUSD.
    monkeypatch.setenv("BB_RSI_REVERSION_PAIR_WHITELIST_V1", "0")

    cand = BBRsiReversion().evaluate(_ctx(symbol="EURUSD=X", adx=20.0))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.confidence == 70
    assert not any("BB_RSI_REDESIGN_V2" in reason for reason in cand.reasons)


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    bb_rsi = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="bb_rsi_reversion",
        score=4.0,
    )
    engine = ScalperEngine()

    monkeypatch.setenv("BB_RSI_REDESIGN_V2", "1")
    monkeypatch.delenv("BB_RSI_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, bb_rsi], other) == []

    monkeypatch.setenv("BB_RSI_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, bb_rsi], other) == [bb_rsi]
