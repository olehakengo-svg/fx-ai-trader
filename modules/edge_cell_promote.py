"""Edge cell matching for Stage-3 direct LIVE promotion.

Spec: knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


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
    """Read ladder stage from system_kv and return units. 0 means disabled."""
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
