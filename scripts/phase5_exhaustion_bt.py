#!/usr/bin/env python3
"""
Phase 5 — S3 Z-Score Exhaustion — 365-day BT (pre-reg LOCKED 2026-04-25)

Companion:
    knowledge-base/wiki/analyses/phase5-pure-edge-portfolio-2026-04-25.md (S3)

Hypothesis:
    1H bar level で価格が EMA200 から |z| > 3σ 乖離 = mean revert への極限値.
    Carry 解消 / panic / capitulation の真空地帯への巻き戻しを獲るカウンター.
    オシレーター完全排除. RR ≥ 2.0 強制.

Cell grid (12 cells):
    z_threshold: {2.5, 3.0, 3.5}
    baseline: {EMA200, SMA100}
    tp_target_ratio: {0.5, 1.0}  (baseline までの距離の何%まで TP)

Bonferroni: alpha_cell = 0.05 / 12 = 0.00417

Binding success (SURVIVOR):
    EV > +5.0 p/trade
    PF > 2.0
    WR >= 50%
    N >= 8 (年間, 0.3% 発生想定で月 ~3-5)
    Welch p < 0.00417
    WF 4/4 same-sign
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # project root for modules.*
from bb_squeeze_rescue_bt import (  # type: ignore
    wilson_lower, welch_t_test, simulate_pnl,
    PIP_MULT, FRICTION_RT, PAIRS, MAX_HOLD_BARS, BAR_MIN,
    MAE_CATASTROPHIC_PIPS, synth_null_trades,
)

# ---------------------------------------------------------------------------
# Configuration (LOCKED) — 1H bar based
# ---------------------------------------------------------------------------

Z_THRESHOLD_GRID = [2.5, 3.0, 3.5]
BASELINE_GRID = ["EMA200", "SMA100"]
TP_TARGET_RATIO_GRID = [0.5, 1.0]
N_CELLS = len(Z_THRESHOLD_GRID) * len(BASELINE_GRID) * len(TP_TARGET_RATIO_GRID)
ALPHA_CELL = 0.05 / N_CELLS  # 0.00417

Z_LOOKBACK = 100
COOLDOWN_BARS = 24
SL_ATR_MULT = 0.5
MIN_RR_HARD = 2.0
EXH_BAR_MIN = 60          # 1H bars
EXH_MAX_HOLD_BARS = 24    # 1日 hold

# Binding
SURVIVOR_EV_MIN = 5.0
SURVIVOR_PF_MIN = 2.0
SURVIVOR_WR_MIN = 50.0
SURVIVOR_N_MIN = 8
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

# ---------------------------------------------------------------------------
# 1H data fetch (override of bb_squeeze 5m fetcher)
# ---------------------------------------------------------------------------

def _fetch_range_1h(symbol: str, from_iso: str, to_iso: str):
    last_err = None
    try:
        from modules.data import fetch_ohlcv_massive
        days = (datetime.fromisoformat(to_iso[:10]) - datetime.fromisoformat(from_iso[:10])).days + 5
        df = fetch_ohlcv_massive(symbol, "1h", days=days)
        df = df.loc[(df.index >= from_iso) & (df.index <= to_iso)]
        if len(df) > 200:
            print(f"[MASSIVE/1h] {symbol}: {len(df)} bars", flush=True)
            return df
        last_err = f"massive returned {len(df)}"
    except Exception as e:
        last_err = f"massive failed: {e}"
    try:
        from modules.data import fetch_ohlcv_range
        df1 = fetch_ohlcv_range(symbol, from_iso, to_iso, interval="1h")
        if len(df1) > 200:
            print(f"[OANDA/1h] {symbol}: {len(df1)} bars", flush=True)
            return df1
    except Exception as e:
        last_err = f"oanda failed: {e}; prev: {last_err}"
    raise RuntimeError(f"data fetch failed: {last_err}")

# ---------------------------------------------------------------------------
# Signal extraction
# ---------------------------------------------------------------------------

def extract_exhaustion_entries(symbol: str, df, z_threshold: float,
                               baseline: str) -> List[Dict[str, Any]]:
    pip = PIP_MULT.get(symbol, 100.0)
    fric_half = FRICTION_RT.get(symbol, 2.0) / 2.0 / pip
    out: List[Dict[str, Any]] = []
    last_entry_bar = -COOLDOWN_BARS

    # Compute baseline series
    if baseline == "EMA200":
        if len(df) < 200:
            return out
        baseline_series = df["Close"].ewm(span=200, adjust=False).mean()
    else:  # SMA100
        if len(df) < 100:
            return out
        baseline_series = df["Close"].rolling(100).mean()

    for i in range(max(200, Z_LOOKBACK + 50), len(df) - EXH_MAX_HOLD_BARS - 1):
        if i - last_entry_bar < COOLDOWN_BARS:
            continue
        bl = baseline_series.iloc[i]
        if math.isnan(bl):
            continue
        recent_close = df["Close"].iloc[i - Z_LOOKBACK: i]
        sigma = recent_close.std()
        if not (sigma > 0):
            continue
        bar_close = float(df["Close"].iloc[i])
        z = (bar_close - bl) / sigma
        if abs(z) < z_threshold:
            continue

        atr = float(df["atr7"].iloc[i]) if "atr7" in df.columns else (
            float(df["High"].iloc[i]) - float(df["Low"].iloc[i]))

        sig_dir = None
        if z >= z_threshold:
            sig_dir = "SELL"
            ep = bar_close - fric_half
            sl = bar_close + SL_ATR_MULT * atr
        elif z <= -z_threshold:
            sig_dir = "BUY"
            ep = bar_close + fric_half
            sl = bar_close - SL_ATR_MULT * atr

        if sig_dir is None:
            continue
        if i + 1 >= len(df):
            continue

        future = df.iloc[i + 1: i + 1 + EXH_MAX_HOLD_BARS]
        bars = [(future.index[k],
                 float(future.iloc[k]["Open"]),
                 float(future.iloc[k]["High"]),
                 float(future.iloc[k]["Low"]),
                 float(future.iloc[k]["Close"])) for k in range(len(future))]
        out.append({
            "pair": symbol, "symbol": symbol,
            "direction": sig_dir, "entry_price": ep, "sl": sl, "tp": None,
            "bars": bars,
            "entry_ts": df.index[i].isoformat() if hasattr(df.index[i], 'isoformat') else str(df.index[i]),
            "baseline_value": float(bl),
            "z_score": float(z),
        })
        last_entry_bar = i

    return out

def attach_tp(trade: Dict[str, Any], target_ratio: float) -> Dict[str, Any]:
    ep = trade["entry_price"]
    bl = trade["baseline_value"]
    if trade["direction"] == "BUY":
        tp = ep + target_ratio * (bl - ep)
    else:
        tp = ep - target_ratio * (ep - bl)
    return {**trade, "tp": tp}

# ---------------------------------------------------------------------------
# Cell evaluation
# ---------------------------------------------------------------------------

def evaluate_cell(trades_template: List[Dict[str, Any]], cell: Dict[str, Any],
                  baseline_pnls: Optional[List[float]] = None) -> Dict[str, Any]:
    tp_trades = []
    for t in trades_template:
        tp_t = attach_tp(t, cell["tp_target_ratio"])
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
    if baseline_pnls is not None and len(baseline_pnls) >= 2 and n >= 2:
        _, p_welch = welch_t_test(pnls, baseline_pnls)
    else:
        p_welch = 1.0
    wf_signs: List[int] = []
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
        "EV>5.0": ev > SURVIVOR_EV_MIN,
        "PF>2.0": pf > SURVIVOR_PF_MIN,
        "WR>=50%": rate >= SURVIVOR_WR_MIN,
        "N>=8": n >= SURVIVOR_N_MIN,
        f"p<{ALPHA_CELL:.5f}": p_welch < ALPHA_CELL,
        "WF_4/4": wf_agree >= SURVIVOR_WF_AGREE,
        "FLOOR_FEASIBLE": not floor_infeasible,
    }
    verdict = "SURVIVOR" if all(survivor_conds.values()) else "REJECT"
    return {
        "cell_id": cell["id"], "params": cell,
        "n": n, "wins": wins, "rate_pct": rate,
        "ev": ev, "pf": pf, "wilson_lo_pct": wlo,
        "p_welch": p_welch, "wf_signs": wf_signs, "wf_agree": wf_agree,
        "mae_breaker_n": breaker_n, "mae_breaker_pct": breaker_pct,
        "floor_infeasible": floor_infeasible,
        "survivor_conds": survivor_conds,
        "verdict": verdict, "pnls": pnls,
    }

# ---------------------------------------------------------------------------
# Real extraction
# ---------------------------------------------------------------------------

def extract_all(from_iso: str, to_iso: str, z_threshold: float, baseline: str) -> List[Dict[str, Any]]:
    from modules.indicators import add_indicators
    out: List[Dict[str, Any]] = []
    for symbol in PAIRS:
        try:
            df = _fetch_range_1h(symbol, from_iso, to_iso)
            df = add_indicators(df).dropna()
            ents = extract_exhaustion_entries(symbol, df, z_threshold, baseline)
            print(f"[entries] {symbol} z={z_threshold} {baseline}: {len(ents)}", flush=True)
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
        args.output_dir = ("/tmp/phase5-exhaustion-dryrun" if args.dry_run
                           else "raw/bt-results/phase5-exhaustion-2026-04-25")

    print("=" * 90)
    print("Phase 5 S3 — Z-Score Exhaustion 365日 BT (pre-reg LOCKED, 1H bars)")
    print(f"  alpha_cell = {ALPHA_CELL:.5f} (Bonferroni 0.05/{N_CELLS})")
    print(f"  z_threshold × baseline × tp_ratio = "
          f"{len(Z_THRESHOLD_GRID)}×{len(BASELINE_GRID)}×{len(TP_TARGET_RATIO_GRID)} = {N_CELLS}")
    print(f"  SURVIVOR: EV>{SURVIVOR_EV_MIN} PF>{SURVIVOR_PF_MIN} WR>={SURVIVOR_WR_MIN}% N>={SURVIVOR_N_MIN}")
    print("=" * 90)

    if args.dry_run:
        print(f"[DRY-RUN] synthetic null trades")
        baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t, 0) for t in synth_null_trades(300, seed=42)]]
        per_extraction = {}
        for z in Z_THRESHOLD_GRID:
            for bl in BASELINE_GRID:
                ts = synth_null_trades(20, seed=hash((z, bl)) & 0xff)
                for t in ts:
                    t["baseline_value"] = t["entry_price"] * 0.998 if t["direction"] == "SELL" else t["entry_price"] * 1.002
                    t["z_score"] = z if t["direction"] == "SELL" else -z
                per_extraction[(z, bl)] = ts
    else:
        print(f"[LIVE] {args.from_iso} → {args.to_iso}")
        baseline_pnls = [s["pnl_pips"] for s in [simulate_pnl(t, 0) for t in synth_null_trades(300, seed=42)]]
        per_extraction = {}
        for z in Z_THRESHOLD_GRID:
            for bl in BASELINE_GRID:
                per_extraction[(z, bl)] = extract_all(args.from_iso, args.to_iso, z, bl)

    print(f"\n--- Cell results ---")
    print(f"{'cell':<6}{'z':>5}{'base':<8}{'TPr':>5}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}"
          f"{'p':>9}{'WF':>5}{'MAE!%':>7}{'verdict':>10}")
    grid = []
    cell_id = 0
    for z in Z_THRESHOLD_GRID:
        for bl in BASELINE_GRID:
            for tr in TP_TARGET_RATIO_GRID:
                cell_id += 1
                cell = {"id": f"C{cell_id:02d}", "z_threshold": z,
                        "baseline": bl, "tp_target_ratio": tr}
                trades = per_extraction.get((z, bl), [])
                r = evaluate_cell(trades, cell, baseline_pnls=baseline_pnls)
                grid.append(r)
                pf_s = f"{r['pf']:.2f}" if r['pf'] != float("inf") else " inf"
                print(f"{r['cell_id']:<6}{z:>5.1f}{bl:<8}{tr:>5.1f}"
                      f"{r['n']:>5}{r['rate_pct']:>6.1f}{r['ev']:>+7.2f}{pf_s:>6}"
                      f"{r['p_welch']:>9.4f}"
                      f"{r['wf_agree']:>3}/{len(r['wf_signs'])}"
                      f"{r['mae_breaker_pct']:>6.1f}%{r['verdict']:>10}")

    survivors = [r for r in grid if r["verdict"] == "SURVIVOR"]
    meta = "SURVIVOR_PRESENT" if survivors else "ALL_REJECT"
    print(f"\nMeta verdict: {meta}")

    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "pre_reg": "knowledge-base/wiki/analyses/phase5-pure-edge-portfolio-2026-04-25.md (S3)",
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
