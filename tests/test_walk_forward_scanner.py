"""Tests for research/edge_discovery/walk_forward_scanner.py."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from research.edge_discovery.walk_forward_scanner import (
    evaluate_cell_walk_forward,
    split_holdout_folds,
    walk_forward_3fold,
)


def _index(start: str, end: str, freq: str = "15min") -> pd.DatetimeIndex:
    # Use lowercase 'h' for hour (pandas 2.2+ requires it)
    f = freq.replace("H", "h") if "H" in freq else freq
    return pd.date_range(start=start, end=end, freq=f, tz="UTC")


class TestSplitHoldoutFolds:
    def test_3_fold_270d_default(self):
        idx = _index("2025-01-01", "2026-04-28", freq="1H")
        folds = split_holdout_folds(idx, holdout_total_days=270, n_folds=3)
        assert len(folds) == 3
        # Each fold is 90 days
        for fs, fe in folds:
            assert (fe - fs).total_seconds() == 90 * 86400
        # Folds are contiguous and last fold ends at the index max
        assert folds[2][1] == idx.max()
        assert folds[1][1] == folds[2][0]
        assert folds[0][1] == folds[1][0]

    def test_5_fold(self):
        idx = _index("2025-01-01", "2026-04-28", freq="1H")
        folds = split_holdout_folds(idx, holdout_total_days=300, n_folds=5)
        assert len(folds) == 5
        for fs, fe in folds:
            assert (fe - fs).total_seconds() == 60 * 86400  # 60d each

    def test_empty_index(self):
        idx = pd.DatetimeIndex([], tz="UTC")
        folds = split_holdout_folds(idx, 270, 3)
        assert folds == []


class TestEvaluateCellWalkForward:
    def _make_evaluator(self, by_fold):
        """Build an evaluator returning fixed (n, wins, ev) by fold index."""
        calls = {"i": 0}

        def evaluator(start, end):
            i = calls["i"]
            calls["i"] += 1
            return by_fold[i]

        return evaluator

    def test_three_passes_yields_survivor(self):
        idx = _index("2025-08-01", "2026-04-28", freq="1H")
        folds = split_holdout_folds(idx, 270, 3)
        # All 3 folds: n=100, wins=60 (WR=0.6), ev=+2.0
        evaluator = self._make_evaluator([(100, 60, 2.0)] * 3)
        res = evaluate_cell_walk_forward("test_cell", evaluator, folds)
        assert res.is_survivor is True
        assert res.pass_count == 3
        assert res.summary["pooled_wr"] == 0.6
        assert res.summary["fold_pass_count"] == 3

    def test_two_passes_yields_survivor(self):
        idx = _index("2025-08-01", "2026-04-28", freq="1H")
        folds = split_holdout_folds(idx, 270, 3)
        # 2 folds pass, 1 fails (low WR)
        evaluator = self._make_evaluator(
            [(100, 60, 2.0), (100, 40, -1.5), (100, 60, 2.0)]
        )
        res = evaluate_cell_walk_forward("test_cell", evaluator, folds)
        assert res.is_survivor is True
        assert res.pass_count == 2

    def test_one_pass_fails_survivor(self):
        idx = _index("2025-08-01", "2026-04-28", freq="1H")
        folds = split_holdout_folds(idx, 270, 3)
        # Only fold 1 passes
        evaluator = self._make_evaluator(
            [(100, 40, -1.5), (100, 60, 2.0), (100, 45, -0.5)]
        )
        res = evaluate_cell_walk_forward("test_cell", evaluator, folds)
        assert res.is_survivor is False
        assert res.pass_count == 1

    def test_small_n_auto_fails(self):
        idx = _index("2025-08-01", "2026-04-28", freq="1H")
        folds = split_holdout_folds(idx, 270, 3)
        # n=3 < min_n_per_fold default 5
        evaluator = self._make_evaluator([(3, 3, 5.0)] * 3)
        res = evaluate_cell_walk_forward("test_cell", evaluator, folds)
        assert res.is_survivor is False
        for fold in res.folds:
            assert fold.passes is False
            assert any("n=3<" in r for r in fold.pass_reasons)

    def test_negative_ev_fails(self):
        idx = _index("2025-08-01", "2026-04-28", freq="1H")
        folds = split_holdout_folds(idx, 270, 3)
        # WR=0.6 but EV=-0.5 (high friction case)
        evaluator = self._make_evaluator([(100, 60, -0.5)] * 3)
        res = evaluate_cell_walk_forward("test_cell", evaluator, folds)
        assert res.is_survivor is False

    def test_ev_std_calculated(self):
        idx = _index("2025-08-01", "2026-04-28", freq="1H")
        folds = split_holdout_folds(idx, 270, 3)
        evaluator = self._make_evaluator(
            [(100, 60, 1.0), (100, 60, 3.0), (100, 60, 5.0)]
        )
        res = evaluate_cell_walk_forward("test_cell", evaluator, folds)
        # std of [1, 3, 5] (population) ≈ 1.633
        assert 1.6 < res.summary["ev_std_across_folds"] < 1.7


class TestWalkForward3Fold:
    def test_convenience_wrapper(self):
        idx = _index("2025-08-01", "2026-04-28", freq="1H")
        called = []

        def evaluator(start, end):
            called.append((start, end))
            return (100, 60, 2.0)

        res = walk_forward_3fold("cell_x", evaluator, idx)
        assert res.is_survivor is True
        assert len(called) == 3  # 3 folds invoked
