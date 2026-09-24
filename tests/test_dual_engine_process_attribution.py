"""二重エンジン (gunicorn master + worker) のプロセス帰属計装 — rule:R3, 2026-09-24.

背景: gunicorn は app.py を master で import した直後に worker を fork する。
import 時 autostart のエンジンは master に残り、worker では StatusHeal が
2 本目のエンジンを起こす (analyses/http-blind-fork-poisoning-2026-09-22 §6)。
30d 実測では shadow 近接 dup 133 ペア (kept 1,670 行の 8.0%) が write-time
`dedup_violation` で全件捕捉される一方、**solo emission (92%) がどちらの
プロセス由来かは記録が無く**、単一エンジン化の regime break 幅 (shadow
生成率の変化) を事前推定できなかった
(analyses/dual-engine-dup-rate-readout-2026-09-24.md §4)。

本テストが固定する契約 (すべて record-only、取引挙動・gate・dedup は不変):
- ``engine_process_role()`` は import 時 PID との一致で 2 値 (import/forked) —
  **実 fork** で検査する (凍結 PID の差し替えだけでは deploy 時の import 順序を通らない)
- origin (autostart / statusheal) = このプロセスのエンジンを実際に起こした経路。
  role が import 順序の前提に依存するのに対し origin は事実 (PR #296 review P1)
- 両方の ``self._db.open_trade(`` call site が ``[EMIT_PROC] <role>`` を
  row reasons に永続する (片側だけ塞ぐと「対称に処置せよ」違反)
- ``[MainLoop] iter=`` / tick / ``[StatusHeal] Healed`` の stdout ログに
  pid が乗る (Render ログで 2 カウンタを PID で分離できる)
- ``get_status()`` payload が ``engine_pid`` / ``engine_process_role`` を返す
"""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

import pytest

from modules import demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import (
    DemoTrader,
    EMIT_PROC_REASON_TAG,
    ENGINE_START_ORIGIN_UNKNOWN,
    emit_proc_marker,
    engine_process_role,
)

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / "modules" / "demo_trader.py").read_text(encoding="utf-8")
APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")


# ── role の 2 値 ─────────────────────────────────────────────────────────

def test_role_is_import_in_the_importing_process():
    assert engine_process_role() == "import"
    assert emit_proc_marker() == f"{EMIT_PROC_REASON_TAG} import:unknown"
    assert emit_proc_marker("autostart") == f"{EMIT_PROC_REASON_TAG} import:autostart"


def test_role_is_forked_when_pid_differs_from_import_pid(monkeypatch):
    """fork 後の子は import 時 PID と一致しない → 'forked'。
    (fork そのものは pytest で再現しないので凍結 PID をずらして等価に検査)"""
    monkeypatch.setattr(
        demo_trader_mod, "_MODULE_IMPORT_PID", demo_trader_mod._MODULE_IMPORT_PID + 1
    )
    assert engine_process_role() == "forked"
    assert emit_proc_marker("statusheal") == f"{EMIT_PROC_REASON_TAG} forked:statusheal"


@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX fork required")
def test_real_fork_child_reports_forked_and_parent_reports_import():
    """凍結 PID の差し替えではなく **実際に fork** して契約を検査する (PR #296 review P1:
    「テストは fork を模しているだけで deploy 時の import 順序を通していない」)。
    親 = import したプロセス → import / 子 = fork 後 → forked。"""
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:  # child
        try:
            os.write(w, engine_process_role().encode())
        finally:
            os._exit(0)
    os.close(w)
    try:
        child_role = os.read(r, 64).decode()
    finally:
        os.close(r)
        os.waitpid(pid, 0)
    assert child_role == "forked"
    assert engine_process_role() == "import"


def test_marker_has_no_pid_digits():
    """row 側 marker に PID を入れると boot 毎に値が変わりラベル分析の
    cardinality が爆発する — role (2 値) × origin (3 値) の有限集合だけを許す。"""
    for o in ("autostart", "statusheal", ENGINE_START_ORIGIN_UNKNOWN):
        assert not re.search(r"\d", emit_proc_marker(o))


# ── origin: 実際の起動経路が記録される ──────────────────────────────────

def test_autostart_path_stamps_origin_before_starting_modes():
    """app.py の import 時 autostart はモード起動の**前**に origin=autostart を刻む
    (後だと最初の tick の row が unknown になる)。"""
    body = re.search(r"def _auto_start_trader\(\):(.*?)\n# Polarity-inverted", APP_SRC, re.S)
    assert body, "_auto_start_trader が見つからない"
    b = body.group(1)
    i_stamp = b.find('_demo_trader._engine_start_origin = "autostart"')
    i_start = b.find("_demo_trader.start(mode=_mode)")
    assert i_stamp != -1 and i_start != -1
    assert i_stamp < i_start, "origin の記録がモード起動より後ろにある"


def test_statusheal_mainloop_restart_stamps_origin():
    """StatusHeal が MainLoop を起こす分岐 (worker で 2 本目のエンジンが立つ経路) が
    origin=statusheal を刻む。"""
    body = _get_status_body()
    i_print = body.find('print("[StatusHeal] MainLoop dead — restarting"')
    i_stamp = body.find('self._engine_start_origin = "statusheal"')
    assert i_print != -1 and i_stamp != -1
    assert 0 < i_stamp - i_print < 400, "origin 記録が MainLoop 再起動分岐の直後にない"


def test_instance_marker_uses_engine_start_origin():
    t = DemoTrader.__new__(DemoTrader)
    assert t._emit_proc_marker() == f"{EMIT_PROC_REASON_TAG} import:unknown"
    t._engine_start_origin = "statusheal"
    assert t._emit_proc_marker() == f"{EMIT_PROC_REASON_TAG} import:statusheal"


# ── 対称性: 両方の open_trade call site が marker を積む ────────────────

_OPEN_TRADE_CALL = "trade_id = self._db.open_trade("


def test_exactly_two_open_trade_call_sites_and_both_append_marker():
    sites = [m.start() for m in re.finditer(re.escape(_OPEN_TRADE_CALL), SRC)]
    assert len(sites) == 2, (
        f"open_trade call site が {len(sites)} 箇所 — 新しい emit 経路を足したら"
        " emit_proc_marker() も同じ commit で積むこと (対称性)"
    )
    for pos in sites:
        window = SRC[max(0, pos - 600):pos]
        assert "self._emit_proc_marker()" in window, (
            "open_trade の直前 600 文字に self._emit_proc_marker() が無い call site がある"
        )
    assert SRC.count("+ [self._emit_proc_marker()]") == 2, "helper の使用箇所 (append) は call site 数と一致"


def test_marker_is_record_only_not_a_predicate():
    """marker を選択条件に使ってはならない (record-only 契約)。
    `if ... EMIT_PROC` / `in reasons` 型の読み取りが本体に無いことを pin。"""
    body = SRC
    for pat in (r"if[^\n]*EMIT_PROC", r"EMIT_PROC_REASON_TAG[^\n]*\bin\b[^\n]*reasons"):
        assert not re.search(pat, body), f"marker が述語として読まれている: {pat}"


# ── stdout ログに pid ────────────────────────────────────────────────────

def test_mainloop_iter_log_carries_pid_and_role():
    m = re.search(r'print\(f"\[MainLoop\] iter=\{_loop_iter\}([^"]*)"', SRC)
    assert m, "[MainLoop] iter= の print が見つからない"
    assert "pid={_os.getpid()}" in m.group(1)
    assert "role={engine_process_role()}" in m.group(1)


def test_mode_tick_log_carries_pid():
    m = re.search(r'print\(f"\[MainLoop/\{mode\}\] tick #([^"]*)"', SRC)
    assert m, "tick ログの print が見つからない"
    assert "pid={_os.getpid()}" in m.group(1)


def test_statusheal_healed_log_carries_pid_and_role():
    m = re.search(r'print\(f"\[StatusHeal\] Healed: \{_healed\}([^"]*)"', SRC)
    assert m, "[StatusHeal] Healed の print が見つからない"
    assert "pid={_os.getpid()}" in m.group(1)
    assert "role={engine_process_role()}" in m.group(1)


def test_autostart_log_carries_pid_and_role():
    m = re.search(r'print\(f"\[AutoStart\] Starting \{len\(_all_modes\)\} modes([^"]*)"', APP_SRC)
    assert m, "[AutoStart] Starting の print が見つからない"
    assert "pid={os.getpid()}" in m.group(1)
    assert "role={_engine_process_role()}" in m.group(1)


# ── status payload ───────────────────────────────────────────────────────

def _get_status_body() -> str:
    m = re.search(r"^    def get_status\(self\)", SRC, re.M)
    assert m
    rest = SRC[m.end():]
    nxt = re.search(r"^    def ", rest, re.M)
    return rest[: nxt.start()]


def test_get_status_payload_declares_engine_pid_role_import_pid_and_origin():
    """engine_import_pid は読み手の self-check 用 — worker で engine_pid ==
    engine_import_pid なら worker 自身が import している (role 軸は使えない)。"""
    body = _get_status_body()
    assert '"engine_pid": _os.getpid()' in body
    assert '"engine_process_role": engine_process_role()' in body
    assert '"engine_import_pid": _MODULE_IMPORT_PID' in body
    assert '"engine_start_origin":' in body


# ── 振る舞い: shadow 永続化 row の reasons に marker が乗る ─────────────

@pytest.fixture
def trader(tmp_path, monkeypatch):
    t = DemoTrader(DemoDB(str(tmp_path / f"emit_proc_{uuid.uuid4().hex}.db")))
    monkeypatch.setattr(t, "_add_log", lambda *_a, **_k: None)
    monkeypatch.setattr(
        t, "_get_mtf_regime",
        lambda _instrument: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"},
    )
    # alpha snapshot は外部データを引く — record-only の付帯物なので潰す
    try:
        from modules import alpha_snapshot as alpha_snap_mod
        monkeypatch.setattr(alpha_snap_mod, "snapshot_at", lambda *_a, **_k: {"error": "unit-test"})
    except Exception:
        pass
    return t


def _reasons_of(row: dict) -> list:
    raw = row.get("reasons")
    if isinstance(raw, str):
        return json.loads(raw) if raw else []
    return list(raw or [])


def test_shadow_emit_row_persists_emit_proc_marker(trader):
    trade_id = trader._open_shadow_emit_trade(
        direction="BUY", entry_price=150.000, sl=149.850, tp=150.200,
        entry_type="rnb_support_bounce", confidence=68, tf="15m",
        reasons=["✅ RNB support 150.00"], score=1.0, mode="rnb_usdjpy",
        instrument="USD_JPY", spread_at_entry=1.0,
        mtf_regime="uncertain", mtf_d1_label=3, mtf_h4_label=3, mtf_vol_state="normal",
        dedup_already_reserved=True,
    )
    assert trade_id, "shadow 永続化が row を返さない (fixture の前提が変わった)"
    rows = [r for r in trader._db.get_open_trades() if r.get("trade_id") == trade_id]
    assert len(rows) == 1
    reasons = _reasons_of(rows[0])
    assert "✅ RNB support 150.00" in reasons, "元の reasons を潰してはいけない"
    assert f"{EMIT_PROC_REASON_TAG} import:unknown" in reasons
    assert sum(1 for r in reasons if r.startswith(EMIT_PROC_REASON_TAG)) == 1, "marker は 1 個だけ"


def test_shadow_emit_row_marker_reflects_forked_role(trader, monkeypatch):
    """反対側 (恒真でないことの確認): role が forked ならその値が乗る。"""
    monkeypatch.setattr(
        demo_trader_mod, "_MODULE_IMPORT_PID", demo_trader_mod._MODULE_IMPORT_PID + 1
    )
    trader._engine_start_origin = "statusheal"
    trade_id = trader._open_shadow_emit_trade(
        direction="SELL", entry_price=150.000, sl=150.150, tp=149.800,
        entry_type="rnb_support_bounce", confidence=68, tf="15m",
        reasons=[], score=1.0, mode="rnb_usdjpy",
        instrument="USD_JPY", spread_at_entry=1.0,
        mtf_regime="uncertain", mtf_d1_label=3, mtf_h4_label=3, mtf_vol_state="normal",
        dedup_already_reserved=True,
    )
    rows = [r for r in trader._db.get_open_trades() if r.get("trade_id") == trade_id]
    assert len(rows) == 1
    assert f"{EMIT_PROC_REASON_TAG} forked:statusheal" in _reasons_of(rows[0])
