"""PR マージゲート (R2) — 読み手を強制する層のテスト。

2026-09-08 実測 (PR #227、[[pr-review-gate-2026-09-08]]): 直近 40 PR で
inline finding を持つ 35 PR の解決済みスレッドは 0 件、review→merge 中央値
2.8 分。レビューは届いていて読まれていなかった。本テストは main に着地した
#231 版実装 (`evaluate(pr) -> (code, msg)`、exit 0/2/3/4) の性質を pin する。

⚠️ #227 版テスト (GraphQL reviewThreads / P0 fail-closed / ページング /
HEAD_UNREVIEWED 前提の 10+ 本) は実装が異なるため盲目移植していない —
それらの性質は #231 版には存在しない (採否は別途判断、決裁文書に記録済み)。
"""
from __future__ import annotations

import pytest

from tools import pr_review_gate as gate

CONNECTOR = "chatgpt-codex-connector"


def _payload(*, reviews=(), comments=(), commits=()):
    return {"reviews": list(reviews), "comments": list(comments),
            "commits": list(commits)}


def _review(body: str, *, login: str = CONNECTOR,
            submitted: str = "2026-09-08T00:00:00Z"):
    return {"author": {"login": login}, "body": body,
            "submittedAt": submitted}


def _comment(body: str, *, login: str = CONNECTOR,
             created: str = "2026-09-08T00:00:00Z"):
    return {"author": {"login": login}, "body": body, "createdAt": created}


# ---------------------------------------------------------------- evaluate

def test_gh_failure_is_exit_4_not_pass(monkeypatch):
    """「取れなかった」を「指摘なし」に折り畳まない (fail closed)。"""
    monkeypatch.setattr(gate, "_gh_pr_json", lambda pr, fields: None)
    code, msg = gate.evaluate(1)
    assert code == 4
    assert "折り畳まない" in msg


def test_no_review_arrival_is_exit_2(monkeypatch):
    """レビュー未到着なら「待て」— 古い承認も無いのに通さない。"""
    monkeypatch.setattr(gate, "_gh_pr_json", lambda pr, fields: _payload())
    code, _ = gate.evaluate(1)
    assert code == 2


def test_review_without_findings_is_exit_0(monkeypatch):
    monkeypatch.setattr(
        gate, "_gh_pr_json",
        lambda pr, fields: _payload(reviews=[_review("LGTM, no issues")]))
    code, _ = gate.evaluate(1)
    assert code == 0


@pytest.mark.parametrize("sev", ["P1", "P2"])
def test_unacked_p1_p2_findings_block_with_exit_3(monkeypatch, sev):
    monkeypatch.setattr(
        gate, "_gh_pr_json",
        lambda pr, fields: _payload(
            reviews=[_review(f"{sev} missing guard in tools/x.py")]))
    code, msg = gate.evaluate(1)
    assert code == 3
    assert "未消化" in msg


def test_p3_only_review_is_not_blocking(monkeypatch):
    """P3 は非ブロッキング (ゲートの分母 = P1/P2 のみ、CLAUDE.md 節と一致)。"""
    monkeypatch.setattr(
        gate, "_gh_pr_json",
        lambda pr, fields: _payload(reviews=[_review("P3 style nit only")]))
    code, _ = gate.evaluate(1)
    assert code == 0


def test_commit_after_review_arrival_counts_as_digestion(monkeypatch):
    monkeypatch.setattr(
        gate, "_gh_pr_json",
        lambda pr, fields: _payload(
            reviews=[_review("P1 broken thing")],
            commits=[{"committedDate": "2026-09-08T01:00:00Z"}]))
    code, msg = gate.evaluate(1)
    assert code == 0
    assert "消化済み" in msg


def test_commit_before_review_arrival_does_not_count(monkeypatch):
    """到着**前**の commit を消化と読まない — 消化は必ずレビュー到着より後。"""
    monkeypatch.setattr(
        gate, "_gh_pr_json",
        lambda pr, fields: _payload(
            reviews=[_review("P1 broken thing")],
            commits=[{"committedDate": "2026-09-07T23:00:00Z"}]))
    code, _ = gate.evaluate(1)
    assert code == 3


def test_review_ack_comment_after_arrival_counts_as_dismiss(monkeypatch):
    monkeypatch.setattr(
        gate, "_gh_pr_json",
        lambda pr, fields: _payload(
            reviews=[_review("P2 questionable default")],
            comments=[_comment("review-ack: 意図的 — 既定値は SSOT 側で検証済み",
                               login="goto",
                               created="2026-09-08T01:00:00Z")]))
    code, _ = gate.evaluate(1)
    assert code == 0


def test_review_ack_before_arrival_does_not_count(monkeypatch):
    """事前に置いた review-ack で将来の finding を先回り消化させない。"""
    monkeypatch.setattr(
        gate, "_gh_pr_json",
        lambda pr, fields: _payload(
            reviews=[_review("P1 real issue")],
            comments=[_comment("review-ack: 先回り",
                               created="2026-09-07T00:00:00Z")]))
    code, _ = gate.evaluate(1)
    assert code == 3


# ---------------------------------------------------- collect_findings 母集団

def test_non_reviewer_comments_are_not_the_gate_population():
    """人間の雑談コメントに P1 と書いてあってもゲート対象にしない。"""
    findings, arrived = gate.collect_findings(
        _payload(comments=[_comment("P1 これは雑談です", login="goto")]))
    assert findings == [] and arrived is False


def test_connector_finding_lines_are_collected_with_arrival_flag():
    findings, arrived = gate.collect_findings(
        _payload(reviews=[_review("intro\nP1 missing requirements\nP3 nit")]))
    assert arrived is True
    assert len(findings) == 1
    assert "P1" in findings[0]["line"]


def test_pr226_regression_shape():
    """実データ由来の回帰 pin: PR #226 は 2 件の未解決 P1 を持ちマージ不可だった。

    実際には review 到着 1 秒後にマージされ、うち 1 件 (registry の
    requirements 欠落) が daily trigger watch を 51 エントリ 2 日間停止させた
    ([[pr-review-gate-2026-09-08]] §3)。
    """
    payload = _payload(reviews=[_review(
        "P1 prereg-trigger-registry.json: artifact_presence requires "
        "`requirements`\n"
        "P1 live_roster_attrition.py: D 分類は現在の昇格集合しか見ていない")])
    findings, arrived = gate.collect_findings(payload)
    assert arrived and len(findings) == 2
    assert not gate.latest_ack(payload, max(f["submitted"] for f in findings))


# ------------------------------------------------------------- 既知の限界の pin

def test_known_limitation_reviewer_match_is_partial():
    """#231 版の限界を**限界として** pin する (黙って仕様に昇格させない)。

    REVIEWER_PAT は部分一致なので `my-codex-helper` の空レビューでも
    「到着」を満たす。#227 版は完全一致 (`is_designated_reviewer`) で
    これを塞いでいた — 採用可否は別途判断 ([[pr-review-gate-2026-09-08]]
    冒頭の経緯追記)。この挙動が**変わったら** (= 完全一致へ強化されたら)
    本テストを更新し、決裁文書の「未実装」記述も同時に更新すること。
    """
    _, arrived = gate.collect_findings(
        _payload(reviews=[_review("looks fine", login="my-codex-helper")]))
    assert arrived is True, (
        "部分一致でなくなった — 強化自体は歓迎。決裁文書 "
        "pr-review-gate-2026-09-08.md 冒頭の『#231 版には未実装』記述を"
        "同時に更新せよ")


# ── 2026-09-11 (rule:R3): 進捗サマリを「到着」と数えていた欠陥の pin ──────────
#
# 実測: PR #249 は open の **18 秒後**に「connector レビュー到着済み・P1/P2
# 指摘なし — マージ可」(exit 0) を返した。その時点でサマリの Status は
# `🔄 **Running**` で、レビュー本体は 1 行も出ていない。R2 ゲートが防ぐはず
# だった「レビュー着弾前マージ」(PR #213 は 6 秒前) をゲート自身が追認する形で、
# **全 PR に対してゲートが空** になっていた。

_SUMMARY_RUNNING = """<!-- codex-pull-request-review-summary -->

## Codex Review Summary

| Review | Status | Commit | Review trigger |
| --- | --- | --- | --- |
| 📝 **Code Review** | 🔄 **Running** since 2026-09-11T02:06:04Z | `7e4fc41` | PR opened |
"""

_SUMMARY_COMPLETED = """<!-- codex-pull-request-review-summary -->

## Codex Review Summary

| Review | Status | Commit | Review trigger |
| --- | --- | --- | --- |
| 📝 **Code Review** | ✅ **Completed** 2026-09-11T02:20:00Z | `7e4fc41` | PR opened |
"""


def _summary(body: str, *, created: str = "2026-09-11T02:06:10Z"):
    return {"author": {"login": CONNECTOR}, "body": body, "createdAt": created}


def test_running_summary_is_not_arrival(monkeypatch):
    """進捗サマリだけの状態で exit 0 を返さないこと (欠陥の直接 pin)。"""
    payload = _payload(comments=[_summary(_SUMMARY_RUNNING)])
    payload["headRefOid"] = "7e4fc417" + "0" * 32
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    code, msg = gate.evaluate(249)
    assert code == 2, f"Running サマリで exit {code} を返した: {msg}"
    assert "実行中" in msg


def test_completed_summary_with_matching_head_is_arrival(monkeypatch):
    payload = _payload(comments=[_summary(_SUMMARY_COMPLETED)])
    payload["headRefOid"] = "7e4fc417" + "0" * 32
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    code, msg = gate.evaluate(249)
    assert code == 0, msg


def test_completed_summary_on_stale_commit_blocks(monkeypatch):
    """修正 push 後は再レビューが自動で走らない — HEAD 不一致を検出すること。"""
    payload = _payload(comments=[_summary(_SUMMARY_COMPLETED)])
    payload["headRefOid"] = "deadbee" + "f" * 33
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    code, msg = gate.evaluate(249)
    assert code == 2
    assert "@codex review" in msg


def test_running_wins_over_completed_when_both_present(monkeypatch):
    """複数レビューで 1 本でも走っていれば未確定 (fail-closed)。"""
    body = _SUMMARY_COMPLETED + "\n| 🔍 **Security Review** | 🔄 **Running** | `7e4fc41` | PR opened |"
    payload = _payload(comments=[_summary(body)])
    payload["headRefOid"] = "7e4fc417" + "0" * 32
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    assert gate.evaluate(249)[0] == 2


def test_real_finding_comment_still_counts_as_arrival(monkeypatch):
    """サマリ除外が本物のレビューコメントまで落とさないこと。"""
    payload = _payload(
        comments=[_summary(_SUMMARY_RUNNING),
                  {"author": {"login": CONNECTOR},
                   "body": "P1: null deref at app.py:10",
                   "createdAt": "2026-09-11T02:30:00Z"}])
    payload["headRefOid"] = "7e4fc417" + "0" * 32
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    code, msg = gate.evaluate(249)
    # Running サマリが同時にあるので「待て」が先に立つ (fail-closed)。
    assert code == 2
    # サマリを外せば finding が未消化として検出される。
    payload["comments"] = payload["comments"][1:]
    code, msg = gate.evaluate(249)
    assert code == 3 and "P1" in msg


def test_summary_helpers_are_pure():
    assert gate.summary_state({"comments": []}) == ("", "")
    st, sha = gate.summary_state({"comments": [_summary(_SUMMARY_RUNNING)]})
    assert (st, sha) == ("running", "7e4fc41")
    st, sha = gate.summary_state({"comments": [_summary(_SUMMARY_COMPLETED)]})
    assert (st, sha) == ("completed", "7e4fc41")
    assert gate.is_summary({"body": _SUMMARY_RUNNING}) is True
    assert gate.is_summary({"body": "P1: something"}) is False


def test_counterfactual_old_behaviour_would_fail_the_new_pin(monkeypatch):
    """旧実装 (サマリを到着扱い) ならこの pin が落ちることの証拠。"""
    payload = _payload(comments=[_summary(_SUMMARY_RUNNING)])
    payload["headRefOid"] = "7e4fc417" + "0" * 32
    monkeypatch.setattr(gate, "_gh_pr_json", lambda *a, **k: payload)
    monkeypatch.setattr(gate, "is_summary", lambda item: False)
    monkeypatch.setattr(gate, "summary_state", lambda payload: ("", ""))
    code, _ = gate.evaluate(249)
    assert code == 0, "counterfactual 構築に失敗 — 旧挙動を再現できていない"
