#!/usr/bin/env python3
"""PR レビュー巡目 / inline P1-P3 集計 — sprint 終了レビューの読み手 (2026-11-13、rule:R3)。

registry `sprint-1022-triage-close` (期日 2026-11-21) の reachability 欄が
「SCRATCH 手順 = tools 化候補: tools/pr_round_stats.py」と宣言していた計数を
tool 化する。計数定義は [[sprint-0922-close-review-2026-10-21]] §2.1 をそのまま
凍結する (数字の定義を変えると 0922 窓との比較が壊れる):

- **巡目** = issue comment に `@codex review` を含む件数 (起票時の自動レビュー
  1 回は含まない)。connector 自身のコメント (進捗サマリ) は数えない。
- **inline P1/P2/P3** = `pulls/{n}/comments` 本文の **先頭 40 文字**にある Codex
  バッジ `![P1 Badge]` (`**P1**` 形式は不使用)。author 返信はバッジで始まらない
  ので数に入らない。
- **code PR** = title 接頭辞が `docs(` / `kb:` / `research(` でない、または docs
  接頭辞でも非 `.md` / 非 `knowledge-base/` ファイルを含むもの。それ以外が
  docs-only。

読むだけ (GitHub API)。価格データ・DB・live 経路・registry には触れない。
gh 失敗は握り潰さず exit 4 (部分集計を「完了」として印字しない = fail-closed)。

使い方:
    python3 tools/pr_round_stats.py --since 2026-10-22 --until 2026-11-21 \
        [--cap 6] [--json out.json] [--pr-min 348] [--pr-max 373]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from collections import Counter
from typing import Any

# pr_review_gate.py と同じ connector 判定 (bot login = chatgpt-codex-connector[bot])
REVIEWER_PAT = re.compile(r"codex|chatgpt", re.IGNORECASE)
ROUND_PAT = re.compile(r"@codex\s+review", re.IGNORECASE)
BADGE_PAT = re.compile(r"!\[P([123]) Badge\]")
BADGE_HEAD_CHARS = 40
DOCS_PREFIX_PAT = re.compile(r"^(docs\(|kb:|research\()")
DEFAULT_CAP = 6
GH_TIMEOUT = 120


# --------------------------------------------------------------------------- pure
def is_connector(login: str | None) -> bool:
    return bool(REVIEWER_PAT.search(login or ""))


def count_rounds(issue_comments: list[dict[str, Any]]) -> int:
    """`@codex review` を含む issue comment の件数 (connector 自身の投稿は除外)。"""
    n = 0
    for c in issue_comments:
        login = ((c.get("user") or {}).get("login")) or ""
        if is_connector(login):
            continue
        if ROUND_PAT.search(c.get("body") or ""):
            n += 1
    return n


def badge_severity(body: str | None) -> str | None:
    """本文先頭 40 文字の Codex バッジから 'P1'/'P2'/'P3' を返す。無ければ None。"""
    m = BADGE_PAT.search((body or "")[:BADGE_HEAD_CHARS])
    return f"P{m.group(1)}" if m else None


def count_inline(inline_comments: list[dict[str, Any]]) -> dict[str, int]:
    """inline comment のバッジ件数 {P1, P2, P3, total}。total はバッジ有無を問わない全件。"""
    out = {"P1": 0, "P2": 0, "P3": 0, "total": len(inline_comments)}
    for c in inline_comments:
        sev = badge_severity(c.get("body"))
        if sev:
            out[sev] += 1
    return out


def classify(title: str, files: list[str]) -> str:
    """'docs' (docs-only) か 'code' か。§2.1 の定義を字義どおりに適用する。"""
    if not DOCS_PREFIX_PAT.search(title or ""):
        return "code"
    for path in files:
        if not path.endswith(".md") or not path.startswith("knowledge-base/"):
            return "code"
    return "docs"


def build_record(pr: dict[str, Any], issue_comments: list[dict[str, Any]],
                 inline_comments: list[dict[str, Any]]) -> dict[str, Any]:
    files = [f.get("path") or "" for f in (pr.get("files") or [])]
    inline = count_inline(inline_comments)
    return {
        "number": pr.get("number"),
        "title": pr.get("title") or "",
        "merged_at": pr.get("mergedAt") or "",
        "kind": classify(pr.get("title") or "", files),
        "n_files": len(files),
        "rounds": count_rounds(issue_comments),
        "inline": inline,
    }


def _stats(values: list[int], cap: int) -> dict[str, Any]:
    if not values:
        return {"n": 0, "median": None, "mean": None, "min": None, "max": None,
                "over_cap": 0, "over_cap_pct": None, "distribution": {}}
    over = sum(1 for v in values if v > cap)
    return {
        "n": len(values),
        "median": statistics.median(values),
        "mean": round(statistics.fmean(values), 2),
        "min": min(values),
        "max": max(values),
        "over_cap": over,
        "over_cap_pct": round(100.0 * over / len(values), 1),
        "distribution": {str(k): v for k, v in sorted(Counter(values).items())},
    }


def summarize(records: list[dict[str, Any]], cap: int = DEFAULT_CAP) -> dict[str, Any]:
    """§2.2 表の数値を class 別 (code / docs / all) に出す。"""
    out: dict[str, Any] = {"cap": cap, "classes": {}}
    for cls in ("code", "docs", "all"):
        rs = [r for r in records if cls == "all" or r["kind"] == cls]
        st = _stats([r["rounds"] for r in rs], cap)
        st["inline_P1"] = sum(r["inline"]["P1"] for r in rs)
        st["inline_P2"] = sum(r["inline"]["P2"] for r in rs)
        st["inline_P3"] = sum(r["inline"]["P3"] for r in rs)
        st["inline_total"] = sum(r["inline"]["total"] for r in rs)
        st["p1_prs"] = [f"#{r['number']}({r['inline']['P1']})" for r in rs
                        if r["inline"]["P1"] > 0]
        st["top_rounds"] = [f"#{r['number']} {r['rounds']}" for r in
                            sorted(rs, key=lambda r: (-r["rounds"], r["number"]))[:3]]
        out["classes"][cls] = st
    return out


def _fmt(v: Any) -> str:
    return "—" if v is None else str(v)


def render_markdown(summary: dict[str, Any], since: str, until: str) -> str:
    c, d, a = (summary["classes"][k] for k in ("code", "docs", "all"))
    cap = summary["cap"]
    lines = [
        f"## 巡目実測 (merged {since}〜{until}、{a['n']} 本、上限 ≤{cap})",
        "",
        f"| 指標 | code PR (n={c['n']}) | docs-only (n={d['n']}) | 全体 (n={a['n']}) |",
        "|---|---|---|---|",
        f"| 巡目 中央値 / 平均 / 範囲 | {_fmt(c['median'])} / {_fmt(c['mean'])} / "
        f"{_fmt(c['min'])}〜{_fmt(c['max'])} | {_fmt(d['median'])} / {_fmt(d['mean'])} / "
        f"{_fmt(d['min'])}〜{_fmt(d['max'])} | {_fmt(a['median'])} / {_fmt(a['mean'])} / "
        f"{_fmt(a['min'])}〜{_fmt(a['max'])} |",
        f"| 巡目 >{cap} (上限超過) | {c['over_cap']} ({_fmt(c['over_cap_pct'])}%) | "
        f"{d['over_cap']} ({_fmt(d['over_cap_pct'])}%) | {a['over_cap']} ({_fmt(a['over_cap_pct'])}%) |",
        f"| 分布 (巡目: 本数) | {_dist(c)} | {_dist(d)} | {_dist(a)} |",
        f"| inline P1 合計 | {c['inline_P1']} | {d['inline_P1']} | {a['inline_P1']} |",
        f"| inline P2 合計 (P3) | {c['inline_P2']} ({c['inline_P3']}) | "
        f"{d['inline_P2']} ({d['inline_P3']}) | {a['inline_P2']} ({a['inline_P3']}) |",
        f"| inline 全件 (返信含む) | {c['inline_total']} | {d['inline_total']} | {a['inline_total']} |",
        f"| P1 > 0 の PR | {' '.join(c['p1_prs']) or 'なし'} | {' '.join(d['p1_prs']) or 'なし'} | — |",
        f"| 最多巡目 | {' / '.join(c['top_rounds']) or '—'} | {' / '.join(d['top_rounds']) or '—'} | — |",
    ]
    return "\n".join(lines)


def _dist(st: dict[str, Any]) -> str:
    dist = st.get("distribution") or {}
    return ", ".join(f"{k}×{v}" for k, v in dist.items()) or "—"


def render_records(records: list[dict[str, Any]]) -> str:
    lines = ["| PR | merged | kind | 巡目 | P1 | P2 | P3 | title |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(records, key=lambda r: r["number"]):
        i = r["inline"]
        lines.append(f"| #{r['number']} | {r['merged_at'][:10]} | {r['kind']} | {r['rounds']} | "
                     f"{i['P1']} | {i['P2']} | {i['P3']} | {r['title'][:60]} |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- gh
def _gh(args: list[str]) -> Any | None:
    """gh を呼び JSON を返す。失敗は None (呼び手が fail-closed にする)。"""
    try:
        out = subprocess.run(["gh", *args], capture_output=True, text=True,
                             timeout=GH_TIMEOUT, check=True)
        return json.loads(out.stdout) if out.stdout.strip() else []
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def gh_repo() -> tuple[str, str] | None:
    d = _gh(["repo", "view", "--json", "owner,name"])
    try:
        return (d["owner"]["login"], d["name"])
    except (TypeError, KeyError):
        return None


def list_merged_prs(since: str, until: str) -> list[dict[str, Any]] | None:
    """merged_at が [since, until] (日付、両端含む) の merged PR。"""
    d = _gh(["pr", "list", "--state", "merged", "--limit", "500",
             "--search", f"merged:{since}..{until}",
             "--json", "number,title,mergedAt,files"])
    if d is None:
        return None
    out = []
    for pr in d:
        day = (pr.get("mergedAt") or "")[:10]
        if since <= day <= until:
            out.append(pr)
    return out


def issue_comments(owner: str, name: str, pr: int) -> list[dict[str, Any]] | None:
    return _paginated(f"repos/{owner}/{name}/issues/{pr}/comments")


def inline_comments(owner: str, name: str, pr: int) -> list[dict[str, Any]] | None:
    return _paginated(f"repos/{owner}/{name}/pulls/{pr}/comments")


def _paginated(path: str) -> list[dict[str, Any]] | None:
    """`gh api --paginate` は複数ページを JSON 配列の連結で返すので --slurp で受け、平坦化。"""
    d = _gh(["api", path, "--paginate", "--slurp"])
    if d is None:
        return None
    flat: list[dict[str, Any]] = []
    for page in d:
        if isinstance(page, list):
            flat.extend(page)
        elif isinstance(page, dict):
            flat.append(page)
    return flat


def collect(since: str, until: str, pr_min: int | None = None,
            pr_max: int | None = None) -> list[dict[str, Any]] | None:
    repo = gh_repo()
    if repo is None:
        return None
    owner, name = repo
    prs = list_merged_prs(since, until)
    if prs is None:
        return None
    records = []
    for pr in sorted(prs, key=lambda p: p.get("number") or 0):
        n = pr.get("number")
        if pr_min is not None and n < pr_min:
            continue
        if pr_max is not None and n > pr_max:
            continue
        ic = issue_comments(owner, name, n)
        pc = inline_comments(owner, name, n)
        if ic is None or pc is None:
            return None
        records.append(build_record(pr, ic, pc))
    return records


# --------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", required=True, help="merged_at 下限 (YYYY-MM-DD、含む)")
    ap.add_argument("--until", required=True, help="merged_at 上限 (YYYY-MM-DD、含む)")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP, help="巡目上限 (既定 6)")
    ap.add_argument("--pr-min", type=int, default=None)
    ap.add_argument("--pr-max", type=int, default=None)
    ap.add_argument("--json", default=None, help="records + summary を JSON で保存")
    ap.add_argument("--no-records", action="store_true", help="PR 別表を印字しない")
    a = ap.parse_args(argv)

    records = collect(a.since, a.until, a.pr_min, a.pr_max)
    if records is None:
        print("gh 取得失敗 — 部分集計は印字しない (fail-closed)", file=sys.stderr)
        return 4
    summary = summarize(records, a.cap)
    print(render_markdown(summary, a.since, a.until))
    if not a.no_records:
        print()
        print(render_records(records))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"since": a.since, "until": a.until, "cap": a.cap,
                       "definition": "sprint-0922-close-review-2026-10-21 §2.1",
                       "records": records, "summary": summary},
                      fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
