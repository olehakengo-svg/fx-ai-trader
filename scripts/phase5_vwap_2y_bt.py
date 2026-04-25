#!/usr/bin/env python3
"""Phase 5 — S5 VWAP/HTF Defense — 365d BT (pre-reg LOCKED 2026-04-25)

Cells (12): pair {EURUSD, GBPUSD} × pullback_min_atr {1.5, 2.0} × defense_line {VWAP, HTF_EMA50, BOTH}
α_cell = 0.05/12 = 0.00417
SURVIVOR: EV>+1.5p, PF>1.5, WR≥45%, N≥30, p<0.00417, WF 4/4
"""
from __future__ import annotations
import argparse, json, math, os, statistics, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ.setdefault("BT_MODE", "1")
try:
    from dotenv import load_dotenv
    _DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
    if _DOTENV_PATH.exists(): load_dotenv(_DOTENV_PATH)
    else: load_dotenv()
except ImportError: pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bb_squeeze_rescue_bt import (
    wilson_lower, welch_t_test, simulate_pnl,
    PIP_MULT, FRICTION_RT, MAX_HOLD_BARS,
    MAE_CATASTROPHIC_PIPS, _fetch_range_5m, synth_null_trades,
)

# LOCKED 2026-04-26 (phase5-secondary-2y-2026-04-26.md):
# - PAIR: EUR/USD + GBP/USD + EUR/JPY (機関大口の cross 防衛線)
# - pullback_atr: 本日 SURVIVOR C03 値 1.5 で固定
# - defense_line: 本日 SURVIVOR は BOTH のみ → BOTH 固定
# - 検定軸 (3): trend_filter ∈ {ema_strict, ema_lite, ema+adx20}
PAIRS_S5 = ["EURUSD=X", "GBPUSD=X", "EURJPY=X"]
PULLBACK_ATR_GRID = [1.5]
DEFENSE_LINE_GRID = ["BOTH"]
TREND_FILTER_GRID = ["ema_strict", "ema_lite", "ema_adx20"]
N_CELLS = len(PAIRS_S5) * len(TREND_FILTER_GRID)  # 9
ALPHA_CELL = 0.05 / N_CELLS  # 0.00556

DEFENSE_TOUCH_ATR = 0.2
SL_ATR_MULT = 0.8
MIN_RR_HARD = 2.5
SESSION_FILTER = (7, 0, 20, 0)  # London-NY (Tokyo 除外)

SURVIVOR_EV_MIN = 1.5
SURVIVOR_PF_MIN = 1.5
SURVIVOR_WR_MIN = 45.0
SURVIVOR_N_MIN = 30
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

def _in_session(bar_time):
    h0,m0,h1,m1 = SESSION_FILTER
    mn = bar_time.hour*60+bar_time.minute
    return h0*60+m0 <= mn <= h1*60+m1

def extract_vwap_defense(symbol, df, pullback_atr, defense_line, trend_filter="ema_strict"):
    pip = PIP_MULT.get(symbol, 100.0)
    fric_half = FRICTION_RT.get(symbol, 2.0) / 2.0 / pip
    out = []
    last_entry_bar = -24
    # HTF EMA50 (1H = 12 × 5m bars rolling)
    if "Close" not in df.columns: return out
    ema50_htf = df["Close"].ewm(span=600, adjust=False).mean()  # ~50h EMA on 5m
    vwap_series = (df["Close"] * df["Volume"]).rolling(288, min_periods=1).sum() / df["Volume"].rolling(288, min_periods=1).sum() if "Volume" in df.columns else df["Close"].rolling(288).mean()

    for i in range(600, len(df) - MAX_HOLD_BARS - 1):
        if i - last_entry_bar < 24:
            continue
        bar_time = df.index[i]
        if hasattr(bar_time, "tzinfo") and bar_time.tzinfo is None:
            bar_time = bar_time.replace(tzinfo=timezone.utc)
        if not _in_session(bar_time):
            continue
        ema9 = float(df["ema9"].iloc[i]) if "ema9" in df.columns else None
        ema21 = float(df["ema21"].iloc[i]) if "ema21" in df.columns else None
        ema50 = float(df["ema50"].iloc[i]) if "ema50" in df.columns else None
        if None in (ema9, ema21, ema50): continue
        vwap_v = float(vwap_series.iloc[i])
        ema_htf_v = float(ema50_htf.iloc[i])
        atr = float(df["atr7"].iloc[i]) if "atr7" in df.columns else 0.001
        bar_close = float(df["Close"].iloc[i])
        bar_open = float(df["Open"].iloc[i])
        prev_low = float(df["Low"].iloc[i-1])
        prev_high = float(df["High"].iloc[i-1])

        adx = float(df["adx"].iloc[i]) if "adx" in df.columns else 0
        if trend_filter == "ema_strict":
            trend_up = ema9 > ema21 > ema50
            trend_down = ema9 < ema21 < ema50
        elif trend_filter == "ema_lite":
            trend_up = ema21 > ema50
            trend_down = ema21 < ema50
        elif trend_filter == "ema_adx20":
            trend_up = (ema21 > ema50) and (adx > 20)
            trend_down = (ema21 < ema50) and (adx > 20)
        else:
            trend_up = trend_down = False
        if not (trend_up or trend_down):
            continue
        # Pullback depth
        recent_high = float(df["High"].iloc[max(0,i-30):i].max())
        recent_low = float(df["Low"].iloc[max(0,i-30):i].min())
        pullback = (recent_high - bar_close) if trend_up else (bar_close - recent_low)
        if pullback < pullback_atr * atr:
            continue
        # Defense touch (binary)
        touch_vwap = abs(bar_close - vwap_v) < DEFENSE_TOUCH_ATR * atr
        touch_ema = abs(bar_close - ema_htf_v) < DEFENSE_TOUCH_ATR * atr
        if defense_line == "VWAP" and not touch_vwap: continue
        if defense_line == "EMA50_HTF" and not touch_ema: continue
        if defense_line == "BOTH" and not (touch_vwap and touch_ema): continue
        defense_v = vwap_v if touch_vwap else ema_htf_v

        sig_dir = ep = sl = tp = None
        if trend_up and prev_low <= defense_v and bar_close > defense_v:
            sig_dir = "BUY"
            ep = bar_close + fric_half
            sl = min(prev_low, ep - SL_ATR_MULT * atr)
            sl_dist = abs(ep - sl)
            tp = ep + MIN_RR_HARD * sl_dist
        elif trend_down and prev_high >= defense_v and bar_close < defense_v:
            sig_dir = "SELL"
            ep = bar_close - fric_half
            sl = max(prev_high, ep + SL_ATR_MULT * atr)
            sl_dist = abs(sl - ep)
            tp = ep - MIN_RR_HARD * sl_dist
        if sig_dir is None: continue
        if i+1 >= len(df): continue

        future = df.iloc[i+1:i+1+MAX_HOLD_BARS]
        bars = [(future.index[k], float(future.iloc[k]["Open"]),
                 float(future.iloc[k]["High"]), float(future.iloc[k]["Low"]),
                 float(future.iloc[k]["Close"])) for k in range(len(future))]
        out.append({"pair": symbol, "symbol": symbol, "direction": sig_dir,
                    "entry_price": ep, "sl": sl, "tp": tp, "bars": bars,
                    "entry_ts": bar_time.isoformat()})
        last_entry_bar = i
    return out

def evaluate_cell(trades, cell, baseline_pnls=None):
    sims = [simulate_pnl(t, time_floor_min=0) for t in trades]
    pnls = [s["pnl_pips"] for s in sims]
    n = len(pnls); wins = sum(1 for p in pnls if p > 0)
    sum_pos = sum(p for p in pnls if p > 0); sum_neg = -sum(p for p in pnls if p < 0)
    ev = sum(pnls)/n if n else 0.0
    pf = sum_pos/sum_neg if sum_neg>0 else (float("inf") if sum_pos>0 else 0.0)
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
    floor_infeasible = breaker_pct > FLOOR_INFEASIBLE_BREAKER_PCT
    sc = {"EV>1.5": ev>SURVIVOR_EV_MIN, "PF>1.5": pf>SURVIVOR_PF_MIN,
          "WR>=45%": rate>=SURVIVOR_WR_MIN, "N>=30": n>=SURVIVOR_N_MIN,
          f"p<{ALPHA_CELL:.5f}": p_welch<ALPHA_CELL,
          "WF_4/4": wf_agree>=SURVIVOR_WF_AGREE, "FLOOR_FEASIBLE": not floor_infeasible}
    verdict = "SURVIVOR" if all(sc.values()) else "REJECT"
    return {"cell_id": cell["id"], "params": cell, "n": n, "wins": wins, "rate_pct": rate,
            "ev": ev, "pf": pf, "wilson_lo_pct": wlo, "p_welch": p_welch,
            "wf_signs": wf_signs, "wf_agree": wf_agree, "mae_breaker_n": breaker_n,
            "mae_breaker_pct": breaker_pct, "floor_infeasible": floor_infeasible,
            "survivor_conds": sc, "verdict": verdict, "pnls": pnls}

def extract_all(from_iso, to_iso, pullback_atr, defense_line, trend_filter):
    from modules.indicators import add_indicators
    out = []
    for symbol in PAIRS_S5:
        try:
            df = _fetch_range_5m(symbol, from_iso, to_iso)
            df = add_indicators(df).dropna()
            ents = extract_vwap_defense(symbol, df, pullback_atr, defense_line, trend_filter=trend_filter)
            print(f"[entries] {symbol} pb={pullback_atr} {defense_line} tf={trend_filter}: {len(ents)}", flush=True)
            out.extend(ents)
        except Exception as e:
            print(f"[err] {symbol}: {e}", flush=True)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_iso", default="2024-04-26")  # 2y
    ap.add_argument("--to", dest="to_iso", default="2026-04-25")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.output_dir is None:
        args.output_dir = "/tmp/phase5-vwap-2y-dryrun" if args.dry_run else "raw/bt-results/phase5-vwap-2y-2026-04-26"
    print(f"=== Phase 5 S5 VWAP 2y BT (PAIR={PAIRS_S5}, α_cell={ALPHA_CELL:.5f}, LOCKED 2026-04-26) ===")
    pa = PULLBACK_ATR_GRID[0]; dl = DEFENSE_LINE_GRID[0]  # 固定
    baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t,0) for t in synth_null_trades(300, seed=42)]]
    per_extraction = {}
    if args.dry_run:
        for tf in TREND_FILTER_GRID:
            per_extraction[tf] = synth_null_trades(20, seed=hash(tf)&0xff)
    else:
        for tf in TREND_FILTER_GRID:
            per_extraction[tf] = extract_all(args.from_iso, args.to_iso, pa, dl, tf)

    print(f"\n--- Cell results ---")
    print(f"{'cell':<6}{'pair':<11}{'tf':<13}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}{'p':>9}{'WF':>5}{'verdict':>10}")
    grid = []
    cell_id = 0
    for pair in PAIRS_S5:
        for tf in TREND_FILTER_GRID:
            cell_id += 1
            cell = {"id": f"C{cell_id:02d}", "pair": pair, "trend_filter": tf,
                    "pullback_atr": pa, "defense_line": dl}
            if args.dry_run:
                trades = per_extraction.get(tf, [])[:15]
                for t in trades: t["pair"]=pair; t["symbol"]=pair
            else:
                all_ents = per_extraction.get(tf, [])
                trades = [t for t in all_ents if t.get("pair")==pair]
            r = evaluate_cell(trades, cell, baseline_pnls=baseline_pnls)
            grid.append(r)
            pf_s = f"{r['pf']:.2f}" if r['pf']!=float("inf") else " inf"
            print(f"{r['cell_id']:<6}{pair[:10]:<11}{tf[:12]:<13}{r['n']:>5}{r['rate_pct']:>6.1f}{r['ev']:>+7.2f}{pf_s:>6}{r['p_welch']:>9.4f}{r['wf_agree']:>3}/{len(r['wf_signs'])}{r['verdict']:>10}")
    survivors = [r for r in grid if r["verdict"]=="SURVIVOR"]
    meta = "SURVIVOR_PRESENT" if survivors else "ALL_REJECT"
    print(f"\nMeta: {meta}")
    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"pre_reg": "phase5-secondary-2y-2026-04-26.md (S5)",
               "alpha_cell": ALPHA_CELL, "n_cells": N_CELLS,
               "from": args.from_iso, "to": args.to_iso, "dry_run": args.dry_run,
               "meta_verdict": meta, "survivors_count": len(survivors),
               "cells": [{k:v for k,v in r.items() if k!="pnls"} for r in grid]}
    with (out_dir / "summary.json").open("w") as f: json.dump(summary, f, indent=2, default=str)
    print(f"[written] {out_dir / 'summary.json'}")
    return 0 if (not args.dry_run or not survivors) else 1

if __name__ == "__main__": sys.exit(main())
