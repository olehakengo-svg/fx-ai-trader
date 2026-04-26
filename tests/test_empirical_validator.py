"""Tests for tools.empirical_validator."""
from __future__ import annotations

import math
import pytest

np = pytest.importorskip("numpy")

# Add project root to path so 'tools' package is importable
import sys
import os
_PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJ_ROOT not in sys.path:
    sys.path.insert(0, _PROJ_ROOT)

from tools.empirical_validator import (
    wilson_ci,
    bootstrap_ci,
    bootstrap_wr_ci,
    monotonicity_test,
    top_k_drop_test,
    bonferroni_correct,
    benjamini_hochberg,
    aggregate_3d,
    sample_size_for_proportion_diff,
)


# ─── Wilson CI ────────────────────────────────────────────────────────

def test_wilson_ci_known_value():
    """Wilson CI for 50/100 success at alpha=0.05 should be approx (0.4038, 0.5962)."""
    ci = wilson_ci(50, 100, alpha=0.05)
    assert ci["p"] == 0.5
    assert ci["low"] == pytest.approx(0.4038, abs=0.01)
    assert ci["high"] == pytest.approx(0.5962, abs=0.01)


def test_wilson_ci_zero_success():
    ci = wilson_ci(0, 30, alpha=0.05)
    assert ci["p"] == 0.0
    assert ci["low"] == pytest.approx(0.0, abs=0.001)
    assert 0 < ci["high"] < 0.20


def test_wilson_ci_full_success():
    ci = wilson_ci(30, 30, alpha=0.05)
    assert ci["p"] == 1.0
    assert ci["high"] == pytest.approx(1.0, abs=0.001)


def test_wilson_ci_zero_n():
    ci = wilson_ci(0, 0)
    assert math.isnan(ci["p"])


def test_wilson_ci_invalid_input():
    with pytest.raises(ValueError):
        wilson_ci(50, 30)


# ─── Bootstrap CI ────────────────────────────────────────────────────

def test_bootstrap_mean_ci_covers_truth():
    """Bootstrap CI for mean should cover the true mean for a known distribution."""
    rng = np.random.default_rng(42)
    samples = rng.normal(loc=2.0, scale=1.0, size=200)
    ci = bootstrap_ci(samples, n_resample=500, alpha=0.05, seed=0)
    assert ci["low"] < 2.0 < ci["high"]
    assert ci["estimate"] == pytest.approx(samples.mean())


def test_bootstrap_wr_ci_for_known_proportion():
    pnls = [1.0] * 60 + [-1.0] * 40  # WR exactly 60%
    ci = bootstrap_wr_ci(pnls, n_resample=500, seed=0)
    assert ci["estimate"] == pytest.approx(0.60)
    assert ci["low"] < 0.60 < ci["high"]
    # 95% CI で大体 +/- 10% に収まる (n=100)
    assert (ci["high"] - ci["low"]) < 0.25


def test_bootstrap_empty():
    ci = bootstrap_ci([], n_resample=10)
    assert math.isnan(ci["estimate"])


# ─── Monotonicity ────────────────────────────────────────────────────

def test_monotonicity_strictly_increasing():
    """4 bins with WR 30/40/55/65 should test as monotonic."""
    bins = [0, 1, 2, 3]
    wrs = [0.30, 0.40, 0.55, 0.65]
    res = monotonicity_test(bins, wrs, n_permutations=200, seed=0)
    # Spearman = 1 because perfectly monotonic
    assert res["spearman"] == pytest.approx(1.0, abs=1e-6)


def test_monotonicity_random_not_monotonic():
    """Shuffled WRs should not be monotonic."""
    bins = [0, 1, 2, 3, 4, 5]
    # Inverted-U shape (clearly non-monotonic)
    wrs = [0.30, 0.50, 0.70, 0.65, 0.45, 0.25]
    res = monotonicity_test(bins, wrs, n_permutations=200, seed=0)
    assert res["monotonic"] is False


def test_monotonicity_too_few_bins():
    res = monotonicity_test([0, 1], [0.4, 0.5])
    assert res["monotonic"] is False
    assert res["n_bins"] == 2


# ─── Top-K-drop ──────────────────────────────────────────────────────

def test_top_1_drop_stable():
    values = [1.0] * 50 + [2.0] * 50
    res = top_k_drop_test(values, k=1)
    assert res["full"] == pytest.approx(1.5)
    # Drop 1 (a 2.0) → mean drops slightly
    assert res["dropped"] < res["full"]
    assert abs(res["drop_pct"]) < 5  # less than 5%


def test_top_1_drop_unstable():
    """1 huge outlier dominates."""
    values = [0.1] * 99 + [100.0]
    res = top_k_drop_test(values, k=1)
    assert res["full"] == pytest.approx((0.1 * 99 + 100) / 100)
    assert res["dropped"] == pytest.approx(0.1)
    assert res["drop_pct"] > 90  # huge instability


def test_top_k_drop_k_too_large():
    res = top_k_drop_test([1.0, 2.0], k=5)
    assert math.isnan(res["dropped"])


# ─── Bonferroni / BH ─────────────────────────────────────────────────

def test_bonferroni_filters_correctly():
    pvals = [0.001, 0.01, 0.04, 0.20]
    sig = bonferroni_correct(pvals, alpha=0.05)
    # threshold = 0.05 / 4 = 0.0125
    assert sig == [True, True, False, False]


def test_bonferroni_empty():
    assert bonferroni_correct([]) == []


def test_benjamini_hochberg_more_lenient():
    pvals = [0.001, 0.01, 0.04, 0.20]
    bonf = bonferroni_correct(pvals, alpha=0.05)
    bh = benjamini_hochberg(pvals, alpha=0.05)
    # BH should flag at least as many as Bonferroni
    assert sum(bh) >= sum(bonf)


# ─── 3D aggregation ──────────────────────────────────────────────────

def test_aggregate_3d_basic():
    trades = [
        {"a": "X", "b": 1, "c": "low",  "pnl_pips": 1.0},
        {"a": "X", "b": 1, "c": "low",  "pnl_pips": 2.0},
        {"a": "X", "b": 1, "c": "low",  "pnl_pips": -1.0},
        {"a": "X", "b": 2, "c": "high", "pnl_pips": 3.0},
        {"a": "Y", "b": 1, "c": "low",  "pnl_pips": -2.0},
    ]
    rows = aggregate_3d(trades, "a", "b", "c")
    # 3 distinct cells
    assert len(rows) == 3
    # X/1/low cell
    cell = next(r for r in rows if r["a"] == "X" and r["b"] == 1 and r["c"] == "low")
    assert cell["n"] == 3
    assert cell["wr"] == pytest.approx(2 / 3)
    assert cell["ev"] == pytest.approx(2.0 / 3)
    assert "wilson_low" in cell
    assert "wilson_high" in cell


def test_aggregate_3d_skips_missing_pnl():
    trades = [
        {"a": "X", "b": 1, "c": "z", "pnl_pips": 1.0},
        {"a": "X", "b": 1, "c": "z"},  # missing pnl
    ]
    rows = aggregate_3d(trades, "a", "b", "c")
    assert len(rows) == 1
    assert rows[0]["n"] == 1


def test_aggregate_3d_empty():
    assert aggregate_3d([], "a", "b", "c") == []


# ─── Sample size planner ─────────────────────────────────────────────

def test_sample_size_finite_for_real_difference():
    n = sample_size_for_proportion_diff(0.40, 0.50)
    # detect 10pp WR difference at alpha=0.05, power=0.80
    # Approx 380-400 per group
    assert 200 < n < 700


def test_sample_size_zero_for_no_diff():
    assert sample_size_for_proportion_diff(0.50, 0.50) == 0


def test_sample_size_smaller_for_larger_effect():
    n_small = sample_size_for_proportion_diff(0.40, 0.50)
    n_big = sample_size_for_proportion_diff(0.30, 0.60)
    assert n_big < n_small


def test_sample_size_invalid_input():
    with pytest.raises(ValueError):
        sample_size_for_proportion_diff(0.0, 0.5)
    with pytest.raises(ValueError):
        sample_size_for_proportion_diff(0.5, 1.0)
