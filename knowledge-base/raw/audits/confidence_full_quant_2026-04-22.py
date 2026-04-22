"""Confidence Q4 Paradox — FULL-QUANT re-analysis (2026-04-22).

Fixes the partial-quant trap of confidence-q4-paradox-2026-04-22.md:
computes PF, EV, Kelly, Payoff, Wilson CI, conditional BEV_WR,
Walk-Forward (pre/post-Cutoff), Mutual Information, Bonferroni with the
correct family size, Odds Ratio, Cohen's h, and a BUY-bias Fisher test.

Protocol:
  - Shadow only (is_shadow=1), XAU excluded
  - Cutoff = 2026-04-16 for Walk-Forward split
  - Bonferroni family M = 44 strategies × 4 conf-quartiles = 176 cells
    (corrected from the post-hoc M=4 in the earlier doc)
  - Kelly Half for position sizing decisions
  - Fisher exact (two-sided) for each cell vs non-Q4 of same strategy
"""
import json, math
from collections import defaultdict
from datetime import datetime, timezone

Z = 1.96
CUTOFF = datetime(2026, 4, 16, tzinfo=timezone.utc)

with open("/tmp/shadow_trades.json") as f:
    data = json.load(f)
trades = [t for t in data.get("trades", [])
          if t.get("is_shadow") == 1
          and t.get("outcome") in ("WIN", "LOSS")
          and t.get("instrument") != "XAU_USD"
          and t.get("pnl_pips") is not None]
print(f"# N = {len(trades)} (shadow, closed, pnl_pips not null)")

CONF_EDGES = [53.0, 61.0, 69.0]
ADX_EDGES = [20.3, 25.3, 31.7]
ATR_EDGES = [0.95, 1.01, 1.09]
CVEMA_EDGES = [-0.019, 0.001, 0.034]

def quartile(v, edges):
    if v is None: return None
    try: v = float(v)
    except: return None
    if v <= edges[0]: return "Q1"
    if v <= edges[1]: return "Q2"
    if v <= edges[2]: return "Q3"
    return "Q4"

def parse_regime(s):
    if isinstance(s, dict): return s
    if isinstance(s, str) and s.startswith("{"):
        try: return json.loads(s)
        except: return {}
    return {}

def parse_dt(s):
    if not s: return None
    try: return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc)
    except: return None

def wilson(k, n, z=Z):
    if n == 0: return (0.0, 1.0)
    p = k/n; den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    h = z*math.sqrt((p*(1-p) + z*z/(4*n))/n) / den
    return (max(0,c-h), min(1,c+h))

def fisher_two_sided(a,b,c,d):
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

def cohens_h(p1, p2):
    """Cohen's h = 2*arcsin(sqrt(p1)) - 2*arcsin(sqrt(p2)).
    Magnitude: small=0.2, medium=0.5, large=0.8."""
    def phi(p):
        p = max(0.0, min(1.0, p))
        return 2*math.asin(math.sqrt(p))
    return phi(p1) - phi(p2)

def odds_ratio(a, b, c, d):
    """OR = (a/b) / (c/d)."""
    if b == 0 or c == 0 or d == 0:
        return None
    return (a*d) / (b*c)

def entropy(p):
    if p <= 0 or p >= 1: return 0.0
    return -p*math.log2(p) - (1-p)*math.log2(1-p)

def compute_cell_metrics(cell_trades):
    """Returns dict with N, WR, PF, EV, Payoff, BEV_WR, edge, Kelly, Wilson."""
    n = len(cell_trades)
    if n == 0:
        return None
    wins = [t for t in cell_trades if t["outcome"] == "WIN"]
    losses = [t for t in cell_trades if t["outcome"] == "LOSS"]
    w = len(wins); l = len(losses)
    wr = w/n if n else 0
    win_pips = [float(t["pnl_pips"]) for t in wins if t.get("pnl_pips") is not None]
    loss_pips = [float(t["pnl_pips"]) for t in losses if t.get("pnl_pips") is not None]
    avg_win = (sum(win_pips)/len(win_pips)) if win_pips else 0.0
    avg_loss = (sum(loss_pips)/len(loss_pips)) if loss_pips else 0.0  # negative
    sum_win = sum(win_pips)
    sum_loss_abs = abs(sum(loss_pips))
    pf = (sum_win / sum_loss_abs) if sum_loss_abs > 0 else (float("inf") if sum_win > 0 else 0.0)
    ev = (sum_win + sum(loss_pips)) / n if n else 0.0
    payoff = (avg_win / abs(avg_loss)) if avg_loss < 0 else (float("inf") if avg_win > 0 else 0.0)
    bev_wr = (1.0 / (1.0 + payoff)) if payoff > 0 and payoff != float("inf") else 0.0
    edge = wr - bev_wr
    # Kelly (full): f* = WR - (1-WR)/payoff
    kelly = wr - (1 - wr)/payoff if payoff > 0 and payoff != float("inf") else 0.0
    kelly_half = kelly / 2.0
    ci_lo, ci_hi = wilson(w, n)
    return {
        "n": n, "w": w, "l": l, "wr": wr,
        "avg_win": avg_win, "avg_loss": avg_loss,
        "sum_win": sum_win, "sum_loss": sum(loss_pips),
        "pf": pf, "ev": ev, "payoff": payoff,
        "bev_wr": bev_wr, "edge": edge,
        "kelly": kelly, "kelly_half": kelly_half,
        "wilson_lo": ci_lo, "wilson_hi": ci_hi,
    }

# Enrich
for t in trades:
    t["_conf_q"] = quartile(t.get("confidence"), CONF_EDGES)
    dt = parse_dt(t.get("entry_time",""))
    t["_dt"] = dt
    t["_post_cutoff"] = dt is not None and dt >= CUTOFF
    rd = parse_regime(t.get("regime",""))
    t["_regime"] = rd.get("regime","UNK")
    t["_adx_q"] = quartile(rd.get("adx"), ADX_EDGES)
    t["_atr_q"] = quartile(rd.get("atr_ratio"), ATR_EDGES)
    t["_cvema_q"] = quartile(rd.get("close_vs_ema200"), CVEMA_EDGES)
    t["_direction"] = str(t.get("direction","")).upper()

# Bonferroni family size
strategies_with_data = sorted({t["entry_type"] for t in trades if t.get("entry_type")})
M_CELLS = len(strategies_with_data) * 4  # strat × conf-Q
ALPHA_BONF = 0.05 / M_CELLS
print(f"# Bonferroni family M = {M_CELLS} cells ({len(strategies_with_data)} strats × 4 conf-Q), α = {ALPHA_BONF:.2e}")
print()

# ════════════════════════════════════════════════════════════════════
# §1 — Full-quant metrics per (strategy × conf-Q)
# ════════════════════════════════════════════════════════════════════
print("="*140)
print("§1 FULL-QUANT: per (strategy × conf-Q) cell — Shadow 全期間")
print("="*140)
header = f"{'strategy':<24} {'Q':<3} {'N':>4} {'WR':>6} {'CI_lo':>6} {'CI_hi':>6} {'PF':>6} {'EV':>7} {'Pay':>5} {'BEV':>5} {'Edge':>6} {'Kelly':>6} {'K/2':>6}"
print(header)
print("-"*140)

cells = {}  # (strat, Q) -> metrics
for strat in strategies_with_data:
    rows = [t for t in trades if t["entry_type"] == strat]
    if len(rows) < 20: continue  # small strategy skipped
    for cq in ("Q1","Q2","Q3","Q4"):
        sub = [t for t in rows if t["_conf_q"] == cq]
        m = compute_cell_metrics(sub)
        if m is None or m["n"] < 5: continue
        cells[(strat, cq)] = m
        pf_str = f"{m['pf']:.2f}" if m['pf'] != float('inf') else "inf"
        pay_str = f"{m['payoff']:.2f}" if m['payoff'] != float('inf') else "inf"
        print(f"{strat:<24} {cq:<3} {m['n']:>4} {m['wr']*100:>5.1f}% {m['wilson_lo']*100:>5.1f}% {m['wilson_hi']*100:>5.1f}% {pf_str:>6} {m['ev']:>+6.2f} {pay_str:>5} {m['bev_wr']*100:>4.1f}% {m['edge']*100:>+5.1f}% {m['kelly']*100:>+5.1f}% {m['kelly_half']*100:>+5.1f}%")

# ════════════════════════════════════════════════════════════════════
# §2 — Q4 paradox check: for each strategy, is Q4 worse on ALL metrics?
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*140)
print("§2 Q4 PARADOX DETECTION — Q4 がその戦略の最悪 cell か (PF/EV/Kelly 同時)")
print("="*140)
print(f"{'strategy':<24} {'N_Q4':>5} {'WR_Q4':>6} {'PF_Q4':>6} {'EV_Q4':>7} {'K_Q4':>7} {'vs_all_PF':>10} {'vs_all_EV':>10} {'Kelly<0':>8} {'worst?':>8}")
print("-"*140)
q4_losers = []  # strategies where Q4 is structurally worst
for strat in strategies_with_data:
    if (strat, "Q4") not in cells: continue
    q4 = cells[(strat, "Q4")]
    others = [cells[(strat,q)] for q in ("Q1","Q2","Q3") if (strat,q) in cells]
    if not others: continue
    # Aggregate non-Q4 metrics (weighted by N)
    tot_n = sum(o["n"] for o in others)
    if tot_n < 10: continue
    agg_w = sum(o["w"] for o in others)
    agg_wr = agg_w/tot_n
    agg_win_sum = sum(o["sum_win"] for o in others)
    agg_loss_sum = sum(o["sum_loss"] for o in others)
    agg_pf = (agg_win_sum / abs(agg_loss_sum)) if agg_loss_sum < 0 else float("inf")
    agg_ev = (agg_win_sum + agg_loss_sum) / tot_n
    q4_pf = q4["pf"] if q4["pf"] != float("inf") else 999
    non_pf = agg_pf if agg_pf != float("inf") else 999
    kelly_neg = q4["kelly"] < 0
    is_worst = (q4_pf < non_pf) and (q4["ev"] < agg_ev) and kelly_neg
    mark = "★STRUCT" if is_worst else ("Kelly<0" if kelly_neg else "")
    pf_str = f"{q4['pf']:.2f}" if q4['pf']!=float('inf') else "inf"
    print(f"{strat:<24} {q4['n']:>5} {q4['wr']*100:>5.1f}% {pf_str:>6} {q4['ev']:>+6.2f} {q4['kelly']*100:>+6.1f}% {non_pf:>10.2f} {agg_ev:>+9.2f} {'Y' if kelly_neg else 'N':>8} {mark:>8}")
    if is_worst:
        q4_losers.append((strat, q4, agg_wr, agg_pf, agg_ev, tot_n, agg_w))

print(f"\n**Q4 が全指標で最悪の戦略 (PF↓ AND EV↓ AND Kelly<0): {len(q4_losers)}**")

# ════════════════════════════════════════════════════════════════════
# §3 — Fisher exact + Odds Ratio + Cohen's h + Bonferroni
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*140)
print("§3 STATISTICAL SIGNIFICANCE: Q4 vs non-Q4 of same strategy")
print(f"Bonferroni family M = {M_CELLS}, α = {ALPHA_BONF:.2e}")
print("="*140)
print(f"{'strategy':<24} {'Q4 W/L':>9} {'non-Q4 W/L':>12} {'Fisher p':>10} {'OR':>7} {'Cohen h':>8} {'α_raw':>7} {'α_bonf':>7}")
print("-"*140)
sig_raw = 0; sig_bonf = 0; bonf_passers = []
for strat, q4, agg_wr, agg_pf, agg_ev, tot_n, agg_w in q4_losers:
    q4_w = q4["w"]; q4_l = q4["n"] - q4["w"]
    non_w = agg_w; non_l = tot_n - agg_w
    p = fisher_two_sided(q4_w, q4_l, non_w, non_l)
    or_val = odds_ratio(q4_w, q4_l, non_w, non_l)
    h = cohens_h(q4["wr"], agg_wr)
    or_str = f"{or_val:.2f}" if or_val is not None else "—"
    raw_mark = "✓" if p < 0.05 else ""
    bonf_mark = "✓" if p < ALPHA_BONF else ""
    if p < 0.05: sig_raw += 1
    if p < ALPHA_BONF:
        sig_bonf += 1
        bonf_passers.append(strat)
    print(f"{strat:<24} {q4_w:>3}/{q4_l:>3}   {non_w:>4}/{non_l:>4}     {p:>8.4f} {or_str:>7} {h:>+7.3f} {raw_mark:>7} {bonf_mark:>7}")
print(f"\nRaw p<0.05: {sig_raw}/{len(q4_losers)} | Bonferroni pass: {sig_bonf}/{len(q4_losers)}")
if bonf_passers:
    print(f"Bonferroni 有意戦略: {bonf_passers}")

# ════════════════════════════════════════════════════════════════════
# §4 — Walk-Forward: pre-Cutoff vs post-Cutoff 再現性
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*140)
print("§4 WALK-FORWARD: pre-Cutoff (~2026-04-16) vs post-Cutoff")
print("="*140)
print(f"{'strategy':<24} {'PRE Q4 N/WR/Kelly':>30} {'POST Q4 N/WR/Kelly':>30} {'pre sign':>10} {'post sign':>10} {'reproduces?':>12}")
print("-"*140)
wf_consistent = []
for strat, q4, *_ in q4_losers:
    rows = [t for t in trades if t["entry_type"] == strat]
    for phase, filt in [("PRE", lambda t: not t["_post_cutoff"]),
                         ("POST", lambda t: t["_post_cutoff"])]:
        pass
    pre_rows = [t for t in rows if not t["_post_cutoff"] and t["_conf_q"] == "Q4"]
    post_rows = [t for t in rows if t["_post_cutoff"] and t["_conf_q"] == "Q4"]
    pre_m = compute_cell_metrics(pre_rows)
    post_m = compute_cell_metrics(post_rows)
    if pre_m is None or post_m is None:
        continue
    pre_str = f"N={pre_m['n']} WR={pre_m['wr']*100:.1f}% K={pre_m['kelly']*100:+.1f}%"
    post_str = f"N={post_m['n']} WR={post_m['wr']*100:.1f}% K={post_m['kelly']*100:+.1f}%"
    pre_sign = "-" if pre_m["kelly"] < 0 else "+"
    post_sign = "-" if post_m["kelly"] < 0 else "+"
    reproduces = pre_sign == post_sign == "-"
    mark = "✓ CONSISTENT" if reproduces else ""
    if reproduces: wf_consistent.append(strat)
    print(f"{strat:<24} {pre_str:>30} {post_str:>30} {pre_sign:>10} {post_sign:>10} {mark:>12}")
print(f"\n**Walk-Forward 両期間で Kelly<0 を再現: {len(wf_consistent)} / {len(q4_losers)}**")
if wf_consistent: print(f"再現戦略: {wf_consistent}")

# ════════════════════════════════════════════════════════════════════
# §5 — Mutual Information: I(outcome; conf-Q) per strategy
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*140)
print("§5 MUTUAL INFORMATION I(outcome; conf_Q) [bits] per strategy")
print("="*140)
print(f"{'strategy':<24} {'N':>5} {'H(O)':>6} {'H(O|Q)':>7} {'MI':>7} {'MI/H(O)':>9}")
print("-"*140)
for strat in strategies_with_data:
    rows = [t for t in trades if t["entry_type"] == strat and t["_conf_q"] is not None]
    if len(rows) < 30: continue
    n = len(rows); w = sum(1 for t in rows if t["outcome"]=="WIN")
    p_w = w/n
    H_O = entropy(p_w)
    if H_O <= 0: continue
    cond_H = 0.0
    for cq in ("Q1","Q2","Q3","Q4"):
        sub = [t for t in rows if t["_conf_q"]==cq]
        if not sub: continue
        p_q = len(sub)/n
        p_w_given_q = sum(1 for t in sub if t["outcome"]=="WIN")/len(sub)
        cond_H += p_q * entropy(p_w_given_q)
    mi = H_O - cond_H
    print(f"{strat:<24} {n:>5} {H_O:>5.3f} {cond_H:>6.3f} {mi:>6.4f} {mi/H_O*100:>7.1f}%")

# ════════════════════════════════════════════════════════════════════
# §6 — ema_cross BUY-bias Fisher test
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*140)
print("§6 ASYMMETRIC BUY BIAS TEST — 4 inverted strategies")
print("="*140)
print(f"{'strategy':<24} {'conf_Q':<3} {'BUY N':>6} {'SELL N':>7} {'BUY/total':>10} {'Fisher p (vs non-Q4)':>22}")
print("-"*140)
for strat in ["ema_cross", "fib_reversal", "ema_trend_scalp", "bb_rsi_reversion"]:
    rows_all = [t for t in trades if t["entry_type"] == strat]
    for cq in ("Q1","Q2","Q3","Q4"):
        sub = [t for t in rows_all if t["_conf_q"]==cq]
        if len(sub) < 5: continue
        b = sum(1 for t in sub if t["_direction"]=="BUY")
        s = sum(1 for t in sub if t["_direction"]=="SELL")
        tot = b+s
        if tot == 0: continue
        buy_pct = b/tot*100
        if cq == "Q4":
            # Fisher vs non-Q4 BUY proportion
            non = [t for t in rows_all if t["_conf_q"] in ("Q1","Q2","Q3")]
            non_b = sum(1 for t in non if t["_direction"]=="BUY")
            non_s = sum(1 for t in non if t["_direction"]=="SELL")
            p = fisher_two_sided(b, s, non_b, non_s)
            p_str = f"{p:.4f}"
            bonf_mark = "  ✓ (Bonf-4)" if p < 0.05/4 else ""
            print(f"{strat:<24} {cq:<3} {b:>6} {s:>7} {buy_pct:>9.1f}%    p={p_str}{bonf_mark}")
        else:
            print(f"{strat:<24} {cq:<3} {b:>6} {s:>7} {buy_pct:>9.1f}%    —")

# ════════════════════════════════════════════════════════════════════
# §7 — Kelly-based gate proposal
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*140)
print("§7 KELLY-BASED GATE PROPOSAL (Option A refinement)")
print("="*140)
print("Rule: ShadowGate if ALL: (Kelly < 0) AND (Wilson 95% upper < BEV_WR) AND (N ≥ 15)")
print("-"*140)
print(f"{'strategy':<24} {'N':>4} {'WR':>6} {'Wilson_hi':>10} {'BEV':>5} {'Kelly':>7} {'条件':>12} {'verdict':>10}")
print("-"*140)
gate_action = []
for strat, q4, *_ in q4_losers:
    k_neg = q4["kelly"] < 0
    ci_below_bev = q4["wilson_hi"] < q4["bev_wr"]
    n_ok = q4["n"] >= 15
    verdict = "SHADOW" if (k_neg and ci_below_bev and n_ok) else ("WATCH" if k_neg else "KEEP")
    conds = f"{'K<0' if k_neg else '—'}+{'CI<BEV' if ci_below_bev else '—'}+{'N≥15' if n_ok else '—'}"
    print(f"{strat:<24} {q4['n']:>4} {q4['wr']*100:>5.1f}% {q4['wilson_hi']*100:>9.1f}% {q4['bev_wr']*100:>4.1f}% {q4['kelly']*100:>+6.1f}% {conds:>12} {verdict:>10}")
    if verdict == "SHADOW":
        gate_action.append((strat, q4))

print(f"\n**Binding gate 候補: {len(gate_action)} 戦略**")
for strat, q4 in gate_action:
    est_pips_saved = -q4["ev"] * q4["n"] * 1.0   # ev is negative, loss per trade
    print(f"  - {strat} Q4: N={q4['n']} Kelly={q4['kelly']*100:+.1f}% EV={q4['ev']:+.2f}pip → 排除で ~{est_pips_saved:+.1f}pip/month 救済推定")
