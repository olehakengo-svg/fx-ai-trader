#!/usr/bin/env python3
"""
Regime 2D v2 Rescan — post-backfill analysis (pre-registered).

Companion to:
    knowledge-base/wiki/analyses/regime-2d-v2-preregister-2026-04-20.md

**Implementation policy**: This script only performs analysis and emits candidate
tables. **It does NOT propose implementation changes**. Human judgement is required
to act on the gate_candidates.csv output, per lesson-reactive-changes.

Inputs:
    --trades-json   Path to a JSON payload matching /api/demo/trades response
                    (list of closed trades with fields: entry_type, instrument,
                    direction, pnl_pips, entry_time, mtf_regime (optional)).
    --output-dir    Directory for CSV / JSON outputs (created if missing).

Gate (pre-committed, see preregister §3):
    N >= 50 per (strategy, regime, direction) cell
    |DeltaWR| >= 10pp between two regimes (same direction)
    Fisher's exact p < alpha_strict = 0.05 / K_effective (two-sided)
    IS-only mode: sign check on IS (2026-04-16 .. 2026-04-18)

Outputs:
    matrix_all.csv          (strategy, regime, direction, N, wins, WR, mean_pnl)
    asymmetry_strict.csv    per-strategy regime asymmetry (N>=50 gate)
    hypothesis_check.csv    predicted sign vs observed sign
    gate_candidates.csv     strategies passing all preregister gates
    summary.json            aggregate counts + config snapshot
    sanity_check.json       Phase E mapping (bb_rsi / fib) sign verification

Usage:
    python3 scripts/regime_2d_v2_rescan.py \\
        --trades-json /tmp/trades_post_backfill.json \\
        --output-dir /tmp/fx-regime-2d-v2

Dry-run (syntax + logic without data):
    python3 scripts/regime_2d_v2_rescan.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Pull the source-of-truth family map
try:
    from research.edge_discovery.strategy_family_map import (
        STRATEGY_FAMILY,
        REGIME_ADAPTIVE_FAMILY,
    )
except Exception:  # pragma: no cover - script can run without import in dry-run
    STRATEGY_FAMILY = {}
    REGIME_ADAPTIVE_FAMILY = {}

# ── Pre-registered constants (DO NOT MODIFY post-hoc) ────────────────────────
FIDELITY_CUTOFF = "2026-04-16"
IS_END = "2026-04-18T23:59:59"        # §3.5 pre-register
MIN_CELL_N = 50                        # §3.1
MIN_DELTA_WR_PP = 10.0                 # §3.2
ALPHA_RAW = 0.05                       # §3.3 family-wise α (before Bonferroni)

REGIMES = (
    "trend_up_strong", "trend_up_weak",
    "trend_down_weak", "trend_down_strong",
    "range_tight", "range_wide", "uncertain",
)
DIRECTIONS = ("BUY", "SELL")

# Pre-registered sign predictions (preregister §2.2).
# +1 = BUY WR > SELL WR, -1 = SELL WR > BUY WR, 0 = no asymmetry expected.
# Only used for hypothesis-check reporting; not for gate judgement.
# (We include the headline TF/MR/BO/SE buckets; RA overrides for 2 strategies.)
def _predicted_sign(strategy: str, regime: str, family: str) -> int:
    """Return +1 / -1 / 0 per preregister §2.2 rules."""
    # RA special cases
    if strategy == "bb_rsi_reversion":
        if regime in ("trend_up_weak", "trend_up_strong",
                      "trend_down_weak", "trend_down_strong"):
            return +1  # BUY > SELL in all trend regimes
        return 0
    if strategy == "fib_reversal":
        if regime in ("trend_up_weak", "trend_up_strong",
                      "trend_down_weak", "trend_down_strong"):
            return -1  # SELL > BUY in all trend regimes
        return 0

    # Family defaults
    if family == "SE":
        return 0
    if family == "TF":
        if regime in ("trend_up_weak", "trend_up_strong"):
            return +1
        if regime in ("trend_down_weak", "trend_down_strong"):
            return -1
        return 0
    if family == "MR":
        # fade trend; note JPY exception in strategy_aware_alignment
        if regime in ("trend_up_weak", "trend_up_strong"):
            return -1
        if regime in ("trend_down_weak", "trend_down_strong"):
            return +1
        return 0
    if family == "BO":
        if regime in ("trend_up_weak", "trend_up_strong"):
            return +1
        if regime in ("trend_down_weak", "trend_down_strong"):
            return -1
        return 0
    return 0


# ── Fisher's exact (two-sided) without SciPy dependency ──────────────────────
def _log_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value for 2x2 contingency table.

        |  win   | loss
     A  |   a    |  b
     B  |   c    |  d

    Sums of tail probabilities <= observed probability.
    """
    n = a + b + c + d
    if n == 0:
        return 1.0
    row1 = a + b
    col1 = a + c
    # observed log-prob
    try:
        logp_obs = (
            _log_comb(row1, a) + _log_comb(n - row1, col1 - a) - _log_comb(n, col1)
        )
    except ValueError:
        return 1.0
    total = 0.0
    k_min = max(0, col1 - (n - row1))
    k_max = min(row1, col1)
    for k in range(k_min, k_max + 1):
        logp = (
            _log_comb(row1, k) + _log_comb(n - row1, col1 - k) - _log_comb(n, col1)
        )
        if logp <= logp_obs + 1e-12:
            total += math.exp(logp)
    return min(1.0, total)


# ── Trade loading ────────────────────────────────────────────────────────────
def load_trades(path: str) -> List[dict]:
    with open(path) as f:
        payload = json.load(f)
    if isinstance(payload, dict):
        trades = payload.get("trades", [])
    else:
        trades = payload
    return list(trades)


def filter_trades(trades: Iterable[dict]) -> List[dict]:
    """Apply post-cutoff / XAU-exclude / closed filter."""
    out = []
    for t in trades:
        inst = (t.get("instrument") or "")
        if "XAU" in inst:
            continue  # user memory: exclude XAU
        if t.get("status") and t["status"].upper() != "CLOSED":
            continue
        if t.get("pnl_pips") is None:
            continue
        et = t.get("entry_time", "") or ""
        if et < FIDELITY_CUTOFF:
            continue
        if not t.get("mtf_regime"):
            continue  # require regime label (backfill prerequisite)
        out.append(t)
    return out


# ── 2D matrix ────────────────────────────────────────────────────────────────
def build_matrix(trades: List[dict]) -> Dict[Tuple[str, str, str], dict]:
    """(strategy, regime, direction) -> {n, wins, pnl}."""
    cells: Dict[Tuple[str, str, str], dict] = defaultdict(
        lambda: {"n": 0, "wins": 0, "pnl": 0.0}
    )
    for t in trades:
        strat = t.get("entry_type") or "unknown"
        regime = t.get("mtf_regime") or "uncertain"
        direction = (t.get("direction") or "").upper()
        if direction not in DIRECTIONS:
            continue
        pnl = float(t.get("pnl_pips", 0.0) or 0.0)
        key = (strat, regime, direction)
        cells[key]["n"] += 1
        cells[key]["wins"] += 1 if pnl > 0 else 0
        cells[key]["pnl"] += pnl
    return cells


def cell_wr(cell: dict) -> float:
    return cell["wins"] / cell["n"] if cell["n"] > 0 else 0.0


def cell_mean_pnl(cell: dict) -> float:
    return cell["pnl"] / cell["n"] if cell["n"] > 0 else 0.0


# ── Asymmetry / gate ─────────────────────────────────────────────────────────
def _effective_family(strategy: str, regime: str) -> str:
    """Mirror strategy_family_map.effective_family without circular import issues."""
    if strategy in REGIME_ADAPTIVE_FAMILY:
        adaptive = REGIME_ADAPTIVE_FAMILY[strategy]
        if regime in adaptive:
            return adaptive[regime]
    return STRATEGY_FAMILY.get(strategy, "UNKNOWN")


def gate_scan(cells: Dict[Tuple[str, str, str], dict]) -> Tuple[List[dict], List[dict], int]:
    """Enumerate all (strategy, regime_A, regime_B, direction) pair tests that
    have N>=MIN_CELL_N in both cells. Returns (all_tests, candidates, k_effective).
    """
    strategies = sorted({k[0] for k in cells})
    all_tests: List[dict] = []
    for strat in strategies:
        for direction in DIRECTIONS:
            qual_regimes = [
                r for r in REGIMES
                if cells.get((strat, r, direction), {}).get("n", 0) >= MIN_CELL_N
            ]
            # Pairwise regime comparisons (unordered)
            for i in range(len(qual_regimes)):
                for j in range(i + 1, len(qual_regimes)):
                    r_a, r_b = qual_regimes[i], qual_regimes[j]
                    c_a = cells[(strat, r_a, direction)]
                    c_b = cells[(strat, r_b, direction)]
                    wr_a = cell_wr(c_a)
                    wr_b = cell_wr(c_b)
                    delta_wr_pp = (wr_a - wr_b) * 100.0
                    p = fisher_exact_two_sided(
                        c_a["wins"], c_a["n"] - c_a["wins"],
                        c_b["wins"], c_b["n"] - c_b["wins"],
                    )
                    all_tests.append({
                        "strategy": strat,
                        "direction": direction,
                        "regime_a": r_a,
                        "regime_b": r_b,
                        "n_a": c_a["n"], "n_b": c_b["n"],
                        "wr_a": wr_a, "wr_b": wr_b,
                        "delta_wr_pp": delta_wr_pp,
                        "p_fisher_two_sided": p,
                        "family_a": _effective_family(strat, r_a),
                        "family_b": _effective_family(strat, r_b),
                    })
    k_effective = max(1, len(all_tests))
    alpha_strict = ALPHA_RAW / k_effective
    candidates: List[dict] = []
    for t in all_tests:
        if abs(t["delta_wr_pp"]) < MIN_DELTA_WR_PP:
            continue
        if t["p_fisher_two_sided"] >= alpha_strict:
            continue
        # Exclude existing RA strategies per preregister §3.6
        if t["strategy"] in REGIME_ADAPTIVE_FAMILY:
            t["exclusion"] = "existing_RA"
            continue
        candidates.append({**t, "alpha_strict": alpha_strict})
    return all_tests, candidates, k_effective


def hypothesis_check(cells: Dict[Tuple[str, str, str], dict]) -> List[dict]:
    """For each (strategy, regime) with both BUY & SELL cells, record predicted
    sign vs observed sign. Used for directional asymmetry sanity, not gate."""
    rows = []
    strategies = sorted({k[0] for k in cells})
    for strat in strategies:
        family_default = STRATEGY_FAMILY.get(strat, "UNKNOWN")
        for regime in REGIMES:
            c_buy = cells.get((strat, regime, "BUY"))
            c_sell = cells.get((strat, regime, "SELL"))
            if not c_buy or not c_sell:
                continue
            if c_buy["n"] < 20 or c_sell["n"] < 20:
                continue
            wr_buy = cell_wr(c_buy)
            wr_sell = cell_wr(c_sell)
            observed_sign = (
                +1 if wr_buy > wr_sell
                else -1 if wr_sell > wr_buy
                else 0
            )
            fam = _effective_family(strat, regime)
            predicted = _predicted_sign(strat, regime, fam)
            rows.append({
                "strategy": strat,
                "regime": regime,
                "family_default": family_default,
                "family_effective": fam,
                "n_buy": c_buy["n"], "n_sell": c_sell["n"],
                "wr_buy": wr_buy, "wr_sell": wr_sell,
                "delta_wr_pp": (wr_buy - wr_sell) * 100.0,
                "predicted_sign": predicted,
                "observed_sign": observed_sign,
                "sign_match": int(predicted == observed_sign) if predicted != 0 else None,
            })
    return rows


def sanity_check_ra(cells: Dict[Tuple[str, str, str], dict]) -> dict:
    """Preregister §4.4 — existing RA mappings must hold after backfill.

    bb_rsi_reversion: BUY > SELL in all trend regimes (predicted +1).
    fib_reversal:     SELL > BUY in all trend regimes (predicted -1).
    """
    trend_regimes = ("trend_up_weak", "trend_up_strong",
                     "trend_down_weak", "trend_down_strong")
    report = {"bb_rsi_reversion": {}, "fib_reversal": {}}
    for strat, expected in (("bb_rsi_reversion", +1), ("fib_reversal", -1)):
        fail = 0
        total = 0
        details = {}
        for r in trend_regimes:
            c_buy = cells.get((strat, r, "BUY"))
            c_sell = cells.get((strat, r, "SELL"))
            if not c_buy or not c_sell:
                details[r] = "insufficient"
                continue
            if c_buy["n"] < 5 or c_sell["n"] < 5:
                details[r] = f"n_too_small(buy={c_buy['n']},sell={c_sell['n']})"
                continue
            total += 1
            d = cell_wr(c_buy) - cell_wr(c_sell)
            observed = +1 if d > 0 else (-1 if d < 0 else 0)
            ok = observed == expected
            fail += 0 if ok else 1
            details[r] = {
                "n_buy": c_buy["n"], "n_sell": c_sell["n"],
                "wr_buy": cell_wr(c_buy), "wr_sell": cell_wr(c_sell),
                "observed_sign": observed,
                "expected_sign": expected,
                "pass": ok,
            }
        report[strat] = {
            "total_regimes_evaluated": total,
            "failures": fail,
            "verdict": "PASS" if fail == 0 and total > 0
                       else ("FAIL" if fail > 0 else "INSUFFICIENT_DATA"),
            "details": details,
        }
    return report


# ── IO helpers ───────────────────────────────────────────────────────────────
def write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def emit_matrix_csv(cells: Dict[Tuple[str, str, str], dict], out: Path) -> None:
    rows = []
    for (s, r, d), c in sorted(cells.items()):
        rows.append({
            "strategy": s, "regime": r, "direction": d,
            "n": c["n"], "wins": c["wins"],
            "wr": cell_wr(c),
            "mean_pnl": cell_mean_pnl(c),
        })
    write_csv(out / "matrix_all.csv", rows,
              ["strategy", "regime", "direction", "n", "wins", "wr", "mean_pnl"])


# ── Dry-run ──────────────────────────────────────────────────────────────────
def _synthesize_dry_run_trades() -> List[dict]:
    """Generate a small deterministic synthetic set for syntax / logic verification."""
    import random
    rng = random.Random(0)
    strats = ["ema_trend_scalp", "bb_rsi_reversion", "fib_reversal",
              "sr_channel_reversal", "session_time_bias"]
    regimes = ["trend_up_weak", "trend_up_strong", "range_tight", "range_wide",
               "trend_down_weak"]
    trades = []
    for i in range(600):
        s = rng.choice(strats)
        r = rng.choice(regimes)
        d = rng.choice(["BUY", "SELL"])
        base_wr = 0.5
        # Encode preregister hypothesis signals to verify sign_match column
        if s == "bb_rsi_reversion" and r.startswith("trend_"):
            base_wr = 0.55 if d == "BUY" else 0.40
        if s == "fib_reversal" and r.startswith("trend_"):
            base_wr = 0.60 if d == "SELL" else 0.35
        pnl = 1.0 if rng.random() < base_wr else -1.0
        trades.append({
            "entry_type": s,
            "instrument": "EUR_USD",
            "direction": d,
            "mtf_regime": r,
            "pnl_pips": pnl,
            "status": "CLOSED",
            "entry_time": f"2026-04-1{6 + (i % 4)}T12:00:00",
        })
    return trades


# ── Main ─────────────────────────────────────────────────────────────────────
def main(argv: List[str] | None = None) -> int:
    global MIN_CELL_N, ALPHA_RAW  # noqa: PLW0603
    parser = argparse.ArgumentParser(
        description="Regime 2D v2 post-backfill rescan (pre-registered)."
    )
    parser.add_argument("--trades-json", help="Path to production /api/demo/trades snapshot")
    parser.add_argument("--output-dir", default="/tmp/fx-regime-2d-v2")
    parser.add_argument("--min-cell-n", type=int, default=MIN_CELL_N,
                        help=f"Pre-registered default: {MIN_CELL_N} (DO NOT override post-hoc)")
    parser.add_argument("--alpha", type=float, default=ALPHA_RAW,
                        help="Pre-registered family-wise alpha (Bonferroni corrected in-script)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run on synthetic deterministic sample (CI / smoke test)")
    args = parser.parse_args(argv)

    if args.min_cell_n != MIN_CELL_N:
        print(f"[warn] min_cell_n overridden to {args.min_cell_n} (pre-registered={MIN_CELL_N})",
              file=sys.stderr)
        MIN_CELL_N = args.min_cell_n
    if args.alpha != ALPHA_RAW:
        print(f"[warn] alpha overridden to {args.alpha} (pre-registered={ALPHA_RAW})",
              file=sys.stderr)
        ALPHA_RAW = args.alpha

    if args.dry_run:
        trades = _synthesize_dry_run_trades()
        print(f"[dry-run] Using {len(trades)} synthetic trades")
    elif args.trades_json:
        raw = load_trades(args.trades_json)
        trades = filter_trades(raw)
        print(f"Loaded {len(raw)} raw trades -> {len(trades)} after filter "
              f"(post-cutoff, closed, mtf_regime populated, FX-only)")
    else:
        print("ERROR: --trades-json or --dry-run required", file=sys.stderr)
        return 2

    if not trades:
        print("ERROR: no trades after filter. Aborting.", file=sys.stderr)
        return 3

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cells = build_matrix(trades)
    emit_matrix_csv(cells, out_dir)

    all_tests, candidates, k_eff = gate_scan(cells)
    # asymmetry_strict.csv = all pairwise tests with both cells >= MIN_CELL_N
    write_csv(out_dir / "asymmetry_strict.csv", all_tests,
              ["strategy", "direction", "regime_a", "regime_b",
               "n_a", "n_b", "wr_a", "wr_b", "delta_wr_pp",
               "p_fisher_two_sided", "family_a", "family_b"])

    write_csv(out_dir / "gate_candidates.csv", candidates,
              ["strategy", "direction", "regime_a", "regime_b",
               "n_a", "n_b", "wr_a", "wr_b", "delta_wr_pp",
               "p_fisher_two_sided", "alpha_strict",
               "family_a", "family_b"])

    hypo = hypothesis_check(cells)
    write_csv(out_dir / "hypothesis_check.csv", hypo,
              ["strategy", "regime", "family_default", "family_effective",
               "n_buy", "n_sell", "wr_buy", "wr_sell", "delta_wr_pp",
               "predicted_sign", "observed_sign", "sign_match"])

    sanity = sanity_check_ra(cells)
    with open(out_dir / "sanity_check.json", "w") as f:
        json.dump(sanity, f, indent=2, default=str)

    summary = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "n_trades_in": len(trades),
        "n_cells": len(cells),
        "n_strategies": len({k[0] for k in cells}),
        "n_regimes_observed": len({k[1] for k in cells}),
        "k_effective_tests": k_eff,
        "alpha_raw": ALPHA_RAW,
        "alpha_strict_bonferroni": ALPHA_RAW / max(1, k_eff),
        "min_cell_n": MIN_CELL_N,
        "min_delta_wr_pp": MIN_DELTA_WR_PP,
        "n_gate_candidates": len(candidates),
        "sanity_check": {
            "bb_rsi_reversion": sanity["bb_rsi_reversion"].get("verdict"),
            "fib_reversal": sanity["fib_reversal"].get("verdict"),
        },
        "preregister_ref": ("knowledge-base/wiki/analyses/"
                            "regime-2d-v2-preregister-2026-04-20.md"),
    }
    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Console summary
    print("=" * 72)
    print("REGIME 2D V2 RESCAN — summary")
    print("=" * 72)
    print(f"trades           : {summary['n_trades_in']}")
    print(f"cells            : {summary['n_cells']}")
    print(f"strategies       : {summary['n_strategies']}")
    print(f"regimes observed : {summary['n_regimes_observed']}")
    print(f"K_effective      : {k_eff}")
    print(f"alpha_strict     : {summary['alpha_strict_bonferroni']:.2e}")
    print(f"gate candidates  : {len(candidates)}")
    for c in candidates:
        print(f"  - {c['strategy']:28s} {c['direction']} "
              f"{c['regime_a']} vs {c['regime_b']} "
              f"ΔWR={c['delta_wr_pp']:+.1f}pp p={c['p_fisher_two_sided']:.2e}")
    print(f"sanity (bb_rsi)  : {summary['sanity_check']['bb_rsi_reversion']}")
    print(f"sanity (fib)     : {summary['sanity_check']['fib_reversal']}")
    print(f"outputs in       : {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
