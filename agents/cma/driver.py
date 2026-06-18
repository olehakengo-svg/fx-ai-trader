"""Session driver + LIVE-flip Gate enforcement (the real-money last line of defense).

Run AFTER worker.py is up, in a second terminal:
    export ANTHROPIC_API_KEY=sk-ant-...
    export FXAI_ENV_ID=env_...            # from setup.sh
    export FXAI_COORDINATOR_ID=agent_...  # from setup.sh
    export GITHUB_VAULT_ID=vlt_...        # vault holding GitHub MCP OAuth cred
    python agents/cma/driver.py

SAFETY: LIVE flips are NOT wired to real env activation yet. evaluate_live_flip()
returns the decision only; the subprocess.run(...) that actually lights LIVE is
commented out. Verify the gates behave for several runs, THEN enable it.
"""
import json
import os

import anthropic

client = anthropic.Anthropic()

# ---- Final gate calibration (2026-06-16: N floor removed, Wilson-led) ----
GATES = dict(
    shadow_eval_min_n=10,                    # evaluation starts
    live_min_n=20,                           # LIVE flip eligibility
    wilson_lo=0.40,                          # primary statistical gate (FDR-corrected)
    lot_ramp={20: 1000, 35: 2500, 50: 5000},  # N -> lot units
    max_friction_pct_of_tp=10.0,
    fdr_q=0.10,
    kelly_frac=0.25,
    max_concurrent=12,                       # near-uncorrelated 12-cell portfolio (TP-HIT)
    max_new_per_week=3,
)


def lot_for_n(n: int) -> int:
    """Lot units by N ramp (0 if below LIVE eligibility)."""
    eligible = [units for thr, units in sorted(GATES["lot_ramp"].items()) if n >= thr]
    return eligible[-1] if eligible else 0


def evaluate_live_flip(inp: dict, state: dict) -> dict:
    fails = []
    if inp["shadow_n"] < GATES["live_min_n"]:
        fails.append(f"N {inp['shadow_n']} < {GATES['live_min_n']}")
    if inp["wilson_lo"] < GATES["wilson_lo"]:
        fails.append(f"Wilson_lo {inp['wilson_lo']} < {GATES['wilson_lo']}")
    if not inp["wf_folds_pass"]:
        fails.append("WF fold fail")
    if not inp["bonferroni_survive"]:
        fails.append("BH-FDR fail")
    if inp["friction_pct_of_tp"] > GATES["max_friction_pct_of_tp"]:
        fails.append("friction > TP10%")
    cap = lot_for_n(inp["shadow_n"])
    if inp["lot_units"] > cap:
        fails.append(f"lot {inp['lot_units']} > ramp cap {cap} for N={inp['shadow_n']}")
    if state["flips_this_week"] >= GATES["max_new_per_week"]:
        fails.append("weekly auto-flip cap")
    if state["concurrent"] >= GATES["max_concurrent"]:
        fails.append("concurrent cap")
    if fails:
        return {"decision": "rejected", "reasons": fails}

    # ---- Reversible-range pass -> auto-flip ----
    # SAFETY: keep commented until gates are verified over several dry runs.
    # subprocess.run(["python", "tools/live_promote.py",
    #                 "--strategy", inp["strategy_id"],
    #                 "--lot", str(min(inp["lot_units"], cap)),
    #                 "--demote-live-n", "5" if inp["shadow_n"] < 35 else "10"])
    state["flips_this_week"] += 1
    state["concurrent"] += 1
    return {"decision": "auto_flipped_DRYRUN", "lot": min(inp["lot_units"], cap),
            "fast_demote": inp["shadow_n"] < 35}


def main() -> None:
    agent_id = os.environ["FXAI_COORDINATOR_ID"]
    env_id = os.environ["FXAI_ENV_ID"]
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=env_id,
        vault_ids=[os.environ["GITHUB_VAULT_ID"]],
        title="fxai autoimprove run",
    )
    print(f"Watch: https://platform.claude.com/workspaces/default/sessions/{session.id}")

    state = {"flips_this_week": 0, "concurrent": 0}
    # Stream-first, then send the outcome kickoff.
    stream = client.beta.sessions.events.stream(session_id=session.id)
    rubric = open(os.path.join(os.path.dirname(__file__), "edge_promotion_rubric.md")).read()
    client.beta.sessions.events.send(session_id=session.id, events=[{
        "type": "user.define_outcome",
        "description": ("fx-ai-trader の負け要因を1つ特定し、shadow-first で検証済みエッジに転換する。"
                        "北極星=月利だが昇格は rubric 準拠。pre-reg を先に台帳へ。"),
        "rubric": {"type": "text", "content": rubric},
        "max_iterations": 5,
    }])

    for ev in stream:
        if ev.type == "agent.custom_tool_use":
            if ev.name == "propose_live_flip":
                result = evaluate_live_flip(ev.input, state)
            else:  # propose_sizing_change -> always human
                result = {"decision": "queued_for_human", "detail": ev.input}
            print(f"[custom_tool] {ev.name} -> {result}")
            client.beta.sessions.events.send(session_id=session.id, events=[{
                "type": "user.custom_tool_result",
                "custom_tool_use_id": ev.id,
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            }])
        elif ev.type == "session.status_idle" and ev.stop_reason.type != "requires_action":
            break
        elif ev.type == "session.status_terminated":
            break


if __name__ == "__main__":
    main()
