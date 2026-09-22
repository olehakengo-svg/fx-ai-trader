"""SL replacement storm guard — OandaBridge.modify_sl / modify_sl_sync (rule:R3, 2026-09-22).

Fixture = storm 4 (#859468 kalman_d7, 2026-09-11) の実測形状:
  family B: SL 目標が 0.001 (1/10 pip) 刻みで振動 (154.349⇄154.350) — 等値では止まらない
  family A: 同一価格の再送 (carry_dip #837978 4,791 回 / #847578 5,936 回)
  単調性違反: BUY 建玉で 154.350→154.270 (8 pip 不利側)、#893161 で 1.2 pip 不利側→同秒自己約定

契約 (tests が pin するもの):
  (a) enforce で各 guard 単独が storm を 1〜数回で止める
  (b) CF: 各 guard を個別に kill (monkeypatch) すると storm fixture が素通りする
      = (a) の assertion は guard の存在に依存している
  (c) CF: 検知器 (_storm_record) を kill するとカウンタが動かない
  (d) 有利側の正当な trail (≥1 pip 単調) は全て通る — 偽陽性ゼロ
  既定 (env 未設定) = 検知のみ: 送信は止めず、カウンタ + WARN だけ動く
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from modules.oanda_bridge import OandaBridge, _storm_pip_size

DEMO = "demo-storm-1"
OANDA_ID = "859468"
N_STORM = 400  # 実 storm は 16,837 — test はスケール縮小、形状は同じ


class _FakeClient:
    """modify_trade を記録して成功を返す。"""

    def __init__(self):
        self.calls: list[tuple[str, float]] = []
        self.configured = True

    def modify_trade(self, oanda_id, stop_loss=None, instrument=None, **kw):
        self.calls.append((oanda_id, stop_loss))
        return True, {"ok": True}


def _bridge(monkeypatch, *, enforce: bool, direction: str = "BUY",
            open_sl: float = 154.115, db=None, **env) -> tuple[OandaBridge, _FakeClient]:
    monkeypatch.setenv("OANDA_LIVE", "true")
    monkeypatch.setenv("STORM_GUARD_ENFORCE", "1" if enforce else "")
    for k in ("STORM_GUARD_DEADBAND_PIPS", "STORM_GUARD_MAX_TX_PER_HOUR",
              "STORM_GUARD_MAX_TX_PER_DAY", "STORM_GUARD_ALLOW_SL_LOOSEN"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, str(v))
    b = OandaBridge(db=db)
    fake = _FakeClient()
    b._client = fake
    # fire-and-forget を inline 化 (modify_sl 経路の決定論化)
    monkeypatch.setattr(b, "_fire", lambda fn, *a, **kw: fn(*a, **kw))
    b.set_trade_mapping(DEMO, OANDA_ID)
    if direction is not None:
        b._storm_register_trade(DEMO, direction, open_sl)
    return b, fake


# ── storm fixtures ─────────────────────────────────────────────────────────

def storm_oscillation(n: int = N_STORM) -> list[float]:
    """family B: 154.349 ⇄ 154.350 (0.1 pip) — storm 4 実測形状。"""
    return [154.349 if i % 2 == 0 else 154.350 for i in range(n)]


def storm_same_price(n: int = N_STORM) -> list[float]:
    """family A: 同一価格再送 (#837978 / #847578)。"""
    return [153.969] * n


def storm_loosen_buy(n: int = N_STORM) -> list[float]:
    """単調性違反: BUY 建玉で SL を 1 pip ずつ下げ続ける (154.350→...)。"""
    return [round(154.350 - 0.01 * i, 3) for i in range(n)]


def legit_trail_buy(n: int = 10) -> list[float]:
    """正当な trail: BUY で 2 pip ずつ有利側 (上) へ。"""
    return [round(154.200 + 0.02 * i, 3) for i in range(n)]


def _run(b: OandaBridge, seq, sync=True) -> list[bool]:
    out = []
    for sl in seq:
        if sync:
            out.append(b.modify_sl_sync(DEMO, sl, instrument="USD_JPY"))
        else:
            b.modify_sl(DEMO, sl, instrument="USD_JPY")
            out.append(None)
    return out


def _kill_all_but(monkeypatch, keep: str):
    """keep 以外の 3 guard を無効化して単独評価にする。"""
    names = {"breaker": "_storm_check_breaker", "idempotent": "_storm_check_idempotent",
             "monotonic": "_storm_check_monotonic", "deadband": "_storm_check_deadband"}
    for k, m in names.items():
        if k != keep:
            monkeypatch.setattr(OandaBridge, m, lambda self, *a, **kw: None)


# ── pip 規約 ───────────────────────────────────────────────────────────────

def test_pip_size_convention_matches_demo_trader():
    assert _storm_pip_size("USD_JPY") == 0.01
    assert _storm_pip_size("XAU_USD") == 0.01
    assert _storm_pip_size("EUR_USD") == 0.0001
    assert _storm_pip_size("EUR_GBP") == 0.0001


# ── 既定 = 検知のみ ────────────────────────────────────────────────────────

def test_default_is_detect_only_storm_passes_but_is_counted(monkeypatch, caplog):
    b, fake = _bridge(monkeypatch, enforce=False)
    assert b._storm_enforce is False
    with caplog.at_level(logging.WARNING):
        _run(b, storm_oscillation())
    # 送信は止めない (既定は検知のみ)
    assert len(fake.calls) == N_STORM
    st = b.get_storm_guard_status()
    assert st["enforce"] is False
    # 1 本目は baseline から 23.4 pip 移動 = 正当。検知のみモードでは送信が続くので
    # last_sl が毎回更新され、0.1 pip 振動は 上=deadband / 下=monotonic (BUY) に交互分類される。
    # 50 送信目で breaker が trip し、以後は breaker が先勝ち (順序 = breaker → 冪等 → 単調性 → dead-band)
    d = st["totals"]["detected"]
    assert d["deadband"] + d["monotonic"] == 49
    assert d["breaker"] == N_STORM - 50
    assert st["totals"]["breaker_trips"] == 1
    assert sum(st["totals"]["skipped"].values()) == 0
    assert st["totals"]["sent"] == N_STORM
    # WARN が出ている (BREAKER TRIPPED は 1 回だけ)
    trips = [r for r in caplog.records if "BREAKER TRIPPED" in r.getMessage()]
    assert len(trips) == 1
    detects = [r for r in caplog.records if "DETECT(would_skip)" in r.getMessage()]
    assert 1 <= len(detects) < N_STORM  # 抑制付き (first 3 + every 100th)


def test_default_detect_only_still_counts_in_evaluated_and_status(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=False)
    _run(b, storm_same_price(20))
    st = b.status["storm_guard"]
    assert st["totals"]["evaluated"] == 20
    assert st["totals"]["detected"]["idempotent"] == 19
    assert st["trades"][DEMO]["counts"]["idempotent"] == 19


# ── (a) enforce: 各 guard 単独で storm が止まる ────────────────────────────

def test_a_deadband_alone_stops_oscillation_storm(monkeypatch):
    _kill_all_but(monkeypatch, "deadband")
    b, fake = _bridge(monkeypatch, enforce=True)
    rets = _run(b, storm_oscillation())
    assert len(fake.calls) == 1              # 154.349 のみ送信、以後 0.1 pip は全 skip
    assert rets[0] is True and all(r is False for r in rets[1:])  # deadband skip = 未変更
    assert b.get_storm_guard_status()["totals"]["skipped"]["deadband"] == N_STORM - 1


def test_a_idempotent_alone_stops_same_price_storm(monkeypatch):
    _kill_all_but(monkeypatch, "idempotent")
    b, fake = _bridge(monkeypatch, enforce=True)
    rets = _run(b, storm_same_price())
    assert len(fake.calls) == 1
    # 冪等 skip は「broker は既にその SL」= True を返す (caller の rollback を誘発しない)
    assert all(r is True for r in rets)
    assert b.get_storm_guard_status()["totals"]["skipped"]["idempotent"] == N_STORM - 1


def test_a_monotonic_alone_rejects_buy_sl_loosening(monkeypatch):
    _kill_all_but(monkeypatch, "monotonic")
    b, fake = _bridge(monkeypatch, enforce=True)
    rets = _run(b, storm_loosen_buy())
    assert len(fake.calls) == 1              # 154.350 (baseline 154.115 から上) のみ
    assert rets[0] is True and all(r is False for r in rets[1:])
    assert b.get_storm_guard_status()["totals"]["skipped"]["monotonic"] == N_STORM - 1


def test_a_monotonic_sell_symmetric(monkeypatch):
    _kill_all_but(monkeypatch, "monotonic")
    b, fake = _bridge(monkeypatch, enforce=True, direction="SELL", open_sl=154.500)
    # SELL: SL↓ は有利 (通す)、SL↑ は違反 (reject)
    assert b.modify_sl_sync(DEMO, 154.400, instrument="USD_JPY") is True
    assert b.modify_sl_sync(DEMO, 154.450, instrument="USD_JPY") is False
    assert len(fake.calls) == 1


def test_a_breaker_alone_caps_hourly_tx(monkeypatch, caplog):
    _kill_all_but(monkeypatch, "breaker")
    b, fake = _bridge(monkeypatch, enforce=True, STORM_GUARD_MAX_TX_PER_HOUR=50)
    with caplog.at_level(logging.WARNING):
        rets = _run(b, storm_oscillation())
    assert len(fake.calls) == 50             # 閾値ちょうどで停止
    assert all(rets[:50]) and not any(rets[50:])
    st = b.get_storm_guard_status()
    assert st["trades"][DEMO]["tripped"] is True
    assert st["totals"]["breaker_trips"] == 1
    assert st["totals"]["skipped"]["breaker"] == N_STORM - 50
    assert len([r for r in caplog.records if "BREAKER TRIPPED" in r.getMessage()]) == 1


def test_a_breaker_daily_cap_and_disable_with_zero(monkeypatch):
    _kill_all_but(monkeypatch, "breaker")
    b, fake = _bridge(monkeypatch, enforce=True,
                      STORM_GUARD_MAX_TX_PER_HOUR=0, STORM_GUARD_MAX_TX_PER_DAY=30)
    _run(b, storm_oscillation(100))
    assert len(fake.calls) == 30
    b2, fake2 = _bridge(monkeypatch, enforce=True,
                        STORM_GUARD_MAX_TX_PER_HOUR=0, STORM_GUARD_MAX_TX_PER_DAY=0)
    _run(b2, storm_oscillation(100))
    assert len(fake2.calls) == 100           # 0 = breaker 無効


def test_a_all_four_enabled_stops_storm4_shape(monkeypatch):
    """storm 4 の合成形状: 振動 + 途中で 8 pip 不利側 + 同一価格。全 guard 有効。"""
    b, fake = _bridge(monkeypatch, enforce=True)
    seq = storm_oscillation(100) + [154.270] * 50 + storm_same_price(50)
    _run(b, seq)
    # 154.349 (正当) のみ。enforce では last_sl が 154.349 に固定されるので
    # 154.350 = deadband (50) / 154.349 = idempotent (49)。154.270 は BUY で 7.9 pip 下 =
    # monotonic reject (50)、153.969 も reject (50)
    assert len(fake.calls) == 1
    st = b.get_storm_guard_status()
    assert st["totals"]["skipped"]["deadband"] == 50
    assert st["totals"]["skipped"]["idempotent"] == 49
    assert st["totals"]["skipped"]["monotonic"] == 100


def test_a_async_modify_sl_path_is_guarded_too(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True)
    _run(b, storm_oscillation(50), sync=False)
    assert len(fake.calls) == 1


# ── (b) CF pin: guard を個別に kill すると storm が素通りする ──────────────

def test_b_cf_kill_deadband_lets_oscillation_storm_through(monkeypatch):
    _kill_all_but(monkeypatch, "deadband")
    monkeypatch.setattr(OandaBridge, "_storm_check_deadband", lambda self, *a, **kw: None)
    b, fake = _bridge(monkeypatch, enforce=True)
    _run(b, storm_oscillation())
    assert len(fake.calls) == N_STORM        # ← guard 不在なら 400 回全部飛ぶ (= test_a_deadband が落ちる形)


def test_b_cf_kill_idempotent_lets_same_price_storm_through(monkeypatch):
    _kill_all_but(monkeypatch, "idempotent")
    monkeypatch.setattr(OandaBridge, "_storm_check_idempotent", lambda self, *a, **kw: None)
    b, fake = _bridge(monkeypatch, enforce=True)
    _run(b, storm_same_price())
    assert len(fake.calls) == N_STORM


def test_b_cf_kill_monotonic_lets_loosening_through(monkeypatch):
    _kill_all_but(monkeypatch, "monotonic")
    monkeypatch.setattr(OandaBridge, "_storm_check_monotonic", lambda self, *a, **kw: None)
    b, fake = _bridge(monkeypatch, enforce=True)
    _run(b, storm_loosen_buy())
    assert len(fake.calls) == N_STORM


def test_b_cf_kill_breaker_lets_storm_through(monkeypatch):
    _kill_all_but(monkeypatch, "breaker")
    monkeypatch.setattr(OandaBridge, "_storm_check_breaker", lambda self, *a, **kw: None)
    b, fake = _bridge(monkeypatch, enforce=True, STORM_GUARD_MAX_TX_PER_HOUR=50)
    _run(b, storm_oscillation())
    assert len(fake.calls) == N_STORM


def test_b_cf_enforce_flag_off_is_the_only_difference(monkeypatch):
    """同一 fixture で enforce のみ反転: 1 送信 ⇄ 400 送信。"""
    b_on, fake_on = _bridge(monkeypatch, enforce=True)
    _run(b_on, storm_oscillation())
    b_off, fake_off = _bridge(monkeypatch, enforce=False)
    _run(b_off, storm_oscillation())
    assert (len(fake_on.calls), len(fake_off.calls)) == (1, N_STORM)


# ── (c) CF pin: 検知器 kill でカウンタが死ぬ ───────────────────────────────

def test_c_detector_counts_in_detect_only_mode(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=False)
    _run(b, storm_oscillation(50))
    t = b.get_storm_guard_status()["totals"]
    # 検知のみ = 送信継続 → 振動は deadband(上) / monotonic(下) に交互分類、合計 49
    assert t["detected"]["deadband"] + t["detected"]["monotonic"] == 49
    assert t["detected"]["deadband"] == 25 and t["detected"]["monotonic"] == 24


def test_c_cf_kill_detector_zeroes_counters(monkeypatch):
    monkeypatch.setattr(OandaBridge, "_storm_record", lambda self, *a, **kw: None)
    b, fake = _bridge(monkeypatch, enforce=False)
    _run(b, storm_oscillation(50))
    t = b.get_storm_guard_status()["totals"]
    assert sum(t["detected"].values()) == 0  # ← 検知器不在 = test_c_detector_counts が落ちる形
    assert len(fake.calls) == 50             # 送信自体は変わらない (検知器は observability のみ)


# ── (d) 偽陽性ゼロ: 正当な trail は通る ────────────────────────────────────

def test_d_legit_buy_trail_all_pass_under_enforce(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True)
    rets = _run(b, legit_trail_buy(10))
    assert all(rets) and len(fake.calls) == 10
    t = b.get_storm_guard_status()["totals"]
    assert sum(t["skipped"].values()) == 0 and sum(t["detected"].values()) == 0


def test_d_legit_sell_trail_all_pass_under_enforce(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True, direction="SELL", open_sl=154.900)
    seq = [round(154.900 - 0.015 * (i + 1), 3) for i in range(10)]  # 1.5 pip ずつ下 (有利)
    rets = _run(b, seq)
    assert all(rets) and len(fake.calls) == 10


def test_d_exactly_one_pip_passes_deadband_boundary(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=154.200)
    assert b.modify_sl_sync(DEMO, 154.210, instrument="USD_JPY") is True   # = 1.0 pip → 通す
    assert b.modify_sl_sync(DEMO, 154.219, instrument="USD_JPY") is False  # 0.9 pip → skip
    assert b.modify_sl_sync(DEMO, 154.220, instrument="USD_JPY") is True   # 1.0 pip from 154.210
    assert len(fake.calls) == 2


def test_d_non_jpy_pair_uses_0_0001_pip(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=1.08000)
    assert b.modify_sl_sync(DEMO, 1.08010, instrument="EUR_USD") is True   # 1.0 pip
    assert b.modify_sl_sync(DEMO, 1.08015, instrument="EUR_USD") is False  # 0.5 pip
    assert len(fake.calls) == 1


def test_d_be_move_after_open_passes(monkeypatch):
    """典型 BE: open SL 153.750 → entry+spread 153.930 (18 pip 有利側) は通る。"""
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=153.750)
    assert b.modify_sl_sync(DEMO, 153.930, instrument="USD_JPY") is True
    assert len(fake.calls) == 1


# ── 方向不明 / 再起動後 seed / opt-in ──────────────────────────────────────

def test_unknown_direction_skips_monotonic_but_counts(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True, direction=None)  # baseline なし (restore 相当、db なし)
    # 1 本目: baseline なし → 通す (baseline 確立)
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is True
    # 2 本目: 方向不明なので単調性は判定不能 → 1 pip 以上の移動は通す (fail-open) + unknown_direction カウント
    assert b.modify_sl_sync(DEMO, 154.300, instrument="USD_JPY") is True
    assert b.get_storm_guard_status()["totals"]["unknown_direction"] == 1
    assert len(fake.calls) == 2


def test_restore_path_seeds_direction_and_sl_from_db(monkeypatch):
    db = MagicMock()
    db.get_open_trades.return_value = [
        {"id": DEMO, "direction": "BUY", "sl": 154.115, "oanda_trade_id": OANDA_ID},
    ]
    b, fake = _bridge(monkeypatch, enforce=True, direction=None, db=db)
    # baseline は DB から seed → 154.100 は BUY で 1.5 pip 下 = monotonic reject
    assert b.modify_sl_sync(DEMO, 154.100, instrument="USD_JPY") is False
    assert len(fake.calls) == 0
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert st["direction"] == "BUY" and st["last_sl"] == 154.115


def test_allow_loosen_env_opt_in_disables_monotonic_reject_but_counts(monkeypatch):
    _kill_all_but(monkeypatch, "monotonic")
    b, fake = _bridge(monkeypatch, enforce=True, STORM_GUARD_ALLOW_SL_LOOSEN=1)
    _run(b, storm_loosen_buy(10))
    assert len(fake.calls) == 10
    t = b.get_storm_guard_status()["totals"]
    assert t["detected"]["monotonic"] == 9 and t["skipped"]["monotonic"] == 0


def test_close_forgets_state_and_state_is_per_trade(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True)
    b._storm_register_trade("other", "SELL", 150.000)
    _run(b, storm_oscillation(10))
    assert DEMO in b.get_storm_guard_status()["trades"]
    b._storm_forget(DEMO)
    assert DEMO not in b.get_storm_guard_status()["trades"]
    assert "other" in b.get_storm_guard_status()["trades"]


def test_inactive_bridge_returns_false_without_touching_guard(monkeypatch):
    monkeypatch.setenv("OANDA_LIVE", "")
    b = OandaBridge(db=None)
    assert b.modify_sl_sync(DEMO, 154.0) is False
    assert b.get_storm_guard_status()["totals"]["evaluated"] == 0
