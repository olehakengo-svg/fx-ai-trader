"""Walk-forward 3-fold scanner with per-trade preservation + clustering audit.

This module is an **additive helper** to ``walk_forward_scanner`` (Phase 9
P2). It introduces:

  * A 4-tuple evaluator contract ``(start, end) -> (n, wins, ev_pip, trades)``
    that preserves the per-trade list per fold. The original 3-tuple API in
    ``walk_forward_scanner.evaluate_cell_walk_forward`` is unchanged.
  * Per-fold AND pooled clustering checks via
    ``research.edge_discovery.clustering_artifacts.detect_repeat_firing``.
    Catches the within-fold artifact case (same-day burst at near-identical
    entry/SL price) that fold-isolation alone misses.
  * Result dataclasses with ``trades`` field so post-hoc audits can run
    independently of the original scanner — closing the Phase 8 gap where
    holdout JSONs preserved aggregate stats only.

Why a separate file
-------------------
Phase 9 P2's ``walk_forward_scanner`` is shipped on main; we don't modify
it to avoid merge conflicts with the parallel discovery session. Future
Phase 9 callers that need clustering can opt into this helper while
existing callers continue to use the 3-tuple API unchanged.

Wiring with mde_pre_reg_check
-----------------------------
The pooled trades returned by ``walk_forward_with_clustering`` can be
passed directly into ``power_analysis.mde_pre_reg_check(..., shadow_trades=
result.pooled_trades, pair=...)`` so the pre-LOCK feasibility check
considers both fold stability and within-fold sample independence.

Usage::

    from research.edge_discovery.walk_forward_with_trades import (
        walk_forward_with_clustering,
    )
    from research.edge_discovery.power_analysis import mde_pre_reg_check

    result = walk_forward_with_clustering(
        cell_id="EUR_JPY|h20|bbpb3|SELL|fw12",
        cell_evaluator=my_bt_runner,   # returns (n, wins, ev_pip, trades)
        df_index=df.index,
        pair="EUR_JPY",
    )
    if not result.is_survivor:
        print("walk-forward fail")
    pc = mde_pre_reg_check(
        n_planned=result.summary["n_total"],
        target_wr=0.6,
        shadow_trades=result.pooled_trades,
        pair="EUR_JPY",
    )
    if not pc.feasible_clustering:
        print("LOCK blocked: clustering artifact")
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from research.edge_discovery.clustering_artifacts import detect_repeat_firing
from research.edge_discovery.power_analysis import (
    n_scaled_wilson_gate,
    wilson_lower_at,
)
from research.edge_discovery.walk_forward_scanner import split_holdout_folds


# ─── Evaluator contract ─────────────────────────────────────────────────
# Returns: (n_trades, wins, ev_pip, trades)
# trades is a list of dicts with keys: entry_time, entry_price, sl, instrument
EvaluatorWithTrades = Callable[
    [pd.Timestamp, pd.Timestamp],
    tuple[int, int, float, list[dict]],
]


@dataclass
class FoldEvaluation:
    """Single-fold result with per-trade preservation."""

    fold_idx: int
    start: pd.Timestamp
    end: pd.Timestamp
    n: int
    wins: int
    wr: float
    wilson_lower: float
    ev_pip: float
    trades: list[dict] = field(default_factory=list)
    passes_stats: bool = False
    stats_reasons: list[str] = field(default_factory=list)
    clustering_verdict: Optional[str] = None
    clustering_flags: list[str] = field(default_factory=list)
    clustering_passes: Optional[bool] = None  # None when n insufficient

    @property
    def passes_full(self) -> bool:
        """Pass requires both stats AND clustering (when evaluable)."""
        if not self.passes_stats:
            return False
        # Clustering=None means insufficient data; do not block on it
        if self.clustering_passes is False:
            return False
        return True


@dataclass
class WalkForwardWithTradesResult:
    """Aggregated walk-forward verdict with pooled clustering check."""

    cell_id: str
    folds: list[FoldEvaluation]
    pooled_trades: list[dict]
    pooled_clustering_verdict: Optional[str]
    pooled_clustering_flags: list[str]
    pass_count_full: int  # pass_full = stats AND clustering
    pass_count_stats_only: int  # backward-compat (Phase 9 P2 metric)
    is_survivor: bool  # passes_full >= min_pass_folds
    summary: dict


# ─── Core evaluator ─────────────────────────────────────────────────────
def evaluate_cell_with_trades(
    cell_id: str,
    cell_evaluator: EvaluatorWithTrades,
    folds: list[tuple[pd.Timestamp, pd.Timestamp]],
    *,
    pair: Optional[str] = None,
    target_wr: float = 0.5,
    min_n_per_fold: int = 5,
    min_pass_folds: int = 2,
    require_positive_ev: bool = True,
) -> WalkForwardWithTradesResult:
    """Walk-forward over folds, preserve trades, run per-fold + pooled clustering.

    Mirrors the gate semantics of ``walk_forward_scanner.evaluate_cell_walk_forward``
    (n-scaled Wilson, EV>0, min_n_per_fold) and adds per-fold + pooled
    clustering verdicts via ``detect_repeat_firing``.
    """
    fold_evals: list[FoldEvaluation] = []
    pooled_trades: list[dict] = []
    for idx, (fs, fe) in enumerate(folds):
        n, wins, ev, trades = cell_evaluator(fs, fe)
        wr = wins / n if n > 0 else 0.0
        wlo = wilson_lower_at(wr, n) if n > 0 else 0.0
        gate = n_scaled_wilson_gate(n, target_wr=target_wr) if n > 0 else 1.0

        # Stats gate (parallel to Phase 9 P2)
        stats_reasons: list[str] = []
        passes_stats = True
        if n < min_n_per_fold:
            passes_stats = False
            stats_reasons.append(f"n={n}<{min_n_per_fold}")
        if wlo < gate:
            passes_stats = False
            stats_reasons.append(f"wilson={wlo:.3f}<gate={gate:.3f}")
        if require_positive_ev and ev <= 0:
            passes_stats = False
            stats_reasons.append(f"ev={ev:.3f}<=0")
        if passes_stats:
            stats_reasons.append("PASS")

        # Per-fold clustering (only if enough data)
        cluster_verdict: Optional[str] = None
        cluster_flags: list[str] = []
        clustering_passes: Optional[bool] = None
        if trades and len(trades) >= min_n_per_fold:
            cluster = detect_repeat_firing(trades, pair=pair)
            cluster_verdict = cluster["verdict"]
            cluster_flags = list(cluster.get("flags") or [])
            clustering_passes = cluster_verdict != "artifactual"

        fold_evals.append(FoldEvaluation(
            fold_idx=idx, start=fs, end=fe, n=n, wins=wins, wr=wr,
            wilson_lower=wlo, ev_pip=ev, trades=list(trades or []),
            passes_stats=passes_stats, stats_reasons=stats_reasons,
            clustering_verdict=cluster_verdict,
            clustering_flags=cluster_flags,
            clustering_passes=clustering_passes,
        ))
        pooled_trades.extend(trades or [])

    # Pooled clustering check (catches single-day artifact that splits across folds)
    pooled_verdict: Optional[str] = None
    pooled_flags: list[str] = []
    if len(pooled_trades) >= min_n_per_fold:
        pooled = detect_repeat_firing(pooled_trades, pair=pair)
        pooled_verdict = pooled["verdict"]
        pooled_flags = list(pooled.get("flags") or [])

    pass_full = sum(1 for f in fold_evals if f.passes_full)
    pass_stats = sum(1 for f in fold_evals if f.passes_stats)
    is_survivor = pass_full >= min_pass_folds

    n_total = sum(f.n for f in fold_evals)
    wins_total = sum(f.wins for f in fold_evals)
    pooled_wr = wins_total / n_total if n_total > 0 else 0.0
    pooled_wilson = wilson_lower_at(pooled_wr, n_total) if n_total > 0 else 0.0
    avg_ev = (
        sum(f.ev_pip * f.n for f in fold_evals) / n_total
        if n_total > 0 else 0.0
    )
    ev_per_fold = [f.ev_pip for f in fold_evals]
    ev_std = _stddev(ev_per_fold) if len(ev_per_fold) > 1 else 0.0

    return WalkForwardWithTradesResult(
        cell_id=cell_id,
        folds=fold_evals,
        pooled_trades=pooled_trades,
        pooled_clustering_verdict=pooled_verdict,
        pooled_clustering_flags=pooled_flags,
        pass_count_full=pass_full,
        pass_count_stats_only=pass_stats,
        is_survivor=is_survivor,
        summary={
            "n_total": n_total,
            "pooled_wr": pooled_wr,
            "pooled_wilson_lower": pooled_wilson,
            "avg_ev_pip": avg_ev,
            "ev_std_across_folds": ev_std,
            "pass_count_full": pass_full,
            "pass_count_stats_only": pass_stats,
            "min_pass_folds": min_pass_folds,
            "pooled_clustering_verdict": pooled_verdict,
            "pooled_clustering_flags": pooled_flags,
        },
    )


def walk_forward_with_clustering(
    cell_id: str,
    cell_evaluator: EvaluatorWithTrades,
    df_index: pd.DatetimeIndex,
    *,
    pair: Optional[str] = None,
    holdout_total_days: int = 270,
    target_wr: float = 0.5,
    min_n_per_fold: int = 5,
    min_pass_folds: int = 2,
    require_positive_ev: bool = True,
) -> WalkForwardWithTradesResult:
    """3-fold rolling walk-forward over the last ``holdout_total_days`` with
    per-trade preservation and clustering audit.

    Companion to ``walk_forward_scanner.walk_forward_3fold``: same fold
    geometry, additionally requires the evaluator to return ``(n, wins,
    ev_pip, trades)`` and runs ``detect_repeat_firing`` per fold + pooled.
    """
    folds = split_holdout_folds(df_index, holdout_total_days, n_folds=3)
    return evaluate_cell_with_trades(
        cell_id, cell_evaluator, folds,
        pair=pair, target_wr=target_wr,
        min_n_per_fold=min_n_per_fold,
        min_pass_folds=min_pass_folds,
        require_positive_ev=require_positive_ev,
    )


def _stddev(values: list[float]) -> float:
    if not values:
        return 0.0
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    return math.sqrt(var)
