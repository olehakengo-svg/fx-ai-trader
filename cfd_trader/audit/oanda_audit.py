"""SQLite oanda_audit table for cfd-trader.

Section 5.D (LIVE/Shadow separation): is_shadow is NOT NULL DEFAULT 0 at
the schema level. All Live aggregations MUST filter is_shadow=0.

Section 5.G (entry_type 二義性): bridge_status separates lifecycle
('sent' vs 'filled') from strategy_name (戦略名) and mode (LIVE/SHADOW).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict
from typing import Any

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS oanda_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT    NOT NULL,
    instrument      TEXT    NOT NULL,
    strategy_name   TEXT    NOT NULL,
    bridge_status   TEXT    NOT NULL,
    side            TEXT    NOT NULL,
    units           INTEGER NOT NULL,
    signal_price    REAL    NOT NULL,
    entry_price     REAL    NOT NULL,
    is_shadow       INTEGER NOT NULL DEFAULT 0,
    mode            TEXT    NOT NULL,
    extra_json      TEXT,
    exit_ts         TEXT,
    exit_price      REAL,
    pnl_point       REAL
);
CREATE INDEX IF NOT EXISTS idx_oanda_audit_instrument ON oanda_audit(instrument);
CREATE INDEX IF NOT EXISTS idx_oanda_audit_is_shadow  ON oanda_audit(is_shadow);
CREATE INDEX IF NOT EXISTS idx_oanda_audit_strategy   ON oanda_audit(strategy_name);
"""

_MIGRATION_SQL = (
    "ALTER TABLE oanda_audit ADD COLUMN exit_ts TEXT",
    "ALTER TABLE oanda_audit ADD COLUMN exit_price REAL",
    "ALTER TABLE oanda_audit ADD COLUMN pnl_point REAL",
)

# Static INSERT — column list matches OandaAuditEntry field order exactly.
# Written as a literal so no runtime SQL string building occurs.
_INSERT_SQL = (
    "INSERT INTO oanda_audit"
    " (ts,instrument,strategy_name,bridge_status,side,units,"
    "signal_price,entry_price,is_shadow,mode,extra_json,"
    "exit_ts,exit_price,pnl_point)"
    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
)

# Pre-built WHERE clauses for every filterable column.
# Keys are validated column names; values are complete, static SQL fragments.
# Building these at module load time against known literals eliminates any
# runtime SQL string interpolation in query_entries.
_WHERE_CLAUSE: dict[str, str] = {
    "id":            "WHERE id = ?",
    "ts":            "WHERE ts = ?",
    "instrument":    "WHERE instrument = ?",
    "strategy_name": "WHERE strategy_name = ?",
    "bridge_status": "WHERE bridge_status = ?",
    "side":          "WHERE side = ?",
    "units":         "WHERE units = ?",
    "signal_price":  "WHERE signal_price = ?",
    "entry_price":   "WHERE entry_price = ?",
    "is_shadow":     "WHERE is_shadow = ?",
    "mode":          "WHERE mode = ?",
    "extra_json":    "WHERE extra_json = ?",
}

# AND fragments used when more than one filter key is supplied.
_AND_CLAUSE: dict[str, str] = {
    "id":            "id = ?",
    "ts":            "ts = ?",
    "instrument":    "instrument = ?",
    "strategy_name": "strategy_name = ?",
    "bridge_status": "bridge_status = ?",
    "side":          "side = ?",
    "units":         "units = ?",
    "signal_price":  "signal_price = ?",
    "entry_price":   "entry_price = ?",
    "is_shadow":     "is_shadow = ?",
    "mode":          "mode = ?",
    "extra_json":    "extra_json = ?",
}


@dataclass
class OandaAuditEntry:
    ts: str
    instrument: str
    strategy_name: str
    bridge_status: str       # 'sent' | 'filled' | 'rejected'
    side: str                # 'long' | 'short'
    units: int
    signal_price: float
    entry_price: float
    is_shadow: int           # 0 = LIVE, 1 = SHADOW
    mode: str                # 'LIVE' | 'SHADOW' | 'RAMP_1' | ...
    extra_json: str | None = None
    exit_ts: str | None = None
    exit_price: float | None = None
    pnl_point: float | None = None


def init_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(CREATE_TABLE_SQL)
        for stmt in _MIGRATION_SQL:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as exc:
                if "duplicate column name" in str(exc):
                    continue
                raise


def record_entry(db_path: str, entry: OandaAuditEntry) -> int:
    d = asdict(entry)
    params = [
        d["ts"], d["instrument"], d["strategy_name"], d["bridge_status"],
        d["side"], d["units"], d["signal_price"], d["entry_price"],
        d["is_shadow"], d["mode"], d["extra_json"],
        d["exit_ts"], d["exit_price"], d["pnl_point"],
    ]
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(_INSERT_SQL, params)
        return int(cur.lastrowid)


def query_entries(db_path: str, where: dict[str, Any]) -> list[OandaAuditEntry]:
    unknown = set(where.keys()) - set(_AND_CLAUSE.keys())
    if unknown:
        raise ValueError(f"Unknown oanda_audit filter columns: {unknown}")

    if not where:
        sql = "SELECT * FROM oanda_audit"
        params: list[Any] = []
    elif len(where) == 1:
        (col,) = where.keys()
        sql = "SELECT * FROM oanda_audit " + _WHERE_CLAUSE[col]
        params = list(where.values())
    else:
        and_parts = " AND ".join(_AND_CLAUSE[col] for col in where.keys())
        sql = "SELECT * FROM oanda_audit WHERE " + and_parts
        params = list(where.values())

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    out: list[OandaAuditEntry] = []
    for r in rows:
        out.append(
            OandaAuditEntry(
                ts=r["ts"],
                instrument=r["instrument"],
                strategy_name=r["strategy_name"],
                bridge_status=r["bridge_status"],
                side=r["side"],
                units=r["units"],
                signal_price=r["signal_price"],
                entry_price=r["entry_price"],
                is_shadow=r["is_shadow"],
                mode=r["mode"],
                extra_json=r["extra_json"],
                exit_ts=r["exit_ts"],
                exit_price=r["exit_price"],
                pnl_point=r["pnl_point"],
            )
        )
    return out
