#!/usr/bin/env python3
"""PR マージゲート — 独立レビューに「読み手」を付ける。

背景 (2026-09-07 プロセスメタ監査 §4.2 R2 / 2026-09-08 実測):
    GitHub の Codex connector レビューは PR #187 以降ほぼ全 PR に到着して
    いるが、直近 40 PR の実測で **inline finding を持つ 35 PR のうち解決
    済みスレッドは 0 件**、review→merge の中央値は 2.8 分、7 PR は
    レビュー到着から 1 分以内 (2 件はレビュー到着前) にマージされていた。
    レビューは無料で届いていて、読まれていなかった (write-only)。
    実害の実例: PR #226 の P1 が registry の必須フィールド欠落を指摘して
    いたが 1 秒後にマージされ、daily の pre-reg trigger watch が 51 エントリ
    まるごと 2 日間停止した。

    本ゲートは「レビューが到着したか」と「P1/P2 が消化 or 明示 dismiss
    されたか」を判定する。**内容の妥当性は判定しない** — 読み手を強制する
    だけで、採否は Claude の判断 (受け入れ / 反証して dismiss)。

estimand (名乗る量):
    - 母集団: 当該 PR の head commit に対する codex reviewer の review と、
      その inline review thread。
    - 分子: 未解決 (isResolved=false) かつ outdated でない P1/P2 スレッド。
    - 時計: GitHub 側の submittedAt (レビュー到着) / head commit の oid。
    - 「レビュー未到着」と「レビュー到着・findings ゼロ」は別状態として返す。

使い方:
    python3 tools/pr_review_gate.py 227            # 判定 (exit 0=マージ可)
    python3 tools/pr_review_gate.py 227 --json
    python3 tools/pr_review_gate.py 227 --wait 900 # 未到着なら最大 15 分待つ

exit code:
    0 = マージ可 (レビュー到着 ∧ 未解決 P1/P2 なし)
    1 = ブロック (未解決 P1/P2 あり、または head commit 未レビュー)
    2 = 判定不能 (gh 失敗等) — 判定不能をマージ可に折り畳まない
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any

# 指定レビュアーは完全一致で照合する。部分一致 (r"codex") だと
# `my-codex-helper` のような無関係アカウントの空レビューでゲートが通る
# (PR #227 Codex P2)。env で上書き可能にして allowlist の追加を許す。
DEFAULT_REVIEWERS = ("chatgpt-codex-connector",)
REVIEWER_LOGINS = frozenset(
    x.strip().lower()
    for x in os.environ.get("PR_REVIEW_GATE_REVIEWERS", "").split(",")
    if x.strip()
) or frozenset(x.lower() for x in DEFAULT_REVIEWERS)


def is_designated_reviewer(login: str | None) -> bool:
    return bool(login) and login.strip().lower() in REVIEWER_LOGINS

# Codex は finding 本文の先頭に P1/P2/P3 バッジ画像を置く。
SEVERITY_PAT = re.compile(r"!\[(P[123]) Badge\]", re.IGNORECASE)
BLOCKING = ("P1", "P2")

_QUERY = """
query($owner:String!, $name:String!, $number:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      number title state
      commits(last:1) { nodes { commit { oid } } }
      reviews(first:50) { nodes { author { login } state submittedAt
                                  commit { oid } } }
      reviewThreads(first:100) {
        nodes { isResolved isOutdated path
                comments(first:1) { nodes { author { login } body url } } }
      }
    }
  }
}
"""


def _repo_slug() -> tuple[str, str]:
    out = subprocess.run(
        ["gh", "repo", "view", "--json", "owner,name"],
        capture_output=True, text=True, check=True)
    d = json.loads(out.stdout)
    return d["owner"]["login"], d["name"]


def fetch_pr(number: int) -> dict[str, Any]:
    owner, name = _repo_slug()
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={_QUERY}",
         "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}"],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)["data"]["repository"]["pullRequest"]


def severity(body: str) -> str:
    m = SEVERITY_PAT.search(body or "")
    return m.group(1).upper() if m else "P?"


def finding_title(body: str) -> str:
    """finding 本文の見出しからバッジ markdown を落として 1 行に。"""
    head = (body or "").splitlines()
    line = head[0] if head else ""
    line = SEVERITY_PAT.sub("", line)
    line = re.sub(r"</?sub>|\*\*|\(https?://[^)]+\)", "", line)
    return line.strip(" *·-") [:160]


def evaluate(pr: dict[str, Any]) -> dict[str, Any]:
    """PR の生データ -> ゲート判定。ネットワークに触らない (テスト可能)。"""
    commits = pr.get("commits", {}).get("nodes") or []
    head = commits[-1]["commit"]["oid"] if commits else ""
    reviews = [r for r in pr.get("reviews", {}).get("nodes", [])
               if is_designated_reviewer((r.get("author") or {}).get("login"))]
    head_reviews = [r for r in reviews
                    if (r.get("commit") or {}).get("oid") == head]

    open_findings: list[dict[str, Any]] = []
    for th in pr.get("reviewThreads", {}).get("nodes", []):
        c = (th.get("comments") or {}).get("nodes") or []
        if not c:
            continue
        author = (c[0].get("author") or {}).get("login") or ""
        if not is_designated_reviewer(author):
            continue
        if th.get("isResolved") or th.get("isOutdated"):
            continue
        body = c[0].get("body", "")
        open_findings.append({
            "severity": severity(body),
            "path": th.get("path", ""),
            "url": c[0].get("url", ""),
            "title": finding_title(body),
        })

    blocking = [f for f in open_findings if f["severity"] in BLOCKING]
    if not reviews:
        return {"verdict": "BLOCK", "reason": "NO_REVIEW", "head": head,
                "detail": f"指定レビュアー ({'/'.join(sorted(REVIEWER_LOGINS))}) "
                          "のレビューが 1 件も到着していない",
                "open_findings": open_findings, "blocking": blocking}
    if not head_reviews:
        return {"verdict": "BLOCK", "reason": "HEAD_UNREVIEWED", "head": head,
                "detail": f"head commit {head[:7]} に対するレビューが無い "
                          "(push 後に再レビューを待て)",
                "open_findings": open_findings, "blocking": blocking}
    if blocking:
        return {"verdict": "BLOCK", "reason": "OPEN_BLOCKING_FINDINGS",
                "head": head,
                "detail": f"未解決の {'/'.join(BLOCKING)} finding が "
                          f"{len(blocking)} 件",
                "open_findings": open_findings, "blocking": blocking}
    return {"verdict": "PASS", "reason": "REVIEWED_NO_BLOCKING", "head": head,
            "detail": f"head {head[:7]} レビュー済 / 未解決 P1・P2 なし",
            "open_findings": open_findings, "blocking": blocking}


def to_text(number: int, res: dict[str, Any]) -> str:
    icon = "✅" if res["verdict"] == "PASS" else "🔴"
    lines = [f"{icon} PR #{number} review gate: {res['verdict']} "
             f"({res['reason']}) — {res['detail']}"]
    for f in res["open_findings"]:
        mark = "🔴" if f["severity"] in BLOCKING else "·"
        lines.append(f"  {mark} [{f['severity']}] {f['path']}: {f['title']}")
        if f["url"]:
            lines.append(f"      {f['url']}")
    if res["verdict"] == "BLOCK":
        lines.append("  → 対応: finding を修正するか、反証を thread に返信して "
                     "resolve せよ。無視してのマージは禁止 (CLAUDE.md マージゲート)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="PR review gate (R2)")
    ap.add_argument("number", type=int)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--wait", type=int, default=0,
                    help="レビュー未到着のとき最大 N 秒待つ (30 秒間隔)")
    args = ap.parse_args()

    deadline = time.monotonic() + max(0, args.wait)
    while True:
        try:
            res = evaluate(fetch_pr(args.number))
        except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError,
                TypeError) as e:
            print(f"⚠️ 判定不能 (gh/GraphQL): {type(e).__name__}: {e}",
                  file=sys.stderr)
            return 2
        waiting = res["reason"] in ("NO_REVIEW", "HEAD_UNREVIEWED")
        if not waiting or time.monotonic() >= deadline:
            break
        print(f"… {res['detail']} — 30 秒待機", file=sys.stderr)
        time.sleep(30)

    print(json.dumps(res, ensure_ascii=False, indent=2) if args.json
          else to_text(args.number, res))
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
