#!/usr/bin/env python3
"""EUR_USD M15 entry RSI trajectory diagnostic.

At each pup_start (entry), measure RSI delta over previous N bars.
Split trades by win/loss (using pup_end exit) to see if losers indeed have
falling RSI at entry.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "data/cache/massive"


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def atr(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0); dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1 / n, adjust=False).mean() / dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + rs)


def run(start="2025-07-01", end="2026-05-05", max_gap=10):
    df = pd.read_parquet(CACHE / "EUR_USD_15m.parquet").loc[start:end].copy()
    c = df["Close"]
    df["ema_fast"] = ema(c, 25); df["ema_mid"] = ema(c, 75); df["ema_slow"] = ema(c, 200)
    df["atr"] = atr(df, 14); df["rsi"] = rsi(c, 14)
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

    # Simulate trades with pup_end exit, record entry context
    cl = df["Close"].values; r = df["rsi"].values
    ps = df["pup_start"].values; pe = df["pup_end"].values
    trades = []
    in_pos = False; ent_i = -1; ent_px = 0.0
    for i in range(len(df)):
        if not in_pos:
            if ps[i]:
                in_pos = True; ent_i = i; ent_px = cl[i]
        else:
            if pe[i]:
                p_pips = (cl[i] - ent_px) / 0.0001
                rsi_now = r[ent_i]
                rsi_1 = r[ent_i - 1] if ent_i >= 1 else np.nan
                rsi_3 = r[ent_i - 3] if ent_i >= 3 else np.nan
                rsi_5 = r[ent_i - 5] if ent_i >= 5 else np.nan
                rsi_10 = r[ent_i - 10] if ent_i >= 10 else np.nan
                trades.append({
                    "pnl_pips": p_pips,
                    "rsi_at_entry": rsi_now,
                    "rsi_d1": rsi_now - rsi_1,
                    "rsi_d3": rsi_now - rsi_3,
                    "rsi_d5": rsi_now - rsi_5,
                    "rsi_d10": rsi_now - rsi_10,
                    "duration": i - ent_i,
                })
                in_pos = False
    t = pd.DataFrame(trades)
    print(f"=== EUR_USD M15 entry-RSI trajectory diag ({start}→{end}, max_gap={max_gap}) ===")
    print(f"trades: {len(t)} | sum={t['pnl_pips'].sum():+.0f}p | mean={t['pnl_pips'].mean():+.2f}p | WR={(t['pnl_pips']>0).mean()*100:.1f}%")
    print(f"\n=== Win vs Loss: entry RSI trajectory ===")
    wins = t[t["pnl_pips"] > 0]; losses = t[t["pnl_pips"] <= 0]
    for grp, name in [(wins, "WINS"), (losses, "LOSSES")]:
        print(f"  {name}  N={len(grp):3d}")
        for k in ["rsi_at_entry", "rsi_d1", "rsi_d3", "rsi_d5", "rsi_d10", "duration"]:
            print(f"    {k:15s} mean={grp[k].mean():+7.2f}  median={grp[k].median():+7.2f}")

    # bucketize rsi_d3 (3-bar momentum at entry)
    print(f"\n=== rsi_d3 (RSI change over 3 bars before entry) bucket → P&L ===")
    bins = [-50, -3, -1, 1, 3, 50]
    labels = ["d3<-3 (steep drop)", "d3 -3~-1", "d3 -1~1 (flat)", "d3 1~3", "d3>3 (steep rise)"]
    t["rsi_d3_bin"] = pd.cut(t["rsi_d3"], bins=bins, labels=labels)
    grp = t.groupby("rsi_d3_bin", observed=True)["pnl_pips"]
    print(f"{'bucket':<22} {'N':>4} {'sum':>8} {'mean':>8} {'WR%':>6}")
    for name, sub in grp:
        wr = (sub > 0).mean() * 100
        print(f"{str(name):<22} {len(sub):>4} {sub.sum():>+8.0f} {sub.mean():>+8.2f} {wr:>6.1f}")

    # rsi_at_entry bucket
    print(f"\n=== rsi_at_entry bucket → P&L ===")
    bins2 = [0, 50, 55, 60, 65, 70, 100]
    labels2 = ["<50", "50-55", "55-60", "60-65", "65-70", ">=70"]
    t["rsi_e_bin"] = pd.cut(t["rsi_at_entry"], bins=bins2, labels=labels2)
    grp2 = t.groupby("rsi_e_bin", observed=True)["pnl_pips"]
    print(f"{'bucket':<10} {'N':>4} {'sum':>8} {'mean':>8} {'WR%':>6}")
    for name, sub in grp2:
        wr = (sub > 0).mean() * 100
        print(f"{str(name):<10} {len(sub):>4} {sub.sum():>+8.0f} {sub.mean():>+8.2f} {wr:>6.1f}")

    # Combined rsi_d3>0 (rising) filter result
    rising = t[t["rsi_d3"] > 0]
    falling = t[t["rsi_d3"] <= 0]
    print(f"\n=== Entry filter test: rsi_d3 > 0 (RSI rising over 3 bars) ===")
    for grp, name in [(rising, "RISING"), (falling, "FALLING")]:
        if len(grp) == 0: continue
        wins_p = grp[grp["pnl_pips"] > 0]["pnl_pips"].sum()
        loss_p = -grp[grp["pnl_pips"] <= 0]["pnl_pips"].sum()
        pf = wins_p / loss_p if loss_p > 0 else float("inf")
        wr = (grp["pnl_pips"] > 0).mean() * 100
        print(f"  {name:<8} N={len(grp):3d}  sum={grp['pnl_pips'].sum():+.0f}p  mean={grp['pnl_pips'].mean():+.2f}p  WR={wr:.1f}%  PF={pf:.3f}")


if __name__ == "__main__":
    run()
