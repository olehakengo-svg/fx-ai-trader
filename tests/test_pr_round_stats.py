"""tools/pr_round_stats.py — 巡目 / inline P1-P3 計数の pin (2026-11-13、rule:R3)。

計数定義は sprint-0922-close-review-2026-10-21 §2.1 を凍結する。ここが変わると
0922 窓 (code 中央値 7 / P1 75 / P2 271) との比較が壊れるので、定義の各辺を pin。
GitHub API には触れない (gh 呼び出しは monkeypatch)。
"""
from __future__ import annotations

import json

import pytest

from tools import pr_round_stats as prs

CONNECTOR = "chatgpt-codex-connector[bot]"
HUMAN = "olehakengo-svg"

P2_BODY = ("**<sub><sub>![P2 Badge](https://img.shields.io/badge/P2-yellow)</sub></sub>  "
           "Carry non-business-day conferences into the next business day**\n\nbody")
P1_BODY = ("**<sub><sub>![P1 Badge](https://img.shields.io/badge/P1-orange)</sub></sub>  "
           "Fix the race**")


def _ic(body, login=HUMAN):
    return {"user": {"login": login}, "body": body}


def _pc(body, login=CONNECTOR):
    return {"user": {"login": login}, "body": body}


# --- 巡目 ----------------------------------------------------------------------
def test_rounds_count_only_codex_review_mentions():
    comments = [_ic("@codex review"), _ic("please @Codex Review again"),
                _ic("unrelated"), _ic("@codex  review\nafter fix")]
    assert prs.count_rounds(comments) == 3


def test_rounds_exclude_connector_own_comments():
    """起票時の自動レビュー (connector のサマリ) は巡目に数えない。"""
    comments = [_ic("<!-- codex-pull-request-review-summary --> @codex review", login=CONNECTOR),
                _ic("@codex review")]
    assert prs.count_rounds(comments) == 1


def test_rounds_zero_when_no_comments():
    assert prs.count_rounds([]) == 0


# --- inline バッジ ---------------------------------------------------------------
@pytest.mark.parametrize("body,sev", [(P1_BODY, "P1"), (P2_BODY, "P2"),
                                      ("![P3 Badge](x) nit", "P3")])
def test_badge_in_first_40_chars(body, sev):
    assert prs.badge_severity(body) == sev


def test_badge_beyond_40_chars_is_not_counted():
    """author 返信が本文途中でバッジを引用しても数えない (先頭 40 文字の定義)。"""
    body = ("x" * 41) + "![P1 Badge](u)"
    assert prs.badge_severity(body) is None


def test_bold_p1_form_is_not_a_badge():
    assert prs.badge_severity("**P1** something") is None
    assert prs.badge_severity(None) is None


def test_count_inline_totals_include_replies():
    inline = [_pc(P1_BODY), _pc(P2_BODY), _pc(P2_BODY), _pc("reply text", login=HUMAN)]
    assert prs.count_inline(inline) == {"P1": 1, "P2": 2, "P3": 0, "total": 4}


# --- code / docs 分類 ----------------------------------------------------------
def test_docs_prefix_with_only_kb_markdown_is_docs():
    assert prs.classify("docs(KB): session log", ["knowledge-base/wiki/log.md",
                                                  "knowledge-base/wiki/sessions/x.md"]) == "docs"


@pytest.mark.parametrize("files", [
    ["knowledge-base/wiki/decisions/prereg-trigger-registry.json"],   # 非 .md
    ["knowledge-base/wiki/log.md", "tools/x.py"],                     # 非 KB
    [".claude/commands/wiki-daily.md"],                               # .md だが非 KB
])
def test_docs_prefix_with_non_md_or_non_kb_file_is_code(files):
    assert prs.classify("docs(KB)+registry: x", files) == "code"


@pytest.mark.parametrize("title", ["feat(tools): x", "fix(demo_trader): y", "test(wg): z"])
def test_non_docs_prefix_is_code_even_if_only_markdown(title):
    assert prs.classify(title, ["knowledge-base/wiki/log.md"]) == "code"


@pytest.mark.parametrize("title", ["kb: sync", "research(e1): note"])
def test_kb_and_research_prefixes_count_as_docs_prefix(title):
    assert prs.classify(title, ["knowledge-base/wiki/log.md"]) == "docs"


# --- 集計 ----------------------------------------------------------------------
def _rec(n, kind, rounds, p1=0, p2=0, p3=0):
    return {"number": n, "title": f"#{n}", "merged_at": "2026-11-01T00:00:00Z", "kind": kind,
            "n_files": 1, "rounds": rounds,
            "inline": {"P1": p1, "P2": p2, "P3": p3, "total": p1 + p2 + p3}}


def test_summarize_median_over_cap_and_distribution():
    recs = [_rec(1, "code", 7, p1=2), _rec(2, "code", 3, p2=1), _rec(3, "code", 9),
            _rec(4, "docs", 1), _rec(5, "docs", 0)]
    s = prs.summarize(recs, cap=6)
    code, docs, allc = s["classes"]["code"], s["classes"]["docs"], s["classes"]["all"]
    assert code["n"] == 3 and code["median"] == 7 and code["over_cap"] == 2
    assert code["over_cap_pct"] == 66.7
    assert code["distribution"] == {"3": 1, "7": 1, "9": 1}
    assert code["inline_P1"] == 2 and code["inline_P2"] == 1
    assert code["p1_prs"] == ["#1(2)"]
    assert code["top_rounds"][0] == "#3 9"
    assert docs["n"] == 2 and docs["median"] == 0.5 and docs["over_cap"] == 0
    assert allc["n"] == 5 and allc["median"] == 3


def test_summarize_empty_class_does_not_crash():
    s = prs.summarize([_rec(1, "code", 2)], cap=6)
    docs = s["classes"]["docs"]
    assert docs["n"] == 0 and docs["median"] is None and docs["over_cap_pct"] is None
    md = prs.render_markdown(s, "2026-10-22", "2026-11-21")
    assert "docs-only (n=0)" in md and "—" in md


def test_render_markdown_has_section_rows():
    s = prs.summarize([_rec(1, "code", 7, p1=1), _rec(2, "docs", 1)], cap=6)
    md = prs.render_markdown(s, "2026-10-22", "2026-11-21")
    assert "| 巡目 中央値 / 平均 / 範囲 | 7 / 7.0 / 7〜7 |" in md
    assert "| 巡目 >6 (上限超過) | 1 (100.0%) |" in md
    assert "| inline P1 合計 | 1 | 0 | 1 |" in md
    assert "#1(1)" in md


def test_build_record_uses_pr_files_for_kind():
    pr = {"number": 372, "title": "docs(KB): x", "mergedAt": "2026-11-12T04:16:30Z",
          "files": [{"path": ".claude/commands/wiki-daily.md"},
                    {"path": "knowledge-base/wiki/log.md"}]}
    r = prs.build_record(pr, [_ic("@codex review")], [_pc(P2_BODY)])
    assert r["kind"] == "code" and r["rounds"] == 1 and r["inline"]["P2"] == 1
    assert r["n_files"] == 2


# --- gh 失敗は fail-closed -----------------------------------------------------
def test_main_exit_4_when_gh_fails(monkeypatch, capsys):
    monkeypatch.setattr(prs, "collect", lambda *a, **k: None)
    assert prs.main(["--since", "2026-10-22", "--until", "2026-11-21"]) == 4
    assert "fail-closed" in capsys.readouterr().err


def test_collect_returns_none_if_any_pr_fetch_fails(monkeypatch):
    monkeypatch.setattr(prs, "gh_repo", lambda: ("o", "r"))
    monkeypatch.setattr(prs, "list_merged_prs", lambda s, u: [
        {"number": 1, "title": "feat: a", "mergedAt": "2026-11-01T00:00:00Z", "files": []},
        {"number": 2, "title": "feat: b", "mergedAt": "2026-11-02T00:00:00Z", "files": []}])
    monkeypatch.setattr(prs, "issue_comments", lambda o, r, n: [] if n == 1 else None)
    monkeypatch.setattr(prs, "inline_comments", lambda o, r, n: [])
    assert prs.collect("2026-10-22", "2026-11-21") is None


def test_collect_respects_pr_range_and_writes_json(monkeypatch, tmp_path):
    monkeypatch.setattr(prs, "gh_repo", lambda: ("o", "r"))
    monkeypatch.setattr(prs, "list_merged_prs", lambda s, u: [
        {"number": 10, "title": "feat: a", "mergedAt": "2026-11-01T00:00:00Z", "files": []},
        {"number": 11, "title": "docs(KB): b", "mergedAt": "2026-11-02T00:00:00Z",
         "files": [{"path": "knowledge-base/wiki/log.md"}]}])
    monkeypatch.setattr(prs, "issue_comments", lambda o, r, n: [_ic("@codex review")] * n)
    monkeypatch.setattr(prs, "inline_comments", lambda o, r, n: [_pc(P1_BODY)])
    out = tmp_path / "s.json"
    rc = prs.main(["--since", "2026-10-22", "--until", "2026-11-21", "--pr-min", "11",
                   "--json", str(out), "--no-records"])
    assert rc == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert [r["number"] for r in d["records"]] == [11]
    assert d["records"][0]["rounds"] == 11 and d["records"][0]["kind"] == "docs"
    assert d["summary"]["classes"]["all"]["inline_P1"] == 1
    assert d["definition"].startswith("sprint-0922-close-review")


def test_list_merged_prs_filters_by_merged_day(monkeypatch):
    monkeypatch.setattr(prs, "_gh", lambda args: [
        {"number": 1, "mergedAt": "2026-10-21T23:59:00Z"},
        {"number": 2, "mergedAt": "2026-10-22T00:00:00Z"},
        {"number": 3, "mergedAt": "2026-11-21T10:00:00Z"},
        {"number": 4, "mergedAt": "2026-11-22T00:00:01Z"}])
    got = prs.list_merged_prs("2026-10-22", "2026-11-21")
    assert [p["number"] for p in got] == [2, 3]


def test_paginated_flattens_slurped_pages(monkeypatch):
    monkeypatch.setattr(prs, "_gh", lambda args: [[{"a": 1}, {"a": 2}], [{"a": 3}]])
    assert prs._paginated("x") == [{"a": 1}, {"a": 2}, {"a": 3}]
    monkeypatch.setattr(prs, "_gh", lambda args: None)
    assert prs._paginated("x") is None
