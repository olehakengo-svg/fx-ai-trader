"""`scripts/hooks/session-end-save.sh` must never leave KB work only local.

2026-09-22: this hook was the GENERATOR of the recurring `main` divergence.
Step 2 commits KB changes to whatever HEAD is (in the primary checkout: `main`),
and step 3's `git push origin main` fails whenever local `main` is behind
origin.  The failure was only echoed to stderr, so every day added a local-only
commit and the divergence was re-created (measured ahead 8 / behind 112).

These tests drive the real script against a real throwaway repo + bare remote,
rather than grepping its text — a grep pin would pass on a script that prints
the right message and still strands the commit.
"""
import os
import shutil
import subprocess
import tempfile

import pytest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "scripts", "hooks", "session-end-save.sh")


def _clean_env():
    """Git env WITHOUT the caller's GIT_* leakage.

    These tests are also run by the repo's own pre-commit hook, which invokes
    pytest from inside `git commit` — so `GIT_DIR`, `GIT_INDEX_FILE`,
    `GIT_WORK_TREE` etc. are exported.  Inherited, they make every `git` call
    below operate on the REAL repository regardless of `cwd`, which both
    invalidates the test and fires the real pre-commit hook against a temp
    directory.  Strip them (found by the pre-commit hook itself, 2026-09-22).
    """
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("GIT_") or k in ("GIT_ASKPASS",)}
    env.setdefault("HOME", os.path.expanduser("~"))
    return env


def _git(cwd, *args, check=True):
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *args],
                          cwd=cwd, check=check, capture_output=True, text=True,
                          env=_clean_env())


@pytest.fixture()
def repo():
    """A work repo on `main` with an origin it can be made to diverge from."""
    root = tempfile.mkdtemp(prefix="kb-hook-")
    remote = os.path.join(root, "remote.git")
    work = os.path.join(root, "work")
    other = os.path.join(root, "other")
    _git(root, "init", "--bare", "-b", "main", remote)
    _git(root, "clone", remote, work)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        _git(work, "config", k, v)

    # The hook calls pre-compact.sh and writes under knowledge-base/.
    os.makedirs(os.path.join(work, "scripts", "hooks"), exist_ok=True)
    os.makedirs(os.path.join(work, "knowledge-base", "wiki", "sessions"),
                exist_ok=True)
    shutil.copy(HOOK, os.path.join(work, "scripts", "hooks",
                                   "session-end-save.sh"))
    with open(os.path.join(work, "scripts", "hooks", "pre-compact.sh"), "w") as f:
        f.write("#!/usr/bin/env bash\nexit 0\n")
    with open(os.path.join(work, "knowledge-base", "seed.md"), "w") as f:
        f.write("seed\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "seed")
    _git(work, "push", "origin", "main")

    _git(root, "clone", remote, other)
    for k, v in (("user.email", "o@o"), ("user.name", "o")):
        _git(other, "config", k, v)
    yield {"root": root, "remote": remote, "work": work, "other": other}
    shutil.rmtree(root, ignore_errors=True)


def _run_hook(work):
    # The hook makes its own `git commit`; point hooks at nothing so the real
    # repo's pre-commit cannot fire against this temp tree.
    env = _clean_env()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "core.hooksPath"
    env["GIT_CONFIG_VALUE_0"] = "/dev/null"
    return subprocess.run(["bash", os.path.join(work, "scripts", "hooks",
                                                "session-end-save.sh")],
                          cwd=work, capture_output=True, text=True, env=env)


def _remote_branches(remote):
    out = _git(remote, "for-each-ref", "--format=%(refname:short)",
               "refs/heads").stdout.split()
    return set(out)


def test_kb_work_reaches_origin_even_when_main_push_is_rejected(repo):
    """KNOWN-NG STATE: local main is behind origin, so `push origin main` fails."""
    # Someone else advances origin/main -> our push will be rejected.
    with open(os.path.join(repo["other"], "knowledge-base", "theirs.md"), "w") as f:
        f.write("theirs\n")
    _git(repo["other"], "add", "-A")
    _git(repo["other"], "commit", "-m", "theirs")
    _git(repo["other"], "push", "origin", "main")

    # Local KB work, uncommitted, exactly as a session would leave it.
    with open(os.path.join(repo["work"], "knowledge-base", "mine.md"), "w") as f:
        f.write("mine\n")

    res = _run_hook(repo["work"])
    assert res.returncode == 0, res.stderr

    head = _git(repo["work"], "rev-parse", "HEAD").stdout.strip()
    rescue = [b for b in _remote_branches(repo["remote"]) if b.startswith("kb-rescue/")]
    assert rescue, (
        "the commit must be pushed to a rescue branch when main is rejected — "
        f"origin has only {_remote_branches(repo['remote'])}; stderr={res.stderr}")
    on_remote = _git(repo["remote"], "rev-parse", rescue[0]).stdout.strip()
    assert on_remote == head, (
        "the rescue branch must carry the very commit that could not reach main")
    assert "退避" in res.stderr, "the escape must be reported, not silent"

    # origin/main itself is untouched: this is a rescue, not a force-push.
    assert _git(repo["remote"], "rev-parse", "main").stdout.strip() != head


def test_the_happy_path_is_unchanged(repo):
    """Counter-pin: when main accepts the push, no rescue branch is created."""
    with open(os.path.join(repo["work"], "knowledge-base", "mine.md"), "w") as f:
        f.write("mine\n")

    res = _run_hook(repo["work"])
    assert res.returncode == 0, res.stderr

    head = _git(repo["work"], "rev-parse", "HEAD").stdout.strip()
    assert _git(repo["remote"], "rev-parse", "main").stdout.strip() == head
    assert not [b for b in _remote_branches(repo["remote"])
                if b.startswith("kb-rescue/")], (
        "a successful push must not leave a rescue branch behind")
    assert "退避" not in res.stderr


def test_nothing_is_committed_when_the_kb_is_clean(repo):
    """Counter-pin: the hook must not manufacture empty commits."""
    before = _git(repo["work"], "rev-parse", "HEAD").stdout.strip()
    res = _run_hook(repo["work"])
    assert res.returncode == 0, res.stderr
    assert _git(repo["work"], "rev-parse", "HEAD").stdout.strip() == before
    assert not [b for b in _remote_branches(repo["remote"])
                if b.startswith("kb-rescue/")]
