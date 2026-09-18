"""family A statement_ladder — pass-1 (label-free event enumeration + gates).

🔒 Runs the FROZEN detector (tools/family_a_ladder_detector.py, pre-reg
knowledge-base/wiki/decisions/family-a-statement-ladder-prereg-2026-08-19.md §10).

**This script must never read intervention labels.** pass-1 exists precisely so
that an UNDERPOWERED verdict can be reached without touching the explore
outcome — see pre-reg §10.3. The label join lives in pass-2 and is unlocked
only when Gate A and Gate B both pass.

    python3 tools/family_a_pass1.py [--json out.json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys

from tools import family_a_ladder_detector as det

# Frozen explore window (pre-reg §3 / §10.1)
EXPLORE_START = _dt.date(2022, 1, 7)
EXPLORE_END = _dt.date(2026, 7, 29)

_FORBIDDEN = ("interventions_daily", "interventions_monthly")


def _assert_label_free() -> None:
    """Structural guard: pass-1 must not have loaded any label source."""
    src = open(__file__, encoding="utf-8").read()
    body = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    for tok in _FORBIDDEN:
        # the literal appears only inside this tuple, never as a data path
        assert body.count(tok) <= 1, f"label source referenced: {tok}"


def run() -> dict:
    _assert_label_free()
    out = det.build(EXPLORE_START, EXPLORE_END)
    gates = det.pass1_gates(out)

    conf_raw = det.load_conference_levels()
    in_window = {d: lv for d, lv in conf_raw.items()
                 if EXPLORE_START <= d <= EXPLORE_END}
    rolled = [str(d) for d in sorted(in_window) if not det.is_business_day(d)]

    return {
        "pre_reg": "family-a-statement-ladder-prereg-2026-08-19.md §10",
        "explore_window": [str(EXPLORE_START), str(EXPLORE_END)],
        "params": {"T": det.T_CARRY_BD, "R": det.R_REARM_BD,
                   "H": det.H_HORIZON_BD, "trigger": det.TRIGGER_LEVEL},
        "conferences_in_window": len(in_window),
        "conferences_rolled_forward": rolled,
        "effective_level_hist": {
            str(lv): sum(1 for v in in_window.values() if v == lv)
            for lv in sorted(set(in_window.values()))},
        "events": [str(d) for d in out.events],
        "gates": gates,
        "verdict_hint": (
            "pass2_unlocked" if gates["pass2_unlocked"]
            else ("FAIL (Gate A: 非特異)" if not gates["gate_a_specificity"]
                  else "UNDERPOWERED / park (Gate B)")),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", dest="out", default="")
    args = ap.parse_args(argv)
    res = run()
    text = json.dumps(res, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
