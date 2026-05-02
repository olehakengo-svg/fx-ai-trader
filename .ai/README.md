# AI Coordination Lane

This directory is the shared handoff lane between Claude Code and Codex.

## Flow

1. Claude Code creates one focused task in `.ai/tasks/queue/`.
2. `tools/ai_run_codex.sh` sends the newest queued task to Codex CLI.
3. Codex writes a run report under `.ai/runs/`.
4. Claude Code reviews the newest report, updates the roadmap/KB, and decides the next task.

## Directory Contract

| Path | Owner | Purpose |
|---|---|---|
| `.ai/tasks/queue/` | Claude Code | Ready tasks for Codex |
| `.ai/tasks/done/` | Claude Code | Completed task specs after review |
| `.ai/tasks/failed/` | Claude Code | Failed or blocked task specs after review |
| `.ai/runs/` | Codex | Execution logs and final reports |
| `.ai/decisions/` | Claude Code | Roadmap decisions, gate changes, and review outcomes |

## Task Rule

Keep each task small enough for one Codex run:

- one bugfix,
- one audit,
- one backtest implementation,
- one test expansion, or
- one roadmap evidence-gathering task.

Do not mix unrelated strategy research, production safety fixes, and UI/dashboard work in the same task.
