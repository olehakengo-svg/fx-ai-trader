#!/usr/bin/env python3
"""Detect stalled Codex tasks in .ai/tasks/running/.

A task is "stalled" if it has been in the running/ dir longer than a
threshold. Normal Codex BT tasks finish in 6-12 minutes; anything over
~30-60 minutes is suspicious (see memory feedback_codex_stash_leak:
task-mpxr8a35 stalled 22h before expiring; 20260608-edge-cell-filter
stalled 39h unnoticed in 2026-06-08).

Usage:
    python3 tools/check_stalled_codex_tasks.py [--threshold-min N] [--json]

Exit codes:
    0  no stalled tasks
    1  one or more stalled tasks found

--json emits a SessionStart hook additionalContext payload on stdout so it
can be wired into a Claude Code SessionStart hook for automatic detection.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# fx-ai-trader repo root (script lives in tools/)
REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNING_DIR = REPO_ROOT / ".ai" / "tasks" / "running"
DEFAULT_THRESHOLD_MIN = 30  # normal tasks finish in 6-12 min


def find_stalled(threshold_min: int) -> list[dict]:
    """Return list of {task, age_min, mtime_iso} for tasks older than threshold."""
    if not RUNNING_DIR.is_dir():
        return []
    now = time.time()
    stalled = []
    for f in sorted(RUNNING_DIR.glob("*.md")):
        age_sec = now - f.stat().st_mtime
        age_min = age_sec / 60.0
        if age_min > threshold_min:
            stalled.append(
                {
                    "task": f.stem,
                    "age_min": round(age_min, 1),
                    "age_hours": round(age_min / 60.0, 1),
                    "mtime_iso": time.strftime(
                        "%Y-%m-%dT%H:%M:%S", time.localtime(f.stat().st_mtime)
                    ),
                }
            )
    return stalled


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--threshold-min",
        type=int,
        default=int(os.environ.get("CODEX_STALL_THRESHOLD_MIN", DEFAULT_THRESHOLD_MIN)),
    )
    ap.add_argument("--json", action="store_true", help="emit SessionStart hook JSON")
    args = ap.parse_args()

    stalled = find_stalled(args.threshold_min)

    if args.json:
        # SessionStart hook contract: emit additionalContext only when stalled.
        if stalled:
            lines = [
                f"🔴 STALLED Codex task(s) detected in {RUNNING_DIR}:",
            ]
            for s in stalled:
                lines.append(
                    f"  - {s['task']} — running {s['age_hours']}h "
                    f"(since {s['mtime_iso']}, threshold {args.threshold_min}min)"
                )
            lines.append(
                "Normal Codex BT tasks finish in 6-12 min. Per policy "
                "feedback_codex_as_review_layer_2026_06_05, consider taking over "
                "with Claude or restarting. Check Render logs for "
                "srv-d7rjnfn7f7vs73d1e6ig (fx-codex-runner) to confirm stall vs crash."
            )
            ctx = "\n".join(lines)
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": ctx,
                        }
                    }
                )
            )
        # If no stalled tasks, emit nothing (clean session start).
        return 1 if stalled else 0

    # Human-readable mode
    if not stalled:
        print(f"✅ No stalled Codex tasks (threshold {args.threshold_min}min)")
        return 0
    print(f"🔴 {len(stalled)} stalled Codex task(s) (threshold {args.threshold_min}min):")
    for s in stalled:
        print(f"  - {s['task']}: {s['age_hours']}h (since {s['mtime_iso']})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
