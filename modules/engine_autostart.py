"""取引エンジン autostart の起動経路を 1 本にする (rule:R3、2026-09-30)。

背景 ([[dual-engine-dup-rate-readout-2026-09-24]]): Render の gunicorn は app.py を
master で import し (preload 相当)、import 時 autostart が master でエンジンを起動、
fork された worker は StatusHeal で 2 本目を起動していた = 同一シグナルを 2 プロセス
が評価・emit する二重エンジン (kept shadow の p_f=0.625、LIVE 送信も両プロセスから)。
併せて master に thread を残すこと自体が fork poisoning の温床
([[lesson-prefork-master-must-not-touch-db-2026-09-22]])。

方針 (§6 案 A の fork-hook 版): 本番では import したプロセスではエンジンを起動せず、
`os.register_at_fork(after_in_child=...)` で **fork された子 (= gunicorn worker) の
中だけで** autostart thread を起こす。gunicorn の config ファイル読込み (Render が
独自 config を渡すかは非公開) に依存しない。

- 子の子 (worker 内の os.fork) では起動しない — claimed フラグは fork で継承される
  ので、最初の子が立てたフラグを孫が見て止まる。加えて親 PID が import PID で
  あることを要求する (二重の安全弁)。
- master の claimed は常に False のまま (after_in_child は子でしか走らない) なので、
  worker が再起動されれば新しい worker がエンジンを起こす。
- 巻き戻しは env `ENGINE_AUTOSTART_IN_IMPORT=1` (旧挙動 = import 時 thread)。
- fork 委譲は **gunicorn master で import されたと確定できた時だけ** (import 時の
  call stack に gunicorn があり、かつ gunicorn/workers/ が無い = arbiter の preload 経路)。
  worker が import するトポロジ (gunicorn 既定の preload_app=False) や gunicorn 外では、
  そのプロセスが serving プロセスなので従来どおり import 時 thread で起動する
  (fork hook は既に fork 済みの worker では発火しない — PR #308 Codex P1)。
"""

from __future__ import annotations

import os
import threading
import traceback
from typing import Callable, Iterable, Mapping, Optional

PLAN_SKIP = "skip"
PLAN_IMPORT_THREAD = "import_thread"
PLAN_FORK_CHILD = "fork_child"

# marker `[EMIT_PROC] <role>:<origin>` の origin 値 (数字を含めない)。
ORIGIN_FORK_CHILD = "forkchild"

IMPORT_CTX_GUNICORN_MASTER = "gunicorn_master"
IMPORT_CTX_GUNICORN_WORKER = "gunicorn_worker"
IMPORT_CTX_OTHER = "other"

_state: dict = {"claimed": False, "import_pid": None, "target": None}


def detect_import_context(filenames: Optional[Iterable[str]] = None) -> str:
    """app を import している call stack から実行文脈を判定する。

    gunicorn/workers/ を経由 = worker の load_wsgi (fork 後の serving プロセス)。
    gunicorn を経由するが workers/ を経由しない = arbiter の preload (fork 前の master)。
    """
    if filenames is None:
        filenames = [f.filename for f in traceback.extract_stack()]
    norm = [str(f).replace("\\", "/") for f in filenames]
    in_gunicorn = any("/gunicorn/" in f for f in norm)
    in_worker = any("/gunicorn/workers/" in f for f in norm)
    if in_worker:
        return IMPORT_CTX_GUNICORN_WORKER
    if in_gunicorn:
        return IMPORT_CTX_GUNICORN_MASTER
    return IMPORT_CTX_OTHER


def plan_autostart(*, is_prod: bool, force_local: bool, legacy_off: bool,
                   env: Mapping[str, str], import_context: str) -> str:
    """import 時にどの経路でエンジンを起こすかを決める (副作用なし)。"""
    if not (is_prod or force_local) or legacy_off:
        return PLAN_SKIP
    if (is_prod and import_context == IMPORT_CTX_GUNICORN_MASTER
            and hasattr(os, "register_at_fork")
            and env.get("ENGINE_AUTOSTART_IN_IMPORT", "0") != "1"):
        return PLAN_FORK_CHILD
    return PLAN_IMPORT_THREAD


def install_fork_child_autostart(target: Callable[[], None], *,
                                 register: Optional[Callable[..., None]] = None) -> None:
    """import したプロセスで呼ぶ。fork された子でだけ target を thread で起動する。

    register は遅延解決 (os.register_at_fork は Unix のみ — Windows では module import
    時に落とさない、PR #308 Codex P2)。fork 委譲は gunicorn master でしか選ばれないので
    非 Unix でここに来ることは無いが、来たら明示的に失敗させる。"""
    if register is None:
        register = getattr(os, "register_at_fork", None)
        if register is None:
            raise RuntimeError("os.register_at_fork unavailable — fork_child plan requires a POSIX fork")
    _state["import_pid"] = os.getpid()
    _state["target"] = target
    _state["claimed"] = False
    register(after_in_child=_after_fork_child)


def _after_fork_child() -> bool:
    """fork 直後の子で走る。起動したら True。"""
    if _state["claimed"]:
        return False
    _state["claimed"] = True
    if _state["target"] is None or os.getppid() != _state["import_pid"]:
        return False
    threading.Thread(target=_state["target"], name="EngineAutoStartForkChild",
                     daemon=True).start()
    return True
