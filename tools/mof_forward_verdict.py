#!/usr/bin/env python3
"""MoF forward pre-reg (台帳 #4) verdict — 凍結仕様の機械適用。
Spec: knowledge-base/wiki/decisions/mof-intervention-forward-prereg-2026-07-24.md (LOCKED 2026-07-24)
"""
import json
from datetime import date
from math import comb

import pandas as pd

P15 = "/Users/jg-n-012/test/fx-ai-trader/data/cache/massive/USD_JPY_15m.parquet"
D_DISCLOSED = [date(2026, 4, 30), date(2026, 5, 4), date(2026, 5, 6)]  # MoF 2026-08-07 開示
S_FROZEN = [date(2026, 4, 30), date(2026, 5, 6)]
WIN = (date(2026, 4, 28), date(2026, 5, 27))
X_FROZEN, Y_FROZEN = 2.0, 0.25  # rule: co_ret <= -Y% and range >= X * trailing20 median range
PIP = 0.01

df = pd.read_parquet(P15)
df = df[["Open", "High", "Low", "Close"]]
df["day"] = [t.date() for t in df.index]  # UTC-day 集計 (凍結)
day = df.groupby("day").agg(Open=("Open", "first"), High=("High", "max"),
                            Low=("Low", "min"), Close=("Close", "last"))
day = day[[d.weekday() < 5 for d in day.index]]
day["range"] = day.High - day.Low
day["co_ret"] = day.Close / day.Open - 1.0
day["trail_med_range"] = day["range"].rolling(20).median().shift(1)

days = list(day.index)
def next_bd(d):
    i = days.index(d) if d in days else None
    if i is None:
        # roll to next existing data day
        later = [x for x in days if x > d]
        return later[0]
    return days[i + 1]

# --- population M (frozen: 21 business days in window, 05-07 missing excluded)
pop = [d for d in days if WIN[0] <= d <= WIN[1]]
print(f"population days in window = {len(pop)} (frozen M=21)")
assert date(2026, 5, 7) not in pop, "05-07 should be missing"

# --- rule regeneration on 2026 window (single application, frozen params)
def candidates(x, y):
    out = []
    for d in pop:
        r = day.loc[d]
        if r.co_ret <= -y / 100.0 and r.range >= x * r.trail_med_range:
            out.append(d)
    return out

S_regen = candidates(X_FROZEN, Y_FROZEN)
print("S regenerated:", S_regen, "| frozen:", S_FROZEN, "| match:", S_regen == S_FROZEN)

# --- E-A hypergeometric
k_eff = len([d for d in D_DISCLOSED if d in pop])
overlap = len(set(S_FROZEN) & set(D_DISCLOSED))
M, s = len(pop), len(S_FROZEN)
def hyper_p_ge(ov, M, s, k):
    # P(|S ∩ D| >= ov), D uniform k of M, S fixed size s
    tot = comb(M, k)
    p = sum(comb(s, j) * comb(M - s, k - j) for j in range(ov, min(s, k) + 1)) / tot
    return p
pA = hyper_p_ge(overlap, M, s, k_eff)
print(f"E-A: k_eff={k_eff} overlap={overlap} p={pA:.4f} -> {'PASS' if (overlap >= 2 and pA <= 0.10) or (k_eff == 1 and overlap >= 1) else 'FAIL'}")

# --- E-C: net_h from anchor t0(d) = next data business day (per-day)
bars = df  # 15m bars with .index timestamps
def first_bar_open(d):
    sub = bars[[t == d for t in bars["day"]]]
    return sub["Open"].iloc[0], sub.index[0]

def bd_offset(d, h):
    i = days.index(d)
    return days[i + h]

rows = []
for ev in D_DISCLOSED:
    anchor_day = next_bd(ev)
    p0, t0 = first_bar_open(anchor_day)
    row = {"event": str(ev), "anchor": str(anchor_day), "p0": float(p0)}
    for h in (1, 2, 5, 10):
        dh = bd_offset(anchor_day, h)
        ph, _ = first_bar_open(dh)
        row[f"net_h{h}"] = round((ph - p0) / PIP, 1)  # SELL 有利 = 負
    # MFE/MAE over [t0, t0+10bd] for SELL
    dend = bd_offset(anchor_day, 10)
    seg = bars[(bars.index >= t0) & ([t < dend for t in bars["day"]])]
    row["mfe_sell_h10"] = round((p0 - seg["Low"].min()) / PIP, 1)
    row["mae_sell_h10"] = round((seg["High"].max() - p0) / PIP, 1)
    rows.append(row)

nets10 = sorted(r["net_h10"] for r in rows)
med10 = nets10[len(nets10) // 2]
print(json.dumps(rows, indent=1))
print(f"E-C: median net_h10 = {med10}p (予測符号 = 負/SELL、band [-319.8,-43.6]) -> {'PASS' if med10 < 0 else 'FAIL'}")
for h in (1, 2, 5):
    ns = sorted(r[f"net_h{h}"] for r in rows)
    print(f"  adjacent h{h}: median {ns[len(ns)//2]}")

# --- §8.3 rule perturbation ±20%
for lbl, x, y in [("X-20%", 1.6, 0.25), ("X+20%", 2.4, 0.25), ("Y-20%", 2.0, 0.20), ("Y+20%", 2.0, 0.30)]:
    print(f"perturb {lbl}: candidates = {candidates(x, y)}")

# --- §8.1 mechanism decomposition for S days
for d in S_FROZEN:
    r = day.loc[d]
    print(f"{d}: co_ret={r.co_ret*100:.2f}% (<= -0.25%: {r.co_ret <= -0.0025}), "
      f"range={r.range/PIP:.0f}p vs 2.0x trail_med={2.0*r.trail_med_range/PIP:.0f}p: {r.range >= 2.0*r.trail_med_range}")
# 05-04 (miss) decomposition
r = day.loc[date(2026, 5, 4)]
print(f"2026-05-04 (S 外の介入日): co_ret={r.co_ret*100:.2f}%, range={r.range/PIP:.0f}p, "
      f"2.0x trail_med={2.0*r.trail_med_range/PIP:.0f}p")
