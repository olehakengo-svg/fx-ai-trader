#!/usr/bin/env python3
"""Phase 5 — S4 Pure Divergence — 365d BT (LOCKED)
Cells (12): pair {GBPUSD, USDJPY} × rsi_extreme {15/85, 20/80, 25/75} × swing_lookback {20, 30}
α_cell = 0.05/12 = 0.00417
SURVIVOR: EV>+1.5p, PF>1.5, WR≥45%, N≥20, p<0.00417
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

PAIRS_S4 = ["GBPUSD=X", "USDJPY=X"]
RSI_EXTREME_GRID = [(15, 85), (20, 80), (25, 75)]
SWING_LOOKBACK_GRID = [20, 30]
N_CELLS = len(PAIRS_S4) * len(RSI_EXTREME_GRID) * len(SWING_LOOKBACK_GRID)
ALPHA_CELL = 0.05 / N_CELLS

SL_ATR_MULT = 0.8
MIN_RR_HARD = 2.0
COOLDOWN_BARS = 24
SESSION_FILTER = (8, 0, 20, 0)

SURVIVOR_EV_MIN = 1.5
SURVIVOR_PF_MIN = 1.5
SURVIVOR_WR_MIN = 45.0
SURVIVOR_N_MIN = 20
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

def _in_session(bar_time):
    h0,m0,h1,m1 = SESSION_FILTER
    mn = bar_time.hour*60+bar_time.minute
    return h0*60+m0 <= mn <= h1*60+m1

def extract_div(symbol, df, rsi_low, rsi_high, swing_lb):
    pip = PIP_MULT.get(symbol, 100.0)
    fric_half = FRICTION_RT.get(symbol, 2.0) / 2.0 / pip
    out = []
    last_entry_bar = -COOLDOWN_BARS
    if "rsi5" not in df.columns: return out

    for i in range(swing_lb + 50, len(df) - MAX_HOLD_BARS - 1):
        if i - last_entry_bar < COOLDOWN_BARS: continue
        bar_time = df.index[i]
        if hasattr(bar_time, "tzinfo") and bar_time.tzinfo is None:
            bar_time = bar_time.replace(tzinfo=timezone.utc)
        if not _in_session(bar_time): continue

        recent = df.iloc[i-swing_lb:i]
        cur_rsi = float(df["rsi5"].iloc[i])
        bar = df.iloc[i]
        cur_high = float(bar["High"]); cur_low = float(bar["Low"])
        cur_close = float(bar["Close"])
        atr = float(df["atr7"].iloc[i]) if "atr7" in df.columns else 0.001

        sig_dir = ep = sl = tp = None

        # BEARISH div: 価格 new HH AND RSI < prev swing high RSI AND RSI ≥ overbought
        if cur_rsi >= rsi_high:
            prev_swing_high_idx = recent["High"].idxmax()
            prev_swing_high = float(recent.loc[prev_swing_high_idx, "High"])
            prev_swing_rsi = float(df.loc[prev_swing_high_idx, "rsi5"])
            if cur_high > prev_swing_high and cur_rsi < prev_swing_rsi:
                sig_dir = "SELL"
                ep = cur_close - fric_half
                sl = cur_high + SL_ATR_MULT * atr
                sl_dist = abs(sl - ep); tp = ep - MIN_RR_HARD * sl_dist

        # BULLISH div (mirror)
        if sig_dir is None and cur_rsi <= rsi_low:
            prev_swing_low_idx = recent["Low"].idxmin()
            prev_swing_low = float(recent.loc[prev_swing_low_idx, "Low"])
            prev_swing_rsi = float(df.loc[prev_swing_low_idx, "rsi5"])
            if cur_low < prev_swing_low and cur_rsi > prev_swing_rsi:
                sig_dir = "BUY"
                ep = cur_close + fric_half
                sl = cur_low - SL_ATR_MULT * atr
                sl_dist = abs(ep - sl); tp = ep + MIN_RR_HARD * sl_dist

        if sig_dir is None: continue
        if i+1 >= len(df): continue
        future = df.iloc[i+1:i+1+MAX_HOLD_BARS]
        bars = [(future.index[k], float(future.iloc[k]["Open"]), float(future.iloc[k]["High"]),
                 float(future.iloc[k]["Low"]), float(future.iloc[k]["Close"])) for k in range(len(future))]
        out.append({"pair": symbol, "symbol": symbol, "direction": sig_dir,
                    "entry_price": ep, "sl": sl, "tp": tp, "bars": bars,
                    "entry_ts": bar_time.isoformat()})
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
    sc = {"EV>1.5": ev>SURVIVOR_EV_MIN, "PF>1.5": pf>SURVIVOR_PF_MIN,
          "WR>=45%": rate>=SURVIVOR_WR_MIN, "N>=20": n>=SURVIVOR_N_MIN,
          f"p<{ALPHA_CELL:.5f}": p_welch<ALPHA_CELL,
          "WF_4/4": wf_agree>=SURVIVOR_WF_AGREE, "FLOOR_FEASIBLE": breaker_pct<=FLOOR_INFEASIBLE_BREAKER_PCT}
    verdict = "SURVIVOR" if all(sc.values()) else "REJECT"
    return {"cell_id": cell["id"], "params": cell, "n": n, "wins": wins, "rate_pct": rate,
            "ev": ev, "pf": pf, "p_welch": p_welch, "wf_signs": wf_signs, "wf_agree": wf_agree,
            "mae_breaker_pct": breaker_pct, "verdict": verdict, "pnls": pnls}

def extract_all(from_iso, to_iso, rsi_low, rsi_high, swing_lb):
    from modules.indicators import add_indicators
    out = []
    for symbol in PAIRS_S4:
        try:
            df = _fetch_range_5m(symbol, from_iso, to_iso)
            df = add_indicators(df).dropna()
            ents = extract_div(symbol, df, rsi_low, rsi_high, swing_lb)
            print(f"[entries] {symbol} rsi[{rsi_low}/{rsi_high}] swing={swing_lb}: {len(ents)}", flush=True)
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
        args.output_dir = "/tmp/phase5-div-dryrun" if args.dry_run else "raw/bt-results/phase5-divergence-2026-04-25"
    print(f"=== Phase 5 S4 Pure Divergence (PAIR={PAIRS_S4}, α={ALPHA_CELL:.5f}) ===")

    baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t,0) for t in synth_null_trades(300, seed=42)]]
    per_extraction = {}
    if args.dry_run:
        for re_ in RSI_EXTREME_GRID:
            for sl_ in SWING_LOOKBACK_GRID:
                per_extraction[(re_, sl_)] = synth_null_trades(20, seed=hash((re_, sl_))&0xff)
    else:
        for re_ in RSI_EXTREME_GRID:
            for sl_ in SWING_LOOKBACK_GRID:
                rl, rh = re_
                per_extraction[(re_, sl_)] = extract_all(args.from_iso, args.to_iso, rl, rh, sl_)

    print(f"\n{'cell':<6}{'pair':<11}{'rsi':<10}{'swing':>6}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}{'p':>9}{'verdict':>10}")
    grid = []; cid = 0
    for pair in PAIRS_S4:
        for re_ in RSI_EXTREME_GRID:
            for sl_ in SWING_LOOKBACK_GRID:
                cid += 1
                cell = {"id": f"C{cid:02d}", "pair": pair, "rsi_extreme": re_, "swing_lb": sl_}
                if args.dry_run:
                    trades = per_extraction.get((re_, sl_), [])[:15]
                    for t in trades: t["pair"]=pair; t["symbol"]=pair
                else:
                    trades = [t for t in per_extraction.get((re_, sl_), []) if t.get("pair")==pair]
                r = evaluate_cell(trades, cell, baseline_pnls=baseline_pnls)
                grid.append(r)
                pf_s = f"{r['pf']:.2f}" if r['pf']!=float("inf") else " inf"
                rsi_s = f"{re_[0]}/{re_[1]}"
                print(f"{r['cell_id']:<6}{pair[:10]:<11}{rsi_s:<10}{sl_:>6}{r['n']:>5}{r['rate_pct']:>6.1f}{r['ev']:>+7.2f}{pf_s:>6}{r['p_welch']:>9.4f}{r['verdict']:>10}")
    survivors = [r for r in grid if r["verdict"]=="SURVIVOR"]
    meta = "SURVIVOR_PRESENT" if survivors else "ALL_REJECT"
    print(f"\nMeta: {meta}")
    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    json.dump({"pre_reg":"phase5-9d-edge-matrix-2026-04-25.md (S4)", "alpha_cell": ALPHA_CELL,
               "n_cells": N_CELLS, "from": args.from_iso, "to": args.to_iso, "dry_run": args.dry_run,
               "meta_verdict": meta, "survivors_count": len(survivors),
               "cells": [{k:v for k,v in r.items() if k!="pnls"} for r in grid]},
              (out_dir/"summary.json").open("w"), indent=2, default=str)
    print(f"[written] {out_dir/'summary.json'}")
    return 0

if __name__ == "__main__": sys.exit(main())
