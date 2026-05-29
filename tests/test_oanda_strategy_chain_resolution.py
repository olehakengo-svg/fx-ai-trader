"""Tests for the demo_trade_id chain resolver used by the strategy backfill.

The chain resolver (``tools.backfill_oanda_strategy_2026_05_19.
resolve_strategy_via_audit_chain``) catches historical PYR orphans whose
sent rows fall outside any time window of the PYR child's open_time. It
walks ``oanda_trade_id → demo_trade_id → sent row`` and, when the
demo_trade_id is a ``PYR_<parent>`` label, also tries the parent.

This is a strictly read-only resolver (no UPDATE) — it returns a label
string. Backfill is exercised end-to-end in
``test_oanda_strategy_chain_backfill_e2e``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.demo_db import DemoDB  # noqa: E402
from tools.backfill_oanda_strategy_2026_05_19 import (  # noqa: E402
    _scan_missing,
    resolve_strategy_via_audit_chain,
)


@pytest.fixture
def db(tmp_path):
    return DemoDB(str(tmp_path / "chain.db"))


def _audit(demo_trade_id, entry_type, bridge_status, *,
           oanda_trade_id="", instrument="GBP_USD", direction="BUY",
           units=10000, timestamp="2026-04-28T09:34:14+00:00"):
    return {
        "timestamp": timestamp,
        "demo_trade_id": demo_trade_id,
        "entry_type": entry_type,
        "direction": direction,
        "instrument": instrument,
        "units": units,
        "is_live": True,
        "bridge_status": bridge_status,
        "block_reason": "",
        "oanda_trade_id": oanda_trade_id,
    }


def _seed_oanda_trade(db, oanda_trade_id, *, instrument="GBP_USD",
                     direction="SELL", open_time="2026-04-28T09:34:14Z",
                     close_time="2026-04-28T09:50:00Z", realized_pl=-12.3,
                     state="CLOSED"):
    db.upsert_oanda_trade({
        "id": oanda_trade_id,
        "instrument": instrument,
        "state": state,
        "direction": direction,
        "initialUnits": "10000",
        "currentUnits": "0",
        "price": "1.25000",
        "openTime": open_time,
        "closeTime": close_time,
        "realizedPL": str(realized_pl),
        "unrealizedPL": "0",
        "financing": "0",
        "commission": "0",
        "marginUsed": "100",
        "stopLossOrder": {"price": "1.25500"},
        "takeProfitOrder": {"price": "1.24000"},
        "averageClosePrice": "1.24600",
    })


def test_chain_resolves_via_direct_demo_trade_id(db):
    """Filled row has demo_trade_id=demo-1; sent row exists for the same id."""
    db.save_oanda_audit(_audit(
        "demo-1", "session_time_bias", "sent",
        timestamp="2026-04-28T09:33:00+00:00",  # 74s earlier — out of 5min default
    ))
    db.save_oanda_audit(_audit(
        "demo-1", "scalp", "filled",
        oanda_trade_id="OANDA-1",
        timestamp="2026-04-28T09:34:14+00:00",
    ))
    with db._safe_conn() as conn:
        result = resolve_strategy_via_audit_chain(conn, "OANDA-1")
    assert result == "session_time_bias", (
        f"chain should resolve to direct demo_trade_id sent row; got {result!r}"
    )


def test_chain_resolves_pyr_child_via_parent(db):
    """PYR child filled row has demo_trade_id=PYR_<parent>.

    The parent's sent row is at parent's open time (far outside any window),
    but is reachable via the ``PYR_`` prefix strip. This is the canonical
    historical-orphan case described in queued task
    20260519-1832-fix-pyr-strategy-attribution-and-dedup.
    """
    # Parent fires at 09:00 with strategy name; PYR child fires at 09:34
    # (34 min later — far outside 5min window).
    db.save_oanda_audit(_audit(
        "parent-1", "doji_breakout", "sent", units=1000,
        timestamp="2026-04-28T09:00:00+00:00",
    ))
    # PYR child's filled row carries demo_trade_id='PYR_parent-1'.
    db.save_oanda_audit(_audit(
        "PYR_parent-1", "scalp", "filled",
        oanda_trade_id="OANDA-PYR-1", units=10000,
        timestamp="2026-04-28T09:34:14+00:00",
    ))
    with db._safe_conn() as conn:
        result = resolve_strategy_via_audit_chain(conn, "OANDA-PYR-1")
    assert result == "doji_breakout", (
        f"PYR chain should resolve to parent sent row; got {result!r}"
    )


def test_chain_returns_empty_when_no_sent_row(db):
    """When no sent row exists anywhere, chain returns empty string."""
    db.save_oanda_audit(_audit(
        "demo-2", "scalp", "filled",
        oanda_trade_id="OANDA-2",
    ))
    with db._safe_conn() as conn:
        result = resolve_strategy_via_audit_chain(conn, "OANDA-2")
    assert result == "", (
        f"chain must return '' when no sent row; got {result!r}"
    )


def test_chain_rejects_mode_label_in_sent_row(db):
    """A sent row whose entry_type is a MODE label (not a strategy) is
    rejected — this prevents legitimately-empty sent rows from polluting
    the strategy column with operational mode names.
    """
    db.save_oanda_audit(_audit("demo-3", "scalp", "sent"))  # mode in sent row
    db.save_oanda_audit(_audit(
        "demo-3", "daytrade", "filled", oanda_trade_id="OANDA-3",
    ))
    with db._safe_conn() as conn:
        result = resolve_strategy_via_audit_chain(conn, "OANDA-3")
    assert result == "", (
        f"chain must reject mode label in sent row; got {result!r}"
    )


def test_chain_returns_empty_for_unknown_oanda_trade_id(db):
    """No audit rows at all → empty result, no exception."""
    with db._safe_conn() as conn:
        result = resolve_strategy_via_audit_chain(conn, "OANDA-NONEXISTENT")
    assert result == ""


def test_chain_returns_empty_for_empty_input(db):
    """Empty oanda_trade_id input → empty result without DB hit."""
    with db._safe_conn() as conn:
        assert resolve_strategy_via_audit_chain(conn, "") == ""


def test_backfill_e2e_chain_first_then_window(db):
    """End-to-end: 3 orphan oanda_trades — one resolves via PYR chain,
    one via direct demo_trade_id chain, one via time-window fallback.

    Validates the priority order (chain before window) and the source
    tagging on the result.
    """
    # Order matters: ``upsert_oanda_trade`` also calls the time-window resolver
    # at insert time and writes strategy if found. To simulate the historical
    # orphan condition we seed trades FIRST (strategy=NULL) and audit rows
    # AFTER, so the backfill is the only path that can attribute strategy.

    # 1) PYR orphan — resolves via parent chain
    _seed_oanda_trade(db, "OANDA-A", open_time="2026-04-28T09:34:14Z",
                     direction="BUY", realized_pl=-21.3)
    db.save_oanda_audit(_audit(
        "p1", "doji_breakout", "sent", units=1000,
        timestamp="2026-04-28T09:00:00+00:00",
    ))
    db.save_oanda_audit(_audit(
        "PYR_p1", "scalp", "filled",
        oanda_trade_id="OANDA-A", units=10000,
        timestamp="2026-04-28T09:34:14+00:00",
    ))

    # 2) Direct chain — sent row matches by demo_trade_id but is outside the
    # 5min window (so window fallback would also fail, chain is required).
    _seed_oanda_trade(db, "OANDA-B", open_time="2026-04-28T09:34:14Z",
                     direction="SELL", realized_pl=+5.6)
    db.save_oanda_audit(_audit(
        "d2", "session_time_bias", "sent",
        timestamp="2026-04-28T09:20:00+00:00",  # 14min before open
    ))
    db.save_oanda_audit(_audit(
        "d2", "scalp", "filled", oanda_trade_id="OANDA-B",
        timestamp="2026-04-28T09:34:14+00:00",
    ))

    # 3) Window-fallback only — no demo_trade_id chain (the filled row's
    # demo_trade_id has no matching sent), but a sent row exists nearby in
    # the time window with matching instrument+direction.
    _seed_oanda_trade(db, "OANDA-C",
                     instrument="USD_JPY", direction="BUY",
                     open_time="2026-05-08T13:17:07Z", realized_pl=+11.0)
    db.save_oanda_audit(_audit(
        "other-id", "trendline_sweep", "sent",
        direction="BUY", instrument="USD_JPY",
        timestamp="2026-05-08T13:16:00+00:00",
    ))
    db.save_oanda_audit(_audit(
        "demo-c", "scalp", "filled", oanda_trade_id="OANDA-C",
        direction="BUY", instrument="USD_JPY",
        timestamp="2026-05-08T13:17:07+00:00",
    ))

    # Dry-run first (no UPDATE).
    dry = _scan_missing(db, window_minutes=5, apply=False)
    assert dry["scanned_missing"] == 3
    assert dry["would_update_count"] == 3
    assert dry["chain_hits"] == 2
    assert dry["window_hits"] == 1

    # Confirm DB column still NULL/empty (dry-run did not write).
    with db._safe_conn() as conn:
        rows = conn.execute(
            "SELECT oanda_trade_id, strategy FROM oanda_trades "
            "WHERE oanda_trade_id IN (?, ?, ?) ORDER BY oanda_trade_id",
            ("OANDA-A", "OANDA-B", "OANDA-C"),
        ).fetchall()
    assert all(not (r["strategy"] or "").strip() for r in rows), (
        f"dry-run must NOT write strategy: {[dict(r) for r in rows]}"
    )

    # Apply for real.
    applied = _scan_missing(db, window_minutes=5, apply=True)
    assert applied["updated_count"] == 3

    with db._safe_conn() as conn:
        result = {
            r["oanda_trade_id"]: r["strategy"]
            for r in conn.execute(
                "SELECT oanda_trade_id, strategy FROM oanda_trades "
                "WHERE oanda_trade_id IN (?, ?, ?)",
                ("OANDA-A", "OANDA-B", "OANDA-C"),
            ).fetchall()
        }
    assert result["OANDA-A"] == "doji_breakout"
    assert result["OANDA-B"] == "session_time_bias"
    assert result["OANDA-C"] == "trendline_sweep"
