#!/usr/bin/env python3
"""Phase 5 — S6 Value Area Reversion — 365d BT (LOCKED)
Cells (12): pair {EURUSD, EURGBP} × vp_lookback_h {4, 6, 8} × va_pct {0.80, 0.85}
α_cell = 0.05/12 = 0.00417
SURVIVOR: EV>+1.0p, PF>1.5, WR≥55%, N≥40 (高勝率盾), p<0.00417
"""
from __future__ import annotations
import argparse, json, math, os, statistics, sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("BT_MODE", "1")
try:
    from dotenv import load_dotenv
    p = Path(__file__).resolve().parents[1] / ".env"
    if p.exists(): load_dotenv(p)
    else: load_dotenv()
except ImportError: pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bb_squeeze_rescue_bt import (
    wilson_lower, welch_t_test, simulate_pnl,
    PIP_MULT, FRICTION_RT, MAX_HOLD_BARS,
    MAE_CATASTROPHIC_PIPS, _fetch_range_5m, synth_null_trades,
)

PAIRS_S6 = ["EURUSD=X", "EURGBP=X"]
VP_LOOKBACK_HOURS_GRID = [4, 6, 8]
VA_PCT_GRID = [0.80, 0.85]
N_CELLS = len(PAIRS_S6) * len(VP_LOOKBACK_HOURS_GRID) * len(VA_PCT_GRID)
ALPHA_CELL = 0.05 / N_CELLS

VP_BUCKETS = 30
SL_ATR_MULT = 0.5
TP_TO_POC_RATIO = 0.6
MIN_RR_HARD = 1.5
COOLDOWN_BARS = 12

SURVIVOR_EV_MIN = 1.0
SURVIVOR_PF_MIN = 1.5
SURVIVOR_WR_MIN = 55.0
SURVIVOR_N_MIN = 40
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

def extract_va(symbol, df, vp_h, va_pct):
    pip = PIP_MULT.get(symbol, 100.0)
    fric_half = FRICTION_RT.get(symbol, 2.0) / 2.0 / pip
    out = []
    last_entry_bar = -COOLDOWN_BARS
    bars_per_hour = 12
    vp_bars = vp_h * bars_per_hour

    for i in range(vp_bars + 50, len(df) - MAX_HOLD_BARS - 1):
        if i - last_entry_bar < COOLDOWN_BARS: continue
        recent = df.iloc[i - vp_bars: i]
        prices = recent["Close"].values
        lo, hi = prices.min(), prices.max()
        if hi - lo <= 0: continue
        bucket_size = (hi - lo) / VP_BUCKETS
        tpo = [0]*VP_BUCKETS
        for p in prices:
            idx = min(int((p - lo) / bucket_size), VP_BUCKETS - 1)
            tpo[idx] += 1
        poc_idx = max(range(VP_BUCKETS), key=lambda k: tpo[k])
        poc = lo + (poc_idx + 0.5) * bucket_size
        sorted_idxs = sorted(range(VP_BUCKETS), key=lambda k: -tpo[k])
        cumsum = 0; total = sum(tpo)
        in_va = set()
        for idx in sorted_idxs:
            in_va.add(idx); cumsum += tpo[idx]
            if cumsum / total >= va_pct: break
        va_high = lo + (max(in_va) + 1) * bucket_size
        va_low = lo + min(in_va) * bucket_size

        bar = df.iloc[i]
        bar_close = float(bar["Close"]); bar_open = float(bar["Open"])
        prev_close = float(df["Close"].iloc[i-1])
        atr = float(df["atr7"].iloc[i]) if "atr7" in df.columns else 0.0001

        if va_low <= bar_close <= va_high: continue
        sig_dir = ep = sl = tp = None
        if bar_close > va_high and bar_close < prev_close:
            sig_dir = "SELL"; ep = bar_close - fric_half
            sl = max(float(df["High"].iloc[i-2:i+1].max()), bar_close + 0.5*atr) + SL_ATR_MULT * atr
            tp_dist = TP_TO_POC_RATIO * (bar_close - poc)
            if tp_dist <= 0: continue
            tp = ep - tp_dist
            sl_dist = abs(sl - ep)
            if sl_dist <= 0 or tp_dist / sl_dist < MIN_RR_HARD: continue
        elif bar_close < va_low and bar_close > prev_close:
            sig_dir = "BUY"; ep = bar_close + fric_half
            sl = min(float(df["Low"].iloc[i-2:i+1].min()), bar_close - 0.5*atr) - SL_ATR_MULT * atr
            tp_dist = TP_TO_POC_RATIO * (poc - bar_close)
            if tp_dist <= 0: continue
            tp = ep + tp_dist
            sl_dist = abs(ep - sl)
            if sl_dist <= 0 or tp_dist / sl_dist < MIN_RR_HARD: continue
        if sig_dir is None: continue
        if i+1 >= len(df): continue
        future = df.iloc[i+1:i+1+MAX_HOLD_BARS]
        bars = [(future.index[k], float(future.iloc[k]["Open"]), float(future.iloc[k]["High"]),
                 float(future.iloc[k]["Low"]), float(future.iloc[k]["Close"])) for k in range(len(future))]
        out.append({"pair": symbol, "symbol": symbol, "direction": sig_dir,
                    "entry_price": ep, "sl": sl, "tp": tp, "bars": bars,
                    "entry_ts": df.index[i].isoformat() if hasattr(df.index[i],'isoformat') else str(df.index[i])})
        last_entry_bar = i
    return out

def evaluate_cell(trades, cell, baseline_pnls=None):
    sims = [simulate_pnl(t, 0) for t in trades]
    pnls = [s["pnl_pips"] for s in sims]
    n = len(pnls); wins = sum(1 for p in pnls if p>0)
    sum_pos = sum(p for p in pnls if p>0); sum_neg = -sum(p for p in pnls if p<0)
    ev = sum(pnls)/n if n else 0; pf = sum_pos/sum_neg if sum_neg>0 else (float("inf") if sum_pos>0 else 0)
    wlo = wilson_lower(wins, n); rate = wins/n*100 if n else 0
    if baseline_pnls and len(baseline_pnls)>=2 and n>=2:
        _, p_welch = welch_t_test(pnls, baseline_pnls)
    else: p_welch = 1.0
    wf_signs = []
    if n >= WF_WINDOWS*2:
        chunk = max(1, n//WF_WINDOWS)
        for w in range(WF_WINDOWS):
            seg = pnls[w*chunk:(w+1)*chunk] if w<WF_WINDOWS-1 else pnls[w*chunk:]
            if seg: wf_signs.append(1 if statistics.mean(seg)>0 else (-1 if statistics.mean(seg)<0 else 0))
    wf_agree = max(wf_signs.count(1), wf_signs.count(-1)) if wf_signs else 0
    breaker_n = sum(1 for s in sims if s["exit_reason"]=="MAE_BREAKER")
    breaker_pct = breaker_n/n*100 if n else 0
    sc = {"EV>1.0": ev>SURVIVOR_EV_MIN, "PF>1.5": pf>SURVIVOR_PF_MIN,
          "WR>=55%": rate>=SURVIVOR_WR_MIN, "N>=40": n>=SURVIVOR_N_MIN,
          f"p<{ALPHA_CELL:.5f}": p_welch<ALPHA_CELL,
          "WF_4/4": wf_agree>=SURVIVOR_WF_AGREE, "FLOOR_FEASIBLE": breaker_pct<=FLOOR_INFEASIBLE_BREAKER_PCT}
    verdict = "SURVIVOR" if all(sc.values()) else "REJECT"
    return {"cell_id": cell["id"], "params": cell, "n": n, "wins": wins, "rate_pct": rate,
            "ev": ev, "pf": pf, "p_welch": p_welch, "wf_signs": wf_signs, "wf_agree": wf_agree,
            "mae_breaker_pct": breaker_pct, "verdict": verdict, "pnls": pnls}

def extract_all(from_iso, to_iso, vp_h, va_pct):
    from modules.indicators import add_indicators
    out = []
    for symbol in PAIRS_S6:
        try:
            df = _fetch_range_5m(symbol, from_iso, to_iso)
            df = add_indicators(df).dropna()
            ents = extract_va(symbol, df, vp_h, va_pct)
            print(f"[entries] {symbol} vp{vp_h}h va{va_pct}: {len(ents)}", flush=True)
            out.extend(ents)
        except Exception as e:
            print(f"[err] {symbol}: {e}", flush=True)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_iso", default="2025-04-26")
    ap.add_argument("--to", dest="to_iso", default="2026-04-25")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.output_dir is None:
        args.output_dir = "/tmp/phase5-va-dryrun" if args.dry_run else "raw/bt-results/phase5-va-2026-04-25"
    print(f"=== Phase 5 S6 VA Reversion (PAIR={PAIRS_S6}, α={ALPHA_CELL:.5f}) ===")

    baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t,0) for t in synth_null_trades(300, seed=42)]]
    per_extraction = {}
    if args.dry_run:
        for vh in VP_LOOKBACK_HOURS_GRID:
            for va in VA_PCT_GRID:
                per_extraction[(vh, va)] = synth_null_trades(30, seed=hash((vh, va))&0xff)
    else:
        for vh in VP_LOOKBACK_HOURS_GRID:
            for va in VA_PCT_GRID:
                per_extraction[(vh, va)] = extract_all(args.from_iso, args.to_iso, vh, va)

    print(f"\n{'cell':<6}{'pair':<11}{'vph':>4}{'vapct':>6}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}{'p':>9}{'verdict':>10}")
    grid = []; cid = 0
    for pair in PAIRS_S6:
        for vh in VP_LOOKBACK_HOURS_GRID:
            for va in VA_PCT_GRID:
                cid += 1
                cell = {"id": f"C{cid:02d}", "pair": pair, "vp_h": vh, "va_pct": va}
                if args.dry_run:
                    trades = per_extraction.get((vh, va), [])[:20]
                    for t in trades: t["pair"]=pair; t["symbol"]=pair
                else:
                    trades = [t for t in per_extraction.get((vh, va), []) if t.get("pair")==pair]
                r = evaluate_cell(trades, cell, baseline_pnls=baseline_pnls)
                grid.append(r)
                pf_s = f"{r['pf']:.2f}" if r['pf']!=float("inf") else " inf"
                print(f"{r['cell_id']:<6}{pair[:10]:<11}{vh:>4}{va:>6.2f}{r['n']:>5}{r['rate_pct']:>6.1f}{r['ev']:>+7.2f}{pf_s:>6}{r['p_welch']:>9.4f}{r['verdict']:>10}")
    survivors = [r for r in grid if r["verdict"]=="SURVIVOR"]
    meta = "SURVIVOR_PRESENT" if survivors else "ALL_REJECT"
    print(f"\nMeta: {meta}")
    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    json.dump({"pre_reg":"phase5-9d-edge-matrix-2026-04-25.md (S6)", "alpha_cell": ALPHA_CELL,
               "n_cells": N_CELLS, "from": args.from_iso, "to": args.to_iso, "dry_run": args.dry_run,
               "meta_verdict": meta, "survivors_count": len(survivors),
               "cells": [{k:v for k,v in r.items() if k!="pnls"} for r in grid]},
              (out_dir/"summary.json").open("w"), indent=2, default=str)
    print(f"[written] {out_dir/'summary.json'}")
    return 0

if __name__ == "__main__": sys.exit(main())
