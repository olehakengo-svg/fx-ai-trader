"""shadow_state: per-strategy cursor for catch-up replay.

The cursor is the ISO-8601 UTC timestamp of the LAST processed candle.
The catch-up runner fetches candles with time > cursor.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS shadow_state (
    strategy_name      TEXT PRIMARY KEY,
    last_processed_ts  TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
"""

_UPSERT_SQL = (
    "INSERT INTO shadow_state (strategy_name, last_processed_ts, updated_at) "
    "VALUES (?, ?, ?) "
    "ON CONFLICT(strategy_name) DO UPDATE SET "
    "last_processed_ts = excluded.last_processed_ts, "
    "updated_at = excluded.updated_at"
)

_SELECT_SQL = "SELECT last_processed_ts FROM shadow_state WHERE strategy_name = ?"


def init_state_table(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_CREATE_TABLE_SQL)


def get_cursor(db_path: str, strategy_name: str) -> str | None:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(_SELECT_SQL, (strategy_name,)).fetchone()
    return row[0] if row else None


def advance_cursor(db_path: str, strategy_name: str, new_ts: str) -> None:
    """Advance the cursor. Rejects regression (new_ts must be > current)."""
    current = get_cursor(db_path, strategy_name)
    if current is not None and new_ts <= current:
        raise ValueError(
            f"cursor regression for {strategy_name}: current={current} new={new_ts}"
        )
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(_UPSERT_SQL, (strategy_name, new_ts, now))
