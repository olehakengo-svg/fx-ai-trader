"""SL replacement storm の根 (caller 側) — LIVE 経路の broker 確認済み SL を persist する (rule:R3, 2026-10-21).

根 (code derivation: knowledge-base/wiki/analyses/storm-guard-design-2026-09-22.md §8):
  `DemoTrader._check_sltp_realtime` (0.5 s 毎) は毎 tick `self._db.get_open_trades()` から
  `sl = trade["sl"]` を読み直す。shadow 分岐は BE/trail の新 SL を `update_sl_tp` で DB に
  persist するが、LIVE 分岐は `modify_sl_sync` 成功後に **persist しない** (2026-06-03
  ab7a4931 以来)。よって LIVE 行の baseline は永久に ON_FILL SL のままで、
    family A (同値 loop)    : 同じ BE 値を毎 tick 再送 (#837978 4,791 / #847578 5,936 / #1254229 269)
    family B (trail⇄BE 往復): Tier2 trail (bid − 0.5·ATR) と Tier1 BE (entry + spread) は同じ
                              if/else の排他 2 分岐で、両方の `if new_sl > sl` が stale な ON_FILL
                              SL と比較されるため恒真 → bid が entry+1.5·ATR を跨ぐたびに反転
                              (#1254773 46,091 送信 / 11.82 h、BE 157.758 ×8,091)
  が同じ根から出る。

修正 (caller 層、bridge 不変):
  (1) LIVE 分岐の `modify_sl_sync` 成功後に shadow と対称に `update_sl_tp` (耐久脚)
  (2) `_live_sl_sent[trade_id]` に最終 broker 確認値を保持し、次 tick の baseline を
      「DB sl と確認値の保護側」で合成 (DB 書込み失敗 = 2026-08-21 Disk 満杯型 の保険)
  (3) 同形状の兄弟 (confluence_scalp 継続 trail) を同 PR で対称修正
  (4) `pnl_r` の分母は ON_FILL SL 距離 (`sl_initial` 列) — persist で `sl` 列が動くため

契約 (本ファイルが pin するもの):
  (a) family A: 同値再送が 1 回で止まる / (b) family B: BE 引き戻しが送られない、送信は単調
  (c) BE writer は trail 後に冪等 / (d) 失敗時の rollback 契約は不変 (再試行は継続)
  (e) shadow 経路は byte 同一 / (f) DB 書込み失敗でも in-memory 脚が storm を止める
  (g) CF: 両脚を殺すと storm #3 の形が再現する = assertion は修正の存在に依存
  (h) 推定量の明示変更: LIVE 行も persist 済み trail SL に対して engine 側 SL_HIT 判定が走る
  (i) pnl_r は ON_FILL SL 距離で割る (legacy 行は従来どおり) / (j) 実 OandaBridge で
      detected.idempotent == detected.monotonic == 0 (enforce 有無とも) — 回帰アラームの基準値
  (k) AST: `_check_sltp_realtime` 内の全 modify_sl_sync 成功分岐が persist する
"""
from __future__ import annotations

import ast
import uuid
from datetime import datetime as real_datetime, timezone
from pathlib import Path

import pytest

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader
from modules.oanda_bridge import OandaBridge

REPO_ROOT = Path(__file__).resolve().parent.parent

ENTRY = 157.75
SL0 = 157.583          # ON_FILL SL = entry − 16.7p (#1254773 実測)
TP0 = 158.47
ATR = 0.16             # trail 幅 0.08 / BE 帯 favorable ∈ [0.128, 0.24) / 切替 bid 157.99
OANDA_ID = "1254773"
SPREAD = 0.008         # OANDA USD_JPY 0.8p → BE 値 = 157.758

FAMILY_B_BIDS = [158.02, 157.95, 158.05, 158.05, 157.95]
STORM_SHAPE_BEFORE_FIX = [157.94, 157.758, 157.97, 157.97, 157.758]   # trail⇄BE 往復 + 同値再送


class _FixedDatetime(real_datetime):
    """2026-05-28 (木) 12:00 UTC — 週末 close / 金曜 21:45Z 壁時計に当たらない (lesson 10-15)。"""

    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        if tz is None:
            return base.replace(tzinfo=None)
        return base.astimezone(tz)


class _StubBridge:
    """modify_sl_sync を記録して result を返す。close_trade も記録。"""

    def __init__(self, result: bool = True):
        self.active = True
        self.result = result
        self.calls: list[float] = []
        self.closes: list[tuple[str, str]] = []

    def modify_sl_sync(self, trade_id, sl, instrument=""):
        self.calls.append(sl)
        return self.result

    def close_trade(self, trade_id, reason="", **_kw):
        self.closes.append((trade_id, reason))
        return True


class _BidScript:
    """tick ごとに 1 bid (最後の値で据え置き)。ask = bid + 0.8p。"""

    def __init__(self, bids):
        self.bids = list(bids)
        self.i = 0

    def __call__(self, _inst):
        b = self.bids[min(self.i, len(self.bids) - 1)]
        self.i += 1
        return {"bid": b, "ask": round(b + SPREAD, 3), "mid": round(b + SPREAD / 2, 4)}


class _FakeClient:
    """tests/test_oanda_bridge_storm_guard.py と同形の最小 OANDA client。"""

    def __init__(self):
        self.calls: list[tuple[str, float]] = []
        self.configured = True

    def modify_trade(self, oanda_id, stop_loss=None, instrument=None, **_kw):
        self.calls.append((oanda_id, stop_loss))
        return True, {"ok": True}

    def get_open_trades(self):
        return True, {"trades": [{"id": OANDA_ID, "instrument": "USD_JPY",
                                  "currentUnits": "1000", "initialUnits": "1000",
                                  "stopLossOrder": {"price": f"{SL0:.3f}"}}]}


@pytest.fixture
def env(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"slroot_{uuid.uuid4().hex}.db")))
    logs: list[str] = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    bridge = _StubBridge()
    monkeypatch.setattr(trader, "_oanda", bridge)
    return trader, bridge, logs


def _open(trader, *, shadow: bool = False,
          entry_type: str = "usdjpy_carry_dip_accumulator") -> str:
    tid = trader._db.open_trade(
        direction="BUY", entry_price=ENTRY, sl=SL0, tp=TP0, entry_type=entry_type,
        confidence=80, tf="1h", mode="daytrade_1h", instrument="USD_JPY",
        is_shadow=shadow, oanda_trade_id="" if shadow else OANDA_ID)
    trader._entry_atr[tid] = ATR
    return tid


def _run(trader, monkeypatch, bids) -> None:
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", _BidScript(bids))
    for _ in bids:
        trader._check_sltp_realtime()


def _row(trader, tid: str) -> dict:
    with trader._db._safe_conn() as conn:
        r = conn.execute("SELECT * FROM demo_trades WHERE trade_id=?", (tid,)).fetchone()
    return dict(r)


# ── (a) family A ───────────────────────────────────────────────────────────

def test_family_a_same_price_resend_stops_after_live_persist(env, monkeypatch):
    trader, bridge, _ = env
    tid = _open(trader)
    _run(trader, monkeypatch, [157.95] * 5)           # favorable 0.20 = BE 帯
    assert bridge.calls == [157.758], bridge.calls    # 修正前: [157.758] * 5
    assert _row(trader, tid)["sl"] == 157.758         # 修正前: 157.583 (ON_FILL のまま)
    assert trader._live_sl_sent[tid] == 157.758


# ── (b) family B ───────────────────────────────────────────────────────────

def test_family_b_trail_then_be_pullback_eliminated(env, monkeypatch):
    trader, bridge, _ = env
    tid = _open(trader)
    _run(trader, monkeypatch, FAMILY_B_BIDS)
    assert bridge.calls == [157.94, 157.97], bridge.calls   # 修正前: STORM_SHAPE_BEFORE_FIX
    assert all(b > a for a, b in zip(bridge.calls, bridge.calls[1:]))
    assert 157.758 not in bridge.calls
    assert _row(trader, tid)["sl"] == 157.97


# ── (c) BE writer の冪等性 ────────────────────────────────────────────────

def test_be_writer_idempotent_after_trail(env, monkeypatch):
    trader, bridge, _ = env
    tid = _open(trader)
    _run(trader, monkeypatch, [158.02] + [157.90] * 20)
    assert bridge.calls == [157.94]
    assert _row(trader, tid)["sl"] == 157.94


# ── (d) 失敗時 rollback 契約は不変 ────────────────────────────────────────

def test_modify_failure_rolls_back_and_persists_nothing(env, monkeypatch):
    trader, bridge, _ = env
    bridge.result = False
    tid = _open(trader)
    _run(trader, monkeypatch, [157.95] * 3)
    assert bridge.calls == [157.758] * 3              # 再試行は継続 (既存契約)
    assert _row(trader, tid)["sl"] == SL0
    assert tid not in trader._live_sl_sent


# ── (e) shadow 経路は不変 ─────────────────────────────────────────────────

def test_shadow_row_path_unchanged(env, monkeypatch):
    trader, bridge, _ = env
    tid = _open(trader, shadow=True)
    path = []
    for b in FAMILY_B_BIDS:
        _run(trader, monkeypatch, [b])
        path.append(_row(trader, tid)["sl"])
    assert bridge.calls == []                          # bridge 不到達
    assert path == [157.94, 157.94, 157.97, 157.97, 157.97]
    assert trader._live_sl_sent == {}


# ── (f) in-memory 脚: DB 書込み失敗でも baseline は ON_FILL に戻らない ──

def test_in_memory_baseline_survives_db_write_failure(env, monkeypatch):
    trader, bridge, _ = env
    tid = _open(trader)

    def _disk_full(*_a, **_k):
        raise RuntimeError("simulated disk full (2026-08-21 型)")

    monkeypatch.setattr(trader._db, "update_sl_tp", _disk_full)
    _run(trader, monkeypatch, [158.02] + [157.95] * 4)
    assert bridge.calls == [157.94]
    assert _row(trader, tid)["sl"] == SL0              # 耐久脚は失敗したまま
    assert trader._live_sl_sent[tid] == 157.94


# ── (g) CF: 両脚を殺すと storm #3 の形が再現する ──────────────────────────

class _NoWriteDict(dict):
    def __setitem__(self, _k, _v):
        pass


def test_cf_killing_both_legs_reproduces_storm_shape(env, monkeypatch):
    trader, bridge, _ = env
    tid = _open(trader)
    monkeypatch.setattr(trader._db, "update_sl_tp", lambda *_a, **_k: None)
    trader._live_sl_sent = _NoWriteDict()
    _run(trader, monkeypatch, FAMILY_B_BIDS)
    assert bridge.calls == STORM_SHAPE_BEFORE_FIX, bridge.calls
    assert _row(trader, tid)["sl"] == SL0


def test_cf_killing_db_leg_only_is_still_protected_by_memory_leg(env, monkeypatch):
    trader, bridge, _ = env
    _open(trader)
    monkeypatch.setattr(trader._db, "update_sl_tp", lambda *_a, **_k: None)
    _run(trader, monkeypatch, FAMILY_B_BIDS)
    assert bridge.calls == [157.94, 157.97]


# ── (h) 推定量の明示変更: LIVE 行の engine 側 SL_HIT は persist 済み trail に対して ──

def test_live_sl_hit_now_judged_against_persisted_trail(env, monkeypatch):
    trader, bridge, _ = env
    tid = _open(trader)
    _run(trader, monkeypatch, [158.02, 157.93])        # trail 157.94 → 次 tick bid 157.93
    row = _row(trader, tid)
    assert bridge.calls == [157.94]
    assert row["status"] == "CLOSED"
    assert row["close_reason"] == "SL_HIT"             # 修正前: BE 157.758 に再計算されて close しない
    assert row["exit_price"] == 157.93
    assert bridge.closes == [(tid, "SL_HIT")]
    assert tid not in trader._live_sl_sent             # close で cleanup


# ── (h') PR #346 Codex P1: 写しは DB close が確定してから捨てる ──────────────

def test_cached_sl_survives_close_trade_db_failure(env, monkeypatch):
    """update_sl_tp が失敗して DB sl が ON_FILL のまま (写しだけが確認済み値) の状態で、
    close_trade が一時的 DB 障害で例外 → 行は OPEN のまま残る。写しを close 前に pop して
    いると次 tick の baseline が ON_FILL に戻り BE 157.758 を再送/緩めてしまう。"""
    trader, bridge, _ = env
    tid = _open(trader)

    def _disk_full(*_a, **_k):
        raise RuntimeError("simulated disk full")

    monkeypatch.setattr(trader._db, "update_sl_tp", _disk_full)
    _run(trader, monkeypatch, [158.02])                 # trail 157.94 → 写しのみ (DB は SL0)
    assert bridge.calls == [157.94] and _row(trader, tid)["sl"] == SL0

    real_close = trader._db.close_trade

    def _db_locked(*_a, **_k):
        raise RuntimeError("simulated: database is locked")

    monkeypatch.setattr(trader._db, "close_trade", _db_locked)
    _run(trader, monkeypatch, [157.93])                 # SL_HIT 経路 → close_trade が例外
    assert _row(trader, tid)["status"] == "OPEN"        # 行は残る (per-trade except)
    assert trader._live_sl_sent[tid] == 157.94          # 写しは捨てられていない
    assert bridge.calls == [157.94]

    _run(trader, monkeypatch, [157.95])                 # BE 帯: 写しが baseline → 再送なし
    assert bridge.calls == [157.94]

    monkeypatch.setattr(trader._db, "close_trade", real_close)
    _run(trader, monkeypatch, [157.93])                 # 復旧 → close 成立 → 写しは pop
    assert _row(trader, tid)["status"] == "CLOSED"
    assert tid not in trader._live_sl_sent


# ── (i) pnl_r の分母は ON_FILL SL 距離 ────────────────────────────────────

def test_pnl_r_uses_initial_sl_not_trailed_sl(tmp_path):
    db = DemoDB(str(tmp_path / "r.db"))

    def _open_row():
        return db.open_trade(direction="BUY", entry_price=ENTRY, sl=SL0, tp=TP0,
                             entry_type="usdjpy_carry_dip_accumulator", confidence=80,
                             tf="1h", mode="daytrade_1h", instrument="USD_JPY",
                             oanda_trade_id=OANDA_ID)

    tid = _open_row()
    db.update_sl_tp(tid, 157.94, TP0)                  # trail persist
    res = db.close_trade(tid, 157.93, "SL_HIT")
    assert res["pnl_pips"] == 18.0
    assert res["pnl_r"] == round(18.0 / 16.7, 2)       # 1.08 — 決済時 sl (19p) で割ると 0.95

    # legacy 行 (sl_initial 無し) は後方互換: 従来どおり決済時 sl で割る
    tid2 = _open_row()
    with db._safe_conn() as conn:
        conn.execute("UPDATE demo_trades SET sl_initial=NULL WHERE trade_id=?", (tid2,))
        conn.commit()
    db.update_sl_tp(tid2, 157.94, TP0)
    res2 = db.close_trade(tid2, 157.93, "SL_HIT")
    assert res2["pnl_r"] == round(18.0 / 19.0, 2)


# ── (j) 実 OandaBridge: 修正後は detected.idempotent == detected.monotonic == 0 ──

@pytest.mark.parametrize("enforce", ["", "1"])
def test_real_bridge_guard_counters_zero_after_fix(env, monkeypatch, enforce):
    trader, _, _ = env
    monkeypatch.setenv("OANDA_LIVE", "true")
    monkeypatch.setenv("STORM_GUARD_ENFORCE", enforce)
    for k in ("STORM_GUARD_DEADBAND_PIPS", "STORM_GUARD_MAX_TX_PER_HOUR",
              "STORM_GUARD_MAX_TX_PER_DAY", "STORM_GUARD_ALLOW_SL_LOOSEN"):
        monkeypatch.delenv(k, raising=False)
    tid = _open(trader)
    b = OandaBridge(db=trader._db)
    fake = _FakeClient()
    b._client = fake
    monkeypatch.setattr(b, "_fire", lambda fn, *a, **kw: fn(*a, **kw))
    b.set_trade_mapping(tid, OANDA_ID)
    b._storm_register_trade(tid, "BUY", SL0)
    monkeypatch.setattr(trader, "_oanda", b)

    _run(trader, monkeypatch, [157.95] * 5 + FAMILY_B_BIDS)

    assert [sl for _, sl in fake.calls] == [157.758, 157.94, 157.97], fake.calls
    st = b.get_storm_guard_status()
    assert st["enforce"] is (enforce == "1")
    assert st["totals"]["sent"] == 3
    assert st["totals"]["detected"]["idempotent"] == 0    # 修正前 (detect-only): ≥ 4
    assert st["totals"]["detected"]["monotonic"] == 0     # 修正前 (detect-only): ≥ 2
    assert sum(st["totals"]["skipped"].values()) == 0
    assert _row(trader, tid)["sl"] == 157.97


# ── (k) AST: 全 modify_sl_sync 成功分岐が persist する (兄弟の対称性) ─────

def test_every_modify_sl_sync_success_branch_persists():
    src = (REPO_ROOT / "modules" / "demo_trader.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_check_sltp_realtime")

    def _is_modify(node) -> bool:
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "modify_sl_sync")

    def _persists(nodes) -> bool:
        return any(isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                   and sub.func.attr == "update_sl_tp"
                   for n in nodes for sub in ast.walk(n))

    checked = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        t = node.test
        if _is_modify(t):                                   # if modify_sl_sync(...): <success>
            assert _persists(node.body), f"L{node.lineno}: 成功分岐に update_sl_tp が無い"
            checked.append(node.lineno)
        elif (isinstance(t, ast.UnaryOp) and isinstance(t.op, ast.Not)
              and _is_modify(t.operand)):                   # if not modify_sl_sync(...): rollback / else: <success>
            assert node.orelse and _persists(node.orelse), (
                f"L{node.lineno}: `if not modify_sl_sync` の else (成功分岐) に update_sl_tp が無い"
                " — LIVE 分岐の未 persist = storm family A/B の根")
            checked.append(node.lineno)
    assert len(checked) >= 6, checked
