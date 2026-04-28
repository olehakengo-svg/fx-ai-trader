"""
Power analysis + n-scaled gates for Phase 9 edge discovery.

Phase 8 post-mortem (raw/phase8/aggregation_2026-04-28.md) identified two
structural gate failures:

  D1: ``Wilson_lower_holdout > 0.48`` is statistically infeasible at
      90d × 11 trades/mo holdout (n≈40). At WR=0.60 the Wilson lower bound
      is 0.446 — i.e. the gate is gated by sample size, not by edge.
  D2: Multiple-comparison crush — Bonferroni over a 14,837-cell family
      requires p < 3.4e-6, beyond the physical EV ceiling of FX edges.

This module supplies:

  * ``min_detectable_wr(n, ...)`` — minimum WR an edge must hit to be
    detectable as Wilson_lower > target at the given sample size.
  * ``min_n_for_wilson(...)`` — required n to clear a target Wilson_lower
    floor at a given true WR. Use this to size holdout windows in Phase 9
    pre-reg LOCK so the gate is statistically reachable.
  * ``n_scaled_wilson_gate(n, target_wr, alpha)`` — the Wilson_lower
    threshold a hypothesis must clear, given n. Replaces fixed gates like
    ``> 0.48`` with an n-aware threshold so small-n holdouts don't auto-
    fail real edges.
  * ``bonferroni_per_family(...)`` / ``mde_pre_reg_check(...)`` — utilities
    to size and validate gate calibration before LOCK.

Design point:
  All thresholds are derived from the closed-form Wilson score interval
  (cf. ``tools.sentinel_promotion_scanner.wilson_lower_bound``). No
  Monte-Carlo simulation needed — power is exactly computable.

References:
  raw/phase8/aggregation_2026-04-28.md (D1/D2 root cause)
  knowledge-base/wiki/decisions/phase8-master-2026-04-28.md (Phase 8 plan)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

WILSON_Z_95 = 1.959963984540054


def wilson_lower(wins: int, n: int, z: float = WILSON_Z_95) -> float:
    """95% Wilson score lower bound on the binomial proportion."""
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1.0 + (z * z) / n
    center = phat + (z * z) / (2.0 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)
    return max(0.0, (center - margin) / denom)


def wilson_lower_at(wr: float, n: int, z: float = WILSON_Z_95) -> float:
    """Wilson lower bound assuming the observed WR equals ``wr``."""
    if n <= 0:
        return 0.0
    denom = 1.0 + (z * z) / n
    center = wr + (z * z) / (2.0 * n)
    margin = z * math.sqrt((wr * (1.0 - wr) + (z * z) / (4.0 * n)) / n)
    return max(0.0, (center - margin) / denom)


def n_scaled_wilson_gate(
    n: int,
    target_wr: float = 0.5,
    z: float = WILSON_Z_95,
) -> float:
    """Lower-bound threshold a cell must clear at sample size ``n``.

    Replaces the fixed ``Wilson_lower > 0.48`` gate. The threshold equals
    ``target_wr`` minus the Wilson margin at WR=target_wr. Equivalent to:
    "an unbiased estimator at the threshold would just barely fail the
    test of WR > target_wr at this n".

    At n→∞ the gate approaches ``target_wr``. At small n the gate relaxes
    in proportion to the Wilson margin, so a real edge is not screened
    out by sample size alone.
    """
    if n <= 0:
        return target_wr
    return wilson_lower_at(target_wr, n, z=z)


def min_detectable_wr(
    n: int,
    target_wilson_lower: float = 0.5,
    z: float = WILSON_Z_95,
    tol: float = 1e-4,
) -> float:
    """Smallest true WR whose 95% Wilson lower bound clears the threshold.

    Uses bisection on the monotone ``wilson_lower_at(wr, n)``. Returns the
    WR floor an edge must achieve to be *detectable* at this n. If
    impossible (lower bound at WR=1 is below threshold), returns 1.0.
    """
    if n <= 0:
        return 1.0
    if wilson_lower_at(1.0, n, z=z) < target_wilson_lower:
        return 1.0
    lo, hi = target_wilson_lower, 1.0
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if wilson_lower_at(mid, n, z=z) < target_wilson_lower:
            lo = mid
        else:
            hi = mid
    return hi


def min_n_for_wilson(
    target_wr: float,
    target_wilson_lower: float = 0.5,
    z: float = WILSON_Z_95,
    n_max: int = 100_000,
) -> int:
    """Smallest n such that an edge with true WR=target_wr passes the gate.

    Use during Phase 9 pre-reg LOCK to verify the holdout window can fit
    enough trades to discriminate the hypothesised edge. If the answer is
    1000 and the holdout admits 30 trades, the LOCK is statistically dead
    on arrival — adjust holdout, gate, or RR before commit.
    """
    if target_wr <= target_wilson_lower:
        return n_max
    lo, hi = 1, n_max
    while lo < hi:
        mid = (lo + hi) // 2
        if wilson_lower_at(target_wr, mid, z=z) >= target_wilson_lower:
            hi = mid
        else:
            lo = mid + 1
    return lo


def bonferroni_per_family(
    n_tests_per_family: list[int],
    alpha: float = 0.05,
) -> list[float]:
    """Per-family Bonferroni thresholds.

    Phase 8 lumped 14,837 cells into one family → 3.4e-6 threshold. This
    helper splits the testing budget across independent track families
    (different a-priori hypotheses), giving each a more realistic gate.
    """
    return [alpha / max(1, n) for n in n_tests_per_family]


@dataclass
class PowerCheck:
    """Pre-LOCK feasibility report for a hypothesised edge."""

    n_planned: int
    target_wr: float
    target_wilson_lower: float
    bonferroni_threshold: Optional[float]
    n_required_for_wilson: int
    detectable_wr: float
    feasible_wilson: bool
    feasible_bonferroni: Optional[bool]
    notes: list[str]


def mde_pre_reg_check(
    n_planned: int,
    target_wr: float,
    target_wilson_lower: float = 0.5,
    bonferroni_threshold: Optional[float] = None,
    z: float = WILSON_Z_95,
) -> PowerCheck:
    """Phase 9 pre-reg LOCK power check.

    Given the planned sample size and hypothesised true WR, decide whether
    the proposed gates are statistically reachable. Use this as a hard
    gate in pre-reg LOCK creation: if ``feasible_wilson`` is False, do not
    commit the LOCK — adjust holdout span, target_wr, RR, or thin the cell
    count before locking.
    """
    n_required = min_n_for_wilson(target_wr, target_wilson_lower, z=z)
    detectable = min_detectable_wr(n_planned, target_wilson_lower, z=z)
    feasible_wilson = wilson_lower_at(target_wr, n_planned, z=z) >= target_wilson_lower

    notes: list[str] = []
    if not feasible_wilson:
        notes.append(
            f"Wilson gate infeasible at n={n_planned}: need n≥{n_required} "
            f"or relax target_wilson_lower to ≤{wilson_lower_at(target_wr, n_planned, z=z):.3f}"
        )

    feasible_bonf: Optional[bool] = None
    if bonferroni_threshold is not None:
        wins = round(target_wr * n_planned)
        from research.edge_discovery.significance import binomial_one_sided_p
        p = binomial_one_sided_p(wins, n_planned, 1.0 - target_wr)
        feasible_bonf = p <= bonferroni_threshold
        if not feasible_bonf:
            notes.append(
                f"Bonferroni infeasible: WR={target_wr} n={n_planned} → "
                f"p≈{p:.2e} > threshold {bonferroni_threshold:.2e}"
            )

    return PowerCheck(
        n_planned=n_planned,
        target_wr=target_wr,
        target_wilson_lower=target_wilson_lower,
        bonferroni_threshold=bonferroni_threshold,
        n_required_for_wilson=n_required,
        detectable_wr=detectable,
        feasible_wilson=feasible_wilson,
        feasible_bonferroni=feasible_bonf,
        notes=notes,
    )
