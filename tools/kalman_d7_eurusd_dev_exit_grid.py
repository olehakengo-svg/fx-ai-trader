#!/usr/bin/env python3
"""EUR_USD M15 — dev_ef_atr exit grid.

Variants:
  Entry: pup_start  (filter: F0 none / F1 rsi>=65)
  Exit:  dev_ef_atr >= X  (X = 1.5, 2.0, 2.5, 3.0), with pup_end fallback
  SL:    none / 1.5xATR
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from kalman_d7_eurusd_filter_grid import prepare


def sim(df, entry_filter: str, dev_thresh: float, sl_mul: float | None = None) -> dict:
    cl = df["Close"].values
    hi = df["High"].values
    lo = df["Low"].values
    ef = df["ema_fast"].values
    a = df["atr"].values
    r = df["rsi"].values
    ps = df["pup_start"].values
    pe = df["pup_end"].values
    n = len(df)

    pnl, durs, reasons = [], [], []
    in_pos = False; ent_i = -1; ent_px = 0.0; ent_atr = 0.0
    for i in range(n):
        if not in_pos:
            if ps[i]:
                if entry_filter == "F0":
                    ok = True
                elif entry_filter == "F1":
                    ok = r[i] >= 65
                else:
                    ok = True
                if ok:
                    in_pos = True; ent_i = i; ent_px = cl[i]; ent_atr = a[i]
        else:
            close_now = False; reason = ""; exit_px = cl[i]
            # SL check first
            if sl_mul is not None and lo[i] <= ent_px - sl_mul * ent_atr:
                close_now = True; reason = "SL"; exit_px = ent_px - sl_mul * ent_atr
            else:
                # dev_ef_atr exit (check on close - might also use high for "touched the level")
                dev_now = (cl[i] - ef[i]) / a[i]
                if dev_now >= dev_thresh:
                    close_now = True; reason = "dev_exit"; exit_px = cl[i]
                elif pe[i]:
                    close_now = True; reason = "pup_end_fb"; exit_px = cl[i]
            if close_now:
                p = (exit_px - ent_px) / 0.0001
                pnl.append(p); durs.append(i - ent_i); reasons.append(reason)
                in_pos = False

    arr = np.array(pnl)
    if len(arr) == 0:
        return {"N": 0}
    cum = arr.cumsum()
    dd = cum - np.maximum.accumulate(cum)
    wins_p = arr[arr > 0].sum(); loss_p = -arr[arr < 0].sum()
    pf = wins_p / loss_p if loss_p > 0 else float("inf")
    wr = (arr > 0).mean()
    from math import sqrt
    N = len(arr); p = wr; z = 1.96
    denom = 1 + z**2 / N
    center = p + z**2 / (2 * N)
    margin = z * sqrt(p * (1 - p) / N + z**2 / (4 * N**2))
    wlo = (center - margin) / denom
    return {"N": N, "sum": arr.sum(), "mean": arr.mean(), "wr": wr * 100, "pf": pf,
            "meanDur": float(np.mean(durs)), "maxDD": float(dd.min()), "wilson_lo": wlo * 100,
            "reasons": pd.Series(reasons).value_counts().to_dict()}


def main():
    df = prepare()
    print(f"=== EUR_USD M15 dev_ef_atr exit grid ===")
    print(f"bars: {len(df):,}  pup_start: {int(df['pup_start'].sum())}")

    combos = []
    for f in ["F0", "F1"]:
        for X in [1.5, 2.0, 2.5, 3.0]:
            for sl in [None, 1.5]:
                combos.append((f, X, sl))

    print(f"\n{'F':<3} {'dev>=':>6} {'SL':<7} {'N':>4} {'sum':>7} {'mean':>7} {'WR%':>5} {'WL%':>5} {'PF':>5} {'DD':>6} {'dur':>4}  reasons")
    print("-" * 110)
    for f, X, sl in combos:
        r = sim(df, f, X, sl)
        if r.get("N", 0) == 0:
            print(f"{f:<3} {X:>6.1f} {(sl if sl else 'none')!s:<7} 0")
            continue
        sl_lbl = "none" if sl is None else f"{sl}"
        print(f"{f:<3} {X:>6.1f} {sl_lbl:<7} {r['N']:>4} {r['sum']:>+7.0f} {r['mean']:>+7.2f} {r['wr']:>5.1f} {r['wilson_lo']:>5.1f} {r['pf']:>5.2f} {r['maxDD']:>+6.0f} {r['meanDur']:>4.0f}  {r['reasons']}")


if __name__ == "__main__":
    main()
