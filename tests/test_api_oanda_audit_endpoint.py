import sqlite3
from decimal import Decimal

import app as app_mod
from modules.demo_db import DemoDB
from modules.oanda_bridge import OandaBridge


def _swap_oanda_bridge(monkeypatch, bridge):
    monkeypatch.setattr(app_mod._demo_trader, "_oanda", bridge)


def _insert_audit_row(db: DemoDB, trade_id: str, sr_strength=0.7, block_reason=""):
    with db._safe_conn() as conn:
        conn.execute(
            """
            INSERT INTO oanda_audit (
                timestamp, demo_trade_id, entry_type, direction, instrument,
                units, is_live, bridge_status, block_reason, oanda_trade_id,
                sr_strength, sr_touches, sr_days_span, sr_is_strong, sr_distance_atr
            ) VALUES (
                '2026-05-26T15:42:00+00:00', ?, 'sr_anti_hunt_bounce', 'BUY',
                'USD_JPY', 1000, 1, 'sent', ?, 'OANDA-1',
                ?, 5, 12.5, 1, 0.8
            )
            """,
            (trade_id, block_reason, sr_strength),
        )
        conn.commit()


def test_api_oanda_audit_limit_20_returns_json(tmp_path, flask_client, monkeypatch):
    db = DemoDB(str(tmp_path / "audit.db"))
    _insert_audit_row(db, "T-20")
    _swap_oanda_bridge(monkeypatch, OandaBridge(db=db))

    response = flask_client.get("/api/oanda/audit?limit=20")
    payload = response.get_json()

    assert response.status_code == 200
    assert set(payload) == {"audit", "total"}
    assert payload["total"] == 1
    assert payload["audit"][0]["demo_trade_id"] == "T-20"
    assert payload["audit"][0]["is_live"] is True


def test_api_oanda_audit_limit_200_serializes_drifted_sqlite_values(
    tmp_path, flask_client, monkeypatch
):
    db = DemoDB(str(tmp_path / "audit.db"))
    _insert_audit_row(
        db,
        "T-BLOB",
        sr_strength=float("nan"),
        block_reason=sqlite3.Binary(b"gate:\xff"),
    )
    _swap_oanda_bridge(monkeypatch, OandaBridge(db=db))

    response = flask_client.get("/api/oanda/audit?limit=200")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["audit"][0]["block_reason"] == "gate:�"
    assert payload["audit"][0]["sr_strength"] is None


def test_api_oanda_audit_memory_fallback_serializes_decimal(flask_client, monkeypatch):
    bridge = OandaBridge(db=None)
    bridge._execution_audit.append(
        {
            "timestamp": "2026-05-26T15:42:00+00:00",
            "demo_trade_id": "T-DEC",
            "entry_type": "manual",
            "bridge_status": "sent",
            "pnl": Decimal("12.34"),
            "sr_meta": {"distance_atr": Decimal("1.25")},
        }
    )
    _swap_oanda_bridge(monkeypatch, bridge)

    response = flask_client.get("/api/oanda/audit?limit=20")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["audit"][0]["pnl"] == 12.34
    assert payload["audit"][0]["sr_meta"]["distance_atr"] == 1.25


def test_api_oanda_audit_empty_table_returns_empty_payload(
    tmp_path, flask_client, monkeypatch
):
    db = DemoDB(str(tmp_path / "audit.db"))
    _swap_oanda_bridge(monkeypatch, OandaBridge(db=db))

    response = flask_client.get("/api/oanda/audit")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload == {"audit": [], "total": 0}
