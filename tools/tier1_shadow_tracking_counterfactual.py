#!/usr/bin/env python3
"""Counterfactual route-through for locked shadow_tracking variants."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from tier1_shadow_tracking_breakdown import (
    LOCK_CELLS,
    REFERENCE_CELLS,
    TIER1_CELLS,
    analyze,
    cell,
    load_rows,
    load_tier_master,
)

DEFAULT_TRADES = Path("/tmp/live-trades-tier1-rca.json")


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def pct(num: int, den: int) -> float:
    return num / den if den else 0.0


def route_base(audit_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, int]]:
    out: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {
        "sent": 0,
        "filled": 0,
        "blocked": 0,
        "shadow_tracking": 0,
    })
    sent_parent: dict[str, tuple[str, str]] = {}
    for row in audit_rows:
        status = str(row.get("bridge_status") or "").lower()
        tid = str(row.get("demo_trade_id") or "")
        if status == "sent" and tid:
            sent_parent[tid] = cell(row)
    for row in audit_rows:
        status = str(row.get("bridge_status") or "").lower()
        key = sent_parent.get(str(row.get("demo_trade_id") or ""), cell(row)) if status == "filled" else cell(row)
        if key not in LOCK_CELLS:
            continue
        if status == "sent" and as_bool(row.get("is_live")):
            out[key]["sent"] += 1
        elif status == "filled" and str(row.get("oanda_trade_id") or "").strip():
            out[key]["filled"] += 1
        elif status in {"blocked", "skipped"}:
            out[key]["blocked"] += 1
            if str(row.get("block_reason") or "") == "shadow_tracking":
                out[key]["shadow_tracking"] += 1
    return out


def decide_variants(breakdown: dict[str, Any]) -> tuple[str, dict[str, set[str]]]:
    lock_conditions = breakdown["conditions_lock_cells"]
    top_condition = next(iter(lock_conditions), "")
    elite_conditions = {"__ELITE_BYPASS__"}
    return top_condition, {
        "V1": {top_condition},
        "V2": {top_condition} | elite_conditions,
        "V3": elite_conditions,
    }


def is_elite_cell(key: tuple[str, str], tiers: dict[str, Any]) -> bool:
    return key[0] in tiers["elite_live"] or key in tiers["pair_promoted"]


def counterfactual(
    audit_rows: list[dict[str, Any]],
    breakdown: dict[str, Any],
    tiers: dict[str, Any],
    variants: list[str],
) -> dict[str, Any]:
    base = route_base(audit_rows)
    top_condition, variant_rules = decide_variants(breakdown)
    shadow_rows = breakdown["rows"]
    by_cell_condition: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in shadow_rows:
        key = (row["entry_type"], row["instrument"])
        if key in LOCK_CELLS:
            by_cell_condition[key][row["condition"]] += 1

    total_non_tier1_shadow_top = int(breakdown["conditions_non_tier1"].get(top_condition, 0))
    total_non_tier1_shadow = sum(int(v) for v in breakdown["conditions_non_tier1"].values())

    result: dict[str, Any] = {
        "pre_registered_variants": {
            "V1": "Top sub-condition single removal, broad relaxation",
            "V2": "Top sub-condition removal plus current tier-master ELITE_LIVE/PAIR_PROMOTED full bypass",
            "V3": "Current tier-master ELITE_LIVE/PAIR_PROMOTED full bypass only",
        },
        "top_subcondition": top_condition,
        "tier_master_elite_live": sorted(tiers["elite_live"]),
        "tier_master_pair_promoted": sorted([list(x) for x in tiers["pair_promoted"]]),
        "variants": {},
    }

    for variant in variants:
        rules = variant_rules[variant]
        rows_out = []
        tier1_filled = tier1_total = tier1_rescued = 0
        ref_rescued = ref_total = 0
        data_integrity_hits = 0
        double_exec_hits = 0
        for key in LOCK_CELLS:
            b = base[key]
            rescue = 0
            rescued_drift = 0
            for cond, n in by_cell_condition[key].items():
                if cond in rules:
                    rescue += n
                    if cond == "audit_state_drift_shadow_skip_not_final_shadow":
                        rescued_drift += n
                if "__ELITE_BYPASS__" in rules and is_elite_cell(key, tiers):
                    rescue += n
                    if cond == "audit_state_drift_shadow_skip_not_final_shadow":
                        rescued_drift += n
            rescue = min(rescue, b["shadow_tracking"])
            total = b["sent"] + b["blocked"]
            cf_filled = b["filled"] + rescue
            is_tier1 = key in TIER1_CELLS
            if is_tier1:
                tier1_filled += cf_filled
                tier1_total += total
                tier1_rescued += rescue
            else:
                ref_total += total
                ref_rescued += rescue
            data_integrity_hits += rescued_drift
            double_exec_hits += rescued_drift
            rows_out.append({
                "cell": f"{key[0]}|{key[1]}",
                "cohort": "tier1" if is_tier1 else "reference",
                "base_filled": b["filled"],
                "base_sent": b["sent"],
                "base_blocked": b["blocked"],
                "base_route_through": pct(b["filled"], total),
                "rescued_shadow_tracking": rescue,
                "counterfactual_filled": cf_filled,
                "counterfactual_route_through": pct(cf_filled, total),
            })

        tier23_regression_pct = pct(
            total_non_tier1_shadow_top if top_condition in rules else 0,
            total_non_tier1_shadow,
        )
        risk_reject = double_exec_hits > 0 or data_integrity_hits > 0
        route_rate = pct(tier1_filled, tier1_total)
        if risk_reject:
            verdict = "REJECT"
        elif route_rate >= 0.50 and tier23_regression_pct <= 0.05:
            verdict = "ACCEPT"
        elif route_rate < 0.20 or tier23_regression_pct > 0.10:
            verdict = "REJECT"
        else:
            verdict = "NEEDS_MORE_EVIDENCE"

        result["variants"][variant] = {
            "tier1_counterfactual_filled": tier1_filled,
            "tier1_route_total": tier1_total,
            "tier1_route_through": route_rate,
            "tier1_rescued": tier1_rescued,
            "reference_rescued": ref_rescued,
            "reference_route_total": ref_total,
            "tier2_3_regression_proxy": {
                "non_lock_top_subcondition_rows": total_non_tier1_shadow_top if top_condition in rules else 0,
                "non_lock_shadow_tracking_rows": total_non_tier1_shadow,
                "pct": tier23_regression_pct,
            },
            "double_execution_risk_hits": double_exec_hits,
            "data_integrity_violation_hits": data_integrity_hits,
            "verdict": verdict,
            "cells": rows_out,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    parser.add_argument("--trades", default=str(DEFAULT_TRADES))
    parser.add_argument("--variants", default="V1,V2,V3")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    audit_rows = load_rows(Path(args.audit))
    trade_rows = load_rows(Path(args.trades)) if Path(args.trades).exists() else []
    tiers = load_tier_master()
    breakdown = analyze(audit_rows, trade_rows, tiers)
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    result = counterfactual(audit_rows, breakdown, tiers, variants)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
