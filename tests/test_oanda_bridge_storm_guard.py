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
  (e) 再起動後 seed: baseline は broker の現 SL (DB sl は stale) / DB 照合は trade_id
      (PR #287 review P1 ×2、CF pin 付き)
  (f) fire-and-forget 競合: 予約は gate 内 (worker 完了前の同時到達が同じ古い baseline
      を見ない)、broker 失敗で rollback (PR #287 review P2、CF pin 付き)
  (g) 未確認予約 ≠ 確認済み: confirmed_sl (broker 受理) と pending (飛行中) を分離。
      同値一致が pending なら modify_sl_sync は worker の結果を待つ / 連鎖失敗後の
      baseline は確認済み値へ戻る (PR #287 review 2 巡目 P1/P2、CF pin 付き)
  (h) 送信直列化: trade ごとに pending[0] だけが broker へ送れる (前の要求が決着するまで
      次を送らない) — 「B 確認済み ∧ A pending」の窓も broker 側の発行順逆転も生じない
      (PR #287 review 3 巡目 P1、CF pin 付き)
  (i) 直列化の順番待ち・timeout drop は enforce のみ — 検知のみでは待たず落とさず
      detected.serialize に数えるだけ (PR #287 review 4 巡目 P2、CF pin 付き)
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
    """modify_trade を記録して成功を返す。open_trades を与えると broker seed に応答する。"""

    def __init__(self, open_trades: list | None = None):
        self.calls: list[tuple[str, float]] = []
        self.configured = True
        self.open_trades = open_trades        # None = broker 到達不能 (ok=False)
        self.fail_modify = False              # True = modify_trade が (False, ...) を返す
        self.open_trades_calls = 0

    def modify_trade(self, oanda_id, stop_loss=None, instrument=None, **kw):
        self.calls.append((oanda_id, stop_loss))
        if self.fail_modify:
            return False, {"errorMessage": "simulated"}
        return True, {"ok": True}

    def get_open_trades(self):
        self.open_trades_calls += 1
        if self.open_trades is None:
            return False, {"error": "simulated broker unavailable"}
        return True, {"trades": list(self.open_trades)}


def _broker_trade(units: str = "1000", sl: str = "154.350") -> dict:
    """OANDA v20 openTrades 行の最小形 (demo_db._parse_oanda_trade と同じ key)。"""
    return {"id": OANDA_ID, "instrument": "USD_JPY", "currentUnits": units,
            "initialUnits": units, "stopLossOrder": {"price": sl}}


def _db_row(direction: str = "BUY", sl: float = 154.115) -> dict:
    """demo_trades 行の実形状: 識別子は `trade_id`、`id` は INTEGER PK (別物)。"""
    return {"id": 17, "trade_id": DEMO, "direction": direction, "sl": sl,
            "oanda_trade_id": OANDA_ID, "status": "OPEN"}


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


# ── 再起動後 seed (PR #287 review P1 ×2) ──────────────────────────────────
# P1-a: demo_trades の識別子は `trade_id` (`id` は INTEGER PK) — 旧 code は `id` を
#       見ていて永久に seed されず、単調性が全 restored trade で fail-open だった。
# P1-b: demo_trades.sl は LIVE 経路で trail 後も更新されない (demo_trader L3188–3199
#       LIVE 分岐は update_sl_tp を呼ばない) = stale。broker 154.350 / DB 154.115 で
#       154.270 (BUY, broker から 8 pip 不利側) を DB 基準で「有利側」と誤判定して
#       送る = guard が守るべき形状の素通し。baseline は broker から取る。

def test_restore_path_seeds_baseline_from_broker_not_stale_db_sl(monkeypatch):
    db = MagicMock()
    db.get_open_trades.return_value = [_db_row("BUY", 154.115)]   # stale (open 時の SL)
    b, fake = _bridge(monkeypatch, enforce=True, direction=None, db=db)
    fake.open_trades = [_broker_trade("1000", "154.350")]         # broker の現 SL
    # review の実例: 154.270 は DB 基準 +15.5 pip (有利) だが broker 基準 −8 pip (不利)
    assert b.modify_sl_sync(DEMO, 154.270, instrument="USD_JPY") is False
    assert len(fake.calls) == 0
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert st["direction"] == "BUY" and st["last_sl"] == 154.350
    assert st["seed_source"] == "broker"
    assert b.get_storm_guard_status()["totals"]["skipped"]["monotonic"] == 1
    # 正当な有利側 (broker 基準 +1.5 pip) は通る
    assert b.modify_sl_sync(DEMO, 154.365, instrument="USD_JPY") is True


def test_restore_path_cf_seeding_stale_db_sl_lets_loosening_through(monkeypatch):
    """CF pin: 旧挙動 (DB sl を baseline に採用) を再現すると review の 8 pip 緩めが通る
    = 上の assertion は broker seed の存在に依存している。"""
    def _old_seed(self, demo_trade_id, st):
        st["direction"], st["last_sl"], st["seeded"] = "BUY", 154.115, True
        st["seed_source"] = "db_stale"
    monkeypatch.setattr(OandaBridge, "_storm_seed_restored", _old_seed)
    b, fake = _bridge(monkeypatch, enforce=True, direction=None, db=MagicMock())
    fake.open_trades = [_broker_trade("1000", "154.350")]
    assert b.modify_sl_sync(DEMO, 154.270, instrument="USD_JPY") is True   # ← 素通し (旧 bug の形)
    assert len(fake.calls) == 1


def test_restore_path_broker_unavailable_uses_db_direction_only_and_matches_trade_id(monkeypatch):
    """P1-a + P1-b fallback: broker 不達なら direction だけ DB (`trade_id` で照合) から。
    stale な DB sl は baseline に使わず、最初の成功送信が baseline になる (fail-open)。"""
    db = MagicMock()
    db.get_open_trades.return_value = [_db_row("BUY", 154.115)]
    b, fake = _bridge(monkeypatch, enforce=True, direction=None, db=db)
    assert fake.open_trades is None                                  # broker 不達
    # 1 本目: baseline なし → 通す (baseline 確立)。stale 154.115 とは比較しない
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is True
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert st["direction"] == "BUY" and st["last_sl"] == 154.350
    assert st["seed_source"] == "db_direction_only"
    # 2 本目: direction は分かるので単調性が効く
    assert b.modify_sl_sync(DEMO, 154.270, instrument="USD_JPY") is False
    assert len(fake.calls) == 1
    assert b.get_storm_guard_status()["totals"]["unknown_direction"] == 0


def test_restore_path_cf_db_row_keyed_only_by_id_never_seeds(monkeypatch):
    """CF pin (P1-a): 行が `trade_id` を持たず `id` だけなら照合できず direction 不明
    = 旧 code (`row.get("id")`) と同じ「永久 fail-open」の形が再現する。"""
    db = MagicMock()
    db.get_open_trades.return_value = [{"id": DEMO, "direction": "BUY", "sl": 154.115}]
    b, fake = _bridge(monkeypatch, enforce=True, direction=None, db=db)
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is True
    assert b.modify_sl_sync(DEMO, 154.270, instrument="USD_JPY") is True   # ← 単調性が効かない
    assert b.get_storm_guard_status()["totals"]["unknown_direction"] == 1
    assert b.get_storm_guard_status()["trades"][DEMO]["seed_source"] is None


def test_restore_path_broker_seed_happens_once_and_sell_direction_from_units(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True, direction=None, db=None)
    fake.open_trades = [_broker_trade("-1000", "154.900")]          # SELL
    assert b.modify_sl_sync(DEMO, 154.950, instrument="USD_JPY") is False   # SELL で SL↑ = reject
    assert b.modify_sl_sync(DEMO, 154.850, instrument="USD_JPY") is True    # SL↓ = 有利
    assert fake.open_trades_calls == 1                              # seed は 1 回だけ
    assert b.get_storm_guard_status()["trades"][DEMO]["direction"] == "SELL"


# ── fire-and-forget 競合 (PR #287 review P2) ─────────────────────────────
# worker 完了後に last_sl / sent_ts を更新する設計だと、worker 完了前に到達した
# N 件が同じ古い baseline を見て全部通る。予約 (reserve) は gate 内で行う。

def _deferred_fire(b, monkeypatch) -> list:
    """_fire を「積むだけ」にして、worker 完了前の同時到達を再現する。"""
    queue: list = []
    monkeypatch.setattr(b, "_fire", lambda fn, *a, **kw: queue.append(lambda: fn(*a, **kw)))
    return queue


def test_p2_async_burst_same_sl_is_reserved_before_worker_runs(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True)
    q = _deferred_fire(b, monkeypatch)
    for _ in range(5):
        b.modify_sl(DEMO, 154.350, instrument="USD_JPY")           # worker は 1 つも走っていない
    assert len(q) == 1                                              # 2 件目以降は予約済み baseline で冪等 skip
    for fn in q:
        fn()
    assert len(fake.calls) == 1
    assert b.get_storm_guard_status()["totals"]["skipped"]["idempotent"] == 4


def test_p2_async_burst_cannot_overshoot_breaker(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True, STORM_GUARD_MAX_TX_PER_HOUR=50)
    q = _deferred_fire(b, monkeypatch)
    for sl in legit_trail_buy(60):                                  # 全て正当 (2 pip 有利側)
        b.modify_sl(DEMO, sl, instrument="USD_JPY")
    assert len(q) == 50                                             # 予約段階で 50 に capped
    assert b.get_storm_guard_status()["totals"]["skipped"]["breaker"] == 10


def test_p2_cf_reserve_after_success_lets_burst_through(monkeypatch):
    """CF pin: 予約を「成功後更新」に戻す (last_sl を gate 内で触らない) と同一 SL 5 件が
    全部飛ぶ = 上の assertion は gate 内予約の存在に依存している。"""
    import threading as _th
    def _no_reserve(self, st, new_sl):                                # pending に積まない = baseline 不変
        st["seq"] += 1
        return {"seq": st["seq"], "new_sl": float(new_sl), "done": _th.Event(), "ok": None}
    monkeypatch.setattr(OandaBridge, "_storm_reserve", _no_reserve)
    b, fake = _bridge(monkeypatch, enforce=True)
    q = _deferred_fire(b, monkeypatch)
    for _ in range(5):
        b.modify_sl(DEMO, 154.350, instrument="USD_JPY")
    assert len(q) == 5                                              # ← 素通し (旧 bug の形)


def test_p2_rollback_on_broker_failure_restores_baseline_sync_and_async(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=154.115)
    fake.fail_modify = True
    # sync: 失敗 → False、last_sl は予約前へ戻る、要求は数える (breaker は要求数)
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is False
    st = b.get_storm_guard_status()
    assert st["trades"][DEMO]["last_sl"] == 154.115
    assert st["totals"]["failed"] == 1 and st["totals"]["sent"] == 1
    # 復旧後の同一 SL 再送は冪等 skip されない (broker は未変更なので再送が正しい)
    fake.fail_modify = False
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is True
    assert b.get_storm_guard_status()["trades"][DEMO]["last_sl"] == 154.350
    # async (inline _fire): 失敗で rollback、成功で据え置き
    fake.fail_modify = True
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")
    assert b.get_storm_guard_status()["trades"][DEMO]["last_sl"] == 154.350
    fake.fail_modify = False
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")
    assert b.get_storm_guard_status()["trades"][DEMO]["last_sl"] == 154.400
    assert b.get_storm_guard_status()["totals"]["failed"] == 2


def test_p2_rollback_does_not_clobber_newer_reservation(monkeypatch):
    """A (失敗) の rollback は、その後 B が baseline を進めていれば触らない。"""
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=154.115)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")               # A 予約
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")               # B 予約 (baseline 154.400)
    fake.fail_modify = True
    q[0]()                                                          # A 失敗 → rollback は no-op
    assert b.get_storm_guard_status()["trades"][DEMO]["last_sl"] == 154.400
    fake.fail_modify = False
    q[1]()
    assert b.get_storm_guard_status()["trades"][DEMO]["last_sl"] == 154.400


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


# ── 未確認予約 ≠ 確認済み (PR #287 review 2 巡目 P1 / P2) ───────────────
# P1-3: 飛行中 (未確認) の同値予約に対して modify_sl_sync が冪等 True を返すと、
#       pyramiding 経路が「元建玉は保護済み」と誤認して追加 exposure を開く。
#       → confirmed_sl (broker 受理済み) と pending (飛行中) を分離、同値一致が pending
#         なら worker の結果を待って返す。
# P2-2: A,B を予約して両方失敗すると、prev_sl 復元型 rollback は B の rollback で
#       未確認の A を baseline に残す。→ rollback は pending から外すだけで、baseline は
#       確認済み値に自然に戻る。

import threading as _threading


def _sync_in_thread(b, sl):
    box = {}
    def _run():
        box["ret"] = b.modify_sl_sync(DEMO, sl, instrument="USD_JPY")
    t = _threading.Thread(target=_run, daemon=True)
    t.start()
    return t, box


def test_p1_sync_idempotent_against_pending_waits_and_returns_worker_outcome(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")               # 飛行中 (未確認)
    assert b.get_storm_guard_status()["trades"][DEMO]["pending"] == [154.350]
    assert b.get_storm_guard_status()["trades"][DEMO]["confirmed_sl"] == 154.115
    # (1) worker が失敗する場合: sync は True を返してはいけない
    t, box = _sync_in_thread(b, 154.350)
    t.join(0.3)
    assert t.is_alive() and "ret" not in box                        # 待っている (即 True ではない)
    fake.fail_modify = True
    q.pop(0)()                                                      # A 失敗
    t.join(2.0)
    assert box["ret"] is False
    assert len(fake.calls) == 1                                     # sync 側は broker を叩かない
    # (2) worker が成功する場合: True
    fake.fail_modify = False
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")               # 再予約 (baseline は 154.115 に戻っている)
    assert len(q) == 1
    t2, box2 = _sync_in_thread(b, 154.350)
    t2.join(0.3)
    assert t2.is_alive()
    q.pop(0)()
    t2.join(2.0)
    assert box2["ret"] is True
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert st["confirmed_sl"] == 154.350 and st["pending"] == []
    assert b.get_storm_guard_status()["totals"]["skipped"]["idempotent"] == 2


def test_p1_sync_idempotent_against_confirmed_returns_true_immediately(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True)
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is True   # 確認済み
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is True   # 冪等 (確認済みに一致) → 即 True
    assert len(fake.calls) == 1


def test_p1_sync_pending_wait_timeout_returns_false(monkeypatch):
    monkeypatch.setattr(OandaBridge, "STORM_PENDING_WAIT_SEC", 0.1)
    b, fake = _bridge(monkeypatch, enforce=True)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is False  # worker 不応答 = 未確認
    assert len(q) == 1 and len(fake.calls) == 0


def test_p1_cf_treating_pending_as_confirmed_returns_true_before_failure(monkeypatch):
    """CF pin: 旧挙動 (`bool(sync_ret)` で即返し) だと worker 失敗前に True が返る。"""
    monkeypatch.setattr(OandaBridge, "_storm_sync_result",
                        lambda self, d, r: True if isinstance(r, dict) else bool(r))
    b, fake = _bridge(monkeypatch, enforce=True)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is True   # ← 未確認を True (旧 bug の形)
    fake.fail_modify = True
    q.pop(0)()
    assert b.get_storm_guard_status()["trades"][DEMO]["confirmed_sl"] == 154.115  # 実際は未保護


def test_p2_cascading_failures_restore_confirmed_baseline(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=154.115)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")               # A
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")               # B
    fake.fail_modify = True
    q.pop(0)()                                                      # A 失敗
    q.pop(0)()                                                      # B 失敗
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert st["pending"] == [] and st["confirmed_sl"] == 154.115 and st["last_sl"] == 154.115
    # 以後の正当な要求は誤って冪等/dead-band/単調性に分類されない
    fake.fail_modify = False
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is True
    assert fake.calls[-1] == (OANDA_ID, 154.350)
    assert b.get_storm_guard_status()["totals"]["failed"] == 2


def test_p2_cf_prev_sl_rollback_leaves_unconfirmed_baseline(monkeypatch):
    """CF pin: 旧挙動 (予約時 prev_sl を記録し rollback で復元) を再現すると、A,B 連鎖失敗後に
    未確認の A (154.350) が baseline に残り、正当な 154.350 が冪等 skip される。"""
    orig_reserve = OandaBridge._storm_reserve
    def _old_reserve(self, st, new_sl):
        prev = self._storm_baseline(st)
        tok = orig_reserve(self, st, new_sl)
        tok["prev_sl"] = prev
        return tok
    def _old_rollback(self, demo_trade_id, st, token):
        with self._storm_lock:
            if self._storm_baseline(st) == token["new_sl"]:
                st["confirmed_sl"] = token["prev_sl"]
            st["pending"].remove(token)
        token["ok"] = False
        token["done"].set()
    monkeypatch.setattr(OandaBridge, "_storm_reserve", _old_reserve)
    monkeypatch.setattr(OandaBridge, "_storm_rollback", _old_rollback)
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=154.115)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")
    fake.fail_modify = True
    q.pop(0)(); q.pop(0)()
    assert b.get_storm_guard_status()["trades"][DEMO]["confirmed_sl"] == 154.350   # ← 未確認値が残る
    fake.fail_modify = False
    assert b.modify_sl_sync(DEMO, 154.350, instrument="USD_JPY") is True           # 冪等 "成功" だが
    assert len(fake.calls) == 2                                                     # broker には届いていない (旧 bug の形)


# ── 送信直列化 (PR #287 review 3 巡目 P1) ────────────────────────────────
# A, B が重なって B が先に broker 確認されると、baseline は pending A を返し続け
# (A < X < B の BUY 要求が「A より tight」として送られ、確認済み B を緩める)、さらに
# broker 側で A が B の後に処理される発行順逆転も起きる。→ trade ごとに pending[0]
# だけが送れる (前の要求が決着するまで次を送らない)。

def _run_in_thread(fn):
    t = _threading.Thread(target=fn, daemon=True)
    t.start()
    return t


def test_serialization_b_worker_waits_until_a_settles(monkeypatch):
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=154.115)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")               # A (seq 1)
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")               # B (seq 2)
    tb = _run_in_thread(q[1])                                       # B の worker が先に走り出す
    tb.join(0.3)
    assert tb.is_alive() and fake.calls == []                       # B は A の決着を待っている
    q[0]()                                                          # A 決着 (成功)
    tb.join(2.0)
    assert not tb.is_alive()
    assert fake.calls == [(OANDA_ID, 154.350), (OANDA_ID, 154.400)]  # broker への到達順 = 発行順
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert st["confirmed_sl"] == 154.400 and st["pending"] == []


def test_serialization_no_window_where_confirmed_b_coexists_with_pending_a(monkeypatch):
    """review の形状: 「B 確認済み ∧ A pending」の窓で A<X<B の BUY 要求が通る。
    直列化下ではその窓が存在しない — X (154.380) は B 確認後に評価され monotonic reject。"""
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=154.115)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")               # A
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")               # B
    tb = _run_in_thread(q[1]); tb.join(0.2)
    # この時点 (A 未決着) の X は baseline=B(pending) 基準で monotonic reject — 送信されない
    assert b.modify_sl_sync(DEMO, 154.380, instrument="USD_JPY") is False
    q[0](); tb.join(2.0)
    # A, B 決着後も X は確認済み B 基準で reject
    assert b.modify_sl_sync(DEMO, 154.380, instrument="USD_JPY") is False
    assert fake.calls == [(OANDA_ID, 154.350), (OANDA_ID, 154.400)]
    assert b.get_storm_guard_status()["totals"]["skipped"]["monotonic"] == 2


def test_serialization_cf_without_turnstile_b_can_confirm_before_a(monkeypatch):
    """CF pin: 順番待ちを外す (旧形) と B が A より先に broker に届き、A pending のまま
    B 確認済みという窓が生じる (= 上の assertion は直列化の存在に依存)。"""
    monkeypatch.setattr(OandaBridge, "_storm_wait_turn", lambda self, *a, **kw: True)
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=154.115)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")               # A
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")               # B
    q[1]()                                                          # B が先に届く (旧形)
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert fake.calls == [(OANDA_ID, 154.400)]
    assert st["confirmed_sl"] == 154.400 and st["pending"] == [154.350]   # ← review の窓


def test_serialization_turn_timeout_drops_request_and_rolls_back(monkeypatch):
    monkeypatch.setattr(OandaBridge, "STORM_TURN_WAIT_SEC", 0.1)
    b, fake = _bridge(monkeypatch, enforce=True, open_sl=154.115)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")               # A: worker が決着しない (走らせない)
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")               # B
    q[1]()                                                          # B は順番待ち timeout → drop
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert fake.calls == []                                         # 順序不明のまま送らない
    assert st["pending"] == [154.350] and st["confirmed_sl"] == 154.115
    assert b.get_storm_guard_status()["totals"]["failed"] == 1
    # sync 経路も同じ: A が決着しない限り drop → False
    assert b.modify_sl_sync(DEMO, 154.450, instrument="USD_JPY") is False
    assert fake.calls == []


def test_detect_only_mode_confirms_and_pends_symmetrically(monkeypatch):
    """既定 (検知のみ) でも予約/確認は同じ機構で動く — 送信は止めない。"""
    b, fake = _bridge(monkeypatch, enforce=False)
    q = _deferred_fire(b, monkeypatch)
    for _ in range(3):
        b.modify_sl(DEMO, 154.350, instrument="USD_JPY")
    assert len(q) == 3                                              # 検知のみ = 全部飛ぶ
    assert b.get_storm_guard_status()["trades"][DEMO]["pending"] == [154.350] * 3
    for fn in q:
        fn()
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert st["pending"] == [] and st["confirmed_sl"] == 154.350
    assert b.get_storm_guard_status()["totals"]["detected"]["idempotent"] == 2


# ── 検知のみモードは直列化でも待たない・落とさない (PR #287 review 4 巡目 P2) ──
# 既定の契約 = 「送信は従来通り、観測だけ」。順番待ち timeout で drop するのは enforce のみ。

def test_detect_only_turn_wait_never_drops_or_delays_but_counts(monkeypatch):
    monkeypatch.setattr(OandaBridge, "STORM_TURN_WAIT_SEC", 0.1)
    b, fake = _bridge(monkeypatch, enforce=False, open_sl=154.115)
    q = _deferred_fire(b, monkeypatch)
    b.modify_sl(DEMO, 154.350, instrument="USD_JPY")               # A: 決着しない (走らせない)
    b.modify_sl(DEMO, 154.400, instrument="USD_JPY")               # B
    t0 = __import__("time").monotonic()
    q[1]()                                                          # B は待たずに送る
    assert __import__("time").monotonic() - t0 < 0.1
    assert fake.calls == [(OANDA_ID, 154.400)]                      # 送信は止めない
    t = b.get_storm_guard_status()["totals"]
    assert t["detected"]["serialize"] == 1 and t["skipped"]["serialize"] == 0
    assert t["failed"] == 0                                         # drop されていない
    st = b.get_storm_guard_status()["trades"][DEMO]
    assert st["confirmed_sl"] == 154.400 and st["pending"] == [154.350]
    assert st["counts"]["serialize"] == 1


def test_detect_only_cf_enforce_is_the_only_difference_for_turn_drop(monkeypatch):
    """同一 fixture で enforce のみ反転: 検知のみ = 送信 / enforce = drop。"""
    monkeypatch.setattr(OandaBridge, "STORM_TURN_WAIT_SEC", 0.1)
    outcomes = {}
    for enforce in (False, True):
        b, fake = _bridge(monkeypatch, enforce=enforce, open_sl=154.115)
        q = _deferred_fire(b, monkeypatch)
        b.modify_sl(DEMO, 154.350, instrument="USD_JPY")
        b.modify_sl(DEMO, 154.400, instrument="USD_JPY")
        q[1]()
        t = b.get_storm_guard_status()["totals"]
        outcomes[enforce] = (len(fake.calls), t["skipped"]["serialize"], t["detected"]["serialize"])
    assert outcomes == {False: (1, 0, 1), True: (0, 1, 0)}
