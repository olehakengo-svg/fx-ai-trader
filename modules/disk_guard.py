"""Disk-capacity telemetry + guards for the Render persistent disk (rule:R3).

Incident 2026-08-21 → 08-25: the 1 GB ``/var/data`` disk filled up and **every
SQLite write failed for 3.5 days**. The dashboard kept rendering the last
successful state, so the outage looked like a quiet market rather than a
failure (MEMORY ``project_render_disk_full_write_outage_2026_08_25``).

Three structural defects made a full disk unrecoverable *and* invisible:

1. ``DemoDB.backup_database`` copied first and rotated afterwards, so once the
   copy raised ``disk I/O error`` the rotation never ran — the very step that
   would have freed space. Four consecutive days FAILED, leaving no backup.
2. Nothing anywhere measured free space. There was no endpoint, no log line,
   and no alert; the fill was only found by hand.
3. ``evaluated_candidates`` (C1 audit table) has no retention policy and grows
   monotonically.

This module supplies the measurement primitives. The self-healing rotation
lives in ``DemoDB.backup_database``; the alert lives in
``scripts/anomaly_watcher.py``; the readout is ``/api/admin/disk_status``.

Pure functions only — no import-time side effects (lesson: tools/modules are
libraries *and* scripts).
"""
from __future__ import annotations

import glob as _glob_mod
import os
import shutil
import sqlite3
from typing import Any, Optional

# Alert ladder. Chosen from the incident: the fill went from "fine" to
# "every write fails" inside one day, so warn early and leave headroom for one
# full backup copy (a backup is ~1x the live DB).
DISK_WARN_PCT = 75.0
DISK_CRITICAL_PCT = 90.0

# A backup copy needs at least the live DB size; require 15% slack on top so a
# concurrent WAL growth spurt cannot wedge the copy halfway.
BACKUP_HEADROOM_RATIO = 1.15


def disk_status(path: str) -> dict[str, Any]:
    """Return total/used/free bytes + used pct for the filesystem holding ``path``.

    ``path`` may be a file or a directory; the containing directory is used
    when the file does not exist yet.
    """
    probe = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    try:
        usage = shutil.disk_usage(probe)
    except OSError as exc:
        return {"path": probe, "error": str(exc)}
    used_pct = (usage.used / usage.total * 100.0) if usage.total else 0.0
    return {
        "path": probe,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "used_pct": round(used_pct, 2),
        "level": (
            "critical" if used_pct >= DISK_CRITICAL_PCT
            else "warn" if used_pct >= DISK_WARN_PCT
            else "ok"
        ),
    }


def _size_or_zero(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def db_footprint(db_path: str) -> dict[str, Any]:
    """Break the disk consumption down by file so a fill can be attributed.

    Reports the live DB, its WAL/SHM sidecars, every rotated backup, and the
    residual ("other") bytes in the same directory. During the incident the
    dominant term was backups: three retained copies of a DB that had grown
    past a third of the disk.
    """
    db_path = os.path.abspath(db_path)
    db_dir = os.path.dirname(db_path)
    db_basename = os.path.splitext(os.path.basename(db_path))[0]

    main = _size_or_zero(db_path)
    wal = _size_or_zero(db_path + "-wal")
    shm = _size_or_zero(db_path + "-shm")

    backups = []
    for bp in sorted(_glob_mod.glob(os.path.join(db_dir, f"{db_basename}_backup_*.db"))):
        backups.append({"name": os.path.basename(bp), "size_bytes": _size_or_zero(bp)})
    backups_total = sum(b["size_bytes"] for b in backups)

    accounted = {db_path, db_path + "-wal", db_path + "-shm"}
    accounted.update(os.path.join(db_dir, b["name"]) for b in backups)
    other_total = 0
    try:
        for entry in os.scandir(db_dir):
            if entry.is_file() and entry.path not in accounted:
                other_total += entry.stat().st_size
    except OSError:
        other_total = -1

    return {
        "db_path": db_path,
        "main_bytes": main,
        "wal_bytes": wal,
        "shm_bytes": shm,
        "backups": backups,
        "backups_total_bytes": backups_total,
        "other_bytes": other_total,
        "tracked_total_bytes": main + wal + shm + backups_total + max(other_total, 0),
    }


def table_rows(db_path: str, table: str) -> Optional[int]:
    """Row count for ``table``, or None when unreadable (missing table / locked)."""
    if not table.isidentifier():
        raise ValueError(f"unsafe table name: {table!r}")
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        try:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        finally:
            conn.close()
    except Exception:
        return None


def has_room_for_backup(db_path: str, headroom_ratio: float = BACKUP_HEADROOM_RATIO) -> dict[str, Any]:
    """Pre-flight check: is there space for one more full backup copy?

    Returned dict always carries ``ok``; callers must skip the copy when it is
    False rather than letting SQLite fail mid-write.
    """
    status = disk_status(db_path)
    if "error" in status:
        # Cannot measure — do not block the backup on a measurement failure.
        return {"ok": True, "reason": "unmeasurable", "disk": status}
    need = int(_size_or_zero(db_path) * headroom_ratio)
    free = status["free_bytes"]
    return {
        "ok": free >= need,
        "need_bytes": need,
        "free_bytes": free,
        "disk": status,
    }


def _is_readable_sqlite(path: str) -> bool:
    """True when ``path`` opens as SQLite and exposes a non-empty schema.

    Used to avoid retaining a *truncated* backup over an intact older one: a
    copy interrupted by a full disk leaves a partial file whose mtime is the
    newest, so "keep the newest" alone would preserve the broken one.
    """
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        try:
            n = conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0]
            return int(n) > 0
        finally:
            conn.close()
    except Exception:
        return False


def emergency_reclaim(db_path: str, keep_backups: int = 1, force: bool = False) -> dict[str, Any]:
    """Reclaim disk when ``/var/data`` is full enough to block writes (rule:R3).

    Runs at app startup and from ``POST /api/admin/disk_reclaim``. It is a
    **no-op unless the disk is actually under pressure** (used_pct >= critical
    or no room for a backup), so a healthy boot never deletes anything.

    Order matters and is derived from the 2026-08-21 incident:

    1. Delete stale backup copies first — the largest single term, and the
       only step that frees space without needing any writes to succeed.
       Retention prefers *readable* backups over merely recent ones.
    2. ``wal_checkpoint(TRUNCATE)`` second. A checkpoint may have to extend
       the main DB, so it is attempted only after step 1 has created slack.
    3. Report. Row-level pruning is the caller's job
       (``candidate_logger.prune_candidates``) because it needs the schema.

    Returns a before/after report; ``freed_bytes`` is the measured delta, not
    an estimate.
    """
    before = disk_status(db_path)
    room = has_room_for_backup(db_path)
    under_pressure = force or (before.get("level") == "critical") or not room.get("ok")

    report: dict[str, Any] = {
        "triggered": bool(under_pressure),
        "before": before,
        "removed_backups": [],
        "kept_backups": [],
        "wal_checkpoint": None,
    }
    if not under_pressure:
        report["after"] = before
        report["freed_bytes"] = 0
        return report

    db_dir = os.path.dirname(os.path.abspath(db_path))
    db_basename = os.path.splitext(os.path.basename(db_path))[0]
    candidates = sorted(
        _glob_mod.glob(os.path.join(db_dir, f"{db_basename}_backup_*.db")),
        key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0,
        reverse=True,
    )
    # Newest-first, but a truncated copy never occupies a keep slot while a
    # readable one is still available.
    readable = [p for p in candidates if _is_readable_sqlite(p)]
    keep = readable[:max(keep_backups, 0)]
    for path in candidates:
        if path in keep:
            report["kept_backups"].append(os.path.basename(path))
            continue
        size = _size_or_zero(path)
        try:
            os.remove(path)
            report["removed_backups"].append({"name": os.path.basename(path), "size_bytes": size})
        except OSError as exc:
            report.setdefault("remove_errors", []).append(
                {"name": os.path.basename(path), "error": str(exc)}
            )

    try:
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            row = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            report["wal_checkpoint"] = list(row) if row else None
        finally:
            conn.close()
    except Exception as exc:
        report["wal_checkpoint"] = f"error: {exc}"

    after = disk_status(db_path)
    report["after"] = after
    report["freed_bytes"] = int(after.get("free_bytes", 0)) - int(before.get("free_bytes", 0))
    return report
