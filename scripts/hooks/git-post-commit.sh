#!/usr/bin/env bash
# Git post-commit hook — セッションログにコミットを自動追記
# .git/hooks/post-commit から呼び出される
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel)"
KB="$ROOT/knowledge-base/wiki/sessions"
TODAY=$(date +%Y-%m-%d)
SESSION_FILE="$KB/${TODAY}-session.md"

# 最新コミット情報
HASH=$(git log -1 --format='%h')
MSG=$(git log -1 --format='%s')
FILES_CHANGED=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null | wc -l | tr -d ' ')

# セッションログが無ければテンプレート作成
if [[ ! -f "$SESSION_FILE" ]]; then
    mkdir -p "$KB"
    # 前回セッションの未解決事項を引き継ぎ
    PREV_SESSION=$(ls -t "$KB/"*.md 2>/dev/null | head -1 || true)
    PREV_UNRESOLVED=""
    if [[ -n "$PREV_SESSION" ]]; then
        PREV_UNRESOLVED=$(sed -n '/^## 未解決事項/,/^## /p' "$PREV_SESSION" 2>/dev/null | grep '^\- \[' || true)
    fi
    cat > "$SESSION_FILE" << TEMPLATE
# Session Log: ${TODAY}

## セッションで行ったこと（時系列）

### Phase 1: （Claudeが記入）

## コミット一覧（自動記録）

| # | Hash | Message | Files |
|---|---|---|---|
| 1 | ${HASH} | ${MSG} | ${FILES_CHANGED} |

## 未解決事項
${PREV_UNRESOLVED:-"- [ ] （前回セッションから引き継ぎなし）"}
TEMPLATE
    exit 0
fi

# 既存セッションログにコミット追記
# コミット一覧テーブルの最後の行番号を見つけて追記
if grep -q "## コミット一覧" "$SESSION_FILE"; then
    # テーブル形式の場合: 最後の | 行の後に追記
    if grep -q '^| [0-9]' "$SESSION_FILE"; then
        LAST_NUM=$(grep -c '^| [0-9]' "$SESSION_FILE")
        NEXT_NUM=$((LAST_NUM + 1))
        # 重複チェック（同じハッシュが既にあればスキップ）
        if grep -q "$HASH" "$SESSION_FILE"; then
            exit 0
        fi
        # 最後のテーブル行の後に挿入
        LAST_LINE=$(grep -n '^| [0-9]' "$SESSION_FILE" | tail -1 | cut -d: -f1)
        sed -i '' "${LAST_LINE}a\\
| ${NEXT_NUM} | ${HASH} | ${MSG} | ${FILES_CHANGED} |" "$SESSION_FILE"
    else
        # 番号リスト形式（既存Phase 1-13形式）の場合
        LAST_NUM=$(grep -c '^[0-9]\+\.' "$SESSION_FILE" | head -1)
        if [[ "$LAST_NUM" -eq 0 ]]; then
            LAST_NUM=0
        fi
        NEXT_NUM=$((LAST_NUM + 1))
        if grep -q "$HASH" "$SESSION_FILE"; then
            exit 0
        fi
        # コミット一覧セクションの末尾に追記
        SECTION_END=$(awk '/^## コミット一覧/{found=1; next} found && /^## /{print NR; exit}' "$SESSION_FILE")
        if [[ -n "$SECTION_END" ]]; then
            INSERT_LINE=$((SECTION_END - 1))
        else
            INSERT_LINE=$(wc -l < "$SESSION_FILE")
        fi
        sed -i '' "${INSERT_LINE}a\\
${NEXT_NUM}. ${MSG} (${HASH}, ${FILES_CHANGED} files)" "$SESSION_FILE"
    fi
fi
