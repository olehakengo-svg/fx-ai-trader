"""Cell-by-Cell Edge Audit (Q1', 2026-04-27)

Identify promotion-eligible cells from demo_trades.db.

Cell key: (entry_type, session, spread_quartile, mode)

For each cell with N >= MIN_N, compute:
  - N, WR, Wilson 95% lower bound
  - EV (mean pnl_pips), PF (gross profit / gross loss)
  - p-value (binomial test vs WR=50%) + Bonferroni correction

Output:
  - JSON to raw/audits/cell_edge_audit_<date>.json
  - Markdown to raw/audits/cell_edge_audit_<date>.md (sorted by Wilson lower)

Promotion candidates (auto-flagged):
  Wilson lower > 0.50 AND N >= MIN_N AND Bonferroni-adjusted p < 0.05

Usage:
  python3 tools/cell_edge_audit.py [--db demo_trades.db] [--include-shadow]
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# Wave 2 / U18 imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.strategy_category import (  # noqa: E402
    compute_spread_quartile,
    _normalize_session,
)


# ─── Configuration ──────────────────────────────────────────────────────
MIN_N: int = 20  # cell minimum N (相対緩めに、Bonferroni で誤検出を抑える)
WILSON_Z: float = 1.96  # 95% CI
PROMOTION_WILSON_LOWER: float = 0.50
PROMOTION_BONFERRONI_ALPHA: float = 0.05


# ─── Statistics helpers ─────────────────────────────────────────────────
def wilson_lower(wins: int, n: int, z: float = WILSON_Z) -> float:
    """Wilson score interval lower bound for proportion."""
    if n == 0:
        return 0.0
    p_hat = wins / n
    denom = 1 + z * z / n
    centre = p_hat + z * z / (2 * n)
    spread = z * math.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


def wilson_upper(wins: int, n: int, z: float = WILSON_Z) -> float:
    if n == 0:
        return 0.0
    p_hat = wins / n
    denom = 1 + z * z / n
    centre = p_hat + z * z / (2 * n)
    spread = z * math.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n))
    return min(1.0, (centre + spread) / denom)


def binomial_two_sided_pvalue(wins: int, n: int, p0: float = 0.5) -> float:
    """Two-sided binomial test p-value vs null p0."""
    if n == 0:
        return 1.0
    # Use normal approximation (n >= 20 typically)
    mean = n * p0
    var = n * p0 * (1 - p0)
    if var <= 0:
        return 1.0
    z = (wins - mean) / math.sqrt(var)
    # Two-sided p-value via standard normal CDF
    p = 2 * (1 - _phi(abs(z)))
    return max(0.0, min(1.0, p))


def _phi(z: float) -> float:
    """Standard normal CDF (Abramowitz & Stegun 26.2.17 approximation)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


# ─── Session derivation ─────────────────────────────────────────────────
def derive_session_from_utc(entry_time_iso: str) -> str:
    """Map entry_time UTC hour to session label.

    Coarse mapping (overlaps with friction_model_v2 / strategy_category):
      0-7   UTC: Tokyo
      7-12  UTC: London
      12-16 UTC: overlap_LN
      16-21 UTC: NY
      21-24 UTC: Sydney
    """
    if not entry_time_iso:
        return "default"
    try:
        ts = datetime.fromisoformat(entry_time_iso.replace("Z", "+00:00"))
        h = ts.astimezone(timezone.utc).hour
    except Exception:
        return "default"
    if h < 7:
        return "Tokyo"
    if h < 12:
        return "London"
    if h < 16:
        return "overlap_LN"
    if h < 21:
        return "NY"
    return "Sydney"


def normalize_mode(mode: str) -> str:
    if not mode:
        return "Unknown"
    m = mode.lower()
    if "scalp" in m:
        return "Scalp"
    if "swing" in m:
        return "Swing"
    if "daytrade" in m:
        return "DT"
    return mode


# ─── Core audit ─────────────────────────────────────────────────────────
def fetch_trades(db_path: str, include_shadow: bool) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Static SQL — no string formatting (semgrep B608 / CWE-89 safe).
    if include_shadow:
        rows = conn.execute("""
            SELECT trade_id, entry_type, mode, instrument, tf,
                   entry_time, entry_price, sl, spread_at_entry,
                   outcome, pnl_pips, is_shadow
            FROM demo_trades
            WHERE outcome IN ('WIN','LOSS')
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT trade_id, entry_type, mode, instrument, tf,
                   entry_time, entry_price, sl, spread_at_entry,
                   outcome, pnl_pips, is_shadow
            FROM demo_trades
            WHERE outcome IN ('WIN','LOSS') AND is_shadow = 0
        """).fetchall()
    conn.close()
    return rows


def cell_key(row: sqlite3.Row) -> tuple[str, str, str, str]:
    et = row["entry_type"] or "unknown"
    sess_raw = derive_session_from_utc(row["entry_time"])
    sess = _normalize_session(sess_raw)
    spread = row["spread_at_entry"] if row["spread_at_entry"] is not None else 0.0
    pair = row["instrument"] or "USD_JPY"
    quartile = compute_spread_quartile(spread, pair) if spread > 0 else "q0"
    mode = normalize_mode(row["mode"])
    return (et, sess, quartile, mode)


def aggregate_cells(rows: Iterable[sqlite3.Row]) -> dict[tuple, dict]:
    cells: dict[tuple, dict] = defaultdict(lambda: {
        "n": 0, "wins": 0, "losses": 0,
        "gross_profit": 0.0, "gross_loss": 0.0,
        "pnl_sum": 0.0, "live_n": 0, "shadow_n": 0,
    })
    for r in rows:
        k = cell_key(r)
        c = cells[k]
        c["n"] += 1
        pnl = float(r["pnl_pips"] or 0.0)
        c["pnl_sum"] += pnl
        if r["outcome"] == "WIN":
            c["wins"] += 1
            c["gross_profit"] += abs(pnl)
        else:
            c["losses"] += 1
            c["gross_loss"] += abs(pnl)
        if r["is_shadow"]:
            c["shadow_n"] += 1
        else:
            c["live_n"] += 1
    return cells


def score_cells(cells: dict[tuple, dict], min_n: int) -> list[dict]:
    """Return sorted list of cell records with stats. Filters n < min_n."""
    qualified = [(k, v) for k, v in cells.items() if v["n"] >= min_n]
    n_tests = max(1, len(qualified))  # Bonferroni denominator
    out: list[dict] = []
    for (et, sess, q, mode), c in qualified:
        n, wins = c["n"], c["wins"]
        wr = wins / n
        wl = wilson_lower(wins, n)
        wu = wilson_upper(wins, n)
        ev = c["pnl_sum"] / n
        pf = (c["gross_profit"] / c["gross_loss"]) if c["gross_loss"] > 0 else float("inf")
        p_raw = binomial_two_sided_pvalue(wins, n, p0=0.5)
        p_bonf = min(1.0, p_raw * n_tests)
        out.append({
            "entry_type": et,
            "session": sess,
            "spread_quartile": q,
            "mode": mode,
            "n": n,
            "wins": wins,
            "live_n": c["live_n"],
            "shadow_n": c["shadow_n"],
            "wr": round(wr, 4),
            "wilson_lower": round(wl, 4),
            "wilson_upper": round(wu, 4),
            "ev_pip": round(ev, 3),
            "pf": round(pf, 3) if pf != float("inf") else None,
            "p_value_raw": round(p_raw, 5),
            "p_value_bonferroni": round(p_bonf, 5),
            "promotion_candidate": (
                wl > PROMOTION_WILSON_LOWER and p_bonf < PROMOTION_BONFERRONI_ALPHA
            ),
        })
    out.sort(key=lambda x: x["wilson_lower"], reverse=True)
    return out


def render_markdown(rows: list[dict], min_n: int, include_shadow: bool) -> str:
    candidates = [r for r in rows if r["promotion_candidate"]]
    lines = [
        f"# Cell-by-Cell Edge Audit (Q1', {datetime.now(timezone.utc).date().isoformat()})",
        "",
        f"Source: demo_trades.db, scope: {'Live + Shadow' if include_shadow else 'Live only'}",
        f"Min N per cell: **{min_n}**",
        f"Total cells qualified: **{len(rows)}**",
        f"Promotion candidates (Wilson lower > {PROMOTION_WILSON_LOWER:.0%} AND Bonferroni p < {PROMOTION_BONFERRONI_ALPHA}): **{len(candidates)}**",
        "",
        "## Promotion Candidates",
        "",
    ]
    if candidates:
        lines += [
            "| entry_type | session | quartile | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in candidates:
            pf_str = f"{r['pf']:.2f}" if r["pf"] is not None else "inf"
            lines.append(
                f"| {r['entry_type']} | {r['session']} | {r['spread_quartile']} | {r['mode']} | "
                f"{r['n']} | {r['wins']} | {r['wr']:.1%} | "
                f"[{r['wilson_lower']:.1%}, {r['wilson_upper']:.1%}] | "
                f"{r['ev_pip']:+.2f} | {pf_str} | {r['p_value_bonferroni']:.4f} |"
            )
    else:
        lines.append("_No cells passed promotion criteria._")

    lines += ["", "## All Qualified Cells (sorted by Wilson lower)", "",
              "| entry_type | session | quartile | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        pf_str = f"{r['pf']:.2f}" if r["pf"] is not None else "inf"
        lines.append(
            f"| {r['entry_type']} | {r['session']} | {r['spread_quartile']} | {r['mode']} | "
            f"{r['n']} ({r['live_n']}/{r['shadow_n']}) | {r['wr']:.1%} | "
            f"{r['wilson_lower']:.1%} | {r['ev_pip']:+.2f} | {pf_str} | "
            f"{r['p_value_raw']:.4f} / {r['p_value_bonferroni']:.4f} |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="demo_trades.db")
    parser.add_argument("--include-shadow", action="store_true",
                        help="Include is_shadow=1 trades in cell aggregation")
    parser.add_argument("--min-n", type=int, default=MIN_N)
    parser.add_argument("--out-dir", default="raw/audits")
    args = parser.parse_args()

    rows_db = fetch_trades(args.db, include_shadow=args.include_shadow)
    if not rows_db:
        print("[cell_edge_audit] No closed trades found", file=sys.stderr)
        sys.exit(1)
    cells = aggregate_cells(rows_db)
    scored = score_cells(cells, args.min_n)
    today = datetime.now(timezone.utc).date().isoformat()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_inclshadow" if args.include_shadow else "_liveonly"
    json_path = out_dir / f"cell_edge_audit_{today}{suffix}.json"
    md_path = out_dir / f"cell_edge_audit_{today}{suffix}.md"

    json_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Live+Shadow" if args.include_shadow else "Live",
        "min_n": args.min_n,
        "total_trades": len(rows_db),
        "qualified_cells": len(scored),
        "promotion_candidates": sum(1 for r in scored if r["promotion_candidate"]),
        "cells": scored,
    }, ensure_ascii=False, indent=2))
    md_path.write_text(render_markdown(scored, args.min_n, args.include_shadow))

    cand_n = sum(1 for r in scored if r["promotion_candidate"])
    print(f"[cell_edge_audit] {len(rows_db)} trades → {len(scored)} qualified cells (N≥{args.min_n})")
    print(f"[cell_edge_audit] Promotion candidates: {cand_n}")
    print(f"[cell_edge_audit] Output: {json_path} + {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
