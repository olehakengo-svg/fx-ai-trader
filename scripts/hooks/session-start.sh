#!/usr/bin/env bash
# SessionStart Hook — KB自動読み込み
# index(Tier+State) + 未解決事項 + lessons + daily report + analyst-memory を注入
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
KB="$ROOT/knowledge-base/wiki"

LATEST_SESSION=$(ls -t "$KB/sessions/"*.md 2>/dev/null | head -1 || true)

# 漏れ防止ログ（最優先で注入 — 新規タスクより先に処理すべき項目）
LEAKED=""
LEAKED_FILE="$KB/leaked-items.md"
if [[ -f "$LEAKED_FILE" ]]; then
    LEAKED_PENDING=$(grep -c '| pending' "$LEAKED_FILE" 2>/dev/null || echo "0")
    if [[ "$LEAKED_PENDING" -gt 0 ]]; then
        LEAKED=$(awk '/^## Active Items/,/^## Resolved Items/' "$LEAKED_FILE" 2>/dev/null | head -30 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
    fi
fi

# 各セクションを取得（ファイル未存在でも続行）
INDEX=$(head -60 "$KB/index.md" 2>/dev/null | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
UNRESOLVED_LABEL=$(basename "${LATEST_SESSION:-unknown}" .md 2>/dev/null || echo "unknown")
UNRESOLVED=$(awk '/^## 未解決事項/{buf=""; capture=1; next} capture && /^## /{capture=0} capture{buf=buf $0 "\n"} END{print buf}' "$LATEST_SESSION" 2>/dev/null | head -25 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
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

# ── KB Integrity Audit ──
KB_AUDIT=""
DEMO_TRADER="$ROOT/modules/demo_trader.py"
STRATEGIES_DIR="$ROOT/knowledge-base/wiki/strategies"
INDEX_FILE="$ROOT/knowledge-base/wiki/index.md"

if [[ -f "$DEMO_TRADER" && -d "$STRATEGIES_DIR" ]]; then
    # Count strategy wiki pages vs QUALIFIED_TYPES strategies
    WIKI_COUNT=$(ls "$STRATEGIES_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')
    QUALIFIED_COUNT=$(python3 -c "
import re
with open('$DEMO_TRADER', 'r') as f:
    src = f.read()
names = set()
for sn in ['_FORCE_DEMOTED', '_SCALP_SENTINEL', '_UNIVERSAL_SENTINEL', '_ELITE_LIVE']:
    m = re.search(rf'{sn}\s*=\s*\{{([^}}]+)\}}', src, re.DOTALL)
    if m:
        names |= set(re.findall(r'\"([a-z_]+)\"', m.group(1)))
m = re.search(r'_STRATEGY_LOT_BOOST\s*=\s*\{(.+?)\n\s*\}', src, re.DOTALL)
if m:
    names |= set(re.findall(r'\"([a-z_]+)\"\s*:', m.group(1)))
m = re.search(r'_PAIR_PROMOTED\s*=\s*\{(.+?)\n\s*\}', src, re.DOTALL)
if m:
    names |= set(re.findall(r'\(\"([a-z_]+)\"', m.group(1)))
missing = []
for n in sorted(names):
    import os
    wiki = os.path.join('$STRATEGIES_DIR', n.replace('_', '-') + '.md')
    if not os.path.exists(wiki):
        missing.append(n)
print(f'{len(names)}|{len(missing)}')
if missing:
    for m in missing[:5]:
        print(m)
" 2>/dev/null || echo "0|0")

    Q_TOTAL=$(echo "$QUALIFIED_COUNT" | head -1 | cut -d'|' -f1)
    Q_MISSING=$(echo "$QUALIFIED_COUNT" | head -1 | cut -d'|' -f2)
    MISSING_NAMES=$(echo "$QUALIFIED_COUNT" | tail -n +2 | head -5 | sed 's/$/\\n/' | tr -d '\n')

    if [[ "$Q_MISSING" -gt 0 ]]; then
        KB_AUDIT="KB INTEGRITY: ${Q_MISSING}/${Q_TOTAL} strategies missing wiki pages.\\n${MISSING_NAMES}"
    fi
fi

# Check if index.md is stale (>7 days old)
if [[ -f "$INDEX_FILE" ]]; then
    INDEX_MTIME=$(stat -f %m "$INDEX_FILE" 2>/dev/null || stat -c %Y "$INDEX_FILE" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    AGE_DAYS=$(( (NOW - INDEX_MTIME) / 86400 ))
    if [[ "$AGE_DAYS" -gt 7 ]]; then
        KB_AUDIT="${KB_AUDIT}index.md is ${AGE_DAYS} days stale — consider running: python3 tools/sync_kb_index.py --write\\n"
    fi
fi

# ── Quick Reference: ロードマップ + 摩擦 + BT TOP戦略 + 判断プロトコル ──
QUICK_REF=""

# ロードマップv2.1サマリー
ROADMAP_FILE="$ROOT/knowledge-base/wiki/syntheses/roadmap-v2.1.md"
if [[ -f "$ROADMAP_FILE" ]]; then
    ROADMAP=$(awk '/^## コンセプト/,/^## 二軸構造/' "$ROADMAP_FILE" 2>/dev/null | head -10 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
    QUICK_REF="${QUICK_REF}ROADMAP: ${ROADMAP}\\n"
fi

# 摩擦テーブル（コンパクト版）
FRICTION_FILE="$ROOT/knowledge-base/wiki/analyses/friction-analysis.md"
if [[ -f "$FRICTION_FILE" ]]; then
    FRICTION=$(awk '/^## Per-Pair Friction/,/^## Aggregate/' "$FRICTION_FILE" 2>/dev/null | head -12 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
    QUICK_REF="${QUICK_REF}FRICTION: ${FRICTION}\\n"
fi

# BT TOP 5 正EV戦略
BT_FILE="$ROOT/knowledge-base/raw/bt-results/comprehensive-bt-scan-2026-04-14.md"
if [[ -f "$BT_FILE" ]]; then
    BT_TOP=$(awk '/^## クオンツ判断/,/^## 注意/' "$BT_FILE" 2>/dev/null | head -15 | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' || true)
    QUICK_REF="${QUICK_REF}BT_TOP5: ${BT_TOP}\\n"
fi

# 判断プロトコルリマインダー
QUICK_REF="${QUICK_REF}DECISION_PROTOCOL: 判断前に必ず確認: (1)根拠=365日BT or Live N>=30か？ (2)どのKBページを読んだか？ (3)バグ修正かパラメータ変更か？ (4)感情的動機でないか？ → 1日データで対策実装は禁止（lesson-reactive-changes参照）\\n"

# 漏れ防止セクションを最上位に配置（pending>0の場合のみ）
LEAKED_SECTION=""
if [[ -n "$LEAKED" ]]; then
    LEAKED_SECTION="--- ⚠️ LEAKED ITEMS (前セッションの漏れ — 新規タスクより先に処理せよ) ---\\n${LEAKED}\\n\\n"
fi

cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"=== KB AUTO-LOAD ===\\n\\n${LEAKED_SECTION}--- QUICK REFERENCE (判断前に必ず確認) ---\\n${QUICK_REF}\\n\\n--- INDEX (Tier + System State) ---\\n${INDEX}\\n\\n--- SESSION CONTEXT (${UNRESOLVED_LABEL}) ---\\n${SESSION_SUMMARY}\\n\\n--- UNRESOLVED ITEMS ---\\n${UNRESOLVED}\\n\\n--- LESSONS (過去の間違い — 繰り返すな) ---\\n${LESSONS}\\n\\n--- LATEST DAILY REPORT ---\\n${DAILY}\\n\\n--- ANALYST MEMORY ---\\n${ANALYST}\\n\\n--- KB DRIFT WARNINGS ---\\n${DRIFT}\\n\\n--- KB INTEGRITY AUDIT ---\\n${KB_AUDIT}\\n=== END KB AUTO-LOAD ==="}}
ENDJSON
