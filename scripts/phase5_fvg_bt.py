#!/usr/bin/env python3
"""
Phase 5 — S8 Fair Value Gap (FVG) — 365日 BT (pre-reg LOCKED 2026-04-25)

Companion: knowledge-base/wiki/analyses/phase5-9d-edge-matrix-2026-04-25.md (S8)

Cell grid (12 cells, PAIR 限定):
    pair: {EURUSD=X, GBPUSD=X}
    gap_min_atr_mult: {0.3, 0.5, 0.7}
    fill_pct: {full_fill, partial_50%}

α_cell = 0.05 / 12 = 0.00417

SURVIVOR (AND):
    EV > +1.5p, PF > 1.5, WR >= 45%, N >= 30, p_welch < 0.00417, WF 4/4
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
from bb_squeeze_rescue_bt import (  # type: ignore
    wilson_lower, welch_t_test, simulate_pnl,
    PIP_MULT, FRICTION_RT, MAX_HOLD_BARS, BAR_MIN,
    MAE_CATASTROPHIC_PIPS, _fetch_range_5m, synth_null_trades,
)

PAIRS_S8 = ["EURUSD=X", "GBPUSD=X"]
GAP_MIN_ATR_GRID = [0.3, 0.5, 0.7]
FILL_PCT_GRID = ["full", "partial_50"]
SESSION_FILTER = (7, 0, 20, 0)  # London-NY only (Tokyo 除外)
N_CELLS = len(PAIRS_S8) * len(GAP_MIN_ATR_GRID) * len(FILL_PCT_GRID)
ALPHA_CELL = 0.05 / N_CELLS  # 0.00417

REENTRY_LOOKBACK = 50
SL_ATR_MULT = 0.5
MIN_RR_HARD = 2.0
COOLDOWN_BARS = 24

SURVIVOR_EV_MIN = 1.5
SURVIVOR_PF_MIN = 1.5
SURVIVOR_WR_MIN = 45.0
SURVIVOR_N_MIN = 30
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

def _in_session(bar_time: datetime) -> bool:
    h0, m0, h1, m1 = SESSION_FILTER
    minute_now = bar_time.hour * 60 + bar_time.minute
    return h0 * 60 + m0 <= minute_now <= h1 * 60 + m1

def extract_fvg_entries(symbol, df, gap_min_atr, fill_pct):
    pip = PIP_MULT.get(symbol, 100.0)
    fric_half = FRICTION_RT.get(symbol, 2.0) / 2.0 / pip
    out = []
    last_entry_bar = -COOLDOWN_BARS
    # 既知の active FVG リスト (まだ fill されていない)
    active_fvgs = []  # list of dicts: {idx, type:bullish/bearish, top, bottom}

    for i in range(REENTRY_LOOKBACK, len(df) - MAX_HOLD_BARS - 1):
        if i < 2:
            continue
        bar_time = df.index[i]
        if hasattr(bar_time, "tzinfo") and bar_time.tzinfo is None:
            bar_time = bar_time.replace(tzinfo=timezone.utc)

        # FVG detection at i-1 (bar i-2, i-1, i の関係)
        bar2_high = float(df["High"].iloc[i-2])
        bar2_low = float(df["Low"].iloc[i-2])
        bar0_high = float(df["High"].iloc[i])
        bar0_low = float(df["Low"].iloc[i])
        atr_at_i = float(df["atr7"].iloc[i]) if "atr7" in df.columns else 0.001

        # Bullish FVG: bar2.High < bar0.Low
        if bar2_high < bar0_low:
            gap = bar0_low - bar2_high
            if gap >= gap_min_atr * atr_at_i:
                active_fvgs.append({"idx": i, "type": "bullish",
                                    "top": bar0_low, "bottom": bar2_high})
        # Bearish FVG: bar2.Low > bar0.High
        if bar2_low > bar0_high:
            gap = bar2_low - bar0_high
            if gap >= gap_min_atr * atr_at_i:
                active_fvgs.append({"idx": i, "type": "bearish",
                                    "top": bar2_low, "bottom": bar0_high})

        # 古い FVG 削除
        active_fvgs = [f for f in active_fvgs if i - f["idx"] <= REENTRY_LOOKBACK]

        if i - last_entry_bar < COOLDOWN_BARS:
            continue
        if not _in_session(bar_time):
            continue

        cur_low = float(df["Low"].iloc[i])
        cur_high = float(df["High"].iloc[i])
        cur_close = float(df["Close"].iloc[i])

        # FVG への retest
        sig_dir = None
        ep = sl = tp = None
        for fvg in active_fvgs:
            if fvg["idx"] == i:
                continue  # 同 bar は無効
            if fvg["type"] == "bullish":
                # 価格が gap zone touch + 反発
                fill_target = fvg["bottom"] if fill_pct == "full" else (fvg["top"] + fvg["bottom"]) / 2
                if cur_low <= fvg["top"] and cur_low > fvg["bottom"] - SL_ATR_MULT * atr_at_i and cur_close > fvg["top"]:
                    if cur_low <= fill_target:
                        sig_dir = "BUY"
                        ep = cur_close + fric_half
                        sl = fvg["bottom"] - SL_ATR_MULT * atr_at_i
                        sl_dist = abs(ep - sl)
                        tp = ep + MIN_RR_HARD * sl_dist
                        break
            else:
                fill_target = fvg["top"] if fill_pct == "full" else (fvg["top"] + fvg["bottom"]) / 2
                if cur_high >= fvg["bottom"] and cur_high < fvg["top"] + SL_ATR_MULT * atr_at_i and cur_close < fvg["bottom"]:
                    if cur_high >= fill_target:
                        sig_dir = "SELL"
                        ep = cur_close - fric_half
                        sl = fvg["top"] + SL_ATR_MULT * atr_at_i
                        sl_dist = abs(sl - ep)
                        tp = ep - MIN_RR_HARD * sl_dist
                        break
        if sig_dir is None:
            continue
        if i + 1 >= len(df):
            continue

        future = df.iloc[i + 1: i + 1 + MAX_HOLD_BARS]
        bars = [(future.index[k],
                 float(future.iloc[k]["Open"]),
                 float(future.iloc[k]["High"]),
                 float(future.iloc[k]["Low"]),
                 float(future.iloc[k]["Close"])) for k in range(len(future))]
        out.append({
            "pair": symbol, "symbol": symbol,
            "direction": sig_dir, "entry_price": ep, "sl": sl, "tp": tp,
            "bars": bars,
            "entry_ts": bar_time.isoformat(),
        })
        last_entry_bar = i

    return out

def evaluate_cell(trades, cell, baseline_pnls=None):
    sims = [simulate_pnl(t, time_floor_min=0) for t in trades]
    pnls = [s["pnl_pips"] for s in sims]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    sum_pos = sum(p for p in pnls if p > 0)
    sum_neg = -sum(p for p in pnls if p < 0)
    ev = sum(pnls) / n if n else 0.0
    pf = sum_pos / sum_neg if sum_neg > 0 else (float("inf") if sum_pos > 0 else 0.0)
    wlo = wilson_lower(wins, n)
    rate = wins / n * 100 if n else 0.0
    if baseline_pnls is not None and len(baseline_pnls) >= 2 and n >= 2:
        _, p_welch = welch_t_test(pnls, baseline_pnls)
    else:
        p_welch = 1.0
    wf_signs = []
    if n >= WF_WINDOWS * 2:
        chunk = max(1, n // WF_WINDOWS)
        for w in range(WF_WINDOWS):
            seg = pnls[w*chunk:(w+1)*chunk] if w < WF_WINDOWS-1 else pnls[w*chunk:]
            if seg:
                wf_signs.append(1 if statistics.mean(seg) > 0 else (-1 if statistics.mean(seg) < 0 else 0))
    wf_agree = max(wf_signs.count(1), wf_signs.count(-1)) if wf_signs else 0
    breaker_n = sum(1 for s in sims if s["exit_reason"] == "MAE_BREAKER")
    breaker_pct = breaker_n / n * 100 if n else 0.0
    floor_infeasible = breaker_pct > FLOOR_INFEASIBLE_BREAKER_PCT
    survivor_conds = {
        "EV>1.5": ev > SURVIVOR_EV_MIN, "PF>1.5": pf > SURVIVOR_PF_MIN,
        "WR>=45%": rate >= SURVIVOR_WR_MIN, "N>=30": n >= SURVIVOR_N_MIN,
        f"p<{ALPHA_CELL:.5f}": p_welch < ALPHA_CELL,
        "WF_4/4": wf_agree >= SURVIVOR_WF_AGREE, "FLOOR_FEASIBLE": not floor_infeasible,
    }
    verdict = "SURVIVOR" if all(survivor_conds.values()) else "REJECT"
    return {
        "cell_id": cell["id"], "params": cell, "n": n, "wins": wins, "rate_pct": rate,
        "ev": ev, "pf": pf, "wilson_lo_pct": wlo, "p_welch": p_welch,
        "wf_signs": wf_signs, "wf_agree": wf_agree,
        "mae_breaker_n": breaker_n, "mae_breaker_pct": breaker_pct,
        "floor_infeasible": floor_infeasible, "survivor_conds": survivor_conds,
        "verdict": verdict, "pnls": pnls,
    }

def extract_all(from_iso, to_iso, gap_min_atr, fill_pct):
    from modules.indicators import add_indicators
    out = []
    for symbol in PAIRS_S8:
        try:
            df = _fetch_range_5m(symbol, from_iso, to_iso)
            df = add_indicators(df).dropna()
            ents = extract_fvg_entries(symbol, df, gap_min_atr, fill_pct)
            print(f"[entries] {symbol} gap×{gap_min_atr} fill={fill_pct}: {len(ents)}", flush=True)
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
        args.output_dir = ("/tmp/phase5-fvg-dryrun" if args.dry_run
                           else "raw/bt-results/phase5-fvg-2026-04-25")

    print(f"=" * 90)
    print(f"Phase 5 S8 — FVG 365日 BT (PAIR 限定: {PAIRS_S8})")
    print(f"  alpha_cell = {ALPHA_CELL:.5f} (Bonferroni 0.05/{N_CELLS})")
    print(f"  Session: London + NY (Tokyo 除外)")
    print(f"=" * 90)

    if args.dry_run:
        baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t, 0) for t in synth_null_trades(300, seed=42)]]
        per_extraction = {}
        for ga in GAP_MIN_ATR_GRID:
            for fp in FILL_PCT_GRID:
                per_extraction[(ga, fp)] = synth_null_trades(30, seed=hash((ga, fp)) & 0xff)
    else:
        baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t, 0) for t in synth_null_trades(300, seed=42)]]
        per_extraction = {}
        for ga in GAP_MIN_ATR_GRID:
            for fp in FILL_PCT_GRID:
                per_extraction[(ga, fp)] = extract_all(args.from_iso, args.to_iso, ga, fp)

    print(f"\n--- Cell results ---")
    print(f"{'cell':<6}{'pair':<11}{'gap×':>5}{'fill':<11}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}"
          f"{'p':>9}{'WF':>5}{'verdict':>10}")
    grid = []
    cell_id = 0
    for pair in PAIRS_S8:
        for ga in GAP_MIN_ATR_GRID:
            for fp in FILL_PCT_GRID:
                cell_id += 1
                cell = {"id": f"C{cell_id:02d}", "pair": pair, "gap_min_atr": ga, "fill_pct": fp}
                if args.dry_run:
                    trades = per_extraction.get((ga, fp), [])[:15]
                    for t in trades: t["pair"] = pair; t["symbol"] = pair
                else:
                    all_ents = per_extraction.get((ga, fp), [])
                    trades = [t for t in all_ents if t.get("pair") == pair]
                r = evaluate_cell(trades, cell, baseline_pnls=baseline_pnls)
                grid.append(r)
                pf_s = f"{r['pf']:.2f}" if r['pf'] != float("inf") else " inf"
                print(f"{r['cell_id']:<6}{pair[:10]:<11}{ga:>5.1f}{fp[:10]:<11}"
                      f"{r['n']:>5}{r['rate_pct']:>6.1f}{r['ev']:>+7.2f}{pf_s:>6}"
                      f"{r['p_welch']:>9.4f}{r['wf_agree']:>3}/{len(r['wf_signs'])}"
                      f"{r['verdict']:>10}")

    survivors = [r for r in grid if r["verdict"] == "SURVIVOR"]
    meta = "SURVIVOR_PRESENT" if survivors else "ALL_REJECT"
    print(f"\nMeta verdict: {meta}")

    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "pre_reg": "knowledge-base/wiki/analyses/phase5-9d-edge-matrix-2026-04-25.md (S8)",
        "alpha_cell": ALPHA_CELL, "n_cells": N_CELLS,
        "from": args.from_iso, "to": args.to_iso, "dry_run": args.dry_run,
        "meta_verdict": meta, "survivors_count": len(survivors),
        "cells": [{k: v for k, v in r.items() if k != "pnls"} for r in grid],
    }
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n[written] {out_dir / 'summary.json'}")
    return 0 if (not args.dry_run or not survivors) else 1

if __name__ == "__main__":
    sys.exit(main())
