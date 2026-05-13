"""Unit tests for sr_weighted_break strategy."""
import os
import pandas as pd
from strategies.daytrade.sr_weighted_break import SrWeightedBreak


def _enable():
    os.environ["SR_WEIGHTED_BREAK_ENABLE"] = "1"


def _disable():
    os.environ.pop("SR_WEIGHTED_BREAK_ENABLE", None)


def test_composite_weight_formula():
    s = SrWeightedBreak()
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


def test_heavy_weighted_levels_gate():
    s = SrWeightedBreak()
    levels = [
        {"price": 110.50, "own_touch": 10, "d1_touch": 3, "w1_touch": 1,
         "round_score": 0.5, "magnitude_score": 0.5},
        {"price": 110.40, "own_touch": 2, "d1_touch": 0, "w1_touch": 0,
         "round_score": 0.0, "magnitude_score": 0.0},
        {"price": 111.00, "own_touch": 1, "d1_touch": 0, "w1_touch": 0,
         "round_score": 0.0, "magnitude_score": 0.0},
    ]
    heavy = s._heavy_weighted_levels(levels)
    # 上位 30% = 1 level (= max(1, int(3*0.3)) = 1)、かつ weight>=3.0
    assert len(heavy) == 1
    assert heavy[0][1]["price"] == 110.50


def test_heavy_weighted_levels_empty():
    s = SrWeightedBreak()
    assert s._heavy_weighted_levels([]) == []


def test_evaluate_returns_none_when_env_disabled():
    _disable()
    s = SrWeightedBreak()
    class Ctx:
        pass
    ctx = Ctx()
    ctx.symbol = "USDJPY=X"
    assert s.evaluate(ctx) is None


def test_strategy_disabled_by_default():
    s = SrWeightedBreak()
    assert s.enabled is False


def test_eurusd_and_eurgbp_excluded():
    _enable()
    s = SrWeightedBreak()

    class Ctx:
        pass

    ctx = Ctx()
    ctx.symbol = "EURUSD=X"
    ctx.df = None  # 早期 return される
    assert s.evaluate(ctx) is None

    ctx2 = Ctx()
    ctx2.symbol = "EURGBP=X"
    ctx2.df = None
    assert s.evaluate(ctx2) is None
    _disable()
