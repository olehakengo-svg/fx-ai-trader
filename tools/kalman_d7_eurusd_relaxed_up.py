#!/usr/bin/env python3
"""EUR_USD M15 — relaxed perfect_up definition.

Strict: ema_fast > ema_mid > ema_slow AND close > ema_fast
Relaxed: ema_fast > ema_mid AND close > ema_fast (drop ema_slow requirement)

The relaxed version catches early uptrends where ema_slow still lags.
BT both with v15m logic (primary rsi65 + rsi_late exit, secondary red-to-green + pup_end).
"""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from kalman_d7_eurusd_filter_grid import prepare


def prepare_relaxed(start, end, max_gap=10):
    df = prepare(start=start, end=end, max_gap=max_gap)
    # Re-compute perfect_up_relaxed: drop ema_slow requirement
    c = df["Close"]
    df["pu_relaxed"] = (df["ema_fast"] > df["ema_mid"]) & (c > df["ema_fast"])
    df["pdn"] = df["perfect_dn"]  # keep strict perfect_dn
    df["neutral_rel"] = ~df["pu_relaxed"] & ~df["pdn"]
    # rebuild bridge with relaxed up
    n = len(df)
    pu = df["pu_relaxed"].values; pdn = df["pdn"].values
    bspu = np.empty(n, dtype=np.int64); cur = 9999
    for i in range(n):
        if pu[i]: cur = 0
        elif pdn[i]: cur = 9999
        else: cur += 1
        bspu[i] = cur
    df["bspu_rel"] = bspu
    df["persistent_up_rel"] = df["pu_relaxed"] | (df["neutral_rel"] & (df["bspu_rel"] <= max_gap))
    df["pup_start_rel"] = df["persistent_up_rel"] & ~df["persistent_up_rel"].shift(1, fill_value=False)
    df["pup_end_rel"] = ~df["persistent_up_rel"]
    df["pdn_in_50"] = df["pdn"].rolling(50).sum()
    return df


def sim_v15m_logic(df, use_relaxed: bool):
    cl = df["Close"].values
    a = df["atr"].values
    r = df["rsi"].values
    if use_relaxed:
        ps = df["pup_start_rel"].values
        pe = df["pup_end_rel"].values
    else:
        ps = df["pup_start"].values
        pe = df["pup_end"].values
    pdn50 = df["pdn_in_50"].values
    n = len(df)
    pnl, ent_types, durs = [], [], []
    in_pos = False; ent_i = -1; ent_px = 0.0; ent_type = ""
    for i in range(n):
        if not in_pos:
            if ps[i]:
                is_primary = r[i] >= 65
                is_secondary = (r[i] < 65) and (not np.isnan(pdn50[i])) and (pdn50[i] >= 30)
                if is_primary or is_secondary:
                    in_pos = True; ent_i = i; ent_px = cl[i]
                    ent_type = "primary" if is_primary else "secondary"
        else:
            close_now = False
            held = i - ent_i
            if ent_type == "primary":
                if held >= 40:
                    r_win = r[max(ent_i, i - 30):i + 1]
                    rmax = r_win.max()
                    if rmax >= 68 and r[i] <= rmax - 3:
                        close_now = True
                if not close_now and pe[i]:
                    close_now = True
            else:
                if pe[i]:
                    close_now = True
            if close_now:
                p = (cl[i] - ent_px) / 0.0001
                pnl.append(p); ent_types.append(ent_type); durs.append(i - ent_i)
                in_pos = False
    arr = np.array(pnl)
    if len(arr) == 0:
        return {"N": 0}
    wins = arr[arr > 0].sum(); losses = -arr[arr < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")
    return {"N": len(arr), "sum": arr.sum(), "mean": arr.mean(), "wr": (arr > 0).mean() * 100, "pf": pf,
            "meanDur": float(np.mean(durs)),
            "n_primary": ent_types.count("primary"), "n_secondary": ent_types.count("secondary")}


def main():
    df_strict = prepare(start="2025-05-21", end="2026-05-21")
    df_strict["pdn_in_50"] = df_strict["perfect_dn"].rolling(50).sum()
    df_relaxed = prepare_relaxed(start="2025-05-21", end="2026-05-21")

    print(f"=== EUR_USD M15 — strict vs relaxed perfect_up (12mo) ===")
    print(f"strict perfect_up bars: {int(df_strict['perfect_up'].sum())}")
    print(f"relaxed perfect_up bars: {int(df_relaxed['pu_relaxed'].sum())}")
    print(f"strict pup_start: {int(df_strict['pup_start'].sum())}")
    print(f"relaxed pup_start: {int(df_relaxed['pup_start_rel'].sum())}")

    print(f"\n{'Variant':<25} {'N':>4} {'Pri':>4} {'Sec':>4} {'sum':>7} {'mean':>7} {'WR%':>5} {'PF':>5}")
    print("-" * 80)
    r1 = sim_v15m_logic(df_strict, use_relaxed=False)
    print(f"{'v15m strict':<25} {r1['N']:>4} {r1['n_primary']:>4} {r1['n_secondary']:>4} {r1['sum']:>+7.0f} {r1['mean']:>+7.2f} {r1['wr']:>5.1f} {r1['pf']:>5.2f}")
    r2 = sim_v15m_logic(df_relaxed, use_relaxed=True)
    print(f"{'v15m relaxed up':<25} {r2['N']:>4} {r2['n_primary']:>4} {r2['n_secondary']:>4} {r2['sum']:>+7.0f} {r2['mean']:>+7.2f} {r2['wr']:>5.1f} {r2['pf']:>5.2f}")


if __name__ == "__main__":
    main()
