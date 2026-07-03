#!/usr/bin/env python3
"""EUR_USD M15 — peak hunt v2.

Refinements from v1:
  - dev_exit=1.8 (median peak observed) instead of 2.5
  - Chandelier with profit activation (only trail after >= K_act*ATR profit)
  - Min-hold N bars (don't exit before bar N)
  - Composite: chandelier-act + rsi-rollover after recent OB-near (RSI>=68)
"""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from kalman_d7_eurusd_filter_grid import prepare


def sim_with_exit_rule(df, rsi_min, exit_fn, sl_mul=1.5, min_hold=0) -> dict:
    cl = df["Close"].values; op_ = df["Open"].values
    hi = df["High"].values; lo = df["Low"].values
    ef = df["ema_fast"].values; a = df["atr"].values
    r = df["rsi"].values
    ps = df["pup_start"].values; pe = df["pup_end"].values
    n = len(df)
    pnl, durs, reasons, caps_abs = [], [], [], []
    in_pos = False; ent_i = -1; ent_px = 0.0; ent_atr = 0.0
    for i in range(n):
        if not in_pos:
            if ps[i] and r[i] >= rsi_min:
                in_pos = True; ent_i = i; ent_px = cl[i]; ent_atr = a[i]
        else:
            close_now = False; reason = ""; exit_px = cl[i]
            held = i - ent_i
            if sl_mul is not None and lo[i] <= ent_px - sl_mul * ent_atr:
                close_now = True; reason = "SL"; exit_px = ent_px - sl_mul * ent_atr
            elif held >= min_hold:
                rc = exit_fn(df, i, ent_i, ent_px, ent_atr)
                if rc is not None:
                    close_now = True; reason = rc[0]; exit_px = rc[1]
                elif pe[i]:
                    close_now = True; reason = "pup_end"; exit_px = cl[i]
            else:
                if pe[i]:
                    close_now = True; reason = "pup_end_early"; exit_px = cl[i]
            if close_now:
                p = (exit_px - ent_px) / 0.0001
                pk = (hi[ent_i:i + 1].max() - ent_px) / 0.0001
                cap_abs = pk - max(p, 0)  # give_back vs peak (only counts if peak was positive)
                pnl.append(p); durs.append(i - ent_i); reasons.append(reason); caps_abs.append(cap_abs)
                in_pos = False
    arr = np.array(pnl)
    if len(arr) == 0: return {"N": 0}
    cum = arr.cumsum(); dd = cum - np.maximum.accumulate(cum)
    wins = arr[arr > 0].sum(); losses = -arr[arr < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")
    return {"N": len(arr), "sum": arr.sum(), "mean": arr.mean(), "wr": (arr > 0).mean() * 100,
            "pf": pf, "meanDur": float(np.mean(durs)), "maxDD": float(dd.min()),
            "mean_giveback": float(np.mean(caps_abs)),
            "reasons": pd.Series(reasons).value_counts().to_dict()}


def main():
    df = prepare(start="2025-05-21", end="2026-05-21")
    print(f"=== EUR_USD M15 peak-hunt v2 (12mo, rsi>=65 filter, SL=1.5xATR) ===")

    # Chandelier with activation: trail only after profit >= K_act * ent_atr
    def make_chand_act(K, K_act):
        def fn(df_, i, ent_i, ent_px, ent_atr):
            cl_ = df_["Close"].iloc[i]
            hh = df_["High"].iloc[ent_i:i + 1].max()
            profit_so_far = hh - ent_px
            if profit_so_far >= K_act * ent_atr:
                if cl_ < hh - K * ent_atr and i > ent_i:
                    return (f"chand_K{K}_act{K_act}", cl_)
            return None
        return fn

    # dev_ef exit at lower threshold
    def make_dev(X):
        def fn(df_, i, ent_i, ent_px, ent_atr):
            cl_ = df_["Close"].iloc[i]; ef_ = df_["ema_fast"].iloc[i]; a_ = df_["atr"].iloc[i]
            if (cl_ - ef_) / a_ >= X:
                return (f"dev_{X}", cl_)
            return None
        return fn

    # rsi rollover from rolling max (only after rsi was >=68 recently)
    def make_rsi_after_ob(N=8, X=5, ob_floor=68):
        def fn(df_, i, ent_i, ent_px, ent_atr):
            if i - ent_i < 3: return None
            r_win = df_["rsi"].iloc[max(ent_i, i - N):i + 1]
            rmax = r_win.max()
            if rmax >= ob_floor and df_["rsi"].iloc[i] <= rmax - X:
                return (f"rsi_after_{ob_floor}_drop{X}", df_["Close"].iloc[i])
            return None
        return fn

    # composite: dev_1.8 OR rsi-after-ob (5pts) OR chand-with-activation
    def make_composite():
        d = make_dev(1.8); r_ = make_rsi_after_ob(8, 5, 68); c = make_chand_act(1.0, 1.5)
        def fn(df_, i, ent_i, ent_px, ent_atr):
            r1 = d(df_, i, ent_i, ent_px, ent_atr)
            if r1: return r1
            r2 = r_(df_, i, ent_i, ent_px, ent_atr)
            if r2: return r2
            r3 = c(df_, i, ent_i, ent_px, ent_atr)
            if r3: return r3
            return None
        return fn

    cands = [
        # baseline
        ("baseline (pup_end)", lambda d, i, ei, ep, ea: None, 0),
        # dev at various thresholds with min_hold
        ("dev>=1.5", make_dev(1.5), 0),
        ("dev>=1.8", make_dev(1.8), 0),
        ("dev>=2.0", make_dev(2.0), 0),
        ("dev>=1.8 + min_hold=10", make_dev(1.8), 10),
        # chandelier with activation
        ("chand K=1.0 act K=1.5", make_chand_act(1.0, 1.5), 0),
        ("chand K=1.5 act K=1.5", make_chand_act(1.5, 1.5), 0),
        ("chand K=1.0 act K=2.0", make_chand_act(1.0, 2.0), 0),
        ("chand K=1.5 act K=2.0", make_chand_act(1.5, 2.0), 0),
        ("chand K=2.0 act K=2.0", make_chand_act(2.0, 2.0), 0),
        # rsi rollover
        ("rsi rolloff 5 after >=68", make_rsi_after_ob(8, 5, 68), 0),
        ("rsi rolloff 7 after >=68", make_rsi_after_ob(8, 7, 68), 0),
        ("rsi rolloff 10 after >=70", make_rsi_after_ob(10, 10, 70), 0),
        # composite
        ("composite (dev+rsi+chand)", make_composite(), 0),
    ]

    print(f"\n{'Rule':<32} {'N':>4} {'sum':>7} {'mean':>7} {'WR%':>5} {'PF':>5} {'gb_p':>5} {'dur':>4}  reasons")
    print("-" * 130)
    for name, fn, hold in cands:
        r = sim_with_exit_rule(df, 65, fn, sl_mul=1.5, min_hold=hold)
        if r.get("N", 0) == 0:
            print(f"{name:<32} 0")
            continue
        print(f"{name:<32} {r['N']:>4} {r['sum']:>+7.0f} {r['mean']:>+7.2f} {r['wr']:>5.1f} {r['pf']:>5.2f} {r['mean_giveback']:>5.1f} {r['meanDur']:>4.0f}  {r['reasons']}")


if __name__ == "__main__":
    main()
