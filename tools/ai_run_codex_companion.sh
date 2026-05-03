#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage:
  ./tools/ai_run_codex_companion.sh --list
  ./tools/ai_run_codex_companion.sh [TASK_FILE|TASK_NUMBER]

Launches the selected task through the Claude Code Codex companion so the work
appears as a persistent Codex task/thread instead of a raw Bash `codex exec`.
EOF
}

queue_tasks() {
  find .ai/tasks/queue -maxdepth 1 -type f -name '*.md' ! -name '.gitkeep' -print | sort
}

load_tasks() {
  TASKS=()
  local task
  while IFS= read -r task; do
    TASKS+=("$task")
  done < <(queue_tasks)
}

task_field() {
  local field="$1"
  local file="$2"
  awk -F': *' -v key="$field" '
    $1 == key {
      sub(/^[[:space:]]+/, "", $2)
      sub(/[[:space:]]+$/, "", $2)
      print $2
      exit
    }
  ' "$file"
}

list_tasks() {
  local idx=0
  local task
  local priority rule gate title status
  load_tasks
  if [[ "${#TASKS[@]}" -eq 0 ]]; then
    echo "No queued Codex tasks in .ai/tasks/queue/."
    return 1
  fi

  echo "Queued Codex tasks:"
  for task in "${TASKS[@]}"; do
    idx=$((idx + 1))
    priority="$(task_field priority "$task")"
    rule="$(task_field rule "$task")"
    gate="$(task_field roadmap_gate "$task")"
    status="$(task_field status "$task")"
    title="$(task_field title "$task")"
    printf "%2d. [%s] %s | %s | %s | %s\n" \
      "$idx" "${priority:-P?}" "${rule:-R?}" "${gate:-Gate ?}" "${status:-unknown}" "$(basename "$task")"
    if [[ -n "$title" ]]; then
      printf "    %s\n" "$title"
    fi
  done
}

select_task_by_number() {
  local choice="$1"
  load_tasks
  if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    return 1
  fi
  if (( choice < 1 || choice > ${#TASKS[@]} )); then
    echo "Task number out of range: $choice" >&2
    return 1
  fi
  printf "%s\n" "${TASKS[$((choice - 1))]}"
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

TASK=""
case "${1:-}" in
  --help|-h)
    usage
    exit 0
    ;;
  --list|-l)
    list_tasks
    exit $?
    ;;
  "")
    echo "No task specified. Use --list, then pass a task number or file." >&2
    exit 2
    ;;
  *)
    if [[ "${1:-}" =~ ^[0-9]+$ ]]; then
      TASK="$(select_task_by_number "$1")"
    else
      TASK="$1"
    fi
    ;;
esac

if [[ -z "$TASK" || ! -f "$TASK" ]]; then
  echo "Task not found: ${TASK:-<empty>}" >&2
  exit 1
fi

COMPANION_SCRIPT="$(resolve_companion_script || true)"
if [[ -z "$COMPANION_SCRIPT" ]]; then
  echo "Codex companion script not found. In Claude Code, run /codex:setup or set CODEX_COMPANION_SCRIPT." >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
SLUG="$(basename "$TASK" .md)"
RUN_DIR=".ai/runs/${STAMP}-${SLUG}"
mkdir -p "$RUN_DIR"

PROMPT_FILE="$RUN_DIR/prompt.md"
FINAL_FILE="$RUN_DIR/final.md"
TASK_TITLE="$(task_field title "$TASK")"
THREAD_TITLE="Codex Companion Task: ${TASK_TITLE:-$SLUG}"

cat > "$PROMPT_FILE" <<EOF
$THREAD_TITLE

You are Codex working on fx-ai-trader.

Read and execute the task file: $TASK

Hard rules:
- Respect existing uncommitted changes. Do not revert user changes.
- Keep changes scoped to the task.
- Do not edit secrets or production credentials.
- Prefer tests and audit scripts listed in the task.
- Write a concise final answer in Japanese with status, files changed, verification summary, risks, and next recommended task.
- If blocked, explain the blocker and the exact evidence needed next.

Before finalizing, write the run report for Claude Code review to:
$FINAL_FILE
EOF

echo "Task: $TASK"
echo "Run:  $RUN_DIR"
echo "Thread title: $THREAD_TITLE"
echo "Codex companion: $COMPANION_SCRIPT"

COMPANION_ARGS=(task --background --write --cwd "$ROOT" --prompt-file "$PROMPT_FILE")
if [[ -n "${CODEX_COMPANION_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARGS=($CODEX_COMPANION_ARGS)
  COMPANION_ARGS=(task "${EXTRA_ARGS[@]}" --background --write --cwd "$ROOT" --prompt-file "$PROMPT_FILE")
fi

COMPANION_OUTPUT="$(node "$COMPANION_SCRIPT" "${COMPANION_ARGS[@]}")"
printf "%s\n" "$COMPANION_OUTPUT"

JOB_ID="$(printf "%s\n" "$COMPANION_OUTPUT" | grep -Eo 'task-[[:alnum:]]+-[[:alnum:]]+' | head -1 || true)"
if [[ -n "$JOB_ID" ]]; then
  TRACK_FILE="$RUN_DIR/codex-job.txt"
  cat > "$TRACK_FILE" <<EOF
job_id=$JOB_ID
task=$TASK
run_dir=$RUN_DIR
final_file=$FINAL_FILE
thread_title=$THREAD_TITLE
status_command=node "$COMPANION_SCRIPT" status $JOB_ID
result_command=node "$COMPANION_SCRIPT" result $JOB_ID
EOF

  echo
  echo "Codex companion tracking:"
  echo "  Job ID: $JOB_ID"
  echo "  Status: node \"$COMPANION_SCRIPT\" status $JOB_ID"
  echo "  Result: node \"$COMPANION_SCRIPT\" result $JOB_ID"
  echo "  Tracking file: $TRACK_FILE"
  echo
  node "$COMPANION_SCRIPT" status "$JOB_ID" || true
fi

echo
echo "Codex companion task launched. Track it by Job ID; the app sidebar can show truncated or unrelated task titles."
echo "Expected run report: $FINAL_FILE"
echo "Review with Claude Code after completion: /fx-review-result"
