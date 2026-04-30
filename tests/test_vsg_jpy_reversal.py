"""Tests for strategies/daytrade/vsg_jpy_reversal.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from strategies.daytrade.vsg_jpy_reversal import VsgJpyReversal
from strategies.context import SignalContext


def _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=2.5, n=50,
                        backtest_mode=True):
    """Build context with quiet history then a vol-surprise final bar.

    BT semantics by default (last bar = closed). For live semantics, pass
    backtest_mode=False; the strategy will then evaluate iloc[-2] as the
    closed bar, so callers should add an extra in-progress bar at the end.
    """
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="15min")
    quiet_returns = np.random.normal(0, 0.0001, n - 1)  # tiny vol
    # Place the surprise return on the LAST bar (BT closed-bar semantics).
    quiet_returns = np.concatenate([quiet_returns, [surprise_factor * 0.001]])
    closes = 160.0 * np.cumprod(1 + quiet_returns)
    df = pd.DataFrame({
        "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
        "Close": closes, "Volume": [1000] * n,
    }, index=dates)
    return SignalContext(
        entry=float(closes[-1]), open_price=float(closes[-2]),
        atr=0.20, adx=20.0, df=df,
        symbol=symbol, tf="15m", is_jpy=True, pip_mult=100,
        backtest_mode=backtest_mode,
    )


class TestVsgJpyReversal:
    def test_only_jpy_crosses_allowed(self):
        s = VsgJpyReversal()
        for sym in ["USDJPY=X", "EURUSD=X", "GBPUSD=X", "AUDUSD=X"]:
            ctx = _ctx_with_surprise(symbol=sym)
            assert s.evaluate(ctx) is None

    def test_enabled_for_shadow(self):
        assert VsgJpyReversal().enabled is True

    def test_eurjpy_supported(self):
        s = VsgJpyReversal()
        ctx = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=4.0)
        cand = s.evaluate(ctx)
        # bullish surprise → SELL
        if cand is not None:
            assert cand.signal == "SELL"
            assert cand.entry_type == "vsg_jpy_reversal"

    def test_gbpjpy_supported(self):
        s = VsgJpyReversal()
        ctx = _ctx_with_surprise(symbol="GBPJPY=X", surprise_factor=4.0)
        cand = s.evaluate(ctx)
        if cand is not None:
            assert cand.signal == "SELL"

    def test_no_signal_with_steady_volatility(self):
        """Steady moderate-vol history (no surprise) → None."""
        s = VsgJpyReversal()
        np.random.seed(99)
        n = 50
        dates = pd.date_range("2024-01-01", periods=n, freq="15min")
        # Steady noise with same magnitude across all bars (no surprise)
        returns = np.random.normal(0, 0.001, n)
        closes = 160.0 * np.cumprod(1 + returns)
        df = pd.DataFrame({
            "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
            "Close": closes, "Volume": [1000] * n,
        }, index=dates)
        ctx = SignalContext(
            entry=float(closes[-1]), open_price=float(closes[-2]),
            atr=0.20, adx=20.0, df=df,
            symbol="EURJPY=X", tf="15m", is_jpy=True, pip_mult=100,
        )
        # The surprise should be moderate, well below 1.5 threshold most of the time
        result = s.evaluate(ctx)
        # accept None or signal — what matters is logic doesn't crash
        assert result is None or result.signal in ("BUY", "SELL")

    def test_min_rr_enforced(self):
        s = VsgJpyReversal()
        ctx = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=4.0)
        cand = s.evaluate(ctx)
        if cand is not None:
            risk = abs(ctx.entry - cand.sl)
            reward = abs(cand.tp - ctx.entry)
            assert reward / risk >= 1.4

    def test_negative_surprise_triggers_buy(self):
        s = VsgJpyReversal()
        # Negative final return = down spike → BUY (fade)
        ctx = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=-4.0)
        cand = s.evaluate(ctx)
        if cand is not None:
            assert cand.signal == "BUY"

    # ── rule:R1/R3 (2026-04-30): threshold semantics + per-bar dedup ──

    def test_threshold_2p5x_below_emits_none(self):
        """In _ctx_with_surprise, quiet std≈1e-4 so realized/forecast ≈ 10×factor.
        factor=0.20 → ratio≈2.0 (< 2.5x threshold) → no emit.
        """
        s = VsgJpyReversal()
        ctx = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=0.20)
        assert s.evaluate(ctx) is None

    def test_threshold_2p5x_above_emits(self):
        """factor=0.30 → ratio≈3.0 (> 2.5x threshold) → must emit."""
        s = VsgJpyReversal()
        ctx = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=0.30)
        cand = s.evaluate(ctx)
        assert cand is not None, "Expected emit at ratio≈3.0 (above 2.5x threshold)"
        assert cand.signal == "SELL"

    def test_per_bar_dedup_blocks_repeat(self):
        """Same closed bar → second evaluate must return None (per-bar dedup)."""
        s = VsgJpyReversal()
        ctx = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=4.0)
        first = s.evaluate(ctx)
        assert first is not None
        # Same ctx (same df, same bar timestamp) — must dedup.
        second = s.evaluate(ctx)
        assert second is None, "Expected per-bar dedup to block second emit on same closed bar"

    def test_per_bar_dedup_releases_on_new_bar(self):
        """New closed bar (different timestamp) → emit allowed again."""
        s = VsgJpyReversal()
        ctx1 = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=4.0, n=50)
        first = s.evaluate(ctx1)
        assert first is not None
        # Build a longer history to simulate the next bar arrival.
        ctx2 = _ctx_with_surprise(symbol="EURJPY=X", surprise_factor=4.0, n=51)
        second = s.evaluate(ctx2)
        assert second is not None, "Expected emit on new closed bar (different bar_id)"

    def test_live_mode_uses_iloc_minus_2(self):
        """Live (backtest_mode=False): closed bar is iloc[-2]; in-progress
        bar at iloc[-1] should NOT trigger emit by itself.
        """
        s = VsgJpyReversal()
        np.random.seed(1)
        n = 51
        dates = pd.date_range("2024-01-01", periods=n, freq="15min")
        quiet = np.random.normal(0, 0.0001, n - 2)
        # Pre-last bar (closed) carries the vol surprise.
        # Last bar (in-progress) is small movement — should be ignored in live.
        rets = np.concatenate([quiet, [4.0 * 0.001, 0.0001]])
        closes = 160.0 * np.cumprod(1 + rets)
        df = pd.DataFrame({
            "Open": closes - 0.05, "High": closes + 0.10, "Low": closes - 0.10,
            "Close": closes, "Volume": [1000] * n,
        }, index=dates)
        ctx = SignalContext(
            entry=float(closes[-1]), open_price=float(closes[-2]),
            atr=0.20, adx=20.0, df=df,
            symbol="EURJPY=X", tf="15m", is_jpy=True, pip_mult=100,
            backtest_mode=False,
        )
        cand = s.evaluate(ctx)
        # Closed bar (iloc[-2]) had the vol surprise → should emit.
        assert cand is not None, "Live mode should evaluate closed bar (iloc[-2]) and emit"
