#!/usr/bin/env python3
"""Virtual Filter Simulation — 6 new PRIME strategies.

Apply each PRIME fire condition to the current shadow data and verify:
  - N_observed (shadow)
  - WR, PF, EV, Kelly, Wilson CI
  - pre/post Cutoff split
  - Fisher exact p
  - fire rate (coverage of parent strategy trades)

Use GLOBAL quartile edges that match task1_why_tp.py for reproducibility.
"""
import json, math
from collections import defaultdict
from datetime import datetime, timezone

CUTOFF = datetime(2026, 4, 16, tzinfo=timezone.utc)
Z = 1.96

# Global quartile edges (from task1_why_tp.py output)
EDGES = {
    "conf":   [53.0, 61.0, 69.0],     # confidence (percent)
    "spread": [0.8, 0.8, 0.8],
    "adx":    [20.3, 25.3, 31.7],
    "atr":    [0.95, 1.01, 1.09],
    "cvema":  [-0.019, 0.001, 0.034],
}

def q(v, edges):
    if v is None: return None
    if v <= edges[0]: return "Q1"
    if v <= edges[1]: return "Q2"
    if v <= edges[2]: return "Q3"
    return "Q4"

def parse_dt(s):
    try: return datetime.fromisoformat(s.replace("Z","+00:00"))
    except: return None

def session_of(h):
    if 0 <= h < 8: return "tokyo"
    if 8 <= h < 13: return "london"
    if 13 <= h < 22: return "ny"
    return "offhours"

def hour_band(h):
    if h is None: return None
    if h < 4: return "00-03"
    if h < 8: return "04-07"
    if h < 12: return "08-11"
    if h < 16: return "12-15"
    if h < 20: return "16-19"
    return "20-23"

def enrich(t):
    d = dict(t); dt = parse_dt(t.get("entry_time",""))
    if dt:
        d["_session"] = session_of(dt.hour)
        d["_hour"] = dt.hour
        d["_hour_band"] = hour_band(dt.hour)
        d["_post_cutoff"] = dt >= CUTOFF
    rj = t.get("regime","")
    rj_d = {}
    if isinstance(rj, str) and rj.startswith("{"):
        try: rj_d = json.loads(rj)
        except: pass
    for k in ("adx","atr_ratio","close_vs_ema200"):
        v = rj_d.get(k)
        if v is not None:
            try: d[f"rj_{k}"] = float(v)
            except: pass
    # quartile labels
    conf = t.get("confidence")
    try: conf = float(conf) if conf is not None else None
    except: conf = None
    d["_conf_q"]  = q(conf, EDGES["conf"])
    d["_atr_q"]   = q(d.get("rj_atr_ratio"), EDGES["atr"])
    d["_adx_q"]   = q(d.get("rj_adx"), EDGES["adx"])
    d["_cvema_q"] = q(d.get("rj_close_vs_ema200"), EDGES["cvema"])
    try: d["_pnl"] = float(t.get("pnl_pips")) if t.get("pnl_pips") is not None else None
    except: d["_pnl"] = None
    return d

def wilson_ci(k, n, z=Z):
    if n == 0: return (0.0, 1.0)
    p = k/n; den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    h = z * math.sqrt((p*(1-p) + z*z/(4*n))/n) / den
    return (max(0, c-h), min(1, c+h))

def fisher_2x2_p(a,b,c,d):
    from math import lgamma, exp
    def lnC(n,k):
        if k<0 or k>n: return float("-inf")
        return lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1)
    nr1=a+b; nr2=c+d; nc1=a+c; nc2=b+d; tot=a+b+c+d
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

def pct(x, d=1):
    if x is None: return "-"
    return f"{100*x:.{d}f}%"

# 6 PRIME strategy specs (pre-register)
PRIMES = [
    {
        "name": "stoch_trend_pullback_PRIME",
        "base": "stoch_trend_pullback",
        "conditions": [("_atr_q", "Q1"), ("direction", "BUY")],
        "human": "ATR_ratio Q1 (≤0.95) AND direction=BUY",
    },
    {
        "name": "stoch_trend_pullback_LONDON_LOWVOL",
        "base": "stoch_trend_pullback",
        "conditions": [("_atr_q", "Q1"), ("_session", "london")],
        "human": "ATR_ratio Q1 (≤0.95) AND session=london",
    },
    {
        "name": "fib_reversal_PRIME",
        "base": "fib_reversal",
        "conditions": [("_conf_q", "Q3"), ("_cvema_q", "Q3")],
        "human": "confidence Q3 (61-69) AND close_vs_ema200 Q3 (0.001-0.034)",
    },
    {
        "name": "bb_rsi_reversion_NY_ATRQ2",
        "base": "bb_rsi_reversion",
        "conditions": [("_hour_band", "12-15"), ("_atr_q", "Q2")],
        "human": "hour_band 12-15 UTC AND ATR_ratio Q2 (0.95-1.01)",
    },
    {
        "name": "engulfing_bb_TOKYO_EARLY",
        "base": "engulfing_bb",
        "conditions": [("_session", "tokyo"), ("_hour_band", "00-03")],
        "human": "session=tokyo AND hour_band 00-03 UTC",
    },
    {
        "name": "sr_fib_confluence_GBP_ADXQ2",
        "base": "sr_fib_confluence",
        "conditions": [("instrument", "GBP_USD"), ("_adx_q", "Q2")],
        "human": "instrument=GBP_USD AND ADX Q2 (20.3-25.3)",
    },
]

def match(t, conds):
    for f, v in conds:
        if t.get(f) != v: return False
    return True

def cell_metrics(trades):
    n = len(trades); w = sum(1 for t in trades if t["outcome"]=="WIN"); l = n-w
    if n == 0: return None
    pnls = [t["_pnl"] for t in trades if t["_pnl"] is not None]
    wins_p = [p for p in pnls if p > 0]
    losses_p = [p for p in pnls if p < 0]
    sum_w = sum(wins_p); sum_l = abs(sum(losses_p))
    pf = sum_w/sum_l if sum_l > 0 else (float("inf") if sum_w > 0 else 0)
    ev = sum(pnls)/len(pnls) if pnls else 0
    avg_w = sum_w/len(wins_p) if wins_p else 0
    avg_l = sum_l/len(losses_p) if losses_p else 0
    payoff = avg_w/avg_l if avg_l > 0 else (float("inf") if avg_w > 0 else 0)
    wr = w/n
    kelly = wr - (1-wr)/payoff if (payoff > 0 and payoff != float("inf")) else (wr if payoff == float("inf") else -1)
    lo, hi = wilson_ci(w, n)
    return {
        "n":n,"w":w,"l":l,"wr":wr,"pf":pf,"ev":ev,"payoff":payoff,"kelly":kelly,
        "wilson_lo":lo,"wilson_hi":hi,"avg_w":avg_w,"avg_l":avg_l,
    }

def main():
    raw = json.load(open("/tmp/shadow_trades.json"))
    trades_all = raw if isinstance(raw, list) else raw.get("trades", [])
    shadow = [enrich(t) for t in trades_all
              if t.get("is_shadow")==1 and t.get("outcome") in ("WIN","LOSS")
              and t.get("instrument") != "XAU_USD"]

    by_strat = defaultdict(list)
    for t in shadow: by_strat[t.get("entry_type","?")].append(t)

    # Bonferroni family size (only PRIME tests)
    alpha_bonf = 0.05 / len(PRIMES)

    print("# Virtual Filter Simulation — 6 PRIME Strategies\n")
    print(f"**As of**: 2026-04-21 (UTC), **Scope**: Shadow only, XAU 除外")
    print(f"**Bonferroni α/M** (M={len(PRIMES)} PRIMEs only): {alpha_bonf:.4f}")
    print(f"**Global quartile edges**: {EDGES}\n")
    print("---\n")

    summary_rows = []
    for p in PRIMES:
        base = p["base"]
        parent = by_strat.get(base, [])
        if not parent:
            print(f"## {p['name']}\n\n**base = {base}**: Shadow data ゼロ. SKIP.\n\n---\n")
            continue
        parent_n = len(parent)
        parent_w = sum(1 for t in parent if t["outcome"]=="WIN")
        parent_wr = parent_w/parent_n

        matched = [t for t in parent if match(t, p["conditions"])]
        m = cell_metrics(matched)

        # Fisher p vs non-matched within parent
        non = [t for t in parent if not match(t, p["conditions"])]
        non_n = len(non); non_w = sum(1 for t in non if t["outcome"]=="WIN")
        fp = fisher_2x2_p(m["w"], m["n"]-m["w"], non_w, non_n-non_w) if m["n"]>=5 and non_n>=5 else None
        bonf_ok = fp is not None and fp < alpha_bonf

        # Walk-forward
        pre = [t for t in matched if not t.get("_post_cutoff")]
        post = [t for t in matched if t.get("_post_cutoff")]
        pre_m = cell_metrics(pre) if pre else None
        post_m = cell_metrics(post) if post else None

        fire_rate = m["n"]/parent_n

        print(f"## {p['name']}\n")
        print(f"- **Base**: {base} (Shadow N={parent_n}, WR={pct(parent_wr)})")
        print(f"- **Fire condition**: {p['human']}")
        print(f"- **Condition key**: `{p['conditions']}`\n")
        print(f"### Virtual sim (all shadow)\n")
        print(f"| N | W | L | WR | Wilson下限 | Lift | PF | EV(pips) | Payoff | Kelly | Fire rate | Fisher p | Bonf? |")
        print(f"|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|")
        lift = m["wr"]/parent_wr if parent_wr > 0 else float("inf")
        fp_str = f"{fp:.4f}" if fp is not None else "-"
        bonf_str = "✓" if bonf_ok else "✗"
        pf_str = "∞" if m["pf"]==float("inf") else f"{m['pf']:.2f}"
        payoff_str = "∞" if m["payoff"]==float("inf") else f"{m['payoff']:.2f}"
        print(f"| {m['n']} | {m['w']} | {m['l']} | {pct(m['wr'])} | {pct(m['wilson_lo'])} | {lift:.2f}x | {pf_str} | {m['ev']:+.2f} | {payoff_str} | {pct(m['kelly'])} | {100*fire_rate:.1f}% | {fp_str} | {bonf_str} |\n")

        print(f"### Walk-forward split\n")
        print(f"| Period | N | W | WR | PF | EV(pips) |")
        print(f"|---|---:|---:|---:|---:|---:|")
        for label, x in [("pre-Cutoff", pre_m), ("post-Cutoff", post_m)]:
            if x is None:
                print(f"| {label} | 0 | 0 | - | - | - |")
            else:
                pfs = "∞" if x["pf"]==float("inf") else f"{x['pf']:.2f}"
                print(f"| {label} | {x['n']} | {x['w']} | {pct(x['wr'])} | {pfs} | {x['ev']:+.2f} |")
        print()

        # Decision per pre-reg logic
        repro = (pre_m is not None and post_m is not None
                 and pre_m["n"]>=3 and post_m["n"]>=3
                 and pre_m["wr"]>0.40 and post_m["wr"]>0.40)
        ev_pos = m["ev"] > 0
        pf_ok = m["pf"] > 1.0
        verdict_parts = []
        if ev_pos: verdict_parts.append("EV+")
        else: verdict_parts.append("EV-")
        if pf_ok: verdict_parts.append("PF>1")
        else: verdict_parts.append("PF≤1")
        if repro: verdict_parts.append("WF再現")
        else: verdict_parts.append("WF未確認")
        if bonf_ok: verdict_parts.append("Bonf有意")
        else: verdict_parts.append("Bonf非有意")
        verdict = " / ".join(verdict_parts)
        print(f"### Verdict: **{verdict}**\n")

        # Save for summary
        summary_rows.append({
            "name": p["name"], "base": base,
            "n": m["n"], "wr": m["wr"], "wilson_lo": m["wilson_lo"],
            "pf": m["pf"], "ev": m["ev"], "payoff": m["payoff"], "kelly": m["kelly"],
            "fire_rate": fire_rate, "fisher_p": fp, "bonf_ok": bonf_ok,
            "pre_n": pre_m["n"] if pre_m else 0, "pre_wr": pre_m["wr"] if pre_m else None,
            "post_n": post_m["n"] if post_m else 0, "post_wr": post_m["wr"] if post_m else None,
            "ev_pos": ev_pos, "pf_ok": pf_ok, "repro": repro,
        })
        print("---\n")

    # Summary table
    print("\n## Virtual Sim Summary\n")
    print("| Strategy | N | WR | Wilson下限 | PF | EV | Kelly | pre/post WR | Fisher p | Bonf? | EV+ | PF>1 | WF再現 |")
    print("|---|---:|---:|---:|---:|---:|---:|---|---:|:---:|:---:|:---:|:---:|")
    for s in summary_rows:
        pre = f"{pct(s['pre_wr'],0)}({s['pre_n']})" if s['pre_wr'] is not None else "-(0)"
        post = f"{pct(s['post_wr'],0)}({s['post_n']})" if s['post_wr'] is not None else "-(0)"
        pf_str = "∞" if s['pf']==float("inf") else f"{s['pf']:.2f}"
        fp_str = f"{s['fisher_p']:.4f}" if s['fisher_p'] is not None else "-"
        print(f"| {s['name']} | {s['n']} | {pct(s['wr'])} | {pct(s['wilson_lo'])} | {pf_str} | {s['ev']:+.2f} | {pct(s['kelly'])} | {pre}/{post} | {fp_str} | {'✓' if s['bonf_ok'] else '✗'} | {'✓' if s['ev_pos'] else '✗'} | {'✓' if s['pf_ok'] else '✗'} | {'✓' if s['repro'] else '✗'} |")

    # Save JSON for downstream
    import json as _j
    with open("/tmp/virtual_sim_6.json","w") as f:
        _j.dump([{**s, "pf": s["pf"] if s["pf"]!=float("inf") else None,
                  "payoff": s["payoff"] if s["payoff"]!=float("inf") else None}
                 for s in summary_rows], f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
