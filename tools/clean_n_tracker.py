#!/usr/bin/env python3
"""Clean-N progress tracker — roadmap v2.2 M3 (clean N>=30 cells x3).

Aggregates production trades per strategy x pair into the three strict
buckets (memory: feedback_live_vs_shadow_strict_separation):
  TRUE_LIVE : is_shadow=0 AND oanda_trade_id != ''
  FLAG_DRIFT: is_shadow=0 AND oanda_trade_id == ''  (write-path bug legacy)
  SHADOW    : is_shadow=1

Outputs an M3 progress table (clean shadow N toward the N>=30 R1
re-evaluation gate + TRUE_LIVE N toward Live N>=30) and flags cells that
crossed the threshold since the caller last checked. Threshold crossings
are the trigger to draft an R1 verification task (12y BT + Bonferroni +
pre-reg) — this script only reports; it never promotes (rule discipline:
Cell-level stats alone must not promote).

Caveats printed with the table:
  - counts are raw rows post-cutoff (2026-04-08); TF-aware dedup is NOT
    re-applied here, so treat N as an upper bound and re-verify with the
    dedup-aware pipeline before any R1 kickoff.
  - XAU excluded.

Usage:
  python3 tools/clean_n_tracker.py [--api https://fx-ai-trader.onrender.com]
                                   [--min-n 20] [--threshold 30] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

import requests

DEFAULT_API = "https://fx-ai-trader.onrender.com"
CUTOFF = "2026-04-08"


def fetch_trades(api: str, limit: int = 100000) -> list[dict]:
    if not api.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise ValueError(f"unsupported API base (https required): {api!r}")
    resp = requests.get(f"{api}/api/demo/trades", params={"limit": limit},
                        timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("trades", [])


def bucket(trade: dict) -> str:
    if trade.get("is_shadow"):
        return "SHADOW"
    return "TRUE_LIVE" if trade.get("oanda_trade_id") else "FLAG_DRIFT"


def aggregate(trades: list[dict]) -> dict:
    cells: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"TRUE_LIVE": 0, "FLAG_DRIFT": 0, "SHADOW": 0}
    )
    for t in trades:
        inst = t.get("instrument", "") or ""
        if inst.startswith("XAU"):
            continue
        entry_time = t.get("entry_time", "") or ""
        if entry_time and entry_time[:10] < CUTOFF:
            continue
        key = (t.get("entry_type", "?") or "?", inst or "?")
        cells[key][bucket(t)] += 1
    return cells


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--min-n", type=int, default=20,
                        help="show cells with shadow or live N >= this")
    parser.add_argument("--threshold", type=int, default=30,
                        help="R1 re-evaluation gate (roadmap M3)")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    try:
        trades = fetch_trades(args.api)
    except Exception as exc:
        print(f"ERROR: trades fetch failed: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 2
    if not trades:
        # lesson: 空結果はバグ — 本番に post-cutoff トレードは必ず存在する
        print("ERROR: 0 trades returned — treat as parser/API bug, not as "
              "'no data' (lesson: 分析ツールは実データ検証必須)", file=sys.stderr)
        return 2

    cells = aggregate(trades)
    rows = [
        {
            "strategy": k[0], "pair": k[1],
            "true_live": v["TRUE_LIVE"], "flag_drift": v["FLAG_DRIFT"],
            "shadow": v["SHADOW"],
            "live_gate": v["TRUE_LIVE"] >= args.threshold,
            "shadow_gate": v["SHADOW"] >= args.threshold,
        }
        for k, v in cells.items()
        if max(v["TRUE_LIVE"], v["SHADOW"]) >= args.min_n
    ]
    rows.sort(key=lambda r: (-r["true_live"], -r["shadow"]))

    if args.as_json:
        print(json.dumps({"threshold": args.threshold, "cells": rows},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"# Clean-N tracker — post-cutoff {CUTOFF}, XAU除外, "
          f"gate N>={args.threshold} (M3)")
    print("# ⚠️ raw counts (dedup未適用=上限値)。R1着手前に dedup-aware 再計測必須")
    print(f"{'strategy':<32}{'pair':<10}{'LIVE':>6}{'DRIFT':>7}{'SHADOW':>8}  gate")
    for r in rows:
        gates = []
        if r["live_gate"]:
            gates.append("LIVE>=30")
        if r["shadow_gate"]:
            gates.append("SHADOW>=30")
        print(f"{r['strategy']:<32}{r['pair']:<10}{r['true_live']:>6}"
              f"{r['flag_drift']:>7}{r['shadow']:>8}  {'✅ ' + '+'.join(gates) if gates else ''}")
    n_live_gate = sum(1 for r in rows if r["live_gate"])
    print(f"\nM3 progress: TRUE_LIVE N>={args.threshold} cells = {n_live_gate} / 3 target")
    return 0


if __name__ == "__main__":
    sys.exit(main())
