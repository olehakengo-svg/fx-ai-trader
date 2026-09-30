"""単一エンジン化 — 本番ではエンジンを fork された子 (gunicorn worker) でだけ起こす
(rule:R3, 2026-09-30、analyses/dual-engine-dup-rate-readout-2026-09-24.md §6/§5b)。

固定する契約:
- 本番 (RENDER) で gunicorn master に import されたときだけ fork_child (master では thread を起こさない)。
  worker 自身の import / gunicorn 外では import 時 thread (PR #308 Codex P1)
- 巻き戻し env ENGINE_AUTOSTART_IN_IMPORT=1 で旧挙動 (import 時 thread)
- ローカル FORCE_AUTOSTART は従来どおり import 時 thread (fork しない dev server 用)
- 子では 1 回だけ起動、孫 (worker 内の os.fork) では起動しない — **実 fork** で検査
- app.py の import 時経路は本番で Thread を直接起こさず install_fork_child_autostart を通る
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pytest

from modules import engine_autostart as ea

ROOT = Path(__file__).resolve().parent.parent
APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")


M = ea.IMPORT_CTX_GUNICORN_MASTER
W = ea.IMPORT_CTX_GUNICORN_WORKER
O = ea.IMPORT_CTX_OTHER
PROD = dict(is_prod=True, force_local=False, legacy_off=False)


@pytest.mark.parametrize("kw,env,ctx,want", [
    (PROD, {}, M, ea.PLAN_FORK_CHILD),
    (PROD, {"ENGINE_AUTOSTART_IN_IMPORT": "1"}, M, ea.PLAN_IMPORT_THREAD),
    (PROD, {"ENGINE_AUTOSTART_IN_IMPORT": "0"}, M, ea.PLAN_FORK_CHILD),
    # worker 自身が import (gunicorn 既定 preload_app=False): fork hook は発火しないので
    # import 時 thread で起こす — PR #308 Codex P1
    (PROD, {}, W, ea.PLAN_IMPORT_THREAD),
    (PROD, {}, O, ea.PLAN_IMPORT_THREAD),
    (dict(is_prod=False, force_local=True, legacy_off=False), {}, M, ea.PLAN_IMPORT_THREAD),
    (dict(is_prod=True, force_local=False, legacy_off=True), {}, M, ea.PLAN_SKIP),
    (dict(is_prod=False, force_local=False, legacy_off=False), {}, M, ea.PLAN_SKIP),
])
def test_plan_autostart(kw, env, ctx, want):
    assert ea.plan_autostart(env=env, import_context=ctx, **kw) == want


@pytest.mark.parametrize("stack,want", [
    # arbiter の preload 経路 (fork 前の master)
    (["/opt/render/.venv/bin/gunicorn", "/x/site-packages/gunicorn/app/base.py",
      "/x/site-packages/gunicorn/arbiter.py", "/x/site-packages/gunicorn/util.py", "/repo/app.py"], M),
    # worker の load_wsgi (fork 後)
    (["/x/site-packages/gunicorn/arbiter.py", "/x/site-packages/gunicorn/workers/base.py",
      "/x/site-packages/gunicorn/app/wsgiapp.py", "/repo/app.py"], W),
    (["/repo/tools/some_bt.py", "/repo/app.py"], O),
    (["C:\\py\\gunicorn\\workers\\gthread.py"], W),
])
def test_detect_import_context(stack, want):
    assert ea.detect_import_context(stack) == want


def test_install_registers_after_in_child_only_and_does_not_start_in_importer():
    calls = []
    ran = []
    ea.install_fork_child_autostart(lambda: ran.append(1), register=lambda **k: calls.append(k))
    assert calls == [{"after_in_child": ea._after_fork_child}]
    time.sleep(0.05)
    assert ran == [], "import したプロセスで target が走った"


def _child_runs_hook(write_fd, *, grandchild: bool) -> None:
    """子プロセス内: hook を呼び (fork 直後を模擬)、起動結果を pipe に書く。"""
    started = ea._after_fork_child()
    time.sleep(0.2)
    msg = f"child:{int(started)};"
    if grandchild:
        pid = os.fork()
        if pid == 0:
            os.write(write_fd, f"grand:{int(ea._after_fork_child())};".encode())
            os._exit(0)
        os.waitpid(pid, 0)
    os.write(write_fd, msg.encode())


def test_real_fork_child_starts_once_and_grandchild_does_not():
    r, w = os.pipe()
    ea.install_fork_child_autostart(lambda: os.write(w, b"target;"), register=lambda **k: None)
    pid = os.fork()
    if pid == 0:
        try:
            _child_runs_hook(w, grandchild=True)
        finally:
            os._exit(0)
    os.waitpid(pid, 0)
    os.close(w)
    out = b""
    while True:
        chunk = os.read(r, 1024)
        if not chunk:
            break
        out += chunk
    os.close(r)
    s = out.decode()
    assert s.count("target;") == 1, s
    assert "child:1;" in s and "grand:0;" in s, s
    assert ea._state["claimed"] is False, "親 (import したプロセス) の claimed が立った"


def test_hook_refuses_when_parent_is_not_the_importer(monkeypatch):
    ran = []
    ea.install_fork_child_autostart(lambda: ran.append(1), register=lambda **k: None)
    monkeypatch.setitem(ea._state, "import_pid", -1)
    assert ea._after_fork_child() is False
    assert ran == []


def test_origin_value_has_no_digits():
    assert not re.search(r"\d", ea.ORIGIN_FORK_CHILD)


def test_app_prod_path_goes_through_fork_child_installer():
    m = re.search(r"_autostart_plan = _plan_autostart\((.*?)\nelse:\n", APP_SRC, re.S)
    assert m, "app.py の autostart 分岐が見つからない"
    block = m.group(1)
    i_fork = block.find("if _autostart_plan == _PLAN_FORK_CHILD:")
    i_install = block.find("_install_fork_child_autostart(")
    i_thread = block.find("_threading_mod.Thread(target=_auto_start_trader")
    assert -1 not in (i_fork, i_install, i_thread)
    assert i_fork < i_install < i_thread, "fork_child 分岐が import 時 thread より先に判定されていない"
    assert "origin=_ORIGIN_FORK_CHILD" in block
    # 旧経路 (無条件の import 時 thread 起動) が残っていない
    assert "if (_is_prod or _force_local) and not _legacy_off:\n    _auto_start_thread" not in APP_SRC


def test_claimed_guard_alone_blocks_second_start(monkeypatch):
    """ppid ガードを通る状態 (import_pid = 親) でも、2 回目の hook は起動しない —
    claimed ガード単独を pin (実 fork テストでは ppid ガードが先に効いて区別できない)。"""
    ran = []
    ea.install_fork_child_autostart(lambda: ran.append(1), register=lambda **k: None)
    monkeypatch.setitem(ea._state, "import_pid", os.getppid())
    assert ea._after_fork_child() is True
    assert ea._after_fork_child() is False
    time.sleep(0.05)
    assert ran == [1]
    monkeypatch.setitem(ea._state, "claimed", False)
