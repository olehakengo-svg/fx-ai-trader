#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage:
  ./tools/ai_codex_status.sh [--result] JOB_ID_OR_RUN_DIR

Looks up a Codex companion job across the Claude plugin data stores used by the
app/CLI bridge. This avoids false "No job found" results when the job was
launched with a different CLAUDE_PLUGIN_DATA value.
EOF
}

resolve_companion_script() {
  if [[ -n "${CODEX_COMPANION_SCRIPT:-}" && -f "$CODEX_COMPANION_SCRIPT" ]]; then
    printf "%s\n" "$CODEX_COMPANION_SCRIPT"
    return 0
  fi
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -f "$CLAUDE_PLUGIN_ROOT/scripts/codex-companion.mjs" ]]; then
    printf "%s\n" "$CLAUDE_PLUGIN_ROOT/scripts/codex-companion.mjs"
    return 0
  fi
  local newest
  newest="$(find "$HOME/.claude/plugins/cache/openai-codex/codex" -path '*/scripts/codex-companion.mjs' -type f 2>/dev/null | sort -V | tail -1)"
  if [[ -n "$newest" && -f "$newest" ]]; then
    printf "%s\n" "$newest"
    return 0
  fi
  return 1
}

track_field() {
  local field="$1"
  local file="$2"
  awk -F= -v key="$field" '$1 == key { print substr($0, length(key) + 2); exit }' "$file"
}

MODE="status"
case "${1:-}" in
  --help|-h)
    usage
    exit 0
    ;;
  --result)
    MODE="result"
    shift
    ;;
esac

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  usage >&2
  exit 2
fi

TRACK_FILE=""
if [[ -d "$TARGET" && -f "$TARGET/codex-job.txt" ]]; then
  TRACK_FILE="$TARGET/codex-job.txt"
elif [[ -f "$TARGET" ]]; then
  TRACK_FILE="$TARGET"
elif [[ -f ".ai/runs/$TARGET/codex-job.txt" ]]; then
  TRACK_FILE=".ai/runs/$TARGET/codex-job.txt"
fi

JOB_ID="$TARGET"
DATA_HINT=""
if [[ -n "$TRACK_FILE" ]]; then
  JOB_ID="$(track_field job_id "$TRACK_FILE")"
  DATA_HINT="$(track_field claude_plugin_data "$TRACK_FILE" || true)"
fi

if [[ -z "$JOB_ID" || ! "$JOB_ID" =~ ^task- ]]; then
  echo "Could not resolve Codex companion job id from: $TARGET" >&2
  exit 2
fi

COMPANION_SCRIPT="$(resolve_companion_script || true)"
if [[ -z "$COMPANION_SCRIPT" ]]; then
  echo "Codex companion script not found. In Claude Code, run /codex:setup or set CODEX_COMPANION_SCRIPT." >&2
  exit 1
fi

declare -a DATA_CANDIDATES=()
add_candidate() {
  local value="$1"
  [[ -n "$value" ]] || return 0
  local existing
  if ((${#DATA_CANDIDATES[@]} > 0)); then
    for existing in "${DATA_CANDIDATES[@]}"; do
      [[ "$existing" == "$value" ]] && return 0
    done
  fi
  DATA_CANDIDATES+=("$value")
}

add_candidate "$DATA_HINT"
add_candidate "${CLAUDE_PLUGIN_DATA:-}"
add_candidate "$HOME/.claude/plugins/data/codex-inline"
add_candidate "$HOME/.claude/plugins/data/codex-openai-codex"
while IFS= read -r dir; do
  add_candidate "$dir"
done < <(find "$HOME/.claude/plugins/data" -maxdepth 1 -type d -name 'codex-*' 2>/dev/null | sort)

for data_dir in "${DATA_CANDIDATES[@]}"; do
  output="$(CLAUDE_PLUGIN_DATA="$data_dir" node "$COMPANION_SCRIPT" "$MODE" "$JOB_ID" 2>&1 || true)"
  if ! grep -q 'No job found' <<<"$output"; then
    echo "CLAUDE_PLUGIN_DATA=$data_dir"
    printf "%s\n" "$output"
    exit 0
  fi
done

output="$(node "$COMPANION_SCRIPT" "$MODE" "$JOB_ID" 2>&1 || true)"
if ! grep -q 'No job found' <<<"$output"; then
  echo "CLAUDE_PLUGIN_DATA=<unset>"
  printf "%s\n" "$output"
  exit 0
fi

echo "No job found for $JOB_ID in known Codex companion stores." >&2
echo "Checked:" >&2
for data_dir in "${DATA_CANDIDATES[@]}"; do
  echo "  $data_dir" >&2
done
exit 1
