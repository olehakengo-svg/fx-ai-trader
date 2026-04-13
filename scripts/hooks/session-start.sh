#!/usr/bin/env bash
# SessionStart Hook — KB自動読み込み
# index(Tier+State) + 未解決事項 + lessons + daily report + analyst-memory を注入
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
KB="$ROOT/knowledge-base/wiki"

LATEST_SESSION=$(ls -t "$KB/sessions/"*.md 2>/dev/null | head -1 || true)

# 各セクションを取得（ファイル未存在でも続行）
INDEX=$(head -60 "$KB/index.md" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
UNRESOLVED_LABEL=$(basename "${LATEST_SESSION:-unknown}" .md 2>/dev/null || echo "unknown")
UNRESOLVED=$(grep -A 50 '## 未解決事項' "$LATEST_SESSION" 2>/dev/null | head -20 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
# v8.9: セッション要約 — 直近のPhaseとコミット一覧（文脈理解のため）
SESSION_SUMMARY=""
if [[ -n "$LATEST_SESSION" ]]; then
    # 最新Phase（### Phase で始まる最後のセクション）+ コミット一覧
    SESSION_SUMMARY=$(awk '/^### Phase/{buf=""; capture=1} capture{buf=buf $0 "\\n"} /^## コミット一覧/{c=1} c{buf2=buf2 $0 "\\n"} END{print buf; print buf2}' "$LATEST_SESSION" 2>/dev/null | tail -30 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
fi
# 教訓の実文を抽出（head -25はヘッダーのみで実際の教訓が0件だった）
LESSONS=$(grep -E '^- 教訓:|^### \[\[lesson-' "$KB/lessons/index.md" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)

DAILY_FILE=$(ls -t "$ROOT/knowledge-base/raw/trade-logs/"*-daily.md 2>/dev/null | head -1 || true)
DAILY=""
if [[ -n "$DAILY_FILE" ]]; then
    DAILY=$(head -15 "$DAILY_FILE" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
fi

# Analyst Memory（末尾20行 = 最新の学習結果）
MEMORY_FILE="$ROOT/knowledge-base/raw/trade-logs/analyst-memory.md"
ANALYST=""
if [[ -f "$MEMORY_FILE" ]]; then
    ANALYST=$(tail -20 "$MEMORY_FILE" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
fi

# KBドリフト検知（check.py --quiet の警告出力を注入）
DRIFT=""
if [[ -f "$ROOT/scripts/check.py" ]]; then
    DRIFT_RAW=$(python3 "$ROOT/scripts/check.py" --quiet 2>/dev/null || true)
    if echo "$DRIFT_RAW" | grep -q '⚠️'; then
        DRIFT=$(echo "$DRIFT_RAW" | grep '⚠️' | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
    fi
fi

cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"=== KB AUTO-LOAD ===\\n\\n--- INDEX (Tier + System State) ---\\n${INDEX}\\n\\n--- SESSION CONTEXT (${UNRESOLVED_LABEL}) ---\\n${SESSION_SUMMARY}\\n\\n--- UNRESOLVED ITEMS ---\\n${UNRESOLVED}\\n\\n--- LESSONS (過去の間違い — 繰り返すな) ---\\n${LESSONS}\\n\\n--- LATEST DAILY REPORT ---\\n${DAILY}\\n\\n--- ANALYST MEMORY ---\\n${ANALYST}\\n\\n--- KB DRIFT WARNINGS ---\\n${DRIFT}\\n=== END KB AUTO-LOAD ==="}}
ENDJSON
