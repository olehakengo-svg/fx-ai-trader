#!/usr/bin/env python3
"""Aggregate Kelly decomposition audit for post-cutoff Live trades.

Thin wrapper around the existing cell-audit helpers:
  - reuses Wilson/stat helpers from tools.cell_edge_audit
  - reuses Wilson companion interval logic from tools.cell_negative_edge_audit
  - reuses Kelly math from modules.stats_utils
"""
from __future__ import annotations

import argparse
import math
import sqlite3
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.stats_utils import kelly_criterion
from research.edge_discovery.significance import binomial_one_sided_p
from tools.cell_edge_audit import wilson_lower
from tools.cell_negative_edge_audit import wilson_upper_at

POST_CUTOFF = "2026-04-08"
EXPECTED_N = 286
EXPECTED_WR = 0.3811
EXPECTED_EV = -0.80
EXPECTED_PNL = -228.6
EXPECTED_EDGE = -0.1804
EXPECTED_FULL_KELLY = 0.0
WR_TOL = 0.005
EDGE_TOL = 0.005
EV_TOL = 0.5
PNL_TOL = 0.5

PAIR_BEV_WR = {
    "USD_JPY": 0.344,
    "EUR_USD": 0.397,
    "GBP_USD": 0.379,
    "EUR_JPY": 0.337,
    "GBP_JPY": 0.344,
}
PAIR_ORDER = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]
SESSION_ORDER = ["Tokyo", "London", "NY", "overlap_LN", "Asia_early", "Sydney"]
REGIME_ORDER = ["bull", "bear", "range", "mixed", "unknown"]
DEMOTE_MARGIN = 0.05
MIN_TABLE_N = 5
MIN_DEMOTE_N = 8
EXCLUDED_INSTRUMENTS = ("XAU_USD", "EUR_GBP")


@dataclass(frozen=True)
class AggregateSnapshot:
    n: int
    wins: int
    losses: int
    wr: float
    ev_pip: float
    pnl_pip: float
    edge: float
    full_kelly: float


@dataclass(frozen=True)
class AxisSpec:
    name: str
    heading: str
    dims: tuple[str, ...]


AXES = [
    AxisSpec("pair", "Pair", ("pair",)),
    AxisSpec("strategy_pair", "Strategy x Pair", ("entry_type", "pair")),
    AxisSpec("session", "Session", ("session",)),
    AxisSpec("regime", "MTF Regime label", ("regime",)),
]


def classify_session_utc(entry_time_iso: str) -> str:
    if not entry_time_iso:
        return "unknown"
    ts = datetime.fromisoformat(entry_time_iso.replace("Z", "+00:00"))
    h = ts.astimezone(timezone.utc).hour
    if 13 <= h < 17:
        return "overlap_LN"
    if 17 <= h < 22:
        return "NY"
    if 7 <= h < 13:
        return "London"
    if 2 <= h < 7:
        return "Tokyo"
    if 0 <= h < 2:
        return "Asia_early"
    return "Sydney"


def normalize_regime_label(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if not value:
        return "unknown"
    if value.startswith("trend_up"):
        return "bull"
    if value.startswith("trend_down"):
        return "bear"
    if value.startswith("range"):
        return "range"
    if value in {"uncertain", "mixed"}:
        return "mixed"
    return "unknown"


def binomial_one_sided_lower_p(wins: int, n: int, p0: float) -> float:
    if n <= 0:
        return 1.0
    if wins < 0:
        return 0.0
    if wins >= n:
        return 1.0
    return max(0.0, 1.0 - binomial_one_sided_p(wins + 1, n, p0))


def assign_flag(*, n: int, ev_pip: float, wilson_upper: float, bev_wr: float) -> str:
    if n >= MIN_DEMOTE_N and ev_pip < 0 and wilson_upper < (bev_wr - DEMOTE_MARGIN):
        return "DEMOTE"
    if n >= MIN_TABLE_N and ev_pip < 0:
        return "WATCH"
    return "OK"


def build_snapshot(rows: Iterable[dict]) -> AggregateSnapshot:
    rows = list(rows)
    wins = sum(1 for row in rows if row["outcome"] == "WIN")
    losses = sum(1 for row in rows if row["outcome"] == "LOSS")
    n = len(rows)
    pnl = sum(float(row["pnl_pips"]) for row in rows)
    wr = wins / n if n else 0.0
    ev = pnl / n if n else 0.0
    gross_profit = sum(float(row["pnl_pips"]) for row in rows if row["outcome"] == "WIN")
    gross_loss = sum(abs(float(row["pnl_pips"])) for row in rows if row["outcome"] == "LOSS")
    if wins and losses:
        avg_win = gross_profit / wins
        avg_loss = gross_loss / losses
        kelly = kelly_criterion(wr, avg_win, avg_loss)
        edge = float(kelly["edge"])
        full_kelly = float(kelly["full_kelly"])
    else:
        edge = 0.0
        full_kelly = 0.0
    return AggregateSnapshot(
        n=n,
        wins=wins,
        losses=losses,
        wr=wr,
        ev_pip=ev,
        pnl_pip=pnl,
        edge=edge,
        full_kelly=full_kelly,
    )


def compare_snapshot(actual: AggregateSnapshot) -> list[str]:
    problems = []
    if actual.n != EXPECTED_N:
        problems.append(f"N mismatch: expected {EXPECTED_N}, got {actual.n}")
    if abs(actual.wr - EXPECTED_WR) > WR_TOL:
        problems.append(
            f"WR mismatch: expected {EXPECTED_WR*100:.2f}%, got {actual.wr*100:.2f}%"
        )
    if abs(actual.ev_pip - EXPECTED_EV) > EV_TOL:
        problems.append(f"EV mismatch: expected {EXPECTED_EV:+.2f}, got {actual.ev_pip:+.2f}")
    if abs(actual.pnl_pip - EXPECTED_PNL) > PNL_TOL:
        problems.append(f"PnL mismatch: expected {EXPECTED_PNL:+.1f}, got {actual.pnl_pip:+.1f}")
    if abs(actual.edge - EXPECTED_EDGE) > EDGE_TOL:
        problems.append(f"Edge mismatch: expected {EXPECTED_EDGE:+.4f}, got {actual.edge:+.4f}")
    if abs(actual.full_kelly - EXPECTED_FULL_KELLY) > EDGE_TOL:
        problems.append(
            f"Kelly mismatch: expected {EXPECTED_FULL_KELLY:+.4f}, got {actual.full_kelly:+.4f}"
        )
    return problems


def fetch_live_rows(db_path: str, cutoff: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT trade_id, entry_type, instrument, direction, mode, entry_time,
                   outcome, pnl_pips, mtf_regime, oanda_trade_id
            FROM demo_trades
            WHERE outcome IN ('WIN', 'LOSS')
              AND entry_time >= ?
              AND instrument NOT IN (?, ?)
              AND oanda_trade_id IS NOT NULL
              AND oanda_trade_id != ''
            ORDER BY entry_time, trade_id
            """,
            (cutoff, *EXCLUDED_INSTRUMENTS),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for row in rows:
        out.append(
            {
                "trade_id": row["trade_id"],
                "entry_type": row["entry_type"] or "unknown",
                "pair": row["instrument"] or "unknown",
                "session": classify_session_utc(row["entry_time"]),
                "regime": normalize_regime_label(row["mtf_regime"]),
                "outcome": row["outcome"],
                "pnl_pips": float(row["pnl_pips"] or 0.0),
            }
        )
    return out


def weighted_bev(rows: list[dict]) -> float:
    counts = Counter(row["pair"] for row in rows)
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    return sum(PAIR_BEV_WR.get(pair, PAIR_BEV_WR["USD_JPY"]) * n for pair, n in counts.items()) / total


def summarize_axis(axis: AxisSpec, rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row[dim]) for dim in axis.dims)
        grouped[key].append(row)

    records = []
    for key, sub_rows in grouped.items():
        n = len(sub_rows)
        if n < MIN_TABLE_N:
            continue
        wins = sum(1 for row in sub_rows if row["outcome"] == "WIN")
        losses = n - wins
        pnl = sum(row["pnl_pips"] for row in sub_rows)
        gross_profit = sum(row["pnl_pips"] for row in sub_rows if row["pnl_pips"] > 0)
        gross_loss = sum(-row["pnl_pips"] for row in sub_rows if row["pnl_pips"] < 0)
        wr = wins / n
        ev = pnl / n
        bev = weighted_bev(sub_rows)
        wilson_lo = wilson_lower(wins, n)
        wilson_up = wilson_upper_at(wr, n)
        pf = (gross_profit / gross_loss) if gross_loss > 0 else math.inf
        records.append(
            {
                "axis": axis.name,
                "heading": axis.heading,
                "dims": dict(zip(axis.dims, key)),
                "trade_ids": sorted(row["trade_id"] for row in sub_rows),
                "n": n,
                "wins": wins,
                "losses": losses,
                "wr": wr,
                "wilson_lo_95": wilson_lo,
                "wilson_up_95": wilson_up,
                "ev_pip": ev,
                "pnl_pip": pnl,
                "pf": pf,
                "bev_wr": bev,
                "gap_to_bev_pp": (wr - bev) * 100.0,
                "flag": assign_flag(n=n, ev_pip=ev, wilson_upper=wilson_up, bev_wr=bev),
            }
        )

    records.sort(key=lambda row: (-abs(row["pnl_pip"]), tuple(row["dims"].values())))
    return records


def bonferroni_annotate(axis_rows: list[list[dict]]) -> tuple[int, list[dict]]:
    flat = [row for rows in axis_rows for row in rows]
    total_cells = len(flat)
    for row in flat:
        p_raw = binomial_one_sided_lower_p(row["wins"], row["n"], row["bev_wr"])
        row["p_value_lower_raw"] = p_raw
        row["p_value_lower_bonf"] = min(1.0, p_raw * max(1, total_cells))
    return total_cells, flat


def format_float(value: float, digits: int = 2, plus: bool = False) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:+.{digits}f}" if plus else f"{value:.{digits}f}"


def render_axis_table(axis: AxisSpec, rows: list[dict]) -> list[str]:
    labels = list(axis.dims)
    header = " | ".join(labels + [
        "N", "wins", "losses", "WR", "Wilson_lo_95", "Wilson_up_95",
        "EV_pip", "PnL_pip", "PF", "BEV_WR", "gap_to_BEV_pp", "flag",
    ])
    sep = " | ".join(["---"] * len(header.split(" | ")))
    lines = [f"## {axis.heading}", "", f"| {header} |", f"| {sep} |"]
    for row in rows:
        vals = [row["dims"][label] for label in labels]
        vals += [
            str(row["n"]),
            str(row["wins"]),
            str(row["losses"]),
            f"{row['wr']*100:.2f}%",
            f"{row['wilson_lo_95']*100:.2f}%",
            f"{row['wilson_up_95']*100:.2f}%",
            format_float(row["ev_pip"], plus=True),
            format_float(row["pnl_pip"], plus=True),
            format_float(row["pf"]),
            f"{row['bev_wr']*100:.2f}%",
            format_float(row["gap_to_bev_pp"], plus=True),
            row["flag"],
        ]
        lines.append(f"| {' | '.join(vals)} |")
    if len(rows) == 0:
        lines.append("| _none_ |")
    lines.append("")
    return lines


def render_audit(rows: list[dict], axis_rows: dict[str, list[dict]], total_cells: int) -> str:
    snapshot = build_snapshot(rows)
    demote_rows = [row for axis in axis_rows.values() for row in axis if row["flag"] == "DEMOTE"]
    watch_rows = [row for axis in axis_rows.values() for row in axis if row["flag"] == "WATCH"]
    ok_rows = [row for axis in axis_rows.values() for row in axis if row["flag"] == "OK"]
    top_destroyers = sorted(
        [row for axis in axis_rows.values() for row in axis],
        key=lambda row: (-abs(row["pnl_pip"]), row["axis"], tuple(row["dims"].values())),
    )[:5]
    excluded_trade_ids = {
        trade_id
        for row in demote_rows
        for trade_id in row["trade_ids"]
    }
    trimmed_rows = [row for row in rows if row["trade_id"] not in excluded_trade_ids]
    trimmed = build_snapshot(trimmed_rows)

    out = [
        "# Aggregate Kelly Decomposition Audit — 2026-05-03",
        "",
        f"Source DB: `demo_trades.db`",
        f"Cutoff: `entry_time >= {POST_CUTOFF}` | Scope: Live (`oanda_trade_id != ''`) | Excluded: XAU_USD, EUR_GBP",
        "",
        "## Aggregate sanity check",
        "",
        f"- N={snapshot.n}, wins={snapshot.wins}, losses={snapshot.losses}, WR={snapshot.wr*100:.2f}%",
        f"- EV={snapshot.ev_pip:+.2f} pip/trade, PnL={snapshot.pnl_pip:+.1f} pip, edge={snapshot.edge*100:+.2f}pp, Kelly={snapshot.full_kelly:+.4f}",
        f"- Counts: DEMOTE={len(demote_rows)}, WATCH={len(watch_rows)}, OK={len(ok_rows)} across {total_cells} qualified cells",
        "",
    ]
    for axis in AXES:
        out.extend(render_axis_table(axis, axis_rows[axis.name]))

    out += ["## Top 5 PnL-destroyer cells", ""]
    for idx, row in enumerate(top_destroyers, start=1):
        dims = ", ".join(f"{k}={v}" for k, v in row["dims"].items())
        out.append(
            f"{idx}. `{row['axis']}` {dims} | N={row['n']} | PnL={row['pnl_pip']:+.1f} | "
            f"EV={row['ev_pip']:+.2f} | WR={row['wr']*100:.2f}% | flag={row['flag']}"
        )
    out += ["", "## DEMOTE list", ""]
    if demote_rows:
        out += [
            "| axis | cell | N | WR | Wilson_up_95 | BEV_WR | p_lower_raw | p_lower_bonf |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in demote_rows:
            cell = ", ".join(f"{k}={v}" for k, v in row["dims"].items())
            out.append(
                f"| {row['axis']} | {cell} | {row['n']} | {row['wr']*100:.2f}% | "
                f"{row['wilson_up_95']*100:.2f}% | {row['bev_wr']*100:.2f}% | "
                f"{row['p_value_lower_raw']:.4g} | {row['p_value_lower_bonf']:.4g} |"
            )
    else:
        out.append("_No cells met the DEMOTE threshold._")
    out += [
        "",
        "## Sensitivity check",
        "",
        f"- Excluding all trades touched by DEMOTE cells removes {len(excluded_trade_ids)} trades.",
        f"- Hypothetical aggregate after DEMOTE exclusion: N={trimmed.n}, WR={trimmed.wr*100:.2f}%, EV={trimmed.ev_pip:+.2f}, PnL={trimmed.pnl_pip:+.1f}, edge={trimmed.edge*100:+.2f}pp, Kelly={trimmed.full_kelly:+.4f}",
        "- Kelly remains <= 0 unless the recomputed value above is strictly positive.",
        "",
        "## Limitations",
        "",
        "- Cells with N < 8 are WATCH-only even when they are economically negative.",
        "- Session and regime rows use trade-count-weighted BEV_WR because they mix multiple pairs.",
        "- DEMOTE cells overlap across axes; the sensitivity check excludes the union of affected trades.",
        "",
    ]
    return "\n".join(out)


def render_blocker(actual: AggregateSnapshot, problems: list[str], db_path: str) -> str:
    return "\n".join(
        [
            "# Aggregate Kelly Decomposition Audit — BLOCKED",
            "",
            "The required 2026-04-29 post-cutoff Live snapshot is not present in the local DB mirror, so a cell decomposition would be fabricated if generated from this workspace.",
            "",
            "## Local snapshot",
            "",
            f"- DB: `{db_path}`",
            f"- N={actual.n}, WR={actual.wr*100:.2f}%, EV={actual.ev_pip:+.2f}, PnL={actual.pnl_pip:+.1f}, edge={actual.edge*100:+.2f}pp, Kelly={actual.full_kelly:+.4f}",
            "",
            "## Mismatch vs required System State snapshot",
            "",
            *[f"- {problem}" for problem in problems],
            "",
            "## Required next evidence",
            "",
            "- A current Render-mirrored `demo_trades.db` whose post-cutoff Live slice matches the wiki snapshot (`N=286`, `WR=38.11%`, `EV=-0.80`, `PnL=-228.6`).",
            "- The mirror must include non-empty `oanda_trade_id` values; this workspace currently has zero such rows in `demo_trades.db`.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="demo_trades.db")
    parser.add_argument("--window", default="post-cutoff")
    parser.add_argument("--output", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-drift",
        action="store_true",
        help=(
            "Generate the full decomposition even when aggregate numbers drift "
            "from the System State baseline. The drift is documented at the top "
            "of the markdown rather than blocking the audit. Use when the KB "
            "snapshot is stale relative to a fresher Render mirror."
        ),
    )
    args = parser.parse_args()

    if args.window != "post-cutoff":
        print(f"unsupported --window={args.window!r}; only 'post-cutoff' is supported", file=sys.stderr)
        return 2

    rows = fetch_live_rows(args.db, POST_CUTOFF)
    snapshot = build_snapshot(rows)
    problems = compare_snapshot(snapshot)

    print(
        "aggregate_sanity_check "
        f"N={snapshot.n} WR={snapshot.wr*100:.2f}% EV={snapshot.ev_pip:+.2f} "
        f"PnL={snapshot.pnl_pip:+.1f} edge={snapshot.edge*100:+.2f}pp Kelly={snapshot.full_kelly:+.4f}"
    )
    if problems:
        for problem in problems:
            print(f"mismatch: {problem}", file=sys.stderr)
        if not args.allow_drift:
            if args.output and not args.dry_run:
                Path(args.output).write_text(render_blocker(snapshot, problems, args.db))
            return 1

    axis_rows = {axis.name: summarize_axis(axis, rows) for axis in AXES}
    total_cells, _ = bonferroni_annotate(list(axis_rows.values()))
    if args.dry_run:
        return 0

    if not args.output:
        print("--output is required unless --dry-run is used", file=sys.stderr)
        return 2
    body = render_audit(rows, axis_rows, total_cells)
    if problems and args.allow_drift:
        drift_note = "\n".join(
            [
                "> ⚠️ **Baseline drift acknowledged**: aggregate numbers diverge from the",
                "> 2026-04-29 wiki System State block. Drift documented below; the",
                "> decomposition uses the actual snapshot in the supplied `--db`.",
                "",
                "### Drift vs wiki/index.md System State (2026-04-29)",
                "",
                *[f"- {problem}" for problem in problems],
                "",
                "---",
                "",
            ]
        )
        body = drift_note + body
    Path(args.output).write_text(body)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
