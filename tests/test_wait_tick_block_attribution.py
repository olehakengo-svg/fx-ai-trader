"""WAIT tick が count ゲートの block 理由を汚染しない (rule:R3, 2026-09-23).

計数器契約バグ **3 例目**。`_tick_entry` の `if signal == "WAIT": return` は
コメントで「WAITはカウントしない」と宣言しているが、旧実装ではこの guard が
3 つの count ゲート (max_per_mode_pair / hedge_block / max_open) の **後ろ**に
置かれていた。これら 3 ゲートの述語は WAIT で自明に真になる:

  - hedge_block: `_ot["direction"] != signal` — signal="WAIT" は全建玉と不一致
  - max_open:    述語が signal 非依存 (全体建玉数のみ)

結果、建玉がある限り **毎 tick の WAIT** が自分の理由名で計上されていた。
本番 gate_block_daily 30d 実測 (2026-08-24〜09-23):

  hedge_block  59,881 件中 55,219 件 (92.2%) が entry_type unknown/wait
  max_open      6,501 件中  5,928 件 (91.2%) が同上
  他の全 reason は 0.0%

同 family: `direction_filter` が 100% WAIT を「方向棄却」と名乗っていた件
(2026-09-05 修正) / 計数器契約バグ (2026-08-18)。

分析: knowledge-base/wiki/analyses/wait-tick-block-attribution-2026-09-23.md
"""

from __future__ import annotations

import inspect
import re
import textwrap
import uuid
from datetime import datetime as real_datetime, timezone

import pytest

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
import tools.alpha_factor_snapshot as alpha_snap_mod
from modules.demo_db import DemoDB
from modules.demo_trader import MODE_CONFIG, DemoTrader

# WAIT より前に評価され、WAIT では述語が真にならない (= 汚染されない) ゲート。
# 実測で 0.0% 汚染だった reason 群の代表。
UNCONTAMINATED_REASONS = ("score_gate", "r2_shadow_demoted_cell")

# WAIT で述語が自明に真になる count ゲート = 本 fix の対象。
COUNT_GATE_REASONS = ("max_per_mode_pair", "hedge_block", "max_open")


class _FixedDatetime(real_datetime):
    """2026-05-28 (木) 12:00 UTC — daytrade active hours 内、週末 block なし。"""

    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        if tz is None:
            return base.replace(tzinfo=None)
        return base.astimezone(tz)


class _StubBridge:
    def __init__(self):
        self.active = True
        self.sent = []
        self.audits = []

    def is_mode_allowed(self, _mode):
        return True

    def _add_audit(self, **kwargs):
        self.audits.append(kwargs)

    def get_strategy_mode(self, _entry_type):
        return "live"

    def open_trade(self, **kwargs):
        self.sent.append(kwargs)
        return True


@pytest.fixture
def trader_env(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"wait_{uuid.uuid4().hex}.db")))
    logs: list[str] = []
    blocked: list[str] = []
    monkeypatch.setattr(trader, "_add_log", logs.append)

    def _rec(*args, **kwargs):
        blocked.append(args[3] if len(args) > 3 else kwargs.get("reason"))

    monkeypatch.setattr(trader, "_record_entry_block", _rec)
    monkeypatch.setattr(trader, "_check_drawdown", lambda: False)
    monkeypatch.setattr(
        trader._exposure_mgr, "check_new_trade", lambda *_a, **_k: (True, "")
    )
    monkeypatch.setattr(
        trader,
        "_get_mtf_regime",
        lambda _i: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"},
    )
    monkeypatch.setattr(trader, "_compute_dow_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(trader, "_compute_v2_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(
        trader, "_compute_confluence_tag", lambda *_a, **_k: {"score": 0, "details": ""}
    )
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_strategy_kelly", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_aggregate_kelly", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_ruin_probability", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_SHADOW_MODE", False)
    bridge = _StubBridge()
    monkeypatch.setattr(trader, "_oanda", bridge)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _i: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(alpha_snap_mod, "snapshot_at", lambda *_a, **_k: {"error": "ut"})
    return trader, logs, blocked, bridge


def _seed_open_buy(trader, monkeypatch, instrument="USD_JPY", mode="daytrade"):
    """daytrade/USD_JPY に建玉 BUY を 1 本置く (hedge 述語の対向側)。

    DB スキーマに結合しないよう `get_open_trades` を差し替える — ゲートが読む
    のは instrument / mode / is_shadow / direction の 4 キーのみ。
    """
    row = {
        "trade_id": "seed-open-buy",
        "mode": mode,
        "instrument": instrument,
        "direction": "BUY",
        "is_shadow": True,
        "entry_price": 150.0,
    }
    monkeypatch.setattr(trader._db, "get_open_trades", lambda: [row])
    return row


def _wait_sig():
    return {
        "signal": "WAIT",
        "entry": 150.0,
        "sl": 149.5,
        "tp": 151.0,
        "entry_type": "unknown",
        "confidence": 0,
        "score": 0.0,
        "reasons": [],
        "atr": 0.07,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _sell_sig():
    sig = _wait_sig()
    # score は方向と整合させる (SELL は負) — さもないと score_gate が先に落とし、
    # hedge ゲートまで到達しない。score_gate が WAIT guard より前にあることの
    # 副次的な確認でもある。
    sig.update(signal="SELL", entry_type="dual_sr_bounce", confidence=70, score=-1.0)
    return sig


# ── 振る舞い pin ────────────────────────────────────────────────────────


def test_wait_tick_records_no_count_gate_block(trader_env, monkeypatch):
    """建玉がある状態の WAIT tick は count ゲートの理由を 1 件も計上しない。"""
    trader, _logs, blocked, _bridge = trader_env
    _seed_open_buy(trader, monkeypatch)
    trader._tick_entry(
        "daytrade", MODE_CONFIG["daytrade"], _wait_sig(), "15m", "USD_JPY"
    )
    for reason in COUNT_GATE_REASONS:
        assert not [b for b in blocked if b and b.startswith(reason)], (
            f"WAIT tick が {reason} を計上した: {blocked}"
        )


def test_wait_tick_creates_no_trade(trader_env, monkeypatch):
    """取引挙動は不変 — WAIT はどの経路でもエントリー/送信しない。"""
    trader, logs, _blocked, bridge = trader_env
    _seed_open_buy(trader, monkeypatch)
    trader._tick_entry(
        "daytrade", MODE_CONFIG["daytrade"], _wait_sig(), "15m", "USD_JPY"
    )
    assert bridge.sent == []
    # count ゲートの診断ログも WAIT では出ない (旧実装は spurious に出していた)
    assert not [m for m in logs if "Slot bypass" in m or "LIVE_EXCEPTION_BYPASS" in m]


def test_directional_signal_still_hedge_blocks(trader_env, monkeypatch):
    """NG を返す既知の入力 (2026-09-18 教訓) — 本物の逆方向シグナルは従来どおり
    hedge_block される。guard を前に出したことで hedge ゲート自体が死んでいない
    ことの対称側 pin (この assert が無いと『全部素通し』でもテストが通る)。"""
    trader, _logs, blocked, _bridge = trader_env
    _seed_open_buy(trader, monkeypatch)
    trader._tick_entry(
        "daytrade", MODE_CONFIG["daytrade"], _sell_sig(), "15m", "USD_JPY"
    )
    assert [b for b in blocked if b and b.startswith("hedge_block")], (
        f"逆方向 SELL が hedge_block されなかった: {blocked}"
    )


# ── 順序 (性質) pin ─────────────────────────────────────────────────────


def _tick_entry_src() -> str:
    return textwrap.dedent(inspect.getsource(DemoTrader._tick_entry))


def test_wait_guard_precedes_every_count_gate():
    """性質 pin: WAIT guard は 3 つの count ゲートすべてより前に現れる。

    counterfactual = guard を元の位置 (max_open の直後) に戻すとこの assert が
    落ちる。構文一致ではなく **出現順序** を pin しているので、コメントや
    書式の変更では誤爆しない。
    """
    src = _tick_entry_src()
    guard = src.index('if signal == "WAIT":')
    for reason in COUNT_GATE_REASONS:
        m = re.search(rf'_block\(\s*\n?\s*f?"{reason}', src)
        if m is None:
            m = re.search(rf'f"{reason}', src)
        assert m is not None, f"{reason} ゲートが見つからない"
        assert guard < m.start(), (
            f"WAIT guard ({guard}) が {reason} ({m.start()}) より後ろにある — "
            "WAIT tick が再び当該カウンタを汚染する"
        )


def test_wait_guard_occurs_exactly_once():
    """guard の重複挿入を防ぐ (前位置に残したまま追加 = 二重 return)。"""
    assert _tick_entry_src().count('if signal == "WAIT":') == 1


def test_uncontaminated_gates_stay_ahead_of_wait_guard():
    """スコープ pin: 実測 0.0% 汚染だったゲートは WAIT guard より前のまま。

    guard を上げすぎると、これらの理由から WAIT 由来でない正当な block が
    消える (= 別方向の計数器破壊)。fix のスコープが 3 ゲートに閉じることを固定。
    """
    src = _tick_entry_src()
    guard = src.index('if signal == "WAIT":')
    for reason in UNCONTAMINATED_REASONS:
        idx = src.find(f'"{reason}')
        assert idx >= 0, f"{reason} ゲートが見つからない"
        assert idx < guard, (
            f"{reason} ({idx}) が WAIT guard ({guard}) より後ろへ移動した — "
            "fix のスコープ超過"
        )
