"""Confidence structural audit — Q4 paradox investigation (2026-04-22).

Goal: identify WHICH (strategy × regime × direction × conf-quartile) cells
show WR inversion (Q4 < Q2/Q3), and quantify the magnitude with Wilson
CI + Fisher p. This gives the target list for confidence formula review.

Protocol-compliant: Shadow only, XAU excluded, Wilson + Fisher + Bonferroni.
"""
import json, math
from collections import defaultdict
from datetime import datetime, timezone

Z = 1.96

with open("/tmp/shadow_trades.json") as f:
    data = json.load(f)
trades = [t for t in data.get("trades", [])
          if t.get("is_shadow") == 1
          and t.get("outcome") in ("WIN", "LOSS")
          and t.get("instrument") != "XAU_USD"]

# Binding edges from prereg-6-prime
CONF_EDGES = [53.0, 61.0, 69.0]
def conf_q(v):
    if v is None: return None
    try: v = float(v)
    except: return None
    if v <= CONF_EDGES[0]: return "Q1"
    if v <= CONF_EDGES[1]: return "Q2"
    if v <= CONF_EDGES[2]: return "Q3"
    return "Q4"

def wilson(k, n, z=Z):
    if n == 0: return (0.0, 1.0)
    p = k/n; den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    h = z*math.sqrt((p*(1-p) + z*z/(4*n))/n) / den
    return (max(0,c-h), min(1,c+h))

def fisher(a,b,c,d):
    from math import lgamma, exp
    def lnC(n,k):
        if k<0 or k>n: return float("-inf")
        return lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1)
    nr1=a+b; nr2=c+d; nc1=a+c; tot=a+b+c+d
    if tot==0: return 1.0
    def lnP(a_):
        b_=nr1-a_; c_=nc1-a_; d_=tot-a_-b_-c_
        if b_<0 or c_<0 or d_<0: return float("-inf")
        return lnC(nr1,a_)+lnC(nr2,c_)-lnC(tot,nc1)
    obs = lnP(a); p = 0.0
    for a_ in range(max(0, nc1-nr2), min(nr1,nc1)+1):
        lp = lnP(a_)
        if lp <= obs+1e-12: p += exp(lp)
    return min(1.0, p)

# Enrich
def parse_regime(s):
    if isinstance(s, dict): return s
    if isinstance(s, str) and s.startswith("{"):
        try: return json.loads(s)
        except: return {}
    return {}

buckets = defaultdict(lambda: {"n":0, "w":0})
overall = defaultdict(lambda: {"n":0, "w":0})
for t in trades:
    et = t.get("entry_type", "")
    rd = parse_regime(t.get("regime", ""))
    reg = rd.get("regime", "UNK")
    direction = str(t.get("direction", "")).upper()
    cq = conf_q(t.get("confidence"))
    if cq is None: continue
    w = 1 if t.get("outcome") == "WIN" else 0
    # Per-strategy × confQ
    buckets[(et, cq)]["n"] += 1
    buckets[(et, cq)]["w"] += w
    # Per-strategy × regime × confQ
    buckets[(et, reg, cq)]["n"] += 1
    buckets[(et, reg, cq)]["w"] += w
    # Overall strategy
    overall[et]["n"] += 1
    overall[et]["w"] += w

# Find inversions: strategies where WR(Q4) < WR(Q2)+5pp AND N(Q4)>=15
print("=" * 100)
print("## Strategy × Conf-Quartile: Q4 WR inversion (strategies with N(Q4)>=15)")
print("=" * 100)
print(f"{'strategy':<28} {'Q1 N/WR':>12} {'Q2 N/WR':>12} {'Q3 N/WR':>12} {'Q4 N/WR':>12}  {'Q4-Q2':>7}  inverted?")
print("-" * 100)

by_strat = defaultdict(dict)
for k, c in buckets.items():
    if len(k) != 2: continue
    et, cq = k
    if isinstance(cq, str) and cq.startswith("Q"):
        by_strat[et][cq] = c

inverted = []
for et, q in sorted(by_strat.items()):
    if overall[et]["n"] < 30: continue   # skip tiny strategies
    q4 = q.get("Q4", {"n":0,"w":0})
    if q4["n"] < 15: continue
    q2 = q.get("Q2", {"n":0,"w":0})
    wr4 = (q4["w"]/q4["n"]*100) if q4["n"] else 0
    wr2 = (q2["w"]/q2["n"]*100) if q2["n"] else 0
    delta = wr4 - wr2
    q1 = q.get("Q1", {"n":0,"w":0})
    q3 = q.get("Q3", {"n":0,"w":0})
    wr1 = (q1["w"]/q1["n"]*100) if q1["n"] else 0
    wr3 = (q3["w"]/q3["n"]*100) if q3["n"] else 0
    # inversion: Q4 WR < max(Q2,Q3) by 8pp or more
    max_mid = max(wr2, wr3)
    is_inv = (wr4 + 8 < max_mid) and (q2["n"] + q3["n"] >= 15)
    inv_mark = "★INV" if is_inv else ""
    print(f"{et:<28} {q1['n']:>3}/{wr1:>5.1f}%  {q2['n']:>3}/{wr2:>5.1f}%  {q3['n']:>3}/{wr3:>5.1f}%  {q4['n']:>3}/{wr4:>5.1f}%  {delta:>+6.1f}  {inv_mark}")
    if is_inv:
        inverted.append((et, q1, q2, q3, q4, wr1, wr2, wr3, wr4))

print(f"\n**Inverted strategies (Q4 WR < max(Q2,Q3) by ≥8pp)**: {len(inverted)}")

# Fisher p for Q4 vs (Q2+Q3) in inverted cases
print("\n" + "=" * 100)
print("## Statistical significance of inversion (Fisher exact p: Q4 vs (Q2+Q3))")
print("=" * 100)
print(f"{'strategy':<28} {'Q4 W/L':>10} {'Q2+Q3 W/L':>12} {'Fisher p':>10}  Bonf?")
print("-" * 100)
M = max(len(inverted), 1)
alpha_bonf = 0.05 / M
sig_count = 0
for et, q1, q2, q3, q4, wr1, wr2, wr3, wr4 in inverted:
    # 2x2: Q4(W,L) vs Q2+Q3(W,L)
    q4_w = q4["w"]; q4_l = q4["n"] - q4["w"]
    q23_w = q2["w"] + q3["w"]; q23_l = (q2["n"] - q2["w"]) + (q3["n"] - q3["w"])
    p = fisher(q4_w, q4_l, q23_w, q23_l)
    mark = "✓" if p < alpha_bonf else ""
    if p < alpha_bonf: sig_count += 1
    print(f"{et:<28} {q4_w:>3}/{q4_l:>3}    {q23_w:>4}/{q23_l:>4}     {p:>8.4f}  {mark}")
print(f"\nBonferroni α (M={M}) = {alpha_bonf:.4f}, inversions passing: {sig_count}/{M}")

# Regime breakdown for the top inverted strategies
print("\n" + "=" * 100)
print("## Regime breakdown for inverted strategies (where does Q4 fail?)")
print("=" * 100)
for et, *_ in inverted[:6]:
    print(f"\n### {et}")
    print(f"{'regime':<14} {'Q1 N/WR':>10} {'Q2 N/WR':>10} {'Q3 N/WR':>10} {'Q4 N/WR':>10}  note")
    print("-" * 80)
    for reg in ("TREND_BULL", "TREND_BEAR", "RANGE", "HIGH_VOL"):
        row = []
        for cq in ("Q1","Q2","Q3","Q4"):
            c = buckets.get((et, reg, cq), {"n":0,"w":0})
            n = c["n"]; w = c["w"]
            wr = (w/n*100) if n else 0
            row.append((n, wr))
        total = sum(r[0] for r in row)
        if total < 5: continue
        q4_n, q4_wr = row[3]
        q23_n = row[1][0]+row[2][0]
        q23_wr = ((buckets.get((et,reg,"Q2"),{"w":0})["w"]+buckets.get((et,reg,"Q3"),{"w":0})["w"])/q23_n*100) if q23_n else 0
        note = ""
        if q4_n >= 5 and q23_n >= 5 and q4_wr + 8 < q23_wr:
            note = f"★ Q4 drop: {q4_wr:.1f}% vs Q2+Q3={q23_wr:.1f}%"
        print(f"{reg:<14} {row[0][0]:>3}/{row[0][1]:>5.1f}%  {row[1][0]:>3}/{row[1][1]:>5.1f}%  {row[2][0]:>3}/{row[2][1]:>5.1f}%  {row[3][0]:>3}/{row[3][1]:>5.1f}%  {note}")

print("\n" + "=" * 100)
print(f"TOTAL: {len(trades)} shadow trades analyzed")
print("=" * 100)
