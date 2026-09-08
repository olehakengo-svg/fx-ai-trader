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
