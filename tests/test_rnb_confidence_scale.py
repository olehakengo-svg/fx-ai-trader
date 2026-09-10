"""rnb confidence 単位整合 + confirm marker pin (rule:R3, 2026-09-10)。

バグ 1 (conf 単位不一致): compute_rnb_signal の BUY confidence は 0-1
スケール (`round(min(_score/2.5, 1.0), 2)`, max 1.0) だったが、demo_trader
の conf gate (`confidence < self._params["confidence_threshold"]`,
threshold=30) は全戦略共通で 0-100 スケールを前提とする。単位不一致で
rnb BUY は 100% `conf<30` block = PR #238 で開通したはずの shadow レーン
(LOCK rnb-support-bounce-shadow-forward) が構造的無発火だった。

バグ 2 (confirm marker 欠落 — 本テストの end-to-end 化で発見): QUALIFIED_TYPES
の confirm gate は「"✅" を含む reason >= 1」を要求するが、compute_rnb_signal
の reasons は marker ゼロ → conf 修理後も 100% `no_confirm` block だった。

既存の tests/test_rnb_shadow_only_registration.py は手書き sig
(confidence=80, reasons=["✅ ..."]) を使っていたため、両欠陥とも通していた —
本ファイルは **実際の compute_rnb_signal 出力** を end-to-end で流す。

pin 6 点:
  1. 単位整合: 実 BUY sig の confidence が 0-100 int かつ gate threshold 以上
  2. confirm marker: 実 BUY sig の reasons に "✅" が >= 1 本
  3. end-to-end: 実 BUY sig が conf/confirm gate を通過し shadow 行化する
     (shadow_only 維持 = OANDA 送信ゼロ も同時に pin)
  4. counterfactual A: 正規化を外した旧 0-1 値では conf gate で落ちる
  5. counterfactual B: "✅" を剥がすと no_confirm gate で落ちる
     (両修理がそれぞれ load-bearing であることの帰属証明)
  6. 他モード非影響: gate 側は 0-100 解釈のまま (29 は block / 31 は通過)
     = 修理が signal 側正規化であり gate 側リスケールでないことの pin
"""
from __future__ import annotations

import uuid
from datetime import datetime as real_datetime, timezone

import numpy as np
import pandas as pd

import app as app_mod
import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
import tools.alpha_factor_snapshot as alpha_snap_mod
from modules.demo_db import DemoDB
from modules.demo_trader import MODE_CONFIG, DemoTrader


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
        DemoDB(str(tmp_path / f"rnb_conf_scale_{uuid.uuid4().hex}.db"))
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


def _patch_common(monkeypatch):
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(
        alpha_snap_mod, "snapshot_at", lambda *_a, **_k: {"error": "unit-test"}
    )


def _make_buy_df(n: int = 60) -> pd.DataFrame:
    """rnb 全 5 条件を満たす 15m df (rn=150.00 支持線反発、UTC 12:00 終端)。

    zone: L=149.98 は 150.00 の ±10p 内 / momentum: 5 本で 10p 下落 (>0.5×ATR)
    overshoot: 2p (<=5p) / rejection: 下ヒゲ 86% (>=50%) / BUY: 上から接近。
    score = 1.0 + 0.5(wick>=65%) + 0.4(overshoot) + 0.3(mom>0.8ATR)
          + 0.2(.00 level) = 2.4 → confidence 96 (0-100)。
    """
    idx = pd.date_range(
        end=pd.Timestamp(2026, 5, 28, 12, 0, tz="UTC"), periods=n, freq="15min"
    )
    o = np.full(n, 150.20)
    h = np.full(n, 150.22)
    l = np.full(n, 150.18)
    c = np.full(n, 150.20)
    # 直前バー: close 150.12 (> rn 150.00 — 上から接近)
    o[-2], h[-2], l[-2], c[-2] = 150.20, 150.21, 150.11, 150.12
    # 最終バー: 150.00 タッチ + 長い下ヒゲで反発
    o[-1], h[-1], l[-1], c[-1] = 150.10, 150.12, 149.98, 150.10
    return pd.DataFrame(
        {"Open": o, "High": h, "Low": l, "Close": c,
         "atr": np.full(n, 0.07)},
        index=idx,
    )


def _real_buy_sig() -> dict:
    sig = app_mod.compute_rnb_signal(_make_buy_df(), symbol="USD_JPY")
    assert sig["signal"] == "BUY", "fixture df must produce a real BUY signal"
    return sig


def _rows(trader):
    with trader._db._safe_conn() as conn:
        return conn.execute(
            "SELECT trade_id, entry_type, instrument, mode, is_shadow "
            "FROM demo_trades"
        ).fetchall()


def _conf_block_keys(trader, mode):
    return [k for k in getattr(trader, "_block_counts", {})
            if k.startswith(f"{mode}:conf<")]


# ── pin 1: 単位整合 (signal 関数単体) ──────────────────────────────


def test_rnb_buy_confidence_is_0_100_scale(tmp_path):
    """実 BUY sig の confidence は 0-100 int で、conf gate の default
    threshold (30) を必ず上回る。旧 0-1 スケール (max 1.0) はここで落ちる。"""
    sig = _real_buy_sig()
    conf = sig["confidence"]
    assert isinstance(conf, int), f"confidence must be int 0-100, got {conf!r}"
    assert 0 <= conf <= 100
    threshold = DemoTrader(
        DemoDB(str(tmp_path / f"params_{uuid.uuid4().hex}.db"))
    )._params["confidence_threshold"]
    assert conf >= threshold, (
        f"rnb BUY confidence {conf} < gate threshold {threshold} — "
        "単位不一致 (0-1 vs 0-100) が再発している"
    )


def test_rnb_buy_reasons_carry_confirm_marker():
    """pin 2: QUALIFIED_TYPES confirm gate (demo_trader `no_confirm:` block) は
    "✅" を含む reason >= 1 を要求する。旧 reasons は marker ゼロで、conf
    修理後もレーンが no_confirm で 100% 死んでいた。"""
    sig = _real_buy_sig()
    assert any("✅" in r for r in sig["reasons"]), (
        f"rnb BUY reasons must carry >=1 '✅' confirm marker: {sig['reasons']}"
    )


def test_rnb_wait_confidence_stays_zero():
    """WAIT 応答の confidence=0 は正規化後も不変 (両スケールで同値)。"""
    df = _make_buy_df()
    # zone から外れた価格帯 → WAIT
    for col in ("Open", "High", "Low", "Close"):
        df[col] = df[col] + 0.17
    sig = app_mod.compute_rnb_signal(df, symbol="USD_JPY")
    assert sig["signal"] == "WAIT"
    assert sig["confidence"] == 0


# ── pin 2: end-to-end — 実 sig が conf gate を通り shadow 行化 ─────────


def test_rnb_real_buy_signal_passes_conf_gate_and_lands_shadow_row(
    tmp_path, monkeypatch
):
    """実際の compute_rnb_signal 出力を _tick_entry へ流し、conf gate を
    通過して shadow 行が記録されること (LOCK の N 蓄積路が生きていること) を
    pin。同時に shadow_only 維持 (最悪ケースでも OANDA 送信ゼロ) も検証。"""
    _patch_common(monkeypatch)
    trader, bridge, logs = _make_trader(tmp_path, monkeypatch)

    trader._tick_entry(
        "rnb_usdjpy",
        MODE_CONFIG["rnb_usdjpy"],
        _real_buy_sig(),
        "15m",
        "USD_JPY",
    )

    assert _conf_block_keys(trader, "rnb_usdjpy") == [], (
        "real rnb BUY must not be blocked at the confidence gate"
    )
    rows = _rows(trader)
    assert rows, "real rnb BUY must land a demo_trades row (shadow N 蓄積路)"
    assert rows[0]["entry_type"] == "rnb_support_bounce"
    assert rows[0]["mode"] == "rnb_usdjpy"
    assert rows[0]["is_shadow"] == 1, "shadow_only mode must persist is_shadow=1"
    assert bridge.sent == [], "shadow-only mode must never reach OANDA open_trade"


# ── pin 3: counterfactual — 正規化を外すと conf gate で死ぬ ─────────────


def test_counterfactual_old_0_1_scale_is_blocked_at_conf_gate(
    tmp_path, monkeypatch
):
    """旧実装の 0-1 値 (round(min(score/2.5, 1.0), 2)) に戻すと、同一 sig が
    conf gate で block され行が一切残らない = 修理 (0-100 正規化) が
    load-bearing であることの帰属証明。"""
    _patch_common(monkeypatch)
    trader, bridge, _logs = _make_trader(tmp_path, monkeypatch)

    sig = _real_buy_sig()
    sig["confidence"] = round(min(sig["score"] / 2.5, 1.0), 2)  # 旧 0-1 スケール
    assert sig["confidence"] <= 1.0

    trader._tick_entry(
        "rnb_usdjpy",
        MODE_CONFIG["rnb_usdjpy"],
        sig,
        "15m",
        "USD_JPY",
    )

    assert _rows(trader) == [], "0-1 scale confidence must die at the conf gate"
    assert bridge.sent == []
    assert _conf_block_keys(trader, "rnb_usdjpy"), (
        "block counter must attribute the drop to the confidence gate"
    )


def test_counterfactual_stripped_confirm_marker_is_blocked_no_confirm(
    tmp_path, monkeypatch
):
    """counterfactual B: reasons から "✅" を剥がすと (conf は正規化済みでも)
    QUALIFIED_TYPES confirm gate で block され行が残らない = confirm marker
    修理が独立に load-bearing であることの帰属証明。"""
    _patch_common(monkeypatch)
    trader, bridge, _logs = _make_trader(tmp_path, monkeypatch)

    sig = _real_buy_sig()
    sig["reasons"] = [r.replace("✅", "").strip() for r in sig["reasons"]]

    trader._tick_entry(
        "rnb_usdjpy",
        MODE_CONFIG["rnb_usdjpy"],
        sig,
        "15m",
        "USD_JPY",
    )

    assert _rows(trader) == [], "marker-less reasons must die at no_confirm gate"
    assert bridge.sent == []
    assert any(
        k.startswith("rnb_usdjpy:no_confirm")
        for k in getattr(trader, "_block_counts", {})
    ), "block counter must attribute the drop to the no_confirm gate"


# ── pin 4: 他モード非影響 — gate は 0-100 解釈のまま ─────────────────


def test_other_mode_conf_gate_scale_unchanged(tmp_path, monkeypatch):
    """修理は signal 側 (rnb) の正規化であり、gate 側のリスケールではない。
    0-100 スケールを返す他モードの境界挙動が不変であることを pin:
    conf=29 は block / conf=31 は conf gate を通過する。"""
    _patch_common(monkeypatch)
    control_cfg = {"instrument": "USD_JPY", "icon": "UT",
                   "label": "unit-test-control"}

    def _control_sig(conf):
        return {
            "signal": "BUY",
            "entry": 150.000,
            "sl": 149.850,
            "tp": 150.200,
            "entry_type": "rnb_support_bounce",
            "confidence": conf,
            "score": 1.0,
            "reasons": ["conf gate scale pin"],
            "atr": 0.07,
            "regime": {"regime": "TRANSITION"},
            "layer_status": {"trade_ok": True,
                             "layer1": {"direction": "neutral"}},
        }

    # threshold (30) 未満 → block
    trader, bridge, _logs = _make_trader(tmp_path, monkeypatch)
    trader._tick_entry("daytrade", control_cfg, _control_sig(29), "15m",
                       "USD_JPY")
    assert _conf_block_keys(trader, "daytrade"), (
        "conf=29 (0-100 scale) must still be blocked — gate 側がリスケール"
        "されていれば通ってしまう"
    )
    assert _rows(trader) == []
    assert bridge.sent == []

    # threshold 以上 → conf gate は通過
    trader2, _bridge2, _logs2 = _make_trader(tmp_path, monkeypatch)
    trader2._tick_entry("daytrade", control_cfg, _control_sig(31), "15m",
                        "USD_JPY")
    assert _conf_block_keys(trader2, "daytrade") == [], (
        "conf=31 (0-100 scale) must pass the confidence gate unchanged"
    )
