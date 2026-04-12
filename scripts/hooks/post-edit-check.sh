#!/usr/bin/env bash
# PostToolUse Hook — Python構文チェック + 整合性チェッカー
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ -z "$FILE" ]] && exit 0

# Python syntax check
if [[ "$FILE" == *.py ]]; then
    python3 -m py_compile "$FILE" 2>&1 && echo "✅ syntax OK: $(basename "$FILE")"
fi

# Strategy / demo_trader / app.py 変更時に整合性チェック
if [[ "$FILE" == *strategies/* || "$FILE" == *demo_trader.py || "$FILE" == *app.py ]]; then
    python3 "$ROOT/scripts/check.py" --quiet
fi
