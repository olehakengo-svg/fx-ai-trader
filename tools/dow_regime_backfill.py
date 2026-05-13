#!/usr/bin/env python3
"""Backfill demo_trades.dow_regime from the literal H1 regime classifier.

Dry-run is the default. Use --apply only after reviewing the planned updates.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.regime_classifier import classify_regime  # noqa: E402


UPDATE_SQL = "UPDATE demo_trades SET dow_regime = ? WHERE trade_id = ?"


def run_backfill(
    db_path: str,
    *,
    apply: bool = False,
    chunk_size: int = 1000,
    limit: int | None = None,
) -> dict:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(demo_trades)")}
        if "dow_regime" not in cols:
            raise RuntimeError("demo_trades.dow_regime column is missing")

        sql = (
            "SELECT trade_id, instrument, entry_time "
            "FROM demo_trades "
            "WHERE dow_regime IS NULL "
            "  AND instrument IS NOT NULL AND instrument != '' "
            "  AND entry_time IS NOT NULL AND entry_time != '' "
            "ORDER BY id"
        )
        params: list[Any] = []
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))

        rows = conn.execute(sql, params).fetchall()
        updates: list[dict[str, str]] = []
        classified = 0
        nulls = 0
        errors: list[dict[str, str]] = []

        for row in rows:
            trade_id = row["trade_id"]
            try:
                regime = classify_regime(row["instrument"], pd.Timestamp(row["entry_time"]))
            except Exception as exc:
                regime = None
                errors.append({"trade_id": trade_id, "error": str(exc)})
            if regime is None:
                nulls += 1
                continue
            classified += 1
            updates.append({"trade_id": trade_id, "dow_regime": regime})

        if apply and updates:
            for start in range(0, len(updates), chunk_size):
                chunk = updates[start:start + chunk_size]
                conn.executemany(
                    UPDATE_SQL,
                    [(u["dow_regime"], u["trade_id"]) for u in chunk],
                )
                conn.commit()

        return {
            "mode": "apply" if apply else "dry-run",
            "db_path": str(db_path),
            "rows_examined": len(rows),
            "classified": classified,
            "nulls": nulls,
            "would_update": len(updates),
            "updated": len(updates) if apply else 0,
            "update_sql": UPDATE_SQL,
            "errors": errors,
            "updates": updates,
        }
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="demo_trades.db", help="SQLite demo_trades DB path")
    parser.add_argument("--apply", action="store_true", help="write updates; default is dry-run")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    result = run_backfill(
        args.db,
        apply=bool(args.apply),
        chunk_size=args.chunk_size,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
