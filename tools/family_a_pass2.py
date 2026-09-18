"""family A statement_ladder — pass-2 (frozen measurement).

🔒 Executes the measurement frozen in
knowledge-base/wiki/decisions/family-a-statement-ladder-prereg-2026-08-19.md §10.2,
unlocked by pass-1 (§10.3 Gate A ∧ Gate B, both PASS on 2026-09-18).

    J    = P(armed | intervention day) − P(armed | non-intervention day)
           (day-level Peirce / Youden skill score, m = 1)
    null = episode-block circular shift of the LABEL series, B = 10,000;
           when the number of distinct shifts is below B, all of them are used and
           p = (1 + #{J_shift ≥ J_obs}) / (1 + #shifts)
    α    = 0.05, one-sided (J > 0)

This consumes the family's single explore look. It must run **once**, on the
event set frozen by pass-1 and already landed on main
(`knowledge-base/raw/analysis/family-a-pass1-events-2026-09-18.json`).

Claim ceiling (§5, unchanged): effective N = 4 episode blocks, so **any result is
descriptive**. No edge claim, no live/tier/lot change, ever.

    python3 tools/family_a_pass2.py [--json out.json]
    python3 -m tools.family_a_pass2 [--json out.json]
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import pathlib
import sys

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools import family_a_ladder_detector as det  # noqa: E402
from tools.family_a_pass1 import EXPLORE_END, EXPLORE_START  # noqa: E402

LABELS_CSV = "data/external/mof_statements/interventions_daily.csv"
FROZEN_EVENTS_JSON = "knowledge-base/raw/analysis/family-a-pass1-events-2026-09-18.json"

# Frozen statistical design (§10.2)
B_SHIFTS = 10_000
ALPHA = 0.05
# Frozen population description (§3) — asserted, never inferred.
DIRECTION = "sell_USD_buy_JPY"
EPISODE_GAP_DAYS = 30
EXPECTED_INTERVENTION_DAYS = 10
EXPECTED_EPISODE_BLOCKS = 4


# --- labels -----------------------------------------------------------------
def load_intervention_days(path: str = LABELS_CSV) -> list[_dt.date]:
    """JPY-buying intervention days inside the frozen explore window."""
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["direction"] != DIRECTION:
                continue
            d = _dt.date.fromisoformat(row["date"])
            if EXPLORE_START <= d <= EXPLORE_END:
                out.append(d)
    return sorted(set(out))


def episode_blocks(days: list[_dt.date], gap: int = EPISODE_GAP_DAYS) -> list[list[_dt.date]]:
    blocks: list[list[_dt.date]] = []
    for d in days:
        if blocks and (d - blocks[-1][-1]).days < gap:
            blocks[-1].append(d)
        else:
            blocks.append([d])
    return blocks


# --- statistic --------------------------------------------------------------
def youden_j(armed: list[bool], label: list[bool]) -> float:
    npos = sum(label)
    nneg = len(label) - npos
    if npos == 0 or nneg == 0:
        return float("nan")
    tp = sum(1 for a, l in zip(armed, label) if l and a)
    fp = sum(1 for a, l in zip(armed, label) if (not l) and a)
    return tp / npos - fp / nneg


def circular_shift(label: list[bool], k: int) -> list[bool]:
    n = len(label)
    k %= n
    return label[-k:] + label[:-k] if k else list(label)


def permutation_p(armed: list[bool], label: list[bool], b: int = B_SHIFTS) -> dict:
    n = len(label)
    shifts = list(range(1, n))
    if len(shifts) > b:                       # subsample evenly, deterministic
        step = len(shifts) / b
        shifts = [shifts[int(i * step)] for i in range(b)]
    j_obs = youden_j(armed, label)
    null = [youden_j(armed, circular_shift(label, k)) for k in shifts]
    ge = sum(1 for j in null if j >= j_obs)
    null_sorted = sorted(null)
    return {
        "j_obs": j_obs,
        "p_one_sided": (1 + ge) / (1 + len(shifts)),
        "n_shifts": len(shifts),
        "null_mean": sum(null) / len(null),
        "null_p95": null_sorted[int(0.95 * len(null_sorted))],
        "null_max": null_sorted[-1],
    }


# --- run --------------------------------------------------------------------
def run() -> dict:
    out = det.build(EXPLORE_START, EXPLORE_END)
    days = out.days

    frozen = json.load(open(FROZEN_EVENTS_JSON, encoding="utf-8"))
    frozen_events = [_dt.date.fromisoformat(d) for d in frozen["events"]]
    if frozen_events != out.events:
        raise SystemExit(
            "ABORT: 凍結イベント集合と再計算が不一致 — pass-2 は凍結集合の上でしか走らせない\n"
            f"  frozen={frozen['events']}\n  rebuilt={[str(d) for d in out.events]}")

    iv_days = load_intervention_days()
    blocks = episode_blocks(iv_days)
    if len(iv_days) != EXPECTED_INTERVENTION_DAYS or len(blocks) != EXPECTED_EPISODE_BLOCKS:
        raise SystemExit(
            "ABORT: ラベル母集団が pre-reg §3 の宣言と不一致 — estimand が凍結時と違う\n"
            f"  期待 {EXPECTED_INTERVENTION_DAYS} 日 / {EXPECTED_EPISODE_BLOCKS} blocks\n"
            f"  実測 {len(iv_days)} 日 / {len(blocks)} blocks: {[str(d) for d in iv_days]}")

    off_bd = [d for d in iv_days if not det.is_business_day(d)]
    iv_set = set(iv_days)

    armed = [d in out.armed for d in days]
    label = [d in iv_set for d in days]
    stat = permutation_p(armed, label)

    npos = sum(label)
    tp = sum(1 for a, l in zip(armed, label) if l and a)
    fp = sum(1 for a, l in zip(armed, label) if (not l) and a)
    nneg = len(label) - npos

    # --- secondary (descriptive only, never decisive — §2 / §10.4 caveat) ---
    per_year = {}
    for yr in sorted({e.year for e in out.events}):
        ev = [e for e in out.events if e.year == yr]
        idx = {d: i for i, d in enumerate(days)}
        armed_y = set()
        for e in ev:
            i = idx[e]
            armed_y.update(days[i: i + det.H_HORIZON_BD + 1])
        a_y = [d in armed_y for d in days]
        # `hit_days` は armed 窓に入った介入「日」数、`events_with_hit` は
        # 窓内に 1 日以上の介入を含む「event」数。1 event が複数の介入日を
        # 覆うため両者は一致しない (2022: 1 event が 10-21 と 10-24 を覆う)。
        ev_hit = 0
        for e in ev:
            i = idx[e]
            if any(d in iv_set for d in days[i: i + det.H_HORIZON_BD + 1]):
                ev_hit += 1
        per_year[str(yr)] = {
            "n_events": len(ev),
            "events_with_hit": ev_hit,
            "hit_days": sum(1 for d in iv_days if d in armed_y),
            "j": youden_j(a_y, label),
        }

    lead = []
    for e in out.events:
        i = days.index(e)
        win = days[i: i + det.H_HORIZON_BD + 1]
        nxt = [d for d in iv_days if d in win]
        lead.append(win.index(nxt[0]) if nxt else None)

    verdict = (
        "PASS (記述級)" if stat["p_one_sided"] <= ALPHA and stat["j_obs"] > 0
        else "FAIL")

    return {
        "pre_reg": "family-a-statement-ladder-prereg-2026-08-19.md §10.2 / §10.4",
        "explore_window": [str(EXPLORE_START), str(EXPLORE_END)],
        "n_business_days": len(days),
        "events": [str(d) for d in out.events],
        "intervention_days": [str(d) for d in iv_days],
        "episode_blocks": [[str(d) for d in b] for b in blocks],
        "intervention_days_off_business_calendar": [str(d) for d in off_bd],
        "contingency": {"n_pos": npos, "n_neg": nneg, "armed_and_pos": tp,
                        "armed_and_neg": fp,
                        "tpr": tp / npos if npos else None,
                        "fpr": fp / nneg if nneg else None},
        "statistic": stat,
        "alpha": ALPHA,
        "verdict": verdict,
        "secondary_descriptive": {
            "per_event_year": per_year,
            "lead_business_days_per_event": lead,
        },
        "claim_ceiling": ("有効 N = 4 episode blocks。PASS でも記述級 — "
                          "edge 主張・live/tier/lot 変更は恒久ゼロ (§5)"),
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
