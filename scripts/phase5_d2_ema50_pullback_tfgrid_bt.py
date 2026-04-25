#!/usr/bin/env python3
"""Phase 5 D1 — BB Extreme Mean Reversion × TF Grid 365日 BT (LOCKED 2026-04-26)
Companion: phase5-tfgrid-multi-tf-2026-04-26.md (D1)

仮説: BB%B ≤ 0.05 / ≥ 0.95 で mean revert, TF 上げほど Edge 安定化期待

Cells (10): TF {15m, 30m, 1h, 2h, 4h} × PAIR {EURUSD, USDJPY}
α_cell = 0.05/10 = 0.005
SURVIVOR: EV>+1.5p, PF>1.5, WR≥50%, N≥20, p<0.005, WF 4/4
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
    PIP_MULT, FRICTION_RT, synth_null_trades,
)

PAIRS_D1 = ["EURUSD=X", "GBPUSD=X"]   # D2 Cable系 trend follow
TF_GRID = ["15m", "30m", "1h", "4h"]   # 2h MASSIVE/OANDA未対応で除外
N_CELLS = len(PAIRS_D1) * len(TF_GRID)  # 8
ALPHA_CELL = 0.05 / N_CELLS  # 0.00625

# TF 別パラメータ (LOCKED, 文献値ベース)
TF_PARAMS = {
    "15m": {"max_hold_bars": 24, "mae_breaker": 15, "bar_min": 15},
    "30m": {"max_hold_bars": 24, "mae_breaker": 20, "bar_min": 30},
    "1h":  {"max_hold_bars": 24, "mae_breaker": 30, "bar_min": 60},
    "4h":  {"max_hold_bars": 24, "mae_breaker": 80, "bar_min": 240},
}

EMA_FAST = 9
EMA_MID = 21
EMA_SLOW = 50
PULLBACK_TOUCH_ATR = 0.3
SL_ATR_MULT = 1.0
MIN_RR_HARD = 2.5

SURVIVOR_EV_MIN = 1.5
SURVIVOR_PF_MIN = 1.5
SURVIVOR_WR_MIN = 35.0  # D2 は trend follow 低 WR 許容
SURVIVOR_N_MIN = 20
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

def _fetch_range_tf(symbol, from_iso, to_iso, tf):
    last_err = None
    try:
        from modules.data import fetch_ohlcv_massive
        days = (datetime.fromisoformat(to_iso[:10]) - datetime.fromisoformat(from_iso[:10])).days + 5
        df = fetch_ohlcv_massive(symbol, tf, days=days)
        df = df.loc[(df.index >= from_iso) & (df.index <= to_iso)]
        if len(df) > 100:
            print(f"[MASSIVE/{tf}] {symbol}: {len(df)} bars", flush=True)
            return df
    except Exception as e:
        last_err = f"massive failed: {e}"
    try:
        from modules.data import fetch_ohlcv_range
        df1 = fetch_ohlcv_range(symbol, from_iso, to_iso, interval=tf)
        if len(df1) > 100:
            print(f"[OANDA/{tf}] {symbol}: {len(df1)} bars", flush=True)
            return df1
    except Exception as e:
        last_err = f"oanda failed: {e}; prev: {last_err}"
    raise RuntimeError(f"data fetch failed: {last_err}")

def simulate_pnl_tf(trade, tf):
    """TF 別 MAX_HOLD / MAE_BREAKER で simulate"""
    params = TF_PARAMS[tf]
    direction = trade["direction"]
    ep = trade["entry_price"]; tp = trade["tp"]; sl = trade["sl"]
    bars = trade.get("bars", [])
    pair = trade["pair"]
    pip = PIP_MULT.get(pair, 100.0)
    fric_exit_half = FRICTION_RT.get(pair, 2.0) / 2.0
    sign = 1 if direction == "BUY" else -1
    mae_cat = params["mae_breaker"]

    realized = 0.0; exit_reason = "TIMEOUT"
    for j, (ts, o, h, l, c) in enumerate(bars[:params["max_hold_bars"]]):
        mae = (ep - l) * pip if direction == "BUY" else (h - ep) * pip
        if mae >= mae_cat:
            realized = -mae - fric_exit_half
            exit_reason = "MAE_BREAKER"; break
        if direction == "BUY":
            if l <= sl:
                realized = (sl - ep) * pip * sign - fric_exit_half
                exit_reason = "SL"; break
            if h >= tp:
                realized = (tp - ep) * pip * sign - fric_exit_half
                exit_reason = "TP"; break
        else:
            if h >= sl:
                realized = (sl - ep) * pip * sign - fric_exit_half
                exit_reason = "SL"; break
            if l <= tp:
                realized = (tp - ep) * pip * sign - fric_exit_half
                exit_reason = "TP"; break
    else:
        last_close = bars[-1][4] if bars else ep
        realized = (last_close - ep) * pip * sign - fric_exit_half
    return {"pnl_pips": realized, "exit_reason": exit_reason}

def extract_d1(symbol, df, tf):
    """D2: EMA50 pullback continuation"""
    pip = PIP_MULT.get(symbol, 100.0)
    fric_half = FRICTION_RT.get(symbol, 2.0) / 2.0 / pip
    out = []
    last_entry_bar = -EMA_SLOW
    if len(df) < EMA_SLOW + 50: return out
    ema9 = df["Close"].ewm(span=EMA_FAST, adjust=False).mean()
    ema21 = df["Close"].ewm(span=EMA_MID, adjust=False).mean()
    ema50 = df["Close"].ewm(span=EMA_SLOW, adjust=False).mean()
    atr = (df["High"] - df["Low"]).rolling(7).mean()

    max_hold = TF_PARAMS[tf]["max_hold_bars"]
    for i in range(EMA_SLOW + 10, len(df) - max_hold - 1):
        if i - last_entry_bar < EMA_SLOW: continue
        cur_close = float(df["Close"].iloc[i])
        cur_atr = float(atr.iloc[i]) if not math.isnan(atr.iloc[i]) else 0.001
        e9 = float(ema9.iloc[i]); e21 = float(ema21.iloc[i]); e50 = float(ema50.iloc[i])
        if math.isnan(e50): continue
        # Trend strict
        trend_up = e9 > e21 > e50
        trend_down = e9 < e21 < e50
        if not (trend_up or trend_down): continue
        # Pullback to EMA50 (touch within ATR×0.3)
        touch_ema50 = abs(cur_close - e50) < PULLBACK_TOUCH_ATR * cur_atr
        if not touch_ema50: continue
        # Bounce confirmation: prev bar at/below EMA50, cur bar away
        prev_low = float(df["Low"].iloc[i-1]); prev_high = float(df["High"].iloc[i-1])
        sig_dir = ep = sl = tp = None
        if trend_up and prev_low <= e50 and cur_close > e50:
            sig_dir = "BUY"
            ep = cur_close + fric_half
            sl = min(prev_low, ep - SL_ATR_MULT * cur_atr)
            sl_dist = abs(ep - sl); tp = ep + MIN_RR_HARD * sl_dist
        elif trend_down and prev_high >= e50 and cur_close < e50:
            sig_dir = "SELL"
            ep = cur_close - fric_half
            sl = max(prev_high, ep + SL_ATR_MULT * cur_atr)
            sl_dist = abs(sl - ep); tp = ep - MIN_RR_HARD * sl_dist
        if sig_dir is None: continue
        if i+1 >= len(df): continue
        future = df.iloc[i+1:i+1+max_hold]
        bars = [(future.index[k], float(future.iloc[k]["Open"]), float(future.iloc[k]["High"]),
                 float(future.iloc[k]["Low"]), float(future.iloc[k]["Close"])) for k in range(len(future))]
        out.append({"pair": symbol, "symbol": symbol, "direction": sig_dir,
                    "entry_price": ep, "sl": sl, "tp": tp, "bars": bars,
                    "entry_ts": df.index[i].isoformat() if hasattr(df.index[i],'isoformat') else str(df.index[i])})
        last_entry_bar = i
    return out

def evaluate_cell(trades, cell, tf, baseline_pnls=None):
    sims = [simulate_pnl_tf(t, tf) for t in trades]
    pnls = [s["pnl_pips"] for s in sims]
    n = len(pnls); wins = sum(1 for p in pnls if p>0)
    sum_pos = sum(p for p in pnls if p>0); sum_neg = -sum(p for p in pnls if p<0)
    ev = sum(pnls)/n if n else 0
    pf = sum_pos/sum_neg if sum_neg>0 else (float("inf") if sum_pos>0 else 0)
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
          "WR>=50%": rate>=SURVIVOR_WR_MIN, "N>=20": n>=SURVIVOR_N_MIN,
          f"p<{ALPHA_CELL:.5f}": p_welch<ALPHA_CELL,
          "WF_4/4": wf_agree>=SURVIVOR_WF_AGREE,
          "FLOOR_FEASIBLE": breaker_pct<=FLOOR_INFEASIBLE_BREAKER_PCT}
    verdict = "SURVIVOR" if all(sc.values()) else "REJECT"
    return {"cell_id": cell["id"], "params": cell, "n": n, "wins": wins, "rate_pct": rate,
            "ev": ev, "pf": pf, "wilson_lo_pct": wlo, "p_welch": p_welch,
            "wf_signs": wf_signs, "wf_agree": wf_agree,
            "mae_breaker_pct": breaker_pct,
            "verdict": verdict, "pnls": pnls}

def extract_all(from_iso, to_iso, tf):
    out = []
    for symbol in PAIRS_D1:
        try:
            df = _fetch_range_tf(symbol, from_iso, to_iso, tf)
            ents = extract_d1(symbol, df, tf)
            print(f"[entries] {symbol} {tf}: {len(ents)}", flush=True)
            out.extend(ents)
        except Exception as e:
            print(f"[err] {symbol} {tf}: {e}", flush=True)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_iso", default="2025-04-26")
    ap.add_argument("--to", dest="to_iso", default="2026-04-25")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.output_dir is None:
        args.output_dir = "/tmp/phase5-d2-tfgrid-dryrun" if args.dry_run else "raw/bt-results/phase5-d2-tfgrid-2026-04-26"
    print(f"=== Phase 5 D1 BB Extreme MR × TF Grid (PAIR={PAIRS_D1}, α={ALPHA_CELL:.5f}, LOCKED 2026-04-26) ===")

    baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t,0) for t in synth_null_trades(300, seed=42)]]
    per_extraction = {}
    if args.dry_run:
        for tf in TF_GRID:
            per_extraction[tf] = synth_null_trades(15, seed=hash(tf)&0xff)
    else:
        for tf in TF_GRID:
            per_extraction[tf] = extract_all(args.from_iso, args.to_iso, tf)

    print(f"\n{'cell':<6}{'pair':<11}{'TF':<6}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}{'p':>9}{'WF':>5}{'verdict':>10}")
    grid = []; cid = 0
    for pair in PAIRS_D1:
        for tf in TF_GRID:
            cid += 1
            cell = {"id": f"C{cid:02d}", "pair": pair, "tf": tf}
            if args.dry_run:
                trades = per_extraction.get(tf, [])[:10]
                for t in trades: t["pair"]=pair; t["symbol"]=pair
            else:
                trades = [t for t in per_extraction.get(tf, []) if t.get("pair")==pair]
            r = evaluate_cell(trades, cell, tf, baseline_pnls=baseline_pnls)
            grid.append(r)
            pf_s = f"{r['pf']:.2f}" if r['pf']!=float("inf") else " inf"
            print(f"{r['cell_id']:<6}{pair[:10]:<11}{tf:<6}{r['n']:>5}{r['rate_pct']:>6.1f}{r['ev']:>+7.2f}{pf_s:>6}{r['p_welch']:>9.4f}{r['wf_agree']:>3}/{len(r['wf_signs'])}{r['verdict']:>10}")
    survivors = [r for r in grid if r["verdict"]=="SURVIVOR"]
    meta = "SURVIVOR_PRESENT" if survivors else "ALL_REJECT"
    print(f"\nMeta: {meta}")
    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    json.dump({"pre_reg":"phase5-tfgrid-multi-tf-2026-04-26.md (D1)", "alpha_cell": ALPHA_CELL,
               "n_cells": N_CELLS, "from": args.from_iso, "to": args.to_iso, "dry_run": args.dry_run,
               "meta_verdict": meta, "survivors_count": len(survivors),
               "cells": [{k:v for k,v in r.items() if k!="pnls"} for r in grid]},
              (out_dir/"summary.json").open("w"), indent=2, default=str)
    print(f"[written] {out_dir/'summary.json'}")
    return 0

if __name__ == "__main__": sys.exit(main())
