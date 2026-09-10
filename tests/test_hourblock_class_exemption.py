"""Static hour block class exemption (rule:R1, 2026-09-02).

min-lot carve-out 契約群 (_STATIC_HOURBLOCK_CLASS_EXEMPT) は 6 つの静的
hour/session block を免除する。免除発火時は [HOURBLOCK_CLASS_EXEMPT] marker を
reasons に永続し、registry `hourblock-class-exempt-r2-rollback` (reasons_marker
フィルタ付き live_count_decision) が R2 rollback の母集団として読む。

counterfactual 構成: 各 gate で「class メンバー = 通過 + marker」「非メンバー =
従来どおり shadow/block」を両側 assert する — 免除分岐を外すとメンバー側が落ち、
gate 自体を壊すと非メンバー側が落ちる。

pre-reg: knowledge-base/wiki/decisions/hourblock-class-exemption-prereg-2026-09-02.md
"""
import uuid
from datetime import datetime as real_datetime, timezone

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader

MARKER = "[HOURBLOCK_CLASS_EXEMPT]"
# class メンバー代表。USD_JPY gate 用 = carry_dip / EUR_USD gate 用も同一戦略で
# 良い (gate は entry_type×instrument×hour で判定し、戦略の本来ペアは見ない)。
MEMBER = "usdjpy_carry_dip_accumulator"
NON_MEMBER = "eurgbp_daily_mr"  # sentinel — block 時は shadow へ退避する側


def _dt_at_hour(hour: int):
    class _At(real_datetime):
        @classmethod
        def now(cls, tz=None):
            base = real_datetime(2026, 9, 2, hour, 30, tzinfo=timezone.utc)
            if tz is None:
                return base.replace(tzinfo=None)
            return base.astimezone(tz)
    return _At


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"hourblock_{uuid.uuid4().hex}.db")))
    logs = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(trader, "_check_drawdown", lambda: False)
    monkeypatch.setattr(
        trader._exposure_mgr, "check_new_trade", lambda *_a, **_k: (True, "")
    )
    monkeypatch.setattr(
        trader, "_get_mtf_regime",
        lambda _i: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"},
    )
    monkeypatch.setattr(trader, "_compute_dow_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(trader, "_compute_v2_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(
        trader, "_compute_confluence_tag", lambda *_a, **_k: {"score": 0, "details": ""}
    )
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: None)
    return trader, logs


def _sig(entry_type, signal="BUY", entry=150.00, tp=150.60):
    return {
        "signal": signal,
        "entry": entry,
        "tp": tp,
        "entry_type": entry_type,
        "confidence": 80,
        "score": 1.0,
        "reasons": ["✅ unit-test"],
        "atr": 0.05,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _cfg(instrument):
    return {"instrument": instrument, "icon": "UT", "label": "unit-test"}


def _rows(trader):
    with trader._db._safe_conn() as conn:
        return conn.execute(
            "SELECT entry_type, instrument, is_shadow, reasons FROM demo_trades"
        ).fetchall()


def _run(tmp_path, monkeypatch, *, hour, instrument, entry_type):
    monkeypatch.setattr(demo_trader_mod, "datetime", _dt_at_hour(hour))
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _i: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    trader._tick_entry("daytrade", _cfg(instrument), _sig(entry_type), "15m", instrument)
    return trader, logs


# ── identity pin: 免除クラス = min-lot 契約群 (性質そのものを SSOT に) ──

def test_exempt_class_is_the_minlot_carveout_set_itself():
    """性質 pin: 免除クラスは min-lot carve-out set と同一実体 (alias)。
    コピーで二重管理すると片方だけ更新されて drift する — identity で固定。"""
    assert (
        DemoTrader._STATIC_HOURBLOCK_CLASS_EXEMPT
        is DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES
    )
    assert MEMBER in DemoTrader._STATIC_HOURBLOCK_CLASS_EXEMPT
    assert NON_MEMBER not in DemoTrader._STATIC_HOURBLOCK_CLASS_EXEMPT


# ── 6 gate それぞれの両側 counterfactual ──

def _assert_exempted(trader, logs, label_fragment):
    rows = _rows(trader)
    assert rows, "class member row must be recorded"
    assert MARKER in (rows[0]["reasons"] or ""), "marker must persist to DB reasons"
    assert any(MARKER in m and label_fragment in m for m in logs)


def _assert_blocked_to_shadow(trader, logs, block_log_fragment):
    rows = _rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert MARKER not in (rows[0]["reasons"] or "")
    assert any(block_log_fragment in m for m in logs)


def test_h13_usdjpy_member_passes_nonmember_shadowed(tmp_path, monkeypatch):
    trader, logs = _run(tmp_path, monkeypatch, hour=13, instrument="USD_JPY",
                        entry_type=MEMBER)
    _assert_exempted(trader, logs, "H13_USD_JPY")
    assert not any("H13 USD_JPY block" in m for m in logs)

    trader2, logs2 = _run(tmp_path, monkeypatch, hour=13, instrument="USD_JPY",
                          entry_type=NON_MEMBER)
    _assert_blocked_to_shadow(trader2, logs2, "H13 USD_JPY block")


def test_h16_20_usdjpy_member_passes_nonmember_shadowed(tmp_path, monkeypatch):
    trader, logs = _run(tmp_path, monkeypatch, hour=18, instrument="USD_JPY",
                        entry_type=MEMBER)
    _assert_exempted(trader, logs, "H18_USD_JPY")

    trader2, logs2 = _run(tmp_path, monkeypatch, hour=18, instrument="USD_JPY",
                          entry_type=NON_MEMBER)
    _assert_blocked_to_shadow(trader2, logs2, "H18 USD_JPY block")


def test_h11_eurusd_member_passes_nonmember_shadowed(tmp_path, monkeypatch):
    trader, logs = _run(tmp_path, monkeypatch, hour=11, instrument="EUR_USD",
                        entry_type=MEMBER)
    _assert_exempted(trader, logs, "H11_EUR_USD")

    trader2, logs2 = _run(tmp_path, monkeypatch, hour=11, instrument="EUR_USD",
                          entry_type=NON_MEMBER)
    _assert_blocked_to_shadow(trader2, logs2, "H11 EUR_USD block")


def test_h7_eurusd_member_passes_nonmember_shadowed(tmp_path, monkeypatch):
    trader, logs = _run(tmp_path, monkeypatch, hour=7, instrument="EUR_USD",
                        entry_type=MEMBER)
    _assert_exempted(trader, logs, "H7_EUR_USD")

    trader2, logs2 = _run(tmp_path, monkeypatch, hour=7, instrument="EUR_USD",
                          entry_type=NON_MEMBER)
    _assert_blocked_to_shadow(trader2, logs2, "H7 EUR_USD block")


def test_tokyo_eurusd_member_passes_nonmember_shadowed(tmp_path, monkeypatch):
    trader, logs = _run(tmp_path, monkeypatch, hour=3, instrument="EUR_USD",
                        entry_type=MEMBER)
    _assert_exempted(trader, logs, "EUR_USD_Tokyo_H3")

    trader2, logs2 = _run(tmp_path, monkeypatch, hour=3, instrument="EUR_USD",
                          entry_type=NON_MEMBER)
    _assert_blocked_to_shadow(trader2, logs2, "session_pair bypass")


def test_lateny_eurusd_member_passes_nonmember_shadowed(tmp_path, monkeypatch):
    trader, logs = _run(tmp_path, monkeypatch, hour=19, instrument="EUR_USD",
                        entry_type=MEMBER)
    _assert_exempted(trader, logs, "EUR_USD_Late_NY_H19")

    trader2, logs2 = _run(tmp_path, monkeypatch, hour=19, instrument="EUR_USD",
                          entry_type=NON_MEMBER)
    _assert_blocked_to_shadow(trader2, logs2, "session_pair bypass")


# ── demoted tier は免除されない (fail-closed) ──

def test_demoted_member_is_not_exempted(tmp_path, monkeypatch):
    monkeypatch.setattr(demo_trader_mod, "datetime", _dt_at_hour(13))
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _i: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(
        trader, "_is_force_demoted_entry", lambda *_a, **_k: True
    )
    trader._tick_entry("daytrade", _cfg("USD_JPY"), _sig(MEMBER), "15m", "USD_JPY")

    rows = _rows(trader)
    assert not any(MARKER in m for m in logs)
    if rows:
        assert MARKER not in (rows[0]["reasons"] or "")


# ── marker は免除発火時のみ — block 帯外のメンバートレードに付かない ──

def test_marker_absent_outside_blocked_windows(tmp_path, monkeypatch):
    trader, logs = _run(tmp_path, monkeypatch, hour=10, instrument="USD_JPY",
                        entry_type=MEMBER)
    rows = _rows(trader)
    assert not any(MARKER in m for m in logs)
    if rows:
        assert MARKER not in (rows[0]["reasons"] or "")


# ── rollback trigger の計数 estimand (reasons_marker フィルタ) ──

def test_count_live_matching_reasons_marker_filter():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    from prereg_trigger_watch import count_live_matching

    rows = [
        # marker 付き live — 数える
        {"entry_type": MEMBER, "instrument": "USD_JPY", "direction": "BUY",
         "oanda_trade_id": "123", "dedup_violation": 0,
         "reasons": f'["✅ x", "{MARKER} H13_USD_JPY 通過"]'},
        # marker 付きだが list 形 reasons — 数える (両対応)
        {"entry_type": "kalman_d7_po_dn_flip", "instrument": "USD_JPY",
         "direction": "SELL", "oanda_trade_id": "124", "dedup_violation": 0,
         "reasons": ["✅ y", f"{MARKER} H16_USD_JPY 通過"]},
        # marker なし live — 数えない (block 帯外トレードの混入防止)
        {"entry_type": MEMBER, "instrument": "USD_JPY", "direction": "BUY",
         "oanda_trade_id": "125", "dedup_violation": 0, "reasons": '["✅ z"]'},
        # marker 付きだが shadow (oanda_trade_id 空) — 数えない
        {"entry_type": MEMBER, "instrument": "USD_JPY", "direction": "BUY",
         "oanda_trade_id": "", "dedup_violation": 0,
         "reasons": f'["{MARKER} H13_USD_JPY 通過"]'},
        # marker 付き live だが dedup_violation=1 — 数えない
        {"entry_type": MEMBER, "instrument": "USD_JPY", "direction": "BUY",
         "oanda_trade_id": "126", "dedup_violation": 1,
         "reasons": f'["{MARKER} H13_USD_JPY 通過"]'},
    ]
    # entry_type="" + marker = class-pooled: 戦略横断で marker 付き clean live のみ
    assert count_live_matching(rows, "", "", "", reasons_marker=MARKER) == 2
    # marker なしの従来動作は不変 (entry_type 指定)
    assert count_live_matching(rows, MEMBER, "USD_JPY", "BUY") == 2
