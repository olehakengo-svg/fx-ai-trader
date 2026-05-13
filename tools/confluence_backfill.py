#!/usr/bin/env python3
"""Dry-run-first backfill for demo_trades confluence observation tags."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cross_pair_confluence import CACHE_DIR, compute_confluence  # noqa: E402

UPDATE_SQL = "UPDATE demo_trades SET confluence_score = ?, confluence_details = ? WHERE trade_id = ?"


def _columns(con: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in con.execute("PRAGMA table_info(demo_trades)").fetchall()}


def run_backfill(
    db_path: str,
    apply: bool = False,
    chunk_size: int = 500,
    cache_dir: str | Path = CACHE_DIR,
) -> dict:
    path = Path(db_path)
    cache: dict[str, pd.DataFrame] = {}
    updates: list[dict] = []
    with sqlite3.connect(path) as con:
        cols = _columns(con)
        missing = {"confluence_score", "confluence_details"} - cols
        if missing:
            raise RuntimeError(f"demo_trades missing columns: {','.join(sorted(missing))}")
        rows = con.execute(
            """
            SELECT trade_id, instrument, direction, entry_time
            FROM demo_trades
            WHERE (confluence_score IS NULL OR confluence_score = '')
              AND instrument != 'XAU_USD'
            ORDER BY entry_time, trade_id
            """
        ).fetchall()
        for trade_id, instrument, direction, entry_time in rows:
            result = compute_confluence(instrument, direction, entry_time, cache_dir=Path(cache_dir), cache=cache)
            updates.append(
                {
                    "trade_id": trade_id,
                    "instrument": instrument,
                    "direction": direction,
                    "entry_time": entry_time,
                    "confluence_score": result.score,
                    "confluence_details": result.details_json(),
                }
            )
        if apply and updates:
            for start in range(0, len(updates), chunk_size):
                chunk = updates[start : start + chunk_size]
                con.executemany(
                    UPDATE_SQL,
                    [
                        (u["confluence_score"], u["confluence_details"], u["trade_id"])
                        for u in chunk
                    ],
                )
            con.commit()
    return {
        "mode": "apply" if apply else "dry-run",
        "db_path": str(path),
        "update_sql": UPDATE_SQL,
        "would_update": len(updates),
        "updates": updates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(ROOT / "data" / "demo_trades.db"))
    parser.add_argument("--apply", action="store_true", help="write updates; default is dry-run")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--cache-dir", default=str(CACHE_DIR))
    args = parser.parse_args()
    result = run_backfill(args.db, apply=args.apply, chunk_size=args.chunk_size, cache_dir=args.cache_dir)
    printable = dict(result)
    printable["updates"] = result["updates"][:5]
    print(json.dumps(printable, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
