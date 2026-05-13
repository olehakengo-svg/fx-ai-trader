"""Unit tests for sr_weighted_bounce strategy."""
import os
import pandas as pd
from strategies.daytrade.sr_weighted_bounce import SrWeightedBounce


def _enable():
    os.environ["SR_WEIGHTED_BOUNCE_ENABLE"] = "1"


def _disable():
    os.environ.pop("SR_WEIGHTED_BOUNCE_ENABLE", None)


def test_composite_weight_formula():
    s = SrWeightedBounce()
    meta = {
        "price": 110.50,
        "own_touch": 3,
        "d1_touch": 2,
        "w1_touch": 1,
        "round_score": 0.5,
        "magnitude_score": 0.6,
    }
    expected = 1.0*3 + 3.0*2 + 5.0*1 + 2.0*0.5 + 1.5*0.6  # = 15.9
    assert abs(s._compute_composite_weight(meta) - expected) < 1e-9


def test_composite_weight_with_touches_alias():
    s = SrWeightedBounce()
    # find_sr_levels_weighted 互換 (touches キー)
    meta = {"price": 110.53, "touches": 4}
    expected = 1.0 * 4
    assert abs(s._compute_composite_weight(meta) - expected) < 1e-9


def test_select_heavy_level_gate_pass():
    s = SrWeightedBounce()
    # 4 levels: 1 heavy in top-30%, 1 below absolute threshold,
    # 1 outside proximity, 1 below percentile
    levels = [
        {"price": 110.50, "own_touch": 10, "d1_touch": 3, "w1_touch": 1,
         "round_score": 0.5, "magnitude_score": 0.5},
        {"price": 110.40, "own_touch": 2, "d1_touch": 0, "w1_touch": 0,
         "round_score": 0.0, "magnitude_score": 0.0},
        {"price": 115.00, "own_touch": 8, "d1_touch": 2, "w1_touch": 1,  # too far
         "round_score": 0.0, "magnitude_score": 0.5},
        {"price": 110.45, "own_touch": 3, "d1_touch": 0, "w1_touch": 0,
         "round_score": 0.0, "magnitude_score": 0.0},
    ]
    # ctx mock minimal
    class Ctx: pass
    ctx = Ctx()
    out = s._select_heavy_level(ctx, levels, signal_price=110.52, atr=0.1)
    assert out is not None
    assert out["price"] == 110.50


def test_select_heavy_level_gate_reject_below_abs():
    s = SrWeightedBounce()
    # All levels below K_ABS_THRESHOLD=3.0
    levels = [
        {"price": 110.50, "own_touch": 1, "round_score": 0.0, "magnitude_score": 0.0},
        {"price": 110.45, "own_touch": 2, "round_score": 0.0, "magnitude_score": 0.0},
    ]
    class Ctx: pass
    out = s._select_heavy_level(Ctx(), levels, signal_price=110.48, atr=0.1)
    assert out is None


def test_evaluate_returns_none_when_env_disabled():
    _disable()
    s = SrWeightedBounce()
    class Ctx: pass
    ctx = Ctx()
    ctx.symbol = "USDJPY=X"
    assert s.evaluate(ctx) is None


# integration sanity: enabled=False default
def test_strategy_disabled_by_default():
    s = SrWeightedBounce()
    assert s.enabled is False
