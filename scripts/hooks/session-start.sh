#!/usr/bin/env bash
# SessionStart Hook — KB自動読み込み
# index(Tier+State) + 未解決事項 + lessons + daily report を注入
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel)"
KB="$ROOT/knowledge-base/wiki"

LATEST_SESSION=$(ls -t "$KB/sessions/"*.md 2>/dev/null | head -1 || true)

# 各セクションを取得（ファイル未存在でも続行）
INDEX=$(head -60 "$KB/index.md" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
UNRESOLVED_LABEL=$(basename "${LATEST_SESSION:-unknown}" .md 2>/dev/null || echo "unknown")
UNRESOLVED=$(grep -A 50 '## 未解決事項' "$LATEST_SESSION" 2>/dev/null | head -20 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
LESSONS=$(head -25 "$KB/lessons/index.md" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)

DAILY_FILE=$(ls -t "$ROOT/knowledge-base/raw/trade-logs/"*-daily.md 2>/dev/null | head -1 || true)
DAILY=""
if [[ -n "$DAILY_FILE" ]]; then
    DAILY=$(head -15 "$DAILY_FILE" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
fi

cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"=== KB AUTO-LOAD ===\\n\\n--- INDEX (Tier + System State) ---\\n${INDEX}\\n\\n--- UNRESOLVED ITEMS (${UNRESOLVED_LABEL}) ---\\n${UNRESOLVED}\\n\\n--- LESSONS (Top Mistakes) ---\\n${LESSONS}\\n\\n--- LATEST DAILY REPORT ---\\n${DAILY}\\n=== END KB AUTO-LOAD ==="}}
ENDJSON
