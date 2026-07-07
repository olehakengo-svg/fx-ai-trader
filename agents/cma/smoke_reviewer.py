"""STEP B — reviewer-only smoke test (do this before the full coordinator loop).

Stands up ONLY the reviewer agent (no multiagent) and asks it to adversarially
refute one real candidate, exercising the Wilson/WF/BH-FDR battery on first-party
data. Confirms the over-fit firewall works before we trust the autonomous loop.

Run worker.py first (it executes the reviewer's bash/read/grep locally), then:
    source agents/cma/ids.env
    export ANTHROPIC_API_KEY=sk-ant-...
    python agents/cma/smoke_reviewer.py
"""
import os

import anthropic

client = anthropic.Anthropic()

# A real N<30 candidate from the audit backlog. Swap as needed.
CANDIDATE = (
    "Refute this edge with the full quant battery (Wilson_lo, WF, BH-FDR q=0.10, "
    "friction<=TP10%, cell-level not aggregate, is_shadow separated), default to reject "
    "if uncertain: orb_trap | GBP_USD | SELL.\n"
    "\n"
    "CWD: you are ALREADY at the fx-ai-trader repo root (the worker's workdir). Do NOT run "
    "broad filesystem searches (`find ~`, `find /`) or interactive `sqlite3` with no SQL — "
    "both wedge the persistent bash shell via the 120s tool timeout. Pass SQL inline.\n"
    "\n"
    "MANDATORY DATA SOURCE — Render production is the ONLY valid primary source; the committed "
    "local ./demo_trades.db and any dated watchdog/CSV/LOCK artifacts are DEV-ONLY and STALE "
    "(CLAUDE.md: 'データ一次ソース: Render 本番。ローカル DB は開発用のみ'). You MUST base every "
    "final number on a FRESH Render pull, not on repo artifacts. Required flow:\n"
    "  1. `python3 tools/render_trades_snapshot.py --output render-fresh-snapshot.db --limit 100000`\n"
    "     (full pull; the web API ignores entry_type/instrument filters and truncates, so pull "
    "all rows and filter locally).\n"
    "  2. LIVE-only cell:  `python3 tools/cell_edge_audit.py --db render-fresh-snapshot.db "
    "--mode v3 --window all --strategy orb_trap`\n"
    "  3. shadow separated: same command + `--include-shadow`\n"
    "  4. Recompute Wilson_lo by hand from the v3 cell (entry_type x session x GBP_USD x SELL x "
    "mode) to verify the tool.\n"
    "Repo artifacts / LOCK docs may be used ONLY as a cross-check, NEVER as the numeric basis. "
    "If the fresh Render pull fails (dead bash, auth, API), STOP and report the data is "
    "unavailable rather than substituting stale artifacts — a verdict on stale local data is "
    "worthless here.\n"
    "\n"
    "Report, separated by is_shadow: N_live, N_shadow, WR, Wilson_lo, WF folds, BH-FDR result, "
    "Kelly, friction%-of-TP, and a satisfied/failed verdict citing the FRESH Render numbers."
)


def main() -> None:
    session = client.beta.sessions.create(
        agent=os.environ["FXAI_REVIEWER_ID"],
        environment_id=os.environ["FXAI_ENV_ID"],
        title="reviewer smoke test",
    )
    print(f"Watch: https://platform.claude.com/workspaces/default/sessions/{session.id}")

    stream = client.beta.sessions.events.stream(session_id=session.id)
    client.beta.sessions.events.send(session_id=session.id, events=[
        {"type": "user.message", "content": [{"type": "text", "text": CANDIDATE}]}
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
