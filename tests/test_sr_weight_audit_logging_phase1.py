import sqlite3

from modules.demo_db import DemoDB
from modules.oanda_bridge import OandaBridge
from strategies.base import Candidate


SR_COLUMNS = {
    "sr_strength",
    "sr_touches",
    "sr_days_span",
    "sr_is_strong",
    "sr_distance_atr",
}


def test_oanda_audit_sr_columns_are_created_and_migration_is_idempotent(tmp_path):
    db = DemoDB(str(tmp_path / "audit.db"))
    db._init_tables()

    with db._safe_conn() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(oanda_audit)")}

    assert SR_COLUMNS <= columns


def test_oanda_add_audit_without_sr_meta_keeps_columns_null(tmp_path):
    db = DemoDB(str(tmp_path / "audit.db"))
    bridge = OandaBridge(db=db)

    bridge._add_audit(
        demo_trade_id="T-NULL",
        entry_type="engulfing_bb",
        is_live=True,
        bridge_status="sent",
        block_reason="",
        direction="BUY",
        instrument="USD_JPY",
        units=1000,
    )

    with db._safe_conn() as conn:
        row = conn.execute(
            "SELECT sr_strength, sr_touches, sr_days_span, sr_is_strong, sr_distance_atr "
            "FROM oanda_audit WHERE demo_trade_id='T-NULL'"
        ).fetchone()

    assert dict(row) == {
        "sr_strength": None,
        "sr_touches": None,
        "sr_days_span": None,
        "sr_is_strong": None,
        "sr_distance_atr": None,
    }


def test_oanda_add_audit_round_trips_sr_meta(tmp_path):
    db = DemoDB(str(tmp_path / "audit.db"))
    bridge = OandaBridge(db=db)

    bridge._add_audit(
        demo_trade_id="T-SR",
        entry_type="dual_sr_bounce",
        is_live=True,
        bridge_status="sent",
        block_reason="",
        direction="BUY",
        instrument="USD_JPY",
        units=1000,
        sr_meta={
            "strength": 0.82,
            "touches": 95,
            "days_span": 33.6,
            "is_strong": True,
            "distance_atr": 1.2,
        },
    )

    with db._safe_conn() as conn:
        row = conn.execute(
            "SELECT sr_strength, sr_touches, sr_days_span, sr_is_strong, sr_distance_atr "
            "FROM oanda_audit WHERE demo_trade_id='T-SR'"
        ).fetchone()

    assert dict(row) == {
        "sr_strength": 0.82,
        "sr_touches": 95,
        "sr_days_span": 33.6,
        "sr_is_strong": 1,
        "sr_distance_atr": 1.2,
    }


def test_candidate_sr_meta_from_level_contains_required_keys():
    level = {
        "price": 150.25,
        "strength": 0.74,
        "touches": 12,
        "days_span": 8.5,
        "is_strong": True,
    }

    meta = Candidate.sr_meta_from_level(level, signal_price=150.10, atr_at_signal=0.05)

    assert meta == {
        "strength": 0.74,
        "touches": 12,
        "days_span": 8.5,
        "is_strong": True,
        "distance_atr": 3.0,
    }


def test_sr_strategy_audit_path_passes_sr_meta_to_add_audit(monkeypatch):
    # Resilient import: tools/scalp_*.py may have monkey-patched
    # modules.demo_trader.DemoTrader with a stub during the same
    # test session. Reload the module so we always exercise the real
    # DemoTrader._add_oanda_audit wrapper.
    import importlib
    import modules.demo_trader as _demo_trader_module

    importlib.reload(_demo_trader_module)
    DemoTrader = _demo_trader_module.DemoTrader

    calls = []

    class DummyOanda:
        active = False

        def is_mode_allowed(self, _mode):
            return False

        def get_strategy_mode(self, _entry_type):
            return "off"

        def _add_audit(self, **kwargs):
            calls.append(kwargs)

    trader = DemoTrader.__new__(DemoTrader)
    trader._oanda = DummyOanda()
    sr_meta = {
        "strength": 0.7,
        "touches": 50,
        "days_span": 20.0,
        "is_strong": True,
        "distance_atr": 0.4,
    }

    for strategy in (
        "dual_sr_bounce",
        "sr_anti_hunt_bounce",
        "dt_sr_channel_reversal",
        "strong_sr_breakout",
        "sr_channel_reversal",
        "sr_fib_confluence",
    ):
        trader._add_oanda_audit(
            trade_id=f"T-{strategy}",
            entry_type=strategy,
            is_live=False,
            bridge_status="skipped",
            block_reason="test",
            direction="BUY",
            instrument="USD_JPY",
            units=1000,
            sr_meta=sr_meta,
        )

    assert len(calls) == 6
    for call in calls:
        assert call["sr_meta"] is not None
        assert set(call["sr_meta"]) == {
            "strength",
            "touches",
            "days_span",
            "is_strong",
            "distance_atr",
        }
