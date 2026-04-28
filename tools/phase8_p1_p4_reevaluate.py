"""
Phase 8 re-evaluation under P1 (n-scaled Wilson gate) and P4 (per-track
Bonferroni). Reads the existing Phase 8 stage1/stage2 JSON outputs and
reports which cells survive under the corrected gates.

Usage:
    python3 tools/phase8_p1_p4_reevaluate.py [--target-wr 0.5] [--alpha 0.05]
        [--out raw/phase8/p1_p4_reevaluation_<date>.md]

Reads:
    raw/phase8/track_a/stage1_20260428_0507.json (full 720-cell stage1)
    raw/phase8/track_a/stage2_holdout_20260428_0507.json (5 cells in holdout)
    raw/phase8/track_b/stage1_seqscan_20260428_0504.json (2087 cells)
    raw/phase8/track_c/stage1_decile_20260428_0504.json (1200 single)
    raw/phase8/track_c/stage2_decile_pair_20260428_0515.json (8604 pair)
    raw/phase8/track_d/stage1_boundary_20260428_0506.json (180 cells)
    raw/phase8/track_d/stage2_subwindow_20260428_0506.json (1200 cells)
    raw/phase8/track_e/stage1_20260428_0507.json (846 cells)

Outputs:
    raw/phase8/p1_p4_reevaluation_<date>.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.edge_discovery.power_analysis import (
    n_scaled_wilson_gate,
    min_detectable_wr,
    min_n_for_wilson,
    bonferroni_per_family,
    wilson_lower_at,
)
from research.edge_discovery.significance import benjamini_hochberg

PHASE8_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw", "phase8")

TRACK_INPUTS = {
    "A": {
        "stage1": os.path.join(PHASE8_ROOT, "track_a", "stage1_20260428_0507.json"),
        "stage2": os.path.join(PHASE8_ROOT, "track_a", "stage2_holdout_20260428_0507.json"),
    },
    "B": {
        "stage1": os.path.join(PHASE8_ROOT, "track_b", "stage1_seqscan_20260428_0504.json"),
        "stage2": os.path.join(PHASE8_ROOT, "track_b", "stage2_holdout_20260428_0512.json"),
    },
    "C": {
        "stage1": os.path.join(PHASE8_ROOT, "track_c", "stage1_decile_20260428_0504.json"),
        "stage2": os.path.join(PHASE8_ROOT, "track_c", "stage2_decile_pair_20260428_0515.json"),
    },
    "D": {
        "stage1": os.path.join(PHASE8_ROOT, "track_d", "stage1_boundary_20260428_0506.json"),
        "stage2": os.path.join(PHASE8_ROOT, "track_d", "stage2_subwindow_20260428_0506.json"),
    },
    "E": {
        "stage1": os.path.join(PHASE8_ROOT, "track_e", "stage1_20260428_0507.json"),
    },
}


def _load_results(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        d = json.load(f)
    if isinstance(d, dict):
        for key in ("all_results", "results", "survivors"):
            if isinstance(d.get(key), list):
                return d[key]
        return []
    if isinstance(d, list):
        return d
    return []


def _cell_n_wr_p(cell: dict[str, Any]) -> tuple[int, float, float] | None:
    n = cell.get("n_trades") or cell.get("n") or 0
    wr = cell.get("wr") or 0.0
    p = cell.get("p_value") or cell.get("p") or 1.0
    if not n or n <= 0:
        return None
    return int(n), float(wr), float(p)


def evaluate_track_p1_p4(
    track: str,
    target_wr: float,
    alpha: float,
) -> dict[str, Any]:
    """Apply n-scaled Wilson gate (P1) + per-track Bonferroni (P4)."""
    paths = TRACK_INPUTS[track]
    s1 = _load_results(paths["stage1"])
    s2 = _load_results(paths.get("stage2", ""))

    n_tests = len(s1)
    bonf_thresh = alpha / max(1, n_tests)

    # Pre-compute BH-FDR mask over all stage1 cells (q=0.10 to match Phase 7/8 LOCK)
    p_values: list[float] = []
    for c in s1:
        nwp = _cell_n_wr_p(c)
        p_values.append(nwp[2] if nwp else 1.0)
    bh_mask = benjamini_hochberg(p_values, q=0.10)

    survivors_bonf = []
    survivors_bh = []
    for idx, c in enumerate(s1):
        nwp = _cell_n_wr_p(c)
        if not nwp:
            continue
        n, wr, p = nwp
        wlo_actual = wilson_lower_at(wr, n)
        wlo_gate = n_scaled_wilson_gate(n, target_wr=target_wr)
        passes_p1 = wlo_actual >= wlo_gate
        passes_bonf = p <= bonf_thresh
        passes_bh = bh_mask[idx]
        if not passes_p1:
            continue
        ev = c.get("ev_net_pip", 0.0)
        if isinstance(ev, (int, float)) and ev <= 0:
            continue
        rec = {
            "n": n,
            "wr": wr,
            "wilson_lower_actual": round(wlo_actual, 4),
            "wilson_lower_gate": round(wlo_gate, 4),
            "p_value": p,
            **{k: v for k, v in c.items() if k in (
                "pair", "direction", "forward_bars", "triplet",
                "buckets", "boundary", "sub_window_utc", "pattern",
                "pattern_kind", "regime", "atr_pct_60d_b",
                "bbpb_15m_b", "ev_net_pip", "pf",
            )},
        }
        if passes_bonf:
            survivors_bonf.append(rec)
        if passes_bh:
            survivors_bh.append(rec)

    return {
        "track": track,
        "n_tests_stage1": n_tests,
        "bonferroni_threshold": bonf_thresh,
        "bonferroni_survivors_count": len(survivors_bonf),
        "bonferroni_survivors": survivors_bonf,
        "bh_fdr_survivors_count": len(survivors_bh),
        "bh_fdr_survivors": survivors_bh,
        "stage2_holdout_count": len(s2) if isinstance(s2, list) else 0,
    }


def render_markdown(report: dict[str, Any], target_wr: float, alpha: float) -> str:
    lines: list[str] = []
    lines.append(f"# Phase 8 Re-evaluation under P1 (n-scaled Wilson) + P4 (per-track Bonferroni)")
    lines.append("")
    lines.append(f"- Date: {date.today().isoformat()}")
    lines.append(f"- target_wr: {target_wr}")
    lines.append(f"- alpha: {alpha}")
    lines.append(f"- Original Phase 8 master gate: ``Wilson_lower_holdout > 0.48`` fixed")
    lines.append(f"- New gates: P1 = ``Wilson_lower(n) > wilson_lower_at(target_wr={target_wr}, n)``; P4 = Bonferroni per track")
    lines.append("")
    lines.append("## Per-track summary")
    lines.append("")
    lines.append("| Track | Stage1 n_tests | Bonf thresh | P1+Bonf survivors | P1+BH-FDR(0.10) survivors |")
    lines.append("|---|---|---|---|---|")
    for trk, r in report.items():
        lines.append(
            f"| {trk} | {r['n_tests_stage1']} | {r['bonferroni_threshold']:.2e} "
            f"| {r['bonferroni_survivors_count']} | {r['bh_fdr_survivors_count']} |"
        )
    lines.append("")

    for kind, sv_key in (("Bonferroni per-track", "bonferroni_survivors"),
                          ("BH-FDR(0.10) per-track", "bh_fdr_survivors")):
        lines.append(f"## Survivors detail ({kind}, top 20 per track by Wilson_lower)")
        lines.append("")
        for trk, r in report.items():
            lines.append(f"### Track {trk}")
            sv = r[sv_key]
            if not sv:
                lines.append("(no survivors)")
                lines.append("")
                continue
            sv = sorted(sv, key=lambda x: -x["wilson_lower_actual"])[:20]
            keys = list(sv[0].keys())
            lines.append("| " + " | ".join(keys) + " |")
            lines.append("|" + "---|" * len(keys))
            for c in sv:
                lines.append("| " + " | ".join(str(c[k]) for k in keys) + " |")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-wr", type=float, default=0.5)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    out = args.out or os.path.join(
        PHASE8_ROOT, f"p1_p4_reevaluation_{date.today().isoformat()}.md"
    )

    report: dict[str, Any] = {}
    for trk in sorted(TRACK_INPUTS.keys()):
        report[trk] = evaluate_track_p1_p4(trk, args.target_wr, args.alpha)

    md = render_markdown(report, args.target_wr, args.alpha)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(md)

    print(f"Wrote {out}")
    n_bonf = sum(r["bonferroni_survivors_count"] for r in report.values())
    n_bh = sum(r["bh_fdr_survivors_count"] for r in report.values())
    print(f"Total survivors P1+Bonf-per-track: {n_bonf}")
    print(f"Total survivors P1+BH-FDR(0.10)-per-track: {n_bh}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
