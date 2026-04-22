"""Confidence v2 — Strategy-type aware confidence mapping.

Background
----------
The legacy confidence formula (app.py L2772, each strategy's `conf = min(X, a + score*b)`)
was designed for trend-follow strategies and monotonically maps feature alignment
strength to confidence. This produces the Q4 paradox for MR/pullback strategies where
strong feature alignment (ADX, EMA order, MACD direction, VWAP deviation) is
*inverse edge* — the higher the alignment, the more likely the reversion/pullback fails.

Root-cause audit: `knowledge-base/wiki/sessions/confidence-formula-root-cause-2026-04-22.md`
Full-quant proof: `knowledge-base/wiki/sessions/confidence-q4-full-quant-2026-04-22.md`

Mathematical rationale
----------------------
Assuming linear EV structures per strategy type:

  EV_trend(x)    ≈  α_T + β_T · S_trend(x)        (β_T > 0)
  EV_MR(x)       ≈  α_M - β_M · S_trend(x) + γ_M · S_extreme(x)
  EV_pullback(x) ≈  α_P + β_P · S_trend(x) - δ_P · S_trend(x)²   (non-monotone)

The legacy `conf = a + b · S(x)` is consistent with EV_trend, inverse-consistent
with the trend component of EV_MR, and diverges from EV_pullback at high S_trend.

Anti-trend penalty
------------------
To realign conf with true EV per strategy type, we subtract a penalty term
proportional to the trend component when the strategy is MR/pullback/reversal.
Empirical thresholds are taken from the full-quant Q4 analysis (2026-04-22):

  - ADX_EDGES_Q4 = 31.7  (Q4 starts here in the shadow dataset)
  - ADX_EDGES_Q3 = 25.3  (Q3 starts here — trend regime threshold, Wilder 1978)

Penalty schedule:
  - MR / reversal:  anti_trend = max(0, ADX - 25) * 2.0   (conf pts)
  - pullback:       anti_trend = max(0, ADX - 31) * 3.0   (conf pts, sharper)
  - trend:          anti_trend = 0                         (no change)

At ADX=40:
  - MR:       penalty = 30 pts  (clamps conf ~55 max)
  - pullback: penalty = 27 pts  (clamps conf ~58 max)
  - trend:    no change

At ADX=25 (threshold):
  - MR:       penalty = 0
  - pullback: penalty = 0
  - trend:    no change

Design constraints
------------------
1. Backward compatible: strategies not declaring strategy_type default to "trend"
   → legacy behavior preserved for 40 strategies that are already trend-consistent.
2. Deterministic & pure: no randomness, no I/O, no state.
3. Fail-safe: invalid inputs return legacy conf (penalty=0).
4. Bounded: output always in [conf_min, conf_max] per strategy policy.

Verification
------------
This module is the LIVE formula. Shadow records continue to log legacy `confidence`
under `confidence_legacy` field (added in demo_trader.py) for post-hoc comparison.
"""
from __future__ import annotations
from typing import Optional


# ═══════════════════════════════════════════════════════════════════
# Anti-trend penalty thresholds (from full-quant audit 2026-04-22)
# ═══════════════════════════════════════════════════════════════════

MR_ADX_THRESHOLD: float = 25.0       # Wilder 1978 trend regime start
MR_ADX_SLOPE: float = 2.0             # conf pts per ADX unit above threshold

PULLBACK_ADX_THRESHOLD: float = 31.0  # Q4 ADX edge from shadow dataset
PULLBACK_ADX_SLOPE: float = 3.0       # sharper: strong trend = no pullback develops

# Valid strategy types
VALID_TYPES = frozenset({"trend", "MR", "pullback", "reversal"})


def anti_trend_penalty(strategy_type: str, adx: float) -> float:
    """Return the anti-trend penalty in confidence points.

    For MR/reversal strategies, high ADX is inverse-edge and should REDUCE conf.
    For pullback strategies, very high ADX means no pullback develops — sharper penalty.
    For trend-follow (default), returns 0 (no change).

    Args:
        strategy_type: one of "trend", "MR", "pullback", "reversal".
        adx: current ADX value (Wilder 1978).

    Returns:
        Penalty points to subtract from legacy conf (always >= 0).
    """
    if strategy_type not in VALID_TYPES:
        return 0.0
    try:
        adx_f = float(adx)
    except (TypeError, ValueError):
        return 0.0
    if adx_f <= 0:
        return 0.0

    if strategy_type in ("MR", "reversal"):
        return max(0.0, adx_f - MR_ADX_THRESHOLD) * MR_ADX_SLOPE
    if strategy_type == "pullback":
        return max(0.0, adx_f - PULLBACK_ADX_THRESHOLD) * PULLBACK_ADX_SLOPE
    # "trend"
    return 0.0


def apply_penalty(
    legacy_conf: int,
    strategy_type: str,
    adx: float,
    conf_min: int = 25,
    conf_max: int = 92,
) -> int:
    """Apply anti-trend penalty to legacy conf and clamp.

    Args:
        legacy_conf: conf computed by the strategy's existing formula.
        strategy_type: see anti_trend_penalty().
        adx: ADX value.
        conf_min: lower bound (default 25 matches legacy scalp floor).
        conf_max: upper bound (default 92 matches legacy daytrade ceiling).

    Returns:
        Adjusted conf in [conf_min, conf_max].
    """
    try:
        base = int(legacy_conf)
    except (TypeError, ValueError):
        return conf_min
    penalty = int(round(anti_trend_penalty(strategy_type, adx)))
    adjusted = base - penalty
    if adjusted < conf_min:
        return conf_min
    if adjusted > conf_max:
        return conf_max
    return adjusted


def conf_breakdown(
    legacy_conf: int,
    strategy_type: str,
    adx: float,
) -> dict:
    """Return an explainability breakdown (for logs / diagnostics).

    Usage: include in Candidate.reasons when conf_v2 differs from legacy_conf.
    """
    penalty = anti_trend_penalty(strategy_type, adx)
    adjusted = apply_penalty(legacy_conf, strategy_type, adx)
    return {
        "strategy_type": strategy_type,
        "legacy_conf": int(legacy_conf),
        "adx": round(float(adx), 1) if adx is not None else None,
        "anti_trend_penalty": round(penalty, 2),
        "conf_v2": adjusted,
        "delta": adjusted - int(legacy_conf),
    }
