from __future__ import annotations

from modules.demo_db import DemoDB


def _audit_entry(timestamp, entry_type, status, *, oanda_trade_id="", units=10000):
    return {
        "timestamp": timestamp,
        "demo_trade_id": f"audit-{status}-{timestamp}",
        "entry_type": entry_type,
        "direction": "BUY",
        "instrument": "GBP_USD",
        "units": units,
        "is_live": True,
        "bridge_status": status,
        "block_reason": "",
        "oanda_trade_id": oanda_trade_id,
    }


def _oanda_trade(oanda_trade_id="OANDA-NEAREST-1"):
    return {
        "id": oanda_trade_id,
        "instrument": "GBP_USD",
        "state": "CLOSED",
        "initialUnits": "10000",
        "currentUnits": "0",
        "price": "1.25000",
        "openTime": "2026-05-19T12:00:00Z",
        "closeTime": "2026-05-19T12:20:00Z",
        "realizedPL": "-5.7",
        "unrealizedPL": "0",
        "financing": "0",
        "commission": "0",
        "marginUsed": "100",
        "stopLossOrder": {"price": "1.24500"},
        "takeProfitOrder": {"price": "1.26000"},
        "averageClosePrice": "1.24943",
    }


def test_closed_oanda_trade_strategy_resolves_from_nearest_sent_not_filled(tmp_path):
    db = DemoDB(str(tmp_path / "nearest.db"))
    db.save_oanda_audit(_audit_entry(
        "2026-05-19T11:59:30+00:00",
        "vix_carry_unwind",
        "sent",
        units=1000,
    ))
    db.save_oanda_audit(_audit_entry(
        "2026-05-19T12:00:00+00:00",
        "daytrade",
        "filled",
        oanda_trade_id="OANDA-NEAREST-1",
        units=10000,
    ))

    db.upsert_oanda_trade(_oanda_trade())

    rows = db.get_oanda_trades(state="CLOSED", limit=10)
    row = next(r for r in rows if r["oanda_trade_id"] == "OANDA-NEAREST-1")
    assert row["strategy"] == "vix_carry_unwind"

    with db._safe_conn() as conn:
        stored = conn.execute(
            "SELECT strategy FROM oanda_trades WHERE oanda_trade_id=?",
            ("OANDA-NEAREST-1",),
        ).fetchone()
    assert stored["strategy"] == "vix_carry_unwind"
