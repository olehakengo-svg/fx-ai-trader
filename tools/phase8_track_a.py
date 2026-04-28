"""Phase 8 Track A — 3-Way Feature Interaction Edge Mining.

Pre-registered LOCK: knowledge-base/wiki/decisions/pre-reg-phase8-track-a-2026-04-28.md

Phase 7 single-feature scan の唯一 survivor は GBP_JPY × hour=20 × SELL のみで
既存 LCR-v2 と redundant。Phase 8 Track A は **2-3 within-pair feature triplet**
× 5 pairs × 2 dir × 3 fw を網羅し、higher-order interaction edge を発掘する。

Stages:
  1: Training scan (275d), per-triplet BH-FDR + N≥100 + EV>0 + capacity
  2: Holdout 90d OOS validation

Usage:
    python3 tools/phase8_track_a.py --stage 1
    python3 tools/phase8_track_a.py --stage 2 --input raw/phase8/track_a/stage1_<tag>.json
    python3 tools/phase8_track_a.py --stage all   # Stage 1 → 2 を一気通貫
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
import time
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
from tools.pattern_discovery import (
    _add_features, _load_pair, wilson_lower, benjamini_hochberg,
    PAIRS_LOCK, DIRECTIONS_LOCK, FORWARD_BARS_LOCK,
    HOLDOUT_DAYS_LOCK, TRAINING_DAYS_LOCK,
    SL_ATR_MULT_LOCK, TP_ATR_MULT_LOCK,
)


# ─────────────────────────────────────────────────────────────
# LOCK — pre-reg-phase8-track-a-2026-04-28.md 準拠
# ─────────────────────────────────────────────────────────────
TRIPLETS_LOCK = [
    # T1: hour × pair × bbpb_15m
    ("hour_utc", "bbpb_15m_b"),
    # T2: hour × bbpb × atr_pct_60d  (3-feature within-pair)
    ("hour_utc", "bbpb_15m_b", "atr_pct_60d_b"),
    # T3: pair × bbpb × rsi
    ("bbpb_15m_b", "rsi_15m_b"),
    # T4: dow × hour × pair
    ("dow", "hour_utc"),
]

MIN_N_TRADES = 100
MIN_TRADES_PER_MONTH = 5
MIN_SHARPE_PE = 0.05
WILSON_THRESHOLD = 0.50
BH_Q = 0.10


# ─────────────────────────────────────────────────────────────
# Stage 1 — Triplet scan on training period
# ─────────────────────────────────────────────────────────────
def _scan_triplet_for_pair(
    df: pd.DataFrame,
    pair: str,
    triplet: tuple,
    forwards: list,
    days: int,
) -> list:
    """Scan all bucket combos for one (pair, triplet)."""
    # Validate columns exist
    for f in triplet:
        if f not in df.columns:
            return []

    # Limit signal bars to those where all triplet features are non-NA
    sub = df.dropna(subset=list(triplet) + ["atr"])
    if len(sub) < 1000:
        return []

    # Determine bucket sets per feature
    bucket_sets = []
    for f in triplet:
        vals = sub[f].dropna().unique().tolist()
        # Strip pandas NA / non-int oddities
        clean = []
        for v in vals:
            try:
                clean.append(int(v))
            except Exception:
                continue
        bucket_sets.append(sorted(set(clean)))

    months = days / 30.0
    results = []

    # Pre-compute all bucket combinations as tuple key
    from itertools import product
    combos = list(product(*bucket_sets))
    feature_arrays = {f: sub[f].astype("Int64").to_numpy() for f in triplet}
    sub_index = sub.index
    sub_to_full = np.array([df.index.get_loc(t) for t in sub_index])
    atr_full = df["atr"]

    for combo in combos:
        # Build mask
        mask = np.ones(len(sub), dtype=bool)
        for f, b in zip(triplet, combo):
            arr = feature_arrays[f]
            mask &= (arr == b)
        if mask.sum() < MIN_N_TRADES:
            continue
        signal_indices_full = sub_to_full[mask].tolist()

        for direction in DIRECTIONS_LOCK:
            for fw in forwards:
                trades = simulate_cell_trades(
                    df, signal_indices_full, direction,
                    atr_series=atr_full,
                    sl_atr_mult=SL_ATR_MULT_LOCK,
                    tp_atr_mult=TP_ATR_MULT_LOCK,
                    max_hold_bars=fw, pair=pair, dedup=True,
                )
                stats = aggregate_trade_stats(trades)
                if stats["n_trades"] < MIN_N_TRADES:
                    continue
                wlo = wilson_lower(stats["n_wins"], stats["n_trades"])
                p = _binom(stats["n_wins"], stats["n_trades"], 0.5)
                per_month = stats["n_trades"] / months

                rec = {
                    "pair": pair,
                    "triplet": list(triplet),
                    "buckets": [int(b) for b in combo],
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
                }
                results.append(rec)
    return results


def stage1_scan(
    days: int = TRAINING_DAYS_LOCK,
    pairs: list = None,
    forwards: list = None,
    triplets: list = None,
) -> dict:
    pairs = pairs or PAIRS_LOCK
    forwards = forwards or FORWARD_BARS_LOCK
    triplets = triplets or TRIPLETS_LOCK

    all_results = []
    pair_dfs = {}
    cutoff_holdout = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)

    for pair in pairs:
        t0 = time.time()
        try:
            df = _load_pair(pair, days + HOLDOUT_DAYS_LOCK)
        except Exception as e:
            print(f"  [{pair}] load failed: {e}", flush=True)
            continue
        df = df[df.index < cutoff_holdout]
        df = _add_features(df).dropna(subset=["atr", "bbpb_15m", "rsi_15m"])
        if len(df) < 1000:
            print(f"  [{pair}] insufficient bars: {len(df)}", flush=True)
            continue
        pair_dfs[pair] = df
        print(f"  [{pair}] training bars: {len(df)} (load+features {time.time()-t0:.1f}s)",
              flush=True)

        for triplet in triplets:
            t1 = time.time()
            res = _scan_triplet_for_pair(df, pair, triplet, forwards, days)
            all_results.extend(res)
            print(f"    triplet {triplet}: {len(res)} cells "
                  f"({time.time()-t1:.1f}s)", flush=True)

    return {"results": all_results, "n_cells": len(all_results)}


def stage1_apply_gates(results: list, q: float = BH_Q) -> list:
    if not results:
        return []
    p_values = [r["p_value"] for r in results]
    bh_sig = benjamini_hochberg(p_values, q=q)
    survivors = []
    for r, sig in zip(results, bh_sig):
        gates = {
            "bh_fdr": sig,
            "wilson_gt_50": r["wilson_lower"] > WILSON_THRESHOLD,
            "n_ge_100": r["n_trades"] >= MIN_N_TRADES,
            "ev_pos": r["ev_net_pip"] > 0,
            "capacity": r["trades_per_month"] >= MIN_TRADES_PER_MONTH,
            "sharpe_pos": (r["sharpe_per_event"] or 0) > MIN_SHARPE_PE,
        }
        if all(gates.values()):
            r2 = dict(r)
            r2["gates"] = gates
            survivors.append(r2)
    return survivors


# ─────────────────────────────────────────────────────────────
# Stage 2 — Holdout OOS
# ─────────────────────────────────────────────────────────────
def stage2_holdout(survivors_s1: list, days: int = TRAINING_DAYS_LOCK) -> list:
    if not survivors_s1:
        return []
    pair_dfs = {}
    cutoff_holdout = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
    survivors_s2 = []

    for r in survivors_s1:
        pair = r["pair"]
        if pair not in pair_dfs:
            try:
                df_full = _load_pair(pair, days + HOLDOUT_DAYS_LOCK)
                df_full = _add_features(df_full).dropna(
                    subset=["atr", "bbpb_15m", "rsi_15m"])
                pair_dfs[pair] = df_full
            except Exception as e:
                print(f"  [{pair}] holdout load failed: {e}", flush=True)
                continue
        df_full = pair_dfs[pair]
        df_hold = df_full[df_full.index >= cutoff_holdout]
        if len(df_hold) < 100:
            r2 = dict(r)
            r2["stage2_holdout"] = {"n": 0, "reason": "insufficient holdout bars"}
            r2["stage2_pass"] = False
            survivors_s2.append(r2)
            continue

        triplet = r["triplet"]
        buckets = r["buckets"]
        mask = np.ones(len(df_hold), dtype=bool)
        for f, b in zip(triplet, buckets):
            if f not in df_hold.columns:
                mask = np.zeros(len(df_hold), dtype=bool)
                break
            arr = df_hold[f].astype("Int64").to_numpy()
            mask &= (arr == b)

        sig_idx = [df_full.index.get_loc(t) for t in df_hold.index[mask]]
        if len(sig_idx) < 10:
            r2 = dict(r)
            r2["stage2_holdout"] = {"n": len(sig_idx), "reason": "n<10"}
            r2["stage2_pass"] = False
            survivors_s2.append(r2)
            continue

        trades = simulate_cell_trades(
            df_full, sig_idx, r["direction"], df_full["atr"],
            sl_atr_mult=SL_ATR_MULT_LOCK, tp_atr_mult=TP_ATR_MULT_LOCK,
            max_hold_bars=r["forward_bars"], pair=pair, dedup=True,
        )
        s = aggregate_trade_stats(trades)
        wlo = wilson_lower(s["n_wins"], s["n_trades"]) if s["n_trades"] > 0 else 0
        passed = (s["n_trades"] >= 10) and (s["wr"] > 0.50) and (s["ev_net_pip"] > 0)
        r2 = dict(r)
        r2["stage2_holdout"] = {
            "n": s["n_trades"], "wr": s["wr"],
            "wilson_lower": round(wlo, 4),
            "ev_net_pip": s["ev_net_pip"],
            "pf": s["pf"],
        }
        r2["stage2_pass"] = passed
        survivors_s2.append(r2)
    return survivors_s2


# ─────────────────────────────────────────────────────────────
# Markdown summary
# ─────────────────────────────────────────────────────────────
def write_summary_md(stage1_out: dict, stage2_results: list, path: Path) -> None:
    final_survivors = [r for r in stage2_results if r.get("stage2_pass")]
    final_sorted = sorted(final_survivors,
                          key=lambda r: -(r.get("ev_net_pip") or 0))

    lines = []
    lines.append("# Phase 8 Track A — 3-Way Feature Interaction Audit Summary")
    lines.append("")
    lines.append(f"- Run: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"- LOCK: `pre-reg-phase8-track-a-2026-04-28.md`")
    lines.append(f"- Triplets scanned: {len(TRIPLETS_LOCK)}")
    lines.append(f"- Pairs: {len(PAIRS_LOCK)} ({', '.join(PAIRS_LOCK)})")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    lines.append(f"| metric | value |")
    lines.append(f"|---|---|")
    lines.append(f"| Stage 1 cells (all) | {stage1_out.get('n_cells_total', 0)} |")
    lines.append(f"| Stage 1 survivors (BH+gates) | {stage1_out.get('n_survivors', 0)} |")
    lines.append(f"| Stage 2 tested on holdout | {len(stage2_results)} |")
    lines.append(f"| Stage 2 final survivors | {len(final_survivors)} |")
    lines.append("")

    if final_sorted:
        lines.append("## Top 5 Final Survivors (by EV_net_pip)")
        lines.append("")
        for i, r in enumerate(final_sorted[:5], 1):
            tdesc = " × ".join(f"{f}={b}" for f, b in zip(r["triplet"], r["buckets"]))
            ho = r["stage2_holdout"]
            lines.append(
                f"### #{i} — `{r['pair']} {r['direction']} fw={r['forward_bars']}` × {tdesc}")
            lines.append("")
            lines.append(
                f"- **Training**: n={r['n_trades']} WR={r['wr']:.3f} "
                f"Wilson_lo={r['wilson_lower']:.3f} "
                f"EV={r['ev_net_pip']:+.2f}p PF={r['pf']} Sharpe_pe={r['sharpe_per_event']:.3f} "
                f"trades/mo={r['trades_per_month']}")
            lines.append(
                f"- **Holdout (90d OOS)**: n={ho['n']} WR={ho['wr']:.3f} "
                f"Wilson_lo={ho.get('wilson_lower'):.3f} "
                f"EV={ho['ev_net_pip']:+.2f}p PF={ho.get('pf')}")
            lines.append("")
    else:
        lines.append("## No final survivors")
        lines.append("")
        lines.append("None of the Stage 1 survivors passed Stage 2 holdout OOS gates.")
        lines.append("")

    # Honest negative findings
    lines.append("## Honest Negative Findings")
    lines.append("")
    s1_survivors = stage1_out.get("survivors", [])
    s1_failed_holdout = [r for r in stage2_results if not r.get("stage2_pass")]
    lines.append(f"- Stage 1 survivors that failed Stage 2: {len(s1_failed_holdout)}")
    if s1_failed_holdout:
        lines.append("")
        lines.append("Top 5 Stage-1 cells that failed holdout (highest training EV):")
        lines.append("")
        sorted_failed = sorted(s1_failed_holdout,
                                key=lambda r: -(r.get("ev_net_pip") or 0))[:5]
        for r in sorted_failed:
            tdesc = " × ".join(f"{f}={b}" for f, b in zip(r["triplet"], r["buckets"]))
            ho = r.get("stage2_holdout", {})
            lines.append(
                f"- `{r['pair']} {r['direction']} fw={r['forward_bars']}` "
                f"× {tdesc}: train n={r['n_trades']} EV={r['ev_net_pip']:+.2f}p WR={r['wr']:.3f} "
                f"→ holdout n={ho.get('n', 0)} WR={ho.get('wr', 'N/A')} "
                f"EV={ho.get('ev_net_pip', 'N/A')}")
        lines.append("")

    # Cross-track redundancy note
    lines.append("## Cross-track Redundancy Check Hints")
    lines.append("")
    lines.append(
        "Phase 7 単発 survivor: `GBP_JPY × hour_utc=20 × SELL` (LCR-v2 redundant)。")
    if final_sorted:
        for r in final_sorted[:5]:
            if (r["pair"] == "GBP_JPY"
                    and r["direction"] == "SELL"
                    and "hour_utc" in r["triplet"]
                    and 20 in [int(b) for f, b in zip(r["triplet"], r["buckets"])
                               if f == "hour_utc"]):
                lines.append(
                    f"- ⚠️ `{r['pair']} SELL × hour=20 × ...` は Phase 7 と重複の可能性。"
                    f" 3rd feature が真に selectivity を加えているか master が判定。")
    lines.append("")

    path.write_text("\n".join(lines))


# ─────────────────────────────────────────────────────────────
# Main CLI
# ─────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=["1", "2", "all"], default="all")
    p.add_argument("--days", type=int, default=TRAINING_DAYS_LOCK)
    p.add_argument("--pairs", nargs="+", default=PAIRS_LOCK)
    p.add_argument("--forwards", type=int, nargs="+", default=FORWARD_BARS_LOCK)
    p.add_argument("--input", default=None,
                   help="Stage 2 用 stage1 JSON path")
    p.add_argument("--output", default="raw/phase8/track_a/")
    p.add_argument("--bh-q", type=float, default=BH_Q)
    args = p.parse_args()

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    stage1_path = None
    stage1_out = None

    if args.stage in ("1", "all"):
        print("=" * 64)
        print("  Phase 8 Track A — Stage 1: Training Triplet Scan")
        print(f"  Pairs: {args.pairs} | Days: {args.days} (training only)")
        print(f"  Holdout reserved: {HOLDOUT_DAYS_LOCK}d")
        print(f"  Triplets ({len(TRIPLETS_LOCK)}): {TRIPLETS_LOCK}")
        print("=" * 64)
        t_start = time.time()
        scan = stage1_scan(days=args.days, pairs=args.pairs,
                           forwards=args.forwards)
        s1_survivors = stage1_apply_gates(scan["results"], q=args.bh_q)
        elapsed = time.time() - t_start
        print(f"\n=== Stage 1 Verdict ({elapsed:.1f}s) ===")
        print(f"  Total cells: {scan['n_cells']}")
        print(f"  Survivors:   {len(s1_survivors)}")
        if s1_survivors:
            print(f"\n  Top 10 by EV_net_pip:")
            for r in sorted(s1_survivors, key=lambda x: -x["ev_net_pip"])[:10]:
                tdesc = " × ".join(f"{f}={b}" for f, b in zip(r["triplet"], r["buckets"]))
                print(f"    {r['pair']} {r['direction']} fw={r['forward_bars']:>2} "
                      f"| {tdesc}: n={r['n_trades']} WR={r['wr']:.3f} "
                      f"Wlo={r['wilson_lower']:.3f} EV={r['ev_net_pip']:+.2f}p "
                      f"S_pe={r['sharpe_per_event']:.3f}")

        stage1_out = {
            "stage": 1,
            "params": {
                "days": args.days, "pairs": args.pairs,
                "forwards": args.forwards, "bh_q": args.bh_q,
                "holdout_days": HOLDOUT_DAYS_LOCK,
                "sl_atr": SL_ATR_MULT_LOCK, "tp_atr": TP_ATR_MULT_LOCK,
                "triplets": [list(t) for t in TRIPLETS_LOCK],
            },
            "n_cells_total": scan["n_cells"],
            "n_survivors": len(s1_survivors),
            "elapsed_sec": round(elapsed, 1),
            "all_results": scan["results"],
            "survivors": s1_survivors,
        }
        stage1_path = out_dir / f"stage1_{date_tag}.json"
        with open(stage1_path, "w") as f:
            json.dump(stage1_out, f, indent=2, default=str)
        print(f"\n  Stage 1 JSON: {stage1_path}")

    if args.stage in ("2", "all"):
        print("\n" + "=" * 64)
        print("  Phase 8 Track A — Stage 2: Holdout 90d OOS")
        print("=" * 64)
        if args.stage == "2":
            if not args.input:
                print("ERROR: --input <stage1.json> required for --stage 2",
                      file=sys.stderr)
                return 1
            with open(args.input) as f:
                stage1_out = json.load(f)
            stage1_path = Path(args.input)
        s1_survivors = stage1_out.get("survivors", []) if stage1_out else []
        if not s1_survivors:
            print("  Stage 1 had no survivors — no Stage 2 work.")
            stage2_results = []
        else:
            t_start = time.time()
            stage2_results = stage2_holdout(s1_survivors, days=args.days)
            elapsed = time.time() - t_start
            final_survivors = [r for r in stage2_results if r.get("stage2_pass")]
            print(f"\n=== Stage 2 Verdict ({elapsed:.1f}s) ===")
            print(f"  Tested:           {len(stage2_results)}")
            print(f"  Final survivors:  {len(final_survivors)}")
            if final_survivors:
                print(f"\n  Final survivors (by holdout EV):")
                for r in sorted(final_survivors,
                                key=lambda x: -x["stage2_holdout"]["ev_net_pip"]):
                    tdesc = " × ".join(f"{f}={b}" for f, b in zip(r["triplet"], r["buckets"]))
                    ho = r["stage2_holdout"]
                    print(f"    {r['pair']} {r['direction']} fw={r['forward_bars']:>2} "
                          f"| {tdesc}")
                    print(f"      train: n={r['n_trades']} WR={r['wr']:.3f} "
                          f"EV={r['ev_net_pip']:+.2f}p")
                    print(f"      hold:  n={ho['n']} WR={ho['wr']:.3f} "
                          f"EV={ho['ev_net_pip']:+.2f}p")
        stage2_out = {
            "stage": 2,
            "params": {
                "days": args.days, "holdout_days": HOLDOUT_DAYS_LOCK,
                "stage1_input": str(stage1_path) if stage1_path else None,
            },
            "n_tested": len(stage2_results),
            "n_final_survivors": sum(1 for r in stage2_results if r.get("stage2_pass")),
            "results": stage2_results,
        }
        stage2_path = out_dir / f"stage2_holdout_{date_tag}.json"
        with open(stage2_path, "w") as f:
            json.dump(stage2_out, f, indent=2, default=str)
        print(f"\n  Stage 2 JSON: {stage2_path}")

        # Summary md
        if stage1_out:
            md_path = out_dir / f"track_a_summary_{date_tag}.md"
            write_summary_md(stage1_out, stage2_results, md_path)
            print(f"  Summary MD:   {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
