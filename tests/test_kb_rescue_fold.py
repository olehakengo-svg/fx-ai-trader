"""`tools/kb_rescue_fold.py` — kb-rescue ref を origin/main に畳む tool の pin。

実 git repo (bare origin + 座礁 host clone + 先行する origin main + fresh runner)
を立てて tool を走らせる。grep pin ではなく「origin/main に内容が届いたか」で
判定する (test_session_end_save_rescue.py と同じ方針)。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import pytest

from tools import kb_rescue_fold as krf


def _clean_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") or k in ("GIT_ASKPASS",)}
    env.setdefault("HOME", os.path.expanduser("~"))
    return env


def _git(cwd, *args, check=True):
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *args], cwd=cwd, check=check,
                          capture_output=True, text=True, env=_clean_env())


def _write(root, rel, text):
    full = os.path.join(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)


def _read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as f:
        return f.read()


def _clone(remote, dst, who):
    _git(os.path.dirname(dst), "clone", "-q", remote, dst)
    _git(dst, "config", "user.email", f"{who}@t")
    _git(dst, "config", "user.name", who)
    return dst


@pytest.fixture()
def world():
    """origin main = seed; host = stale clone that strands a KB commit as a kb-rescue ref."""
    root = tempfile.mkdtemp(prefix="kb-fold-")
    remote = os.path.join(root, "remote.git")
    _git(root, "init", "-q", "--bare", "-b", "main", remote)
    seed = _clone(remote, os.path.join(root, "seed"), "seed")
    _write(seed, "knowledge-base/wiki/index.md", "# index\nline A\nline B\n")
    _write(seed, "knowledge-base/wiki/log.md", "# log\n")
    _write(seed, "README.md", "code\n")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-q", "-m", "seed")
    _git(seed, "push", "-q", "origin", "main")
    host = _clone(remote, os.path.join(root, "host"), "host")  # will go stale
    other = _clone(remote, os.path.join(root, "other"), "other")  # advances origin main
    yield {"root": root, "remote": remote, "host": host, "other": other}
    shutil.rmtree(root, ignore_errors=True)


def _strand(host, date, files, subject="auto: KB session-end save"):
    """Commit `files` on the host's stale main and push it the way the hook does."""
    for rel, text in files.items():
        _write(host, rel, text)
    _git(host, "add", "-A")
    _git(host, "commit", "-q", "-m", f"{subject} ({date})")
    sha = _git(host, "rev-parse", "HEAD").stdout.strip()
    _git(host, "push", "-q", "origin", f"{sha}:refs/heads/kb-rescue/main-{date}-{sha}")
    return sha


def _advance_origin(other, files, msg="origin moved"):
    _git(other, "pull", "-q", "--rebase", "origin", "main")
    for rel, text in files.items():
        _write(other, rel, text)
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", msg)
    _git(other, "push", "-q", "origin", "main")


def _run_tool(remote, root, name, *extra):
    runner = _clone(remote, os.path.join(root, name), "runner")
    rc = krf.main(["--repo", runner, "--in-place", *extra])
    return runner, rc


def _remote_refs(remote):
    out = _git(remote, "for-each-ref", "--format=%(refname:short)", "refs/heads/kb-rescue/").stdout
    return sorted(out.split())


# ----------------------------------------------------------------------- pins
def test_a_stranded_kb_commit_reaches_origin_main_via_3way(world):
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    # origin moves on (touches index.md line A); host strands a trade log + index.md line C.
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\nline A (origin)\nline B\n",
                            "knowledge-base/wiki/log.md": "# log\n- origin entry\n"})
    sha = _strand(host, "2026-11-14", {
        "knowledge-base/raw/trade-logs/2026-11-13.md": "# 2026-11-13 Daily Trade Log\nstranded\n",
        "knowledge-base/wiki/index.md": "# index\nline A\nline B\nline C (host)\n",
    })
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    check = _clone(remote, os.path.join(root, "check"), "check")
    assert _read(check, "knowledge-base/raw/trade-logs/2026-11-13.md").startswith("# 2026-11-13")
    assert _read(check, "knowledge-base/wiki/index.md") == "# index\nline A (origin)\nline B\nline C (host)\n"
    assert "- origin entry" in _read(check, "knowledge-base/wiki/log.md")
    subj = _git(check, "log", "-1", "--format=%s%n%b").stdout
    assert "fold kb-rescue/main-2026-11-14" in subj and sha in subj
    assert _remote_refs(remote) == []  # pruned after a successful push
    assert _git(runner, "status", "--porcelain").stdout == ""


def test_a_commit_touching_non_kb_paths_is_manual_not_silently_trimmed(world):
    """hook は KB-only の履歴しか退避しない — 混在 commit は MANUAL (非 KB を黙って捨てない)。"""
    host, remote, root = world["host"], world["remote"], world["root"]
    _strand(host, "2026-11-14", {"knowledge-base/wiki/log.md": "# log\n- host\n", "README.md": "changed\n"},
            subject="mixed")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip() == "seed"
    assert _read(runner, "README.md") == "code\n"
    assert len(_remote_refs(remote)) == 1


def test_a_conflicting_ref_is_reported_kept_and_leaves_the_tree_clean(world):
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\nline A (origin)\nline B\n"})
    _strand(host, "2026-11-14", {"knowledge-base/wiki/index.md": "# index\nline A (host)\nline B\n"})
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert _git(runner, "status", "--porcelain").stdout == ""
    assert _read(runner, "knowledge-base/wiki/index.md") == "# index\nline A (origin)\nline B\n"
    assert len(_remote_refs(remote)) == 1  # CONFLICT refs are never pruned
    head = _git(runner, "log", "-1", "--format=%s").stdout
    assert "fold" not in head


def test_a_conflict_does_not_block_the_next_ref(world):
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\nline A (origin)\nline B\n"})
    _strand(host, "2026-11-13", {"knowledge-base/wiki/index.md": "# index\nline A (host)\nline B\n"})
    _strand(host, "2026-11-14", {"knowledge-base/raw/trade-logs/2026-11-14.md": "ok\n"})
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    check = _clone(remote, os.path.join(root, "check"), "check")
    assert _read(check, "knowledge-base/raw/trade-logs/2026-11-14.md") == "ok\n"
    # both refs stay: the 11-14 ref's history still carries the unaccounted 11-13 commit (6 巡目 P1)
    refs = _remote_refs(remote)
    assert len(refs) == 2 and "2026-11-13" in refs[0] and "2026-11-14" in refs[1]


def test_session_logs_are_excluded_so_hook_noise_folds_to_empty(world):
    host, remote, root = world["host"], world["remote"], world["root"]
    _strand(host, "2026-11-14", {"knowledge-base/wiki/sessions/2026-11-14-session.md": "1. auto (abc, 1 files)\n"})
    runner, rc = _run_tool(remote, root, "runner", "--prune")
    assert rc == 0
    assert _remote_refs(remote) == []
    assert not os.path.exists(os.path.join(runner, "knowledge-base/wiki/sessions/2026-11-14-session.md"))


def test_content_already_in_main_is_present_and_pruned_without_a_new_commit(world):
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    _strand(host, "2026-11-14", {"knowledge-base/wiki/log.md": "# log\n- same entry\n"})
    _advance_origin(other, {"knowledge-base/wiki/log.md": "# log\n- same entry\n"}, msg="manual rescue")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    assert _remote_refs(remote) == []
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip() == "manual rescue"


def test_without_push_folded_refs_are_not_pruned(world):
    host, remote, root = world["host"], world["remote"], world["root"]
    _strand(host, "2026-11-14", {"knowledge-base/wiki/log.md": "# log\n- host\n"})
    runner, rc = _run_tool(remote, root, "runner", "--prune")
    assert rc == 0
    assert len(_remote_refs(remote)) == 1  # the fold only exists locally


def test_dirty_kb_tree_is_fail_closed(world):
    host, remote, root = world["host"], world["remote"], world["root"]
    _strand(host, "2026-11-14", {"knowledge-base/wiki/log.md": "# log\n- host\n"})
    runner = _clone(remote, os.path.join(root, "runner"), "runner")
    _write(runner, "knowledge-base/wiki/index.md", "# index\nuser WIP\n")
    assert krf.main(["--repo", runner, "--in-place"]) == 4
    assert _read(runner, "knowledge-base/wiki/index.md") == "# index\nuser WIP\n"


def test_conflict_markers_are_detected_only_at_line_start():
    assert krf.has_conflict_markers("a\n<<<<<<< HEAD\nb\n=======\nc\n>>>>>>> x\n")
    assert krf.has_conflict_markers("x\n=======\n")
    assert not krf.has_conflict_markers("KB 本文で `<<<<<<<` を説明している行\n")
    assert not krf.has_conflict_markers("table |=======| not a marker\n")


def test_name_status_z_parsing_handles_renames_and_odd_paths():
    raw = "M\0knowledge-base/wiki/日本語 memo.md\0A\0knowledge-base/raw/new \"quoted\".md\0R100\0old.md\0new.md\0"
    assert krf.parse_name_status_z(raw) == [("M", "knowledge-base/wiki/日本語 memo.md", None),
                                            ("A", "knowledge-base/raw/new \"quoted\".md", None), ("R", "new.md", "old.md")]
    assert krf.parse_name_status_z("") == []


def test_refs_are_folded_in_commit_time_order():
    entries = [("r-late", "b", 200), ("r-early", "a", 100), ("r-tie2", "d", 150), ("r-tie1", "c", 150)]
    assert [r for r, _ in krf.sort_refs_by_time(entries)] == ["r-early", "r-tie1", "r-tie2", "r-late"]


# ------------------------------------------------------- union (hot-file additive)
def test_both_sides_appending_to_the_same_hot_file_is_union_resolved(world):
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    _advance_origin(other, {"knowledge-base/wiki/log.md": "# log\n\n## 2026-11-13 autopilot\n- §7.6 deploy attribution\n"})
    sha = _strand(host, "2026-11-14", {
        "knowledge-base/raw/trade-logs/2026-11-13.md": "# 2026-11-13 Daily Trade Log\n",
        "knowledge-base/wiki/log.md": "# log\n\n## 2026-11-13 wiki-daily\n- fills 0 / closes 0, shadow 112 +11.5\n",
    })
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    check = _clone(remote, os.path.join(root, "check"), "check")
    log = _read(check, "knowledge-base/wiki/log.md")
    assert "## 2026-11-13 autopilot" in log and "## 2026-11-13 wiki-daily" in log
    assert log.index("autopilot") < log.index("wiki-daily")  # ours (origin) first, then the rescued text
    assert not krf.has_conflict_markers(log)
    body = _git(check, "log", "-1", "--format=%b").stdout
    assert "union-resolved 1" in body and sha in body
    assert _remote_refs(remote) == []


def test_a_prior_manual_rescue_is_never_duplicated_by_union(world):
    """新規ファイルが target に既にある ref は union しない (先行救出の手直し版と重複する)。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    _strand(host, "2026-11-14", {
        "knowledge-base/raw/trade-logs/2026-11-13.md": "# 2026-11-13 Daily Trade Log\n",
        "knowledge-base/wiki/log.md": "# log\n\n## 2026-11-13 wiki-daily\n- fills 0\n",
    })
    # autopilot rescued it by hand, editing the wording while at it
    _advance_origin(other, {"knowledge-base/raw/trade-logs/2026-11-13.md": "# 2026-11-13 Daily Trade Log\n",
                            "knowledge-base/wiki/log.md": "# log\n\n## 2026-11-13 wiki-daily (rescued 13th)\n- fills 0\n"},
                    msg="manual rescue")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    check = _clone(remote, os.path.join(root, "check"), "check")
    assert _read(check, "knowledge-base/wiki/log.md").count("2026-11-13 wiki-daily") == 1
    assert len(_remote_refs(remote)) == 1


def test_near_duplicate_additions_are_not_unioned():
    # reworded (not a verbatim superset) and too similar → left for a human, never concatenated
    text = ("# log\n<<<<<<< ours\n- 2026-11-13: fills 0 / closes 0 / NAV ¥271,681 (edited by hand)\n"
            "||||||| base\n=======\n- 2026-11-13: fills 0 / closes 0 / NAV ¥271,682\n>>>>>>> theirs\n")
    merged, resolved, unresolved = krf.resolve_additive_conflicts(text)
    assert (resolved, unresolved) == (0, 1) and merged == text
    # a verbatim superset (ours = theirs + suffix) counts as contained → ours kept, nothing duplicated
    text2 = ("# log\n<<<<<<< ours\n- 2026-11-13: fills 0 / closes 0 / NAV ¥271,681 (rescued, edited)\n"
             "||||||| base\n=======\n- 2026-11-13: fills 0 / closes 0 / NAV ¥271,681\n>>>>>>> theirs\n")
    merged2, r2, u2 = krf.resolve_additive_conflicts(text2)
    assert (r2, u2) == (1, 0) and merged2 == "# log\n- 2026-11-13: fills 0 / closes 0 / NAV ¥271,681 (rescued, edited)\n"


def test_non_additive_or_non_diff3_blocks_are_left_alone():
    with_base = "<<<<<<< ours\nA2\n||||||| base\nA1\n=======\nA3\n>>>>>>> theirs\n"
    assert krf.resolve_additive_conflicts(with_base)[1:] == (0, 1)
    no_diff3 = "<<<<<<< ours\nalpha section\n=======\nomega section\n>>>>>>> theirs\n"
    assert krf.resolve_additive_conflicts(no_diff3)[1:] == (0, 1)
    additive = "x\n<<<<<<< ours\nalpha section about deploys\n||||||| base\n=======\nomega notes on shadow\n>>>>>>> theirs\ny\n"
    merged, r, u = krf.resolve_additive_conflicts(additive)
    assert (r, u) == (1, 0) and merged == "x\nalpha section about deploys\nomega notes on shadow\ny\n"




def test_a_hand_rescued_ref_whose_lines_all_survive_is_present_and_pruned(world):
    """先行の手動救出が見出しだけ手直ししていても、本文行が逐語で残っていれば PRESENT。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    body = "".join(f"- 2026-11-13 observation line number {i} with enough length to count as content\n" for i in range(10))
    _strand(host, "2026-11-14", {
        "knowledge-base/raw/trade-logs/2026-11-13.md": "# 2026-11-13 Daily Trade Log\n" + body,
        "knowledge-base/wiki/log.md": "# log\n\n## 2026-11-13 wiki-daily\n" + body,
    })
    _advance_origin(other, {"knowledge-base/raw/trade-logs/2026-11-13.md": "# 2026-11-13 Daily Trade Log\n" + body,
                            "knowledge-base/wiki/log.md": "# log\n\n## 2026-11-13 wiki-daily (rescued by hand, 13th)\n" + body},
                    msg="manual rescue")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    assert _remote_refs(remote) == []
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip() == "manual rescue"


def test_present_ratio_counts_only_long_added_lines():
    patch = ("diff --git a/knowledge-base/a.md b/knowledge-base/a.md\n--- a/x\n+++ b/x\n"
             "+short\n+" + "L" * 50 + "\n+" + "M" * 50 + "\n")
    added = {"knowledge-base/a.md": krf.added_lines(patch)}
    assert added == {"knowledge-base/a.md": ["L" * 50, "M" * 50]}
    assert krf.present_ratio(added, {"knowledge-base/a.md": "x " + "L" * 50 + " y"}) == (1, 2)
    assert krf.present_ratio(added, {}) == (0, 2)


def test_repo_location_git_env_is_not_inherited(monkeypatch):
    """pre-commit 内の pytest は GIT_DIR / GIT_INDEX_FILE を export する — 継承すると実 repo を触る。"""
    monkeypatch.setenv("GIT_DIR", "/nonexistent/.git")
    monkeypatch.setenv("GIT_INDEX_FILE", "/nonexistent/index")
    monkeypatch.setenv("GIT_ASKPASS", "keep-me")
    env = krf.git_env()
    assert "GIT_DIR" not in env and "GIT_INDEX_FILE" not in env
    assert env["GIT_ASKPASS"] == "keep-me"


# --------------------------------------------------- PR #376 Codex findings (P1 / P2)
def test_present_against_an_unpublished_local_fold_is_not_pruned(world):
    """P1: ローカルだけで畳んだ後に --push --prune で再実行しても、HEAD が origin に無い間は
    PRESENT 判定で ref を消さない (消すと内容が origin に無いまま退避だけ失われる)。"""
    host, remote, root = world["host"], world["remote"], world["root"]
    _strand(host, "2026-11-14", {"knowledge-base/wiki/log.md": "# log\n- host entry long enough to count as content line\n"})
    runner = _clone(remote, os.path.join(root, "runner"), "runner")
    assert krf.main(["--repo", runner, "--in-place"]) == 0            # local fold, HEAD ahead of origin
    assert krf.main(["--repo", runner, "--in-place", "--push", "--prune"]) == 0
    assert len(_remote_refs(remote)) == 1                               # kept
    check = _clone(remote, os.path.join(root, "check"), "check")
    assert "host entry" not in _read(check, "knowledge-base/wiki/log.md")  # origin unchanged, nothing lost


def test_a_staged_non_kb_change_blocks_the_fold(world):
    """P2: `git commit` は index 全体を commit するので、非 KB の staged 変更があれば走らせない。"""
    host, remote, root = world["host"], world["remote"], world["root"]
    _strand(host, "2026-11-14", {"knowledge-base/wiki/log.md": "# log\n- host\n"})
    runner = _clone(remote, os.path.join(root, "runner"), "runner")
    _write(runner, "README.md", "unfinished code\n")
    _git(runner, "add", "README.md")
    assert krf.main(["--repo", runner, "--in-place", "--push"]) == 4
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip() == "seed"
    check = _clone(remote, os.path.join(root, "check"), "check")
    assert _read(check, "README.md") == "code\n"


def test_dirty_entries_rules():
    por = ("\0".join([" M knowledge-base/wiki/index.md",            # KB worktree change → blocks
                      " M knowledge-base/wiki/sessions/2026-11-14-session.md",  # hook noise → ignored
                      " M README.md",                                # non-KB unstaged → ignored (not committed)
                      "?? scratch.txt",                              # untracked → ignored
                      "R  tools/new.py", "tools/old.py",             # staged rename (2 entries) → blocks
                      " M knowledge-base/wiki/日本語 memo.md",       # non-ASCII, unquoted under -z → blocks
                      "M  tools/x.py"]) + "\0")                     # staged anywhere → blocks
    assert krf.dirty_entries(por) == [" M knowledge-base/wiki/index.md", "R  tools/new.py",
                                      " M knowledge-base/wiki/日本語 memo.md", "M  tools/x.py"]
    assert krf.dirty_entries("") == []
    # --include-sessions: session drafts block too, except the hook-noise file named explicitly
    por2 = "\0".join([" M knowledge-base/wiki/sessions/2026-11-01-session.md",
                       " M knowledge-base/wiki/sessions/2026-11-14-session.md"]) + "\0"
    assert krf.dirty_entries(por2, excludes=(), hook_noise="knowledge-base/wiki/sessions/2026-11-14-session.md") == \
        [" M knowledge-base/wiki/sessions/2026-11-01-session.md"]
    assert krf.dirty_entries(por2) == []


def test_a_conflict_in_a_non_ascii_path_with_spaces_is_restored_cleanly(world):
    """P2: patch header の regex 解析は core.quotePath で化ける → NUL 区切りの name-status で取る。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    path = "knowledge-base/wiki/日本語 memo.md"
    _advance_origin(other, {path: "# memo\nline A (origin)\n"}, msg="origin adds memo")
    _git(host, "pull", "-q", "--rebase", "origin", "main")  # host sees the memo, then goes stale
    _advance_origin(other, {path: "# memo\nline A (origin v2)\n"}, msg="origin edits memo")
    _strand(host, "2026-11-14", {path: "# memo\nline A (host)\n"})
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert _git(runner, "status", "--porcelain").stdout == ""
    assert _read(runner, path) == "# memo\nline A (origin v2)\n"
    assert len(_remote_refs(remote)) == 1


def test_an_untracked_file_in_the_way_is_never_deleted(world):
    """P1: patch が作るパスに user の untracked ファイルがあれば触らず CONFLICT。"""
    host, remote, root = world["host"], world["remote"], world["root"]
    _strand(host, "2026-11-14", {"knowledge-base/raw/trade-logs/2026-11-13.md": "# stranded\n",
                                 "knowledge-base/wiki/log.md": "# log\n- host\n"})
    runner = _clone(remote, os.path.join(root, "runner"), "runner")
    _write(runner, "knowledge-base/raw/trade-logs/2026-11-13.md", "user draft, uncommitted\n")
    assert krf.main(["--repo", runner, "--in-place", "--push", "--prune"]) == 2
    assert _read(runner, "knowledge-base/raw/trade-logs/2026-11-13.md") == "user draft, uncommitted\n"
    assert _read(runner, "knowledge-base/wiki/log.md") == "# log\n"  # nothing applied
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip() == "seed"
    assert len(_remote_refs(remote)) == 1


def test_an_unstaged_edit_to_a_non_ascii_kb_file_blocks_the_fold(world):
    """P1 (3 巡目): porcelain の引用パスで dirty 検査をすり抜け、_restore が user の下書きを HEAD で潰す。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    path = "knowledge-base/wiki/日本語.md"
    _advance_origin(other, {path: "# memo\nbase\n"}, msg="origin adds memo")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    _advance_origin(other, {path: "# memo\nbase (origin v2)\n"}, msg="origin edits memo")
    _strand(host, "2026-11-14", {path: "# memo\nbase (host)\n"})
    runner = _clone(remote, os.path.join(root, "runner"), "runner")
    _write(runner, path, "# memo\nuser draft, uncommitted\n")
    assert krf.main(["--repo", runner, "--in-place"]) == 4
    assert _read(runner, path) == "# memo\nuser draft, uncommitted\n"


def test_a_rejected_rename_is_fully_rolled_back_and_never_leaks_into_the_next_fold(world):
    """P1 (3 巡目): rename 元の削除が index に残ると、次の fold commit がその削除を push してしまう。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\nline A (origin)\nline B\n"})
    # ref 1: rename log.md + a conflicting index.md edit → must be rejected as a whole
    _git(host, "mv", "knowledge-base/wiki/log.md", "knowledge-base/wiki/log-renamed.md")
    _strand(host, "2026-11-13", {"knowledge-base/wiki/index.md": "# index\nline A (host)\nline B\n"})
    # ref 2: a clean addition that must still fold
    _strand(host, "2026-11-14", {"knowledge-base/raw/trade-logs/2026-11-14.md": "ok\n"})
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert _git(runner, "status", "--porcelain").stdout == ""
    assert _read(runner, "knowledge-base/wiki/log.md") == "# log\n"
    assert not os.path.exists(os.path.join(runner, "knowledge-base/wiki/log-renamed.md"))
    check = _clone(remote, os.path.join(root, "check"), "check")
    assert _read(check, "knowledge-base/wiki/log.md") == "# log\n"          # the deletion never reached origin
    assert _read(check, "knowledge-base/raw/trade-logs/2026-11-14.md") == "ok\n"
    files = _git(check, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.split()
    assert files == ["knowledge-base/raw/trade-logs/2026-11-14.md"]
    assert len(_remote_refs(remote)) == 2   # the rejected rename is still unaccounted → both refs kept


def test_a_clean_rename_folds_and_reaches_origin(world):
    """P2 (4 巡目): apply が消した旧パスを `git add` に渡すと pathspec エラーで止まる。"""
    host, remote, root = world["host"], world["remote"], world["root"]
    _git(host, "mv", "knowledge-base/wiki/log.md", "knowledge-base/wiki/log-renamed.md")
    _strand(host, "2026-11-14", {"knowledge-base/wiki/log-renamed.md": "# log\n- renamed and edited\n"})
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    assert _git(runner, "status", "--porcelain").stdout == ""
    check = _clone(remote, os.path.join(root, "check"), "check")
    assert not os.path.exists(os.path.join(check, "knowledge-base/wiki/log.md"))
    assert _read(check, "knowledge-base/wiki/log-renamed.md") == "# log\n- renamed and edited\n"
    assert _remote_refs(remote) == []


def test_include_sessions_makes_a_session_draft_block_the_fold(world):
    """P2 (5 巡目): --include-sessions では session log も patch に入るので、下書きは dirty として止める。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    path = "knowledge-base/wiki/sessions/2026-11-01-session.md"
    _advance_origin(other, {path: "# session\nbase\n"}, msg="origin adds session")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    _advance_origin(other, {path: "# session\nbase (origin v2)\n"}, msg="origin edits session")
    _strand(host, "2026-11-14", {path: "# session\nbase (host)\n"})
    runner = _clone(remote, os.path.join(root, "runner"), "runner")
    _write(runner, path, "# session\nuser draft, uncommitted\n")
    assert krf.main(["--repo", runner, "--in-place", "--include-sessions"]) == 4
    assert _read(runner, path) == "# session\nuser draft, uncommitted\n"
    # default run (sessions excluded) ignores the draft and folds nothing from that ref
    assert krf.main(["--repo", runner, "--in-place"]) == 0
    assert _read(runner, path) == "# session\nuser draft, uncommitted\n"


def test_unpublished_ancestor_saves_are_folded_before_the_tip_ref_is_pruned(world):
    """P1 (6 巡目): 前の save の push が落ちて ref を持たない commit も、次の ref の履歴から畳む。"""
    host, remote, root = world["host"], world["remote"], world["root"]
    # save 1: committed on stale main but its rescue push failed (no ref)
    _write(host, "knowledge-base/raw/trade-logs/2026-11-12.md", "# first save, never got its own ref\n")
    _git(host, "add", "-A")
    _git(host, "commit", "-q", "-m", "auto: KB session-end save (2026-11-13)")
    first = _git(host, "rev-parse", "HEAD").stdout.strip()
    # save 2: pushed as a rescue ref whose history carries save 1
    tip = _strand(host, "2026-11-14", {"knowledge-base/raw/trade-logs/2026-11-13.md": "# second save\n"})
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    check = _clone(remote, os.path.join(root, "check"), "check")
    assert _read(check, "knowledge-base/raw/trade-logs/2026-11-12.md").startswith("# first save")
    assert _read(check, "knowledge-base/raw/trade-logs/2026-11-13.md") == "# second save\n"
    log = _git(check, "log", "--format=%b", "-3").stdout
    assert first in log and tip in log          # one fold commit per rescued save
    assert _remote_refs(remote) == []


def test_worst_status_order():
    assert krf.worst_status(["EMPTY", "PRESENT", "FOLDED"]) == "FOLDED"
    assert krf.worst_status(["FOLDED", "CONFLICT", "MANUAL"]) == "CONFLICT"
    assert krf.worst_status([]) == "ANCESTOR"


def test_present_requires_every_changed_file_even_short_lined_ones(world):
    """P1 (7 巡目): 長い行を持たないファイル (1 行 JSON) が未到達なら PRESENT にしない。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    long_line = "- 2026-11-13 observation with enough length to count as a long content line here\n"
    _strand(host, "2026-11-14", {"knowledge-base/raw/report-2026-11-13.md": "# report\n" + long_line,
                                 "knowledge-base/raw/metrics-2026-11-13.json": '{"n": 1}\n'})
    # manual rescue brought only the report (heading edited), never the metrics file
    _advance_origin(other, {"knowledge-base/raw/report-2026-11-13.md": "# report (rescued by hand)\n" + long_line},
                    msg="manual rescue")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert len(_remote_refs(remote)) == 1
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip() == "manual rescue"


def test_rerunning_a_folded_hot_file_union_does_not_duplicate_the_addition(world):
    """P2 (7 巡目): theirs が ours に丸ごと含まれていれば union で二度足さない。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    _advance_origin(other, {"knowledge-base/wiki/log.md": "# log\n\n## 2026-11-13 autopilot\n- §7.6 deploy attribution for the restart\n"})
    _strand(host, "2026-11-14", {"knowledge-base/wiki/log.md": "# log\n\n## 2026-11-13 wiki-daily\n- fills 0 / closes 0, shadow 112 +11.5 pips\n"})
    runner1, rc1 = _run_tool(remote, root, "runner1", "--push")      # fold + push, ref kept (no --prune)
    assert rc1 == 0
    runner2, rc2 = _run_tool(remote, root, "runner2", "--push", "--prune")
    assert rc2 == 0
    check = _clone(remote, os.path.join(root, "check"), "check")
    log = _read(check, "knowledge-base/wiki/log.md")
    assert log.count("## 2026-11-13 wiki-daily") == 1 and log.count("## 2026-11-13 autopilot") == 1
    assert _remote_refs(remote) == []
    assert _git(runner2, "log", "-1", "--format=%s").stdout.strip().startswith("docs(KB): fold")  # run 2 added no commit


def test_union_keeps_ours_when_theirs_is_already_contained():
    text = ("# log\n<<<<<<< ours\n## A autopilot section about deploys\n## B wiki-daily section about shadow\n"
            "||||||| base\n=======\n## B wiki-daily section about shadow\n>>>>>>> theirs\n")
    merged, resolved, unresolved = krf.resolve_additive_conflicts(text)
    assert (resolved, unresolved) == (1, 0)
    assert merged == "# log\n## A autopilot section about deploys\n## B wiki-daily section about shadow\n"

