"""マージ前レビュー消化ゲート (process-meta-audit-2026-09-07 R2)。

背景: GitHub Codex connector のレビューは PR #75 以降ほぼ全 PR に届いていたが、
レビュー→マージ間隔 56 秒〜2 分が常態で、P1 指摘が無対応のままマージされて
いた (PR #213 はレビュー到着の 6 秒前にマージ) — 「独立レビュー不在」ではなく
**読み手不在**。本ツールはマージ直前に呼び、(a) connector レビューの到着
(b) P1/P2 指摘の消化 (レビュー到着後の対応 commit or 理由付きコメント) を判定する。

使い方:
    python3 tools/pr_review_gate.py <PR番号>            # 判定
    python3 tools/pr_review_gate.py <PR番号> --wait 300  # 到着まで最大 300 秒待つ

exit code: 0 = マージ可 / 2 = レビュー未到着 (待て) / 3 = P1/P2 未消化 / 4 = gh 失敗
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from typing import Any

REVIEWER_PAT = re.compile(r"codex|chatgpt", re.IGNORECASE)
FINDING_PAT = re.compile(r"\bP[12]\b")

# connector が PR open 直後に投げる進捗サマリ。findings ではなく**状態表**であり、
# Status 列が `🔄 **Running**` → `✅ **Completed**` と in-place に書き換わる。
# 2026-09-11 (rule:R3): 旧実装はこのサマリを「connector コメントが 1 件ある」
# という理由だけで *レビュー到着* と数え、findings ゼロなので exit 0 を返していた。
# 実測 PR #249 は open から **18 秒後**に「レビュー到着済み・P1/P2 指摘なし —
# マージ可」を返した (その時点で Status は Running)。R2 ゲートが防ぐはずだった
# 「レビュー着弾前マージ (#213 は 6 秒前)」を、ゲート自身が追認していた。
SUMMARY_MARKER = "<!-- codex-pull-request-review-summary -->"
_RUNNING_PAT = re.compile(r"\*\*Running\*\*", re.IGNORECASE)
_COMPLETED_PAT = re.compile(r"\*\*Completed\*\*", re.IGNORECASE)
# サマリ表の Commit 列 (例: `| ... | `7e4fc41` | PR opened |`)。
_SUMMARY_SHA_PAT = re.compile(r"`([0-9a-f]{7,40})`")


def is_summary(item: dict[str, Any]) -> bool:
    return SUMMARY_MARKER in (item.get("body") or "")


def summary_state(payload: dict[str, Any]) -> tuple[str, str]:
    """connector 進捗サマリの (状態, レビュー対象 SHA) を返す。

    状態 = "running" / "completed" / "" (サマリ無し)。Running と Completed が
    同時に載る (複数レビュー) 場合は **running を優先** — 1 本でも走っていれば
    消化判定は未確定だから (fail-closed)。
    """
    latest = ""
    body = ""
    for item in (payload.get("comments") or []):
        if not is_summary(item):
            continue
        created = item.get("createdAt") or item.get("submittedAt") or ""
        if created >= latest:
            latest, body = created, (item.get("body") or "")
    if not body:
        return "", ""
    sha = ""
    for line in body.splitlines():
        if _RUNNING_PAT.search(line) or _COMPLETED_PAT.search(line):
            m = _SUMMARY_SHA_PAT.search(line)
            if m:
                sha = m.group(1)
                break
    if _RUNNING_PAT.search(body):
        return "running", sha
    if _COMPLETED_PAT.search(body):
        return "completed", sha
    return "", sha


def _gh_pr_json(pr: int, fields: str) -> dict[str, Any] | None:
    try:
        out = subprocess.run(
            ["gh", "pr", "view", str(pr), "--json", fields],
            capture_output=True, text=True, timeout=60, check=True)
        return json.loads(out.stdout)
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def collect_findings(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    """(connector 由来の P1/P2 findings, connector レビュー到着済みか) を返す。"""
    arrived = False
    findings: list[dict[str, Any]] = []
    reviews = payload.get("reviews") or []
    buckets = reviews + (payload.get("comments") or [])
    review_ids = {id(r) for r in reviews}
    for item in buckets:
        author = ((item.get("author") or {}).get("login") or "")
        if not REVIEWER_PAT.search(author):
            continue
        # 進捗サマリは「レビューが走っている」ことしか示さない。これを到着と
        # 数えると PR open 直後に exit 0 が返る (2026-09-11 実測 18 秒)。
        # サマリ由来の到着判定は summary_state() 側だけで行う。
        if is_summary(item):
            continue
        body = item.get("body") or ""
        item_findings = [line.strip()[:200] for line in body.splitlines()
                         if FINDING_PAT.search(line)]
        # 2026-09-11 第 2 の空振り (PR #250 実測): connector は
        # 「To use Codex here, create an environment for this repo」という
        # **セットアップ通知**も同じ author で投げる。レビューは 1 度も
        # 走っていないのに旧判定ではこれが到着 (findings ゼロ → exit 0) になった。
        # 到着の positive evidence = (i) 正式 review オブジェクト /
        # (ii) P1/P2 を含む本文 / (iii) サマリ Completed (evaluate 側) の 3 つだけ。
        # 素の connector コメントは通知であって到着ではない (fail-closed)。
        if id(item) in review_ids or item_findings:
            arrived = True
        for line in item_findings:
            findings.append({"author": author,
                             "submitted": item.get("submittedAt")
                             or item.get("createdAt") or "",
                             "line": line})
    return findings, arrived


def latest_ack(payload: dict[str, Any], after: str) -> bool:
    """finding 到着後に、対応を明示するコメント/commit があるか。

    消化の定義 = レビュー到着より後の (a) 新規 commit (対応) または
    (b) `review-ack:` で始まる理由付きコメント (dismiss)。
    """
    for c in payload.get("comments") or []:
        body = (c.get("body") or "").lower()
        created = c.get("createdAt") or ""
        if body.startswith("review-ack:") and created > after:
            return True
    for commit in payload.get("commits") or []:
        committed = (commit.get("committedDate") or "")
        if committed > after:
            return True
    return False


def head_sha(payload: dict[str, Any]) -> str:
    """PR HEAD の SHA。取れなければ空文字 (SHA 照合はスキップされる)。"""
    return str(payload.get("headRefOid") or "")


def evaluate(pr: int) -> tuple[int, str]:
    payload = _gh_pr_json(pr, "reviews,comments,commits,headRefOid")
    if payload is None:
        return 4, f"PR #{pr}: gh 取得失敗 — 『取れなかった』を『指摘なし』と折り畳まない"
    findings, arrived = collect_findings(payload)
    state, reviewed_sha = summary_state(payload)
    if state == "running":
        return 2, (f"PR #{pr}: connector レビューは実行中 (サマリ Status=Running) — "
                   f"完了まで待つ (--wait)。進捗サマリの存在は *到着* ではない "
                   f"(rule:R3 2026-09-11)")
    if state == "completed":
        arrived = True
        head = head_sha(payload)
        if head and reviewed_sha and not head.startswith(reviewed_sha):
            return 2, (
                f"PR #{pr}: レビュー済み commit {reviewed_sha} が HEAD {head[:7]} と"
                f"不一致 — 修正 push 後の再レビューは自動で走らない。"
                f"`gh pr comment {pr} --body \"@codex review\"` を先に実行せよ "
                f"(CLAUDE.md コードレビュー節)")
    if not arrived:
        return 2, (
            f"PR #{pr}: connector レビュー未到着 — 数分待つ (--wait)。"
            f"connector が『create an environment for this repo』等の通知しか"
            f"返していない場合はレビューが走っていない (通知は到着ではない) — "
            f"`gh pr comment {pr} --body \"@codex review\"` で再依頼するか、"
            f"`review-ack: <理由>` で明示 dismiss せよ。"
            f"docs/KB のみの PR なら待たずにマージ可 (CLAUDE.md コードレビュー節)")
    if not findings:
        return 0, f"PR #{pr}: connector レビュー到着済み・P1/P2 指摘なし — マージ可"
    newest = max(f["submitted"] for f in findings)
    if latest_ack(payload, newest):
        return 0, (f"PR #{pr}: P1/P2 {len(findings)} 件は到着後の対応 commit / "
                   f"review-ack コメントで消化済み — マージ可")
    lines = "\n".join(f"  - [{f['author']}] {f['line']}" for f in findings[:10])
    return 3, (f"PR #{pr}: P1/P2 指摘 {len(findings)} 件が未消化:\n{lines}\n"
               f"→ 対応 commit を積むか、`review-ack: <理由>` コメントで明示 dismiss せよ")


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pr", type=int)
    ap.add_argument("--wait", type=int, default=0,
                    help="レビュー未到着のとき最大この秒数まで 30 秒間隔で再試行")
    args = ap.parse_args(argv)
    deadline = time.time() + args.wait
    while True:
        code, msg = evaluate(args.pr)
        if code != 2 or time.time() >= deadline:
            print(msg)
            return code
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
