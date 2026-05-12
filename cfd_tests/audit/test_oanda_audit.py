import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from cfd_trader.audit.oanda_audit import (
    init_db,
    record_entry,
    query_entries,
    query_live,
    query_shadow,
    query_unrouted,
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


def test_broker_trade_id_column_added_and_indexed(tmp_db: Path) -> None:
    """broker_trade_id must exist as TEXT and be indexed."""
    conn = sqlite3.connect(str(tmp_db))
    cols = {r[1]: r[2] for r in conn.execute("PRAGMA table_info(oanda_audit)").fetchall()}
    assert "broker_trade_id" in cols
    assert cols["broker_trade_id"].upper() == "TEXT"
    idx_names = {r[1] for r in conn.execute("PRAGMA index_list(oanda_audit)").fetchall()}
    assert "idx_oanda_audit_broker_id" in idx_names


def test_record_with_broker_trade_id_round_trip(tmp_db: Path) -> None:
    """A LIVE entry with broker_trade_id round-trips through query_entries."""
    record_entry(
        str(tmp_db),
        OandaAuditEntry(
            ts="2026-05-12T01:00:00Z", instrument="SPX500_USD",
            strategy_name="orb_ny_open_short", bridge_status="filled",
            side="short", units=1, signal_price=5000.0, entry_price=5000.0,
            is_shadow=0, mode="LIVE", broker_trade_id="MT5#84212391",
        ),
    )
    rows = query_entries(str(tmp_db), {"broker_trade_id": "MT5#84212391"})
    assert len(rows) == 1
    assert rows[0].broker_trade_id == "MT5#84212391"
    assert rows[0].is_shadow == 0


def test_query_live_requires_broker_trade_id(tmp_db: Path) -> None:
    """query_live MUST exclude is_shadow=0 rows whose broker_trade_id is missing.

    This is the strict-separation contract from feedback memory:
    is_shadow=0 alone is not sufficient for "Live". An order that the
    broker rejected (bridge_status='rejected', broker_trade_id NULL)
    must NOT count toward Live N.
    """
    common = dict(
        instrument="SPX500_USD", strategy_name="s",
        side="long", units=1, signal_price=5000.0, entry_price=5000.0,
    )
    # 1: real LIVE — broker accepted, ticket present
    record_entry(str(tmp_db), OandaAuditEntry(
        ts="2026-05-12T00:00:00Z", bridge_status="filled",
        is_shadow=0, mode="LIVE", broker_trade_id="MT5#1",
        **common,
    ))
    # 2: LIVE intent but broker rejected — is_shadow=0 but NULL ticket
    record_entry(str(tmp_db), OandaAuditEntry(
        ts="2026-05-12T00:01:00Z", bridge_status="rejected",
        is_shadow=0, mode="LIVE", broker_trade_id=None,
        **common,
    ))
    # 3: LIVE intent, bridge dropped — is_shadow=0 but empty-string ticket
    record_entry(str(tmp_db), OandaAuditEntry(
        ts="2026-05-12T00:02:00Z", bridge_status="sent",
        is_shadow=0, mode="LIVE", broker_trade_id="",
        **common,
    ))
    # 4: SHADOW — must not appear in either Live or Unrouted
    record_entry(str(tmp_db), OandaAuditEntry(
        ts="2026-05-12T00:03:00Z", bridge_status="filled",
        is_shadow=1, mode="SHADOW", broker_trade_id=None,
        **common,
    ))

    live = query_live(str(tmp_db))
    shadow = query_shadow(str(tmp_db))
    unrouted = query_unrouted(str(tmp_db))

    assert {e.broker_trade_id for e in live} == {"MT5#1"}
    assert {e.is_shadow for e in shadow} == {1}
    assert len(shadow) == 1
    # Both the rejected row AND the empty-string row are "unrouted Live intent"
    assert len(unrouted) == 2
    assert all(e.is_shadow == 0 for e in unrouted)
    assert all(e.broker_trade_id in (None, "") for e in unrouted)


def test_existing_db_migrates_to_add_broker_trade_id(tmp_path: Path) -> None:
    """A pre-existing DB without broker_trade_id must migrate on init_db.

    Simulates the production scenario where Phase 2 wrote SHADOW rows
    without the column; we must not lose those rows when adding it.
    """
    db = tmp_path / "legacy.db"
    legacy_create = """
        CREATE TABLE oanda_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL, instrument TEXT NOT NULL,
            strategy_name TEXT NOT NULL, bridge_status TEXT NOT NULL,
            side TEXT NOT NULL, units INTEGER NOT NULL,
            signal_price REAL NOT NULL, entry_price REAL NOT NULL,
            is_shadow INTEGER NOT NULL DEFAULT 0, mode TEXT NOT NULL,
            extra_json TEXT
        );
    """
    with sqlite3.connect(str(db)) as conn:
        conn.executescript(legacy_create)
        conn.execute(
            "INSERT INTO oanda_audit (ts,instrument,strategy_name,bridge_status,"
            "side,units,signal_price,entry_price,is_shadow,mode) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("2026-05-11T14:30:00Z", "SPX500_USD", "orb_ny_open_short",
             "filled", "short", 1, 5000.0, 5000.0, 1, "SHADOW"),
        )

    init_db(str(db))  # must add the new column without losing the row

    rows = query_entries(str(db), {"strategy_name": "orb_ny_open_short"})
    assert len(rows) == 1
    assert rows[0].broker_trade_id is None
    # And it must show up in the shadow bucket, not the live or unrouted bucket
    assert len(query_shadow(str(db))) == 1
    assert len(query_live(str(db))) == 0
    assert len(query_unrouted(str(db))) == 0
