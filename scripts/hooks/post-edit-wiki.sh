#!/usr/bin/env bash
# PostToolUse Hook — Wiki更新検知
set -euo pipefail

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[[ -z "$FILE" ]] && exit 0

if [[ "$FILE" == *knowledge-base/wiki/* ]]; then
    BASENAME=$(basename "$FILE")
    cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"Wiki updated: ${BASENAME}. Run /wiki-lint to check for broken links and contradictions."}}
ENDJSON
fi
