"""Drift check: audit rows referencing strategies absent from the catalog.

Phase 2 reports only. No auto-fix.
"""
from __future__ import annotations

import sqlite3

from cfd_trader.strategies import catalog


_DISTINCT_STRATEGIES_SQL = "SELECT DISTINCT strategy_name FROM oanda_audit"


def find_orphan_strategies(db_path: str) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(_DISTINCT_STRATEGIES_SQL).fetchall()
    audit_names = {r[0] for r in rows}
    registered = set(catalog.STRATEGIES.keys())
    return sorted(audit_names - registered)
