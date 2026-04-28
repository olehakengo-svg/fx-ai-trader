"""
Walk-forward 3-fold scanner template for Phase 9 edge discovery.

Phase 8 used a single 90-day holdout, which let regime bias dominate small
holdouts (Track A's GBP_JPY fw=4 collapsed from training WR=0.61 to holdout
WR=0.486 — likely 90d window happened to be ranging when the cell needs
trending). P2 in /Users/jg-n-012/.claude/plans/memoized-snuggling-eclipse.md.

This module supplies a generic helper that:

  * Splits the most-recent ``holdout_total_days`` of data into ``n_folds``
    contiguous, non-overlapping rolling windows.
  * Runs a user-supplied evaluator (cell → (n, wins, ev_pip)) on each fold.
  * Applies a user-supplied gate (n, wr, wilson_lower, ev) per fold and
    returns ``passes >= min_pass_folds`` cells as walk-forward-stable
    survivors.

Phase 9 scanners (track_*) call ``walk_forward_3fold`` instead of single
holdout. Stage 1 (training) keeps the LOCK gate; the wf 3-fold check
replaces Phase 8 Stage 2 holdout. Cells that survive are robust by
construction across at least 2 of the 3 most-recent regimes.

Reused infrastructure:
  research.edge_discovery.power_analysis.{wilson_lower_at, n_scaled_wilson_gate}
  research.edge_discovery.significance.benjamini_hochberg
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd

from research.edge_discovery.power_analysis import (
    n_scaled_wilson_gate,
    wilson_lower_at,
)


@dataclass
class FoldResult:
    """Single-fold evaluation of one cell."""

    fold_idx: int
    start: pd.Timestamp
    end: pd.Timestamp
    n: int
    wins: int
    wr: float
    wilson_lower: float
    ev_pip: float
    passes: bool
    pass_reasons: list[str]


@dataclass
class WalkForwardResult:
    """Aggregated walk-forward verdict for one cell."""

    cell_id: str
    folds: list[FoldResult]
    pass_count: int
    is_survivor: bool
    summary: dict


def split_holdout_folds(
    df_index: pd.DatetimeIndex,
    holdout_total_days: int = 270,
    n_folds: int = 3,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Split the last ``holdout_total_days`` into ``n_folds`` rolling windows.

    Returns a list of (fold_start, fold_end) timestamp pairs, ordered from
    oldest to newest. Each fold spans ``holdout_total_days / n_folds`` days.

    Phase 9 default: 270 days / 3 folds = 90d per fold (matches Phase 8
    single-holdout span, but tested 3 times across 3 regimes).
    """
    if len(df_index) == 0:
        return []
    end = df_index.max()
    start_total = end - pd.Timedelta(days=holdout_total_days)
    fold_days = holdout_total_days / n_folds
    folds: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for i in range(n_folds):
        fs = start_total + pd.Timedelta(days=fold_days * i)
        fe = start_total + pd.Timedelta(days=fold_days * (i + 1))
        folds.append((fs, fe))
    return folds


def evaluate_cell_walk_forward(
    cell_id: str,
    cell_evaluator: Callable[[pd.Timestamp, pd.Timestamp], tuple[int, int, float]],
    folds: list[tuple[pd.Timestamp, pd.Timestamp]],
    *,
    target_wr: float = 0.5,
    min_n_per_fold: int = 5,
    min_pass_folds: int = 2,
    require_positive_ev: bool = True,
) -> WalkForwardResult:
    """Apply a per-fold evaluator and aggregate the walk-forward verdict.

    Parameters
    ----------
    cell_id : str
        Identifier for reporting (e.g. "EUR_JPY|hour20|bbpb3|SELL|fw12").
    cell_evaluator : callable
        ``(start_ts, end_ts) -> (n_trades, wins, ev_pip)`` for the cell on
        the requested time window. The caller owns trade simulation and
        friction adjustment; this scanner only aggregates per-fold stats.
    folds : list of (start, end)
        Output of ``split_holdout_folds``.
    target_wr : float
        Wilson lower-bound floor for ``n_scaled_wilson_gate`` (default 0.5).
    min_n_per_fold : int
        Minimum trades required to score a fold; smaller folds auto-fail.
    min_pass_folds : int
        Number of folds that must pass for the cell to be a survivor
        (default 2 of 3).
    require_positive_ev : bool
        When True, EV must be > 0 to pass the fold gate; turn off only for
        diagnostic (no-friction) runs.

    Returns
    -------
    WalkForwardResult
    """
    fold_results: list[FoldResult] = []
    for idx, (fs, fe) in enumerate(folds):
        n, wins, ev = cell_evaluator(fs, fe)
        wr = wins / n if n > 0 else 0.0
        wlo = wilson_lower_at(wr, n) if n > 0 else 0.0
        gate = n_scaled_wilson_gate(n, target_wr=target_wr) if n > 0 else 1.0

        reasons: list[str] = []
        passes = True
        if n < min_n_per_fold:
            passes = False
            reasons.append(f"n={n}<{min_n_per_fold}")
        if wlo < gate:
            passes = False
            reasons.append(f"wilson={wlo:.3f}<gate={gate:.3f}")
        if require_positive_ev and ev <= 0:
            passes = False
            reasons.append(f"ev={ev:.3f}<=0")
        if passes:
            reasons.append("PASS")

        fold_results.append(
            FoldResult(
                fold_idx=idx,
                start=fs,
                end=fe,
                n=n,
                wins=wins,
                wr=wr,
                wilson_lower=wlo,
                ev_pip=ev,
                passes=passes,
                pass_reasons=reasons,
            )
        )

    pass_count = sum(1 for f in fold_results if f.passes)
    is_survivor = pass_count >= min_pass_folds

    n_total = sum(f.n for f in fold_results)
    wins_total = sum(f.wins for f in fold_results)
    pooled_wr = wins_total / n_total if n_total > 0 else 0.0
    pooled_wilson = wilson_lower_at(pooled_wr, n_total) if n_total > 0 else 0.0
    avg_ev = (
        sum(f.ev_pip * f.n for f in fold_results) / n_total
        if n_total > 0
        else 0.0
    )
    ev_per_fold = [f.ev_pip for f in fold_results]
    ev_std = _stddev(ev_per_fold) if len(ev_per_fold) > 1 else 0.0

    return WalkForwardResult(
        cell_id=cell_id,
        folds=fold_results,
        pass_count=pass_count,
        is_survivor=is_survivor,
        summary={
            "n_total": n_total,
            "pooled_wr": pooled_wr,
            "pooled_wilson_lower": pooled_wilson,
            "avg_ev_pip": avg_ev,
            "ev_std_across_folds": ev_std,
            "fold_pass_count": pass_count,
            "min_pass_folds": min_pass_folds,
        },
    )


def _stddev(values: list[float]) -> float:
    """Population standard deviation (matches statistics.pstdev)."""
    if not values:
        return 0.0
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def walk_forward_3fold(
    cell_id: str,
    cell_evaluator: Callable[[pd.Timestamp, pd.Timestamp], tuple[int, int, float]],
    df_index: pd.DatetimeIndex,
    *,
    holdout_total_days: int = 270,
    target_wr: float = 0.5,
    min_n_per_fold: int = 5,
    min_pass_folds: int = 2,
    require_positive_ev: bool = True,
) -> WalkForwardResult:
    """Convenience wrapper: 3-fold rolling walk-forward over the last
    ``holdout_total_days`` of ``df_index``. See evaluate_cell_walk_forward
    for the parameter semantics.
    """
    folds = split_holdout_folds(df_index, holdout_total_days, n_folds=3)
    return evaluate_cell_walk_forward(
        cell_id,
        cell_evaluator,
        folds,
        target_wr=target_wr,
        min_n_per_fold=min_n_per_fold,
        min_pass_folds=min_pass_folds,
        require_positive_ev=require_positive_ev,
    )
