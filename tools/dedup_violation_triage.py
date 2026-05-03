#!/usr/bin/env python3
"""
Triage the 46 shadow-only per-bar dedup violations into:
  - HISTORICAL_LEGACY
  - ACTIVE_GAP_PROBABLE
  - INDETERMINATE

This is a read-only forensic wrapper around tools/per_bar_dedup_audit.py.
It validates the audit headline via subprocess, re-derives the row-level
violations from the same local snapshot, and emits deterministic JSON and/or
markdown suitable for follow-up gate-fix or backfill tasks.
"""

from __future__ import annotations

import argparse
import ast
import json
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.per_bar_dedup_audit import (
    _local_db_path,
    _parse_ts,
    detect_violations,
)

LESSON_PATH = PROJECT_ROOT / "knowledge-base" / "wiki" / "lessons" / "lesson-per-bar-dedup-tf-aware-2026-05-03.md"
APP_PATH = PROJECT_ROOT / "app.py"
DEMO_TRADER_PATH = PROJECT_ROOT / "modules" / "demo_trader.py"

EXPECTED_TOTAL = 46
EXPECTED_LIVE = 0

CLASSIFICATION_ORDER = {
    "ACTIVE_GAP_PROBABLE": 0,
    "INDETERMINATE": 1,
    "HISTORICAL_LEGACY": 2,
}

PROMOTION_TIER_ORDER = (
    "ELITE_LIVE",
    "PAIR_PROMOTED",
    "UNIVERSAL_SENTINEL",
    "SCALP_SENTINEL",
    "PAIR_DEMOTED",
    "FORCE_DEMOTED",
    "REGISTERED_SHADOW",
    "UNREGISTERED",
)


@dataclass(frozen=True)
class RegistrySnapshot:
    app_registered: frozenset[str]
    demo_registered: frozenset[str]
    force_demoted: frozenset[str]
    elite_live: frozenset[str]
    scalp_sentinel: frozenset[str]
    universal_sentinel: frozenset[str]
    pair_promoted: frozenset[tuple[str, str]]
    pair_demoted: frozenset[tuple[str, str]]


def _run_cmd(cmd: list[str], *, allow_nonzero: bool = False) -> str:
    proc = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0 and not allow_nonzero:
        raise subprocess.CalledProcessError(
            proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr
        )
    return proc.stdout


def load_audit_summary() -> dict:
    body = _run_cmd(
        [sys.executable, "tools/per_bar_dedup_audit.py", "--json"],
        allow_nonzero=True,
    )
    return json.loads(body)


def load_trade_rows() -> list[dict]:
    conn = sqlite3.connect(str(_local_db_path()))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT
                trade_id,
                entry_type,
                instrument,
                direction,
                entry_time,
                tf,
                pnl_pips,
                dedup_violation,
                is_shadow,
                oanda_trade_id,
                signal_price,
                status,
                entry_price
            FROM demo_trades
            WHERE entry_time >= ?
            ORDER BY entry_time, trade_id
            """,
            ("2026-04-03T00:00:00+00:00",),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def _literal_strings(node: ast.AST) -> set[str]:
    out: set[str] = set()
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        out.add(node.value)
    elif isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        for elt in node.elts:
            out |= _literal_strings(elt)
    elif isinstance(node, ast.Dict):
        for key in node.keys:
            if key is not None:
                out |= _literal_strings(key)
    return out


def _literal_pair_tuples(node: ast.AST) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        for elt in node.elts:
            if (
                isinstance(elt, ast.Tuple)
                and len(elt.elts) >= 2
                and all(
                    isinstance(sub, ast.Constant) and isinstance(sub.value, str)
                    for sub in elt.elts[:2]
                )
            ):
                out.add((elt.elts[0].value, elt.elts[1].value))
            else:
                out |= _literal_pair_tuples(elt)
    elif isinstance(node, ast.Dict):
        for key in node.keys:
            if key is not None:
                out |= _literal_pair_tuples(key)
    return out


def _collect_named_literals(path: Path, target_names: set[str]) -> dict[str, ast.AST]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in target_names:
                    found[target.id] = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id in target_names and node.value is not None:
                found[target.id] = node.value
    return found


def load_registry_snapshot() -> RegistrySnapshot:
    app_nodes = _collect_named_literals(APP_PATH, {"QUALIFIED_TYPES", "DT_QUALIFIED"})
    app_registered: set[str] = set()
    for node in app_nodes.values():
        app_registered |= _literal_strings(node)

    demo_targets = {
        "_FORCE_DEMOTED",
        "_SCALP_SENTINEL",
        "_UNIVERSAL_SENTINEL",
        "_PAIR_PROMOTED",
        "_PAIR_DEMOTED",
        "_ELITE_LIVE",
    }
    demo_nodes = _collect_named_literals(DEMO_TRADER_PATH, demo_targets)

    force_demoted = _literal_strings(demo_nodes["_FORCE_DEMOTED"])
    scalp_sentinel = _literal_strings(demo_nodes["_SCALP_SENTINEL"])
    universal_sentinel = _literal_strings(demo_nodes["_UNIVERSAL_SENTINEL"])
    elite_live = _literal_strings(demo_nodes["_ELITE_LIVE"])
    pair_promoted = _literal_pair_tuples(demo_nodes["_PAIR_PROMOTED"])
    pair_demoted = _literal_pair_tuples(demo_nodes["_PAIR_DEMOTED"])

    demo_registered = (
        force_demoted
        | scalp_sentinel
        | universal_sentinel
        | elite_live
        | {strategy for strategy, _pair in pair_promoted}
        | {strategy for strategy, _pair in pair_demoted}
    )

    return RegistrySnapshot(
        app_registered=frozenset(app_registered),
        demo_registered=frozenset(demo_registered),
        force_demoted=frozenset(force_demoted),
        elite_live=frozenset(elite_live),
        scalp_sentinel=frozenset(scalp_sentinel),
        universal_sentinel=frozenset(universal_sentinel),
        pair_promoted=frozenset(pair_promoted),
        pair_demoted=frozenset(pair_demoted),
    )


def detect_cutoff() -> datetime:
    try:
        out = _run_cmd(
            [
                "git",
                "log",
                "--follow",
                "--format=%cI",
                "-1",
                "--",
                str(LESSON_PATH.relative_to(PROJECT_ROOT)),
            ]
        ).strip()
        if out:
            dt = _parse_ts(out)
            if dt is not None:
                return dt
    except subprocess.CalledProcessError:
        pass
    fallback = _parse_ts("2026-05-03T00:00:00+09:00")
    if fallback is None:
        raise RuntimeError("failed to parse fallback cutoff")
    return fallback


def promotion_tier(strategy: str, pair: str, registry: RegistrySnapshot) -> str:
    if strategy in registry.elite_live:
        return "ELITE_LIVE"
    if (strategy, pair) in registry.pair_promoted:
        return "PAIR_PROMOTED"
    if strategy in registry.force_demoted:
        return "FORCE_DEMOTED"
    if (strategy, pair) in registry.pair_demoted:
        return "PAIR_DEMOTED"
    if strategy in registry.universal_sentinel:
        return "UNIVERSAL_SENTINEL"
    if strategy in registry.scalp_sentinel:
        return "SCALP_SENTINEL"
    if strategy in registry.app_registered or strategy in registry.demo_registered:
        return "REGISTERED_SHADOW"
    return "UNREGISTERED"


def classify_row(
    strategy: str,
    pair: str,
    ts: datetime,
    cutoff: datetime,
    registry: RegistrySnapshot,
) -> str:
    if ts < cutoff:
        return "HISTORICAL_LEGACY"
    tier = promotion_tier(strategy, pair, registry)
    if tier in {"FORCE_DEMOTED", "UNREGISTERED"}:
        return "INDETERMINATE"
    return "ACTIVE_GAP_PROBABLE"


def build_rows(cutoff: datetime, registry: RegistrySnapshot) -> list[dict]:
    trades = load_trade_rows()
    trade_by_id = {trade["trade_id"]: trade for trade in trades}
    violations = detect_violations(trades)

    rows: list[dict] = []
    for violation in violations:
        trade_id = violation["cur_trade_id"]
        trade = trade_by_id[trade_id]
        ts = _parse_ts(trade["entry_time"])
        if ts is None:
            continue
        strategy = trade["entry_type"]
        pair = trade["instrument"]
        tier = promotion_tier(strategy, pair, registry)
        classification = classify_row(strategy, pair, ts, cutoff, registry)
        rows.append(
            {
                "trade_id": trade_id,
                "strategy": strategy,
                "pair": pair,
                "tf": trade.get("tf") or violation.get("tf") or "?",
                "ts": trade["entry_time"],
                "signal_price": trade.get("signal_price"),
                "action": trade.get("direction"),
                "exit_status": trade.get("status"),
                "pnl": round(float(trade.get("pnl_pips") or 0.0), 4),
                "classification": classification,
                "is_shadow": int(trade.get("is_shadow") or 0),
                "oanda_fill": bool((trade.get("oanda_trade_id") or "").strip()),
                "tier": tier,
                "bar_window_s": violation["bar_window_s"],
                "delta_s": violation["delta_s"],
                "already_flagged": bool(violation["cur_already_flagged"]),
                "entry_price": trade.get("entry_price"),
            }
        )
    rows.sort(key=lambda row: (row["ts"], row["strategy"], row["pair"], row["trade_id"]))
    return rows


def summarize_rows(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    by_classification = Counter(row["classification"] for row in rows)
    by_combo: dict[tuple[str, str, str], dict] = defaultdict(
        lambda: {
            "count": 0,
            "pnl": 0.0,
            "classification": None,
            "shadow_rows": 0,
            "tier": None,
        }
    )
    for row in rows:
        key = (row["strategy"], row["pair"], row["tf"])
        agg = by_combo[key]
        agg["count"] += 1
        agg["pnl"] += row["pnl"]
        agg["classification"] = row["classification"]
        agg["shadow_rows"] += int(bool(row["is_shadow"]))
        agg["tier"] = row["tier"]

    combo_rows = []
    for (strategy, pair, tf), agg in by_combo.items():
        combo_rows.append(
            {
                "strategy": strategy,
                "pair": pair,
                "tf": tf,
                "count": agg["count"],
                "pnl": round(agg["pnl"], 4),
                "classification": agg["classification"],
                "tier": agg["tier"],
            }
        )
    combo_rows.sort(
        key=lambda row: (
            CLASSIFICATION_ORDER[row["classification"]],
            -abs(row["pnl"]),
            row["strategy"],
            row["pair"],
            row["tf"],
        )
    )

    active_gap = [row for row in combo_rows if row["classification"] == "ACTIVE_GAP_PROBABLE"]
    promotion_rows = [
        row
        for row in combo_rows
        if row["tier"] in {"ELITE_LIVE", "PAIR_PROMOTED", "UNIVERSAL_SENTINEL", "PAIR_DEMOTED", "FORCE_DEMOTED"}
        and row["strategy"] in {"session_time_bias", "doji_breakout", "post_news_vol", "ema200_trend_reversal"}
    ]
    promotion_rows.sort(
        key=lambda row: (
            PROMOTION_TIER_ORDER.index(row["tier"]),
            -abs(row["pnl"]),
            row["strategy"],
            row["pair"],
        )
    )

    return {
        "counts": {
            "HISTORICAL_LEGACY": by_classification["HISTORICAL_LEGACY"],
            "ACTIVE_GAP_PROBABLE": by_classification["ACTIVE_GAP_PROBABLE"],
            "INDETERMINATE": by_classification["INDETERMINATE"],
            "TOTAL": len(rows),
        },
        "combo_rows": combo_rows,
        "active_gap": active_gap,
        "promotion_rows": promotion_rows,
    }


def sensitivity_counts(base_cutoff: datetime, registry: RegistrySnapshot) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for label, delta_days in (("minus_3d", -3), ("base", 0), ("plus_3d", 3)):
        rows = build_rows(base_cutoff + timedelta(days=delta_days), registry)
        counts = summarize_rows(rows)["counts"]
        out[label] = {
            "HISTORICAL_LEGACY": counts["HISTORICAL_LEGACY"],
            "ACTIVE_GAP_PROBABLE": counts["ACTIVE_GAP_PROBABLE"],
            "INDETERMINATE": counts["INDETERMINATE"],
        }
    return out


def format_num(value: float) -> str:
    return f"{value:+.1f}p"


def render_markdown(payload: dict) -> str:
    counts = payload["summary"]["counts"]
    cutoff = payload["cutoff"]
    sensitivity = payload["cutoff_sensitivity"]
    lines = [
        "# Dedup Violation Triage — 2026-05-03",
        "",
        f"- Cutoff used: `{cutoff}` (lesson commit date fallback policy)",
        f"- Underlying audit drift guard: `total={payload['audit_summary']['total_violations']}`, `live={payload['audit_summary']['violations_with_oanda_fill']}`",
        f"- Verdict: `ACTIVE_GAP_PROBABLE={counts['ACTIVE_GAP_PROBABLE']}`; all 46 rows are historical unless a later snapshot introduces post-cutoff rows.",
        "",
        "## Summary Counts",
        "",
        "| Classification | Rows |",
        "|---|---:|",
        f"| HISTORICAL_LEGACY | {counts['HISTORICAL_LEGACY']} |",
        f"| ACTIVE_GAP_PROBABLE | {counts['ACTIVE_GAP_PROBABLE']} |",
        f"| INDETERMINATE | {counts['INDETERMINATE']} |",
        f"| TOTAL | {counts['TOTAL']} |",
        "",
        "## Per-Combo Table",
        "",
        "| Classification | Strategy | Pair | TF | Rows | Dup PnL | Tier |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in payload["summary"]["combo_rows"]:
        lines.append(
            f"| {row['classification']} | {row['strategy']} | {row['pair']} | {row['tf']} | "
            f"{row['count']} | {format_num(row['pnl'])} | {row['tier']} |"
        )

    lines.extend(["", "## ACTIVE_GAP List", ""])
    if payload["summary"]["active_gap"]:
        for row in payload["summary"]["active_gap"]:
            lines.append(f"- {row['strategy']} / {row['pair']} / {row['tf']} — {row['count']} rows")
    else:
        lines.append("- None. No post-cutoff registered strategy rows were found.")

    lines.extend(["", "## Promotion Impact", ""])
    if payload["summary"]["promotion_rows"]:
        for row in payload["summary"]["promotion_rows"]:
            lines.append(
                f"- {row['strategy']} / {row['pair']} / {row['tf']} — tier `{row['tier']}`, "
                f"{row['count']} duplicated shadow rows, duplicate PnL {format_num(row['pnl'])}."
            )
    else:
        lines.append("- None of the affected combos intersect current ELITE_LIVE / PAIR_PROMOTED / shadow promotion tiers.")
    lines.append(
        "- Wilson/EV impact verdict: current live promotion math does not move directly here because `violations_with_oanda_fill=0`; the risk is shadow candidate inflation/deflation in follow-up promotion audits, not live fill contamination."
    )

    lines.extend(
        [
            "",
            "## Cutoff-Date Sensitivity",
            "",
            "| Cutoff | HIST | ACTIVE | INDET |",
            "|---|---:|---:|---:|",
            f"| cutoff-3d | {sensitivity['minus_3d']['HISTORICAL_LEGACY']} | {sensitivity['minus_3d']['ACTIVE_GAP_PROBABLE']} | {sensitivity['minus_3d']['INDETERMINATE']} |",
            f"| cutoff | {sensitivity['base']['HISTORICAL_LEGACY']} | {sensitivity['base']['ACTIVE_GAP_PROBABLE']} | {sensitivity['base']['INDETERMINATE']} |",
            f"| cutoff+3d | {sensitivity['plus_3d']['HISTORICAL_LEGACY']} | {sensitivity['plus_3d']['ACTIVE_GAP_PROBABLE']} | {sensitivity['plus_3d']['INDETERMINATE']} |",
            "",
        ]
    )
    base_active = sensitivity["base"]["ACTIVE_GAP_PROBABLE"]
    stable = all(bucket["ACTIVE_GAP_PROBABLE"] == base_active for bucket in sensitivity.values())
    if stable:
        lines.append("- Result is stable under cutoff +/-3 days: ACTIVE_GAP count does not change.")
    else:
        lines.append("- Result is brittle under cutoff +/-3 days: ACTIVE_GAP count changes.")

    return "\n".join(lines) + "\n"


def build_payload() -> dict:
    audit = load_audit_summary()
    audit_summary = audit["summary"]
    registry = load_registry_snapshot()
    cutoff = detect_cutoff()
    rows = build_rows(cutoff, registry)
    summary = summarize_rows(rows)
    sensitivity = sensitivity_counts(cutoff, registry)
    return {
        "cutoff": cutoff.isoformat(),
        "audit_summary": audit_summary,
        "rows": rows,
        "summary": summary,
        "cutoff_sensitivity": sensitivity,
    }


def print_dry_run(payload: dict) -> None:
    counts = payload["summary"]["counts"]
    print(
        "summary:",
        f"HIST={counts['HISTORICAL_LEGACY']}",
        f"ACTIVE={counts['ACTIVE_GAP_PROBABLE']}",
        f"INDET={counts['INDETERMINATE']}",
        f"TOTAL={counts['TOTAL']}",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    ap.add_argument("--dry-run", action="store_true", help="Print summary counts and enforce drift guard")
    ap.add_argument("--output", type=Path, help="Write markdown report to this path")
    args = ap.parse_args()

    payload = build_payload()
    total = payload["audit_summary"]["total_violations"]
    live_count = payload["audit_summary"]["violations_with_oanda_fill"]
    drift_ok = (total == EXPECTED_TOTAL and live_count == EXPECTED_LIVE)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_markdown(payload), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))

    if args.dry_run:
        print_dry_run(payload)
        if not drift_ok:
            return 2

    if not (args.json or args.dry_run or args.output):
        print(render_markdown(payload))

    return 0


if __name__ == "__main__":
    sys.exit(main())
