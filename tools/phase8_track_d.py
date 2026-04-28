"""Phase 8 Track D — Session Boundary Transitions edge mining.

Pre-registered LOCK: knowledge-base/wiki/decisions/pre-reg-phase8-track-d-2026-04-28.md
Master plan:        knowledge-base/wiki/decisions/phase8-master-2026-04-28.md

Stages (本セッションで Stage 1+2 のみ):
  1: Boundary-level scan (6 boundaries × 5 pairs × 2 dir × 3 fw = 180 cells)
  2: Sub-window scan (40 sub-windows × 5 pairs × 2 dir × 3 fw ≤ 1200 cells)

Usage:
    python3 tools/phase8_track_d.py --stage 1 --days 275
    python3 tools/phase8_track_d.py --stage 2 --days 275 --input raw/phase8/track_d/stage1_boundary_<ts>.json
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

try:
    from scipy.stats import binomtest as _bt
    def _binom(k, n, p):
        return _bt(k=k, n=n, p=p, alternative="two-sided").pvalue
except ImportError:
    from scipy.stats import binom_test as _bt
    def _binom(k, n, p):
        return _bt(k, n, p, alternative="two-sided")

from tools.lib.trade_sim import simulate_cell_trades, aggregate_trade_stats


# ─────────────────────────────────────────────────────────────
# LOCK constants (must match pre-reg-phase8-track-d-2026-04-28.md)
# ─────────────────────────────────────────────────────────────
PAIRS_LOCK = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]
DIRECTIONS_LOCK = ["BUY", "SELL"]
FORWARD_BARS_LOCK = [4, 8, 12]
HOLDOUT_DAYS_LOCK = 90
TRAINING_DAYS_LOCK = 275
SL_ATR_MULT_LOCK = 1.0
TP_ATR_MULT_LOCK = 1.5

# 6 boundary windows. (start_hour, start_min, end_hour, end_min) UTC.
# end is exclusive. cross-midnight handled explicitly for `pre_tokyo`.
BOUNDARY_WINDOWS = {
    "tokyo_to_london": (6, 0, 8, 0),
    "london_to_ny":    (12, 0, 14, 0),
    "ny_to_asia":      (21, 0, 23, 0),
    "pre_tokyo":       (22, 0, 24, 0),   # 22:00-00:00 (cross-midnight, end=24 == 00:00)
    "pre_london":      (6, 0, 7, 0),
    "pre_ny":          (12, 30, 13, 30),
}


# ─────────────────────────────────────────────────────────────
# Statistics helpers (re-used from pattern_discovery)
# ─────────────────────────────────────────────────────────────
def wilson_lower(wins: int, n: int, alpha: float = 0.05) -> float:
    if n == 0:
        return 0.0
    z = 1.959963984540054
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return max(0.0, c - h)


def benjamini_hochberg(p_values: list, q: float = 0.10) -> list:
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    rejected = [False] * n
    for rank_i, (orig_i, p) in enumerate(indexed, start=1):
        threshold = (rank_i / n) * q
        if p <= threshold:
            for k in range(rank_i):
                rejected[indexed[k][0]] = True
    return rejected


# ─────────────────────────────────────────────────────────────
# Window membership
# ─────────────────────────────────────────────────────────────
def _bar_in_window(ts: pd.Timestamp, start_h: int, start_m: int,
                   end_h: int, end_m: int) -> bool:
    """True if bar's UTC time falls within [start, end). end_h=24 => 00:00 next day."""
    h = ts.hour
    m = ts.minute
    cur = h * 60 + m
    sm = start_h * 60 + start_m
    em = end_h * 60 + end_m  # 24*60 = 1440 (treated as next-day 00:00)
    if em <= 1440 and sm < em:
        return sm <= cur < em
    # cross-midnight (rare for our LOCK)
    return cur >= sm or cur < (em - 1440)


def boundary_signal_indices(df: pd.DataFrame, boundary_id: str) -> list:
    """Return df row indices (positional) where bar belongs to the boundary.

    Weekend exclusion: dow ∈ [0..4] (already filtered in feature pipeline,
    but redundant filter applied here for safety).
    """
    sh, sm, eh, em = BOUNDARY_WINDOWS[boundary_id]
    idx_pos = []
    # Vectorized membership for speed
    hours = df.index.hour.values
    mins = df.index.minute.values
    cur = hours * 60 + mins
    sm_total = sh * 60 + sm
    em_total = eh * 60 + em
    if em_total <= 1440 and sm_total < em_total:
        mask = (cur >= sm_total) & (cur < em_total)
    else:
        mask = (cur >= sm_total) | (cur < (em_total - 1440))
    # weekday filter
    dow = df.index.dayofweek.values
    mask = mask & (dow <= 4)
    idx_pos = list(np.where(mask)[0])
    return idx_pos


def subwindow_15min_for_boundary(boundary_id: str) -> list:
    """Enumerate 15-min sub-windows inside a boundary window.

    Returns list of (sub_id, start_h, start_m, end_h, end_m). Each sub-window
    covers exactly one 15m bar.
    """
    sh, sm, eh, em = BOUNDARY_WINDOWS[boundary_id]
    sm_total = sh * 60 + sm
    em_total = eh * 60 + em
    subs = []
    t = sm_total
    while t < em_total:
        s_h, s_m = divmod(t, 60)
        e_t = t + 15
        e_h, e_m = divmod(e_t, 60)
        # normalize end_h=24 → label as such (handled by membership)
        sub_id = f"{boundary_id}_{s_h:02d}{s_m:02d}"
        subs.append((sub_id, s_h, s_m, e_h, e_m))
        t = e_t
    return subs


# ─────────────────────────────────────────────────────────────
# Data + ATR
# ─────────────────────────────────────────────────────────────
def _load_pair(pair: str, days: int) -> pd.DataFrame:
    from tools.bt_data_cache import BTDataCache
    cache = BTDataCache()
    df = cache.get(pair, "15m", days=days)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    return df[df.index >= cutoff].copy()


def _add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    c = df["Close"].astype(float)
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()],
                   axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / period, adjust=False).mean()
    return df


def _prepare_pair_df(pair: str, days: int) -> pd.DataFrame:
    """Load + ATR + holdout reservation + weekday filter."""
    df = _load_pair(pair, days)
    cutoff_holdout = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
    df = df[df.index < cutoff_holdout]
    df = _add_atr(df).dropna(subset=["atr"])
    df = df[df.index.dayofweek <= 4]   # weekday only
    return df


# ─────────────────────────────────────────────────────────────
# Stage 1 — Boundary-level scan
# ─────────────────────────────────────────────────────────────
def stage1_boundary_scan(days: int, pairs: list, forwards: list) -> dict:
    all_results = []
    cell_counter = 0
    for pair in pairs:
        print(f"\n=== Stage 1 — {pair} ===", flush=True)
        try:
            df = _prepare_pair_df(pair, days)
        except Exception as e:
            print(f"  load failed: {e}", flush=True)
            continue
        if len(df) < 1000:
            print(f"  insufficient bars: {len(df)}", flush=True)
            continue
        print(f"  Training bars: {len(df)} (holdout reserved)", flush=True)

        for bnd_id in BOUNDARY_WINDOWS.keys():
            sig_idx = boundary_signal_indices(df, bnd_id)
            if len(sig_idx) < 50:
                continue

            for direction in DIRECTIONS_LOCK:
                for fw in forwards:
                    trades = simulate_cell_trades(
                        df, sig_idx, direction,
                        atr_series=df["atr"],
                        sl_atr_mult=SL_ATR_MULT_LOCK,
                        tp_atr_mult=TP_ATR_MULT_LOCK,
                        max_hold_bars=fw, pair=pair, dedup=True,
                    )
                    stats = aggregate_trade_stats(trades)
                    if stats["n_trades"] < 50:
                        continue

                    wlo = wilson_lower(stats["n_wins"], stats["n_trades"])
                    p = _binom(stats["n_wins"], stats["n_trades"], 0.5)
                    months = days / 30.0
                    per_month = stats["n_trades"] / months

                    all_results.append({
                        "stage": 1,
                        "pair": pair,
                        "boundary": bnd_id,
                        "window_utc": f"{BOUNDARY_WINDOWS[bnd_id][0]:02d}:{BOUNDARY_WINDOWS[bnd_id][1]:02d}-{BOUNDARY_WINDOWS[bnd_id][2]:02d}:{BOUNDARY_WINDOWS[bnd_id][3]:02d}",
                        "direction": direction,
                        "forward_bars": fw,
                        "n_trades": stats["n_trades"],
                        "wr": stats["wr"],
                        "wilson_lower": round(wlo, 4),
                        "ev_net_pip": stats["ev_net_pip"],
                        "pf": stats["pf"],
                        "kelly": stats["kelly"],
                        "sharpe_per_event": stats["sharpe_per_event"],
                        "trades_per_month": round(per_month, 1),
                        "p_value": round(float(p), 6),
                    })
                    cell_counter += 1

    print(f"\nTotal Stage 1 cells generated: {cell_counter}")
    return {"results": all_results, "n_cells": cell_counter}


def stage1_apply_gates(results: list, q: float = 0.10) -> list:
    if not results:
        return []
    p_values = [r["p_value"] for r in results]
    bh_sig = benjamini_hochberg(p_values, q=q)
    survivors = []
    for r, sig in zip(results, bh_sig):
        gates = {
            "bh_fdr": sig,
            "wilson_gt_50": r["wilson_lower"] > 0.50,
            "n_ge_50": r["n_trades"] >= 50,
            "ev_pos": r["ev_net_pip"] > 0,
            "capacity": r["trades_per_month"] >= 5,
            "sharpe_pos": (r["sharpe_per_event"] or 0) > 0.05,
        }
        if all(gates.values()):
            r["gates"] = gates
            survivors.append(r)
    return survivors


# ─────────────────────────────────────────────────────────────
# Stage 2 — Sub-window scan
# ─────────────────────────────────────────────────────────────
def _subwindow_signal_indices(df: pd.DataFrame, sub_h: int, sub_m: int,
                               end_h: int, end_m: int) -> list:
    hours = df.index.hour.values
    mins = df.index.minute.values
    cur = hours * 60 + mins
    sm_total = sub_h * 60 + sub_m
    em_total = end_h * 60 + end_m
    if em_total <= 1440 and sm_total < em_total:
        mask = (cur >= sm_total) & (cur < em_total)
    else:
        mask = (cur >= sm_total) | (cur < (em_total - 1440))
    dow = df.index.dayofweek.values
    mask = mask & (dow <= 4)
    return list(np.where(mask)[0])


def stage2_subwindow_scan(days: int, pairs: list, forwards: list,
                          stage1_survivors: list = None) -> dict:
    """Stage 2: per-15min-sub-window inside each boundary.

    Note: Stage 2 scans ALL (boundary, sub_window, pair, dir, fw) regardless
    of Stage 1 survivors — boundary-level cell may not survive even when
    sub-window does (and vice versa). This is conservative for Bonferroni
    but exposes time-of-day specifics.
    """
    all_results = []
    cell_counter = 0
    for pair in pairs:
        print(f"\n=== Stage 2 — {pair} ===", flush=True)
        try:
            df = _prepare_pair_df(pair, days)
        except Exception as e:
            print(f"  load failed: {e}", flush=True)
            continue
        if len(df) < 1000:
            continue

        for bnd_id in BOUNDARY_WINDOWS.keys():
            sub_windows = subwindow_15min_for_boundary(bnd_id)
            for sub_id, sh, sm_, eh, em_ in sub_windows:
                sig_idx = _subwindow_signal_indices(df, sh, sm_, eh, em_)
                if len(sig_idx) < 50:
                    continue
                for direction in DIRECTIONS_LOCK:
                    for fw in forwards:
                        trades = simulate_cell_trades(
                            df, sig_idx, direction,
                            atr_series=df["atr"],
                            sl_atr_mult=SL_ATR_MULT_LOCK,
                            tp_atr_mult=TP_ATR_MULT_LOCK,
                            max_hold_bars=fw, pair=pair, dedup=True,
                        )
                        stats = aggregate_trade_stats(trades)
                        if stats["n_trades"] < 50:
                            continue

                        wlo = wilson_lower(stats["n_wins"], stats["n_trades"])
                        p = _binom(stats["n_wins"], stats["n_trades"], 0.5)
                        months = days / 30.0
                        per_month = stats["n_trades"] / months

                        all_results.append({
                            "stage": 2,
                            "pair": pair,
                            "boundary": bnd_id,
                            "sub_window": sub_id,
                            "sub_window_utc": f"{sh:02d}:{sm_:02d}-{eh:02d}:{em_:02d}",
                            "direction": direction,
                            "forward_bars": fw,
                            "n_trades": stats["n_trades"],
                            "wr": stats["wr"],
                            "wilson_lower": round(wlo, 4),
                            "ev_net_pip": stats["ev_net_pip"],
                            "pf": stats["pf"],
                            "kelly": stats["kelly"],
                            "sharpe_per_event": stats["sharpe_per_event"],
                            "trades_per_month": round(per_month, 1),
                            "p_value": round(float(p), 6),
                        })
                        cell_counter += 1

    print(f"\nTotal Stage 2 cells generated: {cell_counter}")
    return {"results": all_results, "n_cells": cell_counter}


def stage2_apply_gates(results: list) -> list:
    if not results:
        return []
    n_tests = len(results)
    survivors = []
    for r in results:
        p_bonf = r["p_value"] * n_tests
        r["p_bonf"] = round(p_bonf, 5)
        gates = {
            "bonferroni": p_bonf < 0.05,
            "wilson_gt_50": r["wilson_lower"] > 0.50,
            "n_ge_50": r["n_trades"] >= 50,
            "ev_pos": r["ev_net_pip"] > 0,
            "capacity": r["trades_per_month"] >= 3,
            "sharpe_pos": (r["sharpe_per_event"] or 0) > 0.05,
        }
        if all(gates.values()):
            r["gates"] = gates
            survivors.append(r)
    return survivors


# ─────────────────────────────────────────────────────────────
# Cross-strategy overlap report
# ─────────────────────────────────────────────────────────────
EXISTING_SESSION_STRATEGIES = [
    {"name": "london_close_reversal_v2", "utc": "20:30-21:00",
     "boundary_overlap": "ny_to_asia (21:00-23:00) は隣接、直接重複なし"},
    {"name": "gotobi_fix",               "utc": "00:45-01:15 (約)",
     "boundary_overlap": "pre_tokyo (22:00-00:00) は隣接、直接重複なし"},
    {"name": "london_fix_reversal",      "utc": "16:00 fix",
     "boundary_overlap": "該当 boundary なし"},
]


def write_overlap_report(survivors_s2: list, out_path: Path) -> None:
    lines = ["# Phase 8 Track D — Existing Strategy Overlap Report\n"]
    lines.append(f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
    lines.append(f"**Stage 2 survivors**: {len(survivors_s2)}\n\n")
    lines.append("## Existing session-time strategies (reference)\n\n")
    lines.append("| Strategy | UTC Window | Track D boundary overlap |\n|---|---|---|\n")
    for s in EXISTING_SESSION_STRATEGIES:
        lines.append(f"| `{s['name']}` | {s['utc']} | {s['boundary_overlap']} |\n")
    lines.append("\n## Track D Stage 2 survivors\n\n")
    if not survivors_s2:
        lines.append("(no survivors)\n")
    else:
        lines.append("| pair | boundary | sub_window UTC | dir | fw | N | WR | EV pip | overlap with existing |\n")
        lines.append("|---|---|---|---|---|---|---|---|---|\n")
        for r in survivors_s2:
            ov = "novel"
            if r.get("boundary") == "ny_to_asia" and r.get("direction") == "SELL":
                ov = "potentially redundant with london_close_reversal_v2 (SELL near NY close)"
            elif r.get("boundary") == "pre_tokyo":
                ov = "may overlap with gotobi_fix (Asia open setup)"
            lines.append(
                f"| {r['pair']} | {r['boundary']} | {r.get('sub_window_utc','-')} | "
                f"{r['direction']} | {r['forward_bars']} | {r['n_trades']} | "
                f"{r['wr']:.3f} | {r['ev_net_pip']:+.2f} | {ov} |\n"
            )
    out_path.write_text("".join(lines))


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=int, required=True, choices=[1, 2])
    p.add_argument("--days", type=int, default=TRAINING_DAYS_LOCK)
    p.add_argument("--pairs", nargs="+", default=PAIRS_LOCK)
    p.add_argument("--forwards", type=int, nargs="+", default=FORWARD_BARS_LOCK)
    p.add_argument("--output", default="raw/phase8/track_d/")
    p.add_argument("--input", default=None,
                   help="JSON path (Stage 2 で stage1 出力)")
    p.add_argument("--bh-q", type=float, default=0.10)
    args = p.parse_args()

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    if args.stage == 1:
        print("=" * 60)
        print("  Phase 8 Track D — Stage 1: Boundary-level scan")
        print(f"  Pairs: {args.pairs} | Days: {args.days}")
        print(f"  Boundaries: {list(BOUNDARY_WINDOWS.keys())}")
        print(f"  Holdout reserved: last {HOLDOUT_DAYS_LOCK} days")
        print("=" * 60)
        scan = stage1_boundary_scan(args.days, args.pairs, args.forwards)
        survivors = stage1_apply_gates(scan["results"], q=args.bh_q)
        print(f"\n=== Stage 1 Verdict ===")
        print(f"Total cells: {scan['n_cells']}")
        print(f"Survivors (BH-FDR q={args.bh_q} + all gates): {len(survivors)}")
        if survivors:
            print(f"\nTop survivors by EV_net_pip:")
            top = sorted(survivors, key=lambda x: -x["ev_net_pip"])
            for r in top:
                print(f"  {r['pair']} {r['boundary']} {r['direction']} fw={r['forward_bars']}: "
                      f"n={r['n_trades']} WR={r['wr']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} EV={r['ev_net_pip']:+.2f}p "
                      f"Sharpe={r['sharpe_per_event']:.3f}")

        out = {
            "stage": 1,
            "track": "D",
            "params": {
                "days": args.days, "pairs": args.pairs,
                "forwards": args.forwards, "bh_q": args.bh_q,
                "holdout_days": HOLDOUT_DAYS_LOCK,
                "sl_atr": SL_ATR_MULT_LOCK, "tp_atr": TP_ATR_MULT_LOCK,
                "boundaries": BOUNDARY_WINDOWS,
            },
            "n_cells_total": scan["n_cells"],
            "n_survivors": len(survivors),
            "all_results": scan["results"],
            "survivors": survivors,
        }
        json_path = out_dir / f"stage1_boundary_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")
        return 0

    elif args.stage == 2:
        print("=" * 60)
        print("  Phase 8 Track D — Stage 2: Sub-window scan (Bonferroni)")
        print("=" * 60)
        scan = stage2_subwindow_scan(args.days, args.pairs, args.forwards)
        survivors = stage2_apply_gates(scan["results"])
        print(f"\n=== Stage 2 Verdict ===")
        print(f"Total cells: {scan['n_cells']}")
        print(f"Survivors (Bonferroni + all gates): {len(survivors)}")
        if survivors:
            print(f"\nTop survivors by EV_net_pip:")
            top = sorted(survivors, key=lambda x: -x["ev_net_pip"])
            for r in top:
                print(f"  {r['pair']} {r['sub_window']} {r['direction']} fw={r['forward_bars']}: "
                      f"n={r['n_trades']} WR={r['wr']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} EV={r['ev_net_pip']:+.2f}p "
                      f"Sharpe={r['sharpe_per_event']:.3f} pBonf={r['p_bonf']:.4f}")

        out = {
            "stage": 2,
            "track": "D",
            "params": {"days": args.days, "pairs": args.pairs,
                       "forwards": args.forwards,
                       "boundaries": BOUNDARY_WINDOWS},
            "n_cells_total": scan["n_cells"],
            "n_survivors": len(survivors),
            "all_results": scan["results"],
            "survivors": survivors,
        }
        json_path = out_dir / f"stage2_subwindow_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")

        # Write overlap report
        overlap_path = out_dir / f"overlap_with_existing_{date_tag}.md"
        write_overlap_report(survivors, overlap_path)
        print(f"Overlap report: {overlap_path}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
