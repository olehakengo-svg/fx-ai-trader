#!/usr/bin/env python3
"""Exit-Repair TP/SL grid BT — pre-reg LOCK 2026-07-07 (rule:R1).

Mechanically executes the 9-config grid defined in
  knowledge-base/wiki/decisions/exit-repair-tp-sl-prereg-2026-07-07.md

This is RESEARCH ONLY. It changes no live parameter. It reuses the production
signal + geometry pipeline (run_daytrade_backtest, backtest_mode=True) via the
env-gated EXIT_REPAIR_MODE path in app.py, which:
  - scales the final production TP/SL distances by the grid ratio levers,
  - forces BE/Trail + time-decay-BE OFF (ablation, pre-reg §2),
  - enters/exits at raw prices with zero embedded engine friction so that this
    harness deducts per-pair theoretical RT friction (pips) externally.

Primary endpoint (pre-reg §4): per-config portfolio-pooled friction-adjusted EV
(pips/trade), multiplicity m=9 BH-FDR q=0.10, daily block-bootstrap SE/p.
PASS if >=1 config has (a) FDR pass (b) WF 3-fold pos_ratio >= 2/3 (c) EV>0.

Usage:
    BT_MODE=1 NO_AUTOSTART=1 python3 tools/exit_repair_grid_bt.py [--boot N] [--pairs ...]
"""
import argparse
import concurrent.futures as _cf
import json
import multiprocessing as _mp
import os
import sys
from datetime import datetime, timezone

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")
os.environ["EXIT_REPAIR_MODE"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# ── pre-reg §2 grid (a priori, m=9) ──
TP_SCALES = [0.4, 0.6, 0.8]
SL_SCALES = [0.6, 0.8, 1.0]
GRID = [(tp, sl) for tp in TP_SCALES for sl in SL_SCALES]

# ── pre-reg §3 target entry_types (bb_rsi_reversion excluded: T10 KILL) ──
TARGET_ENTRY_TYPES = {
    "trendline_sweep", "wick_imbalance_reversion", "zz_pivot_v60_sr",
    "vix_carry_unwind", "dt_sr_channel_reversal", "vsg_jpy_reversal",
}

DEFAULT_PAIRS = ["USDJPY=X", "EURUSD=X", "GBPUSD=X", "EURJPY=X"]

# per-pair theoretical RT friction (pips) — friction-analysis.md (judgment basis)
RT_FRICTION = {"USD_JPY": 2.14, "EUR_USD": 2.00, "GBP_USD": 4.53, "EUR_JPY": 2.50}
# sensitivity floor (spread + exit-slip realized), described only (pre-reg §3/§7)
FRICTION_FLOOR = 1.30

PIP = {"USD_JPY": 0.01, "EUR_JPY": 0.01, "EUR_USD": 0.0001, "GBP_USD": 0.0001}

# diagnosis window (in-sample, drives the grid) — excluded from evaluation
DIAG_START = pd.Timestamp("2026-06-07", tz="UTC")
DIAG_END = pd.Timestamp("2026-07-08", tz="UTC")

LOOKBACK = 365
FDR_Q = 0.10


def _parse_ts(s):
    ts = pd.Timestamp(s)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts


def _gross_r(t):
    """Realized gross R (ATR multiples), friction-free (engine friction=0)."""
    ef = t.get("exit_friction_m", 0.0)
    if t["outcome"] == "WIN":
        return t.get("tp_m", 0.0) - ef
    return -(t.get("actual_sl_m", t.get("sl_m", 0.0)) + ef)


def _gross_pips(t):
    pair = t["pair"]
    return _gross_r(t) * (t["atr"] / PIP[pair])


def _net_pips(t, friction_map):
    return _gross_pips(t) - friction_map[t["pair"]]


def run_one(task):
    """Worker: run one (tp,sl,pair) grid cell; return picklable filtered rows.

    Runs in a spawned subprocess (ProcessPoolExecutor). Returns a dict with
    'rows' as plain JSON-safe records (ts stored as ISO string).
    """
    tp_scale, sl_scale, symbol, lookback = task
    os.environ["BT_MODE"] = "1"
    os.environ["NO_AUTOSTART"] = "1"
    os.environ["EXIT_REPAIR_MODE"] = "1"
    os.environ["EXIT_REPAIR_TP_SCALE"] = f"{tp_scale}"
    os.environ["EXIT_REPAIR_SL_SCALE"] = f"{sl_scale}"
    import app
    app._dt_bt_cache.clear()
    try:
        res = app.run_daytrade_backtest(symbol, lookback_days=lookback, interval="15m")
    except Exception as e:  # pragma: no cover
        return {"task": task, "raw": 0, "rows": [], "error": str(e)}
    tl = res.get("trade_log", []) or []
    rows = []
    for t in tl:
        if t.get("entry_type") not in TARGET_ENTRY_TYPES:
            continue
        if "atr" not in t or "pair" not in t:
            continue
        ts = _parse_ts(t["entry_time"])
        if DIAG_START <= ts < DIAG_END:
            continue  # in-sample exclusion
        gp = _gross_pips(t)
        rows.append({
            "entry_type": t["entry_type"], "pair": t["pair"], "sig": t.get("sig"),
            "outcome": t["outcome"], "ts": ts.isoformat(),
            "gross_pips": gp,
            "net_pips": gp - RT_FRICTION[t["pair"]],
            "net_pips_floor": gp - FRICTION_FLOOR,
        })
    return {"task": task, "raw": len(tl), "rows": rows}


def _hydrate(rows):
    """Attach _ts/_date pandas objects to worker rows for stats."""
    for r in rows:
        ts = pd.Timestamp(r["ts"])
        r["_ts"] = ts
        r["_date"] = ts.normalize()
    return rows


def block_bootstrap(rows, value_key="net_pips", b=2000, seed=1729):
    """Daily block bootstrap. Returns (ev, se, p_one_sided_gt0)."""
    if not rows:
        return 0.0, 0.0, 1.0
    by_date = {}
    for t in rows:
        by_date.setdefault(t["_date"], []).append(t[value_key])
    dates = list(by_date.keys())
    blocks = [np.array(by_date[d], dtype=float) for d in dates]
    n_blocks = len(blocks)
    ev = float(np.mean([v for blk in blocks for v in blk]))
    rng = np.random.default_rng(seed)
    means = np.empty(b)
    for i in range(b):
        idx = rng.integers(0, n_blocks, n_blocks)
        vals = np.concatenate([blocks[j] for j in idx])
        means[i] = vals.mean()
    se = float(np.std(means, ddof=1))
    # one-sided p for H1: EV>0  ->  fraction of resamples at or below 0
    p = float((np.sum(means <= 0.0) + 1) / (b + 1))
    return ev, se, p


def wf_folds(rows, value_key="net_pips", k=3):
    """Chronological k-fold; return list of fold EVs and pos_ratio."""
    if len(rows) < k:
        return [], 0.0
    srt = sorted(rows, key=lambda t: t["_ts"])
    n = len(srt)
    evs = []
    for f in range(k):
        seg = srt[f * n // k:(f + 1) * n // k]
        if not seg:
            continue
        evs.append(float(np.mean([t[value_key] for t in seg])))
    pos = sum(1 for e in evs if e > 0)
    return evs, (pos / len(evs) if evs else 0.0)


def bh_fdr(pvals, q=FDR_Q):
    """Benjamini-Hochberg. Returns set of indices that pass."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    passed = set()
    max_k = -1
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= (rank / m) * q:
            max_k = rank
    if max_k > 0:
        for rank, i in enumerate(order, start=1):
            if rank <= max_k:
                passed.add(i)
    return passed


def cell_stats(rows, value_key="net_pips"):
    """Secondary per-cell (pair×entry_type×dir) descriptive stats."""
    cells = {}
    for t in rows:
        key = f"{t['pair']}×{t['entry_type']}×{t['sig']}"
        cells.setdefault(key, []).append(t)
    out = {}
    for key, ts in cells.items():
        vals = np.array([t[value_key] for t in ts])
        wins = [v for v in vals if v > 0]
        losses = [v for v in vals if v <= 0]
        avg_w = float(np.mean(wins)) if wins else 0.0
        avg_l = float(np.mean(losses)) if losses else 0.0
        out[key] = {
            "n": len(ts),
            "wr": round(100 * len(wins) / len(ts), 1),
            "ev": round(float(vals.mean()), 3),
            "sum": round(float(vals.sum()), 1),
            "payoff": round(abs(avg_w / avg_l), 3) if avg_l else None,
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--pairs", nargs="*", default=DEFAULT_PAIRS)
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--lookback", type=int, default=LOOKBACK)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    t_start = datetime.now(timezone.utc)
    print("=" * 70)
    print("  Exit-Repair TP/SL grid BT (pre-reg LOCK 2026-07-07, rule:R1)")
    print(f"  Grid: TP{TP_SCALES} × SL{SL_SCALES} (m={len(GRID)}), 365d, diag-window excluded")
    print(f"  Pairs: {args.pairs}  workers={args.workers}")
    print("=" * 70)

    # ── parallel dispatch of all (tp,sl,pair) cells ──
    tasks = [(tp, sl, sym, args.lookback) for (tp, sl) in GRID for sym in args.pairs]
    by_config = {(tp, sl): [] for (tp, sl) in GRID}
    per_pair_raw_cfg = {(tp, sl): {} for (tp, sl) in GRID}
    ctx = _mp.get_context("spawn")
    done = 0
    with _cf.ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx) as ex:
        futs = {ex.submit(run_one, t): t for t in tasks}
        for fut in _cf.as_completed(futs):
            r = fut.result()
            tp, sl, sym, _lb = r["task"]
            by_config[(tp, sl)].extend(_hydrate(r["rows"]))
            per_pair_raw_cfg[(tp, sl)][sym] = r["raw"]
            done += 1
            err = f" ERR={r['error']}" if r.get("error") else ""
            print(f"  [{done:2d}/{len(tasks)}] TP{tp} SL{sl} {sym}: "
                  f"raw={r['raw']} kept={len(r['rows'])}{err}", flush=True)

    configs = []
    for (tp, sl) in GRID:
        rows = by_config[(tp, sl)]
        per_pair_raw = per_pair_raw_cfg[(tp, sl)]
        ev, se, p = block_bootstrap(rows, "net_pips", b=args.boot)
        ev_f, se_f, p_f = block_bootstrap(rows, "net_pips_floor", b=args.boot)
        evs, pos_ratio = wf_folds(rows, "net_pips")
        cfg = {
            "tp_scale": tp, "sl_scale": sl,
            "n": len(rows),
            "ev_pips": round(ev, 4), "se": round(se, 4), "p_one_sided": round(p, 5),
            "ev_pips_floor": round(ev_f, 4), "p_floor": round(p_f, 5),
            "wf_fold_evs": [round(e, 3) for e in evs],
            "wf_pos_ratio": round(pos_ratio, 3),
            "cells": cell_stats(rows, "net_pips"),
            "per_pair_raw": per_pair_raw,
        }
        configs.append(cfg)
        print(f"    N={cfg['n']}  EV={cfg['ev_pips']:+.3f}p  SE={cfg['se']:.3f}  "
              f"p={cfg['p_one_sided']:.4f}  WF={cfg['wf_fold_evs']} pos={cfg['wf_pos_ratio']}")

    # BH-FDR over m=9
    pvals = [c["p_one_sided"] for c in configs]
    passed_fdr = bh_fdr(pvals, FDR_Q)
    for i, c in enumerate(configs):
        c["fdr_pass"] = i in passed_fdr
        c["PASS"] = bool(c["fdr_pass"] and c["wf_pos_ratio"] >= 2 / 3 and c["ev_pips"] > 0)

    any_pass = any(c["PASS"] for c in configs)
    verdict = "PASS" if any_pass else "FAIL"

    elapsed = (datetime.now(timezone.utc) - t_start).total_seconds()
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prereg": "knowledge-base/wiki/decisions/exit-repair-tp-sl-prereg-2026-07-07.md",
        "grid": GRID, "m": len(GRID), "fdr_q": FDR_Q,
        "pairs": args.pairs, "lookback_days": args.lookback,
        "diag_window_excluded": [str(DIAG_START), str(DIAG_END)],
        "friction_rt_theoretical": RT_FRICTION, "friction_floor_sensitivity": FRICTION_FLOOR,
        "boot": args.boot,
        "verdict_mechanical": verdict,
        "configs": configs,
        "elapsed_s": round(elapsed, 1),
    }

    out = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge-base", "raw", "bt-results", "exit_repair_tp_sl_grid_2026_07.json",
    )
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print(f"  MECHANICAL VERDICT: {verdict}   (elapsed {elapsed:.0f}s)")
    print("  config          N     EV(p)    p      FDR  WFpos  PASS")
    for c in configs:
        print(f"  TP{c['tp_scale']} SL{c['sl_scale']}   {c['n']:5d}  {c['ev_pips']:+7.3f}  "
              f"{c['p_one_sided']:.3f}  {'Y' if c['fdr_pass'] else '·'}   "
              f"{c['wf_pos_ratio']:.2f}   {'PASS' if c['PASS'] else '·'}")
    print(f"\n  Saved: {out}")
    print("=" * 70)


if __name__ == "__main__":
    main()
