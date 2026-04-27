"""Cell-by-Cell Edge Audit (Q1', 2026-04-27; v2 + v3 added 2026-04-27)

Identify promotion-eligible cells from demo_trades.db.

Cell key:
  v1 (default): (entry_type, session, spread_quartile, mode)
  v2 (--mode v2): (entry_type, session, pair, mode)
    - spread_quartile を drop (USD_JPY/EUR_USD で degenerate, discriminating power ゼロ)
    - pair を追加 (cross-pair 比較で edge を見つける)
  v3 (--mode v3): (entry_type, session, pair, direction, mode)
    - 非対称エッジ検出 (USD_JPY/SELLは負けるがGBP_USD/BUYは勝つ型)
    - dt_bb_rsi_mr GBP_USD/BUY のような direction-specific edge 監査用

For each cell with N >= MIN_N, compute:
  - N, WR, Wilson 95% lower bound
  - EV (mean pnl_pips), PF (gross profit / gross loss)
  - p-value (binomial test vs WR=50%)
  - Bonferroni-adjusted p (conservative)
  - Benjamini-Hochberg FDR-adjusted p (less conservative, for additional candidate hunting)

Time window option (--window):
  all (default): 全期間
  30d / 14d / 7d: 直近 N 日のみ (regime shift 捕捉)

Output:
  - JSON to raw/audits/cell_edge_audit_<date>_<suffix>.json
  - Markdown to raw/audits/cell_edge_audit_<date>_<suffix>.md (sorted by Wilson lower)

Promotion candidates (auto-flagged):
  Wilson lower > 0.50 AND N >= MIN_N AND Bonferroni p < 0.05

WATCH candidates (flagged for additional hunting via FDR):
  Wilson lower > 0.50 AND N >= MIN_N AND FDR-adjusted p < 0.05 AND Bonferroni p ≥ 0.05

Usage:
  python3 tools/cell_edge_audit.py [--db demo_trades.db] [--include-shadow]
  python3 tools/cell_edge_audit.py --mode v2 --window 30d --include-shadow
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
def fetch_trades(db_path: str, include_shadow: bool,
                 since_iso: str | None = None) -> list[sqlite3.Row]:
    """Fetch closed trades. since_iso filters by entry_time >= since_iso."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Static SQL — no string formatting (semgrep B608 / CWE-89 safe).
    if since_iso is not None:
        if include_shadow:
            rows = conn.execute("""
                SELECT trade_id, entry_type, mode, instrument, direction, tf,
                       entry_time, entry_price, sl, spread_at_entry,
                       outcome, pnl_pips, is_shadow
                FROM demo_trades
                WHERE outcome IN ('WIN','LOSS')
                  AND entry_time >= ?
            """, (since_iso,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT trade_id, entry_type, mode, instrument, direction, tf,
                       entry_time, entry_price, sl, spread_at_entry,
                       outcome, pnl_pips, is_shadow
                FROM demo_trades
                WHERE outcome IN ('WIN','LOSS') AND is_shadow = 0
                  AND entry_time >= ?
            """, (since_iso,)).fetchall()
    else:
        if include_shadow:
            rows = conn.execute("""
                SELECT trade_id, entry_type, mode, instrument, direction, tf,
                       entry_time, entry_price, sl, spread_at_entry,
                       outcome, pnl_pips, is_shadow
                FROM demo_trades
                WHERE outcome IN ('WIN','LOSS')
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT trade_id, entry_type, mode, instrument, direction, tf,
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


def cell_key_v2(row: sqlite3.Row) -> tuple[str, str, str, str]:
    """v2: drop spread_quartile (degenerate for USD_JPY/EUR_USD), add pair."""
    et = row["entry_type"] or "unknown"
    sess_raw = derive_session_from_utc(row["entry_time"])
    sess = _normalize_session(sess_raw)
    pair = row["instrument"] or "USD_JPY"
    mode = normalize_mode(row["mode"])
    return (et, sess, pair, mode)


def cell_key_v3(row: sqlite3.Row) -> tuple[str, str, str, str, str]:
    """v3: v2 + direction (BUY/SELL). For asymmetric edge detection."""
    et = row["entry_type"] or "unknown"
    sess_raw = derive_session_from_utc(row["entry_time"])
    sess = _normalize_session(sess_raw)
    pair = row["instrument"] or "USD_JPY"
    direction = (row["direction"] or "?").upper()
    mode = normalize_mode(row["mode"])
    return (et, sess, pair, direction, mode)


def aggregate_cells(rows: Iterable[sqlite3.Row], mode: str = "v1") -> dict[tuple, dict]:
    """Aggregate trades into cells.

    mode: 'v1' (entry_type × session × spread_quartile × mode)
          'v2' (entry_type × session × pair × mode) — degenerate dim 削除
          'v3' (entry_type × session × pair × direction × mode) — 非対称エッジ検出
    """
    if mode == "v3":
        keyfn = cell_key_v3
    elif mode == "v2":
        keyfn = cell_key_v2
    else:
        keyfn = cell_key
    cells: dict[tuple, dict] = defaultdict(lambda: {
        "n": 0, "wins": 0, "losses": 0,
        "gross_profit": 0.0, "gross_loss": 0.0,
        "pnl_sum": 0.0, "live_n": 0, "shadow_n": 0,
    })
    for r in rows:
        k = keyfn(r)
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


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """BH (FDR) adjusted p-values. Returns list in original order."""
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adj = [0.0] * n
    # ranked: i-th smallest p has rank i+1
    cum_min = 1.0
    for rank in range(n - 1, -1, -1):
        orig_idx, p = indexed[rank]
        bh = min(1.0, p * n / (rank + 1))
        cum_min = min(cum_min, bh)
        adj[orig_idx] = cum_min
    return adj


def score_cells(cells: dict[tuple, dict], min_n: int, mode: str = "v1") -> list[dict]:
    """Return sorted list of cell records with stats. Filters n < min_n.

    Outputs include both Bonferroni and BH (FDR) adjusted p-values.
    """
    qualified = [(k, v) for k, v in cells.items() if v["n"] >= min_n]
    n_tests = max(1, len(qualified))
    # First pass: collect raw p-values
    raw_records: list[dict] = []
    raw_pvals: list[float] = []
    for k, c in qualified:
        n, wins = c["n"], c["wins"]
        wr = wins / n
        wl = wilson_lower(wins, n)
        wu = wilson_upper(wins, n)
        ev = c["pnl_sum"] / n
        pf = (c["gross_profit"] / c["gross_loss"]) if c["gross_loss"] > 0 else float("inf")
        p_raw = binomial_two_sided_pvalue(wins, n, p0=0.5)
        p_bonf = min(1.0, p_raw * n_tests)
        # v1 key: (et, sess, q, mode), v2 key: (et, sess, pair, mode), v3: + direction
        if mode == "v3":
            et, sess, pair, direction, md = k
            cell_dim = {"entry_type": et, "session": sess, "pair": pair,
                        "direction": direction, "mode": md}
        elif mode == "v2":
            et, sess, pair, md = k
            cell_dim = {"entry_type": et, "session": sess, "pair": pair, "mode": md}
        else:
            et, sess, q, md = k
            cell_dim = {"entry_type": et, "session": sess, "spread_quartile": q, "mode": md}
        rec = {
            **cell_dim,
            "n": n, "wins": wins,
            "live_n": c["live_n"], "shadow_n": c["shadow_n"],
            "wr": round(wr, 4),
            "wilson_lower": round(wl, 4),
            "wilson_upper": round(wu, 4),
            "ev_pip": round(ev, 3),
            "pf": round(pf, 3) if pf != float("inf") else None,
            "p_value_raw": round(p_raw, 5),
            "p_value_bonferroni": round(p_bonf, 5),
        }
        raw_records.append(rec)
        raw_pvals.append(p_raw)

    # BH FDR adjustment (less conservative than Bonferroni)
    bh_adj = benjamini_hochberg(raw_pvals)
    out: list[dict] = []
    for rec, bh in zip(raw_records, bh_adj):
        wl = rec["wilson_lower"]
        p_bonf = rec["p_value_bonferroni"]
        rec["p_value_bh_fdr"] = round(bh, 5)
        rec["promotion_candidate"] = (
            wl > PROMOTION_WILSON_LOWER and p_bonf < PROMOTION_BONFERRONI_ALPHA
        )
        # WATCH: passes BH but not Bonferroni (additional hunt pool)
        rec["watch_candidate"] = (
            wl > PROMOTION_WILSON_LOWER
            and bh < PROMOTION_BONFERRONI_ALPHA
            and p_bonf >= PROMOTION_BONFERRONI_ALPHA
        )
        out.append(rec)
    out.sort(key=lambda x: x["wilson_lower"], reverse=True)
    return out


def render_markdown(rows: list[dict], min_n: int, include_shadow: bool,
                    audit_mode: str = "v1", window: str = "all") -> str:
    """Render audit results to markdown. Supports v1/v2/v3 cell schemas."""
    candidates = [r for r in rows if r["promotion_candidate"]]
    watch = [r for r in rows if r.get("watch_candidate")]
    if audit_mode == "v3":
        third_dim = "pair"
    elif audit_mode == "v2":
        third_dim = "pair"
    else:
        third_dim = "spread_quartile"
    extra_dim = "direction" if audit_mode == "v3" else None
    lines = [
        f"# Cell-by-Cell Edge Audit ({audit_mode}, window={window}, {datetime.now(timezone.utc).date().isoformat()})",
        "",
        f"Source: demo_trades.db, scope: {'Live + Shadow' if include_shadow else 'Live only'}",
        f"Cell key dims: entry_type × session × **{third_dim}** × mode",
        f"Min N per cell: **{min_n}**, Time window: **{window}**",
        f"Total cells qualified: **{len(rows)}**",
        f"Promotion candidates (Wilson lower > {PROMOTION_WILSON_LOWER:.0%} AND Bonferroni p < {PROMOTION_BONFERRONI_ALPHA}): **{len(candidates)}**",
        f"WATCH candidates (BH FDR p < {PROMOTION_BONFERRONI_ALPHA}, Bonferroni 不通過): **{len(watch)}**",
        "",
        "## Promotion Candidates",
        "",
    ]
    if candidates:
        if extra_dim:
            lines += [
                f"| entry_type | session | {third_dim} | {extra_dim} | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|",
            ]
            for r in candidates:
                pf_str = f"{r['pf']:.2f}" if r["pf"] is not None else "inf"
                lines.append(
                    f"| {r['entry_type']} | {r['session']} | {r[third_dim]} | {r[extra_dim]} | {r['mode']} | "
                    f"{r['n']} | {r['wins']} | {r['wr']:.1%} | "
                    f"[{r['wilson_lower']:.1%}, {r['wilson_upper']:.1%}] | "
                    f"{r['ev_pip']:+.2f} | {pf_str} | {r['p_value_bonferroni']:.4f} |"
                )
        else:
            lines += [
                f"| entry_type | session | {third_dim} | mode | N | wins | WR | Wilson [lo, hi] | EV pip | PF | p (Bonf) |",
                "|---|---|---|---|---|---|---|---|---|---|---|",
            ]
            for r in candidates:
                pf_str = f"{r['pf']:.2f}" if r["pf"] is not None else "inf"
                lines.append(
                    f"| {r['entry_type']} | {r['session']} | {r[third_dim]} | {r['mode']} | "
                    f"{r['n']} | {r['wins']} | {r['wr']:.1%} | "
                    f"[{r['wilson_lower']:.1%}, {r['wilson_upper']:.1%}] | "
                    f"{r['ev_pip']:+.2f} | {pf_str} | {r['p_value_bonferroni']:.4f} |"
                )
    else:
        lines.append("_No cells passed promotion criteria._")

    def _row_dim_cells(r: dict) -> str:
        if extra_dim:
            return f"{r[third_dim]} | {r[extra_dim]}"
        return f"{r[third_dim]}"

    dim_header = f"{third_dim} | {extra_dim}" if extra_dim else third_dim
    pad = "---|" if extra_dim else ""

    if watch:
        lines += ["", "## WATCH Candidates (FDR-significant only)", "",
                  f"| entry_type | session | {dim_header} | mode | N | WR | Wilson lo | EV pip | p (Bonf / BH) |",
                  f"|---|---|---|{pad}---|---|---|---|---|---|"]
        for r in watch:
            lines.append(
                f"| {r['entry_type']} | {r['session']} | {_row_dim_cells(r)} | {r['mode']} | "
                f"{r['n']} | {r['wr']:.1%} | {r['wilson_lower']:.1%} | "
                f"{r['ev_pip']:+.2f} | {r['p_value_bonferroni']:.4f} / {r['p_value_bh_fdr']:.4f} |"
            )

    lines += ["", "## All Qualified Cells (sorted by Wilson lower)", "",
              f"| entry_type | session | {dim_header} | mode | N (Live/Shadow) | WR | Wilson lower | EV pip | PF | p (raw / Bonf / BH) |",
              f"|---|---|---|{pad}---|---|---|---|---|---|---|"]
    for r in rows:
        pf_str = f"{r['pf']:.2f}" if r["pf"] is not None else "inf"
        lines.append(
            f"| {r['entry_type']} | {r['session']} | {_row_dim_cells(r)} | {r['mode']} | "
            f"{r['n']} ({r['live_n']}/{r['shadow_n']}) | {r['wr']:.1%} | "
            f"{r['wilson_lower']:.1%} | {r['ev_pip']:+.2f} | {pf_str} | "
            f"{r['p_value_raw']:.4f} / {r['p_value_bonferroni']:.4f} / "
            f"{r.get('p_value_bh_fdr', 0):.4f} |"
        )
    return "\n".join(lines) + "\n"


def _window_to_iso(window: str) -> str | None:
    """Map '7d' / '14d' / '30d' / 'all' to ISO timestamp cutoff (or None for all)."""
    if window in (None, "", "all"):
        return None
    if not window.endswith("d"):
        raise ValueError(f"Invalid --window {window!r}; expected '7d'/'14d'/'30d'/'all'")
    days = int(window[:-1])
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return cutoff.isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="demo_trades.db")
    parser.add_argument("--include-shadow", action="store_true",
                        help="Include is_shadow=1 trades in cell aggregation")
    parser.add_argument("--min-n", type=int, default=MIN_N)
    parser.add_argument("--out-dir", default="raw/audits")
    parser.add_argument("--mode", choices=["v1", "v2", "v3"], default="v1",
                        help="v1: spread_quartile dim / v2: pair dim / "
                             "v3: pair × direction (asymmetric edge)")
    parser.add_argument("--strategy", default=None,
                        help="Filter to single entry_type for focused audit")
    parser.add_argument("--window", default="all",
                        help="Time window: 7d/14d/30d/all (default all)")
    args = parser.parse_args()

    since = _window_to_iso(args.window)
    rows_db = fetch_trades(args.db, include_shadow=args.include_shadow,
                           since_iso=since)
    if not rows_db:
        print("[cell_edge_audit] No closed trades found", file=sys.stderr)
        sys.exit(1)
    if args.strategy:
        rows_db = [r for r in rows_db if r["entry_type"] == args.strategy]
        if not rows_db:
            print(f"[cell_edge_audit] No trades for strategy={args.strategy!r}", file=sys.stderr)
            sys.exit(1)
    cells = aggregate_cells(rows_db, mode=args.mode)
    scored = score_cells(cells, args.min_n, mode=args.mode)
    today = datetime.now(timezone.utc).date().isoformat()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = [today, args.mode, args.window,
             "inclshadow" if args.include_shadow else "liveonly"]
    suffix = "_" + "_".join(parts)
    json_path = out_dir / f"cell_edge_audit{suffix}.json"
    md_path = out_dir / f"cell_edge_audit{suffix}.md"

    json_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Live+Shadow" if args.include_shadow else "Live",
        "audit_mode": args.mode,
        "window": args.window,
        "min_n": args.min_n,
        "total_trades": len(rows_db),
        "qualified_cells": len(scored),
        "promotion_candidates": sum(1 for r in scored if r["promotion_candidate"]),
        "watch_candidates": sum(1 for r in scored if r.get("watch_candidate")),
        "cells": scored,
    }, ensure_ascii=False, indent=2))
    md_path.write_text(render_markdown(scored, args.min_n, args.include_shadow,
                                       audit_mode=args.mode, window=args.window))

    cand_n = sum(1 for r in scored if r["promotion_candidate"])
    watch_n = sum(1 for r in scored if r.get("watch_candidate"))
    print(f"[cell_edge_audit] mode={args.mode} window={args.window} "
          f"{len(rows_db)} trades → {len(scored)} qualified cells (N≥{args.min_n})")
    print(f"[cell_edge_audit] Promotion candidates: {cand_n} | WATCH candidates: {watch_n}")
    print(f"[cell_edge_audit] Output: {json_path} + {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
