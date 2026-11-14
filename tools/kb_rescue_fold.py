#!/usr/bin/env python3
"""kb-rescue ref を origin/main に畳む — 座礁 KB 救出の後半を自動化 (2026-11-14、rule:R3)。

背景
----
`scripts/hooks/session-end-save.sh` は、ローカル main が origin より behind で
`git push origin main` が落ちたとき、その run の KB 自動 commit を
`refs/heads/kb-rescue/main-<date>-<sha>` として origin へ退避する (PR #276)。
しかし退避 ref を **origin/main に畳む作業は手作業のまま**で、autopilot が
`git diff <parent> <sha> -- <files>` を `git apply --3way` する「座礁救出 PR」を
2026-10-13 から 2026-11-13 の間に 12 本積んだ (sprint-0922 close review §4 #8 は
これを「供給の 21〜38%」の固定費と見積もった)。本 tool はその手順をそのまま
機械化する。

やること (ref ごと、commit 日時の昇順)
--------------------------------------
1. ref の commit C が target (既定 origin/main) の祖先なら ANCESTOR (畳み済み)。
2. 親が 1 つでなければ MANUAL (hook が作る commit は常に単一親。違えば人が見る)。
3. patch = `git diff C^ C -- knowledge-base/` から `wiki/sessions/` を除いたもの
   (session log の自動行は post-commit hook の複製で、救出対象にしない —
   [[2026-11-12-session]] 移植法)。空なら EMPTY。
4. `git apply --3way` (diff3 marker) で target の作業木に当てる。clean なら
   1 ref = 1 commit (FOLDED)。conflict block が **全て base 空の純追記** (origin 側も
   同じ場所に追記していた、hot file の典型) なら ours + theirs の union で解決して
   FOLDED (CLAUDE.md の hot file union 規律)。ただし patch が新規作成するファイルが
   target に既にある (= 先行の手動救出) か、ours / theirs が似すぎている (同じ追記の
   別版) 場合は union しない。当たらないとき、patch の追加行 (len > 40) が target に
   逐語で ≥ 95% あるか `git apply --reverse --check` が通れば内容は既に target にある
   = PRESENT (先行の手動救出)。どちらも駄目なら CONFLICT — 作業木を戻して次へ
   (fail-closed: 部分適用は commit しない)。
5. 適用後に行頭 conflict marker (`<<<<<<<` / `=======` / `>>>>>>>`) が変更ファイル
   に残っていれば CONFLICT 扱い (2026-10-20 PR #338 の再発防止、行頭アンカー)。
6. `--push` で target branch へ push (non-ff なら fetch + rebase を 1 回だけ再試行)。
7. `--prune` で ANCESTOR / EMPTY / PRESENT、および push 済み FOLDED の ref を
   origin から削除する (CONFLICT / MANUAL は残す = 次 run も報告される)。

触らないもの: 価格データ・DB・live 経路・registry JSON の条件文。knowledge-base/
以外のパスは patch に含めない (hook 側も KB-only を検査済み、二重ガード)。

exit code: 0 = 問題なし / 2 = CONFLICT or MANUAL が残った / 3 = push 失敗 /
4 = git 失敗 (fail-closed、部分結果を「完了」として印字しない)。

使い方
------
    # GitHub Actions (日次): fresh clone の main 上で
    python3 tools/kb_rescue_fold.py --in-place --push --prune --json out.json

    # ローカル (autopilot worktree、branch 上に畳んで PR に載せる)
    python3 tools/kb_rescue_fold.py --in-place
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from typing import Iterable

RESCUE_PREFIX = "kb-rescue/"
KB_ROOT = "knowledge-base/"
DEFAULT_EXCLUDES = ("knowledge-base/wiki/sessions/",)
MARKER_PAT = re.compile(r"^(<<<<<<< |=======$|>>>>>>> )", re.MULTILINE)
NEW_FILE_PAT = re.compile(r"^diff --git a/(\S+) b/(\S+)\nnew file mode", re.MULTILINE)
# union 解決を諦める類似度 (ours と theirs が「同じ追記の別版」なら人が見る)
UNION_MAX_SIMILARITY = 0.8
# 「内容は既に target にある」判定: patch の追加行 (len > 40) が target の同ファイルに
# 逐語で ≥ 95% 残っていれば PRESENT (先行の手動救出が見出し等を手直ししていても拾う)
PRESENT_MIN_LINE_LEN = 40
PRESENT_MIN_RATIO = 0.95
GIT_TIMEOUT = 300

ST_ANCESTOR = "ANCESTOR"
ST_MANUAL = "MANUAL"
ST_EMPTY = "EMPTY"
ST_FOLDED = "FOLDED"
ST_PRESENT = "PRESENT"
ST_CONFLICT = "CONFLICT"
PRUNE_OK_STATES = frozenset({ST_ANCESTOR, ST_EMPTY, ST_PRESENT})


class GitError(RuntimeError):
    pass


@dataclass
class RefResult:
    ref: str
    sha: str
    status: str
    detail: str = ""
    files: list[str] = field(default_factory=list)
    commit: str = ""


@dataclass
class Summary:
    target: str
    remote: str
    results: list[RefResult] = field(default_factory=list)
    pushed: bool = False
    pruned: list[str] = field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)


# --------------------------------------------------------------------------- git
# 呼び出し元 (pre-commit hook 内の pytest など) が export する repo 位置系の GIT_* を
# 剥がす。継承すると `--repo` に関係なく**実 repo** を操作してしまう
# (MEMORY feedback_git_env_leak_tests_touch_real_repo、2026-09-22)。
_REPO_LOCATION_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                      "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX", "GIT_COMMON_DIR")


def git_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in _REPO_LOCATION_ENV}


class Git:
    def __init__(self, cwd: str):
        self.cwd = cwd

    def run(self, *args: str, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess:
        try:
            p = subprocess.run(["git", *args], cwd=self.cwd, capture_output=True, text=True,
                               input=input_text, timeout=GIT_TIMEOUT, env=git_env())
        except (OSError, subprocess.TimeoutExpired) as e:  # pragma: no cover - env
            raise GitError(f"git {' '.join(args)}: {e}") from e
        if check and p.returncode != 0:
            raise GitError(f"git {' '.join(args)} -> {p.returncode}: {p.stderr.strip()[:500]}")
        return p

    def out(self, *args: str) -> str:
        return self.run(*args).stdout

    def ok(self, *args: str, input_text: str | None = None) -> bool:
        return self.run(*args, check=False, input_text=input_text).returncode == 0


# -------------------------------------------------------------------------- pure
def has_conflict_markers(text: str) -> bool:
    """行頭アンカーの marker 検査 (部分文字列 assert は KB 本文で偽陽性になる)。"""
    return bool(MARKER_PAT.search(text))


def patch_paths(patch: str) -> list[str]:
    """`diff --git a/X b/X` 行から変更パスを取る (rename は b 側)。"""
    paths: list[str] = []
    for m in re.finditer(r"^diff --git a/(\S+) b/(\S+)$", patch, re.MULTILINE):
        p = m.group(2)
        if p not in paths:
            paths.append(p)
    return paths


def new_file_paths(patch: str) -> list[str]:
    """patch が新規作成するパス (`new file mode`)。target に既にあれば「先行救出済み」の徴候。"""
    return [m.group(2) for m in NEW_FILE_PAT.finditer(patch)]


def resolve_additive_conflicts(text: str) -> tuple[str, int, int]:
    """diff3 形式の conflict block のうち **base が空 (両側とも純追記)** のものを
    ours + theirs の union に解決する (CLAUDE.md: hot file conflict は union 解決)。

    base が空でない / diff3 の base marker が無い / ours と theirs が似すぎている
    (同じ追記の別版 = 先行救出で手直しされた形) block は触らず残す (fail-closed)。
    戻り値 = (新テキスト, 解決数, 未解決数)。
    """
    out: list[str] = []
    resolved = unresolved = 0
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        ln = lines[i]
        if not ln.startswith("<<<<<<< "):
            out.append(ln)
            i += 1
            continue
        j = i + 1
        ours: list[str] = []
        base: list[str] | None = None
        theirs: list[str] = []
        section = ours
        closed = False
        while j < len(lines):
            cur = lines[j]
            if cur.startswith("||||||| "):
                base = []
                section = base
            elif cur.rstrip("\r\n") == "=======":
                section = theirs
            elif cur.startswith(">>>>>>> "):
                closed = True
                break
            else:
                section.append(cur)
            j += 1
        if not closed:
            out.extend(lines[i:])
            unresolved += 1
            break
        sim = difflib.SequenceMatcher(None, "".join(ours), "".join(theirs)).ratio()
        if base is not None and not base and sim < UNION_MAX_SIMILARITY:
            out.extend(ours)
            out.extend(theirs)
            resolved += 1
        else:
            out.extend(lines[i:j + 1])
            unresolved += 1
        i = j + 1
    return "".join(out), resolved, unresolved


def added_lines_by_path(patch: str) -> dict[str, list[str]]:
    """patch の `+` 行 (header 除く、strip 後 len > PRESENT_MIN_LINE_LEN) をパス別に。"""
    out: dict[str, list[str]] = {}
    cur: str | None = None
    for ln in patch.splitlines():
        m = re.match(r"^diff --git a/(\S+) b/(\S+)$", ln)
        if m:
            cur = m.group(2)
            out.setdefault(cur, [])
            continue
        if cur and ln.startswith("+") and not ln.startswith("+++"):
            body = ln[1:].strip()
            if len(body) > PRESENT_MIN_LINE_LEN:
                out[cur].append(body)
    return out


def present_ratio(added: dict[str, list[str]], current: dict[str, str]) -> tuple[int, int]:
    """(target に逐語で存在する追加行数, 追加行総数)。"""
    hit = tot = 0
    for path, lines in added.items():
        text = current.get(path, "")
        for body in lines:
            tot += 1
            if body in text:
                hit += 1
    return hit, tot


def is_excluded(path: str, excludes: Iterable[str]) -> bool:
    return any(path.startswith(x) for x in excludes)


def pathspec(excludes: Iterable[str]) -> list[str]:
    return [KB_ROOT, *[f":(exclude){x}" for x in excludes]]


def sort_refs_by_time(entries: list[tuple[str, str, int]]) -> list[tuple[str, str]]:
    """(ref, sha, committer_ts) → 時刻昇順 (同時刻は ref 名で安定)。"""
    return [(r, s) for r, s, _ in sorted(entries, key=lambda e: (e[2], e[0]))]


# --------------------------------------------------------------------------- core
def list_rescue_refs(git: Git, remote: str) -> list[tuple[str, str]]:
    out = git.out("for-each-ref", "--format=%(refname:short)%09%(objectname)%09%(committerdate:unix)",
                  f"refs/remotes/{remote}/{RESCUE_PREFIX}")
    entries: list[tuple[str, str, int]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        entries.append((parts[0], parts[1], int(parts[2])))
    return sort_refs_by_time(entries)


def rescue_patch(git: Git, sha: str, excludes: Iterable[str]) -> str:
    return git.out("diff", "--no-color", "--no-ext-diff", f"{sha}^", sha, "--", *pathspec(excludes))


def parent_count(git: Git, sha: str) -> int:
    line = git.out("rev-list", "--parents", "-n", "1", sha).split()
    return len(line) - 1


def _restore(git: Git, paths: list[str]) -> None:
    """失敗した apply の痕跡を、その patch が触るパスに限って戻す。"""
    for p in paths:
        if git.ok("cat-file", "-e", f"HEAD:{p}"):
            git.run("checkout", "HEAD", "--", p)
        else:
            git.run("rm", "-f", "-q", "--ignore-unmatch", "--", p, check=False)
            full = os.path.join(git.cwd, p)
            if os.path.exists(full):
                os.remove(full)


def _content_present(git: Git, patch: str) -> tuple[bool, str]:
    added = added_lines_by_path(patch)
    current = {}
    for path in added:
        p = git.run("show", f"HEAD:{path}", check=False)
        current[path] = p.stdout if p.returncode == 0 else ""
    hit, tot = present_ratio(added, current)
    ok = tot > 0 and hit / tot >= PRESENT_MIN_RATIO
    return ok, f"{hit}/{tot} added lines already verbatim in target"


def _changed_files_have_markers(git: Git, paths: list[str]) -> list[str]:
    bad = []
    for p in paths:
        full = os.path.join(git.cwd, p)
        if not os.path.isfile(full):
            continue
        with open(full, encoding="utf-8", errors="replace") as f:
            if has_conflict_markers(f.read()):
                bad.append(p)
    return bad


def fold_one(git: Git, ref: str, sha: str, excludes: Iterable[str],
             today_session: str | None) -> RefResult:
    if git.ok("merge-base", "--is-ancestor", sha, "HEAD"):
        return RefResult(ref, sha, ST_ANCESTOR, "already an ancestor of HEAD")
    n_parents = parent_count(git, sha)
    if n_parents != 1:
        return RefResult(ref, sha, ST_MANUAL, f"{n_parents} parents (hook commits are single-parent)")
    patch = rescue_patch(git, sha, excludes)
    if not patch.strip():
        return RefResult(ref, sha, ST_EMPTY, "no knowledge-base diff outside excluded paths")
    paths = patch_paths(patch)

    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8") as tf:
        tf.write(patch)
        patch_file = tf.name
    try:
        applied = git.run("-c", "merge.conflictStyle=diff3", "apply", "--3way", patch_file, check=False)
        detail = "committed"
        if applied.returncode != 0:
            pre_existing = [p for p in new_file_paths(patch) if git.ok("cat-file", "-e", f"HEAD:{p}")]
            if pre_existing:
                # 新規ファイルが target に既にある = 先行 (手動) 救出の徴候。union で重複を
                # 作らないために人に回す。
                _restore(git, paths)
                present, why = _content_present(git, patch)
                if present or git.ok("apply", "--reverse", "--check", patch_file):
                    return RefResult(ref, sha, ST_PRESENT, f"content already in target ({why})", files=paths)
                return RefResult(ref, sha, ST_CONFLICT,
                                 f"new files already in target (prior rescue?): {pre_existing[:3]}; {why}",
                                 files=paths)
            n_res = n_unres = 0
            for p in _changed_files_have_markers(git, paths):
                full = os.path.join(git.cwd, p)
                with open(full, encoding="utf-8") as f:
                    merged, r, u = resolve_additive_conflicts(f.read())
                n_res += r
                n_unres += u
                if u == 0:
                    with open(full, "w", encoding="utf-8") as f:
                        f.write(merged)
            if n_unres or not n_res:
                _restore(git, paths)
                present, why = _content_present(git, patch)
                if present or git.ok("apply", "--reverse", "--check", patch_file):
                    return RefResult(ref, sha, ST_PRESENT, f"content already in target ({why})", files=paths)
                return RefResult(ref, sha, ST_CONFLICT,
                                 f"unresolved {n_unres} block(s); {why}; " + applied.stderr.strip()[-300:],
                                 files=paths)
            detail = f"committed (union-resolved {n_res} additive block(s))"
        bad = _changed_files_have_markers(git, paths)
        if bad:
            _restore(git, paths)
            return RefResult(ref, sha, ST_CONFLICT, f"conflict markers left in {bad}", files=paths)
        git.run("add", "-A", "--", *paths)
        if not git.out("diff", "--cached", "--name-only").strip():
            return RefResult(ref, sha, ST_PRESENT, "apply produced no change", files=paths)
        subject = git.out("log", "-1", "--format=%s", sha).strip()
        date = git.out("log", "-1", "--format=%ci", sha).strip()
        msg = (f"docs(KB): fold {ref.split('/', 1)[-1]} (座礁救出 自動、rule:R3)\n\n"
               f"source: {sha} \"{subject}\" ({date})\n"
               f"tool: tools/kb_rescue_fold.py (git apply --3way diff3, sessions excluded; {detail})\n")
        git.run("commit", "-q", "-m", msg)
        if today_session and os.path.exists(os.path.join(git.cwd, today_session)):
            # post-commit hook (scripts/hooks/git-post-commit.sh) が今日の session log に
            # commit 行を複製する。次の apply に混ぜないよう捨てる (CLAUDE.md 自走原則)。
            git.run("checkout", "--", today_session, check=False)
        return RefResult(ref, sha, ST_FOLDED, detail, files=paths,
                         commit=git.out("rev-parse", "HEAD").strip())
    finally:
        os.unlink(patch_file)


def push_with_retry(git: Git, remote: str, branch: str) -> bool:
    if git.ok("push", remote, f"HEAD:refs/heads/{branch}"):
        return True
    git.run("fetch", remote, branch)
    if not git.ok("rebase", f"{remote}/{branch}"):
        git.run("rebase", "--abort", check=False)
        return False
    return git.ok("push", remote, f"HEAD:refs/heads/{branch}")


def prune_refs(git: Git, remote: str, summary: Summary) -> list[str]:
    pruned = []
    for r in summary.results:
        if r.status in PRUNE_OK_STATES or (r.status == ST_FOLDED and summary.pushed):
            name = r.ref.split("/", 1)[-1]  # origin/kb-rescue/... → kb-rescue/...
            if git.ok("push", remote, "--delete", name):
                pruned.append(name)
    return pruned


def today_session_path() -> str:
    import datetime as _dt
    return f"knowledge-base/wiki/sessions/{_dt.date.today().isoformat()}-session.md"


def run(args: argparse.Namespace) -> int:
    git = Git(args.repo)
    excludes = () if args.include_sessions else DEFAULT_EXCLUDES
    git.run("fetch", "--quiet", args.remote, args.branch,
            f"+refs/heads/{RESCUE_PREFIX}*:refs/remotes/{args.remote}/{RESCUE_PREFIX}*")
    target = f"{args.remote}/{args.branch}"
    if not args.in_place:
        raise GitError("only --in-place is implemented (run inside a checkout of the target branch)")
    dirty = [ln for ln in git.out("status", "--porcelain", "--", KB_ROOT).splitlines()
             if ln.strip() and not ln[3:].startswith(DEFAULT_EXCLUDES[0])]
    if dirty:
        raise GitError(f"knowledge-base/ has uncommitted changes (fail-closed): {dirty[:3]}")

    summary = Summary(target=target, remote=args.remote)
    refs = list_rescue_refs(git, args.remote)
    if args.limit:
        refs = refs[-args.limit:]
    for ref, sha in refs:
        summary.results.append(fold_one(git, ref, sha, excludes,
                                        today_session=today_session_path()))
    if args.push and summary.count(ST_FOLDED):
        summary.pushed = push_with_retry(git, args.remote, args.branch)
    if args.prune:
        summary.pruned = prune_refs(git, args.remote, summary)

    report = {"summary": {s: summary.count(s) for s in
                          (ST_FOLDED, ST_PRESENT, ST_EMPTY, ST_ANCESTOR, ST_CONFLICT, ST_MANUAL)},
              "pushed": summary.pushed, "pruned": summary.pruned,
              "results": [asdict(r) for r in summary.results]}
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    for r in summary.results:
        print(f"{r.status:9} {r.ref}  {r.detail[:120]}")
    print(f"-- folded {report['summary'][ST_FOLDED]} / present {report['summary'][ST_PRESENT]} / "
          f"empty {report['summary'][ST_EMPTY]} / ancestor {report['summary'][ST_ANCESTOR]} / "
          f"conflict {report['summary'][ST_CONFLICT]} / manual {report['summary'][ST_MANUAL]}; "
          f"pushed={summary.pushed} pruned={len(summary.pruned)}")
    if args.push and summary.count(ST_FOLDED) and not summary.pushed:
        return 3
    if summary.count(ST_CONFLICT) or summary.count(ST_MANUAL):
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="git checkout to operate in")
    ap.add_argument("--remote", default="origin")
    ap.add_argument("--branch", default="main", help="target branch on the remote")
    ap.add_argument("--in-place", action="store_true",
                    help="apply onto the current HEAD of --repo (must be a checkout of the target)")
    ap.add_argument("--push", action="store_true", help="push HEAD to <remote>/<branch> after folding")
    ap.add_argument("--prune", action="store_true",
                    help="delete rescue refs whose content is in the target (never CONFLICT/MANUAL)")
    ap.add_argument("--include-sessions", action="store_true",
                    help="also fold wiki/sessions/ (default: excluded, post-commit hook noise)")
    ap.add_argument("--limit", type=int, default=0, help="only the newest N refs")
    ap.add_argument("--json", help="write the report here")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except GitError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
