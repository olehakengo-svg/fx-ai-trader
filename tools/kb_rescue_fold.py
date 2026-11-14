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

やること (ref ごと、commit 日時の昇順。ref の tip だけでなく HEAD から未公開の祖先 commit を
全部、古い順に 1 commit ずつ畳む — 前の save の push が落ちていた場合の取りこぼし防止)
--------------------------------------
1. commit C が target (既定 origin/main) の祖先なら ANCESTOR (畳み済み)。
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
7. `--prune` で EMPTY、および **HEAD が remote に公開済みのときだけ** ANCESTOR / PRESENT /
   FOLDED の ref を origin から削除する (CONFLICT / MANUAL は残す = 次 run も報告される)。
   起動時に index の変更 (パス問わず) か knowledge-base/ の worktree 変更があれば exit 4。

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


def parse_name_status_z(raw: str) -> list[tuple[str, str, str | None]]:
    """`git diff --name-status -z` の出力 → [(status, path, src_path_or_None)]。NUL 区切りなので空白・非 ASCII・
    引用符付きパスでも壊れない (patch header の regex 解析は core.quotePath で化ける —
    PR #376 Codex P2)。rename/copy (R/C) は旧パス・新パスの 2 要素を持つ。"""
    items = raw.split("\0")
    out: list[tuple[str, str, str | None]] = []
    i = 0
    while i < len(items):
        st = items[i]
        if not st:
            i += 1
            continue
        if st[0] in ("R", "C") and i + 2 < len(items):
            # rename/copy: 旧パスも返す — rollback で両端を戻さないと apply が消した
            # 旧パスの削除が index に残り、次の fold commit に混入する (PR #376 Codex P1)
            out.append((st[0], items[i + 2], items[i + 1]))
            i += 3
        elif i + 1 < len(items):
            out.append((st[0], items[i + 1], None))
            i += 2
        else:
            break
    return out

def added_lines(patch_text: str) -> list[str]:
    """1 ファイル分の patch の `+` 行 (header 除く、strip 後 len > PRESENT_MIN_LINE_LEN)。"""
    out = []
    for ln in patch_text.splitlines():
        if ln.startswith("+") and not ln.startswith("+++"):
            body = ln[1:].strip()
            if len(body) > PRESENT_MIN_LINE_LEN:
                out.append(body)
    return out

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
        ours_text, theirs_text = "".join(ours), "".join(theirs)
        sim = difflib.SequenceMatcher(None, ours_text, theirs_text).ratio()
        if base is not None and not base and theirs_text.strip() and theirs_text.strip() in ours_text:
            # theirs は既に ours に丸ごと含まれている (再実行 / 先行 fold) → 二重化せず ours のまま
            # (PR #376 Codex P2 7 巡目)。resolved に数え、ファイルは無変更になる
            out.extend(ours)
            resolved += 1
        elif base is not None and not base and sim < UNION_MAX_SIMILARITY:
            out.extend(ours)
            out.extend(theirs)
            resolved += 1
        else:
            out.extend(lines[i:j + 1])
            unresolved += 1
        i = j + 1
    return "".join(out), resolved, unresolved


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


def dirty_entries(porcelain_z: str, excludes: Iterable[str] = DEFAULT_EXCLUDES,
                  hook_noise: str | None = None) -> list[str]:
    """`git status --porcelain -z` (NUL 区切り、引用なし — 非 ASCII パスも素のまま) から、
    fold を止めるべきエントリを返す:
    - index に載っている変更は**パスを問わず**全て (`git commit` は index 全体を commit するので、
      非 KB の staged 変更が fold commit に混入する — PR #376 Codex P2)
    - knowledge-base/ の worktree 変更のうち、**この run で patch に入り得るパス** (= `excludes` の
      外)。`--include-sessions` なら session log の下書きも止める (PR #376 Codex P2 5 巡目)。
      今日の session log (`hook_noise` = post-commit hook の複製) だけは常に除く
    `-z` では rename/copy のエントリが `XY new\0old\0` と 2 要素になる。
    """
    items = porcelain_z.split("\0")
    out = []
    i = 0
    while i < len(items):
        ent = items[i]
        if len(ent) < 4:
            i += 1
            continue
        x, y, path = ent[0], ent[1], ent[3:]
        i += 2 if x in ("R", "C") or y in ("R", "C") else 1
        if x == "?":
            continue
        if x != " ":
            out.append(ent)
        elif (y != " " and path.startswith(KB_ROOT) and not is_excluded(path, excludes)
              and path != hook_noise):
            out.append(ent)
    return out

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


def rescue_files(git: Git, sha: str, excludes: Iterable[str]) -> list[tuple[str, str, str | None]]:
    """patch が触る (status, path, rename 元) — NUL 区切りで取る。"""
    return parse_name_status_z(git.out("diff", "--name-status", "-z", f"{sha}^", sha, "--", *pathspec(excludes)))

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


def _content_present(git: Git, sha: str, paths: list[str]) -> tuple[bool, str]:
    """**全ファイル**が target に入っているかを判定する。長い追加行 (len > 40) を持つファイルは
    逐語残存 ≥ 95%、持たないファイル (1 行 JSON 等) はそのファイル分の patch が reverse-apply
    できるかで厳密に見る。1 ファイルでも未達なら PRESENT にしない (PR #376 Codex P1 7 巡目:
    短い行しかないファイルは比率の分母から消え、ref を prune しながら取りこぼしていた)。"""
    if not paths:
        return False, "no files"
    missing: list[str] = []
    hit = tot = 0
    for path in paths:
        patch_f = git.out("diff", "--no-color", "--no-ext-diff", f"{sha}^", sha, "--", path)
        long_lines = added_lines(patch_f)
        if long_lines:
            cur = git.run("show", f"HEAD:{path}", check=False)
            text = cur.stdout if cur.returncode == 0 else ""
            h = sum(1 for body in long_lines if body in text)
            hit += h
            tot += len(long_lines)
            if h / len(long_lines) < PRESENT_MIN_RATIO:
                missing.append(path)
        elif patch_f.strip():
            ok = git.run("apply", "--reverse", "--check", "-", check=False, input_text=patch_f).returncode == 0
            if not ok:
                missing.append(path)
    if missing:
        return False, f"{hit}/{tot} long lines verbatim; not accounted: {missing[:3]}"
    return True, f"{hit}/{tot} long added lines verbatim in target, {len(paths)} file(s) all accounted"


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


STATUS_RANK = {ST_CONFLICT: 5, ST_MANUAL: 4, ST_FOLDED: 3, ST_PRESENT: 2, ST_EMPTY: 1, ST_ANCESTOR: 0}


def worst_status(statuses: Iterable[str]) -> str:
    return max(statuses, key=lambda st: STATUS_RANK[st], default=ST_ANCESTOR)


def fold_commit(git: Git, ref: str, sha: str, excludes: Iterable[str],
                today_session: str | None) -> RefResult:
    """1 commit 分の KB diff を HEAD に畳む。"""
    if git.ok("merge-base", "--is-ancestor", sha, "HEAD"):
        return RefResult(ref, sha, ST_ANCESTOR, "already an ancestor of HEAD")
    n_parents = parent_count(git, sha)
    if n_parents != 1:
        return RefResult(ref, sha, ST_MANUAL, f"{n_parents} parents (hook commits are single-parent)")
    non_kb = [p for p in git.out("diff", "--name-only", "-z", f"{sha}^", sha).split("\0")
              if p and not p.startswith(KB_ROOT)]
    if non_kb:
        # hook は KB-only の履歴しか退避しない。混在していたら人が見る (黙って非 KB を捨てない)
        return RefResult(ref, sha, ST_MANUAL, f"non-KB paths in commit: {non_kb[:3]}")
    patch = rescue_patch(git, sha, excludes)
    if not patch.strip():
        return RefResult(ref, sha, ST_EMPTY, "no knowledge-base diff outside excluded paths")
    files = rescue_files(git, sha, excludes)
    paths = [p for _, p, _ in files] + [src for _, _, src in files if src]
    new_files = [p for st, p, _ in files if st in ("A", "R", "C")]
    if git.out("diff", "--cached", "--name-only").strip():
        # 前の ref の rollback 漏れなどで index が汚れていたら、次の commit に混入する前に止める
        return RefResult(ref, sha, ST_MANUAL, "index not clean before apply (fail-closed)", files=paths)
    # 作業木に **untracked** で同名ファイルがあると apply は失敗し、_restore がそれを消してしまう
    # (HEAD に無いので「patch が作った」と区別できない — PR #376 Codex P1)。触る前に止める。
    in_the_way = [p for p in new_files
                  if os.path.exists(os.path.join(git.cwd, p)) and not git.ok("cat-file", "-e", f"HEAD:{p}")]
    if in_the_way:
        return RefResult(ref, sha, ST_CONFLICT, f"untracked files in the way (left untouched): {in_the_way[:3]}",
                         files=paths)

    with tempfile.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8") as tf:
        tf.write(patch)
        patch_file = tf.name
    try:
        applied = git.run("-c", "merge.conflictStyle=diff3", "apply", "--3way", patch_file, check=False)
        detail = "committed"
        if applied.returncode != 0:
            pre_existing = [p for p in new_files if git.ok("cat-file", "-e", f"HEAD:{p}")]
            if pre_existing:
                # 新規ファイルが target に既にある = 先行 (手動) 救出の徴候。union で重複を
                # 作らないために人に回す。
                _restore(git, paths)
                present, why = _content_present(git, sha, paths)
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
                present, why = _content_present(git, sha, paths)
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
        # apply --3way は削除・rename 元の除去を index に既に載せている。消えたパスを
        # `git add` に渡すと pathspec エラーで落ちる (PR #376 Codex P2) ので、存在する
        # パス (union で書き直したファイルを含む) だけを add する。
        existing = [p for p in paths if os.path.lexists(os.path.join(git.cwd, p))]
        if existing:
            git.run("add", "-A", "--", *existing)
        if not git.out("diff", "--cached", "--name-only").strip():
            return RefResult(ref, sha, ST_PRESENT, "apply produced no change", files=paths)
        subject = git.out("log", "-1", "--format=%s", sha).strip()
        date = git.out("log", "-1", "--format=%ci", sha).strip()
        msg = (f"docs(KB): fold {ref.split('/', 1)[-1]} (座礁救出 自動、rule:R3)\n\n"
               f"source: {sha} \"{subject}\" ({date})\n"
               f"tool: tools/kb_rescue_fold.py (git apply --3way diff3, sessions excluded; {detail})\n")
        # post-commit hook (scripts/hooks/git-post-commit.sh) は今日の session log に commit 行を
        # 複製する (無ければ template を作る)。**commit 前の内容を退避して戻す** — `checkout --`
        # で HEAD に戻すと、その file に user の未 commit 下書きがあった場合に消える
        # (PR #376 Codex P1 8 巡目)。この run が生成した差分だけを打ち消す。
        session_full = os.path.join(git.cwd, today_session) if today_session else None
        session_before: bytes | None = None
        if session_full and os.path.exists(session_full):
            with open(session_full, "rb") as f:
                session_before = f.read()
        git.run("commit", "-q", "-m", msg)
        if session_full:
            if session_before is not None:
                with open(session_full, "rb") as f:
                    after = f.read()
                if after != session_before:
                    with open(session_full, "wb") as f:
                        f.write(session_before)
            elif os.path.exists(session_full) and not git.ok("cat-file", "-e", f"HEAD:{today_session}"):
                os.remove(session_full)   # hook が作った untracked template だけを消す
        return RefResult(ref, sha, ST_FOLDED, detail, files=paths,
                         commit=git.out("rev-parse", "HEAD").strip())
    finally:
        os.unlink(patch_file)


def fold_ref(git: Git, ref: str, tip: str, excludes: Iterable[str], today_session: str | None,
             seen: dict[str, RefResult]) -> RefResult:
    """退避 ref の tip だけでなく **HEAD から見て未公開の祖先 commit 全部** を古い順に畳む。
    前の session-end save の push が落ちていると、その commit は自分の ref を持たず次の ref の
    履歴にだけ乗っている (hook は `origin/main..VALIDATED` 全件を KB-only 検査して tip を押す —
    PR #376 Codex P1)。ref の status は構成 commit の最悪値。"""
    commits = [c for c in git.out("rev-list", "--reverse", "--first-parent", f"HEAD..{tip}").split() if c]
    if not commits:
        return RefResult(ref, tip, ST_ANCESTOR, "already an ancestor of HEAD")
    parts: list[RefResult] = []
    for c in commits:
        if c not in seen:
            seen[c] = fold_commit(git, ref, c, excludes, today_session)
        parts.append(seen[c])
    status = worst_status(r.status for r in parts)
    detail = "; ".join(f"{r.sha[:9]}={r.status}" + (f" ({r.detail})" if r.status in (ST_CONFLICT, ST_MANUAL) else "")
                       for r in parts)
    files = sorted({f for r in parts for f in r.files})
    folded = [r.commit for r in parts if r.status == ST_FOLDED and r.commit]
    return RefResult(ref, tip, status, f"{len(parts)} commit(s): {detail}"[:600], files=files,
                     commit=folded[-1] if folded else "")


def push_with_retry(git: Git, remote: str, branch: str) -> bool:
    if git.ok("push", remote, f"HEAD:refs/heads/{branch}"):
        return True
    git.run("fetch", remote, branch)
    if not git.ok("rebase", f"{remote}/{branch}"):
        git.run("rebase", "--abort", check=False)
        return False
    return git.ok("push", remote, f"HEAD:refs/heads/{branch}")


def head_is_published(git: Git, remote: str, branch: str) -> bool:
    """HEAD が <remote>/<branch> の祖先 (= ここで見た内容が origin にある) か。fetch し直してから判定。"""
    git.run("fetch", "--quiet", remote, branch)
    return git.ok("merge-base", "--is-ancestor", "HEAD", f"{remote}/{branch}")


def prune_refs(git: Git, remote: str, branch: str, summary: Summary) -> list[str]:
    """ANCESTOR / PRESENT / FOLDED は **HEAD 基準**の判定なので、HEAD が remote に公開されて
    いるときだけ prune する (ローカルだけで畳んだ状態で ref を消すと内容が origin に無いまま
    退避 ref だけ失われる — PR #376 Codex P1)。EMPTY は内容を持たないので常に prune 可。"""
    published = head_is_published(git, remote, branch)
    pruned = []
    for r in summary.results:
        ok = r.status == ST_EMPTY or (published and r.status in (ST_ANCESTOR, ST_PRESENT, ST_FOLDED))
        if ok:
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
    dirty = dirty_entries(git.out("status", "--porcelain", "-z", "--untracked-files=no"),
                          excludes, hook_noise=today_session_path())
    if dirty:
        raise GitError(f"uncommitted changes (fail-closed; staged anywhere, or knowledge-base/ worktree): {dirty[:3]}")

    summary = Summary(target=target, remote=args.remote)
    refs = list_rescue_refs(git, args.remote)
    if args.limit:
        refs = refs[-args.limit:]
    seen: dict[str, RefResult] = {}
    for ref, sha in refs:
        summary.results.append(fold_ref(git, ref, sha, excludes, today_session_path(), seen))
    # push は **commit 単位**の FOLDED で判定する: CONFLICT commit を含む ref (status = CONFLICT)
    # の中の clean commit も畳まれているので、ref 単位で見ると取りこぼす
    folded_commits = sum(1 for r in seen.values() if r.status == ST_FOLDED)
    if args.push and folded_commits:
        summary.pushed = push_with_retry(git, args.remote, args.branch)
    if args.prune:
        summary.pruned = prune_refs(git, args.remote, args.branch, summary)

    report = {"summary": {s: summary.count(s) for s in
                          (ST_FOLDED, ST_PRESENT, ST_EMPTY, ST_ANCESTOR, ST_CONFLICT, ST_MANUAL)},
              "folded_commits": folded_commits, "pushed": summary.pushed, "pruned": summary.pruned,
              "results": [asdict(r) for r in summary.results]}
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    for r in summary.results:
        print(f"{r.status:9} {r.ref}  {r.detail[:120]}")
    print(f"-- folded {report['summary'][ST_FOLDED]} / present {report['summary'][ST_PRESENT]} / "
          f"empty {report['summary'][ST_EMPTY]} / ancestor {report['summary'][ST_ANCESTOR]} / "
          f"conflict {report['summary'][ST_CONFLICT]} / manual {report['summary'][ST_MANUAL]}; "
          f"folded_commits={folded_commits} pushed={summary.pushed} pruned={len(summary.pruned)}")
    if args.push and folded_commits and not summary.pushed:
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
