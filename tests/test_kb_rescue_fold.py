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


def test_a_regenerated_portfolio_header_block_resolves_to_ours():
    # 2026-11-25〜26 cron 4 run 連続 CONFLICT 3/3 の根: sync_kb_index.py が毎 run 再生成する
    # `## Current Portfolio (auto-synced, <date>)` 見出しに wiki-daily が時変の注記を書き足すため、
    # 座礁 commit を畳む頃には origin 側の見出しが差し替わっていて base ≠ 空 = union 対象外だった。
    # 生成見出し 1 行 vs 1 行の block は target (ours) の再生成版を採る。本文側の hunk は別 block。
    text = ("<!-- KB_PORTFOLIO_START -->\n<<<<<<< ours\n## Current Portfolio (auto-synced, 2026-11-25)\n"
            "||||||| base\n## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 09:54Z — 2 fills)\n"
            "=======\n## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 22:51Z re-run — 0 fills)\n"
            ">>>>>>> theirs\n\n### ELITE_LIVE\n")
    merged, resolved, unresolved = krf.resolve_additive_conflicts(text)
    assert (resolved, unresolved) == (1, 0)
    assert merged == "<!-- KB_PORTFOLIO_START -->\n## Current Portfolio (auto-synced, 2026-11-25)\n\n### ELITE_LIVE\n"
    # 非 diff3 (base marker なし) や、片側が見出し以外の行を含む block は従来どおり人が見る
    no_base = ("<<<<<<< ours\n## Current Portfolio (auto-synced, 2026-11-25)\n=======\n"
               "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified)\n>>>>>>> theirs\n")
    assert krf.resolve_additive_conflicts(no_base)[1:] == (0, 1)
    with_body = ("<<<<<<< ours\n## Current Portfolio (auto-synced, 2026-11-25)\n||||||| base\n"
                 "## Current Portfolio (auto-synced, 2026-10-30)\n=======\n"
                 "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified)\n- extra body line\n>>>>>>> theirs\n")
    assert krf.resolve_additive_conflicts(with_body)[1:] == (0, 1)
    # 見出しが別物 (System State 等) なら対象外
    other = ("<<<<<<< ours\n## System State — last wiki-daily 11-26\n||||||| base\n## System State — last wiki-daily 11-24\n"
             "=======\n## System State — last wiki-daily 11-25\n>>>>>>> theirs\n")
    assert krf.resolve_additive_conflicts(other)[1:] == (0, 1)


def test_a_wiki_daily_note_on_the_regenerated_portfolio_header_folds_and_keeps_ours(world):
    """2026-11-25〜26 の実 ref (b4b5fd25e 系 3 本) の再現: wiki-daily は `## Current Portfolio (auto-synced, …)`
    見出しに注記を書き足すが、origin 側は sync_kb_index.py が毎 run その 1 行を再生成する → base ≠ 空。
    見出し block は ours (再生成版) を採り、本文 (trade log) は畳まれ、ref は prune される。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    body = "".join(f"- 2026-11-24 22:51Z re-run observation line number {i} long enough to count\n" for i in range(10))
    seed_hdr = "## Current Portfolio (auto-synced, 2026-10-30)\n"
    note_hdr = "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 22:51Z re-run — 0 fills)\n"
    regen_hdr = "## Current Portfolio (auto-synced, 2026-11-25)\n"
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + seed_hdr + "line A\nline B\n"}, msg="seed header")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    _strand(host, "2026-11-25", {
        "knowledge-base/raw/trade-logs/2026-11-24.md": "# 2026-11-24 Daily Trade Log\n" + body,
        "knowledge-base/wiki/index.md": "# index\n" + note_hdr + "line A\nline B\n",
    })
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\nline B\n"},
                    msg="sync_kb_index regenerates the header")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    assert _remote_refs(remote) == []
    check = _clone(remote, os.path.join(root, "check"), "check")
    idx = _read(check, "knowledge-base/wiki/index.md")
    assert idx == "# index\n" + regen_hdr + "line A\nline B\n"      # ours kept, no markers, note not resurrected
    assert _read(check, "knowledge-base/raw/trade-logs/2026-11-24.md") == "# 2026-11-24 Daily Trade Log\n" + body
    assert "generated-header" in _git(check, "log", "-1", "--format=%b").stdout


def test_a_hand_folded_ref_whose_only_missing_line_is_the_regenerated_header_is_present(world):
    """PR 経路 (autopilot が手で畳んで merge) の後、cron が同じ ref を再評価する: 本文は全て target に
    あり、欠けているのは意図的に捨てた生成見出しの注記版だけ → PRESENT → prune (永久 CONFLICT にしない)。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    body = "".join(f"- 2026-11-24 22:51Z re-run observation line number {i} long enough to count\n" for i in range(10))
    seed_hdr = "## Current Portfolio (auto-synced, 2026-10-30)\n"
    note_hdr = "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 22:51Z re-run — 0 fills)\n"
    regen_hdr = "## Current Portfolio (auto-synced, 2026-11-25)\n"
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + seed_hdr + "line A\nline B\n"}, msg="seed header")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    _strand(host, "2026-11-25", {
        "knowledge-base/raw/trade-logs/2026-11-24.md": "# 2026-11-24 Daily Trade Log\n" + body,
        "knowledge-base/wiki/index.md": "# index\n" + note_hdr + "line A\nline B\n",
    })
    _advance_origin(other, {"knowledge-base/raw/trade-logs/2026-11-24.md": "# 2026-11-24 Daily Trade Log\n" + body,
                            "knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\nline B\n"},
                    msg="manual rescue PR keeps the regenerated header")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    assert _remote_refs(remote) == []
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip() == "manual rescue PR keeps the regenerated header"
    assert note_hdr not in _read(runner, "knowledge-base/wiki/index.md")


def test_header_credit_does_not_hide_a_lost_short_body_edit(world):
    """PR #391 Codex P2: 座礁側が生成見出し + 短い本文行 (≤ 40 字) を変え、origin が同じ本文行を別内容に
    変えた場合、見出し credit だけで 1/1 accounted = PRESENT → prune されてはいけない。見出し credit を
    使う file は非見出しの追加行を長さ不問で全行検証し、届いていなければ CONFLICT のまま ref を残す。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    seed_hdr = "## Current Portfolio (auto-synced, 2026-10-30)\n"
    note_hdr = "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 22:51Z re-run — 0 fills)\n"
    regen_hdr = "## Current Portfolio (auto-synced, 2026-11-25)\n"
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + seed_hdr + "line A\nline B\n"}, msg="seed header")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    sha = _strand(host, "2026-11-25", {"knowledge-base/wiki/index.md": "# index\n" + note_hdr + "line A\n- obs 7\n"})
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\n- obs 9\n"},
                    msg="origin regenerates the header and rewrites the short body line")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert _remote_refs(remote) == [f"kb-rescue/main-2026-11-25-{sha}"]   # kept for a human
    assert "- obs 7" not in _read(runner, "knowledge-base/wiki/index.md")  # nothing partially applied
    assert not krf.has_conflict_markers(_read(runner, "knowledge-base/wiki/index.md"))
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip().startswith("origin regenerates")


def test_header_credit_does_not_hide_a_lost_body_deletion(world):
    """PR #391 Codex P2 (2 巡目): 座礁側が生成見出しを変え + 本文行を **削除**、origin が同じ行を別内容に
    編集した場合、削除は追加行を生まないので追加行検証だけでは素通りする。非見出しの削除行が target に
    残っていれば「削除は届いていない」= CONFLICT のまま ref を残す。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    seed_hdr = "## Current Portfolio (auto-synced, 2026-10-30)\n"
    note_hdr = "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 22:51Z re-run — 0 fills)\n"
    regen_hdr = "## Current Portfolio (auto-synced, 2026-11-25)\n"
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + seed_hdr + "line A\n- stale entry\n"}, msg="seed header")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    sha = _strand(host, "2026-11-25", {"knowledge-base/wiki/index.md": "# index\n" + note_hdr + "line A\n"})
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\n- stale entry (edited)\n"},
                    msg="origin regenerates the header and edits the entry the host deleted")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert _remote_refs(remote) == [f"kb-rescue/main-2026-11-25-{sha}"]
    assert "- stale entry (edited)" in _read(runner, "knowledge-base/wiki/index.md")   # target untouched
    assert not krf.has_conflict_markers(_read(runner, "knowledge-base/wiki/index.md"))
    # 3 巡目 P2: 旧文字列を含まない **置換** も pickaxe は「消えた」と見る → 置換 hunk (+ 行あり) は
    # 純削除の証拠にしない → CONFLICT のまま
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\n- revised observation\n"},
                    msg="origin rewrites the entry with unrelated text")
    runner1, rc1 = _run_tool(remote, root, "runner1", "--push", "--prune")
    assert rc1 == 2 and _remote_refs(remote) == [f"kb-rescue/main-2026-11-25-{sha}"]
    assert "- revised observation" in _read(runner1, "knowledge-base/wiki/index.md")
    # 同じ削除が target 側でも済んでいれば (origin が同じ行を消した) PRESENT → prune
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\n"}, msg="origin deletes it too")
    runner2, rc2 = _run_tool(remote, root, "runner2", "--push", "--prune")
    assert rc2 == 0 and _remote_refs(remote) == []


def test_an_unrelated_addition_in_the_same_hunk_is_not_proof_of_a_deletion(world):
    """PR #391 Codex P2 (4 巡目): 座礁側が見出し注記 + 本文行の削除 + 無関係な行の追加を同じ hunk で行い、
    origin が削除対象の行を別内容に書き換え + 同じ無関係行を持つ場合、追加行の存在だけで削除を認めては
    いけない。削除は「target 履歴で純削除」か「target が座礁側と同じ置換をした」場合のみ届いたと見る。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    seed_hdr = "## Current Portfolio (auto-synced, 2026-10-30)\n"
    note_hdr = "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 22:51Z re-run — 0 fills)\n"
    regen_hdr = "## Current Portfolio (auto-synced, 2026-11-25)\n"
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + seed_hdr + "line A\n- stale entry\n"}, msg="seed header")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    sha = _strand(host, "2026-11-25", {"knowledge-base/wiki/index.md": "# index\n" + note_hdr + "line A\n- new note\n"})
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\n- revised observation\n- new note\n"},
                    msg="origin rewrites the deleted entry and already has the note")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert _remote_refs(remote) == [f"kb-rescue/main-2026-11-25-{sha}"]
    assert "- revised observation" in _read(runner, "knowledge-base/wiki/index.md")
    # target が座礁側と同じ置換 (- stale entry → - new note) をしていれば PRESENT → prune
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\n- new note\n"},
                    msg="origin applies the same replacement")
    runner2, rc2 = _run_tool(remote, root, "runner2", "--push", "--prune")
    assert rc2 == 0 and _remote_refs(remote) == []


def test_a_hand_applied_replacement_that_keeps_the_old_text_is_present(world):
    """PR #391 Codex P2 (5 巡目): 手畳みが本文の置換 `- obs 7` → `- obs 7 (verified)` と新規 trade log を
    適用し、生成見出しは再生成版のままにした ref は PRESENT → prune でなければならない。pickaxe は旧文字列が
    新行に残ると命中しないので、座礁 hunk の追加行が旧行を含み target に存在することで置換を認める。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    body = "".join(f"- 2026-11-24 22:51Z re-run observation line number {i} long enough to count\n" for i in range(10))
    seed_hdr = "## Current Portfolio (auto-synced, 2026-10-30)\n"
    note_hdr = "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 22:51Z re-run — 0 fills)\n"
    regen_hdr = "## Current Portfolio (auto-synced, 2026-11-25)\n"
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + seed_hdr + "line A\n- obs 7\n"}, msg="seed header")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    _strand(host, "2026-11-25", {
        "knowledge-base/raw/trade-logs/2026-11-24.md": "# 2026-11-24 Daily Trade Log\n" + body,
        "knowledge-base/wiki/index.md": "# index\n" + note_hdr + "line A\n- obs 7 (verified)\n",
    })
    _advance_origin(other, {"knowledge-base/raw/trade-logs/2026-11-24.md": "# 2026-11-24 Daily Trade Log\n" + body,
                            "knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\n- obs 7 (verified)\n"},
                    msg="manual rescue applies the replacement and keeps the regenerated header")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    assert _remote_refs(remote) == []
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip().startswith("manual rescue applies")


def test_a_separately_added_new_line_is_not_proof_the_replacement_landed(world):
    """PR #391 Codex P2 (6 巡目): 座礁側が `- obs 7` → `- obs 7 (verified)` の置換、origin が `- obs 7` を
    `- obs 9` に書き換えつつ `- obs 7 (verified)` を**別途**追加した場合、新行の存在 (包含) だけで置換を
    認めてはいけない。target 履歴に「旧行削除 + 新行 (⊆ 座礁追加行)」の hunk があるときだけ届いたと見る。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    seed_hdr = "## Current Portfolio (auto-synced, 2026-10-30)\n"
    note_hdr = "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 22:51Z re-run — 0 fills)\n"
    regen_hdr = "## Current Portfolio (auto-synced, 2026-11-25)\n"
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + seed_hdr + "line A\n- obs 7\n"}, msg="seed header")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    sha = _strand(host, "2026-11-25", {"knowledge-base/wiki/index.md": "# index\n" + note_hdr + "line A\n- obs 7 (verified)\n"})
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\n- obs 9\n- obs 7 (verified)\n"},
                    msg="origin rewrites obs 7 to obs 9 and adds the verified line separately")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert _remote_refs(remote) == [f"kb-rescue/main-2026-11-25-{sha}"]
    assert "- obs 9" in _read(runner, "knowledge-base/wiki/index.md")


def test_a_short_addition_needs_whole_line_history_evidence(world):
    """PR #391 Codex P2 (7 巡目): 座礁側が見出し注記 + `- obs 7` を追記、origin が見出し再生成 + `- obs 70` を
    追記した場合、`line_superseded` の部分一致 (`- obs 7` ⊂ `- obs 70`) で追加行を「差し替え済み」と誤認して
    はいけない。実際の到達経路は 2 つ: (1) 純追記 union の「theirs は ours に含まれる」判定が部分一致で
    `- obs 7` ⊂ `- obs 70` → ours のまま = 無変更 → PRESENT、(2) 見出し credit 経路の `line_superseded`
    (部分一致)。どちらも短い行は行単位一致を要求する (長い行の verbatim superset は従来どおり)。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    seed_hdr = "## Current Portfolio (auto-synced, 2026-10-30)\n"
    note_hdr = "## Current Portfolio (auto-synced, 2026-10-30; wiki-daily verified 2026-11-24 22:51Z re-run — 0 fills)\n"
    regen_hdr = "## Current Portfolio (auto-synced, 2026-11-25)\n"
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + seed_hdr + "line A\n"}, msg="seed header")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    sha = _strand(host, "2026-11-25", {"knowledge-base/wiki/index.md": "# index\n" + note_hdr + "line A\n- obs 7\n"})
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + regen_hdr + "line A\n- obs 70\n"},
                    msg="origin regenerates the header and appends a different observation")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert _remote_refs(remote) == [f"kb-rescue/main-2026-11-25-{sha}"]
    assert "- obs 7\n" not in _read(runner, "knowledge-base/wiki/index.md")
    # pure 関数側の pin: 短い行は行単位、長い行は部分一致 (verbatim superset) のまま
    assert not krf._theirs_contained(["- obs 70\n"], ["- obs 7\n"])
    assert krf._theirs_contained(["- obs 7\n", "- obs 70\n"], ["- obs 7\n"])
    long = "- 2026-11-13: fills 0 / closes 0 / NAV ¥271,681 and a long enough tail\n"
    assert krf._theirs_contained([long[:-1] + " (rescued, edited)\n"], [long])


def test_a_handwritten_draft_in_todays_session_log_survives_the_fold(world):
    """P1 (8 巡目): 今日の session log の未 commit 下書きは、post-commit 掃除で消してはいけない。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    today = krf.today_session_path()
    _advance_origin(other, {today: "# Session Log\n\n## Phase 1\n- committed line\n"}, msg="origin adds today's log")
    _strand(host, "2026-11-14", {"knowledge-base/raw/trade-logs/2026-11-13.md": "# stranded\n"})
    runner = _clone(remote, os.path.join(root, "runner"), "runner")
    draft = "# Session Log\n\n## Phase 1\n- committed line\n- handwritten draft, not yet committed\n"
    _write(runner, today, draft)
    assert krf.main(["--repo", runner, "--in-place", "--push", "--prune"]) == 0
    assert _read(runner, today) == draft
    check = _clone(remote, os.path.join(root, "check"), "check")
    assert _read(check, "knowledge-base/raw/trade-logs/2026-11-13.md") == "# stranded\n"
    assert "handwritten draft" not in _read(check, today)   # the draft was never committed by the tool



def test_a_superseded_status_line_in_a_hot_file_still_counts_as_present(world):
    """2026-11-15 cron 3 run 連続 CONFLICT 14/14 の根: index.md の NAV 行 / 見出しは毎 run が上書きする
    時変 status 行で、先行救出された後に次の run が差し替えると逐語残存では永久に「欠落」になる。
    target 履歴に一度入った行 (pickaxe) は差し替え済みとして accounted → PRESENT → prune。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    body = "".join(f"- 2026-11-06 observation line number {i} with enough length to count as content\n" for i in range(10))
    status_old = "- 現在: NAV 2026-11-06 03:18Z 実測 ¥270,000 (status row rewritten by every wiki-daily run)\n"
    status_new = "- 現在: NAV 2026-11-11 05:49Z 実測 ¥271,000 (status row rewritten by every wiki-daily run)\n"
    _strand(host, "2026-11-06", {
        "knowledge-base/raw/trade-logs/2026-11-06.md": "# 2026-11-06 Daily Trade Log\n" + body,
        "knowledge-base/wiki/index.md": "# index\n" + status_old + "line A\nline B\n",
    })
    _advance_origin(other, {"knowledge-base/raw/trade-logs/2026-11-06.md": "# 2026-11-06 Daily Trade Log\n" + body,
                            "knowledge-base/wiki/index.md": "# index\n" + status_old + "line A\nline B\n"},
                    msg="manual rescue")
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + status_new + "line A\nline B\n"},
                    msg="next wiki-daily supersedes the status row")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 0
    assert _remote_refs(remote) == []
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip() == "next wiki-daily supersedes the status row"
    assert status_old not in _read(runner, "knowledge-base/wiki/index.md")  # 旧 status 行を蘇らせない


def test_a_lost_long_lined_file_is_not_present_even_when_hot_file_lines_were_superseded(world):
    """差し替え済み判定は履歴に一度入った行にしか効かない: 届いていないファイルは pickaxe 0 → CONFLICT のまま。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    body = "".join(f"- 2026-11-06 observation line number {i} with enough length to count as content\n" for i in range(5))
    status_old = "- 現在: NAV 2026-11-06 03:18Z 実測 ¥270,000 (status row rewritten by every wiki-daily run)\n"
    status_new = "- 現在: NAV 2026-11-11 05:49Z 実測 ¥271,000 (status row rewritten by every wiki-daily run)\n"
    _strand(host, "2026-11-06", {
        "knowledge-base/raw/trade-logs/2026-11-06.md": "# 2026-11-06 Daily Trade Log\n" + body,
        "knowledge-base/raw/observations-2026-11-06.md": "# obs\n" + body.replace("observation", "never rescued"),
        "knowledge-base/wiki/index.md": "# index\n" + status_old + "line A\nline B\n",
    })
    _advance_origin(other, {"knowledge-base/raw/trade-logs/2026-11-06.md": "# 2026-11-06 Daily Trade Log\n" + body,
                            "knowledge-base/wiki/index.md": "# index\n" + status_old + "line A\nline B\n"},
                    msg="manual rescue (forgot the observations file)")
    _advance_origin(other, {"knowledge-base/wiki/index.md": "# index\n" + status_new + "line A\nline B\n"},
                    msg="next wiki-daily")
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert len(_remote_refs(remote)) == 1
    assert _git(runner, "log", "-1", "--format=%s").stdout.strip() == "next wiki-daily"
    assert not os.path.exists(os.path.join(runner, "knowledge-base/raw/observations-2026-11-06.md"))


def test_line_superseded_ignores_history_reachable_from_the_stranded_parent_and_deletions(world):
    """PR #378 Codex P2: 座礁 commit の親から到達できる履歴 (origin が足して消した行、同秒でも) は
    「差し替え済み」ではない。`-S` は削除側にも一致するので、命中 commit に行が実在することまで見る。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    git = krf.Git(other)
    line = "- a long line that origin once had and deleted before the stranded commit existed\n"
    _advance_origin(other, {"knowledge-base/wiki/log.md": "# log\n" + line}, msg="origin adds")
    added = _git(other, "rev-parse", "HEAD").stdout.strip()
    _advance_origin(other, {"knowledge-base/wiki/log.md": "# log\n"}, msg="origin deletes")
    deleted = _git(other, "rev-parse", "HEAD").stdout.strip()
    body = line.strip()
    # 親 = 削除後 (host が pull した状態): 追加も削除も先行履歴 → 偽
    assert krf.line_superseded(git, "knowledge-base/wiki/log.md", body, deleted) is False
    # 親 = 追加後: 範囲に残るのは削除 commit だけ (-S は一致するが行は実在しない) → 偽
    assert krf.line_superseded(git, "knowledge-base/wiki/log.md", body, added) is False
    # 親 = 追加前: 追加 commit が範囲に入り、その file に行が実在 → 真
    assert krf.line_superseded(git, "knowledge-base/wiki/log.md", body, f"{added}^") is True
    assert krf.line_superseded(git, "knowledge-base/wiki/log.md", "", f"{added}^") is False


def test_a_line_origin_deleted_and_the_host_re_added_is_not_present(world):
    """Codex P2 の再現: origin が足して消した行を host が同秒内に再追加して座礁 → 届いていないので
    PRESENT にせず、ref を prune しない (以前の --since 判定は PRESENT → prune で退避ごと失っていた)。"""
    host, other, remote, root = world["host"], world["other"], world["remote"], world["root"]
    line = "- 2026-11-16 a long observation line that origin added, deleted, and the host re-added\n"
    note = "".join(f"- 2026-11-16 unrelated note number {i} long enough to be a content line of its own\n" for i in range(3))
    _advance_origin(other, {"knowledge-base/wiki/log.md": "# log\n" + line}, msg="origin adds")
    _advance_origin(other, {"knowledge-base/wiki/log.md": "# log\n"}, msg="origin deletes")
    _git(host, "pull", "-q", "--rebase", "origin", "main")
    # origin が先に進む (host はここから stale) + 同じ領域に別の追記 → 3-way は conflict
    _advance_origin(other, {"knowledge-base/wiki/log.md": "# log\n" + note,
                            "knowledge-base/raw/trade-logs/2026-11-16.md": "# 2026-11-16 Daily Trade Log\n" + note},
                    msg="origin moves on")
    _strand(host, "2026-11-16", {"knowledge-base/wiki/log.md": "# log\n" + line,
                                 "knowledge-base/raw/trade-logs/2026-11-16.md": "# 2026-11-16 Daily Trade Log\n" + line})
    runner, rc = _run_tool(remote, root, "runner", "--push", "--prune")
    assert rc == 2
    assert len(_remote_refs(remote)) == 1
    assert line not in _read(runner, "knowledge-base/wiki/log.md")
