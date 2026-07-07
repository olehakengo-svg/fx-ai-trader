"""Snapshot → cell-audit pipeline schema-parity tests.

Guards the schema contract between `tools/render_trades_snapshot.py` (which
materialises the Render `/api/demo/trades` payload into a local SQLite
`demo_trades` table) and `tools/cell_edge_audit.py` (which SELECTs
`spread_at_entry` from that table). A snapshot missing `spread_at_entry`
breaks the audit with "no such column: spread_at_entry".
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(mod_name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


snapshot = _load("render_trades_snapshot", "tools/render_trades_snapshot.py")
cell_audit = _load("cell_edge_audit", "tools/cell_edge_audit.py")


def _fake_trades() -> list[dict]:
    """Two closed trades mimicking the API payload, including spread_at_entry."""
    base = {
        "status": "CLOSED", "outcome": "WIN", "is_shadow": 0,
        "entry_type": "orb_trap", "mode": "scalp", "instrument": "GBP_USD",
        "direction": "SELL", "tf": "M5",
        "entry_time": "2026-06-01T09:00:00+00:00",
        "entry_price": 1.27, "sl": 1.275, "tp": 1.26, "pnl_pips": 5.0,
    }
    t1 = {**base, "trade_id": "t1", "spread_at_entry": 1.4,
          "spread_at_exit": 1.1, "slippage_pips": 0.3, "signal_price": 1.2705}
    t2 = {**base, "trade_id": "t2", "spread_at_entry": 1.6,
          "spread_at_exit": 1.9, "slippage_pips": 0.7, "signal_price": 1.2698,
          "outcome": "LOSS", "pnl_pips": -3.0}
    return [t1, t2]


def test_snapshot_table_has_spread_at_entry_column(tmp_path):
    """render_trades_snapshot SCHEMA must include spread_at_entry."""
    assert "spread_at_entry" in snapshot.SCHEMA
    assert "spread_at_entry" in snapshot.KEPT_FIELDS


def test_audit_runs_against_fresh_snapshot(tmp_path):
    """A snapshot written by render_trades_snapshot.write() must be queryable
    by cell_edge_audit.fetch_trades() without a manual ALTER TABLE."""
    db = tmp_path / "snap.db"
    snapshot.write(db, _fake_trades())

    # This is the exact SELECT that used to raise "no such column".
    rows = cell_audit.fetch_trades(str(db), include_shadow=False)
    assert len(rows) == 2
    spreads = sorted(r["spread_at_entry"] for r in rows)
    assert spreads == [1.4, 1.6]


def test_snapshot_preserves_friction_diagnostics(tmp_path):
    """slippage_pips / spread_at_exit / signal_price must survive the
    snapshot round-trip. They are the raw inputs risk_analytics
    pnl_attribution uses to measure friction, so a snapshot dropping them
    makes external friction verification impossible (they are diagnostic
    metadata only — never re-subtracted from pnl_pips)."""
    for col in ("slippage_pips", "spread_at_exit", "signal_price"):
        assert col in snapshot.SCHEMA
        assert col in snapshot.KEPT_FIELDS

    import sqlite3

    db = tmp_path / "snap.db"
    snapshot.write(db, _fake_trades())
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT trade_id, slippage_pips, spread_at_exit, signal_price"
        " FROM demo_trades ORDER BY trade_id").fetchall()
    conn.close()
    assert [dict(r) for r in rows] == [
        {"trade_id": "t1", "slippage_pips": 0.3,
         "spread_at_exit": 1.1, "signal_price": 1.2705},
        {"trade_id": "t2", "slippage_pips": 0.7,
         "spread_at_exit": 1.9, "signal_price": 1.2698},
    ]


def test_v3_stats_independent_of_spread(tmp_path):
    """v3 cells key on (entry_type, session, pair, direction, mode) — never
    spread — so populating vs NULL-ing spread must not change v3 stats."""
    db = tmp_path / "snap.db"
    snapshot.write(db, _fake_trades())
    rows = cell_audit.fetch_trades(str(db), include_shadow=False)

    cells = cell_audit.aggregate_cells(rows, mode="v3")
    scored = cell_audit.score_cells(cells, min_n=1, mode="v3")
    assert len(scored) == 1
    rec = scored[0]
    assert rec["n"] == 2 and rec["wins"] == 1
    assert rec["entry_type"] == "orb_trap" and rec["direction"] == "SELL"
    assert "spread_quartile" not in rec  # v3 has no spread dimension
