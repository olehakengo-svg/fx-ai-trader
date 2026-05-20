"""SQLite helpers for Bigbeluga displacement/delta grid BT."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Mapping


DDL = """
CREATE TABLE IF NOT EXISTS bigbeluga_disp_delta_cells (
    cell_id          TEXT PRIMARY KEY,         -- "{pair}_{hypothesis}_{volMult}_{bodyPct}_{horizon}"
    pair             TEXT NOT NULL,
    tf               TEXT NOT NULL,            -- "H1"
    intrabar_tf      TEXT NOT NULL,            -- "M5"
    hypothesis       TEXT NOT NULL,            -- "H-A" / "H-B" / "H-C" / "H-D"
    vol_mult         REAL NOT NULL,
    body_pct         REAL NOT NULL,
    horizon_bars     INTEGER NOT NULL,
    cohort           TEXT NOT NULL,            -- "primary_12y" or "secondary_1y"
    n_trades         INTEGER NOT NULL,
    win_rate         REAL,
    ev_pip           REAL,
    ev_pct           REAL,
    profit_factor    REAL,
    wilson_lower_95  REAL,
    sharpe_annual    REAL,
    kelly_fraction   REAL,
    max_dd_pct       REAL,
    mae_mean_pct     REAL,
    mae_p5_pct       REAL,
    mfe_mean_pct     REAL,
    year_flip_count  INTEGER,
    p_value          REAL,
    bonferroni_pass  INTEGER,                  -- 0/1
    bh_fdr_pass      INTEGER,                  -- 0/1
    g7_delta_incremental INTEGER,              -- 0/1, H-A/H-B では NULL
    verdict          TEXT NOT NULL,            -- "SHADOW_CANDIDATE"/"CONDITIONAL"/"REJECT"
    period_start     TEXT NOT NULL,
    period_end       TEXT NOT NULL,
    bt_data_source   TEXT NOT NULL DEFAULT 'MASSIVE_parquet',
    generated_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bbdd_verdict ON bigbeluga_disp_delta_cells(verdict);
CREATE INDEX IF NOT EXISTS idx_bbdd_pair_hyp ON bigbeluga_disp_delta_cells(pair, hypothesis);
CREATE INDEX IF NOT EXISTS idx_bbdd_cohort ON bigbeluga_disp_delta_cells(cohort);
"""


COLUMNS = [
    "cell_id",
    "pair",
    "tf",
    "intrabar_tf",
    "hypothesis",
    "vol_mult",
    "body_pct",
    "horizon_bars",
    "cohort",
    "n_trades",
    "win_rate",
    "ev_pip",
    "ev_pct",
    "profit_factor",
    "wilson_lower_95",
    "sharpe_annual",
    "kelly_fraction",
    "max_dd_pct",
    "mae_mean_pct",
    "mae_p5_pct",
    "mfe_mean_pct",
    "year_flip_count",
    "p_value",
    "bonferroni_pass",
    "bh_fdr_pass",
    "g7_delta_incremental",
    "verdict",
    "period_start",
    "period_end",
    "bt_data_source",
    "generated_at",
]


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(DDL)
    conn.commit()


def replace_cells(conn: sqlite3.Connection, cells: Iterable[Mapping[str, Any]]) -> int:
    rows = list(cells)
    init_db(conn)
    placeholders = ", ".join(["?"] * len(COLUMNS))
    columns_sql = ", ".join(COLUMNS)
    sql = f"INSERT OR REPLACE INTO bigbeluga_disp_delta_cells ({columns_sql}) VALUES ({placeholders})"
    values = [tuple(row.get(col) for col in COLUMNS) for row in rows]
    with conn:
        conn.executemany(sql, values)
    return len(rows)
