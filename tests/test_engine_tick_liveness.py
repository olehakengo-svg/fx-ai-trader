"""エンジン生存計装 (tick 前進の実時刻) の契約テスト — rule:R3, 2026-08-28.

背景: watcher は 2026-08-27 時点でエンジン本体の生存を **一切**見ていな
かった。``main_loop_alive`` は ``Thread.is_alive()`` で「生きたまま詰まって
いる」を alive と報告し、``tick_counts`` は絶対値しか出ないため単発観測では
前進が判定できず、``candidate_stagnation`` は HTF Hard Block 後の行を数える
ので「全候補ブロック」と「エンジン死亡」を区別できない (08-27 の 73 分
ゼロ行は実際に benign だった)。

本テストが固定する契約:
- ``_record_tick`` が **唯一**の tick カウンタ更新経路である (call-site 欠落
  の構造的防止 — 本プロジェクトはこの型を 4 回踏んでいる)
- カウンタとタイムスタンプが**不可分**に更新される
- ``never_ticked`` / ``not_running`` / ``ok`` を折り畳まない
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import pytest

from modules.demo_trader import DemoTrader

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / "modules" / "demo_trader.py").read_text(encoding="utf-8")



def _function_body(src: str, name: str) -> str:
    """``def <name>`` から次の同インデント ``def`` 直前までを返す。"""
    m = re.search(rf"^(\s*)def {re.escape(name)}\(", src, re.M)
    assert m, f"{name} が見つからない"
    indent = m.group(1)
    rest = src[m.end():]
    nxt = re.search(rf"^{indent}def ", rest, re.M)
    return src[m.start(): m.end() + (nxt.start() if nxt else len(rest))]


@pytest.fixture
def trader():
    """__init__ は OANDA / DB / スレッドを起こすので、計装だけを対象に
    生のインスタンスを組む (payload は self._runners と属性しか読まない)。"""
    t = DemoTrader.__new__(DemoTrader)
    t._runners = {}
    return t


def _run(trader, *modes):
    trader._runners = {m: {"running": True} for m in modes}


class TestRecordTickIsTheOnlyWriter:
    def test_counter_and_timestamp_update_together(self, trader):
        """increment とタイムスタンプが別経路だと片方だけ更新されて壊れる。
        不可分であることを固定する。"""
        before = time.time()
        trader._record_tick("scalp")
        assert trader._tick_counts["scalp"] == 1
        assert trader._tick_last_advance["scalp"] >= before

    def test_repeated_ticks_accumulate(self, trader):
        for _ in range(3):
            trader._record_tick("daytrade")
        assert trader._tick_counts["daytrade"] == 3

    def test_returns_counter_for_caller_logging(self, trader):
        tc = trader._record_tick("daytrade")
        assert tc is trader._tick_counts

    def test_no_other_call_site_increments_the_counter(self):
        """**構造 pin**: ``_tick_counts`` を直接 +1 するコードが
        ``_record_tick`` の外に生えたら落ちる。

        本プロジェクトは「同じ 2 行を各経路にコピーし、新しい経路で片方
        だけ忘れる」型のバグを 4 回踏んでいる (PR #168 ctx.hour_utc 定数
        固着 123 日 / PR #204 bar_time 全行 NULL 等)。増分経路を 1 箇所に
        集約しただけでは将来の追加を防げないので、テストで固定する。
        """
        body = _function_body(SRC, "_record_tick")
        assert "self._tick_counts = _tc" in body, "_record_tick 本体が見つからない"
        outside = SRC.replace(body, "")
        increments = re.findall(
            r"^\s*(\w+)\[mode\]\s*=\s*\1\.get\(mode,\s*0\)\s*\+\s*1", outside, re.M
        )
        assert increments == [], (
            f"tick カウンタを直接 +1 している箇所が {len(increments)} 件ある。"
            f"_record_tick() を経由させること"
        )

    def test_record_tick_is_referenced_by_every_tick_path(self):
        """呼び出し側が消えたら (= 計装が外れたら) 落ちる。"""
        assert SRC.count("self._record_tick(mode)") == 2


class TestEngineTickPayload:
    def test_running_but_never_ticked_reports_since_process_start(self, trader):
        """起動直後は正常だが、起動失敗も同じ形。None を返して黙って
        skip させず、経過秒を出して呼び出し側が閾値で切れるようにする。"""
        _run(trader, "scalp")
        trader._main_loop_start_ts = time.time() - 42
        p = trader._engine_tick_payload()
        assert p["engine_tick_status"] == "never_ticked"
        assert 41 <= p["engine_tick_age_sec"] <= 60

    def test_no_running_modes_is_not_running_not_stall(self, trader):
        """全モード停止中は「止まっている」ではなく「止められている」。
        資格 (eligible) と実状態 (effective) を混同しない。"""
        trader._runners = {"scalp": {"running": False}}
        p = trader._engine_tick_payload()
        assert p["engine_tick_status"] == "not_running"
        assert p["engine_tick_age_sec"] is None
        assert p["engine_tick_running_modes"] == 0

    def test_age_is_newest_advance_across_running_modes(self, trader):
        """engine は単一 main loop が全モードを順に回すので、engine レベル
        の生存指標は **最も新しい** 前進。最も古いモードで測ると、interval
        60 秒のモードの都合で engine が死にかけに見える。"""
        _run(trader, "scalp", "daytrade_1h")
        now = time.time()
        trader._tick_last_advance = {"scalp": now - 5, "daytrade_1h": now - 55}
        p = trader._engine_tick_payload()
        assert p["engine_tick_status"] == "ok"
        assert 4.5 <= p["engine_tick_age_sec"] <= 7
        assert p["engine_tick_stalest_mode"] == "daytrade_1h"
        assert 54 <= p["engine_tick_stalest_age_sec"] <= 58

    def test_stopped_modes_do_not_drag_the_age(self, trader):
        """止めたモードのタイムスタンプは古いまま残る。走っているモード
        だけで測らないと、user が 1 モード止めた瞬間に永久発火する。"""
        trader._runners = {"scalp": {"running": True},
                           "daytrade_xau": {"running": False}}
        now = time.time()
        trader._tick_last_advance = {"scalp": now - 3, "daytrade_xau": now - 90000}
        p = trader._engine_tick_payload()
        assert p["engine_tick_status"] == "ok"
        assert p["engine_tick_age_sec"] < 10
        assert p["engine_tick_stalest_mode"] == "scalp"
        assert p["engine_tick_running_modes"] == 1

    def test_a_newly_started_mode_is_never_ticked_not_ok(self, trader):
        """走っているが 1 度も tick していないモードは ages に入らない。
        他モードが動いていれば engine は ok。"""
        _run(trader, "scalp", "brand_new_mode")
        trader._tick_last_advance = {"scalp": time.time() - 2}
        p = trader._engine_tick_payload()
        assert p["engine_tick_status"] == "ok"
        assert p["engine_tick_running_modes"] == 2

    def test_payload_keys_always_present(self, trader):
        """欠落 key は下流で silent skip を生む (live_n_stagnation が
        126 日 no-op だった直接原因)。"""
        for setup in (lambda: None, lambda: _run(trader, "scalp")):
            trader._runners = {}
            trader._tick_last_advance = {}
            setup()
            p = trader._engine_tick_payload()
            assert "engine_tick_status" in p
            assert "engine_tick_age_sec" in p
            assert "engine_tick_running_modes" in p

    def test_payload_survives_broken_runners(self, trader):
        """_runners が壊れていても status 全体を落とさない。"""
        trader._runners = None
        p = trader._engine_tick_payload()
        assert p["engine_tick_status"] == "not_running"

    def test_namespaced_keys_do_not_collide_with_generic_status(self):
        """PR #207 と同じ理由: 汎用 ``error``/``now`` と衝突する名前を
        使うと「計装の失敗」が「status 全体の失敗」に化ける。"""
        assert "engine_tick_" in SRC
        assert re.search(r'"engine_tick_status"', SRC)

    def test_status_payload_includes_engine_tick(self):
        """get_status() から実際に配線されている (write-only にしない)。"""
        assert "**self._engine_tick_payload()," in SRC


class TestNeverStartedMainLoopIsNotSilent:
    """**最悪ケースの無検知を塞ぐ** — rule:R3, 2026-08-28 (実測で発見).

    `_main_loop_start_ts` は `_main_loop` の先頭で設定されるので、**main loop
    スレッドが一度も起動しなかった場合には存在しない**。ところが `start()` は
    `_runners[mode]["running"] = True` を先に立てるため、「モードは running
    なのに tick ゼロ」という**この検知器が存在する理由そのもの**の状態が作れる。

    初版はこのとき `engine_tick_age_sec = None` を返し、watcher が
    `engine_tick_missing` (= NOTIFY_NEVER、web 旧版と同じ扱い) に分類して
    **完全に沈黙**した。実際に本番相当の payload を組んで確認した。
    """

    def test_payload_always_returns_a_number_when_never_ticked(self, trader):
        _run(trader, "scalp")
        assert not hasattr(trader, "_main_loop_start_ts")
        p = trader._engine_tick_payload()
        assert p["engine_tick_status"] == "never_ticked"
        assert isinstance(p["engine_tick_age_sec"], float), (
            "None を返すと watcher が version skew と誤分類して沈黙する"
        )

    def test_explicit_start_ts_still_wins(self, trader):
        _run(trader, "scalp")
        trader._main_loop_start_ts = time.time() - 300
        p = trader._engine_tick_payload()
        assert 299 <= p["engine_tick_age_sec"] <= 320
