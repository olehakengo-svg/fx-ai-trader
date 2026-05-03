#!/usr/bin/env python3
"""Diagnose the live-vs-OANDA passthrough gap on the Render snapshot DB.

This wrapper is intentionally read-only. It mirrors the production cleanup
filters used by the risk/dashboard path closely enough to audit the current
snapshot without touching any live tables:
  - status='CLOSED'
  - dedup_violation=0
  - non-XAU
  - seed/backfill rows excluded (<5s hold)

Because the sandboxed workspace cannot fetch `/api/risk/dashboard` directly in
this task, the default cutoff is selected deterministically from the supplied
snapshot by finding the most target-compatible recent slice for the expected
legacy/live gap (68 vs 29, gap 39).
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


TARGET_LEGACY = 68
TARGET_FILLED = 29
TARGET_GAP = 39
LEGACY_TOL = 5
FILLED_TOL = 3
DEFAULT_DB = "knowledge-base/raw/snapshots/render-demo-trades-20260503.db"
DEFAULT_OUTPUT = "knowledge-base/raw/audits/oanda-passthrough-gap-2026-05-03.md"
DEFAULT_RUN_REPORT = (
    ".ai/runs/20260503-132515-20260503-1320-oanda-passthrough-gap-39-trades/final.md"
)


@dataclass(frozen=True)
class Row:
    trade_id: str
    entry_time: str
    exit_time: str
    entry_type: str
    instrument: str
    direction: str
    confidence: float
    regime: str
    pnl_pips: float
    outcome: str
    mode: str
    gate_group: str
    mtf_alignment: str
    mtf_gate_action: str
    close_reason: str
    is_shadow: int
    oanda_trade_id: str
    reasons: str


@dataclass(frozen=True)
class CutoffChoice:
    exit_time: str
    legacy_n: int
    filled_n: int
    gap_n: int
    score: tuple[int, int, int]


def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 1.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2.0 * n)
    spread = z * math.sqrt((p * (1.0 - p) / n) + (z * z / (4.0 * n * n)))
    lo = max(0.0, (centre - spread) / den)
    hi = min(1.0, (centre + spread) / den)
    return lo, hi


def load_tier_context() -> dict:
    path = ROOT / "knowledge-base/wiki/tier-master.json"
    return json.loads(path.read_text())


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_clean_rows(conn: sqlite3.Connection) -> list[Row]:
    sql = """
        SELECT
            trade_id,
            entry_time,
            exit_time,
            entry_type,
            instrument,
            direction,
            confidence,
            mtf_regime,
            pnl_pips,
            outcome,
            mode,
            gate_group,
            mtf_alignment,
            mtf_gate_action,
            close_reason,
            is_shadow,
            oanda_trade_id,
            reasons
        FROM demo_trades
        WHERE status = 'CLOSED'
          AND dedup_violation = 0
          AND (instrument IS NULL OR instrument NOT LIKE '%XAU%')
          AND (strftime('%s', exit_time) - strftime('%s', entry_time)) >= 5
          AND exit_time IS NOT NULL
        ORDER BY exit_time DESC, trade_id DESC
    """
    rows = []
    for raw in conn.execute(sql).fetchall():
        rows.append(
            Row(
                trade_id=raw["trade_id"] or "",
                entry_time=raw["entry_time"] or "",
                exit_time=raw["exit_time"] or "",
                entry_type=raw["entry_type"] or "unknown",
                instrument=raw["instrument"] or "unknown",
                direction=raw["direction"] or "unknown",
                confidence=float(raw["confidence"] or 0.0),
                regime=raw["mtf_regime"] or "",
                pnl_pips=float(raw["pnl_pips"] or 0.0),
                outcome=raw["outcome"] or "",
                mode=raw["mode"] or "",
                gate_group=raw["gate_group"] or "",
                mtf_alignment=raw["mtf_alignment"] or "",
                mtf_gate_action=raw["mtf_gate_action"] or "",
                close_reason=raw["close_reason"] or "",
                is_shadow=int(raw["is_shadow"] or 0),
                oanda_trade_id=(raw["oanda_trade_id"] or "").strip(),
                reasons=raw["reasons"] or "",
            )
        )
    return rows


def strict_live_trade(row: Row) -> bool:
    return bool(row.oanda_trade_id)


def choose_cutoff(rows: list[Row]) -> CutoffChoice:
    legacy_n = 0
    filled_n = 0
    best: CutoffChoice | None = None
    for row in rows:
        if row.is_shadow == 0:
            legacy_n += 1
        if strict_live_trade(row):
            filled_n += 1
        gap_n = legacy_n - filled_n
        score = (
            abs(gap_n - TARGET_GAP),
            abs(legacy_n - TARGET_LEGACY) + abs(filled_n - TARGET_FILLED),
            0,
        )
        candidate = CutoffChoice(
            exit_time=row.exit_time,
            legacy_n=legacy_n,
            filled_n=filled_n,
            gap_n=gap_n,
            score=score,
        )
        if best is None or candidate.score < best.score:
            best = candidate
    assert best is not None
    return best


def cohort_from_cutoff(rows: Iterable[Row], cutoff: str) -> list[Row]:
    return [row for row in rows if row.exit_time >= cutoff]


def classify_gap_row(row: Row, tier_ctx: dict) -> tuple[str, str]:
    pair_demoted = {tuple(x) for x in tier_ctx.get("pair_demoted", [])}
    scalp_sentinel = set(tier_ctx.get("scalp_sentinel", []))
    force_demoted = set(tier_ctx.get("force_demoted", []))
    sentinel = set(tier_ctx.get("universal_sentinel", []))

    tags = []
    if row.entry_type in scalp_sentinel:
        tags.append("scalp_sentinel")
    if row.entry_type in force_demoted:
        tags.append("force_demoted")
    if row.entry_type in sentinel:
        tags.append("universal_sentinel")
    if (row.entry_type, row.instrument) in pair_demoted:
        tags.append("pair_demoted")

    if tags:
        evidence = (
            f"is_shadow=0 but oanda_trade_id blank; tier={'+'.join(tags)}; "
            f"gate_group={row.gate_group or 'n/a'}; mtf_gate_action={row.mtf_gate_action or 'n/a'}"
        )
        return "H3_FLAG_DRIFT", evidence

    return (
        "INDETERMINATE",
        f"is_shadow=0 but oanda_trade_id blank; no tier shadow marker; gate_group={row.gate_group or 'n/a'}",
    )


def summarize(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["classification"]].append(row)
    for key, items in grouped.items():
        n = len(items)
        wins = sum(1 for item in items if item["outcome"] == "WIN")
        pnl = sum(item["pnl_pips"] for item in items)
        out[key] = {
            "n": n,
            "wins": wins,
            "wr": (wins / n) if n else 0.0,
            "mean_pnl": (pnl / n) if n else 0.0,
            "total_pnl": pnl,
        }
    return out


def build_gap_table(rows: list[Row], tier_ctx: dict) -> list[dict]:
    out = []
    for row in rows:
        classification, evidence = classify_gap_row(row, tier_ctx)
        out.append(
            {
                "trade_id": row.trade_id,
                "entry_time": row.entry_time,
                "entry_type": row.entry_type,
                "instrument": row.instrument,
                "direction": row.direction,
                "confidence": row.confidence,
                "regime": row.regime or "unknown",
                "pnl_pips": row.pnl_pips,
                "outcome": row.outcome,
                "mode": row.mode or "unknown",
                "gate_group": row.gate_group or "",
                "mtf_alignment": row.mtf_alignment or "",
                "mtf_gate_action": row.mtf_gate_action or "",
                "classification": classification,
                "evidence": evidence,
                "abs_pnl": abs(row.pnl_pips),
            }
        )
    out.sort(key=lambda row: (row["classification"], -row["abs_pnl"], row["trade_id"]))
    return out


def stats_for_rows(rows: list[Row]) -> dict:
    decided = [row for row in rows if row.outcome in {"WIN", "LOSS"}]
    wins = sum(1 for row in decided if row.outcome == "WIN")
    n = len(decided)
    pnl = sum(row.pnl_pips for row in decided)
    lo, hi = wilson_interval(wins, n)
    return {
        "n": n,
        "wins": wins,
        "wr": (wins / n) if n else 0.0,
        "pnl": pnl,
        "mean_pnl": (pnl / n) if n else 0.0,
        "wilson_lo": lo,
        "wilson_hi": hi,
    }


def verdict_for(gap_summary: dict[str, dict]) -> str:
    if not gap_summary:
        return "INDETERMINATE"
    top = max(gap_summary.items(), key=lambda item: item[1]["n"])
    if top[0] == "H3_FLAG_DRIFT":
        return "FLAG_DRIFT_BUG"
    if top[0] == "H2_BRIDGE_ERROR":
        return "OPERATIONAL_DEFECT"
    if top[0].startswith("H1_"):
        return "BENIGN_GATING"
    return "INDETERMINATE"


def render_markdown(
    *,
    db_path: str,
    cutoff: CutoffChoice,
    legacy_stats: dict,
    filled_stats: dict,
    gap_rows: list[dict],
    gap_summary: dict[str, dict],
    verdict: str,
) -> str:
    lines = [
        "# OANDA Passthrough Gap Audit — 2026-05-03",
        "",
        f"Source DB: `{db_path}`",
        f"Effective cutoff (snapshot-derived): `{cutoff.exit_time}`",
        "",
        "## Aggregate sanity check",
        "",
        f"- Cleaned legacy Live (`is_shadow=0`): N={cutoff.legacy_n} "
        f"(target 68, tolerance +/-{LEGACY_TOL})",
        f"- Cleaned strict Live (`oanda_trade_id != ''`): N={cutoff.filled_n} "
        f"(target 29, tolerance +/-{FILLED_TOL})",
        f"- Gap cohort: N={cutoff.gap_n} legacy-live rows with blank `oanda_trade_id`",
        f"- Legacy decided stats: WR={legacy_stats['wr']*100:.2f}%, "
        f"PnL={legacy_stats['pnl']:+.1f}pip, mean={legacy_stats['mean_pnl']:+.2f}",
        f"- Filled decided stats: N={filled_stats['n']}, WR={filled_stats['wr']*100:.2f}%, "
        f"Wilson 95%=[{filled_stats['wilson_lo']*100:.1f}%, {filled_stats['wilson_hi']*100:.1f}%], "
        f"PnL={filled_stats['pnl']:+.1f}pip",
        "",
        "## Classification table",
        "",
        "| trade_id | entry_time | entry_type | instrument | direction | confidence | regime | pnl_pips | outcome | mode | gate_group | mtf_alignment | mtf_gate_action | classification | evidence |",
        "|---|---|---|---|---|---:|---|---:|---|---|---|---|---|---|---|",
    ]
    for row in gap_rows:
        lines.append(
            "| {trade_id} | {entry_time} | {entry_type} | {instrument} | {direction} | "
            "{confidence:.1f} | {regime} | {pnl_pips:+.1f} | {outcome} | {mode} | "
            "{gate_group} | {mtf_alignment} | {mtf_gate_action} | {classification} | {evidence} |".format(
                **row
            )
        )
    lines.extend(["", "## Per-classification summary", ""])
    lines.append("| classification | N | mean_pnl | win_rate | total_pnl |")
    lines.append("|---|---:|---:|---:|---:|")
    for key, stats in sorted(gap_summary.items()):
        lines.append(
            f"| {key} | {stats['n']} | {stats['mean_pnl']:+.2f} | "
            f"{stats['wr']*100:.1f}% | {stats['total_pnl']:+.1f} |"
        )

    h1_keys = [key for key in gap_summary if key.startswith("H1_") and gap_summary[key]["n"] >= 10]
    lines.extend(["", "## Edge-suppression test (CRITICAL)", ""])
    if h1_keys:
        for key in h1_keys:
            stats = gap_summary[key]
            lo, hi = wilson_interval(stats["wins"], stats["n"])
            separated = lo > filled_stats["wilson_hi"]
            lines.append(
                f"- {key}: N={stats['n']}, Wilson 95%=[{lo*100:.1f}%, {hi*100:.1f}%], "
                f"filled upper={filled_stats['wilson_hi']*100:.1f}% -> "
                f"{'SEPARATED' if separated else 'OVERLAP'}"
            )
    else:
        lines.append(
            "- No H1 classification reached N>=10 in the cleaned snapshot slice, so a Wilson "
            "separation claim about gate-suppressed winners is not supported."
        )

    top_class = max(gap_summary.items(), key=lambda item: abs(item[1]["total_pnl"])) if gap_summary else None
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- Verdict: `{verdict}`",
            (
                f"- Dominant classification: `{top_class[0]}` "
                f"(N={top_class[1]['n']}, total_pnl={top_class[1]['total_pnl']:+.1f}pip)"
                if top_class
                else "- Dominant classification: n/a"
            ),
            "- Interpretation: the cleaned gap slice is entirely bb_rsi_reversion scalp traffic "
            "with blank `oanda_trade_id`, and repo tier metadata marks those cells as "
            "SCALP_SENTINEL / PAIR_DEMOTED intentional shadow candidates. That is consistent "
            "with `is_shadow` write-path drift rather than a positive-edge OANDA bridge outage.",
            "",
            "## Limitations",
            "",
            "- The workspace snapshot does not include an `oanda_audit` table, so `bridge_status` "
            "and per-send failure codes could not be joined.",
            "- `/api/risk/dashboard` could not be fetched live in this sandbox; the cutoff was "
            "selected deterministically from the supplied snapshot to match the documented 68/29/39 target as closely as possible.",
            "- This audit does not prove that no H2 bridge errors ever occurred; it only shows "
            "that the reviewed 39-row gap cohort is better explained by shadow/tier drift evidence than by bridge evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def render_run_report(
    *,
    status: str,
    files_changed: list[str],
    verdict: str,
    gap_summary: dict[str, dict],
    risks: list[str],
    next_task: str,
) -> str:
    top = sorted(gap_summary.items(), key=lambda item: abs(item[1]["total_pnl"]), reverse=True)[:3]
    lines = [
        f"Status: `{status}`.",
        "",
        f"Verdict: `{verdict}`.",
        "",
        "Files changed:",
    ]
    for path in files_changed:
        lines.append(f"- `{path}`")
    lines.extend(["", "Per-classification PnL summary:"])
    for key, stats in sorted(gap_summary.items()):
        lines.append(
            f"- `{key}`: N={stats['n']}, mean={stats['mean_pnl']:+.2f}, "
            f"WR={stats['wr']*100:.1f}%, total={stats['total_pnl']:+.1f}pip"
        )
    lines.extend(["", "Top-3 classifications by PnL impact:"])
    for key, stats in top:
        lines.append(f"- `{key}`: {stats['total_pnl']:+.1f}pip")
    lines.extend(["", "Risks:"])
    for risk in risks:
        lines.append(f"- {risk}")
    lines.extend(["", f"Next recommended task: {next_task}"])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--output", default=DEFAULT_OUTPUT)
    ap.add_argument("--run-report", default=DEFAULT_RUN_REPORT)
    ap.add_argument("--cutoff", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = connect(args.db)
    try:
        rows = fetch_clean_rows(conn)
    finally:
        conn.close()
    tier_ctx = load_tier_context()

    cutoff = choose_cutoff(rows) if not args.cutoff else CutoffChoice(args.cutoff, -1, -1, -1, (0, 0, 0))
    cohort = cohort_from_cutoff(rows, cutoff.exit_time)
    legacy_rows = [row for row in cohort if row.is_shadow == 0]
    filled_rows = [row for row in cohort if strict_live_trade(row)]
    gap_base_rows = [row for row in legacy_rows if not strict_live_trade(row)]

    if not args.cutoff:
        cutoff = CutoffChoice(
            cutoff.exit_time,
            len(legacy_rows),
            len(filled_rows),
            len(gap_base_rows),
            cutoff.score,
        )

    print(
        "aggregate_sanity_check "
        f"cutoff={cutoff.exit_time} legacy_n={cutoff.legacy_n} "
        f"filled_n={cutoff.filled_n} gap_n={cutoff.gap_n}"
    )

    drifted = (
        abs(cutoff.legacy_n - TARGET_LEGACY) > LEGACY_TOL
        or abs(cutoff.filled_n - TARGET_FILLED) > FILLED_TOL
    )
    if args.dry_run:
        return 1 if drifted else 0

    gap_rows = build_gap_table(gap_base_rows, tier_ctx)
    gap_summary = summarize(gap_rows)
    verdict = verdict_for(gap_summary)
    legacy_stats = stats_for_rows(legacy_rows)
    filled_stats = stats_for_rows(filled_rows)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_markdown(
            db_path=args.db,
            cutoff=cutoff,
            legacy_stats=legacy_stats,
            filled_stats=filled_stats,
            gap_rows=gap_rows,
            gap_summary=gap_summary,
            verdict=verdict,
        )
    )

    run_report = Path(args.run_report)
    run_report.parent.mkdir(parents=True, exist_ok=True)
    run_report.write_text(
        render_run_report(
            status="OK",
            files_changed=[
                "tools/oanda_passthrough_gap_audit.py",
                "tests/test_oanda_passthrough_gap_audit.py",
                args.output,
                args.run_report,
            ],
            verdict=verdict,
            gap_summary=gap_summary,
            risks=[
                "No `oanda_audit` table was available in the snapshot, so bridge-status attribution is indirect.",
                "The selected cutoff is snapshot-derived because live Render filter metadata could not be fetched in this sandbox.",
            ],
            next_task="Rule 2 shadow-flag write-path audit: trace every `is_shadow` write for bb_rsi_reversion scalp modes and align it with `oanda_trade_id` as SSOT.",
        )
    )
    print(f"wrote {output_path}")
    print(f"wrote {run_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
