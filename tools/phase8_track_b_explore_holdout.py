"""Phase 8 Track B — Exploratory holdout audit (NON-LOCK).

Stage 1 (LOCK) had 0 formal survivors because no cell achieved
Wilson_lower > 0.50 with RR=1.5 setup. This script runs a non-binding
holdout check on the top EV>0 + Wilson_lower>0.40 candidates so the master
plan aggregator has visibility into "near-survivor" characteristics.

Output is exploratory — promotion is gated by Stage 1 LOCK gates which
were not met. Use for audit / cross-track comparison only.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import warnings
warnings.filterwarnings("ignore")
import pandas as pd

from tools.lib.trade_sim import simulate_cell_trades, aggregate_trade_stats
from tools.phase8_track_b import (
    _load_pair, _add_atr, add_all_patterns, wilson_lower,
    HOLDOUT_DAYS_LOCK, SL_ATR_MULT_LOCK, TP_ATR_MULT_LOCK,
    TRAINING_DAYS_LOCK,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--top-n", type=int, default=15)
    p.add_argument("--ev-min", type=float, default=0.0)
    p.add_argument("--wilson-min", type=float, default=0.40)
    p.add_argument("--output", default="raw/phase8/track_b/")
    args = p.parse_args()

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    with open(args.input) as f:
        s1 = json.load(f)
    results = s1.get("all_results", [])
    cands = [r for r in results
             if r["ev_net_pip"] >= args.ev_min and r["wilson_lower"] >= args.wilson_min
             and r["n_trades"] >= 50]
    cands.sort(key=lambda x: -x["ev_net_pip"])
    cands = cands[:args.top_n]
    print(f"=== Exploratory holdout audit on top {len(cands)} near-survivors ===")

    pair_dfs = {}
    audited = []
    for r in cands:
        pair = r["pair"]
        if pair not in pair_dfs:
            try:
                df = _load_pair(pair, TRAINING_DAYS_LOCK + HOLDOUT_DAYS_LOCK)
                df = _add_atr(df).dropna(subset=["atr"])
                df = add_all_patterns(df)
                pair_dfs[pair] = df
            except Exception as e:
                print(f"  load failed {pair}: {e}", flush=True)
                continue
        df = pair_dfs[pair]
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
        df_hold = df[df.index >= cutoff]
        col = f"pat_{r['pattern_kind']}"
        mask = (df_hold[col] == r["pattern"])
        bucket_idx = df_hold[mask].index
        sig_idx_hold = [df.index.get_loc(t) for t in bucket_idx]
        if len(sig_idx_hold) < 3:
            r2 = dict(r)
            r2["holdout"] = {"n_signals": len(sig_idx_hold), "skip": "n<3"}
            audited.append(r2)
            continue

        trades = simulate_cell_trades(
            df, sig_idx_hold, r["direction"], df["atr"],
            sl_atr_mult=SL_ATR_MULT_LOCK, tp_atr_mult=TP_ATR_MULT_LOCK,
            max_hold_bars=r["forward_bars"], pair=pair, dedup=True,
        )
        s = aggregate_trade_stats(trades)
        wlo = wilson_lower(s["n_wins"], s["n_trades"]) if s["n_trades"] > 0 else 0
        r2 = dict(r)
        r2["holdout"] = {
            "n_signals": len(sig_idx_hold), "n_trades": s["n_trades"],
            "wr": s["wr"], "wilson_lower": round(wlo, 4),
            "ev_net_pip": s["ev_net_pip"],
            "wr_in_holdout_above_0_50": s["wr"] > 0.50,
            "ev_in_holdout_pos": s["ev_net_pip"] > 0,
        }
        audited.append(r2)
        ho = r2["holdout"]
        ok = "✅" if (ho["wr_in_holdout_above_0_50"] and ho["ev_in_holdout_pos"]) else "❌"
        print(f"  {ok} {pair} {r['direction']} {r['pattern_kind']}={r['pattern']} fw={r['forward_bars']}: "
              f"train n={r['n_trades']} WR={r['wr']:.3f} EV={r['ev_net_pip']:+.2f}p | "
              f"holdout n={ho.get('n_trades', 'NA')} WR={ho.get('wr', 0):.3f} "
              f"EV={ho.get('ev_net_pip', 0):+.2f}p")

    out = {
        "exploratory": True,
        "note": "Non-LOCK exploratory audit. Stage 1 formal LOCK gate (Wilson>0.50) was not met by any cell.",
        "params": {"top_n": args.top_n, "ev_min": args.ev_min,
                   "wilson_min": args.wilson_min},
        "audited": audited,
    }
    json_path = out_dir / f"explore_holdout_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nJSON: {json_path}")


if __name__ == "__main__":
    main()
