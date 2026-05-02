"""Regression test for the oanda_audit JOIN invariant (audit 2026-05-01 P0-4).

Background: `oanda_audit.entry_type` is dual-purpose. Rows with
`bridge_status='sent'` carry the strategy name (e.g. 'vwap_mean_reversion');
rows with `bridge_status='filled'` carry the OANDA-side mode (e.g. 'PYR_BUY',
'PYR_SELL' for pyramid children). The JOIN in `DemoDB.get_oanda_trades()`
COALESCEs `a.entry_type` as a fallback for `d.entry_type` — without the
`AND a.bridge_status='sent'` filter on the ON clause, the COALESCE silently
substitutes pyramid mode labels for strategy names, polluting Kelly/WR
aggregations downstream.

These tests pin the invariant in two ways:
  1. SQL inspection — the literal `bridge_status = 'sent'` substring must
     appear in the JOIN. If a refactor drops it, this test fails immediately.
  2. End-to-end behavior — when both 'sent' and 'filled' audit rows exist
     for the same demo_trade_id, the strategy column must reflect the 'sent'
     row's entry_type, never the 'filled' row's mode.
"""
from __future__ import annotations

import os
import tempfile

import pytest

from modules.demo_db import DemoDB


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DemoDB(db_path=path)
    os.unlink(path)


def _audit_entry(demo_trade_id: str, entry_type: str, bridge_status: str,
                 oanda_trade_id: str = "", direction: str = "BUY",
                 instrument: str = "USD_JPY") -> dict:
    return {
        "timestamp": "2026-05-01T12:00:00Z",
        "demo_trade_id": demo_trade_id,
        "entry_type": entry_type,
        "direction": direction,
        "instrument": instrument,
        "units": 100,
        "is_live": True,
        "bridge_status": bridge_status,
        "block_reason": "",
        "oanda_trade_id": oanda_trade_id,
    }


def _insert_oanda_trade_row(conn, oanda_id: str, instrument: str = "USD_JPY",
                            state: str = "CLOSED") -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO oanda_trades
            (oanda_trade_id, instrument, state, direction,
             initial_units, current_units, open_price, close_price,
             open_time, close_time, realized_pl, unrealized_pl,
             financing, commission, stop_loss, take_profit,
             trailing_sl, pnl_pips, close_reason, margin_used,
             raw_json, synced_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
        """,
        (oanda_id, instrument, state, "BUY", 100, 100, 150.0, 150.5,
         "2026-05-01T12:00:00Z", "2026-05-01T12:30:00Z", 5.0, 0.0,
         0.0, 0.0, 149.5, 151.0, 0.0, 50.0, "TAKE_PROFIT", 100.0,
         "{}"),
    )
    conn.commit()


def test_join_clause_contains_bridge_status_filter():
    """SQL inspection: the literal filter MUST be in the JOIN.

    Audit 2026-05-01 P0-4: we lock this string in a regression test so that
    a future refactor cannot silently drop the filter.
    """
    import inspect
    src = inspect.getsource(DemoDB.get_oanda_trades)
    assert "a.bridge_status = 'sent'" in src, (
        "DemoDB.get_oanda_trades JOIN must filter oanda_audit by "
        "bridge_status='sent' to avoid mixing PYR_* mode labels into the "
        "strategy column. See audit 2026-05-01 Pillar 3.1."
    )


def test_strategy_resolves_to_sent_not_filled(db):
    """When both 'sent' (strategy='vwap_mean_reversion') and 'filled'
    (entry_type='PYR_BUY' = mode) audit rows exist for the same
    demo_trade_id, the JOIN must return the 'sent' row's entry_type.
    """
    # Open a demo trade WITHOUT entry_type populated on demo_trades
    # (simulate the strategy=NULL on demo case from the audit memo).
    # We bypass open_trade since it always sets entry_type — instead
    # we craft the row directly to leave entry_type='' so that the
    # COALESCE fallback to oanda_audit.entry_type is exercised.
    demo_trade_id = "DEMO_TEST_001"
    oanda_trade_id = "OANDA_TEST_001"
    with db._lock:  # noqa: SLF001 — test reaches into the DAO on purpose
        with db._safe_conn() as conn:
            # entry_type is NULL on demo_trades → COALESCE falls through to
            # oanda_audit.entry_type, exercising the JOIN filter we are
            # locking in.
            conn.execute(
                """
                INSERT INTO demo_trades
                    (trade_id, direction, entry_price, sl, tp, entry_type,
                     confidence, status, oanda_trade_id, is_shadow)
                VALUES (?, 'BUY', 150.0, 149.5, 151.0, NULL, 50,
                        'CLOSED', ?, 0)
                """,
                (demo_trade_id, oanda_trade_id),
            )
            _insert_oanda_trade_row(conn, oanda_trade_id)

    # 'filled' row arrives FIRST (worst case — naive JOIN without filter
    # would prefer it).
    db.save_oanda_audit(_audit_entry(
        demo_trade_id, entry_type="PYR_BUY", bridge_status="filled",
        oanda_trade_id=oanda_trade_id,
    ))
    # Then the canonical 'sent' row with the strategy name.
    db.save_oanda_audit(_audit_entry(
        demo_trade_id, entry_type="vwap_mean_reversion", bridge_status="sent",
    ))

    rows = db.get_oanda_trades(state="CLOSED", limit=10)
    matching = [r for r in rows if r.get("oanda_trade_id") == oanda_trade_id]
    assert matching, "expected oanda_trade row to be returned"
    assert matching[0]["strategy"] == "vwap_mean_reversion", (
        f"strategy column leaked PYR_* mode label: got "
        f"{matching[0]['strategy']!r}"
    )
