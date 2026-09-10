"""rnb_usdjpy: block カウンタの estimand 分離 + registration drift ガード
(rule:R3, 2026-09-05)。

背景 — 監視ログが 2026-08-26〜09-04 の 8 回連続で `rnb_usdjpy:direction_filter`
を 🔴 escalate し「compute_rnb_signal の WAIT-path バグ」を仮説に置いていた。
実体は 2 つの独立した構造事実:

  (1) `direction_filter` カウンタは「方向が逆」と「そもそもシグナルが無い
      (WAIT)」を同じ名前で数えていた。direction_filter を持つ唯一のモード
      rnb_usdjpy の signal_fn (app.compute_rnb_signal) は WAIT / BUY しか
      返さず SELL への return path が構造上存在しない (12.8y / 315,623 bar
      実測で SELL=0 / BUY 0.705% / WAIT 99.295%) ため、旧ラベルの中身は
      **恒久的に 100% が WAIT** = 「方向棄却」を一度も測っていなかった。

  (2) `rnb_support_bounce` は 2026-04-05 の導入コミット db5e3e4c で
      MODE_CONFIG / signal_fn / _1H_PRESERVE_SLTP / MAX_HOLD_SEC には
      登録されたが **QUALIFIED_TYPES へは一度も登録されなかった**。
      よって BUY が出ても `unknown_type:rnb_support_bounce` で落ち、
      auto_start=True のまま **shadow 1 行すら出せないモード**だった。

本テストは (1) の分離を挙動レベルで pin し、(2) を「既知ドリフト集合との
完全一致」で pin する。

(2) は 2026-09-10 に解消済み — stage-1 構造的 shadow-only 登録 (rule:R1,
user 承認 2026-09-10「進めて」, packet:
knowledge-base/wiki/decisions/rnb-support-bounce-r1-packet-2026-09-10.md)。
既知ドリフト集合は空になり、完全一致 pin は「新規ドリフトの検出」専用に
戻った。登録後の構造 (shadow-only 3 点 block / QUALIFIED 化 / sentinel
非追加) は tests/test_rnb_shadow_only_registration.py が pin する。

分析: knowledge-base/wiki/analyses/rnb-dead-mode-and-block-estimand-2026-09-05.md
教訓: knowledge-base/wiki/lessons/lesson-block-counter-unmeasured-estimand-2026-09-05.md
"""
from __future__ import annotations

import ast
import inspect
import textwrap
import uuid
from datetime import datetime as real_datetime, timezone
from unittest.mock import MagicMock

import pytest

import app as app_mod
import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader, MODE_CONFIG


_LONDON_THU = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)


# ── _tick_entry ローカルの型集合を AST で取り出す ────────────────────────
def _literal_sets_from_tick_entry() -> dict:
    src = textwrap.dedent(inspect.getsource(DemoTrader._tick_entry))
    tree = ast.parse(src)
    out: dict = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id not in ("QUALIFIED_TYPES", "CONDITIONAL_TYPES", "BLOCKED_TYPES"):
            continue
        if isinstance(node.value, ast.Set):
            out[target.id] = {e.value for e in node.value.elts
                              if isinstance(e, ast.Constant) and isinstance(e.value, str)}
        elif (isinstance(node.value, ast.Call)
              and isinstance(node.value.func, ast.Name)
              and node.value.func.id == "set"
              and not node.value.args):
            out[target.id] = set()
    missing = {"QUALIFIED_TYPES", "CONDITIONAL_TYPES", "BLOCKED_TYPES"} - set(out)
    assert not missing, f"_tick_entry から取り出せなかった型集合: {sorted(missing)}"
    return out


def _literal_entry_types(fn_name: str) -> set:
    """signal_fn のソースから `"entry_type": "<literal>"` を全て集める。

    変数経由で entry_type を組み立てる関数 (compute_daytrade_signal 等) からは
    WAIT sentinel の literal しか取れない = ガードは保守的 (false positive を
    出さない) 方向に効く。
    """
    fn = getattr(app_mod, fn_name, None)
    if fn is None:
        return set()
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, val in zip(node.keys, node.values):
            if (isinstance(key, ast.Constant) and key.value == "entry_type"
                    and isinstance(val, ast.Constant)
                    and isinstance(val.value, str) and val.value):
                found.add(val.value)
    return found


# ══════════════════════════════════════════════════════════════════════
# (1) block カウンタの estimand 分離 — 挙動 pin
# ══════════════════════════════════════════════════════════════════════

def _pinned_datetime(now_utc: real_datetime):
    class _Pinned(real_datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return now_utc.replace(tzinfo=None)
            return now_utc.astimezone(tz)
    return _Pinned


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"rnb_{uuid.uuid4().hex}.db")))
    monkeypatch.setattr(trader, "_add_log", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_check_drawdown", lambda: False)
    monkeypatch.setattr(trader._exposure_mgr, "check_new_trade",
                        lambda *_a, **_k: (True, ""))
    monkeypatch.setattr(
        trader, "_get_mtf_regime",
        lambda _inst: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"})
    monkeypatch.setattr(trader, "_compute_dow_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(trader, "_compute_v2_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(trader, "_compute_confluence_tag",
                        lambda *_a, **_k: {"score": 0, "details": ""})
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: None)
    fake_bridge = MagicMock()
    fake_bridge.active = True
    fake_bridge.is_mode_allowed.return_value = True
    fake_bridge.open_trade.return_value = False
    monkeypatch.setattr(trader, "_oanda", fake_bridge)
    return trader


def _rnb_sig(signal: str) -> dict:
    return {
        "signal": signal,
        "entry": 150.000 if signal != "WAIT" else 150.123,
        "sl": 149.850,
        "tp": 150.200,
        "entry_type": "rnb_support_bounce" if signal != "WAIT" else "",
        "confidence": 80 if signal != "WAIT" else 0,
        "score": 1.0 if signal != "WAIT" else 0,
        "reasons": ["✅ rnb estimand pin"] if signal != "WAIT" else [],
        "atr": 0.07,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _drive(signal: str, tmp_path, monkeypatch):
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _pinned_datetime(_LONDON_THU))
    trader = _make_trader(tmp_path, monkeypatch)
    cfg = dict(MODE_CONFIG["rnb_usdjpy"])
    trader._tick_entry("rnb_usdjpy", cfg, _rnb_sig(signal), "15m", "USD_JPY")
    return dict(getattr(trader, "_block_counts", {})), trader


def test_wait_is_counted_as_no_signal_not_direction_filter(tmp_path, monkeypatch):
    """WAIT は「方向棄却」ではない — 旧実装はここを direction_filter と数えていた。"""
    counts, _trader = _drive("WAIT", tmp_path, monkeypatch)
    assert counts.get("rnb_usdjpy:no_signal") == 1, counts
    assert "rnb_usdjpy:direction_filter" not in counts, counts


def test_opposite_direction_is_still_counted_as_direction_filter(tmp_path, monkeypatch):
    """本物の方向棄却 (SELL vs BUY-only) は direction_filter のまま。"""
    counts, _trader = _drive("SELL", tmp_path, monkeypatch)
    assert counts.get("rnb_usdjpy:direction_filter") == 1, counts
    assert "rnb_usdjpy:no_signal" not in counts, counts


def test_buy_passes_direction_gate_and_lands_as_shadow_row(tmp_path, monkeypatch):
    """許可方向 (BUY) は direction gate と unknown_type を通過し shadow 行になる。

    2026-09-10 stage-1 shadow-only 登録 (rule:R1, packet
    rnb-support-bounce-r1-packet-2026-09-10) 後の挙動 pin:
      - `unknown_type:rnb_support_bounce` はもう発生しない (dead mode 解消)
      - 行は必ず is_shadow=1 で永続化 (shadow_only=True の write-path 保証)
      - OANDA open_trade は呼ばれない (送信ガード最終段)
    登録が黙って外れたら unknown_type 復活で本テストが落ちる。
    """
    counts, trader = _drive("BUY", tmp_path, monkeypatch)
    assert "rnb_usdjpy:no_signal" not in counts, counts
    assert "rnb_usdjpy:direction_filter" not in counts, counts
    assert not any(k.startswith("rnb_usdjpy:unknown_type") for k in counts), counts
    with trader._db._safe_conn() as conn:
        rows = conn.execute(
            "SELECT entry_type, mode, is_shadow FROM demo_trades"
        ).fetchall()
    assert rows, f"shadow 行が書かれていない (counts={counts})"
    assert rows[0]["entry_type"] == "rnb_support_bounce"
    assert rows[0]["mode"] == "rnb_usdjpy"
    assert rows[0]["is_shadow"] == 1
    assert not trader._oanda.open_trade.called, (
        "shadow-only mode から OANDA open_trade が呼ばれた")


# ══════════════════════════════════════════════════════════════════════
# (2) 構造 pin — 性質を書く (MEMORY: 構文でなくスコープを絞った性質)
# ══════════════════════════════════════════════════════════════════════

def test_direction_filter_is_only_used_by_rnb_usdjpy():
    """このラベル分離の作用域を pin。新しい direction_filter モードが増えたら
    その signal_fn についても「WAIT しか来ないのか」を再検討させる。"""
    modes = sorted(m for m, c in MODE_CONFIG.items() if c.get("direction_filter"))
    assert modes == ["rnb_usdjpy"], modes


def test_compute_rnb_signal_cannot_emit_sell():
    """compute_rnb_signal が返しうる signal literal は {WAIT, BUY} のみ。

    SELL path が追加されたらこのテストが落ちる — その時点で
    `direction_filter` カウンタは初めて非ゼロの意味を持つので、監視側の
    読み方 (analyses/rnb-dead-mode-and-block-estimand-2026-09-05.md) を
    更新すること。
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(app_mod.compute_rnb_signal)))
    signals = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, val in zip(node.keys, node.values):
            if (isinstance(key, ast.Constant) and key.value == "signal"
                    and isinstance(val, ast.Constant)):
                signals.add(val.value)
    assert signals == {"WAIT", "BUY"}, (
        f"compute_rnb_signal の signal literal が変化した: {sorted(signals)}")


# 既知の registration drift: **空** (2026-09-10 に唯一の既知ドリフト
# ("rnb_usdjpy", "rnb_support_bounce") を stage-1 shadow-only 登録で解消 —
# rule:R1, user 承認 2026-09-10, packet rnb-support-bounce-r1-packet-2026-09-10)。
# 新規ドリフトが 1 件でも生まれれば完全一致 pin が落ちて判断が要求される。
KNOWN_REGISTRATION_DRIFT: set = set()


def test_auto_start_modes_have_no_unknown_registration_drift():
    """auto_start モードの signal_fn が返す literal entry_type は
    QUALIFIED ∪ CONDITIONAL ∪ BLOCKED に入っていなければならない。

    db5e3e4c (2026-04-05) は MODE_CONFIG / signal_fn / preserve list /
    MAX_HOLD_SEC の 4 箇所を配線したのに QUALIFIED_TYPES だけ忘れ、
    153 日間「動いているが 1 行も出せないモード」を生んだ。**完全一致**で
    pin するので、新規ドリフトも既知ドリフトの解消も必ずテストを落とす。
    """
    sets = _literal_sets_from_tick_entry()
    registered = (sets["QUALIFIED_TYPES"] | sets["CONDITIONAL_TYPES"]
                  | sets["BLOCKED_TYPES"])
    drift = set()
    for mode, cfg in MODE_CONFIG.items():
        if not cfg.get("auto_start"):
            continue
        for et in _literal_entry_types(cfg.get("signal_fn", "")):
            if et not in registered:
                drift.add((mode, et))
    assert drift == KNOWN_REGISTRATION_DRIFT, (
        f"registration drift 変化: 検出={sorted(drift)} / "
        f"既知={sorted(KNOWN_REGISTRATION_DRIFT)}")


def test_registration_drift_scan_actually_reaches_real_modes():
    """ガードの分母 pin — auto_start モードを 1 つも走査していない
    (= 常に drift 空集合) 状態で緑になるのを防ぐ。"""
    scanned = [m for m, c in MODE_CONFIG.items() if c.get("auto_start")]
    assert len(scanned) >= 20, scanned
    sets = _literal_sets_from_tick_entry()
    assert len(sets["QUALIFIED_TYPES"]) >= 50, len(sets["QUALIFIED_TYPES"])
    assert "wait" in sets["BLOCKED_TYPES"]
