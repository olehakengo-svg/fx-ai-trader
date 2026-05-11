"""Centralized SQL helpers for oanda_audit.

Section 5.D discipline: Live aggregations MUST filter is_shadow=0, Shadow
MUST filter is_shadow=1. Both filters are enforced here so callers cannot
forget. Add new helpers to this file; do NOT inline SQL in other modules.
"""
from __future__ import annotations

import sqlite3

from cfd_trader.audit.oanda_audit import OandaAuditEntry


# Static SQL literals — no runtime string composition (semgrep static-SQL rule).
_SHADOW_WHERE_SQL = (
    "SELECT ts, instrument, strategy_name, bridge_status, side, units, "
    "signal_price, entry_price, is_shadow, mode, extra_json, "
    "exit_ts, exit_price, pnl_point "
    "FROM oanda_audit WHERE is_shadow = 1 AND strategy_name = ?"
)
_LIVE_WHERE_SQL = (
    "SELECT ts, instrument, strategy_name, bridge_status, side, units, "
    "signal_price, entry_price, is_shadow, mode, extra_json, "
    "exit_ts, exit_price, pnl_point "
    "FROM oanda_audit WHERE is_shadow = 0 AND strategy_name = ?"
)
_COUNT_SHADOW_SQL = (
    "SELECT COUNT(*) FROM oanda_audit "
    "WHERE is_shadow = 1 AND strategy_name = ?"
)
_COUNT_LIVE_SQL = (
    "SELECT COUNT(*) FROM oanda_audit "
    "WHERE is_shadow = 0 AND strategy_name = ?"
)


def _rows_to_entries(rows: list[tuple]) -> list[OandaAuditEntry]:
    out = []
    for r in rows:
        out.append(OandaAuditEntry(
            ts=r[0], instrument=r[1], strategy_name=r[2],
            bridge_status=r[3], side=r[4], units=r[5],
            signal_price=r[6], entry_price=r[7], is_shadow=r[8],
            mode=r[9], extra_json=r[10],
            exit_ts=r[11], exit_price=r[12], pnl_point=r[13],
        ))
    return out


def shadow_trades_for(db_path: str, *, strategy_name: str) -> list[OandaAuditEntry]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(_SHADOW_WHERE_SQL, (strategy_name,)).fetchall()
    return _rows_to_entries(rows)


def live_trades_for(db_path: str, *, strategy_name: str) -> list[OandaAuditEntry]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(_LIVE_WHERE_SQL, (strategy_name,)).fetchall()
    return _rows_to_entries(rows)


def count_shadow(db_path: str, *, strategy_name: str) -> int:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(_COUNT_SHADOW_SQL, (strategy_name,)).fetchone()
    return int(row[0])


def count_live(db_path: str, *, strategy_name: str) -> int:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(_COUNT_LIVE_SQL, (strategy_name,)).fetchone()
    return int(row[0])
