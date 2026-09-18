"""PR マージゲート — inline review thread を読むこと (2026-09-18、rule:R3)。

第 3 の空振り形状: connector は P1/P2 を **inline review comment** で投げるが、
`gh pr view --json reviews,comments` にはその本文が入らない。実測 (2026-09-18、
PR #249/#250/#253/#256/#257/#258/#261/#263/#264/#265) では inline に 28 件の
P1/P2 があり top-level review 本文には 0 件 = findings 軸は導入以来ずっと恒真だった。
"""
from __future__ import annotations

import pytest

from tools import pr_review_gate as gate

CONNECTOR = "chatgpt-codex-connector"

P2_BODY = (
    "**<sub><sub>![P2 Badge](https://img.shields.io/badge/P2-yellow)</sub></sub>  "
    "Carry non-business-day conferences into the next business day**\n\n"
    "`days` contains only business days, ...")


def _thread(*, body=P2_BODY, login=CONNECTOR, resolved=False, outdated=False,
            path="tools/x.py", created="2026-09-18T02:11:00Z"):
    return {"isResolved": resolved, "isOutdated": outdated, "path": path,
            "comments": {"nodes": [{"author": {"login": login}, "body": body,
                                    "url": "https://github.com/x#r1",
                                    "createdAt": created}]}}


def _payload(*, reviews=(), comments=(), commits=(), head="a" * 40):
    return {"reviews": list(reviews), "comments": list(comments),
            "commits": list(commits), "headRefOid": head}


# --- thread_findings ---------------------------------------------------------
def test_open_connector_thread_is_a_finding():
    out = gate.thread_findings([_thread()])
    assert len(out) == 1
    assert out[0]["inline"] is True
    assert out[0]["path" if "path" in out[0] else "line"]
    assert "tools/x.py" in out[0]["line"]
    assert "Carry non-business-day" in out[0]["line"]
    assert "![P2 Badge]" not in out[0]["line"]      # バッジ markdown は落とす


@pytest.mark.parametrize("kw", [{"resolved": True}, {"outdated": True}])
def test_resolved_or_outdated_thread_is_not_blocking(kw):
    assert gate.thread_findings([_thread(**kw)]) == []


def test_non_connector_thread_is_ignored():
    assert gate.thread_findings([_thread(login="some-human")]) == []


def test_thread_without_severity_marker_is_ignored():
    assert gate.thread_findings([_thread(body="nit: rename this variable")]) == []


def test_empty_thread_does_not_crash():
    assert gate.thread_findings([{"comments": {"nodes": []}}, {}]) == []


# --- evaluate wiring ---------------------------------------------------------
def test_inline_finding_blocks_even_when_toplevel_review_is_clean(monkeypatch):
    """回帰の本体: これが旧実装の恒真 exit 0 だった形状。"""
    payload = _payload(reviews=[{"author": {"login": CONNECTOR},
                                 "body": "Didn't find any major issues.",
                                 "submittedAt": "2026-09-18T02:11:00Z"}])
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    monkeypatch.setattr(gate, "fetch_review_threads", lambda pr: [_thread()])
    code, msg = gate.evaluate(265)
    assert code == 3, msg
    assert "未消化" in msg
    assert "tools/x.py" in msg


def test_inline_finding_acked_by_later_commit_passes(monkeypatch):
    payload = _payload(
        reviews=[{"author": {"login": CONNECTOR}, "body": "see comments",
                  "submittedAt": "2026-09-18T02:11:00Z"}],
        commits=[{"committedDate": "2026-09-18T02:20:00Z"}])
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    monkeypatch.setattr(gate, "fetch_review_threads", lambda pr: [_thread()])
    code, msg = gate.evaluate(265)
    assert code == 0, msg
    assert "消化済み" in msg


def test_inline_finding_alone_counts_as_review_arrival(monkeypatch):
    """review オブジェクトが無くても inline finding があれば到着している。"""
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: _payload())
    monkeypatch.setattr(gate, "fetch_review_threads", lambda pr: [_thread()])
    assert gate.evaluate(265)[0] == 3


def test_thread_fetch_failure_is_exit_4_not_pass(monkeypatch):
    """『取れなかった』を『指摘なし』に折り畳まない (fail-closed)。"""
    payload = _payload(reviews=[{"author": {"login": CONNECTOR},
                                 "body": "LGTM",
                                 "submittedAt": "2026-09-18T02:11:00Z"}])
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    monkeypatch.setattr(gate, "fetch_review_threads", lambda pr: None)
    code, msg = gate.evaluate(265)
    assert code == 4, msg
    assert "折り畳まない" in msg


def test_clean_pass_message_states_what_was_searched(monkeypatch):
    """『指摘なし』は探した範囲を名乗る — 恒真メッセージの再発防止。"""
    payload = _payload(reviews=[{"author": {"login": CONNECTOR}, "body": "LGTM",
                                 "submittedAt": "2026-09-18T02:11:00Z"}])
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    monkeypatch.setattr(gate, "fetch_review_threads", lambda pr: [])
    code, msg = gate.evaluate(265)
    assert code == 0
    assert "inline thread" in msg


# --- 構造 pin ---------------------------------------------------------------
def test_evaluate_actually_calls_the_thread_fetcher(monkeypatch):
    """配線が外れたら落ちる pin (thread を読まない実装への逆戻り防止)。"""
    called = []
    payload = _payload(reviews=[{"author": {"login": CONNECTOR}, "body": "LGTM",
                                 "submittedAt": "2026-09-18T02:11:00Z"}])
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)

    def _spy(pr):
        called.append(pr)
        return []

    monkeypatch.setattr(gate, "fetch_review_threads", _spy)
    gate.evaluate(265)
    assert called == [265]


# --- Codex P2 (PR #267、自分自身のゲートが拾った): ページング ---------------
class _Proc:
    def __init__(self, stdout):
        self.stdout = stdout
        self.returncode = 0


def _page(nodes, *, has_next, cursor=None):
    import json
    return _Proc(json.dumps({"data": {"repository": {"pullRequest": {
        "reviewThreads": {
            "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
            "nodes": nodes}}}}}))


@pytest.fixture
def _repo(monkeypatch):
    monkeypatch.setattr(gate, "_gh_repo", lambda: ("o", "r"))


def test_all_pages_are_fetched(monkeypatch, _repo):
    pages = [_page([_thread(path="a.py")], has_next=True, cursor="c1"),
             _page([_thread(path="b.py")], has_next=True, cursor="c2"),
             _page([_thread(path="c.py")], has_next=False)]
    seen = []

    def _run(cmd, **kw):
        seen.append(next((a.split("=", 1)[1] for a in cmd if a.startswith("after=")), None))
        return pages.pop(0)

    monkeypatch.setattr(gate.subprocess, "run", _run)
    th = gate.fetch_review_threads(1)
    assert len(th) == 3
    assert [t["path"] for t in th] == ["a.py", "b.py", "c.py"]
    assert seen == ["", "c1", "c2"]     # 1 ページ目は cursor 無し


def test_finding_on_a_later_page_still_blocks(monkeypatch, _repo):
    """P2 の失敗シナリオそのもの: 2 ページ目にだけ finding がある。"""
    pages = [_page([_thread(body="nit", path="clean.py")], has_next=True, cursor="c1"),
             _page([_thread(path="late.py")], has_next=False)]
    monkeypatch.setattr(gate.subprocess, "run", lambda cmd, **kw: pages.pop(0))
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: _payload(
        reviews=[{"author": {"login": CONNECTOR}, "body": "Didn't find any major issues.",
                  "submittedAt": "2026-09-18T02:11:00Z"}]))
    code, msg = gate.evaluate(1)
    assert code == 3, msg
    assert "late.py" in msg


def test_has_next_page_without_cursor_is_fail_closed(monkeypatch, _repo):
    monkeypatch.setattr(gate.subprocess, "run",
                        lambda cmd, **kw: _page([_thread()], has_next=True, cursor=None))
    assert gate.fetch_review_threads(1) is None


def test_page_limit_exhaustion_is_fail_closed(monkeypatch, _repo):
    """打ち切ったリストを『全部見た』と名乗らせない。"""
    monkeypatch.setattr(gate.subprocess, "run",
                        lambda cmd, **kw: _page([_thread()], has_next=True, cursor="c"))
    assert gate.fetch_review_threads(1) is None


def test_repo_resolution_failure_is_fail_closed(monkeypatch):
    monkeypatch.setattr(gate, "_gh_repo", lambda: None)
    assert gate.fetch_review_threads(1) is None
