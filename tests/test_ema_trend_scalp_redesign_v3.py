"""ETS_REDESIGN_V3 Pre-reg LOCK gate tests.

Pre-reg LOCK: knowledge-base/wiki/analyses/ema-trend-scalp-redesign-prereg-2026-05-15.md
Gate: mtf_alignment='aligned' AND direction='BUY' AND instrument='GBP_USD'.
strategy 層では deterministic な pair + direction を enforce する。
mtf_alignment は demo_trader.py の mtf_gated routing で post-hoc 適用される。
"""
from __future__ import annotations

from strategies.context import SignalContext
from strategies.scalp.ema_trend_scalp import EmaTrendScalp


def _ctx_buy(symbol: str = "GBPUSD=X") -> SignalContext:
    """BUY シグナルが立つ標準セットアップ (EMA9>EMA21, 陽線, RSI/BB 中庸)."""
    return SignalContext(
        entry=1.2510,
        open_price=1.2508,
        atr=0.0010,
        atr7=0.0010,
        ema9=1.2512,
        ema21=1.2505,
        ema50=1.2500,
        ema200=1.2490,
        adx=22.0,
        adx_pos=28.0,
        adx_neg=14.0,
        rsi=52.0,
        rsi5=52.0,
        rsi9=52.0,
        stoch_k=55.0,
        stoch_d=50.0,
        macdh=0.0002,
        macdh_prev=0.0001,
        bbpb=0.55,
        prev_close=1.2507,
        prev_open=1.2509,
        prev_high=1.2512,
        prev_low=1.2503,
        symbol=symbol,
        tf="5m",
        is_jpy=False,
        pip_mult=10000,
        backtest_mode=True,
    )


def _ctx_sell(symbol: str = "GBPUSD=X") -> SignalContext:
    """SELL シグナルが立つ標準セットアップ (EMA9<EMA21, 陰線)."""
    return SignalContext(
        entry=1.2490,
        open_price=1.2492,
        atr=0.0010,
        atr7=0.0010,
        ema9=1.2488,
        ema21=1.2495,
        ema50=1.2500,
        ema200=1.2510,
        adx=22.0,
        adx_pos=14.0,
        adx_neg=28.0,
        rsi=48.0,
        rsi5=48.0,
        rsi9=48.0,
        stoch_k=45.0,
        stoch_d=50.0,
        macdh=-0.0002,
        macdh_prev=-0.0001,
        bbpb=0.45,
        prev_close=1.2493,
        prev_open=1.2491,
        prev_high=1.2497,
        prev_low=1.2488,
        symbol=symbol,
        tf="5m",
        is_jpy=False,
        pip_mult=10000,
        backtest_mode=True,
    )


def test_v3_default_off_preserves_legacy_buy_for_any_pair(monkeypatch):
    monkeypatch.delenv("ETS_REDESIGN_V3", raising=False)

    for sym in ("GBPUSD=X", "USDJPY=X", "EURUSD=X"):
        ctx = _ctx_buy(sym)
        # USD_JPY/EUR_USD は pip_mult が違うので調整
        if "JPY" in sym:
            ctx.entry = 150.10
            ctx.open_price = 150.08
            ctx.ema9 = 150.12
            ctx.ema21 = 150.05
            ctx.ema50 = 150.00
            ctx.ema200 = 149.90
            ctx.atr = 0.10
            ctx.atr7 = 0.10
            ctx.prev_close = 150.07
            ctx.prev_open = 150.09
            ctx.prev_high = 150.12
            ctx.prev_low = 150.03
            ctx.is_jpy = True
            ctx.pip_mult = 100
        cand = EmaTrendScalp().evaluate(ctx)
        assert cand is not None, f"legacy BUY should fire for {sym}"
        assert cand.signal == "BUY"


def test_v3_default_off_preserves_legacy_sell(monkeypatch):
    monkeypatch.delenv("ETS_REDESIGN_V3", raising=False)
    cand = EmaTrendScalp().evaluate(_ctx_sell("GBPUSD=X"))
    assert cand is not None
    assert cand.signal == "SELL"


def test_v3_on_allows_gbpusd_buy(monkeypatch):
    monkeypatch.setenv("ETS_REDESIGN_V3", "1")
    cand = EmaTrendScalp().evaluate(_ctx_buy("GBPUSD=X"))
    assert cand is not None
    assert cand.signal == "BUY"


def test_v3_on_blocks_non_gbpusd_pair(monkeypatch):
    monkeypatch.setenv("ETS_REDESIGN_V3", "1")
    ctx = _ctx_buy("EURUSD=X")
    cand = EmaTrendScalp().evaluate(ctx)
    assert cand is None


def test_v3_on_blocks_usdjpy(monkeypatch):
    monkeypatch.setenv("ETS_REDESIGN_V3", "1")
    ctx = _ctx_buy("USDJPY=X")
    ctx.entry = 150.10
    ctx.open_price = 150.08
    ctx.ema9 = 150.12
    ctx.ema21 = 150.05
    ctx.ema50 = 150.00
    ctx.ema200 = 149.90
    ctx.atr = 0.10
    ctx.atr7 = 0.10
    ctx.prev_close = 150.07
    ctx.prev_open = 150.09
    ctx.prev_high = 150.12
    ctx.prev_low = 150.03
    ctx.is_jpy = True
    ctx.pip_mult = 100
    cand = EmaTrendScalp().evaluate(ctx)
    assert cand is None


def test_v3_on_blocks_sell_on_allowed_pair(monkeypatch):
    monkeypatch.setenv("ETS_REDESIGN_V3", "1")
    cand = EmaTrendScalp().evaluate(_ctx_sell("GBPUSD=X"))
    assert cand is None


def test_v3_helper_reads_env(monkeypatch):
    monkeypatch.delenv("ETS_REDESIGN_V3", raising=False)
    assert EmaTrendScalp.redesign_v3_enabled() is False
    monkeypatch.setenv("ETS_REDESIGN_V3", "1")
    assert EmaTrendScalp.redesign_v3_enabled() is True
    monkeypatch.setenv("ETS_REDESIGN_V3", "0")
    assert EmaTrendScalp.redesign_v3_enabled() is False
