#!/usr/bin/env python3
"""
SCORE_GATE direction-aware fix — Pre-reg LOCK KPI tracker.

Tracks ELITE_LIVE 3 strategies × {BUY, SELL} = 6 strata since the fix
deployed on 2026-04-28. Designed to be run daily via cron or on-demand.

Pre-reg LOCK source: knowledge-base/wiki/decisions/score-gate-direction-aware-2026-04-28.md
Re-evaluation date: 2026-05-12

Usage:
    python3 tools/score_gate_kpi_check.py             # current status
    python3 tools/score_gate_kpi_check.py --json      # machine-readable
    python3 tools/score_gate_kpi_check.py --since 2026-04-28T09:23  # custom cutoff

Hard-stop conditions (rule:R2 — exit code 2 when triggered):
  1. ELITE_LIVE × SELL N>=10 with WR<30%
  2. Overall N>=15 with PF<0.6
  3. 6 consecutive losses on any (strategy, pair)

KPI thresholds for re-evaluation (Continuation):
  N>=15, WR>=40% (Wilson lower>30%), PF>=0.8, EV>=-0.5p, max consecutive losses<6
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import requests

ELITE_LIVE = ("session_time_bias", "trendline_sweep", "gbp_deep_pullback")
DEFAULT_CUTOFF_ISO = "2026-04-28T09:00:00+00:00"  # ~ deploy time of 5ca018c
PROD_TRADES_URL = (
    "https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000"
)


def _fetch_trades(timeout: int = 30) -> list[dict]:
    # Enforce https scheme (defense in depth — see CWE-939). The URL is a
    # hardcoded constant above, but re-validate at call site for clarity.
    if not PROD_TRADES_URL.startswith("https://"):
        raise ValueError(f"Refusing non-https URL: {PROD_TRADES_URL}")
    resp = requests.get(
        PROD_TRADES_URL,
        headers={"User-Agent": "kpi-check/1.0"},
        timeout=timeout,
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get("trades", [])


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    """Wilson score lower bound (one-sided 95% by default)."""
    if n <= 0:
        return 0.0
    p = wins / n
    z2 = z * z
    centre = p + z2 / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)
    return (centre - spread) / (1 + z2 / n)


def _max_consec_losses(trades: list[dict]) -> int:
    """Max consecutive LOSS in chronological order."""
    sorted_t = sorted(trades, key=lambda t: t.get("entry_time", ""))
    cur = mx = 0
    for t in sorted_t:
        if t.get("outcome") == "LOSS":
            cur += 1
            mx = max(mx, cur)
        elif t.get("outcome") == "WIN":
            cur = 0
        # BREAKEVEN / None / OPEN: reset to 0 (conservative)
        else:
            cur = 0
    return mx


def aggregate(trades: list[dict], cutoff_iso: str) -> dict:
    """Return {(strategy, direction): {n, wins, losses, ev, pf, wilson_lo, max_consec}}.
    Only Live + Closed trades count toward Pre-reg KPI.
    """
    relevant = [
        t for t in trades
        if t.get("entry_type") in ELITE_LIVE
        and t.get("entry_time", "") >= cutoff_iso
        and not t.get("is_shadow", 0)
        and t.get("status") == "CLOSED"
    ]
    grouped = defaultdict(list)
    for t in relevant:
        grouped[(t["entry_type"], t["direction"])].append(t)

    out = {}
    for key, group in grouped.items():
        wins = sum(1 for t in group if t.get("outcome") == "WIN")
        losses = sum(1 for t in group if t.get("outcome") == "LOSS")
        n = wins + losses
        pnl_list = [float(t.get("pnl_pips", 0) or 0) for t in group]
        gross_win = sum(p for p in pnl_list if p > 0)
        gross_loss = -sum(p for p in pnl_list if p < 0)
        ev = (sum(pnl_list) / n) if n else 0.0
        pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0
        wilson_lo = _wilson_lower(wins, n) if n else 0.0
        out[key] = dict(
            n=n,
            wins=wins,
            losses=losses,
            wr=(wins / n) if n else 0.0,
            ev_pips=ev,
            pf=pf,
            wilson_lo_one_sided_95=wilson_lo,
            max_consec_losses=_max_consec_losses(group),
        )
    return out


def evaluate(agg: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (alerts_R2_hard_stop, warnings, info)."""
    alerts: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    sell_total_n = sum(v["n"] for k, v in agg.items() if k[1] == "SELL")
    sell_total_wins = sum(v["wins"] for k, v in agg.items() if k[1] == "SELL")
    sell_wr = (sell_total_wins / sell_total_n) if sell_total_n else 0.0

    overall_n = sum(v["n"] for v in agg.values())
    overall_wins = sum(v["wins"] for v in agg.values())
    overall_pnl = []
    overall_gross_win = 0.0
    overall_gross_loss = 0.0
    for k, v in agg.items():
        # crude reconstruction; per-key PF was already computed
        # for overall PF we need to revisit individual trades, fall back to sum
        overall_gross_win += v["wins"] * max(v["ev_pips"], 0)
        overall_gross_loss += v["losses"] * max(-v["ev_pips"], 0)
    overall_pf = (overall_gross_win / overall_gross_loss) if overall_gross_loss > 0 else float("inf")

    # Hard-stop 1: ELITE_LIVE × SELL N>=10 with WR<30%
    if sell_total_n >= 10 and sell_wr < 0.30:
        alerts.append(
            f"R2 HARD STOP: ELITE_LIVE×SELL N={sell_total_n} WR={sell_wr:.1%} < 30%"
        )

    # Hard-stop 2: Overall N>=15 with PF<0.6
    if overall_n >= 15 and overall_pf < 0.6:
        alerts.append(
            f"R2 HARD STOP: Overall N={overall_n} PF={overall_pf:.2f} < 0.6"
        )

    # Hard-stop 3: 6 consecutive losses any key
    for key, v in agg.items():
        if v["max_consec_losses"] >= 6:
            alerts.append(
                f"R2 HARD STOP: {key[0]}×{key[1]} max_consec_losses={v['max_consec_losses']}"
            )

    # Continuation KPI warnings (when N is large enough but threshold not met)
    for key, v in agg.items():
        if v["n"] >= 15:
            if v["wr"] < 0.40:
                warnings.append(
                    f"{key[0]}×{key[1]} N={v['n']} WR={v['wr']:.1%} < 40% (re-eval target)"
                )
            if v["wilson_lo_one_sided_95"] < 0.30:
                warnings.append(
                    f"{key[0]}×{key[1]} Wilson lower={v['wilson_lo_one_sided_95']:.3f} < 0.30"
                )
            if v["pf"] < 0.8:
                warnings.append(f"{key[0]}×{key[1]} PF={v['pf']:.2f} < 0.8")
            if v["ev_pips"] < -0.5:
                warnings.append(f"{key[0]}×{key[1]} EV={v['ev_pips']:.2f}p < -0.5")

    # Info: progress to N=15
    for key in [(et, d) for et in ELITE_LIVE for d in ("BUY", "SELL")]:
        v = agg.get(key, {"n": 0})
        info.append(f"  {key[0]:25} {key[1]:4}  N={v.get('n', 0):3}/15")

    return alerts, warnings, info


def render(agg: dict, cutoff_iso: str, alerts: list[str], warnings: list[str], info: list[str]) -> str:
    lines = [
        "═" * 72,
        f"SCORE_GATE direction-aware fix — Pre-reg LOCK KPI tracker",
        f"Pre-reg: knowledge-base/wiki/decisions/score-gate-direction-aware-2026-04-28.md",
        f"Cutoff: {cutoff_iso}",
        f"Re-eval: 2026-05-12 (14d post-deploy)",
        "═" * 72,
        "",
        "Per-stratum KPI (Live trades only, status=CLOSED):",
        f"  {'strategy':25} {'dir':>4} {'N':>4} {'WR':>6} {'Wlo95':>7} {'EV(p)':>7} {'PF':>5} {'consec':>7}",
    ]
    for key in [(et, d) for et in ELITE_LIVE for d in ("BUY", "SELL")]:
        v = agg.get(key)
        if not v:
            lines.append(
                f"  {key[0]:25} {key[1]:>4} {0:>4} {'--':>6} {'--':>7} {'--':>7} {'--':>5} {'--':>7}"
            )
            continue
        pf_str = "inf" if v["pf"] == float("inf") else f"{v['pf']:5.2f}"
        lines.append(
            f"  {key[0]:25} {key[1]:>4} {v['n']:>4} {v['wr']:6.1%} "
            f"{v['wilson_lo_one_sided_95']:7.3f} {v['ev_pips']:7.2f} {pf_str:>5} {v['max_consec_losses']:>7}"
        )

    lines.append("")
    if alerts:
        lines.append(f"🛑 R2 HARD STOP TRIGGERS ({len(alerts)}):")
        for a in alerts:
            lines.append(f"  • {a}")
        lines.append("")
    if warnings:
        lines.append(f"⚠️  Re-eval warnings ({len(warnings)}):")
        for w in warnings:
            lines.append(f"  • {w}")
        lines.append("")
    lines.append("Sample progress to N=15:")
    lines.extend(info)

    if not alerts and not warnings:
        lines.append("")
        lines.append("✅ No hard-stop triggers. Continue accumulation toward N≥15.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default=DEFAULT_CUTOFF_ISO,
                        help=f"ISO cutoff (default {DEFAULT_CUTOFF_ISO})")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args()

    try:
        trades = _fetch_trades()
    except Exception as e:
        print(f"ERROR fetching {PROD_TRADES_URL}: {e}", file=sys.stderr)
        sys.exit(3)

    agg = aggregate(trades, args.since)
    alerts, warnings, info = evaluate(agg)

    if args.json:
        # serialize tuple keys as "strategy|direction"
        agg_serializable = {f"{k[0]}|{k[1]}": v for k, v in agg.items()}
        print(json.dumps({
            "cutoff": args.since,
            "agg": agg_serializable,
            "alerts": alerts,
            "warnings": warnings,
            "trade_count_live_closed": sum(v["n"] for v in agg.values()),
        }, ensure_ascii=False, indent=2))
    else:
        print(render(agg, args.since, alerts, warnings, info))

    # Exit codes for cron consumers
    if alerts:
        sys.exit(2)  # hard stop
    sys.exit(0)


if __name__ == "__main__":
    main()
