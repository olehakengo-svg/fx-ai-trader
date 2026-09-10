#!/usr/bin/env python3
"""equity_curve_shadow_gating FORWARD measurement (ledger #22) — rule:R3.

Frozen pre-reg (v2 forward, LOCKED 2026-08-03):
    knowledge-base/wiki/decisions/
    equity-curve-shadow-gating-explore-prereg-2026-08-03.md

P-10 type freeze: gate x outcome joint computation is PROHIBITED before
first look 2026-11-06. This harness refuses to run before that date.

Design (frozen):
  - primary family: 4 active cells x K{5,10,20}, Bonferroni m=12
  - outcomes: forward shadow closed trades entry_time >= 2026-08-04
    (state warm-up may use earlier history; outcomes forward-only)
  - primary p: one-sided, computed on the UNIQUE-SPACED series
  - null: within-cell EPOCH-stratified permutation (epoch boundaries =
    first-parent merge-commit dates on main touching frozen path list;
    strata with <10 eligible outcomes merge into the FOLLOWING stratum)
  - robustness: (i) full-series contrast>0 (ii) LOYO-week informative
    folds (iii) coverage in [0.25,0.75] (iv) split-half (v) top-2 |pnl|
    excluded — all sign-preserving, required for PASS
  - degenerate permutations counted conservatively; knife-edge p<5*alpha
    -> deterministic 100k rerun

Usage (first look, on/after 2026-11-06):
    python3 tools/render_trades_snapshot.py --output <new_snapshot> --limit 100000
    python3 tools/equity_curve_gating_explore.py --snapshot <new_snapshot>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

FIRST_LOOK = "2026-11-06"
FORWARD_FROM = "2026-08-04"          # outcomes: entry_time >= this
FORWARD_CUTOFF = "2026-11-01"        # outcomes: entry_time < this
WARMUP_FROM = "2026-04-08"           # state warm-up history (Fidelity Cutoff)

PRIMARY_CELLS: Tuple[Tuple[str, str, str], ...] = (
    ("daytrade_gbpusd", "session_time_bias", "GBP_USD"),
    ("daytrade_eur", "session_time_bias", "EUR_USD"),
    ("scalp_5m_gbp", "vol_momentum_scalp", "GBP_USD"),
    ("daytrade_gbpusd", "xs_momentum", "GBP_USD"),
)
KS = (5, 10, 20)
SEED = 20260803
ALPHA = 0.05 / (len(PRIMARY_CELLS) * len(KS))  # m=12
COVERAGE_RANGE = (0.25, 0.75)
LOYO_MAX_FLIPS = 3
DEDUP_WINDOW_S = 60.0
MIN_HOLD_S = 5.0
MIN_CELL_N = 150                     # forward N floor for verdict participation
LIVE_HOLE_MAX = 0.20                 # composition-confounded threshold
RT_PIPS = {"USD_JPY": 2.14, "EUR_USD": 2.00, "GBP_USD": 4.53, "EUR_JPY": 2.50}
N_PERM = 10000                       # frozen; CLI below this is rejected
EPOCH_PATHS = ("modules/demo_trader.py", "modules/demo_db.py",
               "modules/shadow_demote_registry.py", "strategies/")
EPOCH_MIN_ELIG = 10


def parse_ts(s: str) -> datetime:
    if not s.endswith("+00:00"):
        raise ValueError("non-UTC timestamp format: %r" % s)
    return datetime.fromisoformat(s)


def derive_epochs() -> List[str]:
    """Frozen rule (pre-reg §4): first-parent merge-commit dates on main
    touching EPOCH_PATHS within the forward window."""
    out = subprocess.run(
        ["git", "log", "--first-parent", "--merges", "--format=%cs",
         "--since", FORWARD_FROM, "--until", FORWARD_CUTOFF,
         "origin/main", "--"] + list(EPOCH_PATHS),
        capture_output=True, text=True, cwd=str(REPO_ROOT), check=True)
    return sorted(set(out.stdout.split()))


def epoch_of(entry_iso: str, boundaries: List[str]) -> int:
    d = entry_iso[:10]
    e = 0
    for i, b in enumerate(boundaries):
        if d >= b:
            e = i + 1
    return e


def load_cell_trades(cur, cell, boundaries) -> List[dict]:
    mode, etype, inst = cell
    rows = cur.execute(
        """SELECT entry_time, exit_time, pnl_pips, direction
           FROM demo_trades
           WHERE status='CLOSED'
             AND (oanda_trade_id IS NULL OR oanda_trade_id='')
             AND COALESCE(is_shadow,1)=1
             AND COALESCE(dedup_violation,0)=0
             AND COALESCE(mode,'')=? AND entry_type=?
             AND COALESCE(instrument,'')=?
             AND entry_time >= ? AND entry_time < ?
           ORDER BY entry_time ASC, trade_id ASC""",
        (mode, etype, inst, WARMUP_FROM, FORWARD_CUTOFF)).fetchall()
    out = []
    last_kept: Dict[str, datetime] = {}
    for et, xt, pnl, direction in rows:
        if pnl is None or xt is None:
            continue
        t_in, t_out = parse_ts(et), parse_ts(xt)
        if t_out < t_in:
            raise RuntimeError("exit<entry row in %s at %s" % (
                "/".join(cell), et))
        if (t_out - t_in).total_seconds() < MIN_HOLD_S:
            continue
        lk = last_kept.get(direction)
        if lk is not None and (t_in - lk).total_seconds() < DEDUP_WINDOW_S:
            continue
        last_kept[direction] = t_in
        out.append({"entry": t_in, "exit": t_out, "pnl": float(pnl),
                    "forward": et >= FORWARD_FROM,
                    "epoch": epoch_of(et, boundaries)})
    return out


def live_hole_fraction(cur, cell) -> float:
    mode, etype, inst = cell
    live, = cur.execute(
        """SELECT COUNT(*) FROM demo_trades
           WHERE status='CLOSED' AND oanda_trade_id IS NOT NULL
             AND oanda_trade_id != ''
             AND COALESCE(mode,'')=? AND entry_type=?
             AND COALESCE(instrument,'')=?
             AND entry_time >= ? AND entry_time < ?""",
        (mode, etype, inst, FORWARD_FROM, FORWARD_CUTOFF)).fetchone()
    shadow, = cur.execute(
        """SELECT COUNT(*) FROM demo_trades
           WHERE status='CLOSED'
             AND (oanda_trade_id IS NULL OR oanda_trade_id='')
             AND COALESCE(is_shadow,1)=1
             AND COALESCE(mode,'')=? AND entry_type=?
             AND COALESCE(instrument,'')=?
             AND entry_time >= ? AND entry_time < ?""",
        (mode, etype, inst, FORWARD_FROM, FORWARD_CUTOFF)).fetchone()
    total = live + shadow
    return (live / total) if total else 0.0


def prior_indices(trades, k) -> List[Optional[List[int]]]:
    exits = sorted(range(len(trades)), key=lambda i: trades[i]["exit"])
    exit_times = [trades[i]["exit"] for i in exits]
    import bisect
    res: List[Optional[List[int]]] = []
    for t in trades:
        pos = bisect.bisect_left(exit_times, t["entry"])
        res.append(None if pos < k else
                   [exits[j] for j in range(pos - k, pos)])
    return res


def eligible_mask(trades, prior_idx) -> List[bool]:
    """Outcome-eligible: has K priors AND is a forward-window trade."""
    return [pri is not None and trades[i]["forward"]
            for i, pri in enumerate(prior_idx)]


def contrast_stat(pnl, prior_idx, elig, extra_mask=None):
    on, off = [], []
    for i, pri in enumerate(prior_idx):
        if not elig[i] or (extra_mask is not None and not extra_mask[i]):
            continue
        state = sum(pnl[j] for j in pri)
        (on if state > 0 else off).append(pnl[i])
    if not on or not off:
        return None, len(on), len(off)
    return (sum(on) / len(on) - sum(off) / len(off)), len(on), len(off)


def merged_strata(trades, elig) -> List[List[int]]:
    """Epoch strata over ALL trades (values shuffle within stratum);
    strata with <EPOCH_MIN_ELIG eligible outcomes merge into the
    FOLLOWING stratum (deterministic)."""
    by_epoch: Dict[int, List[int]] = {}
    for i, t in enumerate(trades):
        by_epoch.setdefault(t["epoch"], []).append(i)
    keys = sorted(by_epoch)
    groups, cur_grp = [], []
    for kk in keys:
        cur_grp.extend(by_epoch[kk])
        n_elig = sum(1 for i in cur_grp if elig[i])
        if n_elig >= EPOCH_MIN_ELIG:
            groups.append(cur_grp)
            cur_grp = []
    if cur_grp:
        if groups:
            groups[-1].extend(cur_grp)
        else:
            groups.append(cur_grp)
    return groups


def perm_pvalue(trades, prior_idx, elig, obs, n_perm, seed) -> float:
    import numpy as np
    rng = np.random.RandomState(seed)
    pnl0 = np.array([t["pnl"] for t in trades])
    strata = [np.array(g) for g in merged_strata(trades, elig)]
    elig_idx = [i for i, e in enumerate(elig) if e]
    pri = np.array([prior_idx[i] for i in elig_idx])
    elig_arr = np.array(elig_idx)
    ge = 0
    for _ in range(n_perm):
        perm = pnl0.copy()
        for idx in strata:
            perm[idx] = perm[idx[rng.permutation(len(idx))]]
        states = perm[pri].sum(axis=1)
        outc = perm[elig_arr]
        on_mask = states > 0
        if not on_mask.any() or on_mask.all():
            ge += 1  # degenerate: conservative
            continue
        if (outc[on_mask].mean() - outc[~on_mask].mean()) >= obs:
            ge += 1
    return (1 + ge) / (n_perm + 1)


def unique_spaced_indices(trades) -> List[bool]:
    keep, last_exit = [], None
    for t in trades:
        ok = last_exit is None or t["entry"] >= last_exit
        keep.append(ok)
        if ok:
            last_exit = t["exit"]
    return keep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True,
                    help="fresh production snapshot (first-look artifact)")
    ap.add_argument("--n-perm", type=int, default=N_PERM)
    args = ap.parse_args()

    today = datetime.now(timezone.utc).date().isoformat()
    if today < FIRST_LOOK:
        print("ERROR: first look is %s — running earlier is peeking "
              "(pre-reg §8, P-10 freeze)" % FIRST_LOOK, file=sys.stderr)
        return 2
    if args.n_perm < N_PERM:
        print("ERROR: n_perm >= %d required" % N_PERM, file=sys.stderr)
        return 2

    snap = Path(args.snapshot)
    digest = hashlib.sha256(snap.read_bytes()).hexdigest()
    boundaries = derive_epochs()
    db = sqlite3.connect("file:%s?mode=ro" % snap, uri=True)
    cur = db.cursor()

    results = []
    for cell in PRIMARY_CELLS:
        trades = load_cell_trades(cur, cell, boundaries)
        pnl = [t["pnl"] for t in trades]
        n_fwd = sum(1 for t in trades if t["forward"])
        hole = live_hole_fraction(cur, cell)
        us_keep = unique_spaced_indices(trades)
        for k in KS:
            pri = prior_indices(trades, k)
            elig = eligible_mask(trades, pri)
            # primary: unique-spaced series
            us_trades = [t for i, t in enumerate(trades) if us_keep[i]]
            us_pri = prior_indices(us_trades, k)
            us_elig = eligible_mask(us_trades, us_pri)
            us_pnl = [t["pnl"] for t in us_trades]
            obs, n_on, n_off = contrast_stat(us_pnl, us_pri, us_elig)
            row = {"cell": "/".join(cell), "K": k,
                   "n_forward": n_fwd, "n_on": n_on, "n_off": n_off,
                   "coverage": (n_on / (n_on + n_off)) if (n_on + n_off) else None,
                   "contrast_primary_us": obs,
                   "live_hole_frac": hole,
                   "underpowered": n_fwd < MIN_CELL_N,
                   "composition_confounded": hole > LIVE_HOLE_MAX}
            if obs is not None and not row["underpowered"]:
                cs = int(hashlib.sha256(("/".join(cell) + str(k)).encode()
                                        ).hexdigest()[:8], 16)
                seed = (SEED + cs) % (2**31 - 1)
                p = perm_pvalue(us_trades, us_pri, us_elig, obs,
                                args.n_perm, seed)
                if p < 5 * ALPHA and args.n_perm < 100000:
                    p = perm_pvalue(us_trades, us_pri, us_elig, obs,
                                    100000, seed)
                    row["knife_edge_rerun"] = True
                row["p_one_sided"] = p
                # robustness (i): full series contrast
                full_c, _, _ = contrast_stat(pnl, pri, elig)
                row["contrast_full"] = full_c
                # (ii) LOYO-week, informative folds only
                weeks = sorted({t["entry"].isocalendar()[:2]
                                for i, t in enumerate(us_trades) if us_elig[i]})
                loyo_pos, loyo_inf = 0, 0
                for w in weeks:
                    mask = [t["entry"].isocalendar()[:2] != w
                            for t in us_trades]
                    c, a, b = contrast_stat(us_pnl, us_pri, us_elig, mask)
                    if c is None:
                        continue
                    loyo_inf += 1
                    if c > 0:
                        loyo_pos += 1
                row["loyo_informative"], row["loyo_positive"] = loyo_inf, loyo_pos
                # (iv) split-half on eligible outcomes
                elig_ids = [i for i, e in enumerate(us_elig) if e]
                c1 = c2 = None
                if len(elig_ids) >= 20:
                    mid = elig_ids[len(elig_ids) // 2]
                    m1 = [i < mid for i in range(len(us_trades))]
                    m2 = [i >= mid for i in range(len(us_trades))]
                    c1, _, _ = contrast_stat(us_pnl, us_pri, us_elig, m1)
                    c2, _, _ = contrast_stat(us_pnl, us_pri, us_elig, m2)
                row["split_half"] = [c1, c2]
                # (v) top-2 |pnl| among eligible outcomes excluded
                by_abs = sorted(elig_ids, key=lambda i: -abs(us_pnl[i]))[:2]
                m5 = [i not in by_abs for i in range(len(us_trades))]
                c5, _, _ = contrast_stat(us_pnl, us_pri, us_elig, m5)
                row["top2_excluded_contrast"] = c5
                on_vals = [us_pnl[i] for i, pri_i in enumerate(us_pri)
                           if us_elig[i] and sum(us_pnl[j] for j in pri_i) > 0]
                on_mean = sum(on_vals) / len(on_vals) if on_vals else None
                row["mean_net_on"] = ((on_mean - RT_PIPS[cell[2]])
                                      if on_mean is not None else None)
                cov_ok = (row["coverage"] is not None and
                          COVERAGE_RANGE[0] <= row["coverage"]
                          <= COVERAGE_RANGE[1])
                robust = bool(
                    (full_c is not None and full_c > 0)
                    and (loyo_pos >= loyo_inf - LOYO_MAX_FLIPS)
                    and cov_ok
                    and (c1 is not None and c1 > 0)
                    and (c2 is not None and c2 > 0)
                    and (c5 is not None and c5 > 0))
                row["stat_pass"] = bool(
                    p < ALPHA and obs > 0 and robust
                    and not row["composition_confounded"])
                row["econ_pass"] = bool(
                    row["stat_pass"] and row["mean_net_on"] is not None
                    and row["mean_net_on"] > 0)
            results.append(row)
            print(" %s K=%-2d n_fwd=%-3d cov=%s c=%s p=%s%s" % (
                row["cell"], k, n_fwd,
                ("%.2f" % row["coverage"]) if row["coverage"] is not None else "—",
                ("%+.3f" % obs) if obs is not None else "—",
                ("%.5f" % row["p_one_sided"])
                if row.get("p_one_sided") is not None else "—",
                "  STAT_PASS" if row.get("stat_pass") else ""))

    stat_passes = [r for r in results if r.get("stat_pass")]
    econ_passes = [r for r in results if r.get("econ_pass")]
    all_under = all(r["underpowered"] for r in results)
    if all_under:
        verdict = "UNDERPOWERED (all cells N<%d — second look 2027-01-31)" % MIN_CELL_N
    elif not stat_passes:
        verdict = "FAIL (primary statistical PASS zero)"
    elif econ_passes:
        verdict = "PASS (statistical + economic)"
    else:
        verdict = "STAT-PASS-ONLY (gated book negative)"

    run = {"asof": today,
           "prereg": "equity-curve-shadow-gating-explore-prereg-2026-08-03",
           "snapshot": str(snap), "snapshot_sha256": digest,
           "forward_window": [FORWARD_FROM, FORWARD_CUTOFF],
           "epoch_boundaries": boundaries,
           "alpha_bonferroni": ALPHA, "m": len(PRIMARY_CELLS) * len(KS),
           "n_perm": args.n_perm, "seed_base": SEED,
           "null": "within-cell epoch-stratified permutation "
                   "(primary on unique-spaced series)",
           "results": results, "family_verdict": verdict}
    out = REPO_ROOT / "knowledge-base" / "raw" / "bt-results" / (
        "ecg_forward-%s.json" % today)
    out.write_text(json.dumps(run, indent=1))
    md = REPO_ROOT / "reports" / ("ecg-forward-%s.md" % today)
    md.parent.mkdir(parents=True, exist_ok=True)
    if not md.exists():
        lines = ["# ECG forward first look (#22) — %s" % today, "",
                 "> pre-reg: [[equity-curve-shadow-gating-explore-prereg-"
                 "2026-08-03]] (v2 forward)。m=%d α=%.5f n_perm=%d" % (
                     run["m"], ALPHA, args.n_perm), "",
                 "| cell | K | n_fwd | cov | contrast(US) | p | flags |",
                 "|---|---|---|---|---|---|---|"]
        fv = lambda v, f="%.3f": (f % v) if v is not None else "—"
        for r in results:
            flags = [x for x in (
                "STAT_PASS" if r.get("stat_pass") else "",
                "ECON_PASS" if r.get("econ_pass") else "",
                "UNDERPOWERED" if r.get("underpowered") else "",
                "COMP-CONF" if r.get("composition_confounded") else "") if x]
            lines.append("| %s | %d | %d | %s | %s | %s | %s |" % (
                r["cell"], r["K"], r["n_forward"], fv(r["coverage"], "%.2f"),
                fv(r["contrast_primary_us"], "%+.3f"),
                fv(r.get("p_one_sided"), "%.5f"), ", ".join(flags) or "—"))
        lines += ["", "## Family verdict: **%s**" % verdict, ""]
        md.write_text("\n".join(lines))
    print("\nfamily_verdict:", verdict)
    print("json:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
