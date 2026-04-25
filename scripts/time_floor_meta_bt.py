#!/usr/bin/env python3
"""
Time-Floor Meta Rescue BT — pre-registered 365-day cross-strategy validation.

Companion to:
    knowledge-base/wiki/analyses/time-floor-meta-rescue-2026-04-25.md

Hypothesis (H1):
    Holding entries to a minimum hold time (e.g. 20 min) before allowing TP/SL/
    TIME_DECAY_EXIT improves EV across multiple under-performing strategies.
    Meta-acceptance: at least 3 of 7 target strategies achieve SURVIVOR in B3
    (hold >= 20 min) cell.

Cell grid (7 strategies × 5 hold floors = 35 BT cells):
    Strategies: ema_trend_scalp, sr_channel_reversal, fib_reversal, engulfing_bb,
                stoch_trend_pullback, macdh_reversal, bb_squeeze_breakout
    Hold floors (B-axis): 0 (B0 baseline), 5, 10, 20, 30 minutes

Bonferroni: alpha_cell = 0.05 / 35 = 0.00143

Binding success per (strategy, cell), all AND:
    EV > +0.5 p/trade
    PF > 1.15
    N >= 30
    Wilson_lo (WR) > 0.7 × observed WR (overfit防止)
    Welch p < 0.00143 vs B0 baseline (per strategy)
    WF 90d × 4 windows: same-sign EV in all 4

Meta-acceptance:
    At B3 (hold >= 20m), >= 3 of 7 strategies SURVIVOR

Survivor-bias defence (catastrophic MAE breaker):
    During the time-floor period (hold < TIME_FLOOR_MIN), running MAE breaching
    MAE_CATASTROPHIC_PIPS = 15 forces immediate close at -MAE depth (loss).
    Diagnostic: per-cell breaker_pct printed; cells with breaker_pct > 30 are
    flagged as "FLOOR_INFEASIBLE" (account-blowup risk in production).

Usage:
    python3 scripts/time_floor_meta_bt.py --from 2025-04-26 --to 2026-04-25 \\
        --output-dir raw/bt-results/time-floor-meta-2026-04-25
    python3 scripts/time_floor_meta_bt.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
from datetime import datetime, timedelta, timezone
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

# Reuse helpers + simulator from companion harness
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bb_squeeze_rescue_bt import (  # type: ignore
    wilson_lower, welch_t_test, simulate_pnl, _utc_session,
    PIP_MULT, FRICTION_RT, PAIRS, MAX_HOLD_BARS, BAR_MIN,
    MAE_CATASTROPHIC_PIPS,
)

# ---------------------------------------------------------------------------
# Configuration (LOCKED from pre-reg)
# ---------------------------------------------------------------------------

TARGET_STRATEGIES: List[str] = [
    "ema_trend_scalp",
    "sr_channel_reversal",
    "fib_reversal",
    "engulfing_bb",
    "stoch_trend_pullback",
    "macdh_reversal",
    "bb_squeeze_breakout",
]

HOLD_FLOORS: List[int] = [0, 5, 10, 20, 30]   # B0..B4

N_CELLS_TOTAL = len(TARGET_STRATEGIES) * len(HOLD_FLOORS)  # 35
ALPHA_CELL = 0.05 / N_CELLS_TOTAL                          # 0.00143

# Per-cell SURVIVOR criteria
SURVIVOR_EV_MIN = 0.5
SURVIVOR_PF_MIN = 1.15
SURVIVOR_N_MIN = 30
SURVIVOR_WLO_VS_OBS_RATIO = 0.70
SURVIVOR_WF_AGREE = 4
WF_WINDOWS = 4

# Meta-acceptance
META_PRIMARY_FLOOR = 20    # main hypothesis cell B3
META_MIN_SURVIVORS = 3

# Survivor-bias diagnostic
FLOOR_INFEASIBLE_BREAKER_PCT = 30.0

# ---------------------------------------------------------------------------
# Cell evaluation (per-strategy × per-floor)
# ---------------------------------------------------------------------------

def evaluate_strategy_floor(trades: List[Dict[str, Any]], strategy: str,
                            time_floor_min: int,
                            baseline_pnls: Optional[List[float]] = None,
                            obs_wr_pct: float = 0.0) -> Dict[str, Any]:
    """Evaluate one (strategy, floor) cell. Trades are pre-filtered to strategy.
    Returns dict including verdict and survivor-bias diagnostics.
    """
    sims = [simulate_pnl(t, time_floor_min) for t in trades]
    pnls = [s["pnl_pips"] for s in sims]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    sum_pos = sum(p for p in pnls if p > 0)
    sum_neg = -sum(p for p in pnls if p < 0)
    ev = (sum(pnls) / n) if n else 0.0
    pf = (sum_pos / sum_neg) if sum_neg > 0 else (float("inf") if sum_pos > 0 else 0.0)
    wlo = wilson_lower(wins, n)
    rate = (wins / n * 100) if n else 0.0
    # Welch
    if baseline_pnls is not None and time_floor_min > 0 and len(baseline_pnls) >= 2 and n >= 2:
        _, p_welch = welch_t_test(pnls, baseline_pnls)
    else:
        p_welch = 1.0
    # WF
    wf_signs: List[int] = []
    if n >= WF_WINDOWS * 5:
        chunk = n // WF_WINDOWS
        for w in range(WF_WINDOWS):
            seg = pnls[w*chunk:(w+1)*chunk] if w < WF_WINDOWS-1 else pnls[w*chunk:]
            if not seg: continue
            seg_ev = statistics.mean(seg)
            wf_signs.append(1 if seg_ev > 0 else (-1 if seg_ev < 0 else 0))
    wf_agree = max(wf_signs.count(1), wf_signs.count(-1)) if wf_signs else 0
    # Survivor-bias diagnostics
    breaker_n = sum(1 for s in sims if s["exit_reason"] == "MAE_BREAKER")
    breaker_pct = (breaker_n / n * 100) if n else 0.0
    floor_infeasible = breaker_pct > FLOOR_INFEASIBLE_BREAKER_PCT
    # Verdict
    survivor_conds = {
        "EV": ev > SURVIVOR_EV_MIN,
        "PF": pf > SURVIVOR_PF_MIN,
        "N": n >= SURVIVOR_N_MIN,
        f"Wlo>{SURVIVOR_WLO_VS_OBS_RATIO*100:.0f}%obs": wlo > obs_wr_pct * SURVIVOR_WLO_VS_OBS_RATIO,
        f"p<{ALPHA_CELL:.5f}": p_welch < ALPHA_CELL if time_floor_min > 0 else True,
        "WF_all_same": wf_agree >= SURVIVOR_WF_AGREE,
        "FLOOR_FEASIBLE": not floor_infeasible,
    }
    verdict = "REJECT"
    if time_floor_min > 0 and all(survivor_conds.values()):
        verdict = "SURVIVOR"
    return {
        "strategy": strategy, "time_floor_min": time_floor_min,
        "n": n, "wins": wins, "rate_pct": rate,
        "ev": ev, "pf": pf, "wilson_lo_pct": wlo,
        "p_welch": p_welch, "wf_signs": wf_signs, "wf_agree": wf_agree,
        "mae_breaker_n": breaker_n, "mae_breaker_pct": breaker_pct,
        "floor_infeasible": floor_infeasible,
        "survivor_conds": survivor_conds,
        "verdict": verdict, "pnls": pnls,
    }

# ---------------------------------------------------------------------------
# Synthetic null trades — mark by entry_type
# ---------------------------------------------------------------------------

def synth_null_trades_per_strategy(n_per_strategy: int = 60, seed: int = 42) -> Dict[str, List[Dict[str, Any]]]:
    rng = random.Random(seed)
    # Reuse generator from bb_squeeze harness, then label
    from bb_squeeze_rescue_bt import synth_null_trades  # type: ignore
    out: Dict[str, List[Dict[str, Any]]] = {}
    for i, strategy in enumerate(TARGET_STRATEGIES):
        ts = synth_null_trades(n_per_strategy, seed=seed + i)
        for t in ts: t["entry_type"] = strategy
        out[strategy] = ts
    return out

# ---------------------------------------------------------------------------
# Real extraction (parallel to bb_squeeze, but yields all 7 strategies)
# ---------------------------------------------------------------------------

def extract_real_trades_multi(from_iso: str, to_iso: str) -> Dict[str, List[Dict[str, Any]]]:
    """365日 BT用: 全 PAIRS で 7 戦略を並行抽出. compute_scalp_signal は1呼出毎に
    1 entry_type しか返さないため、戦略ごとに extract を回す (mafe pattern)."""
    from bb_squeeze_rescue_bt import _fetch_range_5m, _extract_strategy_entries
    from modules.indicators import add_indicators
    out: Dict[str, List[Dict[str, Any]]] = {s: [] for s in TARGET_STRATEGIES}
    for symbol in PAIRS:
        try:
            df = _fetch_range_5m(symbol, from_iso, to_iso)
            df = add_indicators(df).dropna()
        except Exception as e:
            print(f"[err] {symbol}: {e}", flush=True); continue
        for strat in TARGET_STRATEGIES:
            try:
                ents = _extract_strategy_entries(symbol, df, strat)
                out[strat].extend(ents)
            except Exception as e:
                print(f"[err] {symbol}/{strat}: {e}", flush=True)
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
    ap.add_argument("--n-synth", type=int, default=60, help="per-strategy synthetic trades")
    args = ap.parse_args()
    if args.output_dir is None:
        args.output_dir = ("/tmp/time-floor-meta-dryrun"
                           if args.dry_run
                           else "raw/bt-results/time-floor-meta-2026-04-25")
    _proj_root = str(Path(__file__).resolve().parents[1])
    if _proj_root not in sys.path:
        sys.path.insert(0, _proj_root)

    print("=" * 90)
    print("Time-Floor Meta Rescue BT — pre-reg LOCKED 2026-04-25")
    print(f"  alpha_cell = {ALPHA_CELL:.5f} (Bonferroni 0.05/{N_CELLS_TOTAL})")
    print(f"  hold floors = {HOLD_FLOORS} min")
    print(f"  {len(TARGET_STRATEGIES)} strategies × {len(HOLD_FLOORS)} floors = {N_CELLS_TOTAL} cells")
    print(f"  meta-accept: ≥{META_MIN_SURVIVORS} SURVIVOR strategies at B (floor={META_PRIMARY_FLOOR}m)")
    print(f"  MAE_CATASTROPHIC_PIPS = {MAE_CATASTROPHIC_PIPS} (survivor-bias defence)")
    print(f"  FLOOR_INFEASIBLE if breaker_pct > {FLOOR_INFEASIBLE_BREAKER_PCT}%")
    print("=" * 90)

    if args.dry_run:
        print(f"[DRY-RUN] {args.n_synth} synthetic null trades per strategy")
        per_strat = synth_null_trades_per_strategy(args.n_synth)
    else:
        print(f"[LIVE] extracting all 7 strategies {args.from_iso} → {args.to_iso}")
        per_strat = extract_real_trades_multi(args.from_iso, args.to_iso)

    # Observed WR per strategy (from full sim at floor=0) — used as Wilson gate baseline
    obs_wr: Dict[str, float] = {}
    base_pnls: Dict[str, List[float]] = {}
    for strat, trades in per_strat.items():
        if not trades: obs_wr[strat] = 0.0; base_pnls[strat] = []; continue
        sims = [simulate_pnl(t, 0) for t in trades]
        ws = sum(1 for s in sims if s["pnl_pips"] > 0)
        obs_wr[strat] = (ws / len(sims) * 100) if sims else 0.0
        base_pnls[strat] = [s["pnl_pips"] for s in sims]

    # Evaluate full grid
    print(f"\n--- Per-(strategy × floor) results ---")
    print(f"{'strategy':<24}{'flr':>4}{'N':>5}{'WR%':>6}{'EV':>7}{'PF':>6}"
          f"{'Wlo%':>6}{'p_welch':>9}{'WF':>5}{'MAE!%':>7}{'verdict':>10}")
    grid: List[Dict[str, Any]] = []
    for strat in TARGET_STRATEGIES:
        trades = per_strat.get(strat, [])
        for floor in HOLD_FLOORS:
            r = evaluate_strategy_floor(trades, strat, floor,
                                        baseline_pnls=base_pnls.get(strat) if floor > 0 else None,
                                        obs_wr_pct=obs_wr.get(strat, 0.0))
            grid.append(r)
            pf_s = f"{r['pf']:.2f}" if r['pf'] != float("inf") else " inf"
            print(f"{strat[:23]:<24}{floor:>4}{r['n']:>5}{r['rate_pct']:>6.1f}"
                  f"{r['ev']:>+7.2f}{pf_s:>6}{r['wilson_lo_pct']:>6.1f}{r['p_welch']:>9.4f}"
                  f"{r['wf_agree']:>3}/{len(r['wf_signs'])}{r['mae_breaker_pct']:>6.1f}%"
                  f"{r['verdict']:>10}")

    # Meta verdict at primary floor (B=20)
    primary = [r for r in grid if r["time_floor_min"] == META_PRIMARY_FLOOR]
    survivors_at_primary = [r for r in primary if r["verdict"] == "SURVIVOR"]
    meta_accept = len(survivors_at_primary) >= META_MIN_SURVIVORS

    # Floor-infeasible flags (any cell)
    infeasible = [r for r in grid if r["floor_infeasible"]]
    print(f"\nMeta-primary (floor={META_PRIMARY_FLOOR}m) survivors: "
          f"{[r['strategy'] for r in survivors_at_primary]} ({len(survivors_at_primary)}/{META_MIN_SURVIVORS} required)")
    print(f"Meta verdict: {'H1_ACCEPTED' if meta_accept else 'H1_REJECTED'}")
    if infeasible:
        print(f"\n[WARN] FLOOR_INFEASIBLE ({len(infeasible)} cells with breaker > {FLOOR_INFEASIBLE_BREAKER_PCT}%):")
        for r in infeasible:
            print(f"  {r['strategy']} floor={r['time_floor_min']}: breaker={r['mae_breaker_pct']:.1f}%")

    # Outputs
    out_dir = Path(args.output_dir); out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "pre_reg": "knowledge-base/wiki/analyses/time-floor-meta-rescue-2026-04-25.md",
        "alpha_cell": ALPHA_CELL,
        "mae_catastrophic_pips": MAE_CATASTROPHIC_PIPS,
        "from": args.from_iso, "to": args.to_iso,
        "dry_run": args.dry_run,
        "n_strategies_with_data": sum(1 for v in per_strat.values() if v),
        "meta_primary_floor": META_PRIMARY_FLOOR,
        "meta_min_survivors_required": META_MIN_SURVIVORS,
        "meta_survivors_count": len(survivors_at_primary),
        "meta_verdict": "H1_ACCEPTED" if meta_accept else "H1_REJECTED",
        "infeasible_cells": [{"strategy": r["strategy"], "floor": r["time_floor_min"],
                              "breaker_pct": r["mae_breaker_pct"]} for r in infeasible],
        "grid": [{k: v for k, v in r.items() if k != "pnls"} for r in grid],
    }
    with (out_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n[written] {out_dir / 'summary.json'}")

    if args.dry_run:
        if not meta_accept and not survivors_at_primary:
            print("[DRY-RUN OK] null hypothesis correctly rejected (no false SURVIVOR)")
            return 0
        else:
            print("[DRY-RUN FAIL] null data produced SURVIVOR — investigate harness")
            return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
