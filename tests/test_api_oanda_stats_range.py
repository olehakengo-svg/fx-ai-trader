from datetime import datetime, timedelta, timezone

import app as app_mod
from modules.demo_db import DemoDB


def _insert_oanda_trade(db: DemoDB, trade_id: str, instrument: str, open_time: str, realized_pl: float = 100.0):
    with db._safe_conn() as conn:
        conn.execute(
            """
            INSERT INTO oanda_trades (
                oanda_trade_id, instrument, state, direction, initial_units,
                current_units, open_price, close_price, open_time, close_time,
                realized_pl, unrealized_pl, financing, commission, pnl_pips,
                close_reason
            ) VALUES (?, ?, 'CLOSED', 'BUY', 1000, 0, 150.0, 150.1, ?, ?,
                      ?, 0, 0, 0, ?, 'TAKE_PROFIT')
            """,
            (trade_id, instrument, open_time, open_time, realized_pl, realized_pl / 10.0),
        )


def test_oanda_stats_range_filters_and_excludes_xau_by_default(tmp_path, flask_client, monkeypatch):
    db = DemoDB(str(tmp_path / "oanda_stats_range.db"))
    old_db = app_mod._demo_db
    old_db_path = app_mod._db_path

    now = datetime.now(timezone.utc)
    today_row = now - timedelta(hours=1)
    within_7d = now - timedelta(days=5)

    _insert_oanda_trade(db, "pre-fidelity", "USD_JPY", "2026-03-01T00:00:00")
    _insert_oanda_trade(db, "post-fidelity-old", "USD_JPY", "2026-04-15T00:00:00")
    _insert_oanda_trade(db, "within-7d", "USD_JPY", within_7d.strftime("%Y-%m-%dT%H:%M:%S"))
    _insert_oanda_trade(db, "today", "USD_JPY", today_row.strftime("%Y-%m-%dT%H:%M:%S"))
    _insert_oanda_trade(db, "today-xau", "XAU_USD", today_row.strftime("%Y-%m-%dT%H:%M:%S"))

    monkeypatch.setattr(app_mod, "_demo_db", db)
    monkeypatch.setattr(app_mod, "_db_path", db._path)
    try:
        today = flask_client.get("/api/oanda/stats?range=today").get_json()
        seven_days = flask_client.get("/api/oanda/stats?range=7d").get_json()
        thirty_days = flask_client.get("/api/oanda/stats?range=30d").get_json()
        all_time = flask_client.get("/api/oanda/stats?range=all").get_json()
        include_xau = flask_client.get("/api/oanda/stats?range=today&exclude_xau=0").get_json()
    finally:
        app_mod._demo_db = old_db
        app_mod._db_path = old_db_path

    assert today["total"] == 1
    assert seven_days["total"] == 2
    assert thirty_days["total"] == 2
    assert all_time["total"] == 3
    assert len({today["total"], seven_days["total"], all_time["total"]}) == 3
    assert include_xau["total"] == 2

    assert "_db_path" in today
    assert today["_filters"] == {
        "instrument": None,
        "date_from": None,
        "date_to": None,
        "effective_date_from": today["_filters"]["effective_date_from"],
        "all_time": False,
        "rolling_days": 0,
        "exclude_xau": True,
    }
    assert today["_filters"]["effective_date_from"].endswith("T00:00:00")
    assert all_time["_filters"]["effective_date_from"] == "2026-04-08T00:00:00"
