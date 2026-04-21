#!/usr/bin/env python3
"""Task 1 DEEP — Shadow TP-hit 条件を完全クオンツ視点で抽出.

追加指標:
  - PF (profit factor) = Σwin_pips / |Σloss_pips|
  - EV (expected pnl per trade, pips)
  - Payoff ratio = avg_win / avg_loss
  - Walk-forward: pre-Cutoff (<2026-04-16) vs post-Cutoff
  - Kelly fraction = WR - (1-WR)/payoff
  - Wilson 95% CI
  - Fisher exact p
  - Bonferroni: α/M where M=探索空間
  - Hour-level clustering within top session

出力: 全 44 戦略 × (pair × session × direction) の cell 詳細.
対象: Shadow only, XAU 除外, outcome in WIN/LOSS.
"""
import json, math, sys
from collections import defaultdict, Counter
from datetime import datetime, timezone

CUTOFF = datetime(2026, 4, 16, tzinfo=timezone.utc)
Z = 1.96
BEV_WR = {"USD_JPY":0.344,"EUR_JPY":0.344,"GBP_JPY":0.344,
          "EUR_USD":0.360,"GBP_USD":0.360,"EUR_GBP":0.360}
BEV_DEFAULT = 0.360

def parse_dt(s):
    try: return datetime.fromisoformat(s.replace("Z","+00:00"))
    except: return None

def session_of(dt):
    if not dt: return "unknown"
    h = dt.hour
    if 0 <= h < 8: return "tokyo"
    if 8 <= h < 13: return "london"
    if 13 <= h < 22: return "ny"
    return "offhours"

def enrich(t):
    d = dict(t); dt = parse_dt(t.get("entry_time",""))
    d["_session"] = session_of(dt); d["_hour"] = dt.hour if dt else None
    d["_dt"] = dt
    d["_post_cutoff"] = (dt is not None and dt >= CUTOFF)
    # pnl_pips can be None; coerce
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

def summarize_cell(trades):
    """Compute cell-level quant metrics from list of enriched trades."""
    n = len(trades)
    if n == 0: return None
    wins = [t for t in trades if t["outcome"]=="WIN"]
    losses = [t for t in trades if t["outcome"]=="LOSS"]
    w = len(wins); l = len(losses)
    wr = w/n if n else 0
    # pnl metrics (exclude None)
    pnls = [t["_pnl"] for t in trades if t["_pnl"] is not None]
    win_pnls = [t["_pnl"] for t in wins if t["_pnl"] is not None]
    loss_pnls = [t["_pnl"] for t in losses if t["_pnl"] is not None]
    sum_win = sum(p for p in win_pnls if p > 0)
    sum_loss = abs(sum(p for p in loss_pnls if p < 0))
    pf = (sum_win / sum_loss) if sum_loss > 0 else (float("inf") if sum_win > 0 else 0)
    ev = (sum(pnls)/len(pnls)) if pnls else 0
    avg_win = (sum(p for p in win_pnls if p > 0)/max(1, sum(1 for p in win_pnls if p > 0))) if win_pnls else 0
    avg_loss = (abs(sum(p for p in loss_pnls if p < 0))/max(1, sum(1 for p in loss_pnls if p < 0))) if loss_pnls else 0
    payoff = (avg_win / avg_loss) if avg_loss > 0 else (float("inf") if avg_win > 0 else 0)
    # Kelly (classic): f = WR - (1-WR)/payoff
    kelly = wr - (1-wr)/payoff if payoff > 0 and payoff != float("inf") else (wr if payoff == float("inf") else -1)
    wilson_lo, wilson_hi = wilson_ci(w, n)
    # Walk-forward counts
    pre = [t for t in trades if not t["_post_cutoff"]]
    post = [t for t in trades if t["_post_cutoff"]]
    pre_w = sum(1 for t in pre if t["outcome"]=="WIN")
    post_w = sum(1 for t in post if t["outcome"]=="WIN")
    return {
        "n": n, "w": w, "l": l, "wr": wr,
        "pf": pf, "ev": ev, "payoff": payoff, "kelly": kelly,
        "wilson_lo": wilson_lo, "wilson_hi": wilson_hi,
        "avg_win": avg_win, "avg_loss": avg_loss,
        "sum_win": sum_win, "sum_loss": sum_loss,
        "n_pre": len(pre), "w_pre": pre_w,
        "wr_pre": pre_w/max(1,len(pre)),
        "n_post": len(post), "w_post": post_w,
        "wr_post": post_w/max(1,len(post)),
    }

def pct(x, d=1):
    if x is None: return "-"
    if x == float("inf"): return "∞"
    return f"{100*x:.{d}f}%"

def fmt_pf(x):
    if x == float("inf"): return "∞"
    return f"{x:.2f}"

def fmt_ev(x):
    return f"{x:+.2f}"

def main():
    raw = json.load(open("/tmp/shadow_trades.json"))
    trades_all = raw if isinstance(raw, list) else raw.get("trades", [])
    shadow = [enrich(t) for t in trades_all
              if t.get("is_shadow") == 1
              and t.get("outcome") in ("WIN","LOSS")
              and t.get("instrument") != "XAU_USD"]
    N = len(shadow); W = sum(1 for t in shadow if t["outcome"]=="WIN")
    baseline_wr = W/N
    by_strat = defaultdict(list)
    for t in shadow: by_strat[t.get("entry_type","?")].append(t)

    # Bonferroni family size
    pairs = sorted(set(t["instrument"] for t in shadow))
    sessions = ["tokyo","london","ny","offhours"]
    directions = ["BUY","SELL"]
    M = len(by_strat) * len(pairs) * len(sessions) * len(directions)
    alpha_bonf = 0.05 / M

    print(f"# Task 1 DEEP — Shadow TP-hit 条件詳細分析 (クオンツ再集計)\n")
    print(f"**As of**: 2026-04-21 (UTC), **Scope**: Shadow only (is_shadow=1), XAU 除外, outcome ∈ {{WIN, LOSS}}\n")
    print(f"- N_total = {N}, W = {W}, baseline WR = **{100*baseline_wr:.2f}%**")
    print(f"- Distinct strategies = {len(by_strat)}")
    print(f"- Cutoff = 2026-04-16 (v9.2.1 regime populated)")
    print(f"- Bonferroni: M = {len(by_strat)} strats × {len(pairs)} pairs × {len(sessions)} sessions × {len(directions)} dirs = **{M} cells**")
    print(f"- Bonferroni α = 0.05/{M} = **{alpha_bonf:.2e}**\n")
    print("**凡例**: N=trades, WR=勝率, PF=profit factor (Σwin_pips/|Σloss_pips|), EV=平均pips/trade, Payoff=avg_win/avg_loss, Kelly=f*=WR-(1-WR)/payoff, Wilson=95% CI下限, Lift=WR_cell/WR_strat_base, p_F=Fisher exact p, WF=walk-forward pre/post Cutoff\n")
    print("---\n")

    # Tier classification for reporting depth
    # L1: N ≥ 50; L2: 20-49; L3: 5-19; L4: <5
    ordered = sorted(by_strat.items(), key=lambda x: -len(x[1]))

    for strat, trs in ordered:
        n = len(trs); w = sum(1 for t in trs if t["outcome"]=="WIN"); l = n-w
        if n < 5:
            continue  # will report L4 at end
        s = summarize_cell(trs)
        tier = "L1" if n>=50 else ("L2" if n>=20 else "L3")
        print(f"## {strat} ({tier}: N={n}, W={w}, L={l}, WR={pct(s['wr'])}, PF={fmt_pf(s['pf'])}, EV={fmt_ev(s['ev'])}pips, Payoff={fmt_pf(s['payoff'])}, Kelly={pct(s['kelly'])})\n")
        print(f"- Walk-forward: pre-Cutoff N={s['n_pre']} WR={pct(s['wr_pre'])} | post-Cutoff N={s['n_post']} WR={pct(s['wr_post'])}")
        base_wr_strat = s["wr"]

        # Enumerate cells
        cells = defaultdict(list)
        for t in trs:
            cells[(t.get("instrument","?"), t.get("_session","?"), t.get("direction","?"))].append(t)
        rows = []
        for key, ts in cells.items():
            if len(ts) < 3: continue
            cs = summarize_cell(ts)
            # Lift vs strategy baseline
            lift = cs["wr"] / base_wr_strat if base_wr_strat > 0 else float("inf") if cs["wr"] > 0 else 0
            # Fisher exact vs rest of this strategy
            cell_w = cs["w"]; cell_l = cs["l"]
            other_w = w - cell_w; other_l = l - cell_l
            fp = fisher_2x2_p(cell_w, cell_l, other_w, other_l) if cs["n"]>=5 and (n-cs["n"])>=5 else None
            bev = BEV_WR.get(key[0], BEV_DEFAULT)
            rows.append((key, cs, lift, fp, bev))

        # Only print cells with WR > strategy baseline OR PF > 1 OR N >= 10 (to keep focused on winners)
        print(f"\n### {strat} — Cell-level profile (N≥3, sorted by WR desc)\n")
        print("| Cell (pair×sess×dir) | N | WR | Wilson下限 | Lift | PF | EV | Payoff | Kelly | WF pre/post WR | p_F | Bonf? |")
        print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|:---:|")
        rows.sort(key=lambda x: (-x[1]["wr"], -x[1]["n"]))
        shown = 0
        for key, cs, lift, fp, bev in rows:
            cell_str = f"{key[0]}×{key[1]}×{key[2]}"
            wf = f"{pct(cs['wr_pre'],0)}({cs['n_pre']})/{pct(cs['wr_post'],0)}({cs['n_post']})"
            pstr = f"{fp:.4f}" if fp is not None else "-"
            bonf_ok = "✓" if (fp is not None and fp < alpha_bonf) else "✗"
            print(f"| {cell_str} | {cs['n']} | {pct(cs['wr'])} | {pct(cs['wilson_lo'])} | {lift:.2f}x | {fmt_pf(cs['pf'])} | {fmt_ev(cs['ev'])} | {fmt_pf(cs['payoff'])} | {pct(cs['kelly'])} | {wf} | {pstr} | {bonf_ok} |")
            shown += 1
            if shown >= 12 and tier != "L1": break
            if shown >= 20: break

        # L1 only: hour-level clustering in TOP (N >=10) session × pair × direction
        if tier == "L1":
            # find top cell with N >= 8
            cand = [(k,c) for (k,c,_,_,_) in rows if c["n"] >= 8 and c["wr"] >= base_wr_strat*1.2]
            if cand:
                key, cs = max(cand, key=lambda x: x[1]["wr"] * math.sqrt(x[1]["n"]))
                hour_cells = defaultdict(lambda: {"n":0,"w":0})
                for t in trs:
                    if (t.get("instrument"), t.get("_session"), t.get("direction")) == key:
                        h = t.get("_hour")
                        if h is None: continue
                        hour_cells[h]["n"] += 1
                        if t["outcome"]=="WIN": hour_cells[h]["w"] += 1
                print(f"\n#### Hour-level clustering inside top cell [{key[0]}×{key[1]}×{key[2]}]\n")
                print("| Hour UTC | N | W | WR |")
                print("|---:|---:|---:|---:|")
                for h in sorted(hour_cells.keys()):
                    c = hour_cells[h]
                    print(f"| {h:02d} | {c['n']} | {c['w']} | {pct(c['w']/c['n'])} |")

        print("\n---\n")

    # Summary: which cells, if any, beat Bonferroni
    print("\n## Bonferroni-significant cells (p < α/M)\n")
    print(f"α/M = {alpha_bonf:.2e} (M = {M} cells)\n")
    print("| Strategy | Cell | N | WR | p_F | ΔWR vs baseline |")
    print("|---|---|---:|---:|---:|---:|")
    any_sig = False
    for strat, trs in ordered:
        n = len(trs); w = sum(1 for t in trs if t["outcome"]=="WIN"); l = n-w
        if n < 10: continue
        cells = defaultdict(list)
        for t in trs:
            cells[(t.get("instrument","?"), t.get("_session","?"), t.get("direction","?"))].append(t)
        base_wr = w/n
        for key, ts in cells.items():
            if len(ts) < 5: continue
            cw = sum(1 for t in ts if t["outcome"]=="WIN"); cl = len(ts)-cw
            ow = w-cw; ol = l-cl
            if ow<5 or ol<5: continue
            fp = fisher_2x2_p(cw, cl, ow, ol)
            if fp < alpha_bonf:
                cell_str = f"{key[0]}×{key[1]}×{key[2]}"
                wr = cw/len(ts)
                print(f"| {strat} | {cell_str} | {len(ts)} | {pct(wr)} | {fp:.2e} | {100*(wr-base_wr):+.1f}pp |")
                any_sig = True
    if not any_sig:
        print("| — | — | — | — | — | — |")
        print("\n**結論**: Bonferroni-strict 基準 (α/M={:.2e}) で有意な cell は **ゼロ**. 全ての 'golden cell' は multiple-testing artifact の可能性.".format(alpha_bonf))

if __name__ == "__main__":
    main()
