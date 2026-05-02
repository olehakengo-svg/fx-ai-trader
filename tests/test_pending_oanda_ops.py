"""pending_oanda_ops persistence tests (audit 2026-05-01 P0-6).

Confirms:
  1. DAO round-trips: create -> mark_done / mark_failed
  2. recover_pending_ops marks rows older than 5 min as 'startup_orphan'
  3. recover_pending_ops leaves fresh rows alone
  4. Empty database returns zeros without raising
"""
from __future__ import annotations

import os
import tempfile
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from modules.demo_db import DemoDB
from modules.oanda_bridge import OandaBridge


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DemoDB(db_path=path)
    os.unlink(path)


def test_pending_op_create_then_done(db):
    pid = db.pending_op_create(
        "open", "DEMO_1", instrument="USD_JPY", direction="BUY",
        units=1000, sl=149.5, tp=151.0,
    )
    assert pid > 0
    rows = db.pending_op_list("pending")
    assert len(rows) == 1
    assert rows[0]["op_type"] == "open"
    assert rows[0]["demo_trade_id"] == "DEMO_1"
    assert rows[0]["status"] == "pending"

    db.pending_op_mark_done(pid, oanda_trade_id="OANDA_42")
    pending_after = db.pending_op_list("pending")
    assert pending_after == []
    done = db.pending_op_list("done")
    assert len(done) == 1
    assert done[0]["oanda_trade_id"] == "OANDA_42"


def test_pending_op_mark_failed_records_attempts_and_error(db):
    pid = db.pending_op_create("open", "DEMO_2", direction="SELL", units=1000)
    db.pending_op_mark_failed(pid, "rate_limited", attempts=3)
    failed = db.pending_op_list("failed")
    assert len(failed) == 1
    assert failed[0]["attempts"] == 3
    assert "rate_limited" in failed[0]["last_error"]


def test_recover_pending_ops_empty(db):
    bridge = OandaBridge(db=db)
    summary = bridge.recover_pending_ops()
    assert summary == {"pending": 0, "stale_marked_failed": 0, "failed": 0}


def test_recover_pending_ops_fresh_row_stays_pending(db):
    db.pending_op_create("open", "DEMO_FRESH")
    bridge = OandaBridge(db=db)
    summary = bridge.recover_pending_ops()
    assert summary["pending"] == 1
    assert summary["stale_marked_failed"] == 0
    # Still pending — fresh, not orphaned
    assert len(db.pending_op_list("pending")) == 1


def test_recover_pending_ops_marks_old_pending_as_startup_orphan(db):
    pid = db.pending_op_create("open", "DEMO_STALE")
    # Backdate created_at to 10 minutes ago to simulate a row that
    # survived a previous process death.
    stale_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    with db._lock:  # noqa: SLF001
        with db._safe_conn() as conn:
            conn.execute(
                "UPDATE pending_oanda_ops SET created_at=? WHERE id=?",
                (stale_ts, pid),
            )
            conn.commit()

    bridge = OandaBridge(db=db)
    summary = bridge.recover_pending_ops()
    assert summary["stale_marked_failed"] == 1
    failed = db.pending_op_list("failed")
    assert any("startup_orphan" in r.get("last_error", "") for r in failed)
    assert db.pending_op_list("pending") == []


def test_recover_pending_ops_handles_db_error_gracefully(db):
    bridge = OandaBridge(db=db)
    with patch.object(db, "pending_op_list", side_effect=RuntimeError("boom")):
        summary = bridge.recover_pending_ops()
    # Must not raise; returns zeroed dict.
    assert summary == {"pending": 0, "stale_marked_failed": 0, "failed": 0}
