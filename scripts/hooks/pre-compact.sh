#!/usr/bin/env bash
# PreCompact Hook — セッションログ自動生成
# コンテキスト圧縮前に、git状態からセッションログのテンプレートを作成。
# Claude が prompt hook で主観的な内容（判断・未解決事項）を追記する。
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel)"
KB="$ROOT/knowledge-base/wiki/sessions"
TODAY=$(date +%Y-%m-%d)
SESSION_FILE="$KB/${TODAY}-session.md"

# セッションログが既に存在する場合はテンプレート生成スキップ（候補検出は実行）
SESSION_EXISTED=false
if [[ -f "$SESSION_FILE" ]]; then
    echo "Session log already exists: ${TODAY}-session.md"
    SESSION_EXISTED=true
fi

# 今日のコミット一覧を取得
COMMITS=$(git log --oneline --since="$TODAY" --no-merges 2>/dev/null || true)
if [[ -z "$COMMITS" ]]; then
    COMMITS="（本日のコミットなし）"
fi

# 変更ファイルの統計
CHANGED_FILES=$(git diff --stat HEAD~5 HEAD 2>/dev/null | tail -1 || echo "（差分取得不可）")

# 前回セッションの未解決事項を引き継ぎ
PREV_SESSION=$(ls -t "$KB/"*.md 2>/dev/null | head -1 || true)
PREV_UNRESOLVED=""
if [[ -n "$PREV_SESSION" ]]; then
    PREV_UNRESOLVED=$(grep -A 30 '## 未解決事項' "$PREV_SESSION" 2>/dev/null | grep '^\- \[' || true)
fi

# テンプレート生成（既存の場合はスキップ）
if [[ "$SESSION_EXISTED" = false ]]; then
mkdir -p "$KB"
cat > "$SESSION_FILE" << TEMPLATE
# Session Log: ${TODAY}

## セッションで行ったこと（時系列）

### Phase 1: （Claudeが記入）
- （コンテキスト圧縮前に自動生成 — 詳細はClaude が追記）

## コミット一覧（本セッション）
${COMMITS}

## 変更統計
${CHANGED_FILES}

## 未解決事項
${PREV_UNRESOLVED:-"- [ ] （前回セッションから引き継ぎなし）"}

TEMPLATE

echo "Created session log: ${TODAY}-session.md"
fi  # end SESSION_EXISTED check

# --- DECISION/LESSON 候補検出 ---
# セッションログが存在する場合（既存 or 今作成）、キーワードから候補を検出
DETECT_FILE="$SESSION_FILE"
if [[ -f "$DETECT_FILE" ]]; then
    echo ""
    echo "--- KB CANDIDATE DETECTION ---"

    # Decision候補: 戦略変更・リスク変更系キーワード
    DECISION_HITS=$(grep -inE 'PROMOT|DEMOT|停止|復活|Reset|Equity|Kelly|DD防御|ロット|パラメータ変更|\[DECISION:' "$DETECT_FILE" 2>/dev/null || true)
    if [[ -n "$DECISION_HITS" ]]; then
        echo "⚡ DECISION候補を検出（wiki/decisions/ への記録を検討）:"
        echo "$DECISION_HITS" | head -5
    fi

    # Lesson候補: バグ修正・想定外系キーワード
    LESSON_HITS=$(grep -inE 'fix|bug|バグ|間違|修正|想定外|乖離|覆|REJECT|壊|不整合|ドリフト' "$DETECT_FILE" 2>/dev/null || true)
    if [[ -n "$LESSON_HITS" ]]; then
        echo "📝 LESSON候補を検出（wiki/lessons/ への記録を検討）:"
        echo "$LESSON_HITS" | head -5
    fi

    echo "--- END DETECTION ---"
fi
