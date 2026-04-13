#!/usr/bin/env bash
# Stop Hook — セッション終了時のKB書込
# 1. session logのコミット自動追記を確認
# 2. 未コミットのKB変更があればauto-commit
# 3. git push（KB変更の永続化）
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
KB="$ROOT/knowledge-base"
TODAY=$(date +%Y-%m-%d)

# 1. pre-compact.sh を実行（session log生成/更新）
# v8.9: stdout も抑制（JSON出力を汚染しないように）
bash "$ROOT/scripts/hooks/pre-compact.sh" >/dev/null 2>/dev/null || true

# 2. 未コミットのKB変更をauto-commit
KB_CHANGES=$(git diff --name-only -- "$KB/" 2>/dev/null || true)
KB_UNTRACKED=$(git ls-files --others --exclude-standard -- "$KB/" 2>/dev/null || true)

if [[ -n "$KB_CHANGES" ]] || [[ -n "$KB_UNTRACKED" ]]; then
    git add "$KB/" >/dev/null 2>/dev/null || true
    git commit -m "auto: KB session-end save (${TODAY})

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>" >/dev/null 2>/dev/null || true

    echo "KB changes auto-committed" >&2
fi

# 3. push（リモートにKB永続化）
git push origin main >/dev/null 2>/dev/null || true

echo '{"systemMessage":"Session log saved to KB."}'
