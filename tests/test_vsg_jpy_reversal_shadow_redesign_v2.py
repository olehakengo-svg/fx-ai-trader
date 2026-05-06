from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.vsg_jpy_reversal import VsgJpyReversal


def _ctx_with_surprise(
    symbol: str = "EURJPY=X",
    surprise_factor: float = 4.0,
    n: int = 80,
    atr: float = 0.20,
) -> SignalContext:
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
    quiet_returns = np.random.normal(0, 0.0001, n - 1)
    returns = np.concatenate([quiet_returns, [surprise_factor * 0.001]])
    closes = 160.0 * np.cumprod(1 + returns)
    df = pd.DataFrame(
        {
            "Open": closes - 0.05,
            "High": closes + 0.10,
            "Low": closes - 0.10,
            "Close": closes,
            "Volume": np.full(n, 1000.0),
        },
        index=dates,
    )
    return SignalContext(
        entry=float(closes[-1]),
        open_price=float(closes[-2]),
        atr=atr,
        adx=20.0,
        df=df,
        symbol=symbol,
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        backtest_mode=True,
        bar_time=dates[-1],
    )


def test_v2_default_off_preserves_legacy_rr_geometry(monkeypatch):
    monkeypatch.delenv("VSG_JPY_REVERSAL_REDESIGN_V2", raising=False)
    ctx = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=4.0)

    cand = VsgJpyReversal().evaluate(ctx)

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.sl == pytest.approx(ctx.entry + ctx.atr * 1.0)
    assert cand.tp < ctx.entry
    assert abs(cand.tp - ctx.entry) / abs(ctx.entry - cand.sl) >= VsgJpyReversal.MIN_RR
    assert cand.max_hold_bars is None
    assert not any("VSG_JPY_REVERSAL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_flag_applies_mr_exit_geometry_and_time_exit(monkeypatch):
    monkeypatch.setenv("VSG_JPY_REVERSAL_REDESIGN_V2", "1")
    ctx = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=4.0)

    cand = VsgJpyReversal().evaluate(ctx)

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.sl == pytest.approx(ctx.entry + ctx.atr * 1.8)
    assert cand.tp < ctx.entry
    assert abs(cand.tp - ctx.entry) <= ctx.atr * 0.9 + 1e-9
    assert abs(cand.tp - ctx.entry) / abs(ctx.entry - cand.sl) < VsgJpyReversal.MIN_RR
    assert cand.max_hold_bars == 2
    assert any("VSG_JPY_REVERSAL_REDESIGN_V2 geometry" in reason for reason in cand.reasons)


def test_v2_gbpjpy_pair_threshold_is_relaxed(monkeypatch):
    ctx = _ctx_with_surprise(symbol="GBPJPY=X", surprise_factor=0.24)

    monkeypatch.delenv("VSG_JPY_REVERSAL_REDESIGN_V2", raising=False)
    assert VsgJpyReversal().evaluate(ctx) is None

    monkeypatch.setenv("VSG_JPY_REVERSAL_REDESIGN_V2", "1")
    cand = VsgJpyReversal().evaluate(ctx)

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.max_hold_bars == 4


def test_v2_flag_is_still_pair_gated(monkeypatch):
    monkeypatch.setenv("VSG_JPY_REVERSAL_REDESIGN_V2", "1")
    ctx = _ctx_with_surprise(symbol="USDJPY=X", surprise_factor=4.0)

    assert VsgJpyReversal().evaluate(ctx) is None


def test_existing_shadow_route_preserved_and_v2_promote_flag_is_non_destructive(monkeypatch):
    other = Candidate("SELL", 80, 151.0, 150.0, [], "other", 9.0)
    vsg = Candidate("BUY", 70, 150.0, 151.0, [], "vsg_jpy_reversal", 4.0)
    engine = DaytradeEngine()

    monkeypatch.delenv("VSG_JPY_REVERSAL_REDESIGN_V2", raising=False)
    monkeypatch.delenv("VSG_JPY_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, vsg], other) == [vsg]

    monkeypatch.setenv("VSG_JPY_REVERSAL_REDESIGN_V2", "1")
    monkeypatch.setenv("VSG_JPY_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, vsg], other) == [vsg]
