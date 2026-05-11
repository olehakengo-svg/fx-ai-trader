"""shadow.state: per-strategy cursor (last-processed candle timestamp)."""
from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from cfd_trader.shadow.state import (
    init_state_table, get_cursor, advance_cursor,
)


def test_init_state_table_creates_schema(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_state_table(str(db))
    conn = sqlite3.connect(str(db))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(shadow_state)").fetchall()}
    assert {"strategy_name", "last_processed_ts", "updated_at"}.issubset(cols)


def test_get_cursor_returns_none_for_unknown_strategy(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_state_table(str(db))
    assert get_cursor(str(db), "missing") is None


def test_advance_cursor_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_state_table(str(db))
    advance_cursor(str(db), "orb_ny_open_short", "2026-05-11T15:00:00Z")
    assert get_cursor(str(db), "orb_ny_open_short") == "2026-05-11T15:00:00Z"


def test_advance_cursor_idempotent_overwrite(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_state_table(str(db))
    advance_cursor(str(db), "orb_ny_open_short", "2026-05-11T15:00:00Z")
    advance_cursor(str(db), "orb_ny_open_short", "2026-05-11T16:00:00Z")
    assert get_cursor(str(db), "orb_ny_open_short") == "2026-05-11T16:00:00Z"


def test_advance_cursor_rejects_regression(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_state_table(str(db))
    advance_cursor(str(db), "orb_ny_open_short", "2026-05-11T16:00:00Z")
    with pytest.raises(ValueError):
        advance_cursor(str(db), "orb_ny_open_short", "2026-05-11T15:00:00Z")
