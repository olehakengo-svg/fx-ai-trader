#!/usr/bin/env python3
"""EUR_USD M15 Kalman D7 — entry filter × exit logic × initial SL grid BT.

Grid (kept small to limit post-hoc selection):
  entry filters (3):
    F0: none (baseline pup_start)
    F1: rsi_d3 > 0
    F2: rsi_d3 > 3 AND rsi_at_entry >= 65
  exit logics (3):
    E0: pup_end only
    E1: peak_v2 (RSI cross down through 70 after recent >=70) + pup_end fallback
    E2: ATR trail 0.5x (similar to v18e)
  initial SL (2):
    S0: none
    S1: 1.5x ATR below entry
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "data/cache/massive"


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


def prepare(start="2025-07-01", end="2026-05-05", max_gap=10):
    df = pd.read_parquet(CACHE / "EUR_USD_15m.parquet").loc[start:end].copy()
    c = df["Close"]
    df["ema_fast"] = ema(c, 25); df["ema_mid"] = ema(c, 75); df["ema_slow"] = ema(c, 200)
    df["atr"] = atr_calc(df, 14); df["rsi"] = rsi_calc(c, 14)
    df["perfect_up"] = (df["ema_fast"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_slow"]) & (c > df["ema_fast"])
    df["perfect_dn"] = (df["ema_slow"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_fast"])
    df["neutral"] = ~df["perfect_up"] & ~df["perfect_dn"]
    pu = df["perfect_up"].values; pdn = df["perfect_dn"].values
    bspu = np.empty(len(df), dtype=np.int64); cur = 9999
    for i in range(len(df)):
        if pu[i]: cur = 0
        elif pdn[i]: cur = 9999
        else: cur += 1
        bspu[i] = cur
    df["bspu"] = bspu
    df["persistent_up"] = df["perfect_up"] | (df["neutral"] & (df["bspu"] <= max_gap))
    df["pup_start"] = df["persistent_up"] & ~df["persistent_up"].shift(1, fill_value=False)
    df["pup_end"] = ~df["persistent_up"]
    df["rsi_d3"] = df["rsi"] - df["rsi"].shift(3)
    # peak_v2: rsi crossed below 70 from above, with recent >=70 within 10 bars
    df["rsi_max10"] = df["rsi"].rolling(10).max()
    df["rsi_was_ob10"] = df["rsi_max10"] >= 70
    df["rsi_cross_down_70"] = (df["rsi"] < 70) & (df["rsi"].shift(1) >= 70)
    df["peak_v2"] = df["rsi_was_ob10"] & df["rsi_cross_down_70"]
    return df


def simulate(df: pd.DataFrame, entry_filter: str, exit_logic: str, sl_atr_mul: float | None = None) -> dict:
    cl = df["Close"].values
    hi = df["High"].values
    lo = df["Low"].values
    a_atr = df["atr"].values
    r = df["rsi"].values
    rsid3 = df["rsi_d3"].values
    ps = df["pup_start"].values
    pe = df["pup_end"].values
    peak = df["peak_v2"].values
    n = len(df)

    pnl = []
    durs = []
    reasons = []
    in_pos = False
    ent_i = -1
    ent_px = 0.0
    ent_atr = 0.0
    peak_extreme = 0.0

    for i in range(n):
        if not in_pos:
            if ps[i]:
                # entry filter check
                if entry_filter == "F0":
                    ok = True
                elif entry_filter == "F1":
                    ok = (not np.isnan(rsid3[i])) and rsid3[i] > 0
                elif entry_filter == "F2":
                    ok = (not np.isnan(rsid3[i])) and rsid3[i] > 3 and r[i] >= 65
                else:
                    ok = True
                if ok:
                    in_pos = True
                    ent_i = i
                    ent_px = cl[i]
                    ent_atr = a_atr[i]
                    peak_extreme = hi[i]
        else:
            close_now = False
            reason = ""
            # initial SL check first (priority)
            if sl_atr_mul is not None and lo[i] <= ent_px - sl_atr_mul * ent_atr:
                close_now = True; reason = "SL"
                exit_px = ent_px - sl_atr_mul * ent_atr
            else:
                # exit logic
                if exit_logic == "E0":
                    if pe[i]:
                        close_now = True; reason = "pup_end"; exit_px = cl[i]
                elif exit_logic == "E1":
                    if peak[i]:
                        close_now = True; reason = "peak_v2"; exit_px = cl[i]
                    elif pe[i]:
                        close_now = True; reason = "pup_end_fb"; exit_px = cl[i]
                elif exit_logic == "E2":
                    # ATR trail 0.5x off rolling high since entry
                    if hi[i] > peak_extreme:
                        peak_extreme = hi[i]
                    trail_px = peak_extreme - 0.5 * ent_atr
                    if lo[i] <= trail_px:
                        close_now = True; reason = "trail"; exit_px = trail_px
                    elif pe[i]:
                        close_now = True; reason = "pup_end_fb"; exit_px = cl[i]
            if close_now:
                p = (exit_px - ent_px) / 0.0001
                pnl.append(p); durs.append(i - ent_i); reasons.append(reason)
                in_pos = False

    arr = np.array(pnl)
    if len(arr) == 0:
        return {"N": 0, "sum": 0, "mean": np.nan, "wr": np.nan, "pf": np.nan, "meanDur": np.nan, "maxDD": np.nan, "reasons": {}}
    cum = arr.cumsum()
    dd = cum - np.maximum.accumulate(cum)
    wins = arr[arr > 0].sum(); losses = -arr[arr < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")
    return {
        "N": len(arr), "sum": arr.sum(), "mean": arr.mean(),
        "wr": (arr > 0).mean() * 100, "pf": pf,
        "meanDur": np.mean(durs), "maxDD": dd.min(),
        "reasons": pd.Series(reasons).value_counts().to_dict(),
    }


def main():
    df = prepare()
    print(f"=== EUR_USD M15 filter×exit×SL grid BT ===")
    print(f"bars: {len(df):,}  pup_start events: {int(df['pup_start'].sum())}")

    rows = []
    for f in ["F0", "F1", "F2"]:
        for e in ["E0", "E1", "E2"]:
            for sl in [None, 1.5]:
                res = simulate(df, f, e, sl)
                rows.append((f, e, "S0" if sl is None else f"S1({sl})", res))

    print(f"\n{'F':<3} {'E':<3} {'SL':<8} {'N':>4} {'sum':>8} {'mean':>7} {'WR%':>6} {'PF':>6} {'maxDD':>7} {'dur':>5}")
    print("-" * 70)
    for f, e, sl, r in rows:
        if r["N"] == 0:
            print(f"{f:<3} {e:<3} {sl:<8} 0")
            continue
        print(f"{f:<3} {e:<3} {sl:<8} {r['N']:>4} {r['sum']:>+8.0f} {r['mean']:>+7.2f} {r['wr']:>6.1f} {r['pf']:>6.3f} {r['maxDD']:>+7.0f} {r['meanDur']:>5.0f}")

    # Highlight survivors PF > 1.0
    survivors = [(f, e, sl, r) for f, e, sl, r in rows if r["N"] > 0 and r["pf"] > 1.0]
    print(f"\n=== Survivors (PF > 1.0): {len(survivors)} / {len(rows)} ===")
    for f, e, sl, r in survivors:
        print(f"  {f}+{e}+{sl}  N={r['N']}  sum={r['sum']:+.0f}p  mean={r['mean']:+.2f}p  WR={r['wr']:.1f}%  PF={r['pf']:.3f}  reasons={r['reasons']}")


if __name__ == "__main__":
    main()
