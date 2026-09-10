"""SQUEEZE_V2_LIVE_HOLD pin (rule:R3 2026-09-10, e2-silent-cells-triage-2026-09-10 §2).

bb_squeeze v2 の live 呼び出し規約 3 層配線修復 (strategies/scalp/squeeze.py)
により、127 日間 構造的 None だった評価器が候補を再び返す。しかし
bb_squeeze_breakout × EUR_USD は _PAIR_PROMOTED 在籍 (2026-05-07 登録、根拠
shadow N=14 EV=+0.01 のみ) かつ spread_gate / spread_sl_gate 免除のため、
評価器修復だけだと「一度も行使されたことのない live OANDA 送信経路」が
突然開く。v2 wave の設計意図は shadow 実測 (INSUFFICIENT_BT_EVIDENCE →
RECOMMEND_SHADOW) であり live 化の R1 手続きは未了 — よって
SQUEEZE_V2_LIVE_HOLD (default=1) が v2 有効時の winner 経路を shadow に固定し、
live 送信挙動を修復前 (= ゼロ) と同一に保つ。

Test design (tests/test_preserve_types_tick_entry.py と同じ real-_tick_entry
駆動パターン):
  1. hold 有効 (default) → demo_trades 行は is_shadow=1、bridge.open_trade は
     呼ばれない (修復後も live 送信ゼロの pin)。
  2. hold 解除 (SQUEEZE_V2_LIVE_HOLD=0) → _PAIR_PROMOTED 経路で
     bridge.open_trade が呼ばれる = hold が deciding gate であることの
     counterfactual (hold 配線を戻すとテスト 1 が落ちる)。
  3. v2 env 無効 → hold は適用されない (v1 挙動への scope 不変 pin)。
"""
from __future__ import annotations

import uuid
from datetime import datetime as real_datetime, timezone
from unittest.mock import MagicMock

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader

# London-session Thursday (matches test_preserve_types_tick_entry.py)
_LONDON_THU = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)


def _pinned_datetime(now_utc: real_datetime):
    class _Pinned(real_datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return now_utc.replace(tzinfo=None)
            return now_utc.astimezone(tz)
    return _Pinned


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"sq_hold_{uuid.uuid4().hex}.db")))
    logs: list = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(trader, "_check_drawdown", lambda: False)
    monkeypatch.setattr(
        trader._exposure_mgr, "check_new_trade", lambda *_a, **_k: (True, ""),
    )
    monkeypatch.setattr(
        trader, "_get_mtf_regime",
        lambda _inst: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"},
    )
    monkeypatch.setattr(trader, "_compute_dow_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(trader, "_compute_v2_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(
        trader, "_compute_confluence_tag",
        lambda *_a, **_k: {"score": 0, "details": ""},
    )
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: None)
    fake_bridge = MagicMock()
    fake_bridge.active = True
    fake_bridge.is_mode_allowed.return_value = True
    fake_bridge.get_strategy_mode.return_value = "auto"
    fake_bridge.open_trade.return_value = True
    monkeypatch.setattr(trader, "_oanda", fake_bridge)
    return trader, fake_bridge, logs


def _sig() -> dict:
    # 修復後の v2 評価器出力と同型 (✅ 付き reasons — no_confirm gate 通過が前提)
    return {
        "signal": "BUY",
        "entry": 1.20000,
        "sl": 1.19880,
        "tp": 1.20300,
        "entry_type": "bb_squeeze_breakout",
        "confidence": 80,
        "score": 4.0,
        "reasons": [
            "✅ SQUEEZE_REDESIGN_V2: closed-bar BB/range breakout BUY",
            "BB width 5%ile expanding on closed signal bar",
            "EMA9>EMA21 trend-continuation filter",
        ],
        "atr": 0.0005,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _drive(tmp_path, monkeypatch):
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(
        demo_trader_mod, "datetime", _pinned_datetime(_LONDON_THU))
    trader, bridge, logs = _make_trader(tmp_path, monkeypatch)
    trader._tick_entry(
        "scalp_eur",
        {"instrument": "EUR_USD", "icon": "UT", "label": "unit-test"},
        _sig(), "1m", "EUR_USD",
    )
    with trader._db._safe_conn() as conn:
        rows = conn.execute(
            "SELECT trade_id, is_shadow FROM demo_trades"
        ).fetchall()
    return trader, bridge, logs, rows


def test_pair_promoted_membership_precondition():
    """前提 pin: bb_squeeze_breakout×EUR_USD は _PAIR_PROMOTED 在籍
    (tier を外す変更が入ったら本テスト群の前提が変わるため fail loudly)。"""
    assert ("bb_squeeze_breakout", "EUR_USD") in DemoTrader._PAIR_PROMOTED


def test_hold_forces_shadow_when_v2_enabled(tmp_path, monkeypatch):
    """hold 有効 (default) + v2 有効 → winner 経路は shadow 固定、OANDA 送信なし。

    counterfactual: modules/demo_trader.py の SQUEEZE_V2_LIVE_HOLD ブロックを
    戻すと _PAIR_PROMOTED 経由で live 送信され本テストが落ちる。
    """
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    monkeypatch.delenv("SQUEEZE_V2_LIVE_HOLD", raising=False)  # default=1

    trader, bridge, logs, rows = _drive(tmp_path, monkeypatch)

    assert rows, (
        "expected a demo_trades row (shadow); blocked instead: "
        f"{trader._block_counts_per_strategy}"
    )
    assert all(r[1] == 1 for r in rows), f"expected is_shadow=1 rows, got {rows}"
    assert not bridge.open_trade.called, "live OANDA send must not happen under hold"
    assert any("SQUEEZE_V2_LIVE_HOLD" in str(m) for m in logs)


def test_hold_disabled_opens_pair_promoted_live(tmp_path, monkeypatch):
    """counterfactual pin: SQUEEZE_V2_LIVE_HOLD=0 だと _PAIR_PROMOTED 経路で
    live 送信が発生する = hold が唯一の deciding gate (spread_gate /
    spread_sl_gate / Phase0 SHADOW gate はすべて _PAIR_PROMOTED 免除)。
    解除は fresh shadow N での R1 決裁後のみ。"""
    monkeypatch.setenv("SQUEEZE_REDESIGN_V2", "1")
    monkeypatch.setenv("SQUEEZE_V2_LIVE_HOLD", "0")

    trader, bridge, logs, rows = _drive(tmp_path, monkeypatch)

    assert rows, (
        "expected a demo_trades row; blocked instead: "
        f"{trader._block_counts_per_strategy}"
    )
    assert bridge.open_trade.called, (
        "with hold disabled, _PAIR_PROMOTED must reach the OANDA send "
        f"(logs tail: {logs[-5:]})"
    )


def test_hold_not_applied_when_v2_env_off(tmp_path, monkeypatch):
    """scope 不変 pin: SQUEEZE_REDESIGN_V2 無効 (v1 評価器) では hold は適用されず
    従来挙動 (_PAIR_PROMOTED live 経路) のまま — 挙動変更は v2 有効時に限定。"""
    monkeypatch.delenv("SQUEEZE_REDESIGN_V2", raising=False)
    monkeypatch.delenv("SQUEEZE_V2_LIVE_HOLD", raising=False)

    trader, bridge, logs, rows = _drive(tmp_path, monkeypatch)

    assert rows, (
        "expected a demo_trades row; blocked instead: "
        f"{trader._block_counts_per_strategy}"
    )
    assert not any("SQUEEZE_V2_LIVE_HOLD" in str(m) for m in logs)
    assert bridge.open_trade.called, "v1 path must remain untouched by the hold"
