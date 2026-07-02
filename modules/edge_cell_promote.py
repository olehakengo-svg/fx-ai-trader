"""Edge cell matching for Stage-3 direct LIVE promotion.

Spec: knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md
SUPERSEDED 2026-06-07 by:
  knowledge-base/wiki/decisions/edge-cells-stage3-wilson-lo-restoration-2026-06-07.md
  (Wilson_lo threshold restored to Bonferroni-correct 0.55)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


# Wilson_lo promotion threshold (Bonferroni-correct for m≈480, α=1.04e-4).
# Restored 2026-06-07 from interim relaxed 0.30 after 5/12 cells (42%) were
# disabled within 12 trading days under the relaxed gate. New Stage-3
# promotions must satisfy Wilson_lo >= 0.55 in Shadow accumulation before
# promote. Currently-listed EDGE_CELLS below were grandfathered under the
# 0.30 gate; their continuation is governed by per-cell stage state in
# Render KV (system_kv `edge_cell_stage:E*`), not by this constant.
# See edge-cells-stage3-wilson-lo-restoration-2026-06-07.md for evidence.
WILSON_LO_THRESHOLD: float = 0.55


def session_of(ts: datetime) -> str:
    """Return LOCK session bucket for a timestamp."""
    h = ts.astimezone(timezone.utc).hour
    if 0 <= h < 7:
        return "ASN"
    if 7 <= h < 13:
        return "LDN"
    if 13 <= h < 21:
        return "NY"
    return "LATE"


@dataclass(frozen=True)
class EdgeCell:
    cell_id: str
    filters: dict
    base_lot: int = 5000


EDGE_CELLS: list[EdgeCell] = [
    EdgeCell("E1", {"strategy": "dt_bb_rsi_mr", "session": "ASN", "direction": "SELL"}),
    EdgeCell("E2", {"strategy": "session_time_bias", "symbol": "EUR_USD", "session": "LDN", "mtf_gate_action": "live_tier_exempt"}),
    EdgeCell("E3", {"strategy": "dt_bb_rsi_mr", "symbol": "EUR_USD", "direction": "SELL"}),
    EdgeCell("E4", {"strategy": "bb_rsi_reversion", "session": "NY", "direction": "SELL"}),
    EdgeCell("E5", {"strategy": "dt_bb_rsi_mr", "symbol": "GBP_USD", "direction": "SELL"}),
    EdgeCell("E6", {"strategy": "rsk_gbpjpy_reversion", "symbol": "GBP_JPY", "direction": "BUY"}),
    EdgeCell("E7", {"strategy": "dt_bb_rsi_mr", "symbol": "GBP_USD", "session": "ASN"}),
    EdgeCell("E8", {"strategy": "session_time_bias", "symbol": "EUR_USD", "session": "LDN"}),
    EdgeCell("E9", {"strategy": "orb_trap", "symbol": "GBP_USD", "direction": "SELL"}),
    EdgeCell("E10", {"strategy": "wick_imbalance_reversion", "symbol": "GBP_USD", "v2_regime": "no_go"}),
    EdgeCell("E11", {"strategy": "dt_bb_rsi_mr", "session": "NY", "direction": "SELL"}),
    EdgeCell("E12", {"strategy": "sr_anti_hunt_bounce", "symbol": "EUR_JPY"}),
]

LADDER_LOTS = {1: 5000, 2: 7500, 3: 10000}
DISABLED_STAGE = 0

# Code-level kill-switch for individual cells (rule:R2 止血). Cells listed here
# return lot=0 regardless of their Render KV `edge_cell_stage:E*` value — the KV
# getter defaults to stage "1" when the key is missing, so a lost/reset KV would
# silently re-arm a cell at 5000u; this constant pins the OFF state in code.
# lot=0 removes the force-live override only: the trade falls through to its
# normal tier resolution (for session_time_bias EUR_USD that is
# _UNIVERSAL_SENTINEL → is_shadow=True enforced, post 9e508ee2 A2 PAIR_PROMOTED
# removal — no OANDA transmission). Cells remain in EDGE_CELLS and demo_trader
# tags edge_cell_id by match eligibility (not lot>0), so shadow observations
# stay attributed (data継続, watchdog visibility) and the cell stays in the
# registry for future re-promotion. Re-enable only after Shadow
# Wilson_lo >= 0.55 (see WILSON_LO_THRESHOLD) + pre-reg LOCK (R1).
#   E8 (session_time_bias EUR_USD LDN broad): disabled 2026-06-25 —
#     Live N=8 WR38% EV=-3.51p (tot -28p) / shadow N=10 EV=-2.10p, both negative.
#     KV stage=0 since 2026-06-04; this pins it against the default="1" reset.
#     E2 (live_tier_exempt subset, Live EV≒+0.26) は据え置き。
#     ref: knowledge-base/wiki/decisions/edge-cell-e8-demote-2026-06-25.md
#   E10 (wick_imbalance_reversion GBP_USD): disabled 2026-07-02 (rule:R2) —
#     30d Live via E10 force-live: N=9 WR=22.2% (2W/7L) -52.5pip (prod trades
#     API 2026-07-02). Pre-reg forensic 2026-06-22 independently identified
#     E10 as the single dominant live loser (n=9 -50.0p; 9/9 losers fired at
#     d1_label in {0,-1} = knife-catching). The edge-cell watchdog would have
#     auto-demoted this (Live N>=10 EV<0) had it not been dead on the
#     API_AUTH_TOKEN gap. Non-cell PAIR_PROMOTED wick fills stay live
#     (30d n=3 +5.6p). Successor: D1-gated continuation variant via its own
#     R1 pipeline (wick-imbalance-gbpusd-continuation-pre-reg-2026-06-22).
#     ref: knowledge-base/wiki/decisions/live-bleeder-demotions-2026-07-02.md
DISABLED_CELLS: frozenset[str] = frozenset({"E8", "E10"})


def match(
    *,
    strategy: str,
    symbol: str,
    entry_time: datetime,
    direction: str,
    v2_regime: str = "",
    mtf_gate_action: str = "",
) -> Optional[EdgeCell]:
    """Return first matching cell (priority E1 > E2 > ... > E12) or None."""
    sess = session_of(entry_time)
    attrs = {
        "strategy": strategy,
        "symbol": symbol,
        "session": sess,
        "direction": direction,
        "v2_regime": v2_regime,
        "mtf_gate_action": mtf_gate_action,
    }
    for cell in EDGE_CELLS:
        if all(attrs.get(k) == v for k, v in cell.filters.items()):
            return cell
    return None


def get_cell_lot(cell_id: str, demo_db) -> int:
    """Read ladder stage from system_kv and return units. 0 means disabled.

    Global kill-switch: EDGE_CELLS_GLOBAL_DISABLED=1 forces units=0 for all cells.
    Used as the emergency stop while the watchdog is being fixed (hot-fix 2026-05-26).
    """
    if os.environ.get("EDGE_CELLS_GLOBAL_DISABLED", "0") == "1":
        return 0
    if cell_id in DISABLED_CELLS:
        return 0
    key = f"edge_cell_stage:{cell_id}"
    getter = getattr(demo_db, "kv_get", None) or getattr(demo_db, "get_system_kv")
    raw = getter(key, default="1")
    try:
        stage = int(raw)
    except (TypeError, ValueError):
        stage = 1
    if stage == DISABLED_STAGE:
        return 0
    return LADDER_LOTS.get(stage, 5000)
