"""Integration test: sr_weighted_break minimal signal generation sanity."""
import os
import pandas as pd
import pytest
from strategies.daytrade.sr_weighted_break import SrWeightedBreak


@pytest.fixture
def enable_env():
    os.environ["SR_WEIGHTED_BREAK_ENABLE"] = "1"
    yield
    os.environ.pop("SR_WEIGHTED_BREAK_ENABLE", None)


def test_evaluate_runs_without_error_on_synthetic_data(enable_env):
    """Build minimal synthetic ctx that includes a break-and-retest setup near a heavy level.

    Verify evaluate returns Candidate or None without exception.
    """
    from strategies.context import SignalContext

    idx = pd.date_range("2026-01-01", periods=20, freq="15min", tz="UTC")
    # Setup: SR=110.40, break on bar -8 (close=110.55 > 110.40+margin), retest current at 110.42
    close_series = [110.30] * 10 + [110.55] * 6 + [110.45, 110.43, 110.42, 110.42]
    open_series  = [110.30] * 10 + [110.40] * 6 + [110.50, 110.45, 110.43, 110.41]
    high_series = [c + 0.02 for c in close_series]
    low_series = [o - 0.02 for o in open_series]

    df = pd.DataFrame({
        "Open":  open_series,
        "High":  high_series,
        "Low":   low_series,
        "Close": close_series,
        "atr":   [0.10] * 20,
        "atr7":  [0.10] * 20,
        "adx":   [25.0] * 20,
        "adx_pos": [25.0] * 20,
        "adx_neg": [22.0] * 20,
        "ema9":  [110.40] * 20,
        "ema21": [110.38] * 20,
        "ema50": [110.35] * 20,
        "ema200":[110.30] * 20,
        "macd_hist": [0.001] * 20,
        "bb_pband": [0.5] * 20,
        "bb_upper": [110.60] * 20,
        "bb_mid": [110.45] * 20,
        "bb_lower": [110.30] * 20,
        "bb_width": [0.01] * 20,
        "rsi": [50.0] * 20,
    }, index=idx)

    heavy_level = {
        "price": 110.40,
        "own_touch": 8,
        "d1_touch": 2,
        "w1_touch": 1,
        "round_score": 0.5,
        "magnitude_score": 0.5,
    }

    ctx = SignalContext(
        entry=110.42, open_price=110.41, atr=0.10, atr7=0.10,
        ema9=110.40, ema21=110.38, ema50=110.35, ema200=110.30,
        rsi=50.0, adx=25.0, adx_pos=25.0, adx_neg=22.0,
        macdh=0.001, macdh_prev=0.0,
        bbpb=0.5, bb_upper=110.60, bb_mid=110.45, bb_lower=110.30, bb_width=0.01,
        prev_close=110.43, prev_open=110.45, prev_high=110.45, prev_low=110.41,
        symbol="USDJPY=X", tf="15m", is_jpy=True, pip_mult=100,
        df=df,
        sr_levels=[110.40, 111.00],
        layer3={"sr_weighted_levels": [heavy_level]},
        regime={"regime": "TREND"},
        htf={"agreement": "mixed"},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=12,
    )

    s = SrWeightedBreak()
    result = s.evaluate(ctx)
    # exception 投げないこと
    assert result is None or hasattr(result, "signal")


def test_evaluate_skips_when_env_disabled():
    os.environ.pop("SR_WEIGHTED_BREAK_ENABLE", None)
    class Ctx:
        pass
    ctx = Ctx()
    ctx.symbol = "USDJPY=X"
    s = SrWeightedBreak()
    assert s.evaluate(ctx) is None
