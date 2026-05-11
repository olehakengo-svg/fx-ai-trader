import sqlite3

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader
from scripts.check_force_demoted_leak_safety import analyze_db


def _insert_trade(conn, trade_id, *, entry_type="vwap_mean_reversion",
                  entry_time="2026-04-20T00:00:00+00:00",
                  instrument="USD_JPY", is_shadow=0,
                  oanda_trade_id="OANDA-1", pnl=-1.0):
    conn.execute(
        """INSERT INTO demo_trades
           (trade_id, status, direction, entry_price, entry_time, exit_price,
            exit_time, sl, tp, pnl_pips, pnl_r, outcome, entry_type,
            confidence, is_shadow, oanda_trade_id, instrument)
           VALUES (?, 'CLOSED', 'BUY', 150.0, ?, 149.99, ?, 149.5, 150.5,
                   ?, -0.1, 'LOSS', ?, 80, ?, ?, ?)""",
        (trade_id, entry_time, entry_time, pnl, entry_type,
         is_shadow, oanda_trade_id, instrument),
    )


def _fetch_rows(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return {
            row["trade_id"]: dict(row)
            for row in conn.execute(
                "SELECT trade_id, is_shadow, force_demoted_live_leak FROM demo_trades"
            )
        }
    finally:
        conn.close()


def test_force_demoted_leak_backfill_is_idempotent_and_respects_boundaries(tmp_path):
    db_path = tmp_path / "force-leak.db"
    db = DemoDB(str(db_path))
    with db._safe_conn() as conn:
        _insert_trade(conn, "leak")
        _insert_trade(conn, "pre-cutoff", entry_time="2026-04-07T23:59:59+00:00")
        _insert_trade(conn, "xau", instrument="XAU_USD")
        _insert_trade(conn, "already-shadow", is_shadow=1, oanda_trade_id="")
        _insert_trade(conn, "non-force", entry_type="trendline_sweep")
        conn.commit()

    rerun = DemoDB(str(db_path))
    rows = _fetch_rows(db_path)

    assert rows["leak"]["is_shadow"] == 1
    assert rows["leak"]["force_demoted_live_leak"] == 1
    assert rows["pre-cutoff"]["is_shadow"] == 0
    assert rows["pre-cutoff"]["force_demoted_live_leak"] == 0
    assert rows["xau"]["is_shadow"] == 0
    assert rows["xau"]["force_demoted_live_leak"] == 0
    assert rows["already-shadow"]["is_shadow"] == 1
    assert rows["already-shadow"]["force_demoted_live_leak"] == 0
    assert rows["non-force"]["is_shadow"] == 0
    assert rows["non-force"]["force_demoted_live_leak"] == 0
    assert rerun.get_force_demoted_leak_backfill_status()["last_startup_backfill_result"]["fixed_count"] == 1

    third = DemoDB(str(db_path))
    assert third.get_force_demoted_leak_backfill_status()["last_startup_backfill_result"]["fixed_count"] == 0


def test_force_demoted_leak_backfill_pauses_on_post_rule_filled_audit(tmp_path):
    db_path = tmp_path / "unsafe-force-leak.db"
    db = DemoDB(str(db_path))
    with db._safe_conn() as conn:
        _insert_trade(conn, "new-live-leak", entry_time="2026-05-11T01:00:00+00:00")
        conn.execute(
            """INSERT INTO oanda_audit
               (timestamp, demo_trade_id, entry_type, bridge_status, oanda_trade_id)
               VALUES ('2026-05-11T01:00:10+00:00', 'new-live-leak',
                       'vwap_mean_reversion', 'filled', 'OANDA-1')"""
        )
        conn.commit()

    rerun = DemoDB(str(db_path))
    rows = _fetch_rows(db_path)
    status = rerun.get_force_demoted_leak_backfill_status()["last_startup_backfill_result"]

    assert rows["new-live-leak"]["is_shadow"] == 0
    assert rows["new-live-leak"]["force_demoted_live_leak"] == 0
    assert status["status"] == "unsafe"
    assert status["unsafe_post_rule_fill_count"] == 1


def test_check_force_demoted_leak_safety_reports_safe_and_unsafe(tmp_path):
    safe_path = tmp_path / "safe-force.db"
    safe_db = DemoDB(str(safe_path))
    with safe_db._safe_conn() as conn:
        _insert_trade(conn, "safe-leak", pnl=-2.5)
        conn.commit()

    safe = analyze_db(str(safe_path))
    assert safe["verdict"] == "SAFE"
    assert safe["q1"]["n"] == 1
    assert safe["q4"]["unsafe_post_rule_fill_count"] == 0

    unsafe_path = tmp_path / "unsafe-force-script.db"
    unsafe_db = DemoDB(str(unsafe_path))
    with unsafe_db._safe_conn() as conn:
        _insert_trade(conn, "unsafe-leak", entry_time="2026-05-11T01:00:00+00:00")
        conn.execute(
            """INSERT INTO oanda_audit
               (timestamp, demo_trade_id, entry_type, bridge_status, oanda_trade_id)
               VALUES ('2026-05-11T01:00:10+00:00', 'unsafe-leak',
                       'vwap_mean_reversion', 'filled', 'OANDA-2')"""
        )
        conn.commit()

    unsafe = analyze_db(str(unsafe_path))
    assert unsafe["verdict"] == "UNSAFE"
    assert unsafe["q4"]["unsafe_post_rule_fill_count"] == 1


def test_force_demoted_final_gate_overrides_late_live_bypass():
    trader = DemoTrader.__new__(DemoTrader)
    logs = []
    trader._add_log = logs.append

    is_shadow, is_promoted, shadow_at_open = trader._apply_force_demoted_final_gate(
        entry_type="vwap_mean_reversion",
        is_shadow=False,
        is_promoted=True,
        shadow_at_open=False,
    )

    assert is_shadow is True
    assert is_promoted is False
    assert shadow_at_open is True
    assert any("[FORCE_DEMOTED_GATE] vwap_mean_reversion forced to shadow" in msg for msg in logs)
