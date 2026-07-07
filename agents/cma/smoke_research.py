"""STEP D — research-agent smoke test (read-only; safe on a dirty tree).

Verifies the research agent: (1) checks what's already tried/killed before proposing,
(2) gathers current external context via web_search/web_fetch, (3) emits structured,
pre-reg-able hypotheses (pair/dir/TF/conditions/m/thresholds). No Memory Store is
attached yet, so it outputs the ledger entries inline.

Run worker.py first (separate terminal), then:
    source agents/cma/ids.env
    python3 agents/cma/smoke_research.py
"""
import os

import anthropic

client = anthropic.Anthropic()

TASK = (
    "You are the research agent for fx-ai-trader. Propose 1-2 FRESH, pre-reg-able edge "
    "hypotheses worth testing next.\n"
    "\n"
    "CWD: you are ALREADY at the repo root (worker workdir). Do NOT run `find ~`/`find /` or "
    "interactive `sqlite3` with no SQL — they wedge the bash shell via the 120s timeout.\n"
    "\n"
    "PROCESS (do all three):\n"
    "  1. DEDUP FIRST — read what has already been tried or killed so you do NOT re-propose it: "
    "knowledge-base/wiki/index.md, knowledge-base/wiki/tier-master.md, and recent "
    "knowledge-base/wiki/lessons/ + decisions/. Known-dead/registered (do NOT re-propose): "
    "orb_trap|GBP_USD|SELL (just refuted), ema_trend_scalp, fib_reversal, session_time_bias, "
    "bb_rsi_reversion, hull_donchian multi-pair transfer. State what you checked.\n"
    "  2. EXTERNAL CONTEXT — use web_search / web_fetch for current regime + positioning: "
    "USDJPY intervention ceiling & carry, DXY, rate differentials, latest COT positioning, "
    "recent high-impact FX news. Cite sources.\n"
    "  3. STRUCTURE each hypothesis as a pre-reg ledger entry (this is what would be written to "
    "the Memory Store before any test):\n"
    "       - id, pair, direction, timeframe\n"
    "       - entry condition (precise, codeable), exit / TP-SL\n"
    "       - prior m (how many hypotheses in this family — for BH-FDR honesty)\n"
    "       - gates: Wilson_lo>=0.40, friction<=TP10%, WF on 12y history\n"
    "       - rationale tying the CURRENT external regime to why this edge should exist now\n"
    "\n"
    "CONSTRAINTS: XAU excluded. You are read-only (no write/edit tool) — output the ledger "
    "entries inline. A hypothesis whose TP is friction-dominated (friction>TP10%) is dead on "
    "arrival — pre-filter for that. Prefer edges grounded in a durable regime mechanism, not "
    "a dredged backtest bucket.\n"
    "\n"
    "Report: the dedup check result, the external-context summary with sources, and the 1-2 "
    "structured pre-reg hypotheses."
)


def main() -> None:
    session = client.beta.sessions.create(
        agent=os.environ["FXAI_RESEARCH_ID"],
        environment_id=os.environ["FXAI_ENV_ID"],
        title="research smoke test",
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
