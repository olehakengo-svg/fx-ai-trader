"""evaluated_candidates.bar_time が live 経路で NULL にならないことを固定 (rule:R3)。

2026-08-24: log_candidates の call site が `bar_time=bar_time` を渡していたが、
live 経路 (demo_trader._tick -> compute_fn(df, tf, sr, symbol)) は bar_time を
渡さないため live 行は全て NULL だった (実測 hull_donchian_fade 30日 1,139 行が
全て NULL)。bar_time は C1 監査テーブルで唯一 bar 粒度への正規化を可能にする列で、
NULL だと「1 バー x 30 poll」と「30 本の別バー」が区別できず funnel 分解が
原理的に計算できない。2026-08-09 の ctx.hour_utc 凍結 (PR #168) と同一の
call-site 欠落パターン = 4 例目。
"""

import ast
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _log_candidates_call():
    """app.py 内の log_candidates 呼び出しノードを返す。"""
    import app as app_module

    src = inspect.getsource(app_module)
    tree = ast.parse(src)
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = getattr(fn, "id", None) or getattr(fn, "attr", None)
        if name in ("_log_cands", "log_candidates"):
            calls.append(node)
    return calls


def test_bar_time_is_not_the_unpassed_live_parameter():
    """live で常に None になる素の `bar_time` を渡していないこと。"""
    calls = _log_candidates_call()
    assert calls, "log_candidates の呼び出しが app.py に見つからない"
    for call in calls:
        for kw in call.keywords:
            if kw.arg == "bar_time":
                assert not (
                    isinstance(kw.value, ast.Name) and kw.value.id == "bar_time"
                ), (
                    "log_candidates(bar_time=bar_time) は live で必ず NULL になる。"
                    "_dt_bar_dt (bar_time or df.index[-1], UTC 正規化) を渡すこと"
                )


def test_bar_time_uses_derived_bar_timestamp():
    """PR #168 が確立した _dt_bar_dt fallback を使っていること。"""
    calls = _log_candidates_call()
    passed = [
        kw.value.id
        for call in calls
        for kw in call.keywords
        if kw.arg == "bar_time" and isinstance(kw.value, ast.Name)
    ]
    assert "_dt_bar_dt" in passed, (
        f"bar_time に渡されている名前: {passed} — _dt_bar_dt を期待"
    )


def test_logged_bar_time_round_trips_to_db(tmp_path):
    """log_candidates が非 None bar_time を実際に永続化することの行動証拠。"""
    from datetime import datetime, timezone
    import sqlite3
    from dataclasses import dataclass

    from modules.candidate_logger import init_candidates_table, log_candidates

    @dataclass
    class _C:
        entry_type: str
        signal: str
        confidence: int
        score: float

    db = str(tmp_path / "c.db")
    init_candidates_table(db)
    bar = datetime(2026, 8, 24, 4, 0, tzinfo=timezone.utc)
    c = [_C("hull_donchian_fade", "BUY", 50, 3.8)]
    log_candidates(db, c, c[0], instrument="EUR_USD", bar_time=bar)

    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT bar_time FROM evaluated_candidates").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] is not None
    assert "2026-08-24" in rows[0][0]
