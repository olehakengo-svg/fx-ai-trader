"""
C1: per-candidate audit table for observability (Phase 10 pivot).

G0a finding (raw/audits/production_routing_audit_2026-04-28.md +
knowledge-base/wiki/lessons/lesson-select-best-bottleneck-2026-04-28.md):

  30 of 54 deployed strategies have NEVER appeared in demo_trades.db. The
  ``DaytradeEngine.select_best()`` keeps only the max-score candidate per
  bar; every other candidate is discarded with no audit trail. Past
  Phase 1-8 conclusions of "0 trade ⇒ no edge" are contaminated by
  competition selection bias.

This module records every Candidate produced by ``evaluate_all()`` to a
new ``evaluated_candidates`` table, **without changing trade-execution
behaviour**. Selection competition still runs and only the winner reaches
``demo_trades``; losers are now visible.

Usage (called from app.py after select_best):

    from modules.candidate_logger import log_candidates
    log_candidates(_db_path, _dt_candidates, _dt_best,
                   instrument=symbol, tf=tf, bar_time=bar_time)

The function is best-effort: any exception is swallowed and logged but
does not interrupt the trade flow.

Plan: /Users/jg-n-012/.claude/plans/memoized-snuggling-eclipse.md
(Phase 10 C1 — observability restoration)
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Iterable, Optional

logger = logging.getLogger("candidate_logger")

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS evaluated_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bar_time TEXT,
    instrument TEXT,
    tf TEXT,
    strategy_name TEXT,
    signal TEXT,
    confidence INTEGER,
    score REAL,
    selected INTEGER DEFAULT 0,
    selected_strategy TEXT,
    rejected_reason TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
)
"""

_INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_evcand_bar_time ON evaluated_candidates(bar_time)",
    "CREATE INDEX IF NOT EXISTS idx_evcand_strategy ON evaluated_candidates(strategy_name)",
    "CREATE INDEX IF NOT EXISTS idx_evcand_selected ON evaluated_candidates(selected)",
    "CREATE INDEX IF NOT EXISTS idx_evcand_created ON evaluated_candidates(created_at)",
]


def init_candidates_table(db_path: str) -> bool:
    """Idempotently create the evaluated_candidates table + indexes.

    Returns True on success, False otherwise. Safe to call once at app
    startup, before any logging.
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(_TABLE_DDL)
        for ddl in _INDEX_DDL:
            cur.execute(ddl)
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.warning("init_candidates_table failed: %s", exc)
        return False


def log_candidates(
    db_path: str,
    candidates: Iterable[Any],
    selected: Optional[Any],
    *,
    instrument: str,
    tf: str = "15m",
    bar_time: Optional[Any] = None,
) -> bool:
    """Record every Candidate from ``evaluate_all`` into the audit table.

    Best-effort. Returns True if all rows inserted, False on any error.
    Trade-execution flow must NOT depend on this returning True.

    Parameters
    ----------
    db_path : str
        Path to demo_trades.db (resolved by app.py).
    candidates : iterable of Candidate
        Output of ``DaytradeEngine.evaluate_all(ctx)``. Each must have
        ``entry_type``, ``signal``, ``confidence``, ``score`` attrs.
    selected : Candidate or None
        Winner from ``select_best``. Used to populate ``selected``=1 for
        the winning row and ``selected_strategy`` on every row.
    instrument : str
        Pair symbol (e.g. "USD_JPY"). Stored as-is.
    tf : str
        Timeframe (default "15m").
    bar_time : str or datetime or None
        Bar timestamp. ``str(bar_time)`` if non-None, else NULL.
    """
    candidates_list = list(candidates) if candidates else []
    if not candidates_list:
        return True

    selected_name = (
        getattr(selected, "entry_type", None)
        if selected is not None else None
    )
    bar_str = str(bar_time) if bar_time is not None else None

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        n_inserted = 0
        for c in candidates_list:
            try:
                name = getattr(c, "entry_type", None)
                sig = getattr(c, "signal", None)
                conf = int(getattr(c, "confidence", 0) or 0)
                score = float(getattr(c, "score", 0.0) or 0.0)
                is_selected = 1 if (selected is not None and c is selected) else 0
                cur.execute(
                    "INSERT INTO evaluated_candidates"
                    " (bar_time, instrument, tf, strategy_name, signal,"
                    "  confidence, score, selected, selected_strategy)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (bar_str, instrument, tf, name, sig,
                     conf, score, is_selected, selected_name),
                )
                n_inserted += 1
            except Exception as row_exc:
                logger.debug("log_candidates row skipped: %s", row_exc)
                continue
        conn.commit()
        conn.close()
        # Return False if every row failed — typical sign that the table
        # is missing or the schema changed. Caller can use this for one-time
        # alerting; trade-execution path must still treat exceptions as soft.
        return n_inserted > 0
    except Exception as exc:
        logger.warning(
            "log_candidates failed (n=%d, instrument=%s): %s",
            len(candidates_list), instrument, exc,
        )
        return False


def query_candidate_summary(
    db_path: str,
    days: int = 30,
) -> dict[str, dict[str, int]]:
    """Per-strategy summary: total candidates produced, total selected.

    Phase 10 C1 success metric: any strategy with ``total_candidates > 0``
    but ``selected = 0`` is real evidence of edge presence + competition
    loss — distinguishing case (b) from case (a) of the bottleneck lesson.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    days_int = max(0, int(days))
    if days_int > 0:
        cutoff_arg = f"-{days_int} days"
        cur.execute(
            "SELECT strategy_name,"
            " COUNT(*) AS total_candidates,"
            " SUM(CASE WHEN selected = 1 THEN 1 ELSE 0 END) AS n_selected,"
            " SUM(CASE WHEN signal = 'BUY' THEN 1 ELSE 0 END) AS n_buy,"
            " SUM(CASE WHEN signal = 'SELL' THEN 1 ELSE 0 END) AS n_sell"
            " FROM evaluated_candidates"
            " WHERE created_at >= datetime('now', ?)"
            " GROUP BY strategy_name",
            (cutoff_arg,),
        )
    else:
        cur.execute(
            "SELECT strategy_name,"
            " COUNT(*) AS total_candidates,"
            " SUM(CASE WHEN selected = 1 THEN 1 ELSE 0 END) AS n_selected,"
            " SUM(CASE WHEN signal = 'BUY' THEN 1 ELSE 0 END) AS n_buy,"
            " SUM(CASE WHEN signal = 'SELL' THEN 1 ELSE 0 END) AS n_sell"
            " FROM evaluated_candidates"
            " GROUP BY strategy_name"
        )
    rows = cur.fetchall()
    conn.close()
    return {
        r["strategy_name"]: {
            "total_candidates": r["total_candidates"],
            "n_selected": r["n_selected"],
            "n_buy": r["n_buy"],
            "n_sell": r["n_sell"],
        }
        for r in rows
    }


def query_candidate_meta(db_path: str) -> dict[str, Any]:
    """Table health: row count, coverage window, distinct strategy count.

    2026-08-24 (rule:R3): the C1 table has been **write-only** since
    2026-04-28 — no API route and no tool ever called
    ``query_candidate_summary``. That is why the hull_donchian_fade
    fire-rate gap (12.6 signal/wk offline vs 1.62 trade/wk live) sat
    undiagnosed for 49 days: the funnel stage between "candidate
    produced" and "trade recorded" was unobservable from outside.

    The row count is returned so unbounded growth on the Render disk is
    visible (no retention job exists as of 2026-08-24).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS rows,"
        " MIN(created_at) AS first_created,"
        " MAX(created_at) AS last_created,"
        " COUNT(DISTINCT strategy_name) AS n_strategies"
        " FROM evaluated_candidates"
    )
    r = cur.fetchone()
    conn.close()
    return {
        "rows": r["rows"],
        "first_created": r["first_created"],
        "last_created": r["last_created"],
        "n_strategies": r["n_strategies"],
    }


def query_candidate_rows(
    db_path: str,
    *,
    strategy: str = "",
    instrument: str = "",
    days: int = 7,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Recent candidate rows for per-bar forensics (newest first).

    Complements :func:`query_candidate_summary` (aggregate) by exposing the
    individual bars, so a strategy with ``total_candidates > 0`` and
    ``n_selected = 0`` can be traced to concrete bar timestamps and matched
    against ``demo_trades`` / block counters.

    Note on estimand: rows are logged **after** the v9.1 HTF Hard Block has
    already filtered the candidate list (app.py), so HTF-blocked candidates
    never reach this table — they are only visible via the
    ``[DTE] HTF_HARD_BLOCK`` stdout line. Do not read a zero row count as
    "the strategy produced no signal".
    """
    where = []
    params: list[Any] = []
    days_int = max(0, int(days))
    if days_int > 0:
        where.append("created_at >= datetime('now', ?)")
        params.append(f"-{days_int} days")
    if strategy:
        where.append("strategy_name = ?")
        params.append(strategy)
    if instrument:
        where.append("instrument = ?")
        params.append(instrument)
    sql = (
        "SELECT bar_time, instrument, tf, strategy_name, signal, confidence,"
        " score, selected, selected_strategy, created_at"
        " FROM evaluated_candidates"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 2000)))

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# Default retention for the C1 audit table, derived rather than guessed: the
# longest window any consumer actually asks for is 30 days
# (``query_candidate_summary`` default; ``query_candidate_rows`` uses 7, and
# the hull funnel analysis used 30). 90 days keeps a 3x margin over every
# observed use while holding the table near its 2026-08 size instead of
# letting it grow without bound. Override with ``C1_RETENTION_DAYS``.
DEFAULT_RETENTION_DAYS = 90


def prune_candidates(db_path: str, keep_days: int = 0) -> dict[str, Any]:
    """Delete ``evaluated_candidates`` rows older than ``keep_days`` (rule:R3).

    The table has grown without bound since 2026-04-28 on a 1 GB Render disk
    that filled completely on 2026-08-21, stopping **all** SQLite writes for
    3.5 days. Capping the table removes one of the two growth terms (the
    other — retained backup copies — is handled in
    ``DemoDB.backup_database``).

    ``keep_days=0`` resolves to ``C1_RETENTION_DAYS`` from the environment,
    falling back to :data:`DEFAULT_RETENTION_DAYS`. A non-positive resolved
    value disables pruning and is reported as ``status="disabled"``.

    Caveat, stated because it is load-bearing: SQLite ``DELETE`` frees pages
    for reuse but does **not** shrink the file. This bounds future growth; it
    does not reclaim disk that is already consumed. ``VACUUM`` would reclaim
    it but needs roughly a second copy of the DB in free space — precisely
    what is unavailable when the disk is full — so it is deliberately not
    run here.
    """
    import os as _os

    if keep_days <= 0:
        try:
            keep_days = int(_os.environ.get("C1_RETENTION_DAYS", DEFAULT_RETENTION_DAYS))
        except (TypeError, ValueError):
            keep_days = DEFAULT_RETENTION_DAYS
    if keep_days <= 0:
        return {"status": "disabled", "keep_days": keep_days, "deleted": 0}

    try:
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM evaluated_candidates WHERE created_at < datetime('now', ?)",
                (f"-{int(keep_days)} days",),
            )
            deleted = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            conn.commit()
            remaining = int(
                conn.execute("SELECT COUNT(*) FROM evaluated_candidates").fetchone()[0]
            )
        finally:
            conn.close()
        logger.info("prune_candidates: deleted=%s remaining=%s keep_days=%s",
                    deleted, remaining, keep_days)
        return {
            "status": "ok",
            "keep_days": keep_days,
            "deleted": deleted,
            "remaining": remaining,
        }
    except Exception as exc:
        logger.warning("prune_candidates failed: %s", exc)
        return {"status": "error", "error": str(exc), "keep_days": keep_days, "deleted": 0}
