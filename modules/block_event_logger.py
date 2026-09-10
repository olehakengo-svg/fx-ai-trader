"""Durable gate-block attribution table (P8, rule:R3, 2026-09-11).

Why this exists — hull_donchian_fade residual localization
([[hull-fire-rate-funnel-2026-08-24]] §8):

  The `_tick_entry` guard chain already counts every block into
  ``DemoTrader._block_counts`` / ``_block_counts_per_strategy`` and logs a
  ``[SENTINEL_BLOCK_DIAG]`` line for diagnostic strategies. But both records
  are **volatile**:

    * the in-memory counters reset on every restart/deploy (observed in
      production 2026-09-11: total=9 with ``per_strategy_counts == {}`` for
      hull, while Render logs prove hull blocks fired daily), and
    * Render log retention is ~2 weeks effective — the 2026-08-26/27 hull
      winner bars were already unattributable when this diagnosis ran.

  The residual therefore looked like an "uninstrumented gate" from every
  durable observation surface, even though the gates were instrumented all
  along. This module makes the attribution durable: a tiny daily aggregate
  (day x mode x entry_type x instrument x reason) persisted to the demo DB.

Estimand (declared in monitoring/estimand_declarations.yml:
gate_block_attribution): per-tick gate-block EVENTS, not unique bars — the
same persistent signal is re-evaluated every ~30s poll, so counts carry up
to ~52x per-bar inflation (same caveat as evaluated_candidates). ``reason``
is normalized with ``reason.split('(')[0]`` exactly like the in-memory
counters, so the two surfaces stay diffable.

Recording only — this module never influences gate behaviour. Every write
is best-effort: exceptions are swallowed (logged at debug/warning) and the
entry path never sees them.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("block_event_logger")

# Retention for the daily aggregate. Key-space is bounded
# (day x mode x entry_type x instrument x reason ~= O(100) rows/day), so 90d
# stays a few thousand rows. Trimmed idempotently at init (app startup) —
# lesson from evaluated_candidates: never ship an audit table without
# retention ([[hull-fire-rate-funnel-2026-08-24]] §4.2).
RETENTION_DAYS = 90

_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS gate_block_daily (
    day TEXT NOT NULL,
    mode TEXT NOT NULL,
    entry_type TEXT NOT NULL,
    instrument TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    first_ts TEXT,
    last_ts TEXT,
    PRIMARY KEY (day, mode, entry_type, instrument, reason)
)
"""

_INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_gbd_entry_type ON gate_block_daily(entry_type)",
    "CREATE INDEX IF NOT EXISTS idx_gbd_day ON gate_block_daily(day)",
]


def init_block_table(db_path: str) -> bool:
    """Idempotently create gate_block_daily + indexes and trim retention.

    Safe to call once at app startup. Returns True on success.
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(_TABLE_DDL)
        for ddl in _INDEX_DDL:
            cur.execute(ddl)
        cur.execute(
            "DELETE FROM gate_block_daily WHERE day < date('now', ?)",
            (f"-{int(RETENTION_DAYS)} days",),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.warning("init_block_table failed: %s", exc)
        return False


def record_block(
    db_path: str,
    *,
    mode: str,
    entry_type: str,
    instrument: str = "",
    reason_key: str,
    ts: Optional[datetime] = None,
) -> bool:
    """Increment the durable daily aggregate for one gate-block event.

    ``reason_key`` must already be normalized (``reason.split('(')[0]``) by
    the caller so the key space matches the in-memory counters exactly.
    Best-effort: returns False instead of raising — the entry path must
    never be affected by this recording (behaviour-neutral by contract).
    """
    try:
        now = ts or datetime.now(timezone.utc)
        day = now.strftime("%Y-%m-%d")
        now_iso = now.isoformat()
        conn = sqlite3.connect(db_path, timeout=5)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO gate_block_daily"
            " (day, mode, entry_type, instrument, reason, count, first_ts, last_ts)"
            " VALUES (?, ?, ?, ?, ?, 1, ?, ?)"
            " ON CONFLICT(day, mode, entry_type, instrument, reason)"
            " DO UPDATE SET count = count + 1, last_ts = excluded.last_ts",
            (day, mode or "", entry_type or "", instrument or "",
             reason_key or "", now_iso, now_iso),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.debug("record_block failed: %s", exc)
        return False


def query_block_counts(
    db_path: str,
    days: int = 7,
    strategy: Optional[str] = None,
) -> dict[str, Any]:
    """Aggregate the durable gate-block table over the last ``days`` days.

    Returns the same key shapes as the in-memory counters so the two
    surfaces can be diffed directly:

      * ``counts``              {"<mode>:<reason>": n}
      * ``per_strategy_counts`` {"<entry_type>:<reason>": n}
      * ``per_cell_counts``     {"<entry_type>|<instrument>:<reason>": n}

    ESTIMAND WARNING: values are per-tick block events (~30s poll), NOT
    unique bars — do not read them as "N setups were blocked". Use them for
    attribution (which gate, which cell) and restart-proof trend, and
    normalize by bar via evaluated_candidates when a rate is needed.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    days_int = max(0, int(days))
    where = ["day >= date('now', ?)"] if days_int > 0 else []
    args: list[Any] = [f"-{days_int} days"] if days_int > 0 else []
    if strategy:
        where.append("entry_type = ?")
        args.append(strategy)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    cur.execute(
        "SELECT mode, entry_type, instrument, reason, SUM(count) AS n"
        f" FROM gate_block_daily{where_sql}"
        " GROUP BY mode, entry_type, instrument, reason",
        args,
    )
    rows = cur.fetchall()
    conn.close()
    counts: dict[str, int] = {}
    per_strategy: dict[str, int] = {}
    per_cell: dict[str, int] = {}
    total = 0
    for r in rows:
        n = int(r["n"] or 0)
        total += n
        mode_key = f"{r['mode']}:{r['reason']}"
        counts[mode_key] = counts.get(mode_key, 0) + n
        strat_key = f"{r['entry_type']}:{r['reason']}"
        per_strategy[strat_key] = per_strategy.get(strat_key, 0) + n
        cell_key = f"{r['entry_type']}|{r['instrument']}:{r['reason']}"
        per_cell[cell_key] = per_cell.get(cell_key, 0) + n
    return {
        "days": days_int,
        "strategy": strategy or None,
        "total": total,
        "counts": counts,
        "per_strategy_counts": per_strategy,
        "per_cell_counts": per_cell,
    }
