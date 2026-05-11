#!/usr/bin/env python3
"""Dry-run safety check for the 2026-05-11 FORCE_DEMOTED live-leak backfill."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.demo_db import DemoDB


CUTOFF = "2026-04-08T00:00:00"
RULE_TS = "2026-05-11T00:00:00"


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


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row["name"] == column for row in conn.execute(f"PRAGMA table_info({table})"))  # nosem


def analyze_db(db_path: str) -> dict:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(db_path)

    force_demoted = DemoDB._force_demoted_entry_types()
    placeholders = ",".join(["?"] * len(force_demoted))
    with _connect(str(path)) as conn:
        audit_present = _table_exists(conn, "oanda_audit")
        marker_present = _column_exists(conn, "demo_trades", "force_demoted_live_leak")
        marker_clean = "AND COALESCE(force_demoted_live_leak, 0) = 0" if marker_present else ""
        params = (CUTOFF, *force_demoted)
        q1_row = conn.execute(
            f"""SELECT COUNT(*) AS n,
                       ROUND(COALESCE(SUM(pnl_pips), 0), 4) AS pnl_total,
                       ROUND(COALESCE(AVG(pnl_pips), 0), 6) AS pnl_avg,
                       MIN(entry_time) AS earliest,
                       MAX(entry_time) AS latest
                FROM demo_trades
                WHERE entry_time >= ?
                  AND instrument != 'XAU_USD'
                  AND is_shadow = 0
                  AND entry_type IN ({placeholders})
                  {marker_clean}""",
            params,
        ).fetchone()
        q1 = dict(q1_row)

        q2_rows = conn.execute(
            """SELECT date(entry_time) AS d, COUNT(*) AS n,
                      ROUND(COALESCE(SUM(pnl_pips), 0), 4) AS pnl
               FROM demo_trades
               WHERE entry_time >= ?
                 AND entry_type = 'vwap_mean_reversion'
                 AND is_shadow = 0
                 AND instrument != 'XAU_USD'
               GROUP BY date(entry_time)
               ORDER BY d""",
            (CUTOFF,),
        ).fetchall()

        q3_rows = conn.execute(
            f"""SELECT entry_type, mode, COUNT(*) AS n
                FROM demo_trades
                WHERE entry_time >= ?
                  AND is_shadow = 0
                  AND instrument != 'XAU_USD'
                  AND entry_type IN ({placeholders})
                GROUP BY entry_type, mode
                ORDER BY entry_type, n DESC""",
            params,
        ).fetchall()

        if audit_present:
            unsafe_count = conn.execute(
                f"""SELECT COUNT(DISTINCT t.trade_id) AS n
                    FROM demo_trades t
                    LEFT JOIN oanda_audit a ON a.demo_trade_id = t.trade_id
                    WHERE t.entry_time >= ?
                      AND t.instrument != 'XAU_USD'
                      AND t.is_shadow = 0
                      AND t.entry_type IN ({placeholders})
                      AND t.entry_time >= ?
                      AND (
                        (t.oanda_trade_id IS NOT NULL AND t.oanda_trade_id != '')
                        OR a.bridge_status = 'filled'
                      )""",
                (CUTOFF, *force_demoted, RULE_TS),
            ).fetchone()["n"]
        else:
            unsafe_count = conn.execute(
                f"""SELECT COUNT(*) AS n
                    FROM demo_trades
                    WHERE entry_time >= ?
                      AND instrument != 'XAU_USD'
                      AND is_shadow = 0
                      AND entry_type IN ({placeholders})
                      AND entry_time >= ?
                      AND oanda_trade_id IS NOT NULL
                      AND oanda_trade_id != ''""",
                (CUTOFF, *force_demoted, RULE_TS),
            ).fetchone()["n"]

        q4_rows = conn.execute(
            f"""SELECT entry_type,
                       SUM(CASE WHEN oanda_trade_id != '' THEN 1 ELSE 0 END) AS with_oanda_id,
                       SUM(CASE WHEN oanda_trade_id = '' OR oanda_trade_id IS NULL THEN 1 ELSE 0 END) AS without_oanda_id
                FROM demo_trades
                WHERE entry_time >= ?
                  AND instrument != 'XAU_USD'
                  AND is_shadow = 0
                  AND entry_type IN ({placeholders})
                GROUP BY entry_type""",
            params,
        ).fetchall()

        return {
            "db_path": str(path),
            "cutoff": CUTOFF,
            "rule_ts": RULE_TS,
            "force_demoted_count": len(force_demoted),
            "audit_table_present": audit_present,
            "marker_column_present": marker_present,
            "q1": q1,
            "q2_vwap_by_day": [dict(row) for row in q2_rows],
            "q3_mode_distribution": [dict(row) for row in q3_rows],
            "q4": {
                "oanda_id_distribution": [dict(row) for row in q4_rows],
                "unsafe_post_rule_fill_count": int(unsafe_count),
            },
            "verdict": "UNSAFE" if unsafe_count > 0 else "SAFE",
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
