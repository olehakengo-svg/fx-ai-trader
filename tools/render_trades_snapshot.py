"""Pull Render /api/demo/trades into a local SQLite snapshot.

Read-only against Render. Writes to a separate snapshot DB to avoid touching
the dev local `demo_trades.db`. Idempotent: drops/recreates the `demo_trades`
table on each run.

Usage:
    python3 tools/render_trades_snapshot.py \\
        --output knowledge-base/raw/snapshots/render-demo-trades-YYYYMMDD.db \\
        --limit 2000

The HTTP client is `requests` and the URL is constructed from a hard-coded
HTTPS host plus an integer-only `limit` querystring, so no scheme/host
injection surface exists.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import requests

RENDER_BASE = "https://fx-ai-trader.onrender.com"
TRADES_PATH = "/api/demo/trades"

SCHEMA = """
CREATE TABLE demo_trades (
    id INTEGER,
    trade_id TEXT,
    status TEXT,
    direction TEXT,
    entry_price REAL,
    entry_time TEXT,
    exit_price REAL,
    exit_time TEXT,
    sl REAL,
    tp REAL,
    spread_at_entry REAL,
    pnl_pips REAL,
    pnl_r REAL,
    outcome TEXT,
    entry_type TEXT,
    confidence REAL,
    tf TEXT,
    reasons TEXT,
    regime TEXT,
    layer1_dir TEXT,
    score REAL,
    close_reason TEXT,
    ema_conf REAL,
    sr_basis TEXT,
    created_at TEXT,
    mode TEXT,
    instrument TEXT,
    is_shadow INTEGER,
    oanda_trade_id TEXT,
    mtf_regime TEXT,
    mtf_alignment TEXT,
    mtf_d1_label INTEGER,
    mtf_h4_label INTEGER,
    mtf_vol_state TEXT,
    mtf_gate_action TEXT,
    gate_group TEXT,
    cooldown_elapsed REAL,
    mafe_favorable_pips REAL,
    mafe_adverse_pips REAL,
    dedup_violation INTEGER,
    alpha_snapshot TEXT,
    close_analysis TEXT
)
"""

KEPT_FIELDS = [
    "id", "trade_id", "status", "direction", "entry_price", "entry_time",
    "exit_price", "exit_time", "sl", "tp", "spread_at_entry", "pnl_pips", "pnl_r", "outcome",
    "entry_type", "confidence", "tf", "reasons", "regime", "layer1_dir",
    "score", "close_reason", "ema_conf", "sr_basis", "created_at", "mode",
    "instrument", "is_shadow", "oanda_trade_id", "mtf_regime", "mtf_alignment",
    "mtf_d1_label", "mtf_h4_label", "mtf_vol_state", "mtf_gate_action",
    "gate_group", "cooldown_elapsed", "mafe_favorable_pips", "mafe_adverse_pips",
    "dedup_violation", "alpha_snapshot", "close_analysis",
]


def fetch(limit: int) -> list[dict]:
    if not isinstance(limit, int) or limit <= 0 or limit > 100000:
        raise ValueError(f"limit must be a positive int <= 100000, got {limit!r}")
    url = RENDER_BASE + TRADES_PATH
    resp = requests.get(url, params={"limit": str(limit)}, timeout=30)
    resp.raise_for_status()
    return resp.json().get("trades", [])


def write(db_path: Path, trades: list[dict]) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    rows = []
    for t in trades:
        rows.append(tuple(t.get(f) for f in KEPT_FIELDS))
    placeholders = ", ".join(["?"] * len(KEPT_FIELDS))
    cols = ", ".join(KEPT_FIELDS)
    cur.executemany(
        f"INSERT INTO demo_trades ({cols}) VALUES ({placeholders})",
        rows,
    )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM demo_trades").fetchone()[0]
    conn.close()
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True, help="path for snapshot SQLite file")
    ap.add_argument("--limit", type=int, default=2000)
    args = ap.parse_args()
    trades = fetch(args.limit)
    n = write(Path(args.output), trades)
    print(f"wrote {n} rows to {args.output}")


if __name__ == "__main__":
    main()
