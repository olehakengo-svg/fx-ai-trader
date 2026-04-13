#!/usr/bin/env bash
# FX AI Trader — pre-commit hook
# Runs fast checks (<10s) before allowing a commit.
# Install: ln -sf ../../scripts/hooks/git-pre-commit.sh .git/hooks/pre-commit

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"

echo "[pre-commit] Running tests..."
python3 -m pytest "$REPO_ROOT/tests/" -x -q || {
    echo "[pre-commit] Tests failed. Commit blocked."
    exit 1
}

echo "[pre-commit] Running consistency check..."
python3 "$REPO_ROOT/scripts/check.py" --quiet || {
    echo "[pre-commit] Consistency check failed. Commit blocked."
    exit 1
}

echo "[pre-commit] All checks passed."
