import sqlite3

from modules.demo_db import DemoDB
from scripts.check_flag_drift_backfill_safety import analyze_db


def _insert_trade(conn, trade_id, *, entry_time, instrument="USD_JPY",
                  is_shadow=0, oanda_trade_id="", pnl=-1.0):
    conn.execute(
        """INSERT INTO demo_trades
           (trade_id, status, direction, entry_price, entry_time, exit_price,
            exit_time, sl, tp, pnl_pips, pnl_r, outcome, entry_type,
            confidence, is_shadow, oanda_trade_id, instrument)
           VALUES (?, 'CLOSED', 'BUY', 150.0, ?, 149.99, ?, 149.5, 150.5,
                   ?, -0.1, 'LOSS', 'trendline_sweep', 80, ?, ?, ?)""",
        (trade_id, entry_time, entry_time, pnl, is_shadow, oanda_trade_id, instrument),
    )


def _fetch_flags(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return {
            row["trade_id"]: dict(row)
            for row in conn.execute(
                "SELECT trade_id, is_shadow, flag_drift_backfilled FROM demo_trades"
            )
        }
    finally:
        conn.close()


def test_flag_drift_backfill_is_idempotent_and_respects_boundaries(tmp_path):
    db_path = tmp_path / "flag-drift.db"
    db = DemoDB(str(db_path))
    with db._safe_conn() as conn:
        _insert_trade(conn, "post-fx-drift", entry_time="2026-04-08T00:00:00")
        _insert_trade(conn, "pre-cutoff", entry_time="2026-04-07T23:59:59")
        _insert_trade(conn, "xau-drift", entry_time="2026-04-08T00:00:00", instrument="XAU_USD")
        _insert_trade(conn, "already-shadow", entry_time="2026-04-08T00:00:00", is_shadow=1)
        _insert_trade(conn, "true-live", entry_time="2026-04-08T00:00:00", oanda_trade_id="OANDA-1")
        conn.commit()

    rerun = DemoDB(str(db_path))
    rows = _fetch_flags(db_path)

    assert rows["post-fx-drift"]["is_shadow"] == 1
    assert rows["post-fx-drift"]["flag_drift_backfilled"] == 1
    assert rows["pre-cutoff"]["is_shadow"] == 0
    assert rows["pre-cutoff"]["flag_drift_backfilled"] == 0
    assert rows["xau-drift"]["is_shadow"] == 0
    assert rows["xau-drift"]["flag_drift_backfilled"] == 0
    assert rows["already-shadow"]["is_shadow"] == 1
    assert rows["already-shadow"]["flag_drift_backfilled"] == 0
    assert rows["true-live"]["is_shadow"] == 0
    assert rows["true-live"]["flag_drift_backfilled"] == 0
    assert rerun.get_flag_drift_backfill_status()["last_startup_backfill_result"]["fixed_count"] == 1

    third = DemoDB(str(db_path))
    assert third.get_flag_drift_backfill_status()["last_startup_backfill_result"]["fixed_count"] == 0


def test_flag_drift_backfill_pauses_when_filled_audit_row_exists(tmp_path):
    db_path = tmp_path / "unsafe.db"
    db = DemoDB(str(db_path))
    with db._safe_conn() as conn:
        _insert_trade(conn, "filled-missing-id", entry_time="2026-04-08T00:00:00")
        conn.execute(
            """INSERT INTO oanda_audit
               (timestamp, demo_trade_id, entry_type, bridge_status, oanda_trade_id)
               VALUES ('2026-05-11T00:00:00+00:00', 'filled-missing-id',
                       'trendline_sweep', 'filled', 'OANDA-AUDIT-1')"""
        )
        conn.commit()

    rerun = DemoDB(str(db_path))
    rows = _fetch_flags(db_path)
    status = rerun.get_flag_drift_backfill_status()["last_startup_backfill_result"]

    assert rows["filled-missing-id"]["is_shadow"] == 0
    assert rows["filled-missing-id"]["flag_drift_backfilled"] == 0
    assert status["status"] == "unsafe"
    assert status["unsafe_filled_audit_count"] == 1


def test_check_flag_drift_backfill_safety_reports_safe_and_unsafe(tmp_path):
    safe_path = tmp_path / "safe.db"
    safe_db = DemoDB(str(safe_path))
    with safe_db._safe_conn() as conn:
        _insert_trade(conn, "safe-drift", entry_time="2026-04-08T00:00:00", pnl=-2.5)
        conn.commit()

    safe = analyze_db(str(safe_path))
    assert safe["verdict"] == "SAFE"
    assert safe["q1"]["n"] == 1
    assert safe["q3"]["n"] == 0

    unsafe_path = tmp_path / "unsafe-script.db"
    unsafe_db = DemoDB(str(unsafe_path))
    with unsafe_db._safe_conn() as conn:
        _insert_trade(conn, "unsafe-drift", entry_time="2026-04-08T00:00:00")
        conn.execute(
            """INSERT INTO oanda_audit
               (timestamp, demo_trade_id, entry_type, bridge_status, oanda_trade_id)
               VALUES ('2026-05-11T00:00:00+00:00', 'unsafe-drift',
                       'trendline_sweep', 'filled', 'OANDA-AUDIT-2')"""
        )
        conn.commit()

    unsafe = analyze_db(str(unsafe_path))
    assert unsafe["verdict"] == "UNSAFE"
    assert unsafe["q3"]["n"] == 1
