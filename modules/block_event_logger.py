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
import re
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
    metric_n INTEGER NOT NULL DEFAULT 0,
    metric_sum REAL,
    metric_min REAL,
    metric_max REAL,
    PRIMARY KEY (day, mode, entry_type, instrument, reason)
)
"""

_INDEX_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_gbd_entry_type ON gate_block_daily(entry_type)",
    "CREATE INDEX IF NOT EXISTS idx_gbd_day ON gate_block_daily(day)",
]


_METRIC_COLUMNS = (
    ("metric_n", "INTEGER NOT NULL DEFAULT 0"),
    ("metric_sum", "REAL"),
    ("metric_min", "REAL"),
    ("metric_max", "REAL"),
)


def _ensure_metric_columns(conn) -> None:
    """Add the 2026-09-21 magnitude columns to a pre-existing table.

    Idempotent: reads PRAGMA table_info and only ALTERs what is missing, so
    it is safe on every startup and on a fresh table created by _TABLE_DDL
    (which already declares them). Recording-only, like the rest of this
    module — a failure here must leave the count-only behaviour intact.
    """
    cur = conn.cursor()
    have = {row[1] for row in cur.execute("PRAGMA table_info(gate_block_daily)")}
    if not have:
        return
    for col, decl in _METRIC_COLUMNS:
        if col not in have:
            cur.execute(f"ALTER TABLE gate_block_daily ADD COLUMN {col} {decl}")


def parse_reason_metric(reason: str) -> Optional[float]:
    """Extract the measured magnitude from a raw ``_block()`` reason string.

    The in-memory counters key on ``reason.split('(')[0]`` to stop key-space
    explosion, which throws away the number the gate actually measured. That
    loss is why the 2026-09-21 ps-seat readout could attribute the 3 seats to
    ``spread_wide`` but could NOT say whether the wall was marginal (3.1p vs a
    3.0p limit = a tunable) or absolute (15p = structural). The daily rollup
    keeps the magnitude as min/sum/max per key instead, so the key space is
    unchanged (same PRIMARY KEY) while the distribution becomes readable.

    Returns the first number inside the first parenthetical, or None when the
    reason carries no measurement (e.g. ``order_bar_dedup``,
    ``no_confirm:macd_rsi_pullback``). Never raises.
    """
    try:
        if not reason or "(" not in reason:
            return None
        inner = reason.split("(", 1)[1]
        m = re.search(r"-?\d+(?:\.\d+)?", inner)
        return float(m.group(0)) if m else None
    except Exception:
        return None


def init_block_table(db_path: str) -> bool:
    """Idempotently create gate_block_daily + indexes and trim retention.

    Safe to call once at app startup. Returns True on success.
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(_TABLE_DDL)
        _ensure_metric_columns(conn)
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
    metric: Optional[float] = None,
    ts: Optional[datetime] = None,
) -> bool:
    """Increment the durable daily aggregate for one gate-block event.

    ``reason_key`` must already be normalized (``reason.split('(')[0]``) by
    the caller so the key space matches the in-memory counters exactly.
    ``metric`` (2026-09-21, rule:R3) is the magnitude the gate measured,
    normally ``parse_reason_metric(reason)`` — it is folded into per-key
    min/sum/max so the key space stays identical while the distribution of
    the blocking quantity becomes readable. ``None`` means "this gate
    reported no number" and leaves metric_sum/min/max untouched (NULL keeps
    meaning never-measured; it is NOT recorded as 0).
    Best-effort: returns False instead of raising — the entry path must
    never be affected by this recording (behaviour-neutral by contract).
    """
    try:
        now = ts or datetime.now(timezone.utc)
        day = now.strftime("%Y-%m-%d")
        now_iso = now.isoformat()
        conn = sqlite3.connect(db_path, timeout=5)
        cur = conn.cursor()
        _ensure_metric_columns(conn)
        _m = None if metric is None else float(metric)
        cur.execute(
            "INSERT INTO gate_block_daily"
            " (day, mode, entry_type, instrument, reason, count, first_ts, last_ts,"
            "  metric_n, metric_sum, metric_min, metric_max)"
            " VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(day, mode, entry_type, instrument, reason)"
            " DO UPDATE SET count = count + 1, last_ts = excluded.last_ts,"
            "  metric_n = metric_n + excluded.metric_n,"
            "  metric_sum = CASE WHEN excluded.metric_sum IS NULL THEN metric_sum"
            "    ELSE COALESCE(metric_sum, 0) + excluded.metric_sum END,"
            "  metric_min = CASE WHEN excluded.metric_min IS NULL THEN metric_min"
            "    WHEN metric_min IS NULL THEN excluded.metric_min"
            "    WHEN excluded.metric_min < metric_min THEN excluded.metric_min"
            "    ELSE metric_min END,"
            "  metric_max = CASE WHEN excluded.metric_max IS NULL THEN metric_max"
            "    WHEN metric_max IS NULL THEN excluded.metric_max"
            "    WHEN excluded.metric_max > metric_max THEN excluded.metric_max"
            "    ELSE metric_max END",
            (day, mode or "", entry_type or "", instrument or "",
             reason_key or "", now_iso, now_iso,
             0 if _m is None else 1, _m, _m, _m),
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
    _ensure_metric_columns(conn)
    cur.execute(
        "SELECT mode, entry_type, instrument, reason, SUM(count) AS n,"
        " SUM(COALESCE(metric_n, 0)) AS m_n, SUM(metric_sum) AS m_sum,"
        " MIN(metric_min) AS m_min, MAX(metric_max) AS m_max"
        f" FROM gate_block_daily{where_sql}"
        " GROUP BY mode, entry_type, instrument, reason",
        args,
    )
    rows = cur.fetchall()
    conn.close()
    counts: dict[str, int] = {}
    per_strategy: dict[str, int] = {}
    per_cell: dict[str, int] = {}
    per_cell_metrics: dict[str, dict[str, float | int]] = {}
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
        # 2026-09-21 (rule:R3): the magnitude reader. Added in the SAME commit
        # as the writer — a collection path without a reader is the
        # write-only failure this project has now hit repeatedly
        # ([[c1-candidate-readout-hull-funnel-2026-08-24]]).
        m_n = int(r["m_n"] or 0)
        if m_n > 0:
            agg = per_cell_metrics.setdefault(
                cell_key, {"n": 0, "sum": 0.0, "min": None, "max": None})
            agg["n"] = int(agg["n"]) + m_n
            agg["sum"] = float(agg["sum"]) + float(r["m_sum"] or 0.0)
            for bound, cmp_fn in (("min", min), ("max", max)):
                val = r[f"m_{bound}"]
                if val is None:
                    continue
                cur_val = agg[bound]
                agg[bound] = float(val) if cur_val is None else cmp_fn(
                    float(cur_val), float(val))
    for agg in per_cell_metrics.values():
        agg["mean"] = round(float(agg["sum"]) / int(agg["n"]), 4) if agg["n"] else None
    return {
        "days": days_int,
        "strategy": strategy or None,
        "total": total,
        "counts": counts,
        "per_strategy_counts": per_strategy,
        "per_cell_counts": per_cell,
        "per_cell_metrics": per_cell_metrics,
    }
