"""Disk-capacity guard tests (rule:R3, 2026-08-26).

Regression pins for the 2026-08-21 → 08-26 write outage: /var/data filled up,
every SQLite write failed for 5 days, and none of the three safeguards that
should have caught or undone it existed.
"""
from __future__ import annotations

import os
import sqlite3

import pytest

from modules import disk_guard
from modules.candidate_logger import init_candidates_table, prune_candidates
from modules.demo_db import DemoDB


def _make_db(path: str, rows: int = 5) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.executemany("INSERT INTO t (v) VALUES (?)", [(f"row{i}",) for i in range(rows)])
    conn.commit()
    conn.close()


# ── disk_status / footprint ──────────────────────────────────────────


def test_disk_status_reports_usage(tmp_path):
    st = disk_guard.disk_status(str(tmp_path))
    assert st["total_bytes"] > 0
    assert 0.0 <= st["used_pct"] <= 100.0
    assert st["level"] in ("ok", "warn", "critical")


def test_disk_status_accepts_nonexistent_file_in_existing_dir(tmp_path):
    st = disk_guard.disk_status(str(tmp_path / "not_created_yet.db"))
    assert "error" not in st
    assert st["path"] == str(tmp_path)


def test_db_footprint_attributes_backups_separately(tmp_path):
    db = tmp_path / "demo_trades.db"
    _make_db(str(db), rows=50)
    for day in ("20260820", "20260821"):
        _make_db(str(tmp_path / f"demo_trades_backup_{day}.db"), rows=50)

    fp = disk_guard.db_footprint(str(db))
    assert fp["main_bytes"] > 0
    assert len(fp["backups"]) == 2
    assert fp["backups_total_bytes"] > 0
    # Backups must not be double-counted as "other".
    assert fp["other_bytes"] == 0


def test_table_rows_rejects_unsafe_identifier(tmp_path):
    db = tmp_path / "x.db"
    _make_db(str(db))
    with pytest.raises(ValueError):
        disk_guard.table_rows(str(db), "t; DROP TABLE t")


def test_table_rows_returns_none_for_missing_table(tmp_path):
    db = tmp_path / "x.db"
    _make_db(str(db))
    assert disk_guard.table_rows(str(db), "nonexistent") is None


# ── backup_database: rotate BEFORE copy ──────────────────────────────


def test_backup_rotates_before_copying(tmp_path, monkeypatch):
    """The incident's root cause: rotation ran after the copy, so a failing
    copy meant space was never freed. Rotation must happen even when the copy
    is then skipped."""
    db = tmp_path / "demo_trades.db"
    _make_db(str(db), rows=20)
    stale = [tmp_path / f"demo_trades_backup_2026081{i}.db" for i in range(4)]
    for s in stale:
        _make_db(str(s), rows=20)

    # Force the pre-flight to refuse: simulate a full disk.
    monkeypatch.setattr(
        disk_guard, "has_room_for_backup",
        lambda *a, **k: {"ok": False, "need_bytes": 10**9, "free_bytes": 0, "disk": {"used_pct": 100.0}},
    )
    result = DemoDB(db_path=str(db)).backup_database(keep_last=3)

    assert result["status"] == "skipped_low_disk"
    # Space was reclaimed despite the copy never running — this is the fix.
    assert result["rotated"] > 0
    survivors = sorted(p.name for p in tmp_path.glob("demo_trades_backup_*.db"))
    assert len(survivors) == 2  # keep_last - 1, leaving room for today's copy


def test_backup_keeps_full_retention_on_healthy_disk(tmp_path):
    db = tmp_path / "demo_trades.db"
    _make_db(str(db), rows=20)
    for i in range(4):
        _make_db(str(tmp_path / f"demo_trades_backup_2026081{i}.db"), rows=20)

    result = DemoDB(db_path=str(db)).backup_database(keep_last=3)
    assert result["status"] == "ok"
    survivors = sorted(p.name for p in tmp_path.glob("demo_trades_backup_*.db"))
    # 2 retained historical + today's new one == keep_last
    assert len(survivors) == 3


# ── emergency_reclaim ────────────────────────────────────────────────


def test_reclaim_is_noop_on_healthy_disk(tmp_path):
    db = tmp_path / "demo_trades.db"
    _make_db(str(db), rows=10)
    _make_db(str(tmp_path / "demo_trades_backup_20260820.db"), rows=10)

    report = disk_guard.emergency_reclaim(str(db))
    assert report["triggered"] is False
    assert report["removed_backups"] == []
    assert (tmp_path / "demo_trades_backup_20260820.db").exists()


def test_reclaim_prefers_readable_backup_over_newer_truncated_one(tmp_path):
    """A copy interrupted by a full disk is the newest file on disk. Keeping
    it and deleting the intact older copies would destroy the only usable
    backup."""
    db = tmp_path / "demo_trades.db"
    _make_db(str(db), rows=10)
    good = tmp_path / "demo_trades_backup_20260820.db"
    _make_db(str(good), rows=10)
    truncated = tmp_path / "demo_trades_backup_20260821.db"
    truncated.write_bytes(b"SQLite format 3\x00" + b"\x00" * 64)  # partial write
    os.utime(truncated, (10**9, 10**9))
    os.utime(good, (10**9 - 5000, 10**9 - 5000))

    report = disk_guard.emergency_reclaim(str(db), keep_backups=1, force=True)
    assert report["triggered"] is True
    assert good.exists(), "the readable backup must survive"
    assert not truncated.exists(), "the truncated copy must be removed"


def test_reclaim_reports_measured_delta(tmp_path):
    db = tmp_path / "demo_trades.db"
    _make_db(str(db), rows=10)
    _make_db(str(tmp_path / "demo_trades_backup_20260819.db"), rows=200)
    report = disk_guard.emergency_reclaim(str(db), keep_backups=0, force=True)
    assert report["removed_backups"], "stale backup should be removed"
    assert "freed_bytes" in report
    assert report["after"]["free_bytes"] >= report["before"]["free_bytes"]


# ── C1 retention ─────────────────────────────────────────────────────


def test_prune_candidates_deletes_only_old_rows(tmp_path):
    db = str(tmp_path / "demo_trades.db")
    assert init_candidates_table(db)
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO evaluated_candidates (strategy_name, created_at)"
        " VALUES ('old', datetime('now', '-400 days'))"
    )
    conn.execute(
        "INSERT INTO evaluated_candidates (strategy_name, created_at)"
        " VALUES ('fresh', datetime('now', '-1 days'))"
    )
    conn.commit()
    conn.close()

    result = prune_candidates(db, keep_days=180)
    assert result["status"] == "ok"
    assert result["deleted"] == 1
    assert result["remaining"] == 1

    conn = sqlite3.connect(db)
    names = [r[0] for r in conn.execute("SELECT strategy_name FROM evaluated_candidates")]
    conn.close()
    assert names == ["fresh"]


def test_prune_candidates_disabled_when_retention_nonpositive(tmp_path, monkeypatch):
    db = str(tmp_path / "demo_trades.db")
    assert init_candidates_table(db)
    monkeypatch.setenv("C1_RETENTION_DAYS", "0")
    result = prune_candidates(db)
    assert result["status"] == "disabled"
    assert result["deleted"] == 0
