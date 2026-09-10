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
    buckets = (payload.get("reviews") or []) + (payload.get("comments") or [])
    for item in buckets:
        author = ((item.get("author") or {}).get("login") or "")
        if not REVIEWER_PAT.search(author):
            continue
        arrived = True
        body = item.get("body") or ""
        for line in body.splitlines():
            if FINDING_PAT.search(line):
                findings.append({"author": author,
                                 "submitted": item.get("submittedAt")
                                 or item.get("createdAt") or "",
                                 "line": line.strip()[:200]})
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


def evaluate(pr: int) -> tuple[int, str]:
    payload = _gh_pr_json(pr, "reviews,comments,commits")
    if payload is None:
        return 4, f"PR #{pr}: gh 取得失敗 — 『取れなかった』を『指摘なし』と折り畳まない"
    findings, arrived = collect_findings(payload)
    if not arrived:
        return 2, (f"PR #{pr}: connector レビュー未到着 — 数分待つ (--wait)。"
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
