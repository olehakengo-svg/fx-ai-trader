"""PR マージゲート (R2) — 読み手を強制する層のテスト。

2026-09-08: 直近 40 PR 実測で inline finding を持つ 35 PR の解決済み
スレッドは 0 件、review→merge 中央値 2.8 分。レビューは届いていて
読まれていなかった。本テストは「読まれない」を機械的に不可能にする層を pin する。
"""
from __future__ import annotations

import pytest

from tools.pr_review_gate import evaluate, finding_title, severity

HEAD = "a" * 40
OLD = "b" * 40


def _pr(*, reviews, threads, head=HEAD):
    return {
        "number": 1, "title": "t", "state": "OPEN",
        "commits": {"nodes": [{"commit": {"oid": head}}]},
        "reviews": {"nodes": reviews},
        "reviewThreads": {"nodes": threads},
    }


def _review(oid=HEAD, login="chatgpt-codex-connector"):
    return {"author": {"login": login}, "state": "COMMENTED",
            "submittedAt": "2026-09-08T00:00:00Z", "commit": {"oid": oid}}


def _thread(*, sev="P1", resolved=False, outdated=False,
            login="chatgpt-codex-connector", path="tools/x.py"):
    badge = f"**<sub><sub>![{sev} Badge](https://x/{sev})</sub></sub>  Fix it**"
    return {"isResolved": resolved, "isOutdated": outdated, "path": path,
            "comments": {"nodes": [{"author": {"login": login},
                                    "body": badge + "\n\ndetail",
                                    "url": "https://gh/1"}]}}


def test_no_review_blocks():
    res = evaluate(_pr(reviews=[], threads=[]))
    assert res["verdict"] == "BLOCK" and res["reason"] == "NO_REVIEW"


def test_review_on_stale_commit_blocks():
    """push 後にレビュー未再到着なら通さない (古いレビューを新 head の承認に流用しない)。"""
    res = evaluate(_pr(reviews=[_review(oid=OLD)], threads=[]))
    assert res["verdict"] == "BLOCK" and res["reason"] == "HEAD_UNREVIEWED"


def test_reviewed_without_findings_passes():
    res = evaluate(_pr(reviews=[_review()], threads=[]))
    assert res["verdict"] == "PASS"


@pytest.mark.parametrize("sev", ["P1", "P2"])
def test_open_p1_p2_blocks(sev):
    res = evaluate(_pr(reviews=[_review()], threads=[_thread(sev=sev)]))
    assert res["verdict"] == "BLOCK"
    assert res["reason"] == "OPEN_BLOCKING_FINDINGS"
    assert len(res["blocking"]) == 1


def test_p3_is_reported_but_not_blocking():
    """P3 は読み手には見せるがマージは止めない (ゲートの分母を明示)。"""
    res = evaluate(_pr(reviews=[_review()], threads=[_thread(sev="P3")]))
    assert res["verdict"] == "PASS"
    assert len(res["open_findings"]) == 1 and res["blocking"] == []


def test_resolved_or_outdated_threads_do_not_block():
    """明示 resolve (= 修正 or 反証返信) と outdated は消化済み扱い。"""
    res = evaluate(_pr(reviews=[_review()],
                       threads=[_thread(resolved=True), _thread(outdated=True)]))
    assert res["verdict"] == "PASS"


def test_non_reviewer_comment_threads_are_ignored():
    """人間の雑談スレッドをゲート対象にしない (母集団の定義を pin)。"""
    res = evaluate(_pr(reviews=[_review()], threads=[_thread(login="someone")]))
    assert res["verdict"] == "PASS"


def test_severity_and_title_parsing():
    body = "**<sub><sub>![P2 Badge](https://img/P2)</sub></sub>  Add a guard**\n\nx"
    assert severity(body) == "P2"
    assert finding_title(body) == "Add a guard"
    assert severity("no badge here") == "P?"


def test_pr226_regression_shape():
    """実データ由来の回帰 pin: PR #226 は 2 件の未解決 P1 を持ちマージ不可だった。

    実際には review 到着 1 秒後にマージされ、うち 1 件 (registry の
    requirements 欠落) が daily trigger watch を 51 エントリ 2 日間停止させた。
    """
    res = evaluate(_pr(reviews=[_review()],
                       threads=[_thread(path="knowledge-base/wiki/decisions/"
                                             "prereg-trigger-registry.json"),
                                _thread(path="tools/live_roster_attrition.py")]))
    assert res["verdict"] == "BLOCK" and len(res["blocking"]) == 2


def test_only_the_designated_reviewer_satisfies_the_gate():
    """部分一致だと `my-codex-helper` の空レビューでゲートが通る (PR #227 P2)。"""
    from tools.pr_review_gate import is_designated_reviewer

    assert is_designated_reviewer("chatgpt-codex-connector")
    assert is_designated_reviewer("Chatgpt-Codex-Connector")
    assert not is_designated_reviewer("my-codex-helper")
    assert not is_designated_reviewer("codex")
    assert not is_designated_reviewer(None)

    res = evaluate(_pr(reviews=[_review(login="my-codex-helper")], threads=[]))
    assert res["verdict"] == "BLOCK" and res["reason"] == "NO_REVIEW"


def test_impostor_thread_author_does_not_hide_a_finding():
    """スレッド側も完全一致で数える (母集団の両端を同じ規則で pin)。"""
    res = evaluate(_pr(reviews=[_review()],
                       threads=[_thread(login="my-codex-helper")]))
    assert res["verdict"] == "PASS", "非指定アカウントのスレッドは対象外"


def test_p0_is_blocking_and_unknown_severity_fails_closed():
    """P0 を P? に落として素通りさせない。判定不能は合格側に折り畳まない。

    PR #227 Codex P1: 旧 regex は `P[123]` だったので P0 が `P?` になり、
    BLOCKING からも外れて「最も重い finding があるのに PASS」になっていた。
    """
    from tools.pr_review_gate import is_blocking, severity

    assert severity("![P0 Badge](https://img/P0) x") == "P0"
    assert is_blocking("P0") and is_blocking("P1") and is_blocking("P2")
    assert is_blocking("P?"), "バッジ無しの指定レビュアー指摘は合格に倒さない"
    assert not is_blocking("P3")

    res = evaluate(_pr(reviews=[_review()], threads=[_thread(sev="P0")]))
    assert res["verdict"] == "BLOCK" and len(res["blocking"]) == 1


def test_unbadged_reviewer_thread_blocks():
    t = _thread()
    t["comments"]["nodes"][0]["body"] = "No badge, but a real concern"
    res = evaluate(_pr(reviews=[_review()], threads=[t]))
    assert res["verdict"] == "BLOCK"


def test_fetch_pr_paginates_review_threads(monkeypatch):
    """100 スレッドを超えた PR で 2 ページ目の P1 を落とさない (PR #227 P2)。"""
    import json as _json
    import subprocess as _sp

    from tools import pr_review_gate as g

    pages = [
        {"pageInfo": {"hasNextPage": True, "endCursor": "c1"},
         "nodes": [_thread(sev="P3")]},
        {"pageInfo": {"hasNextPage": False, "endCursor": None},
         "nodes": [_thread(sev="P1")]},
    ]
    calls = {"n": 0}

    class _R:
        returncode = 0
        stderr = ""

        def __init__(self, body):
            self.stdout = body

    def fake_run(args, **kw):
        if args[:2] == ["gh", "repo"]:
            return _R(_json.dumps({"owner": {"login": "o"}, "name": "r"}))
        page = pages[calls["n"]]
        calls["n"] += 1
        return _R(_json.dumps({"data": {"repository": {"pullRequest": {
            "number": 1, "title": "t", "state": "OPEN",
            "commits": {"nodes": [{"commit": {"oid": HEAD}}]},
            "reviews": {"nodes": [_review()]},
            "reviewThreads": page}}}}))

    monkeypatch.setattr(_sp, "run", fake_run)
    pr = g.fetch_pr(1)
    assert calls["n"] == 2, "2 ページ目を取りに行っていない"
    assert len(pr["reviewThreads"]["nodes"]) == 2
    assert evaluate(pr)["verdict"] == "BLOCK", "2 ページ目の P1 が届いていない"


def test_fetch_pr_fails_closed_when_pages_never_end(monkeypatch):
    """辿りきれないときに「見えた範囲で合格」にしない。"""
    import json as _json
    import subprocess as _sp

    import pytest as _pytest

    from tools import pr_review_gate as g

    class _R:
        returncode = 0
        stderr = ""

        def __init__(self, body):
            self.stdout = body

    def fake_run(args, **kw):
        if args[:2] == ["gh", "repo"]:
            return _R(_json.dumps({"owner": {"login": "o"}, "name": "r"}))
        return _R(_json.dumps({"data": {"repository": {"pullRequest": {
            "number": 1, "title": "t", "state": "OPEN",
            "commits": {"nodes": [{"commit": {"oid": HEAD}}]},
            "reviews": {"nodes": [_review()]},
            "reviewThreads": {"pageInfo": {"hasNextPage": True,
                                           "endCursor": "c"},
                              "nodes": []}}}}}))

    monkeypatch.setattr(_sp, "run", fake_run)
    with _pytest.raises(RuntimeError):
        g.fetch_pr(1)
