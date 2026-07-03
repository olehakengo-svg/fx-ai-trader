#!/usr/bin/env python3
"""EUR_USD M15 — analyze "rejected by RSI filter" pup_starts.

For each pup_start where rsi<65 (filtered out), compute hypothetical P&L
using pup_end exit (and dev_ef >= 2.5 exit). Tag with timestamp so user can
pinpoint specific events.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kalman_d7_eurusd_filter_grid import prepare


def main(start="2025-05-21", end="2026-05-21"):
    df = prepare(start=start, end=end)
    cl = df["Close"].values
    hi = df["High"].values
    lo = df["Low"].values
    ef = df["ema_fast"].values
    a = df["atr"].values
    r = df["rsi"].values
    rsid3 = df["rsi_d3"].values
    ps = df["pup_start"].values
    pe = df["pup_end"].values
    n = len(df)

    # Simulate ALL pup_start (no filter) with pup_end exit, plus dev_exit info
    trades = []
    in_pos = False; ent_i = -1; ent_px = 0.0
    for i in range(n):
        if not in_pos:
            if ps[i]:
                in_pos = True; ent_i = i; ent_px = cl[i]
        else:
            if pe[i]:
                # also compute the hypothetical dev>=2.5 exit
                dev_exit_i = -1
                for j in range(ent_i, i + 1):
                    if (cl[j] - ef[j]) / a[j] >= 2.5:
                        dev_exit_i = j
                        break
                peak_j = ent_i + int(hi[ent_i:i + 1].argmax())
                trades.append({
                    "ent_ts_utc": df.index[ent_i],
                    "ent_ts_jst": df.index[ent_i] + pd.Timedelta(hours=9),
                    "exit_pup_ts_utc": df.index[i],
                    "exit_pup_ts_jst": df.index[i] + pd.Timedelta(hours=9),
                    "rsi_at_entry": r[ent_i],
                    "rsi_d3_at_entry": rsid3[ent_i] if not np.isnan(rsid3[ent_i]) else 0,
                    "rejected_by_rsi65": r[ent_i] < 65,
                    "pnl_pup_end": (cl[i] - ent_px) / 0.0001,
                    "pnl_dev_exit": ((cl[dev_exit_i] if dev_exit_i >= 0 else cl[i]) - ent_px) / 0.0001,
                    "dev_exit_hit": dev_exit_i >= 0,
                    "peak_pips": (hi[peak_j] - ent_px) / 0.0001,
                    "bars_held": i - ent_i,
                })
                in_pos = False
    t = pd.DataFrame(trades)
    print(f"=== EUR_USD M15 rejected-entry diag ({start}→{end}) ===")
    print(f"Total pup_start: {len(t)}")

    rej = t[t["rejected_by_rsi65"]].copy()
    kep = t[~t["rejected_by_rsi65"]].copy()
    print(f"\nKept (rsi>=65):    N={len(kep)}  pup_end mean={kep['pnl_pup_end'].mean():+.2f}p  WR={(kep['pnl_pup_end']>0).mean()*100:.1f}%  sum={kep['pnl_pup_end'].sum():+.0f}p")
    print(f"Rejected (rsi<65): N={len(rej)}  pup_end mean={rej['pnl_pup_end'].mean():+.2f}p  WR={(rej['pnl_pup_end']>0).mean()*100:.1f}%  sum={rej['pnl_pup_end'].sum():+.0f}p")

    print(f"\nRejected with dev_exit hit (would have closed at +27+ p area):")
    rej_dev = rej[rej["dev_exit_hit"]].copy()
    print(f"  N={len(rej_dev)} / {len(rej)}  ({100*len(rej_dev)/len(rej) if len(rej)>0 else 0:.1f}%)")
    print(f"  pnl_dev_exit mean={rej_dev['pnl_dev_exit'].mean():+.2f}p  sum={rej_dev['pnl_dev_exit'].sum():+.0f}p  WR={(rej_dev['pnl_dev_exit']>0).mean()*100:.1f}%")
    print(f"  pnl_pup_end (if held to end) mean={rej_dev['pnl_pup_end'].mean():+.2f}p  sum={rej_dev['pnl_pup_end'].sum():+.0f}p")
    print(f"  peak_pips mean={rej_dev['peak_pips'].mean():+.2f}p")

    print(f"\n=== Top 10 rejected by peak_pips potential (would have been big wins if entered) ===")
    top = rej.sort_values("peak_pips", ascending=False).head(10)
    for _, row in top.iterrows():
        flag = "DEV_HIT" if row["dev_exit_hit"] else ""
        print(f"  {row['ent_ts_jst']!s:<20} JST  rsi={row['rsi_at_entry']:5.1f}  d3={row['rsi_d3_at_entry']:+5.1f}  peak={row['peak_pips']:+6.1f}p  pup_end={row['pnl_pup_end']:+6.1f}p  dev_exit={row['pnl_dev_exit']:+6.1f}p  {flag}")

    print(f"\n=== Specific event search: 4/30 19:15 JST area ===")
    t["ent_ts_jst_naive"] = t["ent_ts_jst"].dt.tz_localize(None)
    target_jst_y = pd.Timestamp("2026-04-30 19:15:00")
    win = pd.Timedelta(hours=8)
    near = t[(t["ent_ts_jst_naive"] >= target_jst_y - win) & (t["ent_ts_jst_naive"] <= target_jst_y + win)]
    print(f"Search around {target_jst_y} ± 8h: {len(near)} pup_starts found")
    for _, row in near.iterrows():
        flag = "REJECTED" if row["rejected_by_rsi65"] else "KEPT"
        print(f"  {row['ent_ts_jst']!s:<20} JST ({row['ent_ts_utc']!s:<20} UTC)  rsi={row['rsi_at_entry']:5.1f}  d3={row['rsi_d3_at_entry']:+5.1f}  peak={row['peak_pips']:+6.1f}p  pup_end={row['pnl_pup_end']:+6.1f}p  exit_jst={row['exit_pup_ts_jst']!s:<20}  [{flag}]")


if __name__ == "__main__":
    main()
