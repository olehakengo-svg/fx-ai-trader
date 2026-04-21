#!/usr/bin/env python3
"""Shadow Deep Analysis — Tasks 1-4 from handover-shadow-deep-analysis-2026-04-21.

Scope:
  - Shadow only (is_shadow=1) with outcome in WIN/LOSS
  - Exclude XAU_USD (user memory: feedback_exclude_xau)
  - Axis: instrument x session x direction (REQUIRED per memory)
  - Stats: N, WR, Wilson CI, Lift, LR, Fisher p (where N permits)

Outputs:
  - Deliverable 1: All-strategy TOP WIN cell table
  - Deliverable 2: Branch 1 gate-pass list (promotion candidates)
  - Deliverable 3: Branch 2 loss-to-win conversion judgement (per strategy)
  - Deliverable 4: Per-strategy SL fingerprint (LOSS top 3)
  - Deliverable 5: Binding pre-registration text
"""
import json, math, sys
from collections import defaultdict, Counter
from datetime import datetime, timezone

SHADOW_JSON = "/tmp/shadow_trades.json"

# Break-Even WR per pair (from prior friction analysis, conservative JPY=34.4%, non-JPY=36%)
BEV_WR = {
    "USD_JPY": 0.344, "EUR_JPY": 0.344, "GBP_JPY": 0.344,
    "EUR_USD": 0.360, "GBP_USD": 0.360, "EUR_GBP": 0.360,
}
BEV_DEFAULT = 0.360

Z = 1.96  # 95% CI

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
    d = dict(t)
    dt = parse_dt(t.get("entry_time",""))
    d["_session"] = session_of(dt)
    d["_hour"] = dt.hour if dt else None
    # parse regime json for rj features
    rj = t.get("regime","")
    if isinstance(rj, str) and rj.startswith("{"):
        try:
            rd = json.loads(rj)
            for k in ("adx","atr_ratio","close_vs_ema200"):
                v = rd.get(k)
                if v is not None: d[f"rj_{k}"] = float(v)
            d["rj_hmm_regime"] = rd.get("hmm_regime","?")
        except: pass
    return d

def wilson_ci(k, n, z=Z):
    if n == 0: return (0.0, 1.0)
    p = k/n
    den = 1 + z*z/n
    c = (p + z*z/(2*n)) / den
    h = z * math.sqrt((p*(1-p) + z*z/(4*n))/n) / den
    return (max(0, c-h), min(1, c+h))

def fisher_2x2_p(a, b, c, d):
    # Fisher exact p (two-sided) without scipy
    # a=cell_WIN, b=cell_LOSS, c=other_WIN, d=other_LOSS
    from math import lgamma, exp
    def lnC(n,k):
        if k<0 or k>n: return float("-inf")
        return lgamma(n+1)-lgamma(k+1)-lgamma(n-k+1)
    n_row1 = a+b; n_row2 = c+d
    n_col1 = a+c; n_col2 = b+d
    total = a+b+c+d
    if total == 0: return 1.0
    def lnP(a_):
        b_ = n_row1 - a_; c_ = n_col1 - a_; d_ = total - a_ - b_ - c_
        if b_<0 or c_<0 or d_<0: return float("-inf")
        return lnC(n_row1,a_) + lnC(n_row2,c_) - lnC(total,n_col1)
    obs = lnP(a)
    p = 0.0
    for a_ in range(max(0, n_col1-n_row2), min(n_row1, n_col1)+1):
        lp = lnP(a_)
        if lp <= obs + 1e-12:
            p += exp(lp)
    return min(1.0, p)

def pct(x): return f"{100*x:.1f}%" if x is not None else "-"

def main():
    raw = json.load(open(SHADOW_JSON))
    trades_all = raw if isinstance(raw, list) else raw.get("trades", [])
    # Filter: shadow, outcome, exclude XAU
    shadow = [enrich(t) for t in trades_all
              if t.get("is_shadow") == 1
              and t.get("outcome") in ("WIN","LOSS")
              and t.get("instrument") != "XAU_USD"]
    N_total = len(shadow)
    N_win = sum(1 for t in shadow if t["outcome"] == "WIN")
    baseline_WR = N_win / N_total if N_total else 0
    print(f"# Shadow Deep Analysis (Tasks 1-4)\n")
    print(f"- Total shadow trades (is_shadow=1, outcome, XAU excluded): **{N_total}**")
    print(f"- WIN: {N_win}, LOSS: {N_total-N_win}")
    print(f"- Baseline WR: **{100*baseline_WR:.2f}%**\n")

    # Group by strategy
    by_strat = defaultdict(list)
    for t in shadow:
        by_strat[t.get("entry_type","?")].append(t)
    print(f"- Distinct strategies with shadow data: **{len(by_strat)}**\n")

    # ==== Per-strategy analysis ====
    results = []
    for strat, trs in sorted(by_strat.items(), key=lambda x: -len(x[1])):
        n = len(trs)
        w = sum(1 for t in trs if t["outcome"] == "WIN")
        wr = w/n
        # Enumerate pair x session x direction cells
        cells = defaultdict(lambda: {"n":0, "w":0})
        for t in trs:
            key = (t.get("instrument","?"), t.get("_session","?"), t.get("direction","?"))
            cells[key]["n"] += 1
            if t["outcome"] == "WIN": cells[key]["w"] += 1

        # WIN cells (top by WR with N>=3) — Task 1
        win_cells = []
        for key, c in cells.items():
            if c["n"] < 3: continue
            cell_wr = c["w"]/c["n"]
            lift = cell_wr / wr if wr > 0 else float("inf") if cell_wr > 0 else 0
            wilson_lo, wilson_hi = wilson_ci(c["w"], c["n"])
            bev = BEV_WR.get(key[0], BEV_DEFAULT)
            # LR: P(cell|WIN)/P(cell|LOSS)
            # where cell membership is "this instrument x session x direction"
            cell_win = c["w"]; cell_loss = c["n"] - c["w"]
            other_win = w - cell_win; other_loss = (n-w) - cell_loss
            pw = cell_win / max(w, 1)
            pl = cell_loss / max(n-w, 1)
            lr = pw / pl if pl > 0 else float("inf") if pw > 0 else 0
            # Fisher p (only when reasonable)
            fp = None
            if c["n"] >= 5 and n-c["n"] >= 5:
                fp = fisher_2x2_p(cell_win, cell_loss, other_win, other_loss)
            win_cells.append({
                "cell": key, "n": c["n"], "wr": cell_wr, "lift": lift,
                "wilson_lo": wilson_lo, "wilson_hi": wilson_hi,
                "lr": lr, "fisher_p": fp, "bev": bev,
                "w": cell_win, "l": cell_loss,
            })
        win_cells.sort(key=lambda x: (-x["wr"], -x["n"]))

        # LOSS cells (Task 3): cells with high LOSS density
        loss_cells_ranked = []
        for key, c in cells.items():
            if c["n"] < 3: continue
            cell_wr = c["w"]/c["n"]
            cell_loss = c["n"] - c["w"]
            other_win = w - c["w"]; other_loss = (n-w) - cell_loss
            pw = c["w"] / max(w, 1)
            pl = cell_loss / max(n-w, 1)
            loss_lr = pl / pw if pw > 0 else float("inf") if pl > 0 else 0
            loss_cells_ranked.append({
                "cell": key, "n": c["n"], "wr": cell_wr, "loss_lr": loss_lr,
                "w": c["w"], "l": cell_loss,
            })
        # Rank by loss concentration: low WR + large N
        loss_cells_ranked.sort(key=lambda x: (x["wr"], -x["n"]))

        # ==== Task 4 Branch 2: LOSS exclusion filter ====
        # Criteria for LOSS cell to exclude: cell_wr <= 0.15 AND loss_lr >= 2.0 AND N>=5
        exclude_cells = []
        for lc in loss_cells_ranked:
            if lc["wr"] <= 0.15 and lc["loss_lr"] >= 2.0 and lc["n"] >= 5:
                exclude_cells.append(lc["cell"])
        # also soft criterion: if insufficient, use cell_wr<=0.20 AND loss_lr>=1.5 AND N>=8
        if not exclude_cells:
            for lc in loss_cells_ranked:
                if lc["wr"] <= 0.20 and lc["loss_lr"] >= 1.5 and lc["n"] >= 8:
                    exclude_cells.append(lc["cell"])

        # Apply filter (conservative OR)
        surviving = [t for t in trs
                     if (t.get("instrument"), t.get("_session"), t.get("direction")) not in exclude_cells]
        n_post = len(surviving)
        w_post = sum(1 for t in surviving if t["outcome"] == "WIN")
        wr_post = w_post/n_post if n_post else 0
        wilson_post_lo, _ = wilson_ci(w_post, n_post)

        # Branch 2 verdict
        if n_post >= 30 and wr_post >= 0.50 and wilson_post_lo > 0.35:
            verdict = "NEW_STRATEGY"
        elif n_post >= 20 and wr_post >= 0.50:
            verdict = "NEW_STRATEGY_TENTATIVE"
        elif n_post >= 30 and wr_post >= 0.40:
            verdict = "MARGINAL_IMPROVEMENT"
        elif wr_post < 0.40 and n_post >= 30:
            verdict = "UNSALVAGEABLE"
        elif n_post < 20:
            verdict = "INSUFFICIENT_N_POST"
        else:
            verdict = "NEEDS_MORE_DATA"

        results.append({
            "strat": strat, "n": n, "w": w, "wr": wr,
            "win_cells": win_cells, "loss_cells": loss_cells_ranked,
            "exclude_cells": exclude_cells,
            "n_post": n_post, "w_post": w_post, "wr_post": wr_post,
            "wilson_post_lo": wilson_post_lo,
            "verdict": verdict,
        })

    # ==== Deliverable 1: TOP WIN cell per strategy ====
    print("## Deliverable 1: All-strategy Top WIN cell (pair \u00d7 session \u00d7 direction)\n")
    print("| Strategy | N | WR | Top cell | cell N | cell WR | Lift | Wilson 下限 | BEV | Wilson>BEV? |")
    print("|---|---:|---:|---|---:|---:|---:|---:|---:|:---:|")
    for r in results:
        top = next((c for c in r["win_cells"] if c["n"] >= 5), (r["win_cells"][0] if r["win_cells"] else None))
        if top is None:
            print(f"| {r['strat']} | {r['n']} | {pct(r['wr'])} | - | - | - | - | - | - | - |")
            continue
        cell_str = f"{top['cell'][0]}\u00d7{top['cell'][1]}\u00d7{top['cell'][2]}"
        ok = "\u2713" if top["wilson_lo"] > top["bev"] else "\u2717"
        print(f"| {r['strat']} | {r['n']} | {pct(r['wr'])} | {cell_str} | {top['n']} | {pct(top['wr'])} | {top['lift']:.2f}x | {pct(top['wilson_lo'])} | {pct(top['bev'])} | {ok} |")

    # ==== Deliverable 2: Branch 1 gate-pass list ====
    print("\n## Deliverable 2: Branch 1 — Threshold adjustment / LIVE promotion candidates\n")
    print("Gate criteria: cell N\u226510, cell WR\u226550%, Lift\u22651.5, Wilson\u226595%\u4e0b\u9650>BEV\n")
    print("| Strategy | Cell (pair\u00d7session\u00d7dir) | N | WR | Lift | Wilson下限 | BEV | Fisher p | Pass? |")
    print("|---|---|---:|---:|---:|---:|---:|---:|:---:|")
    promotion_candidates = []
    for r in results:
        for c in r["win_cells"]:
            n_ok = c["n"] >= 10
            wr_ok = c["wr"] >= 0.50
            lift_ok = c["lift"] >= 1.5
            wilson_ok = c["wilson_lo"] > c["bev"]
            if not (n_ok and wr_ok and lift_ok): continue
            cell_str = f"{c['cell'][0]}\u00d7{c['cell'][1]}\u00d7{c['cell'][2]}"
            fp = f"{c['fisher_p']:.4f}" if c['fisher_p'] is not None else "-"
            passed = "\u2713" if (n_ok and wr_ok and lift_ok and wilson_ok) else "\u2717"
            print(f"| {r['strat']} | {cell_str} | {c['n']} | {pct(c['wr'])} | {c['lift']:.2f}x | {pct(c['wilson_lo'])} | {pct(c['bev'])} | {fp} | {passed} |")
            if n_ok and wr_ok and lift_ok and wilson_ok:
                promotion_candidates.append({"strat": r["strat"], "cell": c["cell"], "n": c["n"], "wr": c["wr"], "lift": c["lift"], "wilson_lo": c["wilson_lo"], "fp": c["fisher_p"]})
    if not promotion_candidates:
        print("\n(no cells pass all 4 gates — mostly N insufficient; continue shadow accumulation)\n")
    else:
        print(f"\n**Promotion candidates (gates passed): {len(promotion_candidates)}**\n")

    # ==== Deliverable 3: Branch 2 loss-to-win judgement (ALL 44 strategies) ====
    print("\n## Deliverable 3: Branch 2 \u2014 LOSS-exclusion \u2192 WIN conversion (ALL strategies)\n")
    print("CORE QUESTION: LOSS条件排除後の WR \u2265 50% か?\n")
    print("| Strategy | baseline N | base WR | Excluded cells | N_post | WR_post | Wilson下限 | Verdict | 新戦略名候補 |")
    print("|---|---:|---:|---|---:|---:|---:|---|---|")
    new_strategy_candidates = []
    unsalvageable = []
    for r in results:
        ex_str = ", ".join(f"{c[0]}\u00d7{c[1]}\u00d7{c[2]}" for c in r["exclude_cells"]) or "-"
        new_name = ""
        if r["verdict"] in ("NEW_STRATEGY","NEW_STRATEGY_TENTATIVE"):
            new_name = f"{r['strat']}_FILTERED"
            new_strategy_candidates.append({**r, "new_name": new_name})
        elif r["verdict"] == "UNSALVAGEABLE":
            unsalvageable.append(r)
        if len(ex_str) > 80: ex_str = ex_str[:77] + "..."
        print(f"| {r['strat']} | {r['n']} | {pct(r['wr'])} | {ex_str} | {r['n_post']} | {pct(r['wr_post'])} | {pct(r['wilson_post_lo'])} | {r['verdict']} | {new_name or '-'} |")

    print(f"\n**Summary**: NEW_STRATEGY={sum(1 for r in results if r['verdict']=='NEW_STRATEGY')}, "
          f"NEW_STRATEGY_TENTATIVE={sum(1 for r in results if r['verdict']=='NEW_STRATEGY_TENTATIVE')}, "
          f"MARGINAL={sum(1 for r in results if r['verdict']=='MARGINAL_IMPROVEMENT')}, "
          f"UNSALVAGEABLE={len(unsalvageable)}, "
          f"INSUFF_N={sum(1 for r in results if r['verdict']=='INSUFFICIENT_N_POST')}, "
          f"NEEDS_MORE={sum(1 for r in results if r['verdict']=='NEEDS_MORE_DATA')}\n")

    # ==== Deliverable 4: Per-strategy SL fingerprint ====
    print("\n## Deliverable 4: SL-hit fingerprint (LOSS top 3 per strategy, N\u22655)\n")
    print("| Strategy | Rank | Cell | N | cell WR | LOSS_LR |")
    print("|---|---:|---|---:|---:|---:|")
    for r in results:
        top_loss = [lc for lc in r["loss_cells"] if lc["n"] >= 5][:3]
        if not top_loss:
            print(f"| {r['strat']} | - | (no cell N\u22655) | - | - | - |")
            continue
        for i, lc in enumerate(top_loss, 1):
            cell_str = f"{lc['cell'][0]}\u00d7{lc['cell'][1]}\u00d7{lc['cell'][2]}"
            lr_str = f"{lc['loss_lr']:.2f}" if lc['loss_lr'] != float('inf') else "\u221e"
            print(f"| {r['strat']} | {i} | {cell_str} | {lc['n']} | {pct(lc['wr'])} | {lr_str} |")

    # Return results for deliverable 5 (binding pre-reg)
    return results, promotion_candidates, new_strategy_candidates, unsalvageable

if __name__ == "__main__":
    results, promos, news, unsal = main()

    # Save structured output for pre-reg generation
    import json as _j
    out = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "promotion_candidates": [{k: (list(v) if isinstance(v, tuple) else v) for k, v in c.items()} for c in promos],
        "new_strategy_candidates": [
            {"strat": r["strat"], "new_name": r["new_name"],
             "baseline_n": r["n"], "baseline_wr": r["wr"],
             "exclude_cells": [list(c) for c in r["exclude_cells"]],
             "n_post": r["n_post"], "wr_post": r["wr_post"],
             "wilson_post_lo": r["wilson_post_lo"],
             "verdict": r["verdict"]}
            for r in news
        ],
        "unsalvageable": [
            {"strat": r["strat"], "baseline_n": r["n"], "baseline_wr": r["wr"],
             "wr_post": r["wr_post"], "n_post": r["n_post"]}
            for r in unsal
        ],
    }
    with open("/tmp/shadow_deep_analysis_results.json", "w") as f:
        _j.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n\nStructured output saved: /tmp/shadow_deep_analysis_results.json", file=sys.stderr)
