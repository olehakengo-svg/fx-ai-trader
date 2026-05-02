#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TASK="${1:-}"
if [[ -z "$TASK" ]]; then
  TASK="$(find .ai/tasks/queue -maxdepth 1 -type f -name '*.md' ! -name '.gitkeep' -print | sort | tail -1)"
fi

if [[ -z "$TASK" || ! -f "$TASK" ]]; then
  WAIT_SECONDS="${AI_WAIT_SECONDS:-120}"
  echo "No queued task found. Waiting up to ${WAIT_SECONDS}s for /fx-next to create one..." >&2
  deadline=$((SECONDS + WAIT_SECONDS))
  while (( SECONDS < deadline )); do
    TASK="$(find .ai/tasks/queue -maxdepth 1 -type f -name '*.md' ! -name '.gitkeep' -print | sort | tail -1)"
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
