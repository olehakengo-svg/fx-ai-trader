"""Integration test: sr_weighted_bounce minimal signal generation sanity."""
import os
import pandas as pd
import pytest
from strategies.daytrade.sr_weighted_bounce import SrWeightedBounce


@pytest.fixture
def enable_env():
    os.environ["SR_WEIGHTED_BOUNCE_ENABLE"] = "1"
    yield
    os.environ.pop("SR_WEIGHTED_BOUNCE_ENABLE", None)


def test_evaluate_runs_without_error_on_synthetic_data(enable_env):
    """Build minimal synthetic ctx with weighted level near price, ADX<30, no recent hunt.

    Verify evaluate returns Candidate or None without exception.
    """
    from strategies.context import SignalContext

    idx = pd.date_range("2026-01-01", periods=20, freq="15min", tz="UTC")
    df = pd.DataFrame({
        "Open":  [110.45] * 20,
        "High":  [110.55] * 20,
        "Low":   [110.40] * 20,
        "Close": [110.50] * 20,
        "atr":   [0.10] * 20,
        "atr7":  [0.10] * 20,
        "adx":   [22.0] * 20,
        "adx_pos": [22.0] * 20,
        "adx_neg": [20.0] * 20,
        "ema9":  [110.49] * 20,
        "ema21": [110.48] * 20,
        "ema50": [110.45] * 20,
        "ema200":[110.40] * 20,
        "macd_hist": [0.001] * 20,
        "bb_pband": [0.2] * 20,
        "bb_upper": [110.55] * 20,
        "bb_mid": [110.50] * 20,
        "bb_lower": [110.45] * 20,
        "bb_width": [0.01] * 20,
        "rsi": [50.0] * 20,
    }, index=idx)

    heavy_level = {
        "price": 110.45,
        "own_touch": 8,
        "d1_touch": 2,
        "w1_touch": 1,
        "round_score": 0.5,
        "magnitude_score": 0.5,
    }
    light_level = {
        "price": 109.00,
        "own_touch": 1,
        "d1_touch": 0,
        "w1_touch": 0,
        "round_score": 0.0,
        "magnitude_score": 0.0,
    }

    ctx = SignalContext(
        entry=110.50, open_price=110.45, atr=0.10, atr7=0.10,
        ema9=110.49, ema21=110.48, ema50=110.45, ema200=110.40,
        rsi=50.0, adx=22.0, adx_pos=22.0, adx_neg=20.0,
        macdh=0.001, macdh_prev=0.0,
        bbpb=0.2, bb_upper=110.55, bb_mid=110.50, bb_lower=110.45, bb_width=0.01,
        prev_close=110.50, prev_open=110.45, prev_high=110.55, prev_low=110.40,
        symbol="USDJPY=X", tf="15m", is_jpy=True, pip_mult=100,
        df=df,
        sr_levels=[110.45, 109.00],
        layer3={"sr_weighted_levels": [heavy_level, light_level]},
        regime={"regime": "RANGE"},
        htf={"agreement": "mixed"},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=12,
    )

    s = SrWeightedBounce()
    result = s.evaluate(ctx)
    # 結果は None または Candidate のどちらでも OK (gate logic 通過にあらゆる field が要るため)
    # 重要: exception を投げないこと
    assert result is None or hasattr(result, "signal")


def test_evaluate_skips_when_env_disabled():
    os.environ.pop("SR_WEIGHTED_BOUNCE_ENABLE", None)
    # ctx は最小限で OK (early return が env check で起こる)
    class Ctx:
        pass
    ctx = Ctx()
    ctx.symbol = "USDJPY=X"
    s = SrWeightedBounce()
    assert s.evaluate(ctx) is None
