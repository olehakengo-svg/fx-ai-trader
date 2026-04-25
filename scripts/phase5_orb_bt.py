#!/usr/bin/env python3
"""
Phase 5 — S7 Opening Range Breakout — 365日 BT (pre-reg LOCKED 2026-04-25)

Companion: knowledge-base/wiki/analyses/phase5-9d-edge-matrix-2026-04-25.md (S7)

Cell grid (12 cells, PAIR 限定):
    pair: {GBPUSD=X, GBPJPY=X}
    volume_spike_ratio: {2.5, 3.0, 4.0}
    session: {London_open, NY_open}

α_cell = 0.05 / 12 = 0.00417

SURVIVOR (AND):
    EV > +2.0p, PF > 1.5, WR >= 40%, N >= 20, p_welch < 0.00417, WF 4/4
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
    if _DOTENV_PATH.exists():
        load_dotenv(_DOTENV_PATH)
    else:
        load_dotenv()
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bb_squeeze_rescue_bt import (  # type: ignore
    wilson_lower, welch_t_test, simulate_pnl,
    PIP_MULT, FRICTION_RT, MAX_HOLD_BARS, BAR_MIN,
    MAE_CATASTROPHIC_PIPS, _fetch_range_5m, synth_null_trades,
)

# ---------------------------------------------------------------------------
# Configuration (LOCKED, PAIR 限定)
# ---------------------------------------------------------------------------

PAIRS_S7 = ["GBPUSD=X", "GBPJPY=X"]
VOLUME_SPIKE_GRID = [2.5, 3.0, 4.0]
SESSION_GRID = {
    "London_open": (7, 0, 8, 30),
    "NY_open":     (13, 0, 14, 30),
}
ASIA_RANGE_HOURS = 6
N_CELLS = len(PAIRS_S7) * len(VOLUME_SPIKE_GRID) * len(SESSION_GRID)
ALPHA_CELL = 0.05 / N_CELLS  # 0.00417

SL_ATR_MULT = 0.8
MIN_RR_HARD = 2.0

SURVIVOR_EV_MIN = 2.0
SURVIVOR_PF_MIN = 1.5
SURVIVOR_WR_MIN = 40.0
SURVIVOR_N_MIN = 20
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

def _in_window(bar_time: datetime, window) -> bool:
    h0, m0, h1, m1 = window
    minute_now = bar_time.hour * 60 + bar_time.minute
    return h0 * 60 + m0 <= minute_now <= h1 * 60 + m1

def extract_orb_entries(symbol: str, df, vol_spike: float, session_window) -> List[Dict[str, Any]]:
    pip = PIP_MULT.get(symbol, 100.0)
    fric_half = FRICTION_RT.get(symbol, 2.0) / 2.0 / pip
    out: List[Dict[str, Any]] = []
    last_entry_bar = -288  # 1 day cooldown
    asia_bars_count = ASIA_RANGE_HOURS * 12

    if "Volume" not in df.columns:
        print(f"[err] {symbol}: Volume column missing", flush=True)
        return out

    for i in range(asia_bars_count + 50, len(df) - MAX_HOLD_BARS - 1):
        if i - last_entry_bar < 288:
            continue
        bar_time = df.index[i]
        if hasattr(bar_time, "tzinfo") and bar_time.tzinfo is None:
            bar_time = bar_time.replace(tzinfo=timezone.utc)
        if not _in_window(bar_time, session_window):
            continue
        # Asia range
        asia_seg = df.iloc[i - asia_bars_count: i]
        asia_high = float(asia_seg["High"].max())
        asia_low = float(asia_seg["Low"].min())
        # Volume spike
        cur_vol = float(df["Volume"].iloc[i])
        avg_vol = float(df["Volume"].iloc[max(0, i - 50): i].mean())
        if avg_vol <= 0 or cur_vol < vol_spike * avg_vol:
            continue
        bar_close = float(df["Close"].iloc[i])
        atr = float(df["atr7"].iloc[i]) if "atr7" in df.columns else (float(df["High"].iloc[i]) - float(df["Low"].iloc[i]))

        sig_dir = None
        ep = sl = None
        if bar_close > asia_high:
            sig_dir = "BUY"
            ep = bar_close + fric_half
            sl = asia_high - SL_ATR_MULT * atr
        elif bar_close < asia_low:
            sig_dir = "SELL"
            ep = bar_close - fric_half
            sl = asia_low + SL_ATR_MULT * atr
        if sig_dir is None:
            continue
        if i + 1 >= len(df):
            continue

        sl_dist = abs(ep - sl)
        if sl_dist <= 0:
            continue
        tp = ep + MIN_RR_HARD * sl_dist if sig_dir == "BUY" else ep - MIN_RR_HARD * sl_dist

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
        "EV>2.0": ev > SURVIVOR_EV_MIN, "PF>1.5": pf > SURVIVOR_PF_MIN,
        "WR>=40%": rate >= SURVIVOR_WR_MIN, "N>=20": n >= SURVIVOR_N_MIN,
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

def extract_all(from_iso, to_iso, vol_spike, session_window):
    from modules.indicators import add_indicators
    out = []
    for symbol in PAIRS_S7:
        try:
            df = _fetch_range_5m(symbol, from_iso, to_iso)
            df = add_indicators(df).dropna()
            ents = extract_orb_entries(symbol, df, vol_spike, session_window)
            print(f"[entries] {symbol} vol×{vol_spike} {session_window}: {len(ents)}", flush=True)
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
        args.output_dir = ("/tmp/phase5-orb-dryrun" if args.dry_run
                           else "raw/bt-results/phase5-orb-2026-04-25")

    print(f"=" * 90)
    print(f"Phase 5 S7 — ORB 365日 BT (PAIR 限定: {PAIRS_S7})")
    print(f"  alpha_cell = {ALPHA_CELL:.5f} (Bonferroni 0.05/{N_CELLS})")
    print(f"=" * 90)

    if args.dry_run:
        baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t, 0) for t in synth_null_trades(300, seed=42)]]
        per_extraction = {(p, vs, sk): synth_null_trades(15, seed=hash((p, vs, sk)) & 0xff)
                          for p in PAIRS_S7 for vs in VOLUME_SPIKE_GRID for sk in SESSION_GRID}
    else:
        baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t, 0) for t in synth_null_trades(300, seed=42)]]
        per_extraction = {}
        # extract per session_key, vol_spike (PAIR は extract_all 内でループ)
        for vs in VOLUME_SPIKE_GRID:
            for sk, sw in SESSION_GRID.items():
                ents = extract_all(args.from_iso, args.to_iso, vs, sw)
                per_extraction[(vs, sk)] = ents

    print(f"\n--- Cell results ---")
    print(f"{'cell':<6}{'pair':<11}{'vol×':>5}{'sess':<13}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}"
          f"{'p':>9}{'WF':>5}{'verdict':>10}")
    grid = []
    cell_id = 0
    for pair in PAIRS_S7:
        for vs in VOLUME_SPIKE_GRID:
            for sk in SESSION_GRID:
                cell_id += 1
                cell = {"id": f"C{cell_id:02d}", "pair": pair, "vol_spike": vs, "session": sk}
                if args.dry_run:
                    trades = per_extraction.get((pair, vs, sk), [])
                else:
                    all_ents = per_extraction.get((vs, sk), [])
                    trades = [t for t in all_ents if t.get("pair") == pair]
                r = evaluate_cell(trades, cell, baseline_pnls=baseline_pnls)
                grid.append(r)
                pf_s = f"{r['pf']:.2f}" if r['pf'] != float("inf") else " inf"
                print(f"{r['cell_id']:<6}{pair[:10]:<11}{vs:>5.1f}{sk[:12]:<13}"
                      f"{r['n']:>5}{r['rate_pct']:>6.1f}{r['ev']:>+7.2f}{pf_s:>6}"
                      f"{r['p_welch']:>9.4f}{r['wf_agree']:>3}/{len(r['wf_signs'])}"
                      f"{r['verdict']:>10}")

    survivors = [r for r in grid if r["verdict"] == "SURVIVOR"]
    meta = "SURVIVOR_PRESENT" if survivors else "ALL_REJECT"
    print(f"\nMeta verdict: {meta}")

    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "pre_reg": "knowledge-base/wiki/analyses/phase5-9d-edge-matrix-2026-04-25.md (S7)",
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
