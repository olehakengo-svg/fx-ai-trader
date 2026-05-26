#!/usr/bin/env python3
"""Add demo_trades.edge_cell_id for Stage-3 edge-cell promotion.

Idempotent: safe to re-run against existing Render disk DBs.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


def migrate(db_path: str | Path) -> bool:
    conn = sqlite3.connect(str(db_path))
    try:
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(demo_trades)").fetchall()
        }
        changed = False
        if "edge_cell_id" not in cols:
            conn.execute("ALTER TABLE demo_trades ADD COLUMN edge_cell_id TEXT DEFAULT ''")
            changed = True
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_edge_cell ON demo_trades(edge_cell_id)"
        )
        conn.commit()
        return changed
    finally:
        conn.close()


def main() -> int:
    db_path = os.environ.get("DB_PATH", "demo_trades.db")
    try:
        changed = migrate(db_path)
    except sqlite3.Error as exc:
        print(f"[edge_cell_id_migration] ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "[edge_cell_id_migration] "
        f"{'added edge_cell_id' if changed else 'edge_cell_id already present'} "
        f"for {db_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
