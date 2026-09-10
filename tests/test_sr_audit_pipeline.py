from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


def _open_sr_shadow_emit(trader, *, entry_type, instrument, direction, entry, sl, tp):
    return trader._open_shadow_emit_trade(
        direction=direction,
        entry_price=entry,
        sl=sl,
        tp=tp,
        entry_type=entry_type,
        confidence=61,
        tf="15m",
        reasons=["[SHADOW_EMIT] regression"],
        score=1.2,
        mode="daytrade",
        instrument=instrument,
        dow_regime="test_dow",
        v2_regime="test_v2",
        confluence_score="1",
        confluence_details="test",
        sr_meta={
            "strength": 0.8,
            "touches": 12,
            "days_span": 4.5,
            "is_strong": True,
            "distance_atr": 0.6,
        },
    )


def _audit_row(db, trade_id):
    with db._safe_conn() as conn:
        return conn.execute(
            "SELECT * FROM oanda_audit WHERE demo_trade_id=?",
            (trade_id,),
        ).fetchone()


def _trade_row(db, trade_id):
    with db._safe_conn() as conn:
        return conn.execute(
            "SELECT * FROM demo_trades WHERE trade_id=?",
            (trade_id,),
        ).fetchone()


def test_sr_anti_hunt_shadow_emit_writes_oanda_audit(tmp_path):
    db = DemoDB(str(tmp_path / "sr-audit.db"))
    trader = DemoTrader(db)

    trade_id = _open_sr_shadow_emit(
        trader,
        entry_type="sr_anti_hunt_bounce",
        instrument="USD_JPY",
        direction="BUY",
        entry=156.10,
        sl=155.80,
        tp=156.70,
    )

    trade = _trade_row(db, trade_id)
    audit = _audit_row(db, trade_id)

    assert trade["entry_type"] == "sr_anti_hunt_bounce"
    assert trade["instrument"] == "USD_JPY"
    assert trade["is_shadow"] == 1
    assert audit["entry_type"] == "sr_anti_hunt_bounce"
    assert audit["instrument"] == "USD_JPY"
    assert audit["bridge_status"] == "skipped"
    # 2026-09-02 (rule:R3): units=0 self-described; prefix preserved for tools.
    assert audit["block_reason"] == "shadow_tracking(shadow_emit_no_lot)"
    assert audit["block_reason"].startswith("shadow_tracking")
    assert audit["is_live"] == 0
    assert audit["sr_is_strong"] == 1


def test_sr_fib_confluence_shadow_emit_writes_oanda_audit(tmp_path):
    db = DemoDB(str(tmp_path / "sr-audit.db"))
    trader = DemoTrader(db)

    trade_id = _open_sr_shadow_emit(
        trader,
        entry_type="sr_fib_confluence",
        instrument="GBP_USD",
        direction="SELL",
        entry=1.3400,
        sl=1.3440,
        tp=1.3320,
    )

    trade = _trade_row(db, trade_id)
    audit = _audit_row(db, trade_id)

    assert trade["entry_type"] == "sr_fib_confluence"
    assert trade["instrument"] == "GBP_USD"
    assert trade["is_shadow"] == 1
    assert audit["entry_type"] == "sr_fib_confluence"
    assert audit["instrument"] == "GBP_USD"
    assert audit["bridge_status"] == "skipped"
    assert audit["block_reason"] == "shadow_tracking(shadow_emit_no_lot)"
    assert audit["block_reason"].startswith("shadow_tracking")
    assert audit["is_live"] == 0
    assert audit["sr_strength"] == 0.8
