#!/usr/bin/env bash
# PreCompact Hook — セッションログ自動生成
# コンテキスト圧縮前に、git状態からセッションログのテンプレートを作成。
# Claude が prompt hook で主観的な内容（判断・未解決事項）を追記する。
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel)"
KB="$ROOT/knowledge-base/wiki/sessions"
TODAY=$(date +%Y-%m-%d)
SESSION_FILE="$KB/${TODAY}-session.md"

# セッションログが既に存在する場合はスキップ（手動作成済み）
if [[ -f "$SESSION_FILE" ]]; then
    echo "Session log already exists: ${TODAY}-session.md"
    exit 0
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

# テンプレート生成
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
