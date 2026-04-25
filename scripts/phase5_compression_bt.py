#!/usr/bin/env python3
"""
Phase 5 — S2 Volatility Compression Breakout — 365-day BT (pre-reg LOCKED 2026-04-25)

Companion to:
    knowledge-base/wiki/analyses/phase5-pure-edge-portfolio-2026-04-25.md (S2)

Hypothesis:
    BB width pct < threshold (収縮) → expansion 解放時に breakout 方向そのものが
    エネルギー方向. オシレーター完全排除. RR ≥ 3.0 強制下限.

Cell grid (18 cells):
    bb_width_pct: {0.05, 0.10, 0.15}
    tp_bb_std_mult: {3.0, 4.0, 5.0}
    breakout_type: {strict_close_break, atr_distance_break}

Bonferroni: alpha_cell = 0.05 / 18 = 0.00278

Binding success (SURVIVOR, all AND):
    EV > +2.0 p/trade
    PF > 1.5
    WR >= 30% (低 WR 高 RR 設計)
    N >= 20 (年間)
    実 RR (摩擦込み) >= 2.5
    Welch p < 0.00278
    WF 4/4 same-sign
"""
from __future__ import annotations

import argparse, json, math, os, statistics, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # project root for modules.*
from bb_squeeze_rescue_bt import (  # type: ignore
    wilson_lower, welch_t_test, simulate_pnl,
    PIP_MULT, FRICTION_RT, PAIRS, MAX_HOLD_BARS, BAR_MIN,
    MAE_CATASTROPHIC_PIPS, _fetch_range_5m, synth_null_trades,
)

# ---------------------------------------------------------------------------
# Configuration (LOCKED)
# ---------------------------------------------------------------------------

BB_WIDTH_PCT_GRID = [0.05, 0.10, 0.15]
TP_BB_STD_MULT_GRID = [3.0, 4.0, 5.0]
BREAKOUT_TYPE_GRID = ["close_break", "atr_distance"]
N_CELLS = len(BB_WIDTH_PCT_GRID) * len(TP_BB_STD_MULT_GRID) * len(BREAKOUT_TYPE_GRID)
ALPHA_CELL = 0.05 / N_CELLS  # 0.00278

BB_WIDTH_LOOKBACK = 100
SL_BB_STD_MULT = 0.7   # 固定 (RR を TP 側で制御)
MIN_RR_HARD = 3.0
ATR_DISTANCE_MULT = 0.3  # atr_distance breakout: |close - mid| > 0.3 ATR

# Binding
SURVIVOR_EV_MIN = 2.0
SURVIVOR_PF_MIN = 1.5
SURVIVOR_WR_MIN = 30.0
SURVIVOR_N_MIN = 20
SURVIVOR_REAL_RR_MIN = 2.5
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

def extract_compression_entries(symbol: str, df, bb_width_pct: float,
                                breakout_type: str) -> List[Dict[str, Any]]:
    """S2 signal extraction.
    Squeeze (BB width < pct percentile) + breakout direction = signal direction.
    """
    pip = PIP_MULT.get(symbol, 100.0)
    fric_half = FRICTION_RT.get(symbol, 2.0) / 2.0 / pip
    out: List[Dict[str, Any]] = []
    last_entry_bar = -10

    if "bb_width" not in df.columns or "bb_upper" not in df.columns:
        print(f"[err] {symbol}: bb_width/bb_upper missing in df", flush=True)
        return out

    for i in range(BB_WIDTH_LOOKBACK + 50, len(df) - MAX_HOLD_BARS - 1):
        if i - last_entry_bar < 5:
            continue
        # BB width percentile (rolling)
        recent_bw = df["bb_width"].iloc[i - BB_WIDTH_LOOKBACK: i]
        if len(recent_bw) < BB_WIDTH_LOOKBACK or recent_bw.isna().any():
            continue
        threshold = recent_bw.quantile(bb_width_pct)
        cur_bw = float(df["bb_width"].iloc[i])
        if cur_bw >= threshold:
            continue  # not in squeeze

        bb_upper = float(df["bb_upper"].iloc[i])
        bb_lower = float(df["bb_lower"].iloc[i])
        bb_mid = (bb_upper + bb_lower) / 2.0
        bb_std = (bb_upper - bb_lower) / 4.0
        if bb_std <= 0:
            continue

        bar = df.iloc[i]
        bar_close = float(bar["Close"])
        atr = float(df["atr7"].iloc[i]) if "atr7" in df.columns else (float(bar["High"]) - float(bar["Low"]))

        sig_dir = None
        if breakout_type == "close_break":
            if bar_close > bb_upper:
                sig_dir = "BUY"
            elif bar_close < bb_lower:
                sig_dir = "SELL"
        else:  # atr_distance
            dist = bar_close - bb_mid
            if dist > ATR_DISTANCE_MULT * atr and bar_close > bb_upper * 0.998:
                sig_dir = "BUY"
            elif dist < -ATR_DISTANCE_MULT * atr and bar_close < bb_lower * 1.002:
                sig_dir = "SELL"

        if sig_dir is None:
            continue
        if i + 1 >= len(df):
            continue

        ep_raw = float(df.iloc[i + 1]["Open"])
        ep = ep_raw + fric_half if sig_dir == "BUY" else ep_raw - fric_half
        sl_dist = SL_BB_STD_MULT * bb_std
        sl = ep - sl_dist if sig_dir == "BUY" else ep + sl_dist

        future = df.iloc[i + 1: i + 1 + MAX_HOLD_BARS]
        bars = [(future.index[k],
                 float(future.iloc[k]["Open"]),
                 float(future.iloc[k]["High"]),
                 float(future.iloc[k]["Low"]),
                 float(future.iloc[k]["Close"])) for k in range(len(future))]
        out.append({
            "pair": symbol, "symbol": symbol,
            "direction": sig_dir,
            "entry_price": ep,
            "sl": sl,
            "tp": None,
            "bars": bars,
            "entry_ts": df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i]),
            "bb_std": bb_std,
        })
        last_entry_bar = i

    return out

def attach_tp(trade: Dict[str, Any], tp_mult: float) -> Dict[str, Any]:
    ep = trade["entry_price"]
    bb_std = trade["bb_std"]
    if trade["direction"] == "BUY":
        tp = ep + tp_mult * bb_std
    else:
        tp = ep - tp_mult * bb_std
    return {**trade, "tp": tp}

# ---------------------------------------------------------------------------
# Cell evaluation
# ---------------------------------------------------------------------------

def evaluate_cell(trades_template: List[Dict[str, Any]], cell: Dict[str, Any],
                  baseline_pnls: Optional[List[float]] = None) -> Dict[str, Any]:
    # Filter: RR ≥ MIN_RR_HARD のみ採用
    tp_trades = []
    for t in trades_template:
        tp_t = attach_tp(t, cell["tp_mult"])
        sl_dist = abs(tp_t["entry_price"] - tp_t["sl"])
        tp_dist = abs(tp_t["tp"] - tp_t["entry_price"])
        if sl_dist <= 0 or tp_dist / sl_dist < MIN_RR_HARD:
            continue
        tp_trades.append(tp_t)

    sims = [simulate_pnl(t, time_floor_min=0) for t in tp_trades]
    pnls = [s["pnl_pips"] for s in sims]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    sum_pos = sum(p for p in pnls if p > 0)
    sum_neg = -sum(p for p in pnls if p < 0)
    ev = sum(pnls) / n if n else 0.0
    pf = sum_pos / sum_neg if sum_neg > 0 else (float("inf") if sum_pos > 0 else 0.0)
    wlo = wilson_lower(wins, n)
    rate = wins / n * 100 if n else 0.0
    avg_win = (sum_pos / wins) if wins else 0.0
    avg_loss = (sum_neg / (n - wins)) if n - wins > 0 else 0.0
    real_rr = avg_win / avg_loss if avg_loss > 0 else 0.0
    if baseline_pnls is not None and len(baseline_pnls) >= 2 and n >= 2:
        _, p_welch = welch_t_test(pnls, baseline_pnls)
    else:
        p_welch = 1.0
    wf_signs: List[int] = []
    if n >= WF_WINDOWS * 5:
        chunk = n // WF_WINDOWS
        for w in range(WF_WINDOWS):
            seg = pnls[w*chunk:(w+1)*chunk] if w < WF_WINDOWS-1 else pnls[w*chunk:]
            if seg:
                wf_signs.append(1 if statistics.mean(seg) > 0 else (-1 if statistics.mean(seg) < 0 else 0))
    wf_agree = max(wf_signs.count(1), wf_signs.count(-1)) if wf_signs else 0
    breaker_n = sum(1 for s in sims if s["exit_reason"] == "MAE_BREAKER")
    breaker_pct = breaker_n / n * 100 if n else 0.0
    floor_infeasible = breaker_pct > FLOOR_INFEASIBLE_BREAKER_PCT

    survivor_conds = {
        "EV>2.0": ev > SURVIVOR_EV_MIN,
        "PF>1.5": pf > SURVIVOR_PF_MIN,
        "WR>=30%": rate >= SURVIVOR_WR_MIN,
        "N>=20": n >= SURVIVOR_N_MIN,
        "RealRR>=2.5": real_rr >= SURVIVOR_REAL_RR_MIN,
        f"p<{ALPHA_CELL:.5f}": p_welch < ALPHA_CELL,
        "WF_4/4": wf_agree >= SURVIVOR_WF_AGREE,
        "FLOOR_FEASIBLE": not floor_infeasible,
    }
    verdict = "SURVIVOR" if all(survivor_conds.values()) else "REJECT"

    return {
        "cell_id": cell["id"], "params": cell,
        "n": n, "wins": wins, "rate_pct": rate,
        "ev": ev, "pf": pf, "wilson_lo_pct": wlo,
        "avg_win": avg_win, "avg_loss": avg_loss, "real_rr": real_rr,
        "p_welch": p_welch, "wf_signs": wf_signs, "wf_agree": wf_agree,
        "mae_breaker_n": breaker_n, "mae_breaker_pct": breaker_pct,
        "floor_infeasible": floor_infeasible,
        "survivor_conds": survivor_conds,
        "verdict": verdict, "pnls": pnls,
    }

# ---------------------------------------------------------------------------
# Real extraction
# ---------------------------------------------------------------------------

def extract_all(from_iso: str, to_iso: str, bb_width_pct: float,
                breakout_type: str) -> List[Dict[str, Any]]:
    from modules.indicators import add_indicators
    out: List[Dict[str, Any]] = []
    for symbol in PAIRS:
        try:
            df = _fetch_range_5m(symbol, from_iso, to_iso)
            df = add_indicators(df).dropna()
            ents = extract_compression_entries(symbol, df, bb_width_pct, breakout_type)
            print(f"[entries] {symbol} pct={bb_width_pct} type={breakout_type}: {len(ents)}", flush=True)
            out.extend(ents)
        except Exception as e:
            print(f"[err] {symbol}: {e}", flush=True)
    return out

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_iso", default="2025-04-26")
    ap.add_argument("--to", dest="to_iso", default="2026-04-25")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.output_dir is None:
        args.output_dir = ("/tmp/phase5-compression-dryrun" if args.dry_run
                           else "raw/bt-results/phase5-compression-2026-04-25")

    print("=" * 90)
    print("Phase 5 S2 — Volatility Compression Breakout 365日 BT (pre-reg LOCKED)")
    print(f"  alpha_cell = {ALPHA_CELL:.5f} (Bonferroni 0.05/{N_CELLS})")
    print(f"  bb_width_pct × tp_mult × breakout = "
          f"{len(BB_WIDTH_PCT_GRID)}×{len(TP_BB_STD_MULT_GRID)}×{len(BREAKOUT_TYPE_GRID)} = {N_CELLS}")
    print(f"  SURVIVOR: EV>{SURVIVOR_EV_MIN} PF>{SURVIVOR_PF_MIN} WR>={SURVIVOR_WR_MIN}% "
          f"N>={SURVIVOR_N_MIN} RealRR>={SURVIVOR_REAL_RR_MIN}")
    print("=" * 90)

    if args.dry_run:
        print(f"[DRY-RUN] synthetic null trades")
        baseline_trades = synth_null_trades(300, seed=42)
        per_extraction = {}
        for pct in BB_WIDTH_PCT_GRID:
            for bt in BREAKOUT_TYPE_GRID:
                # synthesize trades with bb_std attached
                ts = synth_null_trades(40, seed=hash((pct, bt)) & 0xff)
                for t in ts:
                    t["bb_std"] = 0.001  # constant for dry-run
                per_extraction[(pct, bt)] = ts
    else:
        print(f"[LIVE] {args.from_iso} → {args.to_iso}")
        baseline_trades = synth_null_trades(300, seed=42)
        per_extraction = {}
        for pct in BB_WIDTH_PCT_GRID:
            for bt in BREAKOUT_TYPE_GRID:
                per_extraction[(pct, bt)] = extract_all(args.from_iso, args.to_iso, pct, bt)

    baseline_sims = [simulate_pnl(t, 0) for t in baseline_trades]
    baseline_pnls = [s["pnl_pips"] for s in baseline_sims]

    print(f"\n--- Cell results ---")
    print(f"{'cell':<6}{'pct':>6}{'TPm':>5}{'btype':<14}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}"
          f"{'rRR':>6}{'p':>9}{'WF':>5}{'MAE!%':>7}{'verdict':>10}")
    grid = []
    cell_id = 0
    for pct in BB_WIDTH_PCT_GRID:
        for tp_m in TP_BB_STD_MULT_GRID:
            for bt in BREAKOUT_TYPE_GRID:
                cell_id += 1
                cell = {"id": f"C{cell_id:02d}", "bb_pct": pct,
                        "tp_mult": tp_m, "breakout": bt}
                trades = per_extraction.get((pct, bt), [])
                r = evaluate_cell(trades, cell, baseline_pnls=baseline_pnls)
                grid.append(r)
                pf_s = f"{r['pf']:.2f}" if r['pf'] != float("inf") else " inf"
                print(f"{r['cell_id']:<6}{pct:>6.2f}{tp_m:>5.1f}{bt[:13]:<14}"
                      f"{r['n']:>5}{r['rate_pct']:>6.1f}{r['ev']:>+7.2f}{pf_s:>6}"
                      f"{r['real_rr']:>6.2f}{r['p_welch']:>9.4f}"
                      f"{r['wf_agree']:>3}/{len(r['wf_signs'])}"
                      f"{r['mae_breaker_pct']:>6.1f}%{r['verdict']:>10}")

    survivors = [r for r in grid if r["verdict"] == "SURVIVOR"]
    meta = "SURVIVOR_PRESENT" if survivors else "ALL_REJECT"
    print(f"\nMeta verdict: {meta}")

    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "pre_reg": "knowledge-base/wiki/analyses/phase5-pure-edge-portfolio-2026-04-25.md (S2)",
        "alpha_cell": ALPHA_CELL, "n_cells": N_CELLS,
        "mae_catastrophic_pips": MAE_CATASTROPHIC_PIPS,
        "from": args.from_iso, "to": args.to_iso, "dry_run": args.dry_run,
        "meta_verdict": meta, "survivors_count": len(survivors),
        "cells": [{k: v for k, v in r.items() if k != "pnls"} for r in grid],
    }
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n[written] {out_dir / 'summary.json'}")

    if args.dry_run:
        return 0 if not survivors else 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
