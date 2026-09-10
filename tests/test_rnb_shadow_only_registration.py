"""rnb_support_bounce stage-1 構造的 shadow-only 登録の drift pin
(rule:R1, user 承認 2026-09-10「進めて」)。

packet: knowledge-base/wiki/decisions/rnb-support-bounce-r1-packet-2026-09-10.md
LOCK:   rnb-support-bounce-shadow-forward (first look shadow N>=41 or 2027-01-15)

登録同期 4 点 (packet §4) のコード側 3 点をここで pin する:
  1. QUALIFIED_TYPES に "rnb_support_bounce" (unknown_type dead mode の解消)
  2. MODE_CONFIG["rnb_usdjpy"]["shadow_only"] is True (構造的 shadow-only)
  3. drift-pin テスト自身 (tests/test_rnb_block_reason_estimand.py の
     KNOWN_REGISTRATION_DRIFT=空 と本ファイル)
  (4 点目 = KB sync は tools/sync_kb_index.py / tier_integrity_check.py)

構造保証 pin (daytrade_audjpy 前例 tests/test_daytrade_audjpy_shadow_only_mode.py
と同型 — 3 点 block 全てを rnb で個別に検証する):
  (a) 送信ガード最終段: 最悪ケース (get_strategy_mode='live' × bridge active
      × SHADOW_MODE off) でも OANDA open_trade が呼ばれず shadow 行になる
  (b) control: mode だけ非 shadow_only にすると send に到達する (帰属証明)
  (c) resend (補完送信) gate / write-path safeguard でも同判定
  (d) _UNIVERSAL_SENTINEL 非追加 pin — sentinel = minlot live 経路。packet §4
      「意図的にやらないこと」の固定。sentinel 追加 = stage-2 相当で R1 必須。
"""
from __future__ import annotations

import ast
import inspect
import textwrap
import uuid
from datetime import datetime as real_datetime, timezone

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
import tools.alpha_factor_snapshot as alpha_snap_mod
from modules.demo_db import DemoDB
from modules.demo_trader import (
    MODE_CONFIG,
    DemoTrader,
    _mode_is_shadow_only,
)


# ── _tick_entry ローカルの QUALIFIED_TYPES を AST で取り出す ─────────────
def _qualified_types() -> set:
    src = textwrap.dedent(inspect.getsource(DemoTrader._tick_entry))
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "QUALIFIED_TYPES"
                and isinstance(node.value, ast.Set)):
            return {e.value for e in node.value.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    raise AssertionError("QUALIFIED_TYPES not found in _tick_entry")


class _FixedDatetime(real_datetime):
    """2026-05-28 (木) 12:00 UTC — active_hours_utc (7,20) 内、週末 block なし。"""

    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        if tz is None:
            return base.replace(tzinfo=None)
        return base.astimezone(tz)


class _StubBridge:
    """最悪ケース bridge: active + 全モード許可 + operator 手動 live 昇格。"""

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


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(
        DemoDB(str(tmp_path / f"rnb_shadow_only_{uuid.uuid4().hex}.db"))
    )
    logs = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(trader, "_check_drawdown", lambda: False)
    monkeypatch.setattr(
        trader._exposure_mgr,
        "check_new_trade",
        lambda *_args, **_kwargs: (True, ""),
    )
    monkeypatch.setattr(
        trader,
        "_get_mtf_regime",
        lambda _instrument: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"},
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
    # 最悪ケース: Phase0 SHADOW_MODE master switch が OFF の本番構成を模擬
    monkeypatch.setattr(trader, "_SHADOW_MODE", False)
    bridge = _StubBridge()
    monkeypatch.setattr(trader, "_oanda", bridge)
    return trader, bridge, logs


def _sig(signal="BUY"):
    return {
        "signal": signal,
        "entry": 150.000,
        "sl": 149.850,
        "tp": 150.200,
        "entry_type": "rnb_support_bounce",
        "confidence": 80,
        "score": 1.0,
        "reasons": ["✅ rnb shadow-only registration pin"],
        "atr": 0.07,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _rows(trader):
    with trader._db._safe_conn() as conn:
        return conn.execute(
            "SELECT trade_id, entry_type, instrument, mode, is_shadow "
            "FROM demo_trades"
        ).fetchall()


def _patch_common(monkeypatch):
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(
        alpha_snap_mod, "snapshot_at", lambda *_a, **_k: {"error": "unit-test"}
    )


# ── 登録同期 pin ───────────────────────────────────────────────────


def test_rnb_support_bounce_is_qualified():
    """同期点 1: QUALIFIED_TYPES 登録 (packet §4 #1)。外れると 2026-04-05〜
    09-10 の dead mode (unknown_type で shadow 行ゼロ) が再発する。"""
    assert "rnb_support_bounce" in _qualified_types()


def test_rnb_mode_declares_structural_shadow_only():
    """同期点 2: MODE_CONFIG shadow_only=True (packet §4 #2)。
    これを外す変更は stage-2 (Shadow→Live 昇格) = R1 手続き +
    LOCK rnb-support-bounce-shadow-forward の first look 通過が必須。"""
    assert MODE_CONFIG["rnb_usdjpy"]["shadow_only"] is True
    assert _mode_is_shadow_only("rnb_usdjpy") is True


def test_rnb_support_bounce_not_in_universal_sentinel():
    """packet §4「意図的にやらないこと」: sentinel = minlot live 経路。
    _UNIVERSAL_SENTINEL への追加は stage-1 の構造保証を破る (R1 必須)。"""
    assert "rnb_support_bounce" not in DemoTrader._UNIVERSAL_SENTINEL


# ── (a) 送信ガード最終段: 最悪ケースで OANDA 発注ゼロ ────────────────


def test_shadow_only_mode_blocks_oanda_even_for_manual_live_promotion(
    tmp_path, monkeypatch
):
    """最悪ケース (get_strategy_mode='live' × bridge active × 全モード許可 ×
    SHADOW_MODE off) でも OANDA open_trade が呼ばれず、行は is_shadow=1。"""
    _patch_common(monkeypatch)
    trader, bridge, logs = _make_trader(tmp_path, monkeypatch)

    trader._tick_entry(
        "rnb_usdjpy",
        MODE_CONFIG["rnb_usdjpy"],
        _sig(),
        "15m",
        "USD_JPY",
    )

    rows = _rows(trader)
    assert rows, "shadow trade row must be recorded (N 蓄積路の確保)"
    assert rows[0]["entry_type"] == "rnb_support_bounce"
    assert rows[0]["instrument"] == "USD_JPY"
    assert rows[0]["mode"] == "rnb_usdjpy"
    assert rows[0]["is_shadow"] == 1
    assert bridge.sent == [], "shadow-only mode must never reach OANDA open_trade"
    assert any("[SHADOW_ONLY_MODE] rnb_usdjpy" in m for m in logs)
    assert not any("[SENT]" in m for m in logs)


# ── (b) control: 帰属証明 ─────────────────────────────────────────


def test_control_same_signal_in_non_shadow_only_mode_reaches_oanda(
    tmp_path, monkeypatch
):
    """mode 名以外は完全同一の入力で send に到達する = (a) の block が
    shadow_only gate 起因であることの帰属証明 (counterfactual control)。
    同時に「QUALIFIED 化した rnb_support_bounce は shadow_only 以外の
    防壁を持たない」という事実 (packet §4 の設計前提) も pin する。"""
    _patch_common(monkeypatch)
    trader, bridge, _logs = _make_trader(tmp_path, monkeypatch)

    trader._tick_entry(
        "daytrade",
        {"instrument": "USD_JPY", "icon": "UT", "label": "unit-test-control"},
        _sig(),
        "15m",
        "USD_JPY",
    )

    assert len(bridge.sent) == 1, "control must reach OANDA send"
    assert bridge.sent[0]["instrument"] == "USD_JPY"


# ── (c) resend gate + write-path safeguard ────────────────────────


def test_resend_promote_gate_blocks_rnb_mode(tmp_path, monkeypatch):
    trader, _bridge, _logs = _make_trader(tmp_path, monkeypatch)
    block = trader._resend_promote_gate_block_reason(
        "rnb_support_bounce", "USD_JPY", "rnb_usdjpy", confidence=80
    )
    assert block == "SHADOW_ONLY_MODE_GATE"


def test_resend_pending_skips_rnb_mode_even_if_shadow_flag_flipped(
    tmp_path, monkeypatch
):
    """is_shadow 反転バグ (defense-in-depth 想定) でも補完送信されない。"""
    trader, bridge, logs = _make_trader(tmp_path, monkeypatch)

    trade_id = trader._db.open_trade(
        "BUY",
        150.000,
        149.850,
        150.200,
        entry_type="rnb_support_bounce",
        confidence=80,
        tf="15m",
        mode="rnb_usdjpy",
        instrument="USD_JPY",
        is_shadow=True,
    )
    # 反転バグを注入: is_shadow=0 かつ oanda_trade_id 空 → resend 候補化
    with trader._db._safe_conn() as conn:
        conn.execute(
            "UPDATE demo_trades SET is_shadow=0, entry_time=? WHERE trade_id=?",
            (real_datetime.now(timezone.utc).isoformat(), trade_id),
        )
        conn.commit()

    trader._resend_pending_oanda_trades()

    assert bridge.sent == [], "resend path must also be blocked for shadow-only mode"
    assert any("SHADOW_ONLY_MODE_GATE" in m for m in logs)


def test_resolve_is_shadow_for_write_forces_shadow_for_rnb_mode(
    tmp_path, monkeypatch
):
    trader, _bridge, _logs = _make_trader(tmp_path, monkeypatch)
    # fill 済みを装っても shadow で永続化 (fail-closed write-path)
    assert (
        trader._resolve_is_shadow_for_write(
            "rnb_support_bounce",
            "USD_JPY",
            "rnb_usdjpy",
            bridge_status="filled",
            oanda_trade_id="OANDA-999",
        )
        is True
    )
