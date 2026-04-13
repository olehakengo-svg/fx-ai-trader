#!/usr/bin/env bash
# UserPromptSubmit Hook — KB読込+書込フロー
# 毎回のユーザーメッセージ時に:
#   1. KB最新状態を注入（index + 未解決 + lessons要約）
#   2. session logの最終更新時刻を確認 → 古ければ更新リマインド
#   3. 前回のKB注入からの差分を検出（変更があれば追加注入）
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
KB="$ROOT/knowledge-base/wiki"
TODAY=$(date +%Y-%m-%d)
SESSION_FILE="$KB/sessions/${TODAY}-session.md"

# --- KB読込（軽量版: index先頭30行 + 未解決 + 目標） ---
INDEX=""
if [[ -f "$KB/index.md" ]]; then
    # 目標 + Tier分類 + System State のみ（詳細はリンク先で参照）
    INDEX=$(head -30 "$KB/index.md" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
fi

# 未解決事項（最新session logから）
UNRESOLVED=""
LATEST_SESSION=$(ls -t "$KB/sessions/"*.md 2>/dev/null | head -1 || true)
if [[ -n "$LATEST_SESSION" ]]; then
    UNRESOLVED=$(grep -A 15 '## 未解決事項' "$LATEST_SESSION" 2>/dev/null | head -15 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
fi

# Lessons要約（先頭10行）
LESSONS=""
if [[ -f "$KB/lessons/index.md" ]]; then
    LESSONS=$(head -10 "$KB/lessons/index.md" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
fi

# Session log更新リマインド
SESSION_REMIND=""
if [[ -f "$SESSION_FILE" ]]; then
    LAST_MOD=$(stat -f %m "$SESSION_FILE" 2>/dev/null || stat -c %Y "$SESSION_FILE" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    AGE=$(( NOW - LAST_MOD ))
    if (( AGE > 1800 )); then
        # 30分以上更新なし
        SESSION_REMIND="⚠️ Session log未更新(${AGE}秒前)。重要な判断・変更があればsession logに記録すること。"
    fi
else
    SESSION_REMIND="⚠️ 本日のsession logが未作成。初回コミット時に自動生成される。"
fi

# 最新コミット（KBドリフト検知）
LAST_COMMIT=$(git log -1 --format='%h %s' 2>/dev/null || echo "unknown")
KB_LAST_COMMIT=$(git log -1 --format='%h' -- knowledge-base/ 2>/dev/null || echo "none")

cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"=== KB SYNC ===\\n${INDEX}\\n--- UNRESOLVED ---\\n${UNRESOLVED}\\n--- LESSONS ---\\n${LESSONS}\\n--- SESSION ---\\n${SESSION_REMIND}\\n--- LAST COMMIT: ${LAST_COMMIT} | KB LAST: ${KB_LAST_COMMIT} ---\\n=== END KB SYNC ==="}}
ENDJSON
