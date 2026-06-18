"""STEP C — dev-agent smoke test.

Exercises the dev agent's pipeline + guardrails on a CONTAINED, ADDITIVE task that
cannot collide with any other agent working the repo (new file only):
build a reusable cell sanity-checker that encodes what the reviewer did by hand
(is_shadow separation + dedup_violation exclusion + Wilson_lo + day-level dedup).

Run worker.py first (separate terminal), then:
    source agents/cma/ids.env
    python3 agents/cma/smoke_dev.py

NOTE: GitHub MCP vault is not set up yet, so this smoke STOPS before push/PR — the
dev agent prepares a branch + commit locally and prints the PR body. The push/PR
path is validated separately once the vault exists.
"""
import os

import anthropic

client = anthropic.Anthropic()

TASK = (
    "You are the dev agent for fx-ai-trader. Implement a small, self-contained tool.\n"
    "\n"
    "CWD: you are ALREADY at the repo root (worker workdir). Do NOT run `find ~`/`find /` "
    "or interactive `sqlite3` with no SQL — they wedge the bash shell via the 120s timeout.\n"
    "\n"
    "TASK (ADDITIVE — new file only, must not edit existing tools): create "
    "`tools/wilson_cell_check.py`, a reusable CLI that audits one edge cell from a Render "
    "snapshot DB and reports honest, dedup-corrected stats. Requirements:\n"
    "  - Args: --db <sqlite>, --strategy, --pair, --direction (and optional --session/--mode).\n"
    "  - Separate is_shadow=0 (LIVE) vs is_shadow=1 (SHADOW) and report each separately.\n"
    "  - Exclude rows flagged dedup_violation=1, AND additionally collapse same-day duplicate "
    "    signals (the shadow sample pseudo-replicates: identical entry/SL/TP fired seconds "
    "    apart cluster into a few calendar days). Report both raw-N and day-deduped-N.\n"
    "  - Compute WR and Wilson_lo (95%) for each (LIVE / SHADOW, raw + day-deduped).\n"
    "  - Pure stdlib + sqlite3 only (no new deps). Add a docstring with usage.\n"
    "  - Add a minimal test under tests/ if a natural place exists; run it.\n"
    "  - Verify it runs: build a tiny throwaway sqlite fixture (or use an existing snapshot if "
    "    present) and show the output for orb_trap|GBP_USD|SELL.\n"
    "\n"
    "GUARDRAILS (hard):\n"
    "  - Work on a NEW branch (e.g. feat/wilson-cell-check). Do NOT commit to main, do NOT "
    "    merge, do NOT modify tools/render_trades_snapshot.py or tools/cell_edge_audit.py "
    "    (another agent is editing those — touching them risks a concurrent-edit conflict).\n"
    "  - Do NOT touch LIVE env, _PAIR_LOT_BOOST, sizing, demo_trader, or any production "
    "    trading path. This is a read-only analysis tool.\n"
    "  - GitHub MCP vault is NOT configured — do NOT use the github MCP tool. Commit locally "
    "    on the branch, then STOP and OUTPUT the exact PR title + body you would submit, plus "
    "    `git diff --stat` and the new file path. Do not push.\n"
    "\n"
    "Report: branch name, new file path, test result, verification output, PR title + body."
)


def main() -> None:
    session = client.beta.sessions.create(
        agent=os.environ["FXAI_DEV_ID"],
        environment_id=os.environ["FXAI_ENV_ID"],
        title="dev smoke test",
    )
    print(f"Watch: https://platform.claude.com/workspaces/default/sessions/{session.id}")

    stream = client.beta.sessions.events.stream(session_id=session.id)
    client.beta.sessions.events.send(session_id=session.id, events=[
        {"type": "user.message", "content": [{"type": "text", "text": TASK}]}
    ])
    for ev in stream:
        if ev.type == "agent.message":
            for b in ev.content:
                if b.type == "text":
                    print(b.text, end="", flush=True)
        elif ev.type == "session.status_idle" and ev.stop_reason.type != "requires_action":
            break
        elif ev.type == "session.status_terminated":
            break


if __name__ == "__main__":
    main()
