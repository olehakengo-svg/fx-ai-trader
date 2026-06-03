#!/usr/bin/env python3
"""MFE Break-Even Lock A/B monitor.

Post-hoc analysis tool for the shadow BE-lock A/B test (deployed 2026-06-03).
Groups trades into A (baseline) and B (BE-locked) via the SAME deterministic
hash used in `modules.demo_trader._mfe_be_lock_group`, then reports per-group
WR / EV / PnL / PF / N + welch t-test for mean PnL difference.

Usage:
    # Pull live shadow trades from the Render API and analyze
    python3 tools/be_lock_ab_monitor.py \\
        --api https://fx-ai-trader.onrender.com \\
        --ab-fraction 0.5 \\
        --since 2026-06-03

    # Analyze a local JSON dump (from /api/demo/trades)
    python3 tools/be_lock_ab_monitor.py --json /tmp/shadow_trades_all.json \\
        --ab-fraction 0.5 --since 2026-06-03

Discriminator: the A/B group is determined by the SAME hash function
(`zlib.crc32(trade_id) % 1000 < ab_fraction*1000`) so the monitor produces
correct attribution as long as `--ab-fraction` matches the env on Render.

Notes:
    * Only inspects trades with `entry_time >= --since` so we exclude the
      pre-deploy history.
    * Skips XAU trades (per project policy).
    * Reports both raw and Welch t-test for mean PnL difference (B - A).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import zlib
from collections import defaultdict
from typing import Iterable

import requests  # noqa: E402


def be_lock_group(trade_id: str, ab_fraction: float) -> str:
    """Mirror of modules.demo_trader._mfe_be_lock_group."""
    if ab_fraction <= 0:
        return "A"
    if ab_fraction >= 1:
        return "B"
    h = zlib.crc32((trade_id or "").encode("utf-8")) & 0xFFFFFFFF
    return "B" if (h % 1000) < int(ab_fraction * 1000) else "A"


def fetch_trades(api: str, limit: int = 20000) -> list[dict]:
    # Reject non-http(s) schemes for defense-in-depth (also enforced by
    # `requests` which doesn't honor file://).
    from urllib.parse import urlparse
    parsed = urlparse(api)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"--api must be http(s); got scheme={parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError(f"--api missing host: {api!r}")
    url = f"{api.rstrip('/')}/api/demo/trades"
    resp = requests.get(
        url,
        params={"limit": limit, "status": "closed", "shadow": 1},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("trades", [])


def load_trades(path: str) -> list[dict]:
    with open(path) as f:
        d = json.load(f)
    if isinstance(d, dict) and "trades" in d:
        return d["trades"]
    return d


def _stats(pnls: list[float]) -> dict:
    n = len(pnls)
    if n == 0:
        return {"n": 0, "mean": 0.0, "wr": 0.0, "sum": 0.0, "pf": 0.0, "std": 0.0}
    mean = sum(pnls) / n
    wins = sum(1 for x in pnls if x > 0)
    g = sum(x for x in pnls if x > 0)
    l = -sum(x for x in pnls if x < 0)
    pf = (g / l) if l > 0 else float("inf") if g > 0 else 0.0
    var = sum((x - mean) ** 2 for x in pnls) / max(n - 1, 1)
    std = math.sqrt(var)
    return {"n": n, "mean": mean, "wr": wins / n, "sum": sum(pnls), "pf": pf, "std": std}


def welch_t_p(mean_a: float, std_a: float, n_a: int,
              mean_b: float, std_b: float, n_b: int) -> tuple[float, float]:
    """Two-sample Welch t-test (B - A) → (t-stat, two-sided p)."""
    if n_a < 2 or n_b < 2 or std_a <= 0 or std_b <= 0:
        return (0.0, 1.0)
    se = math.sqrt(std_a ** 2 / n_a + std_b ** 2 / n_b)
    if se <= 0:
        return (0.0, 1.0)
    t = (mean_b - mean_a) / se
    # Two-sided p via normal approximation (large samples; conservative for small)
    p = math.erfc(abs(t) / math.sqrt(2))
    return (t, p)


def _filter(trades: Iterable[dict], since: str | None) -> list[dict]:
    out = []
    for t in trades:
        if not t.get("is_shadow"):
            continue
        if t.get("instrument") == "XAU_USD":
            continue
        if t.get("pnl_pips") is None:
            continue
        if since and (t.get("entry_time") or "") < since:
            continue
        out.append(t)
    return out


def report(trades: list[dict], ab_fraction: float) -> int:
    groups: dict[str, list[float]] = {"A": [], "B": []}
    by_cell: dict[tuple, dict[str, list[float]]] = defaultdict(lambda: {"A": [], "B": []})
    be_lock_eligible_count = 0

    # Import here so the script also runs against a stale checkout
    try:
        from modules.demo_trader import _mfe_be_lock_trigger_for, MFE_BE_LOCK_DEFAULT_TRIGGER_PIPS
    except Exception:
        _mfe_be_lock_trigger_for = None
        MFE_BE_LOCK_DEFAULT_TRIGGER_PIPS = 2.0  # noqa: N806

    for t in trades:
        g = be_lock_group(t["trade_id"], ab_fraction)
        pnl = float(t["pnl_pips"])
        groups[g].append(pnl)

        # Per-strategy: count only strategies where BE-lock would actually fire
        et = t.get("entry_type") or "?"
        if _mfe_be_lock_trigger_for is not None:
            trig = _mfe_be_lock_trigger_for(et, MFE_BE_LOCK_DEFAULT_TRIGGER_PIPS)
            if trig > 0 and g == "B":
                be_lock_eligible_count += 1

        cell = (et, t.get("instrument") or "?", t.get("direction") or "?")
        by_cell[cell][g].append(pnl)

    a_stats = _stats(groups["A"])
    b_stats = _stats(groups["B"])
    t, p = welch_t_p(
        a_stats["mean"], a_stats["std"], a_stats["n"],
        b_stats["mean"], b_stats["std"], b_stats["n"],
    )

    print("=" * 90)
    print(f"MFE BE-Lock A/B Monitor — ab_fraction={ab_fraction} | N_total={len(trades)}")
    print("=" * 90)
    print(f"{'group':<8} {'N':>6} {'mean':>7} {'WR%':>6} {'sumP':>9} {'PF':>6} {'std':>6}")
    print(f"{'A':<8} {a_stats['n']:>6} {a_stats['mean']:>7.2f} {a_stats['wr']*100:>6.1f}"
          f" {a_stats['sum']:>9.0f} {a_stats['pf']:>6.3f} {a_stats['std']:>6.2f}")
    print(f"{'B':<8} {b_stats['n']:>6} {b_stats['mean']:>7.2f} {b_stats['wr']*100:>6.1f}"
          f" {b_stats['sum']:>9.0f} {b_stats['pf']:>6.3f} {b_stats['std']:>6.2f}")
    print()
    print(f"ΔEV (B - A): {b_stats['mean'] - a_stats['mean']:+.3f} pips/trade")
    print(f"Welch t = {t:.3f}, two-sided p = {p:.4f}")
    if a_stats["n"] >= 100 and b_stats["n"] >= 100 and p < 0.05:
        verdict = "STAT SIG" if (b_stats["mean"] > a_stats["mean"]) else "STAT SIG (B WORSE!)"
    else:
        verdict = "INCONCLUSIVE (N too low or p >= 0.05)"
    print(f"Verdict: {verdict}")

    # Per-cell top movers
    print()
    print("Top 10 cells by |ΔEV (B-A)| (require N_A >= 10 and N_B >= 10):")
    rows = []
    for cell, gs in by_cell.items():
        if len(gs["A"]) < 10 or len(gs["B"]) < 10:
            continue
        sa = _stats(gs["A"])
        sb = _stats(gs["B"])
        rows.append((cell, sa, sb, sb["mean"] - sa["mean"]))
    rows.sort(key=lambda r: -abs(r[3]))
    print(f"  {'entry_type':<32} {'pair':<9} {'dir':<5} "
          f"{'Na':>4} {'Nb':>4} {'mean_A':>7} {'mean_B':>7} {'Δ':>7}")
    for cell, sa, sb, d in rows[:10]:
        et, inst, dirn = cell
        print(f"  {et[:32]:<32} {inst:<9} {dirn:<5} "
              f"{sa['n']:>4} {sb['n']:>4} {sa['mean']:>7.2f} {sb['mean']:>7.2f} {d:>+7.2f}")

    return 0 if a_stats["n"] > 0 and b_stats["n"] > 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", help="Render API base URL")
    ap.add_argument("--json", help="Local JSON file (alternative to --api)")
    ap.add_argument("--ab-fraction", type=float, default=0.5,
                    help="A/B split fraction (must match SHADOW_BE_LOCK_AB_FRACTION env)")
    ap.add_argument("--since", help="ISO datetime — only count trades after this")
    ap.add_argument("--limit", type=int, default=20000)
    args = ap.parse_args()

    if not args.api and not args.json:
        ap.error("provide --api or --json")

    trades = fetch_trades(args.api, args.limit) if args.api else load_trades(args.json)
    print(f"[load] {len(trades)} raw trades")
    trades = _filter(trades, args.since)
    print(f"[filter] {len(trades)} shadow non-XAU trades after {args.since or '(any time)'}")
    return report(trades, args.ab_fraction)


if __name__ == "__main__":
    sys.exit(main())
