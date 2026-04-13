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

# 未解決事項（最新session logから — 最後の「## 未解決事項」セクションを取得）
UNRESOLVED=""
LATEST_SESSION=$(ls -t "$KB/sessions/"*.md 2>/dev/null | head -1 || true)
if [[ -n "$LATEST_SESSION" ]]; then
    UNRESOLVED=$(awk '/^## 未解決事項/{buf=""; capture=1; next} capture && /^## /{capture=0} capture{buf=buf $0 "\n"} END{print buf}' "$LATEST_SESSION" 2>/dev/null | head -20 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
fi

# Lessons — 実際の教訓を抽出（ヘッダーではなく教訓本文）
LESSONS=""
if [[ -f "$KB/lessons/index.md" ]]; then
    # 「教訓:」行を抽出 → 実際の学びのみ注入（ヘッダー/テンプレートを除外）
    LESSONS=$(grep -E '^- 教訓:' "$KB/lessons/index.md" 2>/dev/null | grep -v '一文で一般化' | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
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

# --- v8.9: 市場コンテキスト注入 ---
# 現在のUTC時刻から市場セッションを判定
UTC_HOUR=$(date -u +%H | sed 's/^0//')
UTC_MIN=$(date -u +%M)
DOW=$(date -u +%u)  # 1=Mon, 7=Sun

MARKET_CTX=""
if (( DOW == 6 || DOW == 7 )); then
    MARKET_CTX="🔴 WEEKEND (市場閉鎖)"
elif (( UTC_HOUR >= 0 && UTC_HOUR < 7 )); then
    MARKET_CTX="🇯🇵 Tokyo Session (UTC ${UTC_HOUR}:${UTC_MIN}) — JPY減価バイアス時間帯"
elif (( UTC_HOUR >= 7 && UTC_HOUR < 12 )); then
    MARKET_CTX="🇬🇧 London Session (UTC ${UTC_HOUR}:${UTC_MIN}) — EUR/GBP減価バイアス時間帯"
elif (( UTC_HOUR >= 12 && UTC_HOUR < 16 )); then
    MARKET_CTX="🇬🇧🇺🇸 London-NY Overlap (UTC ${UTC_HOUR}:${UTC_MIN}) — 最高流動性/London Fix(15:45-17:00)"
elif (( UTC_HOUR >= 16 && UTC_HOUR < 21 )); then
    MARKET_CTX="🇺🇸 NY Session (UTC ${UTC_HOUR}:${UTC_MIN})"
else
    MARKET_CTX="🌙 Late NY/Pre-Tokyo (UTC ${UTC_HOUR}:${UTC_MIN}) — 五十日チェック窓(23:00-01:15)"
fi

# 4原則リマインダ（常時）
PRINCIPLES="⚠️ 4原則: 攻める/デスゾーン=動的のみ/静的時間ブロック禁止/攻撃は最大の防御"
QUANT_RULE="🔬 クオンツルール: XAU除外/ペア×戦略粒度/Post-cutoff起点/分析→判断→実装"

cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"=== KB SYNC ===\\n${INDEX}\\n--- UNRESOLVED ---\\n${UNRESOLVED}\\n--- LESSONS ---\\n${LESSONS}\\n--- SESSION ---\\n${SESSION_REMIND}\\n--- MARKET ---\\n${MARKET_CTX}\\n${PRINCIPLES}\\n${QUANT_RULE}\\n--- LAST COMMIT: ${LAST_COMMIT} | KB LAST: ${KB_LAST_COMMIT} ---\\n=== END KB SYNC ==="}}
ENDJSON
