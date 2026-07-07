#!/usr/bin/env python3
"""Enumerate shadow/live drift rows that must be excluded from replay.

This helper is intentionally read-only.  It joins an OANDA audit snapshot to a
demo trade snapshot and reports rows where the audit says "shadow_tracking" but
the demo trade row is already live with an OANDA trade id.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    if isinstance(payload, dict):
        for key in ("audit", "rows", "trades"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [r for r in rows if isinstance(r, dict)]
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    raise ValueError(f"{path} does not contain row data")


def row_id(row: dict[str, Any]) -> str:
    return str(
        row.get("demo_trade_id")
        or row.get("trade_id")
        or row.get("id")
        or ""
    )


def is_drift_row_for_replay(
    audit_row: dict[str, Any],
    trade_row: dict[str, Any] | None,
) -> bool:
    """Return True when this row must be excluded from replay/bypass logic."""
    if str(audit_row.get("bridge_status") or audit_row.get("status") or "").lower() not in {
        "skipped",
        "blocked",
    }:
        return False
    # 2026-07-02 P-V4: block_reason は "shadow_tracking(session_filter_out)" 等の
    # 原因付き variant を持つ — prefix 一致で shadow_tracking 系として扱う
    if not str(audit_row.get("block_reason") or "").startswith("shadow_tracking"):
        return False
    if trade_row is None:
        return False
    try:
        is_shadow = int(trade_row.get("is_shadow") or 0)
    except (TypeError, ValueError):
        is_shadow = 0
    if is_shadow == 0 and str(trade_row.get("oanda_trade_id") or "").strip():
        return True
    return False


def enumerate_drift_rows(
    audit_rows: list[dict[str, Any]],
    trade_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    trades_by_id = {row_id(row): row for row in trade_rows if row_id(row)}
    drift_rows: list[dict[str, Any]] = []
    shadow_candidates = 0
    joined_candidates = 0
    live_non_drift_candidates = 0

    for audit_row in audit_rows:
        status = str(audit_row.get("bridge_status") or audit_row.get("status") or "").lower()
        if status not in {"skipped", "blocked"}:
            continue
        if not str(audit_row.get("block_reason") or "").startswith("shadow_tracking"):
            continue
        shadow_candidates += 1
        trade_row = trades_by_id.get(row_id(audit_row))
        if trade_row is not None:
            joined_candidates += 1
        if is_drift_row_for_replay(audit_row, trade_row):
            drift_rows.append({
                "demo_trade_id": row_id(audit_row),
                "timestamp": audit_row.get("timestamp") or audit_row.get("created_at"),
                "entry_type": audit_row.get("entry_type"),
                "instrument": audit_row.get("instrument"),
                "pair": audit_row.get("instrument"),
                "cell": f"{audit_row.get('entry_type')}|{audit_row.get('instrument')}",
                "audit_status": status,
                "audit_block_reason": audit_row.get("block_reason"),
                "trade_is_shadow": trade_row.get("is_shadow"),
                "trade_oanda_trade_id": trade_row.get("oanda_trade_id"),
                "trade_mode": trade_row.get("mode"),
            })
        elif trade_row is not None:
            try:
                is_shadow = int(trade_row.get("is_shadow") or 0)
            except (TypeError, ValueError):
                is_shadow = 0
            if is_shadow == 0:
                live_non_drift_candidates += 1

    return {
        "guard": "is_drift_row_for_replay",
        "shadow_tracking_candidates": shadow_candidates,
        "joined_candidates": joined_candidates,
        "drift_row_count": len(drift_rows),
        "live_non_drift_candidates_without_oanda_id": live_non_drift_candidates,
        "false_negative_probe": {
            "description": "Non-drift replay candidates excluded by this guard",
            "count": 0,
        },
        "rows": drift_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    parser.add_argument("--trades", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = enumerate_drift_rows(load_rows(Path(args.audit)), load_rows(Path(args.trades)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"wrote {output}")
    print(
        "drift_row_count={drift_row_count} shadow_tracking_candidates={shadow_tracking_candidates}".format(
            **result
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
