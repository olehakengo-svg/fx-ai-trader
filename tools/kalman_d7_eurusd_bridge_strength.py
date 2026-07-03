#!/usr/bin/env python3
"""EUR_USD M15 — bridge strengthening grid.

Current bridge: perfect_dn (1 bar) immediately breaks bridge.
New: require N consecutive perfect_dn bars to break bridge.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def atr_calc(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi_calc(s, n=14):
    d = s.diff()
    up = d.clip(lower=0); dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1 / n, adjust=False).mean() / dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + rs)


CACHE = Path(__file__).resolve().parent.parent / "data/cache/massive"


def prepare(start="2025-05-21", end="2026-05-21", max_gap=10, dn_break_required=1):
    df = pd.read_parquet(CACHE / "EUR_USD_15m.parquet").loc[start:end].copy()
    c = df["Close"]
    df["ema_fast"] = ema(c, 25); df["ema_mid"] = ema(c, 75); df["ema_slow"] = ema(c, 200)
    df["atr"] = atr_calc(df, 14); df["rsi"] = rsi_calc(c, 14)
    df["perfect_up"] = (df["ema_fast"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_slow"]) & (c > df["ema_fast"])
    df["perfect_dn"] = (df["ema_slow"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_fast"])
    df["neutral"] = ~df["perfect_up"] & ~df["perfect_dn"]
    pu = df["perfect_up"].values; pdn = df["perfect_dn"].values
    n = len(df)
    bspu = np.empty(n, dtype=np.int64)
    dn_streak = np.empty(n, dtype=np.int64)
    cur_bspu = 9999
    cur_dn = 0
    for i in range(n):
        if pdn[i]:
            cur_dn += 1
        else:
            cur_dn = 0
        dn_streak[i] = cur_dn
        if pu[i]:
            cur_bspu = 0
        elif cur_dn >= dn_break_required:
            cur_bspu = 9999
        else:
            cur_bspu += 1
        bspu[i] = cur_bspu
    df["bspu"] = bspu
    df["dn_streak"] = dn_streak
    df["persistent_up"] = df["perfect_up"] | (~df["perfect_up"] & (df["bspu"] <= max_gap))
    df["pup_start"] = df["persistent_up"] & ~df["persistent_up"].shift(1, fill_value=False)
    df["pup_end"] = ~df["persistent_up"]
    df["rsi_d3"] = df["rsi"] - df["rsi"].shift(3)
    return df


def sim(df, rsi_min: float | None = None, sl_mul: float | None = None, dev_thresh: float | None = None) -> dict:
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
                if rsi_min is None or r[i] >= rsi_min:
                    in_pos = True; ent_i = i; ent_px = cl[i]; ent_atr = a[i]
        else:
            close_now = False; reason = ""; exit_px = cl[i]
            if sl_mul is not None and lo[i] <= ent_px - sl_mul * ent_atr:
                close_now = True; reason = "SL"; exit_px = ent_px - sl_mul * ent_atr
            else:
                if dev_thresh is not None and (cl[i] - ef[i]) / a[i] >= dev_thresh:
                    close_now = True; reason = "dev_exit"; exit_px = cl[i]
                elif pe[i]:
                    close_now = True; reason = "pup_end"; exit_px = cl[i]
            if close_now:
                p = (exit_px - ent_px) / 0.0001
                pnl.append(p); durs.append(i - ent_i); reasons.append(reason)
                in_pos = False
    arr = np.array(pnl)
    if len(arr) == 0:
        return {"N": 0}
    cum = arr.cumsum()
    dd = cum - np.maximum.accumulate(cum)
    wins = arr[arr > 0].sum(); losses = -arr[arr < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")
    wr = (arr > 0).mean()
    return {"N": len(arr), "sum": arr.sum(), "mean": arr.mean(), "wr": wr * 100, "pf": pf,
            "meanDur": float(np.mean(durs)), "maxDD": float(dd.min()),
            "reasons": pd.Series(reasons).value_counts().to_dict()}


def main():
    print(f"=== EUR_USD M15 bridge strengthening grid (12mo) ===")
    # dn_break_required: 1 (current) / 2 / 3 / 5
    # rsi_min: None / 60 / 65
    # dev / SL: as v15j (2.5 / 1.5xATR) — only use one good combo
    print(f"\n{'dn_brk':>6} {'rsi_min':>8} {'dev':>4} {'SL':>4} {'N':>4} {'sum':>7} {'mean':>7} {'WR%':>5} {'PF':>5} {'DD':>6} reasons")
    print("-" * 110)
    for dn_brk in [1, 2, 3, 5]:
        df = prepare(dn_break_required=dn_brk)
        ps_count = int(df["pup_start"].sum())
        print(f"# dn_break={dn_brk}: pup_start events: {ps_count}")
        for rmin in [None, 60, 65]:
            # Variant A: pure pup_end exit (like v15i)
            r1 = sim(df, rsi_min=rmin)
            if r1.get("N", 0) > 0:
                rlbl = "none" if rmin is None else str(rmin)
                print(f"{dn_brk:>6} {rlbl:>8} {'-':>4} {'-':>4} {r1['N']:>4} {r1['sum']:>+7.0f} {r1['mean']:>+7.2f} {r1['wr']:>5.1f} {r1['pf']:>5.2f} {r1['maxDD']:>+6.0f}  pure_pup_end")
            # Variant B: dev_exit 2.5 + SL 1.5 (like v15j)
            r2 = sim(df, rsi_min=rmin, dev_thresh=2.5, sl_mul=1.5)
            if r2.get("N", 0) > 0:
                rlbl = "none" if rmin is None else str(rmin)
                print(f"{dn_brk:>6} {rlbl:>8} {'2.5':>4} {'1.5':>4} {r2['N']:>4} {r2['sum']:>+7.0f} {r2['mean']:>+7.2f} {r2['wr']:>5.1f} {r2['pf']:>5.2f} {r2['maxDD']:>+6.0f}  {r2['reasons']}")


if __name__ == "__main__":
    main()
