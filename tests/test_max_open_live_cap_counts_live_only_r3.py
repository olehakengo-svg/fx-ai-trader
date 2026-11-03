"""グローバル建玉上限 `max_open_trades` は **live 建玉数** で判定する — counterfactual pin
(rule:R3, 2026-11-03, O-2026-11-02-1 / registry `max-open-live-cap-counts-shadow-r3`).

背景: knowledge-base/wiki/research/daily-observations-2026-11.md O-2026-11-02-1
  旧実装 `_n_open = len(open_trades)` は live + shadow の総数を live 上限 8 と比較して
  いたため、open live 0 でも shadow 建玉 8 本で live-eligible 型 (carry_dip =
  `_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS` 非所属) が `[SHADOW_BYPASS] max_open` に落ちた
  (2026-10-30 08:02:59Z row 20285、単一エンジン期の実測 1/12)。shadow が live を削る =
  Live vs Shadow 厳格分離 (原則 1) の違反。

修復: live 上限は `is_shadow` 偽の建玉数で判定、shadow 上限 (max_open + 8) は総数のまま。
各 pin は revert で落ちる CF pin + 対称側の不変 pin
(MEMORY feedback_check_the_symmetric_side_2026_09_19):
  1. CF: shadow 建玉が live 上限を埋めていても live-eligible 行は LIVE のまま (marker なし)
  2. 対称: live 建玉が上限を埋めていれば従来どおり shadow 化 + `[SHADOW_BYPASS] max_open`
  3. 対称: live 建玉が上限を埋め、総数が shadow 上限にも達していれば従来どおり hard block
  4. 対称: `_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS` 所属は live 上限超過でも LIVE (不変)
  5. shadow 上限: 上流で shadow 化済みの行は総数 ≥ max_open+8 で block、未満なら
     marker なしで記録 (旧実装は総数 ≥ max_open で `[SHADOW_BYPASS] max_open` を誤付与)
  6. AST: live 上限の比較対象が総数 `len(open_trades)` に戻っていない
lot / シグナル / bypass 例外集合 / 凍結値は一切変更しない。
"""
from __future__ import annotations

import inspect
import re

import pytest

import modules.demo_trader as demo_trader_mod
from modules.demo_trader import _SHADOW_BYPASS_REASON_TAG, DemoTrader

from tests.test_pre_send_guard_observability_r3 import (
    ELITE,
    _cfg,
    _fake_bridge,
    _make_trader,
    _promote_synthetic_elite,
    _row_reasons,
    _sentinelize_elite,
    _sig,
)

# fixture 建玉は signal (daytrade / EUR_USD) と別 mode × 別 instrument に置き、
# per-cell 上限 (max_per_mode_pair) / hedge_block / signal-reverse を踏ませない。
_FIXTURE_MODE = "scalp"
_FIXTURE_INST = "GBP_USD"


def _seed_open(trader, n: int, *, is_shadow: bool):
    for i in range(n):
        trader._db.open_trade(
            direction="BUY", entry_price=1.3000, sl=1.2950, tp=1.3100,
            entry_type=f"fixture_{i}", confidence=50, tf="1m",
            mode=_FIXTURE_MODE, instrument=_FIXTURE_INST,
            is_shadow=is_shadow,
            oanda_trade_id="" if is_shadow else f"OANDA-FIX-{i}",
        )


def _seed_same_cell_live(trader):
    """signal と同 cell (daytrade / EUR_USD / BUY) の live 建玉 1 本 — per-cell live 上限 1 を
    埋めて `max_per_mode_pair` の shadow bypass (max_open 節より上流) を踏ませる。"""
    trader._db.open_trade(
        direction="BUY", entry_price=1.1900, sl=1.1850, tp=1.2000,
        entry_type="fixture_cell", confidence=50, tf="15m",
        mode="daytrade", instrument="EUR_USD",
        is_shadow=False, oanda_trade_id="OANDA-CELL-1",
    )


def _setup(tmp_path, monkeypatch, *, max_open: int):
    fake = _fake_bridge(strategy_mode="live")
    _promote_synthetic_elite(monkeypatch)
    _sentinelize_elite(monkeypatch)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_oanda", fake)
    trader._params["max_open_trades"] = max_open
    return trader, logs, fake


def _entry_rows(trader):
    """fixture 建玉を除いた、本 tick が生成した行。"""
    with trader._db._safe_conn() as conn:
        return conn.execute(
            "SELECT trade_id, is_shadow, oanda_trade_id, reasons FROM demo_trades "
            "WHERE entry_type = ?", (ELITE,),
        ).fetchall()


# ── 1. CF pin: shadow 建玉が live 上限を埋めていても live-eligible 行は LIVE ────────


def test_shadow_open_trades_do_not_consume_live_cap(tmp_path, monkeypatch):
    trader, logs, fake = _setup(tmp_path, monkeypatch, max_open=3)
    _seed_open(trader, 3, is_shadow=True)  # live 0 / shadow 3 = 旧実装なら総数 3 ≥ 3

    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    rows = _entry_rows(trader)
    assert rows and len(rows) == 1
    assert rows[0]["is_shadow"] == 0, dict(rows[0])
    assert fake.open_trade.called
    assert not any("[SHADOW] max_open bypass:" in m for m in logs), logs
    assert f"{_SHADOW_BYPASS_REASON_TAG} max_open" not in _row_reasons(rows[0]), _row_reasons(rows[0])


# ── 2. 対称: live 建玉が上限を埋めていれば従来どおり shadow 化 + marker ─────────────


def test_live_open_trades_still_consume_live_cap(tmp_path, monkeypatch):
    trader, logs, fake = _setup(tmp_path, monkeypatch, max_open=3)
    _seed_open(trader, 3, is_shadow=False)  # live 3 / shadow 0

    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    rows = _entry_rows(trader)
    assert rows and len(rows) == 1 and rows[0]["is_shadow"] == 1
    assert not fake.open_trade.called
    assert any("[SHADOW] max_open bypass:" in m and "live=3/3" in m for m in logs), logs
    assert f"{_SHADOW_BYPASS_REASON_TAG} max_open" in _row_reasons(rows[0])


# ── 3. 対称: live 上限超過 ∧ 総数 ≥ shadow 上限 → hard block (不変) ────────────────


def test_live_cap_full_and_shadow_cap_full_hard_blocks(tmp_path, monkeypatch):
    trader, logs, fake = _setup(tmp_path, monkeypatch, max_open=2)
    _seed_open(trader, 2, is_shadow=False)
    _seed_open(trader, 8, is_shadow=True)  # 総数 10 = max_open + 8

    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    assert not _entry_rows(trader)
    assert not fake.open_trade.called
    assert any("max_open(2/2)" in m for m in logs), logs


# ── 4. 対称: bypass 例外は live 上限超過でも LIVE (不変) ──────────────────────────


def test_bypass_exception_still_allowed_live_over_live_cap(tmp_path, monkeypatch):
    trader, logs, fake = _setup(tmp_path, monkeypatch, max_open=2)
    monkeypatch.setattr(
        DemoTrader, "_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS",
        frozenset(DemoTrader._COUNT_GATE_BYPASS_LIVE_EXCEPTIONS) | {ELITE},
    )
    _seed_open(trader, 2, is_shadow=False)

    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    rows = _entry_rows(trader)
    assert rows and len(rows) == 1 and rows[0]["is_shadow"] == 0
    assert fake.open_trade.called
    assert any("[LIVE_EXCEPTION_BYPASS]" in m and "max_open bypass" in m for m in logs), logs


# ── 5. shadow 上限は総数のまま: 上流 shadow 行は総数 ≥ max_open+8 で block ─────────


def test_upstream_shadow_row_blocked_at_total_shadow_cap(tmp_path, monkeypatch):
    # max_per_mode_pair slot bypass (max_open 節の上流) で shadow 化済みの行:
    # 同 cell (daytrade / EUR_USD) に live 1 本 (上限 1) を置く
    trader, logs, fake = _setup(tmp_path, monkeypatch, max_open=3)
    _seed_same_cell_live(trader)
    _seed_open(trader, 10, is_shadow=True)  # live 1 / 総数 11 = max_open + 8

    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    assert not _entry_rows(trader)
    assert not fake.open_trade.called
    assert any("max_open_shadow_cap(11/11)" in m for m in logs), logs


def test_upstream_shadow_row_under_total_cap_has_no_max_open_marker(tmp_path, monkeypatch):
    """旧実装は総数 ≥ max_open (live 0 でも) で `[SHADOW_BYPASS] max_open` を誤付与。"""
    trader, logs, fake = _setup(tmp_path, monkeypatch, max_open=3)
    _seed_same_cell_live(trader)
    _seed_open(trader, 4, is_shadow=True)  # live 1 / 総数 5 (3 ≤ 5 < 11)

    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    rows = _entry_rows(trader)
    assert rows and len(rows) == 1 and rows[0]["is_shadow"] == 1
    assert not fake.open_trade.called
    reasons = _row_reasons(rows[0])
    assert f"{_SHADOW_BYPASS_REASON_TAG} max_per_mode_pair" in reasons, reasons
    assert not any("[SHADOW] max_open bypass:" in m for m in logs), logs
    assert f"{_SHADOW_BYPASS_REASON_TAG} max_open" not in reasons, reasons


# ── 6. AST pin: live 上限の比較対象が総数に戻っていない ───────────────────────────


def test_live_cap_compares_live_count_not_total():
    src = inspect.getsource(DemoTrader._tick_entry)
    assert re.search(r"_n_open_live\s*=\s*sum\(1 for _t in open_trades if not _t\.get\(\"is_shadow\"", src)
    assert "if _n_open_live >= _max_open:" in src
    assert "if _n_open >= _max_open:" not in src
    # shadow 上限は総数のまま
    assert "elif _is_shadow and _n_open >= _shadow_max:" in src
