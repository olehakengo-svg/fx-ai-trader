"""JPY 台帳 writer が実約定 units を読む (rule:R3, 2026-11-19).

[[dd-ledger-broker-close-booking-r3-2026-11-04]] §6-2 の残余: `demo_trades` に units
列が無いため `_book_equity_close` の `pip_value_jpy(instrument, trade.get("units", 0), …)`
は常に 1,000 units 既定 (= ¥10/pip 慣行) に落ちていた。Track C D-b の宣言
「pnl_pips × units × pip価値(JPY)」と code が不一致 = lot-blind。defensive 0.2x 期の
live fill は min-lot 1,000 で一致していたが、lot↑ (T5 1.0x 復帰など、R1) の瞬間に
台帳が lot-blind に戻る構造だった。

修復: 送信 units は `oanda_audit` (sent / filled 行)、broker 約定 units は
`oanda_trades.initial_units` に既に永続化されているので、writer がその順で読む
(`DemoDB.get_live_units` → `DemoTrader._resolve_ledger_units`)。未解決時のみ従来の
1,000 既定で、出所を `[LEDGER_UNITS] source=` marker に残す。

固定する性質:
  1. audit に units=5,000 の filled 行がある建玉の決済は pnl × 5,000 × pip で計上される
     (1,000 既定ではない) — lot-blind 回帰 pin
  2. audit/oanda_trades のどちらにも無ければ従来どおり 1,000 既定 (source=default)
     = 現行 min-lot 運用の計上値は byte 不変
  3. audit が無く oanda_trades にだけある場合は initial_units を読む (符号は捨てる)
  4. filled 行が sent 行より優先される / is_live=0 (blocked) 行や units=0 行は読まない
  5. row 自体に units があればそれを最優先 (source=row)
lot / シグナル / tier 閾値 / 凍結値は一切変更しない。
"""
from __future__ import annotations

import uuid

import pytest

import modules.data as data_mod
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader, pip_value_jpy
from modules.risk_analytics import get_dd_lot_multiplier

_INST = "USD_JPY"


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"ddu_{uuid.uuid4().hex}.db")))
    logs = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader._eq_peak_jpy = 359288.47
    trader._eq_current_jpy = trader._eq_peak_jpy - 0.05 * trader._EQ_BASE_CAPITAL_JPY
    trader._eq_peak = 0.0
    trader._eq_current = 0.0
    trader._dd_lot_mult = get_dd_lot_multiplier(0.05)
    trader._defensive_mode = trader._dd_lot_mult < 1.0
    return trader, logs


def _open_live_row(trader, oanda_id):
    trade_id = trader._db.open_trade(
        direction="BUY", entry_price=150.0, sl=149.8, tp=150.4,
        entry_type="unit_fixture", confidence=60, tf="15m", mode="daytrade",
        instrument=_INST, is_shadow=False, oanda_trade_id=oanda_id,
    )
    return next(r for r in trader._db.get_open_trades() if r["trade_id"] == trade_id)


def _audit(trader, trade_id, *, units, status="filled", is_live=True, oanda_id=""):
    trader._db.save_oanda_audit({
        "timestamp": "2026-11-19T00:00:00+00:00",
        "demo_trade_id": trade_id, "entry_type": "daytrade",
        "direction": "BUY", "instrument": _INST, "units": units,
        "is_live": is_live, "bridge_status": status, "block_reason": "",
        "oanda_trade_id": oanda_id,
    })


def _marker(logs):
    return next(l for l in logs if l.startswith("[LEDGER_UNITS]"))


# ── 1. lot-blind 回帰 pin: audit の units=5,000 が計上に使われる ─────────────

def test_writer_books_with_audit_units_not_default_1000(tmp_path, monkeypatch):
    trader, logs = _make_trader(tmp_path, monkeypatch)
    row = _open_live_row(trader, "OANDA-U-1")
    _audit(trader, row["trade_id"], units=5000, oanda_id="OANDA-U-1")
    assert "units" not in row  # demo_trades に units 列が無いことの pin
    jpy_before = trader._eq_current_jpy

    assert trader._book_equity_close(row, +10.0) is True

    expected = 10.0 * pip_value_jpy(_INST, 5000, trader._rate_mid)
    assert expected == pytest.approx(500.0)
    assert trader._eq_current_jpy - jpy_before == pytest.approx(expected)
    assert trader._eq_current_jpy - jpy_before != pytest.approx(100.0)  # 1,000 既定なら ¥100
    m = _marker(logs)
    assert "units=5000" in m and "source=audit_or_oanda" in m


# ── 2. 未解決は従来どおり 1,000 既定 (現行 min-lot 運用は byte 不変) ─────────

def test_writer_falls_back_to_default_1000_when_nothing_recorded(tmp_path, monkeypatch):
    trader, logs = _make_trader(tmp_path, monkeypatch)
    row = _open_live_row(trader, "OANDA-U-2")
    jpy_before = trader._eq_current_jpy

    assert trader._book_equity_close(row, -40.0) is True

    assert trader._eq_current_jpy - jpy_before == pytest.approx(-400.0)
    assert trader._eq_current_jpy - jpy_before == pytest.approx(
        -40.0 * pip_value_jpy(_INST, 0, trader._rate_mid))
    m = _marker(logs)
    assert "units=1000" in m and "source=default" in m


def test_min_lot_1000_audit_row_books_same_as_legacy(tmp_path, monkeypatch):
    """現行運用 (全 live fill が 1,000u) では修復前後で計上値が同じ。"""
    trader, _ = _make_trader(tmp_path, monkeypatch)
    row = _open_live_row(trader, "OANDA-U-3")
    _audit(trader, row["trade_id"], units=1000, oanda_id="OANDA-U-3")
    jpy_before = trader._eq_current_jpy
    trader._book_equity_close(row, +12.5)
    assert trader._eq_current_jpy - jpy_before == pytest.approx(125.0)


# ── 3. oanda_trades.initial_units へのフォールバック (符号は捨てる) ─────────

def test_get_live_units_falls_back_to_oanda_trades_initial_units(tmp_path, monkeypatch):
    trader, logs = _make_trader(tmp_path, monkeypatch)
    row = _open_live_row(trader, "OANDA-U-4")
    trader._db.upsert_oanda_trade({
        "id": "OANDA-U-4", "instrument": _INST, "state": "CLOSED",
        "initialUnits": "-3000", "currentUnits": "0", "price": "150.0",
        "averageClosePrice": "149.9", "openTime": "2026-11-19T00:00:00Z",
        "closeTime": "2026-11-19T01:00:00Z", "realizedPL": "-300",
    })
    assert trader._db.get_live_units(row["trade_id"], "OANDA-U-4") == 3000
    jpy_before = trader._eq_current_jpy
    trader._book_equity_close(row, -10.0)
    assert trader._eq_current_jpy - jpy_before == pytest.approx(-300.0)
    assert "units=3000" in _marker(logs)


# ── 4. 優先順位と除外 ───────────────────────────────────────────────────────

def test_get_live_units_prefers_filled_over_sent_and_ignores_blocked(tmp_path, monkeypatch):
    trader, _ = _make_trader(tmp_path, monkeypatch)
    row = _open_live_row(trader, "OANDA-U-5")
    tid = row["trade_id"]
    _audit(trader, tid, units=1000, status="sent")
    _audit(trader, tid, units=2000, status="filled", oanda_id="OANDA-U-5")
    _audit(trader, tid, units=9000, status="sent")  # 後続 sent (id 大) より filled 優先
    assert trader._db.get_live_units(tid) == 2000

    row_b = _open_live_row(trader, "")
    _audit(trader, row_b["trade_id"], units=7000, status="blocked", is_live=False)
    assert trader._db.get_live_units(row_b["trade_id"]) is None

    row_c = _open_live_row(trader, "")
    _audit(trader, row_c["trade_id"], units=0, status="sent")
    assert trader._db.get_live_units(row_c["trade_id"]) is None
    assert trader._db.get_live_units("", "") is None


def test_get_live_units_only_sent_row_is_used(tmp_path, monkeypatch):
    """fill callback 前に決済が走る稀経路でも sent 行の units で計上できる。"""
    trader, _ = _make_trader(tmp_path, monkeypatch)
    row = _open_live_row(trader, "OANDA-U-6")
    _audit(trader, row["trade_id"], units=4000, status="sent")
    assert trader._db.get_live_units(row["trade_id"], "OANDA-U-6") == 4000


# ── 5. row に units があれば最優先 ──────────────────────────────────────────

def test_resolve_ledger_units_row_wins(tmp_path, monkeypatch):
    trader, _ = _make_trader(tmp_path, monkeypatch)
    row = _open_live_row(trader, "OANDA-U-7")
    _audit(trader, row["trade_id"], units=5000, oanda_id="OANDA-U-7")
    assert trader._resolve_ledger_units(dict(row, units=2500)) == (2500, "row")
    assert trader._resolve_ledger_units(row) == (5000, "audit_or_oanda")
    assert trader._resolve_ledger_units({"trade_id": "nope", "oanda_trade_id": ""}) == (0, "default")
    assert trader._resolve_ledger_units(dict(row, units="abc")) == (5000, "audit_or_oanda")


def test_ineligible_rows_do_not_emit_units_marker(tmp_path, monkeypatch):
    trader, logs = _make_trader(tmp_path, monkeypatch)
    assert trader._book_equity_close(
        {"oanda_trade_id": "", "is_shadow": 1, "instrument": _INST}, -40.0) is False
    assert not any(l.startswith("[LEDGER_UNITS]") for l in logs)
