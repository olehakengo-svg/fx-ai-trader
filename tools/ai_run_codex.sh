#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage:
  ./tools/ai_run_codex.sh --list
  ./tools/ai_run_codex.sh --pick
  ./tools/ai_run_codex.sh [TASK_FILE|TASK_NUMBER]

Default with no argument runs the newest queued task for backward compatibility.
Use --list first when multiple queued tasks exist.
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
  --pick|-p)
    list_tasks
    echo
    read -r -p "Run which task number? " TASK_NUMBER
    TASK="$(select_task_by_number "$TASK_NUMBER")"
    ;;
  "")
    TASK="$(queue_tasks | tail -1)"
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
  WAIT_SECONDS="${AI_WAIT_SECONDS:-120}"
  echo "No queued task found. Waiting up to ${WAIT_SECONDS}s for /fx-next to create one..." >&2
  deadline=$((SECONDS + WAIT_SECONDS))
  while (( SECONDS < deadline )); do
    TASK="$(queue_tasks | tail -1)"
    if [[ -n "$TASK" && -f "$TASK" ]]; then
      break
    fi
    sleep 2
  done
fi

if [[ -z "$TASK" || ! -f "$TASK" ]]; then
  echo "Still no queued task in .ai/tasks/queue/." >&2
  echo "Options:" >&2
  echo "  1. In Claude Code, wait for /fx-next to finish." >&2
  echo "  2. Or create a bootstrap task now: ./tools/ai_next_bootstrap.sh" >&2
  echo "  3. Then rerun: ./tools/ai_run_codex.sh" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
SLUG="$(basename "$TASK" .md)"
RUN_DIR=".ai/runs/${STAMP}-${SLUG}"
mkdir -p "$RUN_DIR"

PROMPT_FILE="$RUN_DIR/prompt.md"
FINAL_FILE="$RUN_DIR/final.md"
EVENTS_FILE="$RUN_DIR/events.jsonl"

cat > "$PROMPT_FILE" <<EOF
You are Codex working on fx-ai-trader.

Read and execute the task file: $TASK

Hard rules:
- Respect existing uncommitted changes. Do not revert user changes.
- Keep changes scoped to the task.
- Do not edit secrets or production credentials.
- Prefer tests and audit scripts listed in the task.
- Write a concise final answer with status, files changed, verification summary, risks, and next recommended task.
- If blocked, explain the blocker and the exact evidence needed next.

Before finalizing, ensure the run report can be reviewed by Claude Code from:
$FINAL_FILE
EOF

echo "Task: $TASK"
echo "Run:  $RUN_DIR"

CODEX_MODEL_DEFAULT="${CODEX_MODEL:-gpt-5.4}"
CODEX_ARGS_DEFAULT=(exec -C "$ROOT" -m "$CODEX_MODEL_DEFAULT" --full-auto --json -o "$FINAL_FILE")
if [[ -n "${CODEX_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  CODEX_ARGS_SPLIT=($CODEX_ARGS)
  echo "Codex args: ${CODEX_ARGS}" >&2
  codex "${CODEX_ARGS_SPLIT[@]}" "$(cat "$PROMPT_FILE")" | tee "$EVENTS_FILE"
else
  echo "Codex model: $CODEX_MODEL_DEFAULT" >&2
  codex "${CODEX_ARGS_DEFAULT[@]}" "$(cat "$PROMPT_FILE")" | tee "$EVENTS_FILE"
fi

echo
echo "Codex final report: $FINAL_FILE"
echo "Review with Claude Code: /fx-review-result"
