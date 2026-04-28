"""Tests for research/edge_discovery/power_analysis.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.edge_discovery.power_analysis import (
    bonferroni_per_family,
    mde_pre_reg_check,
    min_detectable_wr,
    min_n_for_wilson,
    n_scaled_wilson_gate,
    wilson_lower,
    wilson_lower_at,
)


class TestWilsonLower:
    def test_wilson_lower_n_zero(self):
        assert wilson_lower(0, 0) == 0.0

    def test_wilson_lower_known(self):
        # n=40, wins=24 (WR=0.6) → Wilson_lower ≈ 0.446 (Phase 8 EUR_JPY holdout)
        wlo = wilson_lower(24, 40)
        assert 0.43 < wlo < 0.46

    def test_wilson_lower_at_matches_wilson_lower(self):
        # wilson_lower_at(0.6, 40) should equal wilson_lower(24, 40) within tol
        a = wilson_lower(24, 40)
        b = wilson_lower_at(0.6, 40)
        assert abs(a - b) < 1e-3


class TestNScaledGate:
    def test_gate_relaxes_at_small_n(self):
        # Strict 0.5 only attainable at n→∞; small n must relax.
        gate_40 = n_scaled_wilson_gate(40, target_wr=0.5)
        gate_400 = n_scaled_wilson_gate(400, target_wr=0.5)
        gate_4000 = n_scaled_wilson_gate(4000, target_wr=0.5)
        assert gate_40 < gate_400 < gate_4000 < 0.5

    def test_gate_phase8_holdout_n40(self):
        # At n=40 target_wr=0.5, gate ~ 0.35 (Wilson margin at p=0.5, n=40)
        # Strictly less than 0.48 (the original Phase 8 fixed gate).
        gate = n_scaled_wilson_gate(40, target_wr=0.5)
        assert 0.33 < gate < 0.40
        assert gate < 0.48

    def test_phase8_eurjpy_passes_under_p1(self):
        # Phase 8 EUR_JPY cell: WR_holdout=0.6 n=40 Wilson_lo=0.446
        # Strict gate 0.48 → fail. P1 gate (~0.40) → pass.
        wlo_actual = wilson_lower_at(0.6, 40)
        gate = n_scaled_wilson_gate(40, target_wr=0.5)
        assert wlo_actual >= gate
        # And the strict gate failed:
        assert wlo_actual < 0.48


class TestMinDetectableWR:
    def test_n_zero_returns_one(self):
        assert min_detectable_wr(0, 0.48) == 1.0

    def test_phase8_n40_target_048(self):
        # At n=40, gate=0.48 → real edge needs WR ≥ ~0.625
        wr = min_detectable_wr(40, 0.48)
        assert 0.61 < wr < 0.64

    def test_n100_target_05(self):
        # At n=100, gate=0.5 → need WR ≥ ~0.598
        wr = min_detectable_wr(100, 0.5)
        assert 0.59 < wr < 0.61


class TestMinNForWilson:
    def test_phase8_target_wr_06(self):
        # Edge with true WR=0.6 needs n≥? for Wilson_lower>0.48
        n = min_n_for_wilson(target_wr=0.6, target_wilson_lower=0.48)
        # Empirically around 80-90 (Phase 8 design admitted only ~40 → impossible)
        assert 60 < n < 110

    def test_target_wr_le_threshold_returns_max(self):
        # If true WR ≤ threshold, no n suffices
        n = min_n_for_wilson(target_wr=0.5, target_wilson_lower=0.5)
        assert n >= 100_000


class TestBonferroniPerFamily:
    def test_track_split(self):
        # Phase 8 5 tracks: A=720, B=2087, C=9804, D=1380, E=846
        thresholds = bonferroni_per_family([720, 2087, 9804, 1380, 846])
        # Bonferroni gets stricter (smaller threshold) for larger families
        # Family sizes sorted ascending: 720 < 846 < 1380 < 2087 < 9804
        # → thresholds order: idx 0 > 4 > 3 > 1 > 2
        assert thresholds[0] > thresholds[4] > thresholds[3] > thresholds[1] > thresholds[2]
        # Each is alpha/n
        assert abs(thresholds[0] - 0.05 / 720) < 1e-12


class TestMDEPreRegCheck:
    def test_phase8_infeasible_design(self):
        # Phase 8: n=40 target_wr=0.6 target_wilson_lower=0.48
        # Should be infeasible (Wilson_lower at WR=0.6 n=40 is 0.446)
        chk = mde_pre_reg_check(
            n_planned=40, target_wr=0.6, target_wilson_lower=0.48,
        )
        assert chk.feasible_wilson is False
        assert chk.n_required_for_wilson > 40
        assert chk.notes  # has at least one explanation

    def test_feasible_design(self):
        # n=200 target_wr=0.6 target_wilson_lower=0.5 → feasible
        chk = mde_pre_reg_check(
            n_planned=200, target_wr=0.6, target_wilson_lower=0.5,
        )
        assert chk.feasible_wilson is True

    def test_with_bonferroni(self):
        # Phase 8 Track C: n_tests=9804 → Bonferroni 5.1e-6
        # n=40 WR=0.6: p ≈ 0.0625 → fail
        chk = mde_pre_reg_check(
            n_planned=40, target_wr=0.6, target_wilson_lower=0.5,
            bonferroni_threshold=0.05 / 9804,
        )
        assert chk.feasible_bonferroni is False
