"""送信前拒否・shadow 化の観測性 5 件 — counterfactual pin (rule:R3, 2026-09-23).

背景: knowledge-base/wiki/decisions/weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22.md
  §2 不成立 (v) PRE_SEND_GUARD 行 (PR #289、Codex 3 巡 + 敵対的レビュー) が確定した
  「送信前拒否 / shadow 化」の帰属欠陥 5 件。分析:
  knowledge-base/wiki/analyses/pre-send-guard-observability-r3-2026-09-23.md

  1. demo_trader pre-check (`_bridge_active` 偽 / `is_mode_allowed` 偽) は oanda_audit
     `blocked` を書くが **in-memory `_is_shadow` / ExposureManager を shadow 化しない**
     (bridge 拒否経路 `[SHADOW_FIX] Bridge refused` と非対称)。DB row 自体は write-time
     invariant (demo_db.open_trade enforce_oanda_live_invariant、48025ebd3 2026-05-11) で
     既に is_shadow=1 — DRAFT §2 (c2) の「is_shadow=0 row が残る」は DB row については
     stale (本 pin が invariant として併記)。欠陥 = 実弾なしの live exposure 計上 +
     `[SHADOW_FIX]` marker ログ無し (= 転記時に (c2) を識別する一次ソースが無い)
  2. bridge `open_trade` 内 `if not self.active` / `is_mode_allowed` 偽 (pre-check 通過後の
     race) は audit も log も書かずに False
  3. `_promo_block_cause` (mode_off / pair_demoted / force_demoted / session_filter …) が
     event 時点で永続されない — 転記時に現在の strategy mode を読むと誤帰属
     (Codex P2 4075642847)
  4. `_UNIVERSAL_SENTINEL` の shadow bypass (`[SHADOW] <gate> bypass:`) の cause が DB logs
     (8000 行刈り込み) にしか残らない (Codex P2 4075642842)
  5. order-bar 予約が後段 `_block` より前にあるため、一度 block されると以降の tick は
     `order_bar_dedup` で固定され、`gate_block_daily` から本当の blocker が消える

各修復は revert で落ちる pin + 対称側の不変 pin を併設する
(MEMORY feedback_check_the_symmetric_side_2026_09_19):
  - 既存 bridge 拒否経路 (`[SHADOW_FIX] Bridge refused transmission`) と accept 経路は不変
  - bridge daily-loss gate は従来どおり自前の `blocked` 1 行のみ / gate 通過は `blocked` 0 行
  - session_filter 変種 `shadow_tracking(session_filter_out)` の優先は不変
    (tests/test_session_filter_promotion_guard.py が pin)
  - 非 sentinel 戦略の `_block` (row なし hard block) は不変
  - 予約前 block / bar_ts なし (予約なし) では first-block は記録されない (恒真でない)
凍結値・estimand・live 送信ロジックは一切変更しない。
"""
from __future__ import annotations

import inspect
import json
import os
import re
import tempfile
import textwrap
import uuid
from datetime import datetime as real_datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.block_event_logger import init_block_table, query_block_counts
from modules.demo_db import DemoDB
from modules.demo_trader import (
    _PROMO_BLOCK_REASON_TAG,
    _SHADOW_BYPASS_REASON_TAG,
    ORDER_BAR_FIRST_BLOCK_REASON_PREFIX,
    DemoTrader,
    promo_block_cause_from_audit,
)
from modules.oanda_bridge import OandaBridge

ELITE = "trendline_sweep"


class _LondonDatetime(real_datetime):
    """2026-05-28 (木) 12:00 UTC — London session、静的 hour block なし。"""

    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        if tz is None:
            return base.replace(tzinfo=None)
        return base.astimezone(tz)


# ── 共通ハーネス (tests/test_bridge_send_accept_contract.py と同型) ────────


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"psg_{uuid.uuid4().hex}.db")))
    logs = []
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
        trader, "_compute_confluence_tag", lambda *_a, **_k: {"score": 0, "details": ""},
    )
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_aggregate_kelly", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_ruin_probability", lambda *_a, **_k: None)
    return trader, logs


def _sig(entry_type=ELITE, signal="BUY", entry=1.2000, tp=1.2060, confidence=80,
         bar_ts=None):
    sig = {
        "signal": signal,
        "entry": entry,
        "tp": tp,
        "entry_type": entry_type,
        "confidence": confidence,
        "score": 1.0,
        "reasons": ["✅ unit-test"],
        "atr": 0.0005,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }
    if bar_ts is not None:
        sig["_closed_bar_ts"] = bar_ts
    return sig


def _cfg(instrument):
    return {"instrument": instrument, "icon": "UT", "label": "unit-test"}


def _fake_bridge(*, accept=True, active=True, mode_allowed=True, strategy_mode="live"):
    fake = MagicMock()
    fake.active = active
    fake.is_mode_allowed.return_value = mode_allowed
    fake.get_strategy_mode.return_value = strategy_mode
    if accept:
        def _accept(**kwargs):
            cb = kwargs.get("callback")
            if cb:
                cb(kwargs["demo_trade_id"], "OANDA-TEST-1")
            return True
        fake.open_trade.side_effect = _accept
    else:
        fake.open_trade.return_value = False
    return fake


def _promote_synthetic_elite(monkeypatch):
    """trendline_sweep は全セル PAIR_DEMOTED 化済み — 契約検証のため ELITE 経路を
    synthetic に復元する (tests/test_bridge_send_accept_contract.py と同じ手法)。"""
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _LondonDatetime)
    monkeypatch.setattr(DemoTrader, "_ELITE_LIVE", frozenset({ELITE}))
    monkeypatch.setattr(
        DemoTrader, "_PAIR_DEMOTED",
        {c for c in DemoTrader._PAIR_DEMOTED if c[0] != ELITE},
    )


def _sentinelize_elite(monkeypatch):
    """同じ synthetic 戦略を _UNIVERSAL_SENTINEL に入れて `_is_shadow_eligible_full`
    を真にする (weekend_gap_fade と同じ bypass 分岐に落とす)。"""
    monkeypatch.setattr(
        DemoTrader, "_UNIVERSAL_SENTINEL", set(DemoTrader._UNIVERSAL_SENTINEL) | {ELITE},
    )


def _run(tmp_path, monkeypatch, *, fake, sig=None, sentinel=False):
    _promote_synthetic_elite(monkeypatch)
    if sentinel:
        _sentinelize_elite(monkeypatch)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_oanda", fake)
    trader._tick_entry("daytrade", _cfg("EUR_USD"), sig or _sig(), "15m", "EUR_USD")
    return trader, logs


def _rows(trader):
    with trader._db._safe_conn() as conn:
        return conn.execute(
            "SELECT trade_id, is_shadow, oanda_trade_id, reasons FROM demo_trades"
        ).fetchall()


def _row_reasons(row) -> list:
    raw = row["reasons"]
    try:
        val = json.loads(raw) if raw else []
    except Exception:
        val = [str(raw)]
    return val if isinstance(val, list) else [str(val)]


def _audits(fake):
    return [c.kwargs for c in fake._add_audit.call_args_list]


# ═══════════════════════════════════════════════════════════════════════
# 1. demo_trader pre-check (bridge inactive / mode not allowed) → row も shadow 化
# ═══════════════════════════════════════════════════════════════════════


def test_pre_check_bridge_inactive_escalates_row_to_shadow(tmp_path, monkeypatch):
    fake = _fake_bridge(active=False)
    trader, logs = _run(tmp_path, monkeypatch, fake=fake)

    rows = _rows(trader)
    assert rows and len(rows) == 1
    assert not fake.open_trade.called, "pre-check must stop before the bridge"
    blocked = [a for a in _audits(fake) if a.get("bridge_status") == "blocked"]
    assert blocked and blocked[0]["block_reason"] == "bridge_inactive"
    assert not (rows[0]["oanda_trade_id"] or "")
    # invariant (write-time flag 48025ebd3): DB row は fill 前は常に is_shadow=1
    assert rows[0]["is_shadow"] == 1
    # counterfactual: 修復前は ExposureManager の position が live (is_shadow=False) の
    # まま残り、実弾なしの exposure 計上 + marker ログ無しだった
    pos = trader._exposure_mgr._positions.get(rows[0]["trade_id"])
    assert pos is not None and pos["is_shadow"] is True, pos
    assert any("[SHADOW_FIX] Pre-send guard" in m and "bridge_inactive" in m for m in logs), logs


def test_pre_check_mode_not_allowed_escalates_row_to_shadow(tmp_path, monkeypatch):
    fake = _fake_bridge(mode_allowed=False)
    trader, logs = _run(tmp_path, monkeypatch, fake=fake)

    rows = _rows(trader)
    assert rows and len(rows) == 1
    assert not fake.open_trade.called
    blocked = [a for a in _audits(fake) if a.get("bridge_status") == "blocked"]
    assert blocked and blocked[0]["block_reason"] == "mode_daytrade_not_allowed"
    assert rows[0]["is_shadow"] == 1
    pos = trader._exposure_mgr._positions.get(rows[0]["trade_id"])
    assert pos is not None and pos["is_shadow"] is True, pos
    assert any("[SHADOW_FIX] Pre-send guard" in m and "mode_daytrade_not_allowed" in m
               for m in logs), logs


def test_symmetric_bridge_refusal_path_unchanged(tmp_path, monkeypatch):
    """対称側: pre-check を通り bridge が False を返す既存経路は従来どおり
    `[SHADOW_FIX] Bridge refused transmission` で shadow 化し、pre-check ログは出ない。"""
    fake = _fake_bridge(accept=False)
    trader, logs = _run(tmp_path, monkeypatch, fake=fake)

    rows = _rows(trader)
    assert fake.open_trade.called
    assert rows and rows[0]["is_shadow"] == 1
    assert trader._exposure_mgr._positions[rows[0]["trade_id"]]["is_shadow"] is True
    assert any("[SHADOW_FIX] Bridge refused transmission" in m for m in logs)
    assert not any("[SHADOW_FIX] Pre-send guard" in m for m in logs)
    statuses = [a.get("bridge_status") for a in _audits(fake)]
    assert "sent" not in statuses and "blocked" not in statuses, statuses


def test_symmetric_accept_path_stays_live(tmp_path, monkeypatch):
    fake = _fake_bridge(accept=True)
    trader, logs = _run(tmp_path, monkeypatch, fake=fake)

    rows = _rows(trader)
    assert rows and rows[0]["is_shadow"] == 0 and rows[0]["oanda_trade_id"] == "OANDA-TEST-1"
    assert trader._exposure_mgr._positions[rows[0]["trade_id"]]["is_shadow"] is False
    assert "sent" in [a.get("bridge_status") for a in _audits(fake)]
    assert not any("[SHADOW_FIX]" in m for m in logs), logs
    assert not any(r.startswith(_PROMO_BLOCK_REASON_TAG) for r in _row_reasons(rows[0]))
    assert not any(r.startswith(_SHADOW_BYPASS_REASON_TAG) for r in _row_reasons(rows[0]))


# ═══════════════════════════════════════════════════════════════════════
# 2. OandaBridge.open_trade — 無 audit で False を返す race 経路に `blocked` audit
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DemoDB(db_path=path)
    os.unlink(path)


def _bridge(db, monkeypatch) -> OandaBridge:
    monkeypatch.setenv("DAILY_LOSS_LIMIT_PIPS", "20.0")
    monkeypatch.setenv("OANDA_LIVE", "true")
    b = OandaBridge(db=db)
    b._daily_loss_cache_ttl_s = 0.0
    return b


def _blocked_audits(db):
    return [r for r in db.get_oanda_audit(limit=50) if r["bridge_status"] == "blocked"]


def test_open_trade_inactive_race_writes_blocked_audit(db, monkeypatch):
    b = _bridge(db, monkeypatch)
    monkeypatch.setattr(type(b), "active", property(lambda self: False))
    logs = []
    assert b.open_trade(
        demo_trade_id="D-RACE-1", direction="BUY", sl=149.5, tp=151.0,
        mode="daytrade", instrument="USD_JPY", units=1000,
        entry_type="weekend_gap_fade", skip_sent_audit=True,
        log_callback=logs.append,
    ) is False
    rows = _blocked_audits(db)
    assert len(rows) == 1, rows
    assert rows[0]["demo_trade_id"] == "D-RACE-1"
    assert rows[0]["entry_type"] == "weekend_gap_fade"
    assert rows[0]["block_reason"] == "bridge_inactive_race"
    assert rows[0]["is_live"] is False
    assert any("bridge_inactive_race" in m for m in logs), logs


def test_open_trade_mode_not_allowed_race_writes_blocked_audit(db, monkeypatch):
    b = _bridge(db, monkeypatch)
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    monkeypatch.setattr(b, "is_mode_allowed", lambda _mode: False)
    assert b.open_trade(
        demo_trade_id="D-RACE-2", direction="BUY", sl=149.5, tp=151.0,
        mode="daytrade", instrument="USD_JPY", units=1000,
    ) is False
    rows = _blocked_audits(db)
    assert len(rows) == 1, rows
    assert rows[0]["demo_trade_id"] == "D-RACE-2"
    assert rows[0]["block_reason"] == "mode_daytrade_not_allowed_race"
    # entry_type 未指定時は従来の audit 規約どおり mode を entry_type に使う
    assert rows[0]["entry_type"] == "daytrade"


def test_open_trade_unsupported_instrument_writes_blocked_audit(db, monkeypatch):
    b = _bridge(db, monkeypatch)
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    assert b.open_trade(
        demo_trade_id="D-RACE-3", direction="BUY", sl=1.0, tp=2.0,
        mode="daytrade", instrument="FOO_BAR", units=1000,
    ) is False
    rows = _blocked_audits(db)
    assert len(rows) == 1, rows
    assert rows[0]["block_reason"] == "unsupported_instrument(FOO_BAR)"


def test_symmetric_daily_loss_gate_still_writes_exactly_one_blocked_audit(db, monkeypatch):
    b = _bridge(db, monkeypatch)
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    monkeypatch.setattr(b, "is_mode_allowed", lambda _mode: True)
    monkeypatch.setattr(b, "_check_daily_loss_gate", lambda: (True, -42.0))
    assert b.open_trade(
        demo_trade_id="D-DL", direction="SELL", sl=150.5, tp=149.0,
        mode="scalp", instrument="USD_JPY", units=1000,
    ) is False
    rows = _blocked_audits(db)
    assert len(rows) == 1, rows
    assert rows[0]["block_reason"].startswith("daily_loss_limit(")


def test_symmetric_gates_pass_writes_no_blocked_audit(db, monkeypatch):
    b = _bridge(db, monkeypatch)
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    monkeypatch.setattr(b, "is_mode_allowed", lambda _mode: True)
    monkeypatch.setattr(b, "_check_daily_loss_gate", lambda: (False, 0.0))
    fired = []
    monkeypatch.setattr(b, "_fire", lambda fn: fired.append(fn))
    assert b.open_trade(
        demo_trade_id="D-OK", direction="BUY", sl=149.5, tp=151.0,
        mode="scalp", instrument="USD_JPY", units=1000,
    ) is True
    assert len(fired) == 1
    assert _blocked_audits(db) == []


# ═══════════════════════════════════════════════════════════════════════
# 3. `_promo_block_cause` を event 時点で row (reasons) + oanda_audit に永続
# ═══════════════════════════════════════════════════════════════════════


def test_mode_off_promo_cause_persisted_on_row_and_audit(tmp_path, monkeypatch):
    fake = _fake_bridge(strategy_mode="off")
    trader, logs = _run(tmp_path, monkeypatch, fake=fake)

    rows = _rows(trader)
    assert rows and len(rows) == 1 and rows[0]["is_shadow"] == 1
    assert not fake.open_trade.called
    reasons = _row_reasons(rows[0])
    assert f"{_PROMO_BLOCK_REASON_TAG} mode_off" in reasons, reasons
    skipped = [a for a in _audits(fake) if a.get("bridge_status") == "skipped"]
    assert skipped and skipped[0]["block_reason"] == "shadow_tracking(promo_block:mode_off)", skipped
    # mode_off は v8.9 fallback (無ログ) で shadow 化されるため、event 時点の一次ソースは
    # 統一永続点の `[PROMO_BLOCK]` ログ (Post-gate escalation ログは発火しない)
    assert any("[PROMO_BLOCK] " in m and "cause=mode_off" in m for m in logs), logs
    assert not any("[SHADOW_FIX] Post-gate escalation" in m for m in logs)
    # event 時点の記録 = その後 strategy mode を live に戻しても row の marker は不変
    fake.get_strategy_mode.return_value = "live"
    assert f"{_PROMO_BLOCK_REASON_TAG} mode_off" in _row_reasons(_rows(trader)[0])


def test_promo_cause_survives_late_demotion_gate_after_live_override(tmp_path, monkeypatch):
    """PR #293 review P2 (4078373240): GRAIL/C1/PRIME の live 復活 (`_shadow_at_open=False`)
    の後に `_apply_force_demoted_final_gate` が shadow へ戻し `_shadow_at_open=True` を書く
    経路では、可変の `_shadow_at_open` を条件に使うと帰属が落ちる。「row 書込み時の live 意図」
    は不変 flag で判定し、`[PROMO_BLOCK] force_demoted` + audit variant が残ることを pin。"""
    fake = _fake_bridge(accept=True, strategy_mode="")
    _promote_synthetic_elite(monkeypatch)
    # synthetic: ELITE 戦略を FORCE_DEMOTED 扱いにし (cause=force_demoted)、GRAIL 候補にも入れて
    # フィルタ合致 → live 復活 → FD 最終ゲートで shadow 化、という実機構の順序を踏ませる
    monkeypatch.setattr(
        DemoTrader, "_is_force_demoted_entry",
        lambda self, et, inst="": et == ELITE,
    )
    monkeypatch.setattr(
        DemoTrader, "_GRAIL_CANDIDATES", set(getattr(DemoTrader, "_GRAIL_CANDIDATES", set())) | {ELITE},
    )
    monkeypatch.setenv("GRAIL_SENTINEL_ENABLED", "1")
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_check_grail_filter", lambda *_a, **_k: True)
    monkeypatch.setattr(trader, "_oanda", fake)
    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    rows = _rows(trader)
    assert rows and len(rows) == 1 and rows[0]["is_shadow"] == 1
    assert not fake.open_trade.called
    # 実機構の順序が踏まれたこと (GRAIL 復活 → FD 最終ゲート)
    assert any("[GRAIL] " in m and "LIVE Sentinel" in m for m in logs), logs
    assert any("[FORCE_DEMOTED_GATE] " in m for m in logs), logs
    reasons = _row_reasons(rows[0])
    assert f"{_PROMO_BLOCK_REASON_TAG} force_demoted" in reasons, reasons
    skipped = [a for a in _audits(fake) if a.get("bridge_status") == "skipped"]
    assert skipped and skipped[0]["block_reason"] == "shadow_tracking(promo_block:force_demoted)", skipped


def test_promo_block_marker_absent_when_gate_passes(tmp_path, monkeypatch):
    """恒真でない側: promotion gate を通った row には `[PROMO_BLOCK]` が付かない。"""
    fake = _fake_bridge(accept=True, strategy_mode="live")
    trader, _ = _run(tmp_path, monkeypatch, fake=fake)
    rows = _rows(trader)
    assert rows and rows[0]["is_shadow"] == 0
    assert not any(r.startswith(_PROMO_BLOCK_REASON_TAG) for r in _row_reasons(rows[0]))
    assert "skipped" not in [a.get("bridge_status") for a in _audits(fake)]


def test_symmetric_shadow_tracking_plain_when_shadow_came_from_upstream(tmp_path, monkeypatch):
    """対称側: 上流 bypass で既に shadow の row (sentinel × recent_emit) は post-gate
    escalation を経ないので audit は従来どおり素の `shadow_tracking` のまま。"""
    fake = _fake_bridge(strategy_mode="off")
    _promote_synthetic_elite(monkeypatch)
    _sentinelize_elite(monkeypatch)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_oanda", fake)
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: 5.0)
    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    rows = _rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    skipped = [a for a in _audits(fake) if a.get("bridge_status") == "skipped"]
    assert skipped and skipped[0]["block_reason"] == "shadow_tracking", skipped
    assert not any("[SHADOW_FIX] Post-gate escalation" in m for m in logs)
    assert not any(r.startswith(_PROMO_BLOCK_REASON_TAG) for r in _row_reasons(rows[0]))


def test_promo_block_cause_normalizer_covers_both_audit_generations():
    """PR #293 review P2 (4078290940): legacy `session_filter_out` (P-V4 契約、書き換え
    ない) と R3 標準 `promo_block:<cause>` を消費側で 1 つの cause に正規化する。"""
    assert promo_block_cause_from_audit("shadow_tracking(promo_block:mode_off)") == "mode_off"
    assert promo_block_cause_from_audit("shadow_tracking(session_filter_out)") == "session_filter"
    assert promo_block_cause_from_audit("shadow_tracking") == ""
    assert promo_block_cause_from_audit("shadow_tracking(weekend_gap_spread_cap(spread=12.0p>10.0p))") == ""
    assert promo_block_cause_from_audit("daily_loss_limit(-42.0pip<=-20.0pip)") == ""
    assert promo_block_cause_from_audit(None) == ""


def test_session_filter_keeps_legacy_audit_key_and_gets_promo_marker(tmp_path, monkeypatch):
    """session_filter は audit を legacy `shadow_tracking(session_filter_out)` のまま
    (exact pin を持つ P-V4 契約) にし、row には標準 `[PROMO_BLOCK] session_filter` を付ける
    — 両世代を helper で同じ cause に読めることの pin (PR #293 review P2)。"""
    import tests.test_session_filter_promotion_guard as _sf
    from edge_cell_test_helpers import make_trader as _make_sf_trader

    cell = (_sf.VIX, _sf.INST)
    monkeypatch.setattr(demo_trader_mod, "DemoTrader", DemoTrader)
    monkeypatch.setattr(
        DemoTrader, "_PAIR_PROMOTED", frozenset(set(DemoTrader._PAIR_PROMOTED) | {cell}))
    monkeypatch.setattr(
        DemoTrader, "_PAIR_DEMOTED", frozenset(t for t in DemoTrader._PAIR_DEMOTED if t != cell))
    monkeypatch.setattr(
        DemoTrader, "_PAIR_SESSION_FILTER", {**DemoTrader._PAIR_SESSION_FILTER, cell: {"Overlap"}})
    trader, logs = _make_sf_trader(tmp_path, monkeypatch, hour=_sf.HOUR_OUT)
    audits = []
    trader._add_oanda_audit = lambda **kw: audits.append(kw)

    trader._tick_entry("daytrade", _sf._usdjpy_cfg(), _sf._vix_sell_sig(), "15m", _sf.INST)

    assert audits and audits[-1]["block_reason"] == "shadow_tracking(session_filter_out)"
    assert promo_block_cause_from_audit(audits[-1]["block_reason"]) == "session_filter"
    rows = _rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert f"{_PROMO_BLOCK_REASON_TAG} session_filter" in _row_reasons(rows[0]), _row_reasons(rows[0])
    assert any("[PROMO_BLOCK] " in m and "cause=session_filter" in m for m in logs), logs


# ═══════════════════════════════════════════════════════════════════════
# 4. `_UNIVERSAL_SENTINEL` の shadow bypass → row reasons に `[SHADOW_BYPASS] <gate>`
# ═══════════════════════════════════════════════════════════════════════


def test_sentinel_recent_emit_bypass_persists_marker(tmp_path, monkeypatch):
    fake = _fake_bridge(strategy_mode="off")
    _promote_synthetic_elite(monkeypatch)
    _sentinelize_elite(monkeypatch)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_oanda", fake)
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: 5.0)
    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    rows = _rows(trader)
    assert rows and len(rows) == 1 and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] recent_emit bypass:" in m for m in logs), logs
    assert f"{_SHADOW_BYPASS_REASON_TAG} recent_emit" in _row_reasons(rows[0]), _row_reasons(rows[0])
    assert not fake.open_trade.called


def test_sentinel_velocity_down_bypass_persists_marker(tmp_path, monkeypatch):
    fake = _fake_bridge(strategy_mode="off")
    _promote_synthetic_elite(monkeypatch)
    _sentinelize_elite(monkeypatch)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_oanda", fake)
    # 5 分前 1.2020 → current 1.2000 = −20pip (daytrade 窓 30 分 / 閾値 15pip 超) vs BUY
    trader._price_history["EUR_USD"] = [
        (_LondonDatetime.now(timezone.utc) - timedelta(minutes=5), 1.2020),
    ]
    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    rows = _rows(trader)
    assert rows and len(rows) == 1 and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] velocity_down bypass:" in m for m in logs), logs
    assert f"{_SHADOW_BYPASS_REASON_TAG} velocity_down" in _row_reasons(rows[0])


def test_sentinel_row_without_bypass_has_no_marker(tmp_path, monkeypatch):
    """恒真でない側: bypass gate を踏まない sentinel row には marker が付かない。"""
    fake = _fake_bridge(strategy_mode="off")
    trader, logs = _run(tmp_path, monkeypatch, fake=fake, sentinel=True)
    rows = _rows(trader)
    assert rows and len(rows) == 1
    assert not any("[SHADOW] " in m and "bypass:" in m for m in logs), logs
    assert not any(r.startswith(_SHADOW_BYPASS_REASON_TAG) for r in _row_reasons(rows[0]))


def test_symmetric_non_sentinel_recent_emit_still_hard_blocks(tmp_path, monkeypatch):
    """対称側: `_is_shadow_eligible_full` 偽の戦略は従来どおり `_block(recent_emit(...))`
    で row を作らない — marker 追加が母集団 (行数) を変えないことの pin。"""
    fake = _fake_bridge(accept=True)
    _promote_synthetic_elite(monkeypatch)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_oanda", fake)
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: 5.0)
    blocked = []
    monkeypatch.setattr(
        trader, "_record_entry_block",
        lambda mode, et, inst, reason, *a, **k: blocked.append(reason),
    )
    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")

    assert _rows(trader) == []
    assert any(r.startswith("recent_emit(") for r in blocked), blocked
    assert not fake.open_trade.called


def test_shadow_bypass_marker_sites_cover_every_bypass_log():
    """スコープ pin: `_tick_entry` 内の `[SHADOW] … → shadow` bypass ログ (relax /
    edge-cell / wg 固有 cause / MTF downgrade / preserve pin を除く) と同数の
    marker append がある。増減はどちらも母集団の帰属面が変わった合図。"""
    src = textwrap.dedent(inspect.getsource(DemoTrader._tick_entry))
    appends = re.findall(r"_shadow_bypass_gates\.append\(", src)
    assert len(appends) == 23, len(appends)
    for gate in (
        "max_per_mode_pair", "max_open", "session_hours", "regime_range_dt_tf",
        "regime_trend_bull_dt_tf", "gbp_asia_flash_crash", "recent_emit",
        "session_pair(EUR_GBP)", "session_pair(EUR_USD_Tokyo)",
        "session_pair(EUR_USD_Late_NY)", "alpha_scan(EUR_USD_SELL)",
        "alpha_scan(RANGE_SELL)", "alpha_scan(TREND_BULL_BUY)", "alpha_scan(H11_EUR_USD)",
        "alpha_scan(H13_USD_JPY)", "alpha_scan(H16-20_USD_JPY)", "alpha_scan(BUY_TREND_BEAR)",
        "alpha_scan(H7-8_EUR_USD)", "regime_guardrail", "spread_guard", "spike",
        "velocity_up", "velocity_down",
    ):
        assert f'_shadow_bypass_gates.append("{gate}' in src, gate


# ═══════════════════════════════════════════════════════════════════════
# 5. order-bar 予約後 terminal block の最初の理由を 1 回だけ永続
# ═══════════════════════════════════════════════════════════════════════

_BAR_TS = "2026-05-28T11:45:00+00:00"


def _counts(trader):
    return query_block_counts(trader._db._path, days=7, strategy=ELITE)["per_strategy_counts"]


def _first_block_keys(counts):
    return {k: v for k, v in counts.items() if ORDER_BAR_FIRST_BLOCK_REASON_PREFIX in k}


def test_post_reservation_first_block_persisted_once_and_surfaced_on_dedup(tmp_path, monkeypatch):
    fake = _fake_bridge(accept=True)
    _promote_synthetic_elite(monkeypatch)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    assert init_block_table(trader._db._path)
    monkeypatch.setattr(trader, "_oanda", fake)
    # 予約 (order-bar) の直後にある recent_emit を非 sentinel で踏む = 予約後 terminal block
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: 5.0)

    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(bar_ts=_BAR_TS), "15m", "EUR_USD")
    counts = _counts(trader)
    assert counts.get(f"{ELITE}:recent_emit") == 1, counts
    first = _first_block_keys(counts)
    assert first == {f"{ELITE}:{ORDER_BAR_FIRST_BLOCK_REASON_PREFIX}recent_emit": 1}, counts
    assert any("[ORDER_BAR_DEDUP] first terminal block after reservation" in m
               and "recent_emit(" in m for m in logs), logs

    # 同じ closed bar の次 tick: dedup で固定されるが、最初の理由が読める
    logs.clear()
    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(bar_ts=_BAR_TS), "15m", "EUR_USD")
    counts = _counts(trader)
    assert counts.get(f"{ELITE}:order_bar_dedup") == 1, counts
    assert counts.get(f"{ELITE}:recent_emit") == 1, "dedup tick must not re-evaluate the gate"
    assert _first_block_keys(counts) == {
        f"{ELITE}:{ORDER_BAR_FIRST_BLOCK_REASON_PREFIX}recent_emit": 1
    }, "first block is persisted exactly once per reservation"
    assert any("[ORDER_BAR_DEDUP] blocked" in m and "first_block=recent_emit" in m for m in logs), logs
    assert _rows(trader) == []


def test_nonterminal_session_filter_downgrade_is_not_recorded_as_first_block(tmp_path, monkeypatch):
    """PR #293 review P2 (4078430621): `_block("session_filter_live_downgrade")` は意図的に
    **非終端** (row は作られ shadow 化される)。予約 key があってもこれを
    `order_bar_dedup_first:*` として記録してはならない (成功した shadow 降格を「最初の
    terminal block」として metric を汚染する)。counter 本体 (`session_filter_live_downgrade`)
    は従来どおり増える。"""
    import tests.test_session_filter_promotion_guard as _sf
    from edge_cell_test_helpers import make_trader as _make_sf_trader

    cell = (_sf.VIX, _sf.INST)
    monkeypatch.setattr(demo_trader_mod, "DemoTrader", DemoTrader)
    monkeypatch.setattr(
        DemoTrader, "_PAIR_PROMOTED", frozenset(set(DemoTrader._PAIR_PROMOTED) | {cell}))
    monkeypatch.setattr(
        DemoTrader, "_PAIR_DEMOTED", frozenset(t for t in DemoTrader._PAIR_DEMOTED if t != cell))
    monkeypatch.setattr(
        DemoTrader, "_PAIR_SESSION_FILTER", {**DemoTrader._PAIR_SESSION_FILTER, cell: {"Overlap"}})
    trader, logs = _make_sf_trader(tmp_path, monkeypatch, hour=_sf.HOUR_OUT)
    assert init_block_table(trader._db._path)
    sig = _sf._vix_sell_sig()
    sig["_closed_bar_ts"] = _BAR_TS  # order-bar 予約を成立させる

    trader._tick_entry("daytrade", _sf._usdjpy_cfg(), sig, "15m", _sf.INST)

    rows = _rows(trader)
    assert rows and rows[0]["is_shadow"] == 1, "non-terminal downgrade must still create the row"
    counts = query_block_counts(trader._db._path, days=7, strategy=_sf.VIX)["per_strategy_counts"]
    assert counts.get(f"{_sf.VIX}:session_filter_live_downgrade") == 1, counts
    assert _first_block_keys(counts) == {}, counts
    assert not any("first terminal block" in m for m in logs), [m for m in logs if "ORDER_BAR" in m]


def test_pre_reservation_block_records_no_first_block(tmp_path, monkeypatch):
    """対称側: 予約前 blocker (conf<threshold) は次 tick で再評価されるので記録しない。"""
    fake = _fake_bridge(accept=True)
    _promote_synthetic_elite(monkeypatch)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    assert init_block_table(trader._db._path)
    monkeypatch.setattr(trader, "_oanda", fake)

    trader._tick_entry(
        "daytrade", _cfg("EUR_USD"), _sig(confidence=1, bar_ts=_BAR_TS), "15m", "EUR_USD",
    )
    counts = _counts(trader)
    assert any(k.startswith(f"{ELITE}:conf<") for k in counts), counts
    assert _first_block_keys(counts) == {}, counts
    assert not any("first terminal block" in m for m in logs)


def test_block_without_bar_ts_records_no_first_block(tmp_path, monkeypatch):
    """対称側: bar_ts が無い sig は予約されない → 予約後 block ではないので記録しない。"""
    fake = _fake_bridge(accept=True)
    _promote_synthetic_elite(monkeypatch)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    assert init_block_table(trader._db._path)
    monkeypatch.setattr(trader, "_oanda", fake)
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: 5.0)

    trader._tick_entry("daytrade", _cfg("EUR_USD"), _sig(), "15m", "EUR_USD")
    counts = _counts(trader)
    assert counts.get(f"{ELITE}:recent_emit") == 1, counts
    assert _first_block_keys(counts) == {}, counts


# ═══════════════════════════════════════════════════════════════════════
# 6. shadow_only 母集団 (pre-reg LOCK) の行数・選択が変わらないこと
#    (marker は reasons への append のみ — 選択子 is_shadow=1 ∧ oanda_trade_id 空 ∧ mode に触れない)
# ═══════════════════════════════════════════════════════════════════════

from modules.demo_trader import MODE_CONFIG  # noqa: E402
import tests.test_rnb_shadow_only_downstream_relax as _rnb  # noqa: E402


def test_rnb_relax_row_population_unchanged_and_no_new_markers(tmp_path, monkeypatch):
    """rnb_usdjpy (shadow_only) の relax 行: 1 行 / is_shadow=1 / oanda_trade_id 空 /
    `[SHADOW_RELAX] velocity_down` は従来どおり。rnb は `_is_shadow_eligible_full` 偽
    なので `[SHADOW_BYPASS]` は付かず、shadow_only mode は `[PROMO_BLOCK]` 対象外。"""
    _rnb._patch_common(monkeypatch)
    trader, bridge, logs, blocked = _rnb._make_trader(tmp_path, monkeypatch)
    _rnb._seed_velocity_down(trader, "USD_JPY", 150.100, 5)
    _rnb._tick_rnb(trader)

    rows = _rows(trader)
    assert len(rows) == 1 and rows[0]["is_shadow"] == 1 and not (rows[0]["oanda_trade_id"] or "")
    reasons = _row_reasons(rows[0])
    assert "[SHADOW_RELAX] velocity_down" in reasons, reasons
    assert not any(r.startswith(_SHADOW_BYPASS_REASON_TAG) for r in reasons), reasons
    assert not any(r.startswith(_PROMO_BLOCK_REASON_TAG) for r in reasons), reasons
    assert bridge.sent == []


def test_daytrade_audjpy_shadow_only_row_excluded_from_promo_marker(tmp_path, monkeypatch):
    """daytrade_audjpy (shadow_only、WS3 stage-2 母集団) で strategy mode が off でも
    row は構造的 shadow のまま 1 行、`[PROMO_BLOCK]` は付かず audit も素の
    shadow_tracking — shadow_only の帰属を promo cause に書き換えない。"""
    _rnb._patch_common(monkeypatch)
    trader, bridge, logs, blocked = _rnb._make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(bridge, "get_strategy_mode", lambda _et: "off")
    assert MODE_CONFIG["daytrade_audjpy"]["shadow_only"] is True
    trader._tick_entry(
        "daytrade_audjpy", MODE_CONFIG["daytrade_audjpy"], _rnb._audjpy_sig(), "15m", "AUD_JPY",
    )

    rows = _rows(trader)
    assert len(rows) == 1 and rows[0]["is_shadow"] == 1 and not (rows[0]["oanda_trade_id"] or "")
    reasons = _row_reasons(rows[0])
    assert not any(r.startswith(_PROMO_BLOCK_REASON_TAG) for r in reasons), reasons
    assert not any(r.startswith(_SHADOW_BYPASS_REASON_TAG) for r in reasons), reasons
    skipped = [a for a in bridge.audits if a.get("bridge_status") == "skipped"]
    assert skipped and skipped[0]["block_reason"] == "shadow_tracking", skipped
    assert not any("[PROMO_BLOCK]" in m for m in logs), [m for m in logs if "PROMO" in m]
    assert bridge.sent == []
