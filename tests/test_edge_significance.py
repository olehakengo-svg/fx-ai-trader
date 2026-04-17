"""Unit tests for research.edge_discovery.significance module.

Covers boundary cases and known-value checks for:
- binomial_one_sided_p (exact + normal approximation paths)
- binomial_two_sided_p (symmetry around p=0.5)
- benjamini_hochberg (classic examples)
- bonferroni_threshold
- build_pocket
- wf_stable_for_cell
- apply_corrections + assign_recommendation integration
"""
from __future__ import annotations

import math
import pytest
import pandas as pd

from research.edge_discovery.significance import (
    binomial_one_sided_p,
    binomial_two_sided_p,
    benjamini_hochberg,
    bonferroni_threshold,
    build_pocket,
    wf_stable_for_cell,
    apply_corrections,
    assign_recommendation,
    PocketStats,
)


# ──────────────────────────────────────────────────────
# binomial_one_sided_p
# ──────────────────────────────────────────────────────
class TestBinomialOneSided:
    def test_zero_n_returns_one(self):
        assert binomial_one_sided_p(0, 0, 0.5) == 1.0

    def test_k_zero_returns_one(self):
        # P(K >= 0) is always 1
        assert binomial_one_sided_p(0, 10, 0.5) == 1.0

    def test_k_exceeds_n_returns_zero(self):
        # P(K >= k) where k>n is impossible
        assert binomial_one_sided_p(11, 10, 0.5) == 0.0

    def test_exact_path_small_n(self):
        # n=10, k=10, p=0.5 → P(K>=10) = 0.5^10 ≈ 0.000977
        p = binomial_one_sided_p(10, 10, 0.5)
        assert abs(p - (0.5 ** 10)) < 1e-9

    def test_exact_path_symmetric(self):
        # For p=0.5, P(K>=k) for n=20, k=10 should be ~0.5 (actually >0.5 since inclusive of mean)
        p = binomial_one_sided_p(10, 20, 0.5)
        # P(K>=10 | n=20,p=0.5) = 1 - P(K<=9) = 1 - 0.4119 = 0.5881
        assert 0.58 < p < 0.60

    def test_normal_approx_path_large_n(self):
        # n=100, k=60, p=0.5 → P(K>=60) ≈ 0.0284 (from tables)
        p = binomial_one_sided_p(60, 100, 0.5)
        assert 0.025 < p < 0.035

    def test_monotone_decreasing_in_k(self):
        # P(K>=k) should be non-increasing as k grows
        ps = [binomial_one_sided_p(k, 50, 0.5) for k in range(0, 51)]
        for i in range(len(ps) - 1):
            assert ps[i] >= ps[i + 1] - 1e-12

    def test_zero_variance_case(self):
        # p0=0 and k>0 → impossible → 0
        # p0=1 and k<=n → certain → 1
        assert binomial_one_sided_p(1, 40, 0.0) == 0.0
        # p0=1 path: sd=0, k=n → return 1.0 (k not > mu)
        # Actually normal-approx branch: mu=n, sd=0, k>mu → 0
        # But our guard checks `k > mu`; with k=n=mu, returns 1.0.
        # For p0=1, any k<=n has P=1.
        assert binomial_one_sided_p(40, 40, 1.0) == 1.0


# ──────────────────────────────────────────────────────
# binomial_two_sided_p
# ──────────────────────────────────────────────────────
class TestBinomialTwoSided:
    def test_zero_n(self):
        assert binomial_two_sided_p(0, 0, 0.5) == 1.0

    def test_bounded_above_by_one(self):
        # Two-sided p must never exceed 1
        for k in range(0, 51):
            p = binomial_two_sided_p(k, 50, 0.5)
            assert 0 <= p <= 1.0

    def test_symmetry_around_half(self):
        # For p=0.5, the test statistic should be symmetric:
        # binomial_two_sided_p(k, n, 0.5) ≈ binomial_two_sided_p(n-k, n, 0.5)
        for k in [5, 10, 15, 20, 25, 30, 35, 40, 45]:
            p1 = binomial_two_sided_p(k, 50, 0.5)
            p2 = binomial_two_sided_p(50 - k, 50, 0.5)
            assert abs(p1 - p2) < 1e-6, f"asymmetric at k={k}: {p1} vs {p2}"

    def test_detects_structural_loser(self):
        # n=200, k=70 wins (35%), p0=0.5 → clearly significant (reject null)
        p = binomial_two_sided_p(70, 200, 0.5)
        assert p < 0.01  # well below 1% threshold

    def test_central_case_not_significant(self):
        # n=100, k=52, p0=0.5 → near the center, not significant
        p = binomial_two_sided_p(52, 100, 0.5)
        assert p > 0.5

    def test_k_equals_n_boundary(self):
        # n=20, k=20, p0=0.5 → very extreme, p should be tiny
        p = binomial_two_sided_p(20, 20, 0.5)
        # one-sided upper tail = 0.5^20, two-sided = 2 * min(upper, lower)
        # lower = P(K<=20) = 1 → upper wins → 2 * 0.5^20
        expected_max = 2 * (0.5 ** 20)
        assert p <= expected_max + 1e-12

    def test_k_zero_boundary(self):
        # n=20, k=0, p0=0.5 → very extreme on the other side
        p = binomial_two_sided_p(0, 20, 0.5)
        assert p <= 2 * (0.5 ** 20) + 1e-12


# ──────────────────────────────────────────────────────
# benjamini_hochberg
# ──────────────────────────────────────────────────────
class TestBenjaminiHochberg:
    def test_empty_input(self):
        assert benjamini_hochberg([], q=0.10) == []

    def test_all_ones_no_rejection(self):
        # All p-values = 1 → reject nothing
        mask = benjamini_hochberg([1.0] * 10, q=0.10)
        assert mask == [False] * 10

    def test_all_zeros_all_rejected(self):
        mask = benjamini_hochberg([0.0] * 5, q=0.10)
        assert mask == [True] * 5

    def test_classic_example(self):
        # Classic BH example: 10 p-values, q=0.05
        # p = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216]
        # Thresholds at q=0.05: (i/10)*0.05 = [0.005, 0.010, 0.015, 0.020, 0.025, ...]
        # Compare: 0.001<=0.005 ✓, 0.008<=0.010 ✓, 0.039<=0.015 ✗, 0.041<=0.020 ✗...
        # But BH rejects all up to the LARGEST i satisfying p_(i) <= (i/n)q.
        # Only p(1) and p(2) satisfy; rejected = first 2 (positions 0,1 in sorted).
        ps = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216]
        mask = benjamini_hochberg(ps, q=0.05)
        assert sum(mask) == 2
        # The two smallest p-values (indices 0 and 1) should be rejected
        assert mask[0] is True and mask[1] is True

    def test_preserves_input_order(self):
        # Input order should be preserved in the mask
        ps = [0.8, 0.001, 0.5, 0.002]  # unsorted
        mask = benjamini_hochberg(ps, q=0.10)
        # smallest two (indices 1 and 3) are candidates for rejection
        # Largest i where p_(i) <= (i/4)*0.10:
        #   i=1: 0.001 <= 0.025 ✓
        #   i=2: 0.002 <= 0.050 ✓
        #   i=3: 0.5   <= 0.075 ✗
        # So reject 2, at original indices 1 and 3
        assert mask == [False, True, False, True]

    def test_step_up_property(self):
        # BH is step-up: if p_(i) passes, all p_(j<=i) are rejected even if they fail threshold
        # p = [0.04, 0.001, 0.005]  at q=0.10
        #   sorted: 0.001 (0.0333), 0.005 (0.0667), 0.04 (0.10)
        #   All pass their thresholds; reject all 3
        mask = benjamini_hochberg([0.04, 0.001, 0.005], q=0.10)
        assert mask == [True, True, True]


# ──────────────────────────────────────────────────────
# bonferroni_threshold
# ──────────────────────────────────────────────────────
class TestBonferroni:
    def test_standard(self):
        assert bonferroni_threshold(0.05, 10) == 0.005

    def test_zero_tests_safe(self):
        # Guard against divide-by-zero; use max(1, n_tests)
        assert bonferroni_threshold(0.05, 0) == 0.05

    def test_negative_tests_safe(self):
        assert bonferroni_threshold(0.05, -5) == 0.05


# ──────────────────────────────────────────────────────
# build_pocket
# ──────────────────────────────────────────────────────
class TestBuildPocket:
    def test_empty_series(self):
        p = build_pocket(key=("test",), pnl_series=pd.Series([], dtype=float))
        assert p.n == 0
        assert p.wins == 0
        assert p.wr == 0.0
        assert p.avg_pips == 0.0
        assert p.pf == 0.0

    def test_all_wins(self):
        p = build_pocket(key=("test",), pnl_series=pd.Series([1.0, 2.0, 3.0]))
        assert p.n == 3
        assert p.wins == 3
        assert p.wr == 1.0
        assert p.total_pips == 6.0
        assert p.pf == float("inf")

    def test_all_losses(self):
        p = build_pocket(key=("test",), pnl_series=pd.Series([-1.0, -2.0, -3.0]))
        assert p.n == 3
        assert p.wins == 0
        assert p.wr == 0.0
        assert p.pf == 0.0

    def test_mixed(self):
        p = build_pocket(
            key=("test",),
            pnl_series=pd.Series([2.0, 2.0, -1.0, -1.0]),
            breakeven_wr=0.5,
        )
        assert p.n == 4
        assert p.wins == 2
        assert p.wr == 0.5
        # PF = 4 / 2 = 2.0
        assert p.pf == 2.0

    def test_nan_handled(self):
        p = build_pocket(key=("x",), pnl_series=pd.Series([1.0, float("nan"), -1.0]))
        assert p.n == 2  # NaN dropped


# ──────────────────────────────────────────────────────
# wf_stable_for_cell
# ──────────────────────────────────────────────────────
class TestWfStable:
    def test_empty(self):
        assert wf_stable_for_cell([]) is None

    def test_insufficient_data(self):
        # Only 5 items across 3 folds → fold_size=1 < min_n_per_fold=10 → None
        items = [(i, 1.0) for i in range(5)]
        assert wf_stable_for_cell(items, n_folds=3, min_n_per_fold=10) is None

    def test_stable_all_positive(self):
        # 30 items, all positive → 3/3 folds positive → stable
        items = [(i, 1.0) for i in range(30)]
        assert wf_stable_for_cell(items, n_folds=3, min_n_per_fold=8) is True

    def test_unstable_all_negative(self):
        items = [(i, -1.0) for i in range(30)]
        assert wf_stable_for_cell(items, n_folds=3, min_n_per_fold=8) is False

    def test_marginal_two_of_three(self):
        # 10 positive, 10 negative, 10 positive → 2/3 folds (positive last) → stable
        items = (
            [(i, 1.0) for i in range(10)]
            + [(i + 10, -1.0) for i in range(10)]
            + [(i + 20, 1.0) for i in range(10)]
        )
        assert wf_stable_for_cell(items, n_folds=3, min_n_per_fold=8) is True

    def test_degrading_strategy_fails_default(self):
        # +/+/- pattern: 2/3 folds positive but LAST is negative.
        # With require_last_fold_positive=True (default), this is UNSTABLE.
        items = (
            [(i, 1.0) for i in range(10)]
            + [(i + 10, 1.0) for i in range(10)]
            + [(i + 20, -1.0) for i in range(10)]
        )
        assert wf_stable_for_cell(items, n_folds=3, min_n_per_fold=8) is False

    def test_degrading_strategy_passes_when_recency_disabled(self):
        items = (
            [(i, 1.0) for i in range(10)]
            + [(i + 10, 1.0) for i in range(10)]
            + [(i + 20, -1.0) for i in range(10)]
        )
        # 2/3 folds positive, ignoring last-fold sign
        assert wf_stable_for_cell(
            items, n_folds=3, min_n_per_fold=8,
            require_last_fold_positive=False,
        ) is True

    def test_sorts_by_time(self):
        # Out-of-order input should be sorted (stable 3/3)
        items = [(30 - i, 1.0) for i in range(30)]  # reverse time
        assert wf_stable_for_cell(items, n_folds=3, min_n_per_fold=8) is True


# ──────────────────────────────────────────────────────
# apply_corrections + assign_recommendation
# ──────────────────────────────────────────────────────
class TestIntegration:
    def _make(self, key, n, wins, avg, p_val, wf=True):
        p = PocketStats(
            key=key, n=n, wins=wins, wr=wins / n if n > 0 else 0.0,
            avg_pips=avg, total_pips=avg * n, pf=2.0, std_pips=1.0,
            breakeven_wr=0.5, p_value=p_val, wf_stable=wf,
        )
        return p

    def test_apply_corrections_empty(self):
        result = apply_corrections([], alpha=0.05, fdr_q=0.10)
        assert result == []

    def test_bonferroni_flag(self):
        pockets = [
            self._make(("a",), n=50, wins=40, avg=2.0, p_val=1e-6),  # very significant
            self._make(("b",), n=50, wins=25, avg=0.0, p_val=0.5),   # not significant
        ]
        apply_corrections(pockets, alpha=0.05)
        # Bonf threshold = 0.05/2 = 0.025
        assert pockets[0].bonf_significant is True
        assert pockets[1].bonf_significant is False

    def test_recommendation_strong(self):
        pockets = [self._make(("a",), n=100, wins=80, avg=2.0, p_val=1e-10, wf=True)]
        apply_corrections(pockets, alpha=0.05)
        assign_recommendation(pockets, min_n_strong=30)
        assert pockets[0].recommendation == "STRONG"

    def test_recommendation_moderate_no_wf(self):
        # FDR-sig positive but WF not stable → MODERATE
        pockets = [
            self._make(("a",), n=100, wins=70, avg=1.5, p_val=1e-4, wf=False),
            # Add a filler to prevent Bonf=FDR degeneracy
            self._make(("b",), n=50, wins=25, avg=0.0, p_val=0.9),
        ]
        apply_corrections(pockets, alpha=0.05, fdr_q=0.10)
        assign_recommendation(pockets, min_n_strong=30)
        # a is FDR-sig + avg>0 + N>=30 + wf=False → MODERATE
        assert pockets[0].recommendation == "MODERATE"

    def test_recommendation_weak_negative(self):
        # Bonf-sig but negative → WEAK (not STRONG/MODERATE)
        pockets = [self._make(("a",), n=100, wins=20, avg=-2.0, p_val=1e-10, wf=True)]
        apply_corrections(pockets, alpha=0.05)
        assign_recommendation(pockets)
        assert pockets[0].recommendation == "WEAK"
        # But bonf_significant should still be True (structural loser detection)
        assert pockets[0].bonf_significant is True

    def test_recommendation_weak_insufficient_n(self):
        pockets = [self._make(("a",), n=10, wins=8, avg=2.0, p_val=1e-6, wf=True)]
        apply_corrections(pockets, alpha=0.05)
        assign_recommendation(pockets, min_n_strong=30)
        assert pockets[0].recommendation == "WEAK"
