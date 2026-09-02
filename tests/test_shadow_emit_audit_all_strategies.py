import pytest

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


SR_META = {
    "strength": 0.83,
    "touches": 9,
    "days_span": 3.5,
    "is_strong": True,
    "distance_atr": 0.42,
}


def _open_shadow_emit(trader, *, entry_type, instrument, sr_meta=None):
    return trader._open_shadow_emit_trade(
        direction="BUY",
        entry_price=1.2345,
        sl=1.2300,
        tp=1.2450,
        entry_type=entry_type,
        confidence=62,
        tf="1h",
        reasons=["[SHADOW_EMIT] audit regression"],
        score=1.1,
        mode="daytrade",
        instrument=instrument,
        sr_meta=sr_meta,
    )


def _audit_row(db, trade_id):
    with db._safe_conn() as conn:
        return conn.execute(
            "SELECT * FROM oanda_audit WHERE demo_trade_id=?",
            (trade_id,),
        ).fetchone()


@pytest.mark.parametrize(
    ("entry_type", "instrument"),
    [
        ("eurgbp_daily_mr", "EUR_GBP"),
        ("price_shock_rev_usd_cad_h1_long", "USD_CAD"),
    ],
)
def test_shadow_emit_non_sr_strategy_writes_oanda_audit(tmp_path, entry_type, instrument):
    db = DemoDB(str(tmp_path / "shadow-emit-audit.db"))
    trader = DemoTrader(db)

    trade_id = _open_shadow_emit(
        trader,
        entry_type=entry_type,
        instrument=instrument,
    )

    audit = _audit_row(db, trade_id)

    assert DemoTrader._should_audit_shadow_emit(entry_type) is True
    assert audit is not None
    assert audit["entry_type"] == entry_type
    assert audit["instrument"] == instrument
    assert audit["bridge_status"] == "skipped"
    # 2026-09-02 (rule:R3): shadow-emit rows self-describe their hardcoded units=0
    # via a "(shadow_emit_no_lot)" suffix; the "shadow_tracking" prefix stays so
    # existing startswith()-based guards/tools remain compatible.
    assert audit["block_reason"] == "shadow_tracking(shadow_emit_no_lot)"
    assert audit["block_reason"].startswith("shadow_tracking")
    assert audit["units"] == 0  # marker only — not an order size
    assert audit["is_live"] == 0
    assert audit["sr_strength"] is None


def test_shadow_emit_sr_strategy_preserves_sr_meta_in_oanda_audit(tmp_path):
    db = DemoDB(str(tmp_path / "shadow-emit-audit.db"))
    trader = DemoTrader(db)

    trade_id = _open_shadow_emit(
        trader,
        entry_type="sr_break_retest",
        instrument="USD_JPY",
        sr_meta=SR_META,
    )

    audit = _audit_row(db, trade_id)

    assert DemoTrader._should_audit_shadow_emit("sr_break_retest") is True
    assert audit is not None
    assert audit["entry_type"] == "sr_break_retest"
    assert audit["instrument"] == "USD_JPY"
    assert audit["bridge_status"] == "skipped"
    assert audit["block_reason"] == "shadow_tracking(shadow_emit_no_lot)"
    assert audit["block_reason"].startswith("shadow_tracking")
    assert audit["units"] == 0  # marker only — not an order size
    assert audit["is_live"] == 0
    assert audit["sr_strength"] == SR_META["strength"]
    assert audit["sr_touches"] == SR_META["touches"]
    assert audit["sr_days_span"] == SR_META["days_span"]
    assert audit["sr_is_strong"] == 1
    assert audit["sr_distance_atr"] == SR_META["distance_atr"]
