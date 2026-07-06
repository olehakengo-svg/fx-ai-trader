from __future__ import annotations

import concurrent.futures as cf
import inspect
import threading
import uuid
from datetime import datetime, timedelta, timezone

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


def _light_trader(db: DemoDB) -> DemoTrader:
    trader = DemoTrader.__new__(DemoTrader)
    trader._db = db
    trader._lock = threading.RLock()
    trader._recent_signal_emits = {}
    trader._dedup_stats = DemoTrader._new_dedup_stats()
    trader._add_log = lambda _msg: None
    trader._add_oanda_audit = lambda **_kwargs: None
    return trader


def _open_shadow(
    trader: DemoTrader,
    *,
    entry_type: str = "dt_bb_rsi_mr",
    instrument: str = "EUR_USD",
    direction: str = "SELL",
    entry: float = 1.16372,
    tf: str = "15m",
    signal_bar_ts=None,
):
    return trader._open_shadow_emit_trade(
        direction=direction,
        entry_price=entry,
        sl=entry + 0.0030 if direction == "SELL" else entry - 0.0030,
        tp=entry - 0.0060 if direction == "SELL" else entry + 0.0060,
        entry_type=entry_type,
        confidence=61,
        tf=tf,
        reasons=["[SHADOW_EMIT] dedup regression"],
        score=1.2,
        mode="daytrade",
        instrument=instrument,
        signal_bar_ts=signal_bar_ts,
    )


def _open_count(db: DemoDB) -> int:
    with db._safe_conn() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM demo_trades").fetchone()["n"]


def test_all_demo_trade_emit_boundaries_contain_dedup_gate():
    trader_src = inspect.getsource(DemoTrader)
    assert trader_src.count("self._db.open_trade(") == 2
    assert "_maybe_reserve_signal_emit(" in inspect.getsource(DemoTrader._tick_entry)
    assert "_maybe_reserve_signal_emit(" in inspect.getsource(
        DemoTrader._open_shadow_emit_trade
    )


def test_shadow_write_boundary_calls_dedup_gate(monkeypatch, tmp_path):
    db = DemoDB(str(tmp_path / "shadow-boundary.db"))
    trader = _light_trader(db)
    calls = []
    original = trader._maybe_reserve_signal_emit

    def wrapped(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", wrapped)

    trade_id = _open_shadow(trader)

    assert trade_id
    assert len(calls) == 1
    assert calls[0][0][:3] == ("dt_bb_rsi_mr", "EUR_USD", "SELL")
    assert calls[0][1]["_path"] == "shadow"
    assert calls[0][1]["window_sec"] == 900


def test_duplicate_shadow_emit_blocks_second_insert(tmp_path):
    db = DemoDB(str(tmp_path / "shadow-duplicate.db"))
    trader = _light_trader(db)

    first = _open_shadow(trader, entry=1.16372)
    second = _open_shadow(trader, entry=1.16370)

    assert first
    assert second is None
    assert _open_count(db) == 1
    assert trader._dedup_stats["shadow_called"] == 2
    assert trader._dedup_stats["shadow_passed"] == 1
    assert trader._dedup_stats["shadow_blocked"] == 1


def test_hydration_restores_recent_db_signal_emit(tmp_path):
    db = DemoDB(str(tmp_path / "hydrate.db"))
    db.open_trade(
        direction="BUY",
        entry_price=1.2345,
        sl=1.2300,
        tp=1.2450,
        entry_type="wick_imbalance_reversion",
        confidence=62,
        tf="15m",
        mode="daytrade",
        instrument="GBP_USD",
        is_shadow=True,
    )

    trader = DemoTrader(db)

    key = ("wick_imbalance_reversion", "GBP_USD", "BUY")
    assert key in trader._recent_signal_emits
    assert trader._dedup_stats["hydrated_from_db"] >= 1


def test_multi_thread_same_key_reservation_has_single_winner(tmp_path):
    db = DemoDB(str(tmp_path / "race.db"))
    trader = _light_trader(db)

    def reserve():
        return trader._maybe_reserve_signal_emit(
            "sr_break_retest",
            "GBP_JPY",
            "BUY",
            window_sec=900,
            _path="shadow",
        )

    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        results = [f.result() for f in [ex.submit(reserve), ex.submit(reserve)]]

    assert sum(result is None for result in results) == 1
    assert sum(result is not None for result in results) == 1
    assert trader._dedup_stats["shadow_called"] == 2
    assert trader._dedup_stats["shadow_passed"] == 1
    assert trader._dedup_stats["shadow_blocked"] == 1


def test_order_bar_dedup_blocks_same_bar_across_mode_threads(tmp_path):
    db = DemoDB(str(tmp_path / "order-bar-race.db"))
    trader = _light_trader(db)
    bar_ts = datetime(2026, 7, 6, 2, 0, tzinfo=timezone.utc)

    def reserve(mode):
        return trader._maybe_reserve_order_bar_emit(
            "hull_donchian_fade",
            "EUR_USD",
            "BUY",
            bar_ts,
            tf="15m",
            mode=mode,
            _path="primary",
        )

    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        results = [f.result() for f in [ex.submit(reserve, "daytrade"), ex.submit(reserve, "daytrade_eur")]]

    assert sum(result is None for result in results) == 1
    assert sum(result is not None for result in results) == 1
    assert (
        trader._block_counts.get("daytrade_eur:order_bar_dedup", 0)
        + trader._block_counts.get("daytrade:order_bar_dedup", 0)
    ) == 1


def test_order_bar_dedup_allows_new_bar_and_opposite_signal(tmp_path):
    db = DemoDB(str(tmp_path / "order-bar-independent.db"))
    trader = _light_trader(db)
    first_bar = datetime(2026, 7, 6, 2, 0, tzinfo=timezone.utc)
    next_bar = datetime(2026, 7, 6, 2, 15, tzinfo=timezone.utc)

    assert trader._maybe_reserve_order_bar_emit(
        "hull_donchian_fade", "EUR_USD", "BUY", first_bar, tf="15m", mode="daytrade", _path="primary"
    ) is None
    assert trader._maybe_reserve_order_bar_emit(
        "hull_donchian_fade", "EUR_USD", "BUY", next_bar, tf="15m", mode="daytrade", _path="primary"
    ) is None
    assert trader._maybe_reserve_order_bar_emit(
        "hull_donchian_fade", "EUR_USD", "SELL", first_bar, tf="15m", mode="daytrade", _path="primary"
    ) is None


def test_shadow_order_bar_dedup_blocks_same_bar_duplicate_insert(tmp_path):
    db = DemoDB(str(tmp_path / "shadow-order-bar.db"))
    trader = _light_trader(db)
    bar_ts = datetime(2026, 7, 6, 2, 0, tzinfo=timezone.utc)

    first = _open_shadow(trader, entry=1.16372, signal_bar_ts=bar_ts)
    # Simulate old recent_emit state expiry while the signal still belongs to the same closed bar.
    trader._recent_signal_emits.clear()
    second = _open_shadow(trader, entry=1.16370, signal_bar_ts=bar_ts)

    assert first
    assert second is None
    assert _open_count(db) == 1
    assert trader._block_counts["daytrade:order_bar_dedup"] == 1
    assert trader._block_counts_per_strategy["dt_bb_rsi_mr:order_bar_dedup"] == 1


def test_tf_window_sec_mapping():
    assert DemoDB._tf_window_sec("15m") == 900
    assert DemoDB._tf_window_sec("4h") == 14400
    assert DemoDB._tf_window_sec("1m") == 60
    # unknown / empty falls back to the legacy 60s window
    assert DemoDB._tf_window_sec(None) == 60
    assert DemoDB._tf_window_sec("") == 60


def test_backfill_flags_same_15m_bar_reemit_beyond_60s(tmp_path):
    """rule:R3 (2026-06-08): backfill window must be TF-aware.

    A 15m strategy re-emitting 120s later is still the same 900s bar — a
    per-bar duplicate. The old fixed-60s window missed these, leaving
    dedup_violation=0 so they contaminated the R2 shadow audit (Claude 検証:
    282 same-bar dupes escaped the flag across 5m/15m/1h strategies).
    """
    db = DemoDB(db_path=str(tmp_path / "tf-backfill.db"))
    base = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    cols = (
        "trade_id,entry_type,instrument,direction,entry_price,sl,tp,"
        "confidence,tf,mode,is_shadow,dedup_violation,entry_time,status"
    )
    with db._safe_conn() as conn:
        for off in (0, 120):  # 120s apart, same 15m bar
            conn.execute(
                f"INSERT INTO demo_trades ({cols}) VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()), "dt_bb_rsi_mr", "EUR_USD", "BUY",
                    1.1, 1.09, 1.12, 60, "15m", "daytrade", 1, 0,
                    (base + timedelta(seconds=off)).isoformat(), "OPEN",
                ),
            )
        conn.commit()

    result = db._backfill_dedup_violation_impl()
    assert result["status"] == "flagged"
    # the 2nd emit (120s > 60s but < 900s 15m bar) is flagged
    assert result["flagged"] == 1


def test_dynamic_dedup_status_targets_include_all_shadow_strategies(tmp_path):
    db = DemoDB(str(tmp_path / "dynamic-targets.db"))
    for entry_type in ("dt_bb_rsi_mr", "sr_break_retest", "wick_imbalance_reversion"):
        db.open_trade(
            direction="BUY",
            entry_price=1.2345,
            sl=1.2300,
            tp=1.2450,
            entry_type=entry_type,
            confidence=62,
            tf="15m",
            mode="daytrade",
            instrument="EUR_USD",
            is_shadow=True,
        )

    summary = db.get_dedup_violation_summary()

    assert {"dt_bb_rsi_mr", "sr_break_retest", "wick_imbalance_reversion"}.issubset(
        set(summary["targets"])
    )


def test_live_duplicate_pairs_are_blocked_by_reproduction(tmp_path):
    duplicate_pairs = [
        ("dt_bb_rsi_mr", "EUR_USD", "SELL", 1.16372, "15m"),
        ("dt_bb_rsi_mr", "GBP_USD", "SELL", 1.34540, "15m"),
        ("dt_bb_rsi_mr", "EUR_USD", "SELL", 1.16370, "15m"),
        ("sr_break_retest", "GBP_JPY", "BUY", 214.190, "15m"),
        ("sr_break_retest", "GBP_JPY", "BUY", 214.262, "15m"),
        ("wick_imbalance_reversion", "EUR_USD", "BUY", 1.16305, "1h"),
    ]
    blocked = 0

    for idx, (entry_type, instrument, direction, entry, tf) in enumerate(duplicate_pairs):
        db = DemoDB(str(tmp_path / f"pair-{idx}.db"))
        trader = _light_trader(db)
        assert _open_shadow(
            trader,
            entry_type=entry_type,
            instrument=instrument,
            direction=direction,
            entry=entry,
            tf=tf,
        )
        assert _open_shadow(
            trader,
            entry_type=entry_type,
            instrument=instrument,
            direction=direction,
            entry=entry,
            tf=tf,
        ) is None
        blocked += trader._dedup_stats["shadow_blocked"]
        assert _open_count(db) == 1

    assert blocked == len(duplicate_pairs)
