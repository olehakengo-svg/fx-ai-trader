#!/usr/bin/env python3
"""EUR_USD M15 — red-to-green transition entry diagnostic.

Goal: find pup_start events that occur AFTER a recent perfect_dn-dominated
period. These represent trend reversals (often the largest moves).

Analysis:
  - For each pup_start, count perfect_dn bars in last N (e.g., 20, 50)
  - Bucket and measure forward P&L (pup_end exit, rsi_late exit)
  - Find threshold of "recent_dn_ratio" that gates a profitable entry
"""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from kalman_d7_eurusd_filter_grid import prepare


def main():
    df = prepare(start="2025-05-21", end="2026-05-21")
    df["pdn_in_20"] = df["perfect_dn"].rolling(20).sum()
    df["pdn_in_50"] = df["perfect_dn"].rolling(50).sum()
    df["pdn_in_100"] = df["perfect_dn"].rolling(100).sum()

    cl = df["Close"].values; hi = df["High"].values; lo = df["Low"].values
    ef = df["ema_fast"].values; a = df["atr"].values; r = df["rsi"].values
    ps = df["pup_start"].values; pe = df["pup_end"].values
    n = len(df)

    # Simulate trades (no entry filter) tracking pdn-in-window context
    trades = []
    in_pos = False; ent_i = -1; ent_px = 0.0
    for i in range(n):
        if not in_pos:
            if ps[i]:
                in_pos = True; ent_i = i; ent_px = cl[i]
        else:
            if pe[i]:
                # peak high
                peak_pos = ent_i + int(hi[ent_i:i + 1].argmax())
                trades.append({
                    "ent_ts_jst": df.index[ent_i] + pd.Timedelta(hours=9),
                    "rsi_at_entry": r[ent_i],
                    "pdn_in_20": df["pdn_in_20"].iloc[ent_i],
                    "pdn_in_50": df["pdn_in_50"].iloc[ent_i],
                    "pdn_in_100": df["pdn_in_100"].iloc[ent_i],
                    "pnl_pup_end": (cl[i] - ent_px) / 0.0001,
                    "peak_pips": (hi[peak_pos] - ent_px) / 0.0001,
                    "bars_held": i - ent_i,
                })
                in_pos = False
    t = pd.DataFrame(trades)
    print(f"=== EUR_USD M15 red-to-green entry diag (12mo) ===")
    print(f"Total pup_start: {len(t)}")

    # Bucket by pdn_in_20
    print(f"\n=== pdn_in_20 bucket (last 20 bars perfect_dn count) ===")
    for lo_, hi_ in [(0, 1), (1, 3), (3, 7), (7, 12), (12, 21)]:
        sub = t[(t["pdn_in_20"] >= lo_) & (t["pdn_in_20"] < hi_)]
        if len(sub) == 0: continue
        wins_p = sub[sub["pnl_pup_end"] > 0]["pnl_pup_end"].sum()
        loss_p = -sub[sub["pnl_pup_end"] <= 0]["pnl_pup_end"].sum()
        pf = wins_p / loss_p if loss_p > 0 else float("inf")
        wr = (sub["pnl_pup_end"] > 0).mean() * 100
        print(f"  pdn_in_20 ∈ [{lo_:>2},{hi_:>2})  N={len(sub):>3}  mean={sub['pnl_pup_end'].mean():+7.2f}p  WR={wr:5.1f}%  PF={pf:5.2f}  peak_mean={sub['peak_pips'].mean():+6.1f}p  avg_rsi={sub['rsi_at_entry'].mean():.1f}")

    # Bucket by pdn_in_50
    print(f"\n=== pdn_in_50 bucket (last 50 bars perfect_dn count) ===")
    for lo_, hi_ in [(0, 5), (5, 15), (15, 25), (25, 35), (35, 51)]:
        sub = t[(t["pdn_in_50"] >= lo_) & (t["pdn_in_50"] < hi_)]
        if len(sub) == 0: continue
        wins_p = sub[sub["pnl_pup_end"] > 0]["pnl_pup_end"].sum()
        loss_p = -sub[sub["pnl_pup_end"] <= 0]["pnl_pup_end"].sum()
        pf = wins_p / loss_p if loss_p > 0 else float("inf")
        wr = (sub["pnl_pup_end"] > 0).mean() * 100
        print(f"  pdn_in_50 ∈ [{lo_:>2},{hi_:>2})  N={len(sub):>3}  mean={sub['pnl_pup_end'].mean():+7.2f}p  WR={wr:5.1f}%  PF={pf:5.2f}  peak_mean={sub['peak_pips'].mean():+6.1f}p  avg_rsi={sub['rsi_at_entry'].mean():.1f}")

    # Combined: low RSI but high pdn (red-to-green transitions)
    print(f"\n=== Combined: low RSI (rsi<65) but recent strong perfect_dn ===")
    for pdn_thresh in [3, 5, 7, 10]:
        sub = t[(t["rsi_at_entry"] < 65) & (t["pdn_in_20"] >= pdn_thresh)]
        if len(sub) == 0: continue
        wins_p = sub[sub["pnl_pup_end"] > 0]["pnl_pup_end"].sum()
        loss_p = -sub[sub["pnl_pup_end"] <= 0]["pnl_pup_end"].sum()
        pf = wins_p / loss_p if loss_p > 0 else float("inf")
        wr = (sub["pnl_pup_end"] > 0).mean() * 100
        print(f"  rsi<65 AND pdn_in_20>={pdn_thresh:>2}: N={len(sub):>3}  mean={sub['pnl_pup_end'].mean():+7.2f}p  WR={wr:5.1f}%  PF={pf:5.2f}  peak_mean={sub['peak_pips'].mean():+6.1f}p  avg_rsi={sub['rsi_at_entry'].mean():.1f}")

    # Also try pdn_in_50
    print(f"\n=== Combined: low RSI (rsi<65) but recent strong perfect_dn (50-bar) ===")
    for pdn_thresh in [10, 15, 20, 25, 30]:
        sub = t[(t["rsi_at_entry"] < 65) & (t["pdn_in_50"] >= pdn_thresh)]
        if len(sub) == 0: continue
        wins_p = sub[sub["pnl_pup_end"] > 0]["pnl_pup_end"].sum()
        loss_p = -sub[sub["pnl_pup_end"] <= 0]["pnl_pup_end"].sum()
        pf = wins_p / loss_p if loss_p > 0 else float("inf")
        wr = (sub["pnl_pup_end"] > 0).mean() * 100
        print(f"  rsi<65 AND pdn_in_50>={pdn_thresh:>2}: N={len(sub):>3}  mean={sub['pnl_pup_end'].mean():+7.2f}p  WR={wr:5.1f}%  PF={pf:5.2f}  peak_mean={sub['peak_pips'].mean():+6.1f}p  avg_rsi={sub['rsi_at_entry'].mean():.1f}")


if __name__ == "__main__":
    main()
