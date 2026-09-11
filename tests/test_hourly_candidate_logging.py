"""HourlyEngine 経路の C1 candidate logging を固定 (rule:R3, 2026-09-11).

発見経路: ps 席供給 30d 再計測の正式 verdict (REJECT, capture 20.6%) を受けて
親監査 §8 の帰属を計算しようとしたところ、hourly 経路には
``evaluated_candidates`` の call site が**存在しない**ことが判明した。
`_dt_engine` (DaytradeEngine) 経路だけが 2026-04-28 以来書かれており、
本番 31d summary に `price_shock_rev_*` が 1 行も無い — 観測 7 行を出した
EUR_GBP / AUD_JPY すら不在。

結果 NZD_JPY / EUR_AUD / USD_CAD の「design 17 本に対する観測ゼロ」を
上流 (evaluate_all が候補を出していない) と下流 (候補は出たが _tick_entry で
落ちた) に帰属できない。本テストは計装の存在と live-safe な契約を pin する。

SSOT: knowledge-base/wiki/analyses/ps-seat-supply-remeasure-2026-09-10.md §7
"""

import ast
import inspect
import textwrap
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest


@dataclass
class _FakeCandidate:
    entry_type: str
    signal: str
    confidence: int
    score: float


def _hourly_fn_source() -> str:
    import app as app_module

    return inspect.getsource(app_module.compute_hourly_signal)


def _hourly_log_calls() -> list:
    """compute_hourly_signal 内の log_candidates 呼び出しノード。"""
    tree = ast.parse(textwrap.dedent(_hourly_fn_source()))
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        if name in ("_log_cands_h1", "_log_cands", "log_candidates"):
            calls.append(node)
    return calls


class TestCallSiteExists:
    def test_hourly_path_logs_candidates(self):
        """HourlyEngine 経路に candidate logging が敷かれていること。

        これが無いと ps 席 (daytrade_1h_* surface slot) の funnel
        「候補 -> select_best -> trade」が原理的に観測不能になる。
        """
        assert _hourly_log_calls(), (
            "compute_hourly_signal に log_candidates 呼び出しが無い — "
            "ps 席の供給帰属 (親監査 §8) が計算できない"
        )

    def test_logs_the_full_candidate_list_not_just_the_winner(self):
        """敗者を含む candidates 全体を渡すこと (select_best の選択バイアス除去)。"""
        calls = _hourly_log_calls()
        first_args = [
            getattr(call.args[1], "id", None)
            for call in calls
            if len(call.args) >= 2
        ]
        assert "candidates" in first_args, (
            f"log_candidates に渡している候補リスト: {first_args} — "
            "`candidates` (evaluate_all の全出力) を期待。`best` や "
            "`shadow_emits` だけでは敗者が観測できない"
        )

    def test_logged_before_the_best_is_none_early_return(self):
        """`best is None` の早期 return より前に記録すること。

        select_best が None を返すのは候補ゼロのときだけなので実害は無いが、
        順序が逆転すると将来 select_best が「候補はあるが選ばない」分岐を
        得たときに敗者が無言で消える。
        """
        src = textwrap.dedent(_hourly_fn_source())
        log_pos = src.find("_log_cands_h1(")
        ret_pos = src.find("if best is None:")
        assert log_pos != -1 and ret_pos != -1
        assert log_pos < ret_pos, (
            "log_candidates が `if best is None:` の早期 return より後にある"
        )


class TestLiveSafetyContract:
    def test_call_is_wrapped_in_try_except(self):
        """計装の失敗が trade flow を壊さないこと (DTE 経路と同一契約)。"""
        tree = ast.parse(textwrap.dedent(_hourly_fn_source()))
        guarded = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Call):
                    continue
                name = getattr(sub.func, "id", None) or getattr(sub.func, "attr", None)
                if name == "_log_cands_h1":
                    guarded = True
        assert guarded, "log_candidates 呼び出しが try/except で保護されていない"

    def test_bar_time_is_not_the_unpassed_live_parameter(self):
        """live で常に None になる素の `bar_time` を渡していないこと。

        live 経路 demo_trader._tick -> compute_fn(df, tf, sr, symbol) は
        bar_time を渡さない (2026-08-24 に DTE 側で実証済みの 4 例目パターン)。
        """
        for call in _hourly_log_calls():
            for kw in call.keywords:
                if kw.arg == "bar_time":
                    assert not (
                        isinstance(kw.value, ast.Name) and kw.value.id == "bar_time"
                    ), (
                        "log_candidates(bar_time=bar_time) は live で必ず NULL。"
                        "df.index[-1] fallback を経た派生値を渡すこと"
                    )

    def test_bar_time_uses_derived_timestamp(self):
        passed = [
            kw.value.id
            for call in _hourly_log_calls()
            for kw in call.keywords
            if kw.arg == "bar_time" and isinstance(kw.value, ast.Name)
        ]
        assert "_h1_bar_dt" in passed, (
            f"bar_time に渡されている名前: {passed} — _h1_bar_dt を期待"
        )


class TestBehaviouralRoundTrip:
    """AST pin だけだと「呼んでいるが書けていない」を見逃すので行動証拠も置く。"""

    def test_log_candidates_persists_hourly_shaped_rows(self, tmp_path):
        from modules.candidate_logger import init_candidates_table, log_candidates

        db = str(tmp_path / "c1.db")
        assert init_candidates_table(db) is True

        seat = _FakeCandidate("price_shock_rev_eur_aud_h1_long", "BUY", 60, 1.0)
        guest = _FakeCandidate("donchian_momentum_breakout", "SELL", 55, 7.3)
        bar = datetime(2026, 9, 10, 13, 0, tzinfo=timezone.utc)

        assert log_candidates(db, [seat, guest], seat,
                              instrument="EUR_AUD", tf="1h", bar_time=bar) is True

        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT strategy_name, tf, bar_time, selected, selected_strategy"
            " FROM evaluated_candidates ORDER BY strategy_name"
        ).fetchall()
        conn.close()

        assert len(rows) == 2, "敗者 (guest) も記録されること"
        names = {r[0] for r in rows}
        assert "price_shock_rev_eur_aud_h1_long" in names
        assert "donchian_momentum_breakout" in names
        assert all(r[1] == "1h" for r in rows)
        assert all(r[2] is not None for r in rows), "bar_time が NULL"
        # 席優先 select (PR #172 §7(a)) の結果が selected に載ること
        seat_row = next(r for r in rows if r[0].startswith("price_shock_rev"))
        assert seat_row[3] == 1
        assert seat_row[4] == "price_shock_rev_eur_aud_h1_long"

    def test_empty_candidate_list_is_a_noop(self, tmp_path):
        """候補ゼロの tick で行を増やさないこと (書込み量の床)。"""
        from modules.candidate_logger import init_candidates_table, log_candidates

        db = str(tmp_path / "c1.db")
        init_candidates_table(db)
        assert log_candidates(db, [], None, instrument="EUR_AUD", tf="1h") is True
        conn = sqlite3.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM evaluated_candidates").fetchone()[0]
        conn.close()
        assert n == 0


class TestCounterfactual:
    """pin が実際に落ちることを確認する (counterfactual、2026-08-30 教訓)。"""

    def test_pin_fails_when_call_site_removed(self):
        """呼び出しを消した source では finder が空を返すこと。

        pin が「常に真」でないことの証拠。call は複数行にまたがるので
        行削除ではなく識別子の改名で不在を作る (行削除だと SyntaxError に
        なり、pin の失敗と構文エラーが見分けられない)。
        """
        src = textwrap.dedent(_hourly_fn_source())
        assert "_log_cands_h1(" in src
        removed = src.replace("_log_cands_h1", "_instrumentation_deleted")
        tree = ast.parse(removed)
        found = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and (getattr(n.func, "id", None) or getattr(n.func, "attr", None))
            in ("_log_cands_h1", "_log_cands", "log_candidates")
        ]
        assert not found, "counterfactual 構築に失敗 (除去後も呼び出しが残った)"


class TestSeatCoverage:
    def test_all_five_price_shock_seats_are_hourly_engine_members(self):
        """計装が 5 席すべてを覆うこと — 席が engine 外にいたら意味がない。"""
        from strategies.hourly import HourlyEngine

        names = {getattr(s, "name", None) for s in HourlyEngine().strategies}
        for seat in (
            "price_shock_rev_eur_gbp_h1_long",
            "price_shock_rev_aud_jpy_h1_long",
            "price_shock_rev_nzd_jpy_h1_long",
            "price_shock_rev_eur_aud_h1_long",
            "price_shock_rev_usd_cad_h1_long",
        ):
            assert seat in names, f"{seat} が HourlyEngine に登録されていない"
