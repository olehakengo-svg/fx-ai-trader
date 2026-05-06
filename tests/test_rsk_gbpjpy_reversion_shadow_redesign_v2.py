from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategies.context import SignalContext
from strategies.daytrade.rsk_gbpjpy_reversion import RskGbpjpyReversion


def _strong_neg_skew_ctx(n: int = 200, base: float = 180.0) -> SignalContext:
    rng = np.random.default_rng(42)
    rets = np.zeros(n)
    rets[1:n - 2] = rng.normal(0, 0.0001, n - 3)
    rets[-2] = -0.005
    rets[-1] = 0.0002
    closes = base * np.cumprod(1 + rets)
    idx = pd.date_range("2026-05-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": closes - 0.05,
            "High": closes + 0.10,
            "Low": closes - 0.10,
            "Close": closes,
            "Volume": np.full(n, 1000.0),
        },
        index=idx,
    )
    return SignalContext(
        entry=float(closes[-1]),
        open_price=float(closes[-2]),
        atr=0.20,
        adx=20.0,
        df=df,
        symbol="GBPJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        backtest_mode=True,
        bar_time=idx[-1],
    )


def test_v2_default_off_preserves_legacy_rr_geometry(monkeypatch):
    monkeypatch.delenv("RSK_GBPJPY_REVERSION_REDESIGN_V2", raising=False)
    ctx = _strong_neg_skew_ctx()

    cand = RskGbpjpyReversion().evaluate(ctx)

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.sl == pytest.approx(ctx.entry - ctx.atr * 1.0)
    assert cand.tp > ctx.entry
    assert abs(cand.tp - ctx.entry) / abs(ctx.entry - cand.sl) >= RskGbpjpyReversion.MIN_RR
    assert not any("RSK_GBPJPY_REVERSION_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_flag_applies_mr_geometry_and_removes_min_rr_gate(monkeypatch):
    monkeypatch.setenv("RSK_GBPJPY_REVERSION_REDESIGN_V2", "1")
    ctx = _strong_neg_skew_ctx()

    cand = RskGbpjpyReversion().evaluate(ctx)

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.sl == pytest.approx(ctx.entry - ctx.atr * 1.8)
    assert cand.tp > ctx.entry
    assert abs(cand.tp - ctx.entry) <= ctx.atr * 0.8 + 1e-9
    assert abs(cand.tp - ctx.entry) / abs(ctx.entry - cand.sl) < RskGbpjpyReversion.MIN_RR
    assert any("RSK_GBPJPY_REVERSION_REDESIGN_V2 geometry" in reason for reason in cand.reasons)


def test_v2_flag_is_still_pair_gated(monkeypatch):
    monkeypatch.setenv("RSK_GBPJPY_REVERSION_REDESIGN_V2", "1")
    ctx = _strong_neg_skew_ctx()
    ctx.symbol = "USDJPY=X"

    assert RskGbpjpyReversion().evaluate(ctx) is None
