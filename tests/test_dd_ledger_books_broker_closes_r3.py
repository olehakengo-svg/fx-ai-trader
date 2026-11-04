"""DD 台帳 (pip / JPY、SSOT) は **broker 側決済 (OANDA_SL_TP) も計上する** — counterfactual pin
(rule:R3, 2026-11-04, registry `dd-ledger-nonbooking-consumer-audit`).

背景: knowledge-base/wiki/analyses/dd-ledger-broker-close-booking-r3-2026-11-04.md
  台帳 writer (pip 台帳 `_eq_current` / JPY 台帳 `_eq_current_jpy` / `_dd_lot_mult`)
  は engine 側決済 (`_main_loop` の close_trade 経路) にしか無く、broker 側で決済された
  live 建玉を `_sync_oanda_closures` が `OANDA_SL_TP` で DB close する経路は台帳を
  素通りしていた (14 例 / 累積 155.0 pip 未計上、[[2026-10-20]] 発見 3)。台帳 DD が
  真の strategy DD より小さく出る = 0.2x lever が早期に緩む側の歪み (本番 10-20 時点
  台帳 DD 10.08% vs tier 境界 8% — 未計上 155p ≈ ¥9.6k ≈ 2.7pt は境界と同桁)。

修復: writer を `DemoTrader._book_equity_close(trade, pnl)` に一本化し、engine 側と
broker 側の両経路から呼ぶ。冪等性は `close_trade` (OPEN 行だけ CLOSED に更新、二重
close は error dict) が保証し、error dict 経路からは呼ばない。
各 pin は revert で落ちる CF pin + 対称側の不変 pin
(MEMORY feedback_check_the_symmetric_side_2026_09_19):
  1. CF: broker 側決済で JPY 台帳 / pip 台帳が動き、tier 境界を跨げば lever が下がる
  2. CF: broker 側決済で KV (eq_current_jpy / dd_lot_mult / defensive_mode) が永続化される
  3. 対称 (不変): shadow 行 / oanda_trade_id 空 / XAU は booking 対象外 (母集団 D-b 不変)
  4. 冪等: 同じ建玉を 2 回 sync しても 1 回しか計上しない / close_trade が error を返す
     経路 (別スレッドが先に close) では計上しない
  5. AST: engine 側 close 経路と `_sync_oanda_closures` の両方が同じ writer を呼び、
     JPY 台帳への加算 (`_eq_current_jpy +=`) が writer の外に存在しない
lot / シグナル / tier 閾値 (DD_LOT_TIERS) / 凍結値は一切変更しない。
"""
from __future__ import annotations

import inspect
import re
import uuid
from unittest.mock import MagicMock

import pytest

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader, pip_value_jpy
from modules.risk_analytics import get_dd_lot_multiplier

_OANDA_ID = "OANDA-BROKER-CLOSE-1"
_INST = "USD_JPY"
_ENTRY = 150.000
_BROKER_CLOSE = 149.600   # BUY → −40.0 pip


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"ddl_{uuid.uuid4().hex}.db")))
    logs = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    return trader, logs


def _seed_ledger(trader, dd_pct: float):
    """JPY 台帳を peak 固定 / DD=dd_pct に置き、lever を整合させる。"""
    trader._eq_peak_jpy = 359288.47
    trader._eq_current_jpy = trader._eq_peak_jpy - dd_pct * trader._EQ_BASE_CAPITAL_JPY
    trader._eq_peak = 0.0
    trader._eq_current = 0.0
    trader._dd_lot_mult = get_dd_lot_multiplier(dd_pct)
    trader._defensive_mode = trader._dd_lot_mult < 1.0


def _open_live_row(trader, *, is_shadow=False, oanda_trade_id=_OANDA_ID, instrument=_INST):
    return trader._db.open_trade(
        direction="BUY", entry_price=_ENTRY, sl=149.800, tp=150.400,
        entry_type="unit_fixture", confidence=60, tf="15m", mode="daytrade",
        instrument=instrument, is_shadow=is_shadow, oanda_trade_id=oanda_trade_id,
    )


def _fake_oanda(closed_ids):
    fake = MagicMock()
    fake.active = True
    fake._trade_map = {}
    fake._client.get_trades.return_value = (
        True,
        {"trades": [{"id": oid, "averageClosePrice": str(_BROKER_CLOSE)} for oid in closed_ids]},
    )
    return fake


def _expected_pnl_jpy(trader, trade_id, pnl_pips):
    row = next(r for r in trader._db.get_all_closed() if r["trade_id"] == trade_id)
    return pnl_pips * pip_value_jpy(row["instrument"], row.get("units", 0), trader._rate_mid)


# ═══════════════════════════════════════════════════════════════════════
# 1–2. CF: broker 側決済が台帳 / lever / KV を動かす
# ═══════════════════════════════════════════════════════════════════════


def test_broker_close_books_jpy_and_pip_ledger_and_lowers_lever(tmp_path, monkeypatch):
    trader, logs = _make_trader(tmp_path, monkeypatch)
    # DD 7.99% = tier 0.40 の上端。−40p の broker 決済で 8% 境界を跨ぐ (→ 0.20)
    _seed_ledger(trader, 0.0799)
    assert trader._dd_lot_mult == pytest.approx(0.40)
    trade_id = _open_live_row(trader)
    trader._oanda = _fake_oanda([_OANDA_ID])
    jpy_before = trader._eq_current_jpy

    trader._sync_oanda_closures()

    closed = [r for r in trader._db.get_all_closed() if r["trade_id"] == trade_id]
    assert len(closed) == 1 and closed[0]["close_reason"] == "OANDA_SL_TP"
    pnl = closed[0]["pnl_pips"]
    assert pnl == pytest.approx(-40.0)
    # pip 台帳
    assert trader._eq_current == pytest.approx(-40.0)
    assert trader._eq_peak == pytest.approx(0.0)
    # JPY 台帳 (SSOT)
    assert trader._eq_current_jpy == pytest.approx(
        jpy_before + _expected_pnl_jpy(trader, trade_id, pnl))
    assert trader._eq_current_jpy < jpy_before
    # lever: 境界を跨いで 0.40 → 0.20、defensive 維持
    dd_pct = (trader._eq_peak_jpy - trader._eq_current_jpy) / trader._EQ_BASE_CAPITAL_JPY
    assert dd_pct > 0.08
    assert trader._dd_lot_mult == pytest.approx(0.20)
    assert trader._defensive_mode is True
    assert any("DD REDUCTION" in m for m in logs)


def test_broker_close_persists_ledger_kv(tmp_path, monkeypatch):
    trader, _ = _make_trader(tmp_path, monkeypatch)
    _seed_ledger(trader, 0.0799)
    _open_live_row(trader)
    trader._oanda = _fake_oanda([_OANDA_ID])

    trader._sync_oanda_closures()

    kv = trader._db.get_system_kv
    assert float(kv("eq_current_jpy", "0")) == pytest.approx(trader._eq_current_jpy, abs=0.01)
    assert float(kv("eq_peak_jpy", "0")) == pytest.approx(trader._eq_peak_jpy, abs=0.01)
    assert float(kv("eq_current", "0")) == pytest.approx(-40.0)
    assert float(kv("dd_lot_mult", "1.0")) == pytest.approx(0.20)
    assert kv("defensive_mode", "0") == "1"


# ═══════════════════════════════════════════════════════════════════════
# 3. 対称 (不変): 母集団 D-b — shadow / oanda_trade_id 空 / XAU は計上しない
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("row", [
    {"oanda_trade_id": "", "is_shadow": 0, "instrument": _INST},
    {"oanda_trade_id": _OANDA_ID, "is_shadow": 1, "instrument": _INST},
    {"oanda_trade_id": _OANDA_ID, "is_shadow": 0, "instrument": "XAU_USD"},
])
def test_writer_ineligible_rows_leave_ledger_untouched(tmp_path, monkeypatch, row):
    trader, _ = _make_trader(tmp_path, monkeypatch)
    _seed_ledger(trader, 0.05)
    jpy_before, pip_before, mult_before = (
        trader._eq_current_jpy, trader._eq_current, trader._dd_lot_mult)

    assert trader._book_equity_close(dict(row, units=0), -40.0) is False

    assert trader._eq_current_jpy == jpy_before
    assert trader._eq_current == pip_before
    assert trader._dd_lot_mult == mult_before


def test_writer_books_eligible_row(tmp_path, monkeypatch):
    trader, _ = _make_trader(tmp_path, monkeypatch)
    _seed_ledger(trader, 0.05)
    jpy_before = trader._eq_current_jpy
    row = {"oanda_trade_id": _OANDA_ID, "is_shadow": 0, "instrument": _INST, "units": 0}

    assert trader._book_equity_close(row, +12.5) is True

    assert trader._eq_current == pytest.approx(12.5)
    assert trader._eq_current_jpy == pytest.approx(
        jpy_before + 12.5 * pip_value_jpy(_INST, 0, trader._rate_mid))


# ═══════════════════════════════════════════════════════════════════════
# 4. 冪等: 2 回 sync / 別スレッド先行 close では 1 回も余分に計上しない
# ═══════════════════════════════════════════════════════════════════════


def test_double_sync_books_once(tmp_path, monkeypatch):
    trader, _ = _make_trader(tmp_path, monkeypatch)
    _seed_ledger(trader, 0.05)
    _open_live_row(trader)
    trader._oanda = _fake_oanda([_OANDA_ID])

    trader._sync_oanda_closures()
    after_first = trader._eq_current_jpy
    trader._sync_oanda_closures()

    assert trader._eq_current_jpy == after_first
    assert trader._eq_current == pytest.approx(-40.0)


def test_close_error_path_does_not_book(tmp_path, monkeypatch):
    trader, _ = _make_trader(tmp_path, monkeypatch)
    _seed_ledger(trader, 0.05)
    _open_live_row(trader)
    trader._oanda = _fake_oanda([_OANDA_ID])
    jpy_before = trader._eq_current_jpy
    monkeypatch.setattr(
        trader._db, "close_trade",
        lambda *_a, **_k: {"error": "Trade already closed by another thread"})

    trader._sync_oanda_closures()

    assert trader._eq_current_jpy == jpy_before
    assert trader._eq_current == pytest.approx(0.0)


# ═══════════════════════════════════════════════════════════════════════
# 5. AST: 両経路が同じ writer を呼ぶ / JPY 加算は writer の外に無い
# ═══════════════════════════════════════════════════════════════════════


def test_ast_both_close_paths_use_single_ledger_writer():
    sync_src = inspect.getsource(DemoTrader._sync_oanda_closures)
    assert "self._book_equity_close(demo_trade, pnl)" in sync_src
    # 計上は close 成功分岐 (error dict でない) の内側にある
    ok_idx = sync_src.index('if "error" not in result:')
    assert sync_src.index("self._book_equity_close(demo_trade, pnl)") > ok_idx

    module_src = inspect.getsource(demo_trader_mod)
    writer_src = inspect.getsource(DemoTrader._book_equity_close)
    assert module_src.count("self._eq_current_jpy +=") == 1
    assert "self._eq_current_jpy +=" in writer_src
    # engine 側 close 経路 (_main_loop の close_trade 後) も同じ writer を呼ぶ
    assert len(re.findall(r"self\._book_equity_close\(trade, pnl\)", module_src)) == 1
