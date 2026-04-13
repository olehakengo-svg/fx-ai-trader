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

# v8.9: 宣言トラッカー — 未完了の宣言がないか確認
echo "[pre-commit] Checking declaration tracker..."
TODAY=$(date +%Y-%m-%d)
SESSION_FILE="$REPO_ROOT/knowledge-base/wiki/sessions/${TODAY}-session.md"
if [[ -f "$SESSION_FILE" ]]; then
    PENDING=$(grep -c '^\- \[ \].*🔊' "$SESSION_FILE" 2>/dev/null || echo 0)
    if [[ "$PENDING" -gt 0 ]]; then
        echo ""
        echo "⚠️  未完了の宣言が${PENDING}件あります:"
        grep '^\- \[ \].*🔊' "$SESSION_FILE" 2>/dev/null | head -5
        echo ""
        echo "コミット前に完了させるか、意図的にスキップする場合はこのまま続行。"
        echo "(ブロックはしません — 警告のみ)"
    fi
fi

echo "[pre-commit] All checks passed."
