"""SQLite helpers for the price shock reversion grid BT."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Mapping, Any


DDL = """
CREATE TABLE IF NOT EXISTS price_shock_grid_cells (
    cell_id          TEXT PRIMARY KEY,         -- "{pair}_{tf}_{direction}_{pct}_{horizon}_{vol_q}"
    pair             TEXT NOT NULL,
    tf               TEXT NOT NULL,            -- "H4" or "H1"
    direction        TEXT NOT NULL,            -- "LONG_SHOCK" or "SHORT_SHOCK"
    percentile       REAL NOT NULL,            -- 0.01, 0.025, 0.05
    horizon_bars     INTEGER NOT NULL,
    vol_quintile     TEXT NOT NULL,            -- "ALL", "Q1"..."Q5"
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
    verdict          TEXT NOT NULL,            -- "SHADOW_CANDIDATE" / "CONDITIONAL" / "REJECT"
    period_start     TEXT NOT NULL,
    period_end       TEXT NOT NULL,
    bt_data_source   TEXT NOT NULL,            -- "MASSIVE_parquet"
    generated_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_psg_verdict ON price_shock_grid_cells(verdict);
CREATE INDEX IF NOT EXISTS idx_psg_pair_tf ON price_shock_grid_cells(pair, tf);
"""


COLUMNS = [
    "cell_id",
    "pair",
    "tf",
    "direction",
    "percentile",
    "horizon_bars",
    "vol_quintile",
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
    sql = f"INSERT OR REPLACE INTO price_shock_grid_cells ({columns_sql}) VALUES ({placeholders})"
    values = [tuple(row.get(col) for col in COLUMNS) for row in rows]
    with conn:
        conn.executemany(sql, values)
    return len(rows)
