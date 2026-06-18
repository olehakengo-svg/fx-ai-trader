#!/usr/bin/env python3
"""EUR_USD M15 — loose filter exploration with pup_end exit, no SL.

Goal: find filter that increases N (vs F2's 23) while keeping PF > 1.5.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from kalman_d7_eurusd_filter_grid import prepare, simulate


def main():
    df = prepare()
    print(f"=== EUR_USD M15 loose-filter grid (pup_end exit, no SL) ===")
    print(f"bars: {len(df):,}  pup_start events: {int(df['pup_start'].sum())}")

    # filter variants: (name, rsi_d3_min, rsi_at_entry_min)
    variants = [
        ("F0  baseline",           -99,  0),
        ("rsi>=70",                -99, 70),
        ("rsi>=65",                -99, 65),
        ("rsi>=60",                -99, 60),
        ("rsi>=55",                -99, 55),
        ("rsi>=50",                -99, 50),
        ("d3>0",                     0,  0),
        ("d3>1",                     1,  0),
        ("d3>2",                     2,  0),
        ("d3>3",                     3,  0),
        ("d3>5",                     5,  0),
        ("d3>0  AND rsi>=60",        0, 60),
        ("d3>0  AND rsi>=65",        0, 65),
        ("d3>1  AND rsi>=60",        1, 60),
        ("d3>1  AND rsi>=65",        1, 65),
        ("d3>2  AND rsi>=55",        2, 55),
        ("d3>2  AND rsi>=60",        2, 60),
        ("d3>2  AND rsi>=65",        2, 65),
        ("d3>3  AND rsi>=55",        3, 55),
        ("d3>3  AND rsi>=60",        3, 60),
        ("d3>3  AND rsi>=65 (F2)",   3, 65),
        ("d3>5  AND rsi>=60",        5, 60),
        ("d3>5  AND rsi>=65",        5, 65),
    ]

    # custom simulate with arbitrary thresholds
    def sim(d3_min: float, rsi_min: float) -> dict:
        cl = df["Close"].values
        a_atr = df["atr"].values
        r = df["rsi"].values
        rsid3 = df["rsi_d3"].values
        ps = df["pup_start"].values
        pe = df["pup_end"].values
        n = len(df)
        pnl, durs = [], []
        in_pos = False; ent_px = 0.0; ent_i = -1
        for i in range(n):
            if not in_pos:
                if ps[i]:
                    d3 = rsid3[i] if not np.isnan(rsid3[i]) else -999
                    if d3 > d3_min and r[i] >= rsi_min:
                        in_pos = True; ent_px = cl[i]; ent_i = i
            else:
                if pe[i]:
                    p = (cl[i] - ent_px) / 0.0001
                    pnl.append(p); durs.append(i - ent_i)
                    in_pos = False
        arr = np.array(pnl)
        if len(arr) == 0:
            return {"N": 0, "sum": 0, "mean": np.nan, "wr": np.nan, "pf": np.nan, "meanDur": np.nan, "maxDD": np.nan, "wilson_lo": np.nan}
        cum = arr.cumsum()
        dd = cum - np.maximum.accumulate(cum)
        wins = arr[arr > 0].sum(); losses = -arr[arr < 0].sum()
        pf = wins / losses if losses > 0 else float("inf")
        wr = (arr > 0).mean()
        # Wilson 95% LB
        from math import sqrt
        N = len(arr); p = wr
        z = 1.96
        denom = 1 + z**2 / N
        center = p + z**2 / (2 * N)
        margin = z * sqrt(p * (1 - p) / N + z**2 / (4 * N**2))
        wlo = (center - margin) / denom
        return {"N": N, "sum": arr.sum(), "mean": arr.mean(), "wr": wr * 100, "pf": pf,
                "meanDur": float(np.mean(durs)), "maxDD": float(dd.min()), "wilson_lo": wlo * 100}

    print(f"\n{'Filter':<26} {'N':>4} {'sum':>7} {'mean':>7} {'WR%':>5} {'WL%':>5} {'PF':>5} {'DD':>6} {'dur':>4}")
    print("-" * 80)
    for name, d3m, rmin in variants:
        r = sim(d3m, rmin)
        if r["N"] == 0:
            print(f"{name:<26} 0")
            continue
        print(f"{name:<26} {r['N']:>4} {r['sum']:>+7.0f} {r['mean']:>+7.2f} {r['wr']:>5.1f} {r['wilson_lo']:>5.1f} {r['pf']:>5.2f} {r['maxDD']:>+6.0f} {r['meanDur']:>4.0f}")


if __name__ == "__main__":
    main()
