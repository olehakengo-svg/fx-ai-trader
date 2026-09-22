"""rnb_usdjpy (shadow_only) 限定の下流 live 保護 gate 迂回 — counterfactual pin
(rule:R3, 2026-09-23)。

背景: knowledge-base/wiki/analyses/rnb-shadow-lane-health-precheck-2026-09-22.md §6/§8 (i)
  09-12 以降の rnb BUY bar 6/6 が velocity_down / mtf_strong_bias / 1h_rr_low の
  hard block で行にならず、LOCK 母集団 (shadow N) がゼロ成長だった。shadow_only
  mode は OANDA 送信が構造的にゼロで、これらの gate が守る資本は無い。
registry: rnb-support-bounce-shadow-forward (AMENDMENT 2026-09-23、旧/新 gate 構成は
  層別既定) / rnb-shadow-lane-health-checkpoint-1 (09-24) / -2 (10-08)

pin (precheck §8 (i) の (a)〜(d) をそのまま写す — 「NG を返す既知の入力」を必ず併設):
  (a) rnb BUY が velocity_down (10 分 −8pip 超) / mtf_strong_bias (strong 逆方向) /
      1h_rr_low (RR 1.19) の各 counterfactual で **shadow 行になる**
  (b) 同じ入力で allowlist を空にする (= 変更前のコード) と従来どおり block される
      (対称側、MEMORY feedback_check_the_symmetric_side_2026_09_19)
  (b'') allowlist に居ても MODE_CONFIG.shadow_only=False なら迂回しない (fail-closed —
      「資格」ではなく「実状態」で gate する)
  (b') daytrade_audjpy (shadow_only=True だが allowlist 外) は同じ counterfactual で
      変更前と同一に block される — これが落ちる実装 = _mode_is_shadow_only を
      汎用化してしまった実装 (WS3 stage-2 pre-reg の母集団を黙って変える)
  (c) OANDA 送信ゼロが不変 (最悪ケース bridge でも open_trade 未呼出)
  (d) session_hours は迂回に含めない — 21 時台の評価は従来どおり
      session_hours(outside_active) で block (窓外行を LOCK 母集団に入れない)
  (e) 迂回は 3 gate に閉じる — spike は rnb でも hard block のまま / _tick_entry 内で
      _downstream_relax を参照する箇所は 3 gate のみ (allowlist の黙った拡張を検知)
"""
from __future__ import annotations

import inspect
import re
import textwrap
import uuid
from datetime import datetime as real_datetime, timedelta, timezone

import pytest

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
import tools.alpha_factor_snapshot as alpha_snap_mod
from modules.demo_db import DemoDB
from modules.demo_trader import (
    MODE_CONFIG,
    DemoTrader,
    _SHADOW_ONLY_DOWNSTREAM_RELAX_GATES,
    _SHADOW_ONLY_DOWNSTREAM_RELAX_MODES,
    _mode_downstream_relax,
    _mode_is_shadow_only,
)


class _FixedDatetime(real_datetime):
    """2026-05-28 (木) 12:00 UTC — active_hours_utc (7,20) 内、週末 block なし。"""

    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        if tz is None:
            return base.replace(tzinfo=None)
        return base.astimezone(tz)


class _AfterHoursDatetime(real_datetime):
    """2026-05-28 (木) 21:30 UTC — rnb active_hours (7,20) の窓外 (precheck §5 の
    「hour=20 bar が 21 時台に評価される」stale 入力を wall-clock 側で再現)。"""

    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 21, 30, tzinfo=timezone.utc)
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
        DemoDB(str(tmp_path / f"rnb_relax_{uuid.uuid4().hex}.db"))
    )
    logs = []
    blocked = []
    monkeypatch.setattr(trader, "_add_log", logs.append)

    def _rec(*args, **kwargs):
        # _record_entry_block(mode, entry_type, instrument, reason, ...)
        blocked.append(args[3] if len(args) > 3 else kwargs.get("reason"))

    monkeypatch.setattr(trader, "_record_entry_block", _rec)
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
    monkeypatch.setattr(trader, "_SHADOW_MODE", False)
    bridge = _StubBridge()
    monkeypatch.setattr(trader, "_oanda", bridge)
    return trader, bridge, logs, blocked


def _patch_common(monkeypatch, dt_cls=_FixedDatetime):
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", dt_cls)
    monkeypatch.setattr(
        alpha_snap_mod, "snapshot_at", lambda *_a, **_k: {"error": "unit-test"}
    )


def _rnb_sig(tp=150.200, sl=149.850):
    """rnb BUY (entry 150.000)。既定 TP/SL = 20p/15p → RR 1.33 (設計値、床 1.2 通過)。"""
    return {
        "signal": "BUY",
        "entry": 150.000,
        "sl": sl,
        "tp": tp,
        "entry_type": "rnb_support_bounce",
        "confidence": 68,
        "score": 1.0,
        "reasons": ["✅ RNB support 150.00", "✅ wick 50%"],
        "atr": 0.07,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _audjpy_sig():
    return {
        "signal": "BUY",
        "entry": 97.500,
        "tp": 98.100,
        "entry_type": "htf_false_breakout",
        "confidence": 80,
        "score": 1.0,
        "reasons": ["✅ unit-test"],
        "atr": 0.08,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _rows(trader):
    with trader._db._safe_conn() as conn:
        return conn.execute(
            "SELECT trade_id, entry_type, instrument, mode, is_shadow, entry_time "
            "FROM demo_trades"
        ).fetchall()


# ── counterfactual 入力 (precheck §6 の 3 gate を個別に踏ませる) ──────────


def _seed_velocity_down(trader, instrument, price_ago, minutes_ago, dt_cls=_FixedDatetime):
    """直近窓の最古価格を高く置く → current (sig entry) との差が閾値超の下落。"""
    trader._price_history[instrument] = [
        (dt_cls.now(timezone.utc) - timedelta(minutes=minutes_ago), price_ago),
    ]


def _seed_strong_sell_bias(trader, instrument, dt_cls=_FixedDatetime):
    """DT strong pattern 由来の SELL bias (1h 有効) → BUY は mtf_strong_bias で衝突。"""
    trader._15m_tactical_bias[instrument] = {
        "direction": "SELL",
        "entry_type": "hs_neckbreak",
        "confidence": 80,
        "updated_at": dt_cls.now(timezone.utc),
        "signal_price": 150.0,
        "strength": "strong",
    }


def _tick_rnb(trader, sig=None):
    trader._tick_entry(
        "rnb_usdjpy", MODE_CONFIG["rnb_usdjpy"], sig or _rnb_sig(), "15m", "USD_JPY"
    )


# ── 定義 pin ───────────────────────────────────────────────────────────


def test_allowlist_is_rnb_only_and_subset_of_shadow_only_modes():
    """allowlist は rnb_usdjpy 1 件 (precheck §8 (i) の範囲)。拡張は当該 mode の
    pre-reg amendment (Rule 1) が先。allowlist ⊆ shadow_only は性質 pin —
    live 送信し得る mode を入れた実装はここで落ちる。"""
    assert _SHADOW_ONLY_DOWNSTREAM_RELAX_MODES == frozenset({"rnb_usdjpy"})
    for mode in _SHADOW_ONLY_DOWNSTREAM_RELAX_MODES:
        assert MODE_CONFIG[mode]["shadow_only"] is True
        assert _mode_is_shadow_only(mode) is True
    assert _SHADOW_ONLY_DOWNSTREAM_RELAX_GATES == ("velocity_down", "mtf_strong_bias", "1h_rr_low")


def test_helper_requires_membership_and_effective_shadow_only(monkeypatch):
    assert _mode_downstream_relax("rnb_usdjpy") is True
    # shadow_only=True でも allowlist 外なら False (daytrade_audjpy = WS3 stage-2 母集団)
    assert _mode_is_shadow_only("daytrade_audjpy") is True
    assert _mode_downstream_relax("daytrade_audjpy") is False
    # allowlist 内でも実状態が shadow_only=False なら False (fail-closed)
    monkeypatch.setitem(MODE_CONFIG["rnb_usdjpy"], "shadow_only", False)
    assert _mode_downstream_relax("rnb_usdjpy") is False


def test_relax_flag_is_referenced_by_exactly_three_gates():
    """(e) スコープ pin: _tick_entry 内の `_downstream_relax` 参照 = 代入 1 + gate 3。
    増えていたら allowlist 迂回が 4 つ目の gate に黙って広がった (母集団変更 =
    LOCK amendment が要る) — 減っていたら gate の迂回が外れた。"""
    src = textwrap.dedent(inspect.getsource(DemoTrader._tick_entry))
    refs = re.findall(r"\b_downstream_relax\b", src)
    assert len(refs) == 4, refs
    for gate in ("velocity_down relax", "mtf_strong_bias relax", "1h_rr_low relax"):
        assert gate in src


# ── (a) rnb: 3 gate が hard block → shadow 行 ───────────────────────────


def test_velocity_down_relaxes_to_shadow_for_rnb(tmp_path, monkeypatch):
    _patch_common(monkeypatch)
    trader, bridge, logs, blocked = _make_trader(tmp_path, monkeypatch)
    # 5 分前 150.100 → current 150.000 = −10.0pip (rnb 窓 10 分 / 閾値 8.0pip 超)
    _seed_velocity_down(trader, "USD_JPY", 150.100, 5)

    _tick_rnb(trader)

    rows = _rows(trader)
    assert rows and rows[0]["is_shadow"] == 1 and rows[0]["mode"] == "rnb_usdjpy"
    assert any("[SHADOW] velocity_down relax: rnb_support_bounce rnb_usdjpy" in m for m in logs)
    assert not any(r.startswith("velocity_down(") for r in blocked), blocked
    assert bridge.sent == []  # (c)


def test_mtf_strong_bias_relaxes_to_shadow_for_rnb(tmp_path, monkeypatch):
    _patch_common(monkeypatch)
    trader, bridge, logs, blocked = _make_trader(tmp_path, monkeypatch)
    _seed_strong_sell_bias(trader, "USD_JPY")

    _tick_rnb(trader)

    rows = _rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] mtf_strong_bias relax: rnb_support_bounce rnb_usdjpy" in m for m in logs)
    assert not any(r.startswith("mtf_strong_bias(") for r in blocked), blocked
    assert bridge.sent == []


def test_1h_rr_low_relaxes_to_shadow_for_rnb(tmp_path, monkeypatch):
    _patch_common(monkeypatch)
    trader, bridge, logs, blocked = _make_trader(tmp_path, monkeypatch)
    # TP 19p / SL 16p = 1.1875 < 1.2 (設計 RR 1.33 との差は 1 pip、precheck §6)
    sig = _rnb_sig(tp=150.190, sl=149.840)

    _tick_rnb(trader, sig)

    rows = _rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] 1h_rr_low relax: rnb_support_bounce rnb_usdjpy" in m for m in logs)
    assert not any(r.startswith("1h_rr_low(") for r in blocked), blocked
    assert bridge.sent == []


# ── (b) 対称側: allowlist を外す = 変更前コードで従来どおり block ─────────


_SCENARIOS = [
    ("velocity_down", "velocity_down(10pip)_vs_BUY"),
    ("mtf_strong_bias", "mtf_strong_bias(SELL_vs_BUY,rnb_support_bounce)"),
    ("1h_rr_low", "1h_rr_low(1.19<1.2,rnb_support_bounce)"),
]


def _arm(trader, gate):
    if gate == "velocity_down":
        _seed_velocity_down(trader, "USD_JPY", 150.100, 5)
        return _rnb_sig()
    if gate == "mtf_strong_bias":
        _seed_strong_sell_bias(trader, "USD_JPY")
        return _rnb_sig()
    return _rnb_sig(tp=150.190, sl=149.840)


@pytest.mark.parametrize("gate,expected_reason", _SCENARIOS)
def test_control_empty_allowlist_hard_blocks_rnb(tmp_path, monkeypatch, gate, expected_reason):
    """counterfactual control: allowlist を空にすると同じ入力が従来の理由で block
    される = (a) の shadow 化が本 PR の allowlist 起因であることの帰属証明。"""
    _patch_common(monkeypatch)
    monkeypatch.setattr(demo_trader_mod, "_SHADOW_ONLY_DOWNSTREAM_RELAX_MODES", frozenset())
    trader, bridge, _logs, blocked = _make_trader(tmp_path, monkeypatch)
    sig = _arm(trader, gate)

    _tick_rnb(trader, sig)

    assert _rows(trader) == []
    assert expected_reason in blocked, blocked
    assert bridge.sent == []


@pytest.mark.parametrize("gate,expected_reason", _SCENARIOS)
def test_fail_closed_when_rnb_mode_is_not_shadow_only(tmp_path, monkeypatch, gate, expected_reason):
    """(b'') allowlist に居ても実状態 shadow_only=False (= 将来の live 化) なら
    迂回は消える — live 資本が乗る mode に live 保護 gate の迂回を残さない。"""
    _patch_common(monkeypatch)
    monkeypatch.setitem(MODE_CONFIG["rnb_usdjpy"], "shadow_only", False)
    trader, bridge, _logs, blocked = _make_trader(tmp_path, monkeypatch)
    sig = _arm(trader, gate)

    _tick_rnb(trader, sig)

    assert _rows(trader) == []
    assert expected_reason in blocked, blocked
    assert bridge.sent == []


# ── (b') 第 2 の対称側: daytrade_audjpy (shadow_only だが allowlist 外) は不変 ──


def test_daytrade_audjpy_velocity_down_still_hard_blocks(tmp_path, monkeypatch):
    """_mode_is_shadow_only を汎用化した実装はここで落ちる (WS3 stage-2 pre-reg
    🔒 ws3-stage2-barrier-ev-prereg-2026-07-09 の母集団を黙って変える)。"""
    _patch_common(monkeypatch)
    trader, bridge, logs, blocked = _make_trader(tmp_path, monkeypatch)
    # daytrade 窓 30 分 / 閾値 15.0pip: 20 分前 97.700 → current 97.500 = −20pip
    _seed_velocity_down(trader, "AUD_JPY", 97.700, 20)

    trader._tick_entry(
        "daytrade_audjpy", MODE_CONFIG["daytrade_audjpy"], _audjpy_sig(), "15m", "AUD_JPY"
    )

    assert _rows(trader) == []
    assert "velocity_down(20pip)_vs_BUY" in blocked, blocked
    assert not any("relax" in m for m in logs)
    assert bridge.sent == []


def test_daytrade_audjpy_mtf_strong_bias_still_hard_blocks(tmp_path, monkeypatch):
    _patch_common(monkeypatch)
    trader, bridge, logs, blocked = _make_trader(tmp_path, monkeypatch)
    _seed_strong_sell_bias(trader, "AUD_JPY")

    trader._tick_entry(
        "daytrade_audjpy", MODE_CONFIG["daytrade_audjpy"], _audjpy_sig(), "15m", "AUD_JPY"
    )

    assert _rows(trader) == []
    assert "mtf_strong_bias(SELL_vs_BUY,htf_false_breakout)" in blocked, blocked
    assert not any("relax" in m for m in logs)
    assert bridge.sent == []


# ── (d) session_hours は迂回しない / (e) 他 gate は hard block のまま ───────


def test_session_hours_stays_hard_block_for_rnb_after_hours(tmp_path, monkeypatch):
    """21 時台の評価 (precheck §5 の stale bar 入力) は relax 対象 gate を踏む前に
    session_hours で block → 窓外行が LOCK 母集団に混入しない。"""
    _patch_common(monkeypatch, dt_cls=_AfterHoursDatetime)
    trader, bridge, logs, blocked = _make_trader(tmp_path, monkeypatch)
    _seed_strong_sell_bias(trader, "USD_JPY", dt_cls=_AfterHoursDatetime)

    _tick_rnb(trader)

    assert _rows(trader) == []
    assert "session_hours(outside_active)" in blocked, blocked
    assert not any("relax" in m for m in logs)
    assert bridge.sent == []


def test_spike_gate_stays_hard_block_for_rnb(tmp_path, monkeypatch):
    """(e) 迂回は帰属した 3 gate のみ — spike (60s レンジ > 1×ATR) は rnb でも
    従来どおり hard block。_is_shadow_eligible_full 経由で緩めた実装はここで落ちる。"""
    _patch_common(monkeypatch)
    trader, bridge, logs, blocked = _make_trader(tmp_path, monkeypatch)
    now = _FixedDatetime.now(timezone.utc)
    trader._price_history["USD_JPY"] = [
        (now - timedelta(seconds=50), 150.000),
        (now - timedelta(seconds=40), 150.150),  # 15.0pip/60s > ATR 0.07
    ]

    _tick_rnb(trader)

    assert _rows(trader) == []
    assert any(r.startswith("spike(") for r in blocked), blocked
    assert not any("relax" in m for m in logs)
    assert bridge.sent == []


def test_relaxed_rows_keep_entry_hour_inside_active_window(tmp_path, monkeypatch):
    """(d) 補助 pin: relax 経由で生まれた行の entry_time (UTC hour) は 7–20 の範囲。"""
    _patch_common(monkeypatch)
    trader, _bridge, _logs, _blocked = _make_trader(tmp_path, monkeypatch)
    _seed_strong_sell_bias(trader, "USD_JPY")

    _tick_rnb(trader)

    rows = _rows(trader)
    assert rows
    hour = int(str(rows[0]["entry_time"])[11:13])
    assert 7 <= hour <= 20, rows[0]["entry_time"]
