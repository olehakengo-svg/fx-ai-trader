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

# 重複チェック（同じハッシュが既にあればスキップ）
if [[ -f "$SESSION_FILE" ]] && grep -q "$HASH" "$SESSION_FILE" 2>/dev/null; then
    exit 0
fi

# セッションログが無ければテンプレート作成
if [[ ! -f "$SESSION_FILE" ]]; then
    mkdir -p "$KB"
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
1. ${MSG} (${HASH}, ${FILES_CHANGED} files)

## 未解決事項
${PREV_UNRESOLVED:-"- [ ] （前回セッションから引き継ぎなし）"}
TEMPLATE
    exit 0
fi

# 既存セッションログにコミット追記（Python で確実に処理）
python3 -c "
import re, sys

path = '$SESSION_FILE'
hash_val = '$HASH'
msg = '''$MSG'''
files = '$FILES_CHANGED'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# コミット一覧セクションを探す
commit_section_start = None
commit_section_end = None
for i, line in enumerate(lines):
    if re.match(r'^## コミット一覧', line):
        commit_section_start = i
    elif commit_section_start is not None and re.match(r'^## ', line) and i > commit_section_start:
        commit_section_end = i
        break

if commit_section_start is None:
    # コミット一覧セクションがなければ未解決事項の前に追加
    for i, line in enumerate(lines):
        if re.match(r'^## 未解決事項', line):
            insert_pos = i
            break
    else:
        insert_pos = len(lines)
    lines.insert(insert_pos, f'\n## コミット一覧（自動記録）\n1. {msg} ({hash_val}, {files} files)\n\n')
else:
    # 既存セクション内の最後の番号付きエントリを見つける
    last_num = 0
    last_entry_line = commit_section_start
    end = commit_section_end if commit_section_end else len(lines)
    for i in range(commit_section_start + 1, end):
        m = re.match(r'^(\d+)\.', lines[i])
        if m:
            last_num = int(m.group(1))
            last_entry_line = i
    next_num = last_num + 1
    new_entry = f'{next_num}. {msg} ({hash_val}, {files} files)\n'
    lines.insert(last_entry_line + 1, new_entry)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
" 2>/dev/null || true
