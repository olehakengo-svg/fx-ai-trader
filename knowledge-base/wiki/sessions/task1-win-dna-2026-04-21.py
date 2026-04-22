#!/usr/bin/env python3
"""Task 1 — WHY did TP-hit trades TP-hit?

Per strategy, characterize the WIN trades' feature DNA:
  - Likelihood ratio LR(v) = P(feat=v | WIN) / P(feat=v | LOSS)
  - Mutual information I(outcome; feature)
  - 2-way conjunction (f1=v1) ∧ (f2=v2) as WIN signature
  - Walk-forward reproducibility (pre- vs post-Cutoff)
  - Fisher exact p + Bonferroni

Output: per-strategy WIN DNA report with math.
"""
import json, math
from collections import defaultdict, Counter
from datetime import datetime, timezone

CUTOFF = datetime(2026, 4, 16, tzinfo=timezone.utc)
Z = 1.96

def parse_dt(s):
    try: return datetime.fromisoformat(s.replace("Z","+00:00"))
    except: return None

def session_of(dt):
    if not dt: return None
    h = dt.hour
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

def quartile(v, edges):
    """edges = [q1, q2, q3]; return Q1/Q2/Q3/Q4"""
    if v is None: return None
    if v <= edges[0]: return "Q1"
    if v <= edges[1]: return "Q2"
    if v <= edges[2]: return "Q3"
    return "Q4"

def compute_quartile_edges(values):
    s = sorted(v for v in values if v is not None)
    if len(s) < 12: return None
    n = len(s)
    return [s[n//4], s[n//2], s[3*n//4]]

def enrich(t):
    d = dict(t); dt = parse_dt(t.get("entry_time",""))
    d["_session"] = session_of(dt)
    d["_hour"] = dt.hour if dt else None
    d["_hour_band"] = hour_band(dt.hour if dt else None)
    d["_post_cutoff"] = dt is not None and dt >= CUTOFF
    # parse regime json
    rj = t.get("regime","")
    if isinstance(rj, str) and rj.startswith("{"):
        try:
            rd = json.loads(rj)
            for k in ("adx","atr_ratio","close_vs_ema200"):
                v = rd.get(k)
                if v is not None:
                    try: d[f"rj_{k}"] = float(v)
                    except: pass
            d["rj_hmm_regime"] = rd.get("hmm_regime")
            d["rj_ema_stack_bull"] = rd.get("ema_stack_bull")
            d["rj_ema_stack_bear"] = rd.get("ema_stack_bear")
        except: pass
    # conf/spread numeric
    for k in ("confidence", "spread_at_entry"):
        v = t.get(k)
        if v is not None:
            try: d[f"_{k}_num"] = float(v)
            except: pass
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

def entropy(p):
    if p <= 0 or p >= 1: return 0.0
    return -p*math.log2(p) - (1-p)*math.log2(1-p)

def mutual_info(trades, feat_key):
    """I(outcome; feature) = H(outcome) - Σ_v P(v) * H(outcome|v)"""
    vals = [t.get(feat_key) for t in trades if t.get(feat_key) is not None]
    if not vals: return 0.0, 0
    n = len(vals)
    w_total = sum(1 for t in trades if t.get(feat_key) is not None and t["outcome"]=="WIN")
    p_w = w_total / n if n else 0
    H_O = entropy(p_w)
    by_val = defaultdict(lambda: {"n":0,"w":0})
    for t in trades:
        v = t.get(feat_key)
        if v is None: continue
        by_val[v]["n"] += 1
        if t["outcome"]=="WIN": by_val[v]["w"] += 1
    cond_H = 0.0
    for v, c in by_val.items():
        if c["n"] == 0: continue
        p_v = c["n"]/n
        p_w_given_v = c["w"]/c["n"]
        cond_H += p_v * entropy(p_w_given_v)
    return H_O - cond_H, n

def pct(x, d=1):
    if x is None: return "-"
    if x == float("inf"): return "∞"
    return f"{100*x:.{d}f}%"

def main():
    raw = json.load(open("/tmp/shadow_trades.json"))
    trades_all = raw if isinstance(raw, list) else raw.get("trades", [])
    shadow = [enrich(t) for t in trades_all
              if t.get("is_shadow") == 1
              and t.get("outcome") in ("WIN","LOSS")
              and t.get("instrument") != "XAU_USD"]

    # Compute GLOBAL quartile edges for universally-available numeric features
    conf_edges = compute_quartile_edges([t.get("_confidence_num") for t in shadow])
    spread_edges = compute_quartile_edges([t.get("_spread_at_entry_num") for t in shadow])
    adx_edges = compute_quartile_edges([t.get("rj_adx") for t in shadow])
    atr_edges = compute_quartile_edges([t.get("rj_atr_ratio") for t in shadow])
    cvema_edges = compute_quartile_edges([t.get("rj_close_vs_ema200") for t in shadow])

    # Apply quartile labels (global to allow cross-strategy comparability)
    for t in shadow:
        if conf_edges:   t["_conf_q"]   = quartile(t.get("_confidence_num"), conf_edges)
        if spread_edges: t["_spread_q"] = quartile(t.get("_spread_at_entry_num"), spread_edges)
        if adx_edges:    t["_adx_q"]    = quartile(t.get("rj_adx"), adx_edges)
        if atr_edges:    t["_atr_q"]    = quartile(t.get("rj_atr_ratio"), atr_edges)
        if cvema_edges:  t["_cvema_q"]  = quartile(t.get("rj_close_vs_ema200"), cvema_edges)

    # Features to mine
    FEATURES = [
        "instrument","_session","_hour_band","direction",
        "mtf_regime","mtf_vol_state","mtf_alignment","mtf_gate_action",
        "mtf_h4_label","mtf_d1_label","layer1_dir","gate_group","sr_basis",
        "rj_hmm_regime","_conf_q","_spread_q","_adx_q","_atr_q","_cvema_q",
    ]

    # Group by strategy
    by_strat = defaultdict(list)
    for t in shadow: by_strat[t.get("entry_type","?")].append(t)
    ordered = sorted(by_strat.items(), key=lambda x: -len(x[1]))

    N_TOTAL = len(shadow)
    W_TOTAL = sum(1 for t in shadow if t["outcome"]=="WIN")
    BASELINE = W_TOTAL / N_TOTAL

    # Bonferroni family size (features × avg_values × strategies)
    # Conservative: count actual (strat, feature, value) tests
    total_tests = 0
    for strat, trs in ordered:
        for f in FEATURES:
            total_tests += len(set(t.get(f) for t in trs if t.get(f) is not None))
    alpha_bonf = 0.05 / max(total_tests, 1)

    print("# Task 1 — WHY did TP-hit trades TP-hit? (WIN DNA analysis)\n")
    print(f"**As of**: 2026-04-21 (UTC), **Scope**: Shadow only, XAU 除外\n")
    print(f"- N_total = {N_TOTAL}, W = {W_TOTAL}, baseline WR = {pct(BASELINE)}")
    print(f"- Cutoff = 2026-04-16 (WF split)")
    print(f"- Total (strat × feature × value) tests: {total_tests}")
    print(f"- Bonferroni α/M = {alpha_bonf:.2e}\n")
    print(f"**凡例**: LR = P(feat=v | WIN) / P(feat=v | LOSS); LR>1 ⇒ WIN-enriched")
    print(f"MI = mutual information I(outcome; feature), bits. 高いほど outcome 予測力大")
    print(f"WR|v = P(WIN | feat=v); WF = walk-forward (pre/post cutoff WR|v)\n")
    print(f"**Global quartile edges**: conf={conf_edges}, spread={spread_edges}, adx={adx_edges}, atr_ratio={atr_edges}, close_vs_ema200={cvema_edges}\n")
    print("---\n")

    # PART 1: Per-strategy WIN DNA
    for strat, trs in ordered:
        n = len(trs); w = sum(1 for t in trs if t["outcome"]=="WIN"); l = n-w
        if w < 3: continue  # skip strategies with too few wins
        wr_s = w/n
        print(f"## {strat} (N={n}, W={w}, L={l}, WR={pct(wr_s)})\n")

        # Mutual information ranking
        mi_rows = []
        for f in FEATURES:
            mi, n_cov = mutual_info(trs, f)
            mi_rows.append((f, mi, n_cov))
        mi_rows.sort(key=lambda x: -x[1])
        print(f"### MI ranking (top 8, non-zero)\n")
        print("| Feature | I(O;F) bits | Coverage N |")
        print("|---|---:|---:|")
        shown = 0
        for f, mi, nc in mi_rows:
            if mi <= 1e-4: continue
            print(f"| {f} | {mi:.4f} | {nc} |")
            shown += 1
            if shown >= 8: break
        if shown == 0: print("| (no feature with MI > 0) | — | — |")
        print()

        # WIN-enriched feature values (all with N_win ≥ 3, filter later for display)
        print(f"### WIN-enriched feature values (top by LR × sqrt(N_win), N_win ≥ 3)\n")
        print("| Feature = value | N | N_win | WR\\|v | LR | WR_pre(N_pre) | WR_post(N_post) | Fisher p | Bonf? |")
        print("|---|---:|---:|---:|---:|---|---|---:|:---:|")
        enriched = []
        for f in FEATURES:
            by_val = defaultdict(lambda: {"n":0,"w":0,"pre_n":0,"pre_w":0,"post_n":0,"post_w":0})
            for t in trs:
                v = t.get(f)
                if v is None: continue
                by_val[v]["n"] += 1
                is_post = t.get("_post_cutoff")
                if is_post:
                    by_val[v]["post_n"] += 1
                    if t["outcome"]=="WIN": by_val[v]["post_w"] += 1
                else:
                    by_val[v]["pre_n"] += 1
                    if t["outcome"]=="WIN": by_val[v]["pre_w"] += 1
                if t["outcome"]=="WIN": by_val[v]["w"] += 1
            for v, c in by_val.items():
                if c["w"] < 3: continue
                pw = c["w"]/max(w,1)
                pl = (c["n"]-c["w"])/max(l,1)
                lr = pw/pl if pl>0 else float("inf") if pw>0 else 0
                if lr < 1.3: continue  # minimal WIN-enrichment threshold
                wrv = c["w"]/c["n"]
                # Fisher
                other_w = w - c["w"]; other_l = l - (c["n"]-c["w"])
                fp = fisher_2x2_p(c["w"], c["n"]-c["w"], other_w, other_l) if c["n"]>=3 and (n-c["n"])>=3 else None
                pre_str = f"{pct(c['pre_w']/c['pre_n'],0)}({c['pre_n']})" if c['pre_n']>0 else "-(0)"
                post_str = f"{pct(c['post_w']/c['post_n'],0)}({c['post_n']})" if c['post_n']>0 else "-(0)"
                enriched.append({"f":f,"v":v,"n":c["n"],"w":c["w"],"wrv":wrv,"lr":lr,"fp":fp,"pre":pre_str,"post":post_str,
                                "reproducible": (c['pre_n']>=3 and c['post_n']>=3 and c['pre_w']/c['pre_n']>0.35 and c['post_w']/c['post_n']>0.35)})
        enriched.sort(key=lambda x: (-x["lr"]*math.sqrt(x["n"]), -x["n"]))
        for e in enriched[:15]:
            fp = f"{e['fp']:.4f}" if e['fp'] is not None else "-"
            bonf = "✓" if (e['fp'] is not None and e['fp'] < alpha_bonf) else "✗"
            print(f"| {e['f']} = {e['v']} | {e['n']} | {e['w']} | {pct(e['wrv'])} | {e['lr']:.2f} | {e['pre']} | {e['post']} | {fp} | {bonf} |")
        if not enriched: print("| (no LR≥1.3 with N_win≥3 — WIN-DNA 皆無) | | | | | | | | |")

        # Reproducibility test: which enriched features survive pre&post cutoff
        repro = [e for e in enriched if e["reproducible"]]
        if repro:
            print(f"\n**再現性通過 (pre&post Cutoff どちらも WR>35%)**: {len(repro)} features")
            for e in repro[:5]:
                print(f"  - `{e['f']}={e['v']}` — LR={e['lr']:.2f}, pre/post WR = {e['pre']}/{e['post']}")
        else:
            print(f"\n**再現性通過**: 0 (WF split で維持される WIN-enriched feature なし)")

        # 2-way conjunction mining
        print(f"\n### 2-way conjunction (WIN signature候補, N_win≥3, conditional WR≥40%)\n")
        print("| Feature1=v1 ∧ Feature2=v2 | N | N_win | WR\\|AND | LR_AND | WF pre/post | 判定 |")
        print("|---|---:|---:|---:|---:|---|:---:|")
        # take top 5 WIN-enriched features and do pairwise conjunctions
        top_feats = [(e["f"], e["v"]) for e in enriched[:6]]
        conjs = []
        for i in range(len(top_feats)):
            for j in range(i+1, len(top_feats)):
                f1, v1 = top_feats[i]; f2, v2 = top_feats[j]
                if f1 == f2: continue
                matching = [t for t in trs if t.get(f1)==v1 and t.get(f2)==v2]
                nn = len(matching); ww = sum(1 for t in matching if t["outcome"]=="WIN")
                if ww < 3: continue
                wrv = ww/nn
                if wrv < 0.40: continue
                # LR for AND
                pw = ww/max(w,1); pl = (nn-ww)/max(l,1)
                lr = pw/pl if pl>0 else float("inf") if pw>0 else 0
                # WF
                pre_matching = [t for t in matching if not t.get("_post_cutoff")]
                post_matching = [t for t in matching if t.get("_post_cutoff")]
                pre_n = len(pre_matching); pre_w = sum(1 for t in pre_matching if t["outcome"]=="WIN")
                post_n = len(post_matching); post_w = sum(1 for t in post_matching if t["outcome"]=="WIN")
                pre_str = f"{pct(pre_w/pre_n,0)}({pre_n})" if pre_n>0 else "-(0)"
                post_str = f"{pct(post_w/post_n,0)}({post_n})" if post_n>0 else "-(0)"
                verdict = ""
                if pre_n>=3 and post_n>=3:
                    if pre_w/pre_n > 0.4 and post_w/post_n > 0.4: verdict = "再現"
                    elif (pre_w/pre_n > 0.4) ^ (post_w/post_n > 0.4): verdict = "片側のみ"
                    else: verdict = "不成立"
                else:
                    verdict = "WF N不足"
                conjs.append({"f1":f1,"v1":v1,"f2":f2,"v2":v2,"n":nn,"w":ww,"wrv":wrv,"lr":lr,
                             "pre":pre_str,"post":post_str,"verdict":verdict})
        conjs.sort(key=lambda x: (-x["wrv"]*math.sqrt(x["w"]), -x["lr"]))
        for c in conjs[:8]:
            print(f"| {c['f1']}={c['v1']} ∧ {c['f2']}={c['v2']} | {c['n']} | {c['w']} | {pct(c['wrv'])} | {c['lr']:.2f} | {c['pre']}/{c['post']} | {c['verdict']} |")
        if not conjs: print("| (no 2-way conjunction with WR|AND≥40% and N_win≥3) | | | | | | |")
        print("\n---\n")

    # PART 2: Cross-strategy MI ranking
    print("\n## Cross-strategy: どの特徴が outcome を最も説明するか?\n")
    print("全 Shadow trades 集計での I(outcome; feature)")
    print("| Feature | I(O;F) bits | Coverage N | Relative |")
    print("|---|---:|---:|---:|")
    global_mi = []
    H_O = entropy(BASELINE)
    for f in FEATURES:
        mi, nc = mutual_info(shadow, f)
        global_mi.append((f, mi, nc))
    global_mi.sort(key=lambda x: -x[1])
    for f, mi, nc in global_mi:
        rel = mi/H_O if H_O>0 else 0
        print(f"| {f} | {mi:.4f} | {nc} | {100*rel:.2f}% |")
    print(f"\nH(outcome) baseline = {H_O:.4f} bits. 各特徴が outcome entropy を何%削減するか")

if __name__ == "__main__":
    main()
