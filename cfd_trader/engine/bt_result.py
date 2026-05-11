"""BTResult dataclass + SQLite persistence helpers.

Section 5.B: every BT run reports N / WR / EV / PF / Wilson_lo / Kelly /
Max_DD / single_year_concentration. Bonferroni m is stored in metadata_json
because at this stage only one strategy is in the catalog; multi-strategy
correction lives in the promotion layer.

SQL is intentionally static (no f-string interpolation) to satisfy the
project's semgrep hook. Same pattern as cfd_trader/audit/oanda_audit.py.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS bt_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name   TEXT    NOT NULL,
    instrument      TEXT    NOT NULL,
    tf              TEXT    NOT NULL,
    start_iso       TEXT    NOT NULL,
    end_iso         TEXT    NOT NULL,
    n               INTEGER NOT NULL,
    wr              REAL    NOT NULL,
    ev_point        REAL    NOT NULL,
    pf              REAL    NOT NULL,
    wilson_lo       REAL    NOT NULL,
    kelly_fraction  REAL    NOT NULL,
    max_dd_point    REAL    NOT NULL,
    single_year_concentration REAL NOT NULL,
    data_source     TEXT    NOT NULL,
    metadata_json   TEXT,
    created_at      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bt_results_strategy ON bt_results(strategy_name);
CREATE INDEX IF NOT EXISTS idx_bt_results_instrument ON bt_results(instrument);
"""

_INSERT_SQL = (
    "INSERT INTO bt_results"
    " (strategy_name,instrument,tf,start_iso,end_iso,n,wr,ev_point,pf,"
    "wilson_lo,kelly_fraction,max_dd_point,single_year_concentration,"
    "data_source,metadata_json,created_at)"
    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
)

_SELECT_ALL_SQL = (
    "SELECT strategy_name, instrument, tf, start_iso, end_iso, n, wr, "
    "ev_point, pf, wilson_lo, kelly_fraction, max_dd_point, "
    "single_year_concentration, data_source, metadata_json "
    "FROM bt_results"
)

_SELECT_BY_STRATEGY_SQL = (
    "SELECT strategy_name, instrument, tf, start_iso, end_iso, n, wr, "
    "ev_point, pf, wilson_lo, kelly_fraction, max_dd_point, "
    "single_year_concentration, data_source, metadata_json "
    "FROM bt_results WHERE strategy_name = ?"
)


@dataclass(frozen=True)
class BTResult:
    strategy_name: str
    instrument: str
    tf: str
    start_iso: str
    end_iso: str
    n: int
    wr: float
    ev_point: float
    pf: float
    wilson_lo: float
    kelly_fraction: float
    max_dd_point: float
    single_year_concentration: float
    data_source: str
    metadata_json: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def init_bt_results_table(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_CREATE_TABLE_SQL)


def insert_bt_result(db_path: str, result: BTResult) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            _INSERT_SQL,
            (
                result.strategy_name, result.instrument, result.tf,
                result.start_iso, result.end_iso,
                result.n, result.wr, result.ev_point, result.pf,
                result.wilson_lo, result.kelly_fraction,
                result.max_dd_point, result.single_year_concentration,
                result.data_source, result.metadata_json, now,
            ),
        )
        return int(cur.lastrowid)


def fetch_bt_results(db_path: str, *, strategy_name: str | None = None) -> list[BTResult]:
    if strategy_name is None:
        sql = _SELECT_ALL_SQL
        params: tuple = ()
    else:
        sql = _SELECT_BY_STRATEGY_SQL
        params = (strategy_name,)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        BTResult(
            strategy_name=r[0], instrument=r[1], tf=r[2],
            start_iso=r[3], end_iso=r[4],
            n=r[5], wr=r[6], ev_point=r[7], pf=r[8],
            wilson_lo=r[9], kelly_fraction=r[10],
            max_dd_point=r[11], single_year_concentration=r[12],
            data_source=r[13], metadata_json=r[14],
        )
        for r in rows
    ]
