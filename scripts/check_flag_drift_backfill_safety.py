#!/usr/bin/env python3
"""Dry-run safety check for the 2026-05-11 FLAG_DRIFT backfill."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


CUTOFF = "2026-04-08T00:00:00"


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def analyze_db(db_path: str) -> dict:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(db_path)

    with _connect(str(path)) as conn:
        audit_present = _table_exists(conn, "oanda_audit")
        q1_row = conn.execute(
            """SELECT COUNT(*) AS n,
                      ROUND(COALESCE(SUM(pnl_pips), 0), 4) AS pnl_total,
                      ROUND(COALESCE(AVG(pnl_pips), 0), 6) AS pnl_avg
               FROM demo_trades
               WHERE entry_time >= ?
                 AND instrument != 'XAU_USD'
                 AND is_shadow = 0
                 AND (oanda_trade_id IS NULL OR oanda_trade_id = '')""",
            (CUTOFF,),
        ).fetchone()
        q1 = dict(q1_row)

        if audit_present:
            q2_rows = conn.execute(
                """SELECT COALESCE(a.bridge_status, 'NULL') AS bridge_status,
                          COUNT(*) AS n
                   FROM demo_trades t
                   LEFT JOIN oanda_audit a ON a.demo_trade_id = t.trade_id
                   WHERE t.entry_time >= ?
                     AND t.instrument != 'XAU_USD'
                     AND t.is_shadow = 0
                     AND (t.oanda_trade_id IS NULL OR t.oanda_trade_id = '')
                   GROUP BY a.bridge_status
                   ORDER BY bridge_status""",
                (CUTOFF,),
            ).fetchall()
            q3_rows = conn.execute(
                """SELECT t.trade_id, t.entry_type, t.instrument, t.entry_time,
                          t.oanda_trade_id, a.bridge_status,
                          a.oanda_trade_id AS audit_oanda_id
                   FROM demo_trades t
                   JOIN oanda_audit a ON a.demo_trade_id = t.trade_id
                   WHERE t.entry_time >= ?
                     AND t.instrument != 'XAU_USD'
                     AND t.is_shadow = 0
                     AND (t.oanda_trade_id IS NULL OR t.oanda_trade_id = '')
                     AND a.bridge_status = 'filled'
                   ORDER BY t.entry_time, t.trade_id
                   LIMIT 50""",
                (CUTOFF,),
            ).fetchall()
            q3_count = conn.execute(
                """SELECT COUNT(*) AS n
                   FROM demo_trades t
                   JOIN oanda_audit a ON a.demo_trade_id = t.trade_id
                   WHERE t.entry_time >= ?
                     AND t.instrument != 'XAU_USD'
                     AND t.is_shadow = 0
                     AND (t.oanda_trade_id IS NULL OR t.oanda_trade_id = '')
                     AND a.bridge_status = 'filled'""",
                (CUTOFF,),
            ).fetchone()["n"]
        else:
            q2_rows = [{"bridge_status": "NO_OANDA_AUDIT_TABLE", "n": q1["n"]}]
            q3_rows = []
            q3_count = 0

        q3_sample = [dict(row) for row in q3_rows]
        q3 = {"n": int(q3_count), "sample": q3_sample}
        return {
            "db_path": str(path),
            "cutoff": CUTOFF,
            "audit_table_present": audit_present,
            "q1": q1,
            "q2": [dict(row) for row in q2_rows],
            "q3": q3,
            "verdict": "UNSAFE" if q3["n"] > 0 else "SAFE",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path", help="Path to demo_trades SQLite DB")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args(argv)

    result = analyze_db(args.db_path)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 1 if result["verdict"] == "UNSAFE" else 0


if __name__ == "__main__":
    sys.exit(main())
