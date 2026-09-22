"""DailyReviewEngine は gunicorn master の pre-fork 窓で SQLite を触ってはならない (rule:R3, 2026-09-22).

背景 (knowledge-base/wiki/analyses/http-blind-fork-poisoning-2026-09-22.md):
Render の gunicorn は app.py を **master (PID 39) で import** し、その直後
(実測 20〜300 ms) に worker を fork する。``DemoTrader.__init__`` が import 時に
起動していた DailyReviewEngine スレッドは、プロセスが UTC 0 時台に起動すると
**即座に**前日レビュー (24 モード × 全件スキャン) + C1 prune + 204 MB backup を
master 側で走らせる。fork がその最中に落ちると、子 (= HTTP worker) は SQLite の
プロセス共有 mutex を locked のまま継承し、**DB を触る全ルートが永久ハング**する
(2026-09-12 / 09-15 / 09-22 の 3 回、各 3h19m〜3h31m の HTTP 全盲)。

固定する性質:
  A. DemoTrader 構築 (= import 時) では DailyReview スレッドが**起動しない**
  B. serving process の heal (``ensure_running``) が起動し、冪等である
  C. heal は request 経路 (before_request heartbeat) に**実際に配線されている**
     (計装を書いても読み手が無ければ無音 — 本プロジェクトが 5 回踏んだ型)

counterfactual (実測済): ``DemoTrader.__init__`` の ``start(defer=True)`` を旧来の
``start()`` に戻すと A が落ちる。heartbeat から ``ensure_daily_review_running`` の
呼び出しを消すと C が落ちる。
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

from modules.daily_review import DailyReviewEngine, THREAD_NAME
from modules.demo_db import DemoDB

ROOT = Path(__file__).resolve().parents[1]


def _live_review_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == THREAD_NAME and t.is_alive()]


class _NoopLearning:
    pass


def test_demo_trader_construction_does_not_start_review_thread(monkeypatch, tmp_path):
    """性質 A — import 時 (= master の pre-fork 窓) にスレッドを起動しない。"""
    from modules.demo_trader import DemoTrader

    before = len(_live_review_threads())
    trader = DemoTrader(DemoDB(str(tmp_path / "t.db")))
    assert len(_live_review_threads()) == before, (
        "DemoTrader 構築で DailyReviewEngine スレッドが起動した — gunicorn master の "
        "pre-fork 窓で SQLite が走り、fork した worker の DB が永久ハングする経路が復活している"
    )
    # arm はされている (heal が「未 start」と誤認して黙らないこと)
    assert trader._daily_review.is_deferred(), "defer 状態が arm されていない"


def test_ensure_running_starts_once_and_is_idempotent(monkeypatch, tmp_path):
    """性質 B — heal は 1 本だけ起動し、2 回目は no-op。"""
    eng = DailyReviewEngine(DemoDB(str(tmp_path / "t.db")), _NoopLearning())
    # scheduler 本体は走らせない (テスト DB でレビューを回さない)
    started = threading.Event()
    monkeypatch.setattr(eng, "_scheduler_loop", lambda: started.wait(5))

    eng.start(defer=True)
    assert eng.is_deferred() and eng._thread is None

    r1 = eng.ensure_running()
    assert r1["healed"] is True
    assert eng._thread is not None and eng._thread.is_alive()

    r2 = eng.ensure_running()
    assert r2["healed"] is False and r2["reason"] == "alive"
    started.set()


def test_ensure_running_refuses_when_never_armed(tmp_path):
    """未 start (テスト/明示的に使わない構成) の engine を勝手に起こさない。"""
    eng = DailyReviewEngine(DemoDB(str(tmp_path / "t.db")), _NoopLearning())
    assert eng.ensure_running() == {"healed": False, "reason": "never started"}


def test_ensure_running_refuses_after_stop(monkeypatch, tmp_path):
    eng = DailyReviewEngine(DemoDB(str(tmp_path / "t.db")), _NoopLearning())
    eng.start(defer=True)
    eng.stop()
    assert eng.ensure_running()["reason"] == "stopped"


def test_heartbeat_reaches_daily_review_heal(flask_client, monkeypatch):
    """性質 C (到達性 pin) — before_request heartbeat が DailyReview の heal を呼ぶ。

    heartbeat は 60s throttle されるため時計を巻き戻してから叩く
    (tests/test_status_volume_keeper.py と同じ手順)。
    """
    import app as app_module

    called: list[int] = []
    monkeypatch.setattr(app_module._demo_trader, "ensure_daily_review_running",
                        lambda: called.append(1) or {"healed": False, "reason": "test"})
    app_module._positioning_heartbeat_last[0] = 0.0
    flask_client.get("/healthz/http")
    assert called, (
        "heartbeat が DemoTrader.ensure_daily_review_running に到達していない — "
        "DailyReview は serving process で誰にも起こされず、日次 backup が止まる"
    )


def test_master_side_status_heal_does_not_start_review():
    """StatusHeal (get_status) は master 側 (AutoStart/Verify) からも呼ばれる。
    そこで DailyReview を起こすと master に戻ってしまうので、heal は request 経路
    (heartbeat) **だけ**に置く — テキスト pin。"""
    src = (ROOT / "modules" / "demo_trader.py").read_text(encoding="utf-8")
    # get_status の本体 (次の `    def ` まで) で daily_review を起動していないこと
    start = src.index("    def get_status(self)")
    nxt = src.index("\n    def ", start + 10)
    heal_block = src[start:nxt]
    assert "_daily_review.ensure_running" not in heal_block
    assert "_daily_review.start(" not in heal_block
    assert "ensure_daily_review_running" not in heal_block
