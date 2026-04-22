"""Confidence Q4 Gate — transition safety net during confidence_v2 rollout.

Purpose
-------
Pure classifier that identifies (strategy × conf_Q=Q4) cells with statistically
confirmed negative Kelly and shadows them. Used as a belt-and-suspenders overlay
on top of the confidence_v2 formula rewrite, covering the 2-4 week period where
v2 behavior has not yet accumulated enough trades for independent validation.

Binding pre-registration
------------------------
Source: `knowledge-base/wiki/sessions/confidence-q4-full-quant-2026-04-22.md` §7
Gate rule (all conditions AND):
  - Kelly_full < 0
  - Wilson 95% upper < BEV_WR
  - N ≥ 15

Cells passing the gate (all 4 SHADOW verdicts):
  - bb_rsi_reversion   conf > 69  (Kelly=-46.9%, EV=-2.48pip)
  - ema_cross          conf > 69  (Kelly=-53.9%, EV=-5.84pip)
  - ema_trend_scalp    conf > 69  (Kelly=-32.3%, EV=-2.47pip)
  - fib_reversal       conf > 69  (Kelly=-54.6%, EV=-2.64pip)

Effect estimate: +572.7 pip/month recovery (Shadow observation).

Lifecycle
---------
This module is INTENTIONALLY transitional. It will be deprecated once:
  1. confidence_v2 accumulates N>=50 post-rewrite trades per gated strategy, AND
  2. Per-strategy Kelly improvement is verified (new Kelly > -5%).

Planned removal: ~2026-06-03 (after 6-week confidence_v2 observation window).

Design constraints
------------------
- Pure function, no I/O, no state.
- Fail-closed: errors return "not gated" (prefer live trading on ambiguity —
  the confidence_v2 fix is the primary defense, this is only the safety net).
- Single decision point: `should_shadow(entry_type, confidence) -> bool`.
"""
from __future__ import annotations
from typing import Optional


# Conf threshold (Q4 lower edge, binding from prereg-6-prime)
Q4_CONF_THRESHOLD: float = 69.0

# Strategies with Kelly<0 AND Wilson_hi<BEV AND N>=15 in shadow data (2026-04-22)
Q4_GATED_STRATEGIES = frozenset({
    "bb_rsi_reversion",
    "ema_cross",
    "ema_trend_scalp",
    "fib_reversal",
})


def should_shadow(entry_type: str, confidence: float) -> bool:
    """Return True if (strategy × conf) falls in a Q4-gated cell.

    Callers should force the trade to Shadow-only (is_shadow=1) on True.
    The strategy still records the signal — only live execution is blocked.

    Args:
        entry_type: Strategy name (e.g. "bb_rsi_reversion").
        confidence: Confidence score (0-100).

    Returns:
        True if the trade should be shadow-only per the Q4 gate.
    """
    if not entry_type or entry_type not in Q4_GATED_STRATEGIES:
        return False
    try:
        conf_f = float(confidence)
    except (TypeError, ValueError):
        return False
    return conf_f > Q4_CONF_THRESHOLD


def gate_reason(entry_type: str, confidence: float) -> Optional[str]:
    """Return a human-readable reason when gated, else None."""
    if not should_shadow(entry_type, confidence):
        return None
    return (
        f"Q4_GATE: {entry_type} conf={confidence:.0f} > {Q4_CONF_THRESHOLD:.0f} "
        f"(full-quant Kelly<0 + Wilson_hi<BEV + N>=15, 2026-04-22)"
    )
