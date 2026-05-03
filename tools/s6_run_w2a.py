#!/usr/bin/env python3
"""Run S6 Wave 2a diagnosis and write the decision artifact."""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.s6_w2a_diagnosis import DiagnosisRow, SpreadHour, run_diagnosis


ROOT = Path(__file__).resolve().parents[1]
CHART_DB = ROOT / "data" / "chart_patterns.db"
DEMO_DB = ROOT / "demo_trades.db"
PARQUET = ROOT / "data" / "cache" / "massive" / "USD_JPY_5m.parquet"
DECISION_DOC = ROOT / "knowledge-base" / "wiki" / "decisions" / "s6-w2a-diagnosis-2026-05-03.md"


def frozen_counts(db_path: Path) -> dict[str, int]:
    with sqlite3.connect(db_path) as con:
        return {
            "signals": int(con.execute("SELECT COUNT(*) FROM chart_pattern_signals").fetchone()[0]),
            "trades": int(con.execute("SELECT COUNT(*) FROM chart_pattern_bt_trades").fetchone()[0]),
            "verdicts": int(con.execute("SELECT COUNT(*) FROM chart_pattern_bt_verdicts").fetchone()[0]),
        }


def fmt(x: float | None, digits: int = 2) -> str:
    if x is None:
        return "NA"
    return f"{x:.{digits}f}"


def verdict_rows(rows: list[DiagnosisRow], axis: str, sub_key: str | None = None) -> list[DiagnosisRow]:
    out = [r for r in rows if r.axis == axis and (sub_key is None or r.sub_key == sub_key)]
    return sorted(out, key=lambda r: (r.pattern_id, r.sub_key))


def table_for_rows(rows: list[DiagnosisRow], title: str, max_rows: int | None = None) -> str:
    selected = rows if max_rows is None else rows[:max_rows]
    lines = [f"### {title}", "", "| pattern | sub_key | N | WR | EV | PF | Wilson_lo | BEV | Bonf_p | Kelly | verdict |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in selected:
        lines.append(
            f"| {r.pattern_name} | {r.sub_key} | {r.n} | {r.wr:.3f} | {r.ev_pips:.2f} | {fmt(r.pf)} | "
            f"{r.wilson_lo_95:.3f} | {r.bev_wr:.3f} | {r.bonferroni_p:.2e} | {r.kelly:.3f} | {r.proposed_verdict} |"
        )
    return "\n".join(lines)


def best_by_pattern(rows: list[DiagnosisRow], axis: str) -> list[DiagnosisRow]:
    grouped: dict[int, list[DiagnosisRow]] = defaultdict(list)
    for row in rows:
        if row.axis == axis:
            grouped[row.pattern_id].append(row)
    return [max(vals, key=lambda r: r.ev_pips) for _, vals in sorted(grouped.items()) if vals]


def write_decision_doc(path: Path, profile: list[SpreadHour], rows: list[DiagnosisRow], before_counts: dict[str, int], after_counts: dict[str, int], mode: str) -> None:
    spread_rows = verdict_rows(rows, "spread_adj")
    flips = [r for r in spread_rows if r.proposed_verdict != "REJECT"]
    rr_best = best_by_pattern(rows, "rr_optimal")
    hour_best = best_by_pattern(rows, "hour_bucket")
    pivot_best = best_by_pattern(rows, "pivot_quality")
    regime_best = best_by_pattern(rows, "regime")

    candidates = sorted(
        [r for r in rr_best + hour_best + pivot_best + regime_best if r.n >= 100],
        key=lambda r: (r.proposed_verdict in {"PROMOTE", "SHADOW"}, r.ev_pips, r.pf or 0.0),
        reverse=True,
    )[:3]

    h1 = "ACCEPT" if flips else "REJECT"
    h2_rescued_by_smaller_tp = any(
        r.ev_pips > 0 and r.sub_key in {"rr=0.50", "rr=0.75"} and r.ev_pips > next((s.ev_pips for s in spread_rows if s.pattern_id == r.pattern_id), -999)
        for r in rr_best
    )
    h2 = "ACCEPT" if h2_rescued_by_smaller_tp else "REJECT"
    h3 = "ACCEPT" if any(r.ev_pips > 0 for r in hour_best) else "REJECT"
    h4 = "ACCEPT" if not any(r.proposed_verdict in {"PROMOTE", "SHADOW"} for r in rows) else "REJECT"
    h5 = "INCONCLUSIVE"

    lines = [
        "# S6 Wave 2a Diagnosis — Spread-adjusted / 7-axis Cell Deepdive",
        "",
        "**Date**: 2026-05-03  ",
        f"**Scope**: USD_JPY M5 `{mode}` only; no LIVE / Shadow exposure  ",
        "**Input**: existing `chart_pattern_bt_trades`; no new BT run  ",
        "",
        "## Frozen Table Check",
        "",
        "| table | before | after | status |",
        "|---|---:|---:|---|",
    ]
    for key in ("signals", "trades", "verdicts"):
        status = "UNCHANGED" if before_counts[key] == after_counts[key] else "CHANGED"
        lines.append(f"| {key} | {before_counts[key]} | {after_counts[key]} | {status} |")

    lines += [
        "",
        "## Hypothesis Verdicts",
        "",
        "| hypothesis | verdict | evidence |",
        "|---|---|---|",
        f"| H1 spread profile rescues cell | {h1} | spread-adjusted flips={len(flips)}; " + ("non-REJECT found" if flips else "flat-1.5p REJECT remains valid") + " |",
        f"| H2 measured-move TP too far | {h2} | best R:R EV max={max((r.ev_pips for r in rr_best), default=0):.2f} pips; optimal multipliers are not below 1.0 |",
        f"| H3 hour bucket edge exists | {h3} | best hour-bucket EV max={max((r.ev_pips for r in hour_best), default=0):.2f} pips |",
        f"| H4 ATR 12-pattern family should be parked if no axis rescues edge | {h4} | PROMOTE/SHADOW rows={sum(1 for r in rows if r.proposed_verdict in {'PROMOTE','SHADOW'})} |",
        "| H5 triple_bottom WF1 macro sensitivity | INCONCLUSIVE | local VIX/DXY source not present; WF1 aggregate only |",
        "",
        "## Empirical Spread Profile",
        "",
        "| hour_utc | N | avg_rt_pips | median_rt_pips | p95_rt_pips |",
        "|---:|---:|---:|---:|---:|",
    ]
    for p in profile:
        lines.append(f"| {p.hour_utc} | {p.n_observations} | {p.avg_round_trip_spread_pips:.2f} | {p.median_round_trip_spread_pips:.2f} | {p.p95_round_trip_spread_pips:.2f} |")

    lines += ["", table_for_rows(spread_rows, "Axis 1 Spread-adjusted EV")]
    lines += ["", table_for_rows(verdict_rows(rows, "exit_reason"), "Axis 2 Exit Reason Distribution")]
    lines += ["", "### Axis 3 MAFE/MFE Distribution", ""]
    lines += ["| pattern | summary |", "|---|---|"]
    for r in verdict_rows(rows, "mafe_mfe"):
        lines.append(f"| {r.pattern_name} | {r.notes} |")
    lines += ["", table_for_rows(rr_best, "Axis 4 R:R Optimal by Pattern")]
    lines += ["", table_for_rows(hour_best, "Axis 5 Best Hour Bucket by Pattern")]
    lines += ["", table_for_rows(verdict_rows(rows, "early_hit"), "Axis 6 Early Hit Distribution")]
    lines += ["", table_for_rows(pivot_best, "Axis 7 Best Pivot Quality Quartile by Pattern")]
    lines += ["", table_for_rows(regime_best, "Axis 8 Best D1 EMA200 Regime by Pattern")]
    lines += ["", table_for_rows(verdict_rows(rows, "triple_bottom_wf1"), "Axis 9 Triple Bottom WF1 Deepdive")]

    lines += [
        "",
        "## Spread-adjusted Verdict Comparison",
        "",
        "| pattern | flat-1.5p verdict | spread-adj verdict | flip |",
        "|---|---|---|---|",
    ]
    for r in spread_rows:
        flip = "none" if r.proposed_verdict == "REJECT" else f"REJECT -> {r.proposed_verdict}"
        lines.append(f"| {r.pattern_name} | REJECT | {r.proposed_verdict} | {flip} |")
    if not flips:
        lines.append("")
        lines.append("Spread-adjusted EV did not rescue any cell. Current evidence supports that the flat-1.5p W2 REJECT was directionally valid.")

    lines += [
        "",
        "## Cell Root Cause and Wave 2b Proposed Fix",
        "",
        "| pattern | root cause | proposed fix |",
        "|---|---|---|",
    ]
    by_pattern = {r.pattern_id: r for r in spread_rows}
    for pattern_id, spread in by_pattern.items():
        best_rr = next((r for r in rr_best if r.pattern_id == pattern_id), None)
        best_hour = next((r for r in hour_best if r.pattern_id == pattern_id), None)
        best_pivot = next((r for r in pivot_best if r.pattern_id == pattern_id), None)
        root = "negative spread-adjusted EV"
        if best_rr and best_rr.ev_pips > spread.ev_pips:
            direction = "smaller TP helped" if best_rr.sub_key in {"rr=0.50", "rr=0.75"} else "larger TP was less bad"
            root += f"; R:R sensitive ({direction}, best {best_rr.sub_key})"
        if best_hour and best_hour.ev_pips > 0:
            root += f"; hour-local edge only in {best_hour.sub_key}"
        if best_pivot and best_pivot.ev_pips > 0:
            root += f"; pivot quality sensitive ({best_pivot.sub_key})"
        fix = f"test W2b geometry with {best_rr.sub_key if best_rr else 'rr=NA'}, {best_hour.sub_key if best_hour else 'hour=NA'}, {best_pivot.sub_key if best_pivot else 'pivot=NA'} as pre-registered diagnostic filters only"
        lines.append(f"| {spread.pattern_name} | {root} | {fix} |")

    lines += [
        "",
        "## Prioritized Wave 2b Candidate List",
        "",
        "| rank | pattern | axis | sub_key | N | EV | PF | proposed W2b test |",
        "|---:|---|---|---|---:|---:|---:|---|",
    ]
    for i, r in enumerate(candidates, 1):
        lines.append(f"| {i} | {r.pattern_name} | {r.axis} | {r.sub_key} | {r.n} | {r.ev_pips:.2f} | {fmt(r.pf)} | lock as diagnostic candidate; rerun out-of-sample only before eligibility |")

    lines += [
        "",
        "## Decision",
        "",
        "No LIVE or Shadow eligibility is created by this task. Wave 2b should remain a detector-geometry diagnosis, not a filter-stacking promotion path.",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default="USD_JPY")
    parser.add_argument("--tf", default="M5")
    parser.add_argument("--mode", default="isolated", choices=["isolated", "arbitrated", "reversed"])
    parser.add_argument("--chart-db", type=Path, default=CHART_DB)
    parser.add_argument("--demo-db", type=Path, default=DEMO_DB)
    parser.add_argument("--parquet", type=Path, default=PARQUET)
    parser.add_argument("--decision-doc", type=Path, default=DECISION_DOC)
    args = parser.parse_args(argv)

    before = frozen_counts(args.chart_db)
    profile, rows, _ = run_diagnosis(args.chart_db, args.demo_db, args.pair, args.tf, args.mode, args.parquet, write_db=True)
    after = frozen_counts(args.chart_db)
    write_decision_doc(args.decision_doc, profile, rows, before, after, args.mode)
    print(f"spread_profile_rows={len(profile)}")
    print(f"diagnosis_rows={len(rows)}")
    print(f"decision_doc={args.decision_doc}")
    print(f"frozen_counts_before={before}")
    print(f"frozen_counts_after={after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
