#!/usr/bin/env python3
"""Break down shadow_tracking audit rows into recoverable upstream causes.

This is a read-only forensic helper.  The production audit table stores only
``block_reason='shadow_tracking'`` for the final OANDA skip, so this script
joins the audit snapshot to the demo trade snapshot and classifies the upstream
cause from persisted routing columns plus the tier master.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRADES = Path("/tmp/live-trades-tier1-rca.json")
TIER_MASTER = ROOT / "knowledge-base/wiki/tier-master.json"
CUTOFF = datetime(2026, 4, 8, tzinfo=timezone.utc)
GATE_V93_CUTOFF = datetime(2026, 4, 28, tzinfo=timezone.utc)

TIER1_CELLS = [
    ("gbp_deep_pullback", "GBP_USD"),
    ("trendline_sweep", "GBP_USD"),
    ("trendline_sweep", "EUR_USD"),
    ("session_time_bias", "USD_JPY"),
    ("session_time_bias", "EUR_USD"),
    ("session_time_bias", "GBP_USD"),
]

REFERENCE_CELLS = [
    ("xs_momentum", "USD_JPY"),
    ("xs_momentum", "EUR_USD"),
    ("doji_breakout", "USD_JPY"),
    ("squeeze_release_momentum", "EUR_USD"),
]

LOCK_CELLS = TIER1_CELLS + REFERENCE_CELLS
OANDA_MODE_BLOCKED = {"daytrade_eur", "daytrade_1h_eur", "daytrade_eurgbp", "scalp_5m"}
SHIELD_EUR_DT_WHITELIST = {"htf_false_breakout"}


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    if " " in text and "T" not in text:
        text = text.replace(" ", "T")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    if isinstance(payload, dict):
        for key in ("audit", "rows", "trades"):
            if isinstance(payload.get(key), list):
                return [r for r in payload[key] if isinstance(r, dict)]
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    raise ValueError(f"{path} does not contain rows")


def load_tier_master(path: Path = TIER_MASTER) -> dict[str, Any]:
    data = json.loads(path.read_text())
    return {
        "elite_live": set(data.get("elite_live", [])),
        "force_demoted": set(data.get("force_demoted", [])),
        "scalp_sentinel": set(data.get("scalp_sentinel", [])),
        "universal_sentinel": set(data.get("universal_sentinel", [])),
        "pair_promoted": {tuple(x) for x in data.get("pair_promoted", [])},
        "pair_demoted": {tuple(x) for x in data.get("pair_demoted", [])},
        "generated_at": data.get("generated_at", ""),
    }


def cell(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("entry_type") or ""), str(row.get("instrument") or ""))


def period(row: dict[str, Any]) -> str:
    dt = parse_dt(row.get("timestamp") or row.get("entry_time") or row.get("created_at"))
    if dt is None:
        return "unknown"
    return "post_cutoff" if dt >= CUTOFF else "pre_cutoff"


def gate_epoch(row: dict[str, Any]) -> str:
    dt = parse_dt(row.get("timestamp") or row.get("entry_time") or row.get("created_at"))
    if dt is None:
        return "unknown"
    return "post_gate_chain_v9_3" if dt >= GATE_V93_CUTOFF else "pre_gate_chain_v9_3"


def classify_shadow(row: dict[str, Any], trade: dict[str, Any] | None, tiers: dict[str, Any]) -> str:
    if not trade:
        return "unjoined_shadow_tracking"

    entry, instrument = cell(row)
    pair = (entry, instrument)
    mode = str(trade.get("mode") or "")
    gate_action = str(trade.get("mtf_gate_action") or "")
    gate_group = str(trade.get("gate_group") or "")
    trade_shadow = int(trade.get("is_shadow") or 0)
    has_oid = bool(str(trade.get("oanda_trade_id") or "").strip())

    if has_oid or trade_shadow == 0:
        return "audit_state_drift_shadow_skip_not_final_shadow"
    if gate_action == "downgraded":
        return "mtf_conflict_downgrade"
    if mode in OANDA_MODE_BLOCKED and entry not in SHIELD_EUR_DT_WHITELIST:
        return f"post_gate_mode_blocked:{mode}"
    if pair in tiers["pair_demoted"]:
        return "pair_demoted_safety_net"
    if entry in tiers["force_demoted"]:
        return "force_demoted_safety_net"
    if entry in tiers["elite_live"] or pair in tiers["pair_promoted"]:
        return "persisted_shadow_unknown_for_promoted_cell"
    if gate_group == "":
        return "legacy_unattributed_shadow_tracking"
    return "phase0_tier_shadow_gate"


def analyze(audit_rows: list[dict[str, Any]], trade_rows: list[dict[str, Any]], tiers: dict[str, Any]) -> dict[str, Any]:
    trade_by_id = {str(r.get("trade_id") or ""): r for r in trade_rows}
    sent_parent: dict[str, tuple[str, str]] = {}
    sent_period: dict[str, str] = {}
    filled_parent_count = 0

    for row in audit_rows:
        status = str(row.get("bridge_status") or "").lower()
        tid = str(row.get("demo_trade_id") or "")
        if status == "sent" and tid:
            sent_parent[tid] = cell(row)
            sent_period[tid] = period(row)
        elif status == "filled" and tid and str(row.get("oanda_trade_id") or "").strip():
            filled_parent_count += 1

    rows: list[dict[str, Any]] = []
    counters = {
        "all_shadow_tracking": Counter(),
        "lock_shadow_tracking": Counter(),
        "tier1_shadow_tracking": Counter(),
        "reference_shadow_tracking": Counter(),
        "period": Counter(),
        "gate_epoch": Counter(),
        "cell_condition": defaultdict(Counter),
        "condition_cell": defaultdict(Counter),
        "non_tier1_condition": Counter(),
        "time_cluster": Counter(),
    }

    for row in audit_rows:
        status = str(row.get("bridge_status") or "").lower()
        if status != "skipped" or str(row.get("block_reason") or "") != "shadow_tracking":
            continue
        key = cell(row)
        trade = trade_by_id.get(str(row.get("demo_trade_id") or ""))
        cond = classify_shadow(row, trade, tiers)
        dt = parse_dt(row.get("timestamp") or row.get("created_at"))
        minute = dt.strftime("%Y-%m-%dT%H:%M") if dt else "unknown"
        record = {
            "demo_trade_id": row.get("demo_trade_id"),
            "timestamp": row.get("timestamp") or row.get("created_at"),
            "entry_type": key[0],
            "instrument": key[1],
            "condition": cond,
            "period": period(row),
            "gate_epoch": gate_epoch(row),
            "direction": row.get("direction"),
            "mode": trade.get("mode") if trade else "",
            "gate_group": trade.get("gate_group") if trade else "",
            "mtf_alignment": trade.get("mtf_alignment") if trade else "",
            "mtf_gate_action": trade.get("mtf_gate_action") if trade else "",
            "trade_is_shadow": trade.get("is_shadow") if trade else None,
            "trade_oanda_trade_id_present": bool(str((trade or {}).get("oanda_trade_id") or "").strip()),
        }
        rows.append(record)
        counters["all_shadow_tracking"][cond] += 1
        counters["period"][record["period"]] += 1
        counters["gate_epoch"][record["gate_epoch"]] += 1
        counters["time_cluster"][minute] += 1
        counters["cell_condition"][f"{key[0]}|{key[1]}"][cond] += 1
        counters["condition_cell"][cond][f"{key[0]}|{key[1]}"] += 1
        if key in LOCK_CELLS:
            counters["lock_shadow_tracking"][cond] += 1
        else:
            counters["non_tier1_condition"][cond] += 1
        if key in TIER1_CELLS:
            counters["tier1_shadow_tracking"][cond] += 1
        if key in REFERENCE_CELLS:
            counters["reference_shadow_tracking"][cond] += 1

    def dump_counter(counter: Counter) -> dict[str, int]:
        return dict(counter.most_common())

    def dump_nested(nested: defaultdict[str, Counter]) -> dict[str, dict[str, int]]:
        return {k: dump_counter(v) for k, v in sorted(nested.items())}

    clustered = {k: v for k, v in counters["time_cluster"].items() if v >= 2}
    return {
        "source_notes": {
            "audit_shadow_tracking_rows": len(rows),
            "joined_trade_rows": sum(1 for r in rows if r["trade_is_shadow"] is not None),
            "filled_parent_rows": filled_parent_count,
            "tier_master_generated_at": tiers["generated_at"],
            "tier1_spec_cell_count": len(TIER1_CELLS),
            "reference_cell_count": len(REFERENCE_CELLS),
        },
        "conditions_all": dump_counter(counters["all_shadow_tracking"]),
        "conditions_lock_cells": dump_counter(counters["lock_shadow_tracking"]),
        "conditions_tier1_cells": dump_counter(counters["tier1_shadow_tracking"]),
        "conditions_reference_cells": dump_counter(counters["reference_shadow_tracking"]),
        "conditions_non_tier1": dump_counter(counters["non_tier1_condition"]),
        "period_breakdown": dump_counter(counters["period"]),
        "gate_epoch_breakdown": dump_counter(counters["gate_epoch"]),
        "cell_condition_matrix": dump_nested(counters["cell_condition"]),
        "condition_cell_matrix": dump_nested(counters["condition_cell"]),
        "time_clusters_ge_2_per_minute": dict(sorted(clustered.items())),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    parser.add_argument("--trades", default=str(DEFAULT_TRADES))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    audit_rows = load_rows(Path(args.audit))
    trade_rows = load_rows(Path(args.trades)) if Path(args.trades).exists() else []
    result = analyze(audit_rows, trade_rows, load_tier_master())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
