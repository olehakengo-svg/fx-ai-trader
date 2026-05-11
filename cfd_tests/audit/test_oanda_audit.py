import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from cfd_trader.audit.oanda_audit import (
    init_db,
    record_entry,
    query_entries,
    OandaAuditEntry,
)


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    db = tmp_path / "test_audit.db"
    init_db(str(db))
    return db


def test_init_db_creates_oanda_audit_with_is_shadow_not_null(tmp_db: Path) -> None:
    conn = sqlite3.connect(str(tmp_db))
    rows = conn.execute("PRAGMA table_info(oanda_audit)").fetchall()
    cols = {r[1]: {"type": r[2], "notnull": r[3], "dflt": r[4]} for r in rows}
    assert "is_shadow" in cols
    assert cols["is_shadow"]["notnull"] == 1
    assert cols["is_shadow"]["dflt"] is not None
    assert int(str(cols["is_shadow"]["dflt"])) == 0


def test_record_and_query_round_trip(tmp_db: Path) -> None:
    e = OandaAuditEntry(
        ts="2026-05-07T12:00:00Z",
        instrument="SPX500_USD",
        strategy_name="dummy_strategy",
        bridge_status="sent",
        side="long",
        units=1,
        signal_price=5000.5,
        entry_price=5000.7,
        is_shadow=1,
        mode="SHADOW",
    )
    record_entry(str(tmp_db), e)
    rows = query_entries(str(tmp_db), {"instrument": "SPX500_USD"})
    assert len(rows) == 1
    assert rows[0].is_shadow == 1
    assert rows[0].bridge_status == "sent"
    assert rows[0].strategy_name == "dummy_strategy"


def test_query_live_only_excludes_shadow(tmp_db: Path) -> None:
    record_entry(
        str(tmp_db),
        OandaAuditEntry(
            ts="2026-05-07T12:00:00Z",
            instrument="SPX500_USD",
            strategy_name="s",
            bridge_status="filled",
            side="long",
            units=1,
            signal_price=5000.0,
            entry_price=5000.0,
            is_shadow=0,
            mode="LIVE",
        ),
    )
    record_entry(
        str(tmp_db),
        OandaAuditEntry(
            ts="2026-05-07T12:01:00Z",
            instrument="SPX500_USD",
            strategy_name="s",
            bridge_status="sent",
            side="long",
            units=1,
            signal_price=5000.0,
            entry_price=5000.0,
            is_shadow=1,
            mode="SHADOW",
        ),
    )
    live = query_entries(str(tmp_db), {"is_shadow": 0})
    assert len(live) == 1
    assert live[0].mode == "LIVE"


def test_init_db_is_idempotent(tmp_path: Path) -> None:
    """Calling init_db twice should not error and should keep new columns."""
    db = tmp_path / "t.db"
    init_db(str(db))
    init_db(str(db))  # second call must not raise
    conn = sqlite3.connect(str(db))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(oanda_audit)").fetchall()}
    assert {"exit_ts", "exit_price", "pnl_point"}.issubset(cols)


def test_record_entry_with_exit_fields(tmp_path: Path) -> None:
    """An entry with exit_ts/exit_price/pnl_point round-trips."""
    db = tmp_path / "t.db"
    init_db(str(db))
    e = OandaAuditEntry(
        ts="2026-05-11T14:30:00Z",
        instrument="SPX500_USD",
        strategy_name="orb_ny_open_short",
        bridge_status="filled",
        side="short",
        units=1,
        signal_price=5400.0,
        entry_price=5400.0,
        is_shadow=1,
        mode="SHADOW",
        extra_json='{"bonferroni_m": 2}',
        exit_ts="2026-05-11T15:30:00Z",
        exit_price=5380.0,
        pnl_point=20.0,
    )
    record_entry(str(db), e)
    rows = query_entries(str(db), {"strategy_name": "orb_ny_open_short"})
    assert len(rows) == 1
    assert rows[0].exit_ts == "2026-05-11T15:30:00Z"
    assert rows[0].exit_price == 5380.0
    assert rows[0].pnl_point == 20.0
