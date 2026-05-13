#!/usr/bin/env python3
"""Cell-conditional 365d BT for cell-promotion pre-reg LOCK (2026-05-13).

Target cells (TOP10 live+shadow, post-cutoff 2026-04-13):
  C1: mqe_gbpusd_fix × GBP_USD × Overlap (12-16 UTC)
  C2: vix_carry_unwind × USD_JPY × London (07-12 UTC)
  C3: sr_fib_confluence × GBP_USD × Overlap (12-16 UTC)
  C4: dt_sr_channel_reversal × EUR_JPY × Overlap (12-16 UTC)

Session bounds (UTC):
  Asia    : 00 - 07
  London  : 07 - 12
  Overlap : 12 - 16
  NY      : 16 - 24

Gate (pre-reg LOCK, 2026-05-13 09 UTC):
  - BT N >= 30 in cell
  - BT EV > 0 (friction included via app.run_daytrade_backtest backtest_mode=True)
  - WR Wilson LB (1.96) > BEV_WR  OR  PF lower bound > 1.0
  - On failure: stay shadow, no promotion
  - On pass: cell-conditional LIVE with Recovery Path lot 0.2x
  - Demote rule: Live N=30 in cell → EV<0 or Wilson<BEV → auto-降格

BEV_WR per pair (from KB friction-analysis):
  USD_JPY: 34.4
  EUR_USD: 39.7
  GBP_USD: 37.9
  EUR_JPY: 33.7
"""
import os, sys, json, math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

SESSION_BOUNDS = [
    ("Asia",    0,  7),
    ("London",  7, 12),
    ("Overlap",12, 16),
    ("NY",     16, 24),
]
BEV_WR = {"USD_JPY":34.4, "EUR_USD":39.7, "GBP_USD":37.9, "EUR_JPY":33.7}

TARGETS = [
    ("mqe_gbpusd_fix",        "GBP_USD", "Overlap"),
    ("vix_carry_unwind",      "USD_JPY", "London"),
    ("sr_fib_confluence",     "GBP_USD", "Overlap"),
    ("dt_sr_channel_reversal","EUR_JPY", "Overlap"),
]
PAIRS = [
    ("USDJPY=X","USD_JPY"),
    ("GBPUSD=X","GBP_USD"),
    ("EURJPY=X","EUR_JPY"),
]
LOOKBACK = 365
INTERVAL = "15m"

def classify_session(hour):
    for n,s,e in SESSION_BOUNDS:
        if s <= hour < e:
            return n
    return "?"

def parse_et(et_str):
    try:
        ts = datetime.fromisoformat(et_str.replace("Z","+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(et_str[:19],"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None

def compute_pnl_pip(t):
    outcome = t.get("outcome")
    tp_m = float(t.get("tp_m") or 0.0)
    sl_m = float(t.get("sl_m") or 0.0)
    friction = float(t.get("exit_friction_m") or 0.0)
    if outcome == "WIN":
        return tp_m - friction
    actual_sl = t.get("actual_sl_m")
    base = float(actual_sl) if actual_sl is not None else sl_m
    return -(base + friction)

def wilson_lb(wins, n, z=1.96):
    if n == 0: return 0.0
    p = wins/n
    denom = 1 + z*z/n
    centre = p + z*z/(2*n)
    half = z*math.sqrt((p*(1-p)+z*z/(4*n))/n)
    return (centre - half)/denom

def pf_lower_bound(pos_pnl, neg_pnl, n, z=1.96):
    # log(PF) ± z·SE where SE ≈ sqrt(2/n) (rough). Use bootstrap-style approx.
    if neg_pnl <= 0 or n < 5:
        return float("inf") if neg_pnl == 0 else 0.0
    pf = pos_pnl / neg_pnl
    if pf <= 0: return 0.0
    log_pf = math.log(pf)
    se = math.sqrt(2.0/n)
    return math.exp(log_pf - z*se)

def stats_block(trades):
    n = len(trades)
    if n == 0: return None
    wins = sum(1 for t in trades if t.get("outcome")=="WIN")
    pnls = [compute_pnl_pip(t) for t in trades]
    pos = sum(p for p in pnls if p>0)
    neg = sum(-p for p in pnls if p<0)
    return {
        "n": n,
        "wins": wins,
        "wr": wins/n*100,
        "ev": sum(pnls)/n,
        "pnl": sum(pnls),
        "pos_pnl": pos,
        "neg_pnl": neg,
        "pf": (pos/neg) if neg>0 else None,
        "wilson_lb": wilson_lb(wins, n)*100,
        "pf_lower": pf_lower_bound(pos, neg, n),
    }

def main():
    t0 = datetime.now()
    print(f"== Cell-conditional 365d BT — {t0:%Y-%m-%d %H:%M:%S} ==")
    print(f"  Lookback: {LOOKBACK}d  Interval: {INTERVAL}")
    print(f"  Targets:  {len(TARGETS)} cells")
    print()
    import app

    out = {"generated_at": t0.isoformat(), "lookback_days": LOOKBACK,
           "interval": INTERVAL, "pairs": {}, "targets": [], "cells": []}

    pair_trades = {}
    for yf, pair in PAIRS:
        print(f"[bt] {pair} ...")
        app._dt_bt_cache.clear()
        t_start = datetime.now()
        try:
            res = app.run_daytrade_backtest(yf, lookback_days=LOOKBACK, interval=INTERVAL)
        except Exception as e:
            print(f"  ! BT failed: {e}")
            out["pairs"][pair] = {"error": str(e)}
            continue
        if res.get("error"):
            print(f"  ! {res['error']}")
            out["pairs"][pair] = {"error": res["error"]}
            continue
        elapsed = (datetime.now()-t_start).total_seconds()
        tl = res.get("trade_log") or []
        pair_trades[pair] = tl
        out["pairs"][pair] = {"n_trades_total": len(tl), "elapsed_s": elapsed}
        print(f"  ✓ {len(tl)} trades in {elapsed:.0f}s")

    # cell decomposition
    for strat, pair, target_sess in TARGETS:
        tl = pair_trades.get(pair, [])
        cell_trades = []
        all_strat_trades = []
        sess_trades = defaultdict(list)
        for t in tl:
            if t.get("entry_type") != strat: continue
            ts = parse_et(t.get("entry_time",""))
            if ts is None: continue
            all_strat_trades.append(t)
            sess = classify_session(ts.hour)
            sess_trades[sess].append(t)
            if sess == target_sess:
                cell_trades.append(t)

        target_stats = stats_block(cell_trades)
        agg_stats = stats_block(all_strat_trades)
        sess_breakdown = {s: stats_block(v) for s,v in sess_trades.items()}

        bev = BEV_WR.get(pair, 35.0)
        gate_n = (target_stats and target_stats["n"] >= 30) if target_stats else False
        gate_ev = (target_stats and target_stats["ev"] > 0) if target_stats else False
        gate_wilson = (target_stats and target_stats["wilson_lb"] > bev) if target_stats else False
        gate_pf = (target_stats and target_stats["pf_lower"] > 1.0) if target_stats else False
        gate_pass = gate_n and gate_ev and (gate_wilson or gate_pf)

        cell = {
            "strategy": strat,
            "pair": pair,
            "session": target_sess,
            "bev_wr": bev,
            "cell": target_stats,
            "aggregate": agg_stats,
            "by_session": sess_breakdown,
            "gate": {
                "n_ge_30": gate_n,
                "ev_gt_0": gate_ev,
                "wilson_gt_bev": gate_wilson,
                "pf_lower_gt_1": gate_pf,
                "PASS": gate_pass,
            }
        }
        out["cells"].append(cell)
        out["targets"].append(f"{strat}×{pair}×{target_sess}")

        # console print
        print()
        print(f"--- {strat} × {pair} × {target_sess} (BEV_WR={bev}%) ---")
        if not target_stats:
            print("  CELL: no trades")
        else:
            ts_s = target_stats
            pf_str = "inf" if ts_s["pf"] is None else f"{ts_s['pf']:.2f}"
            print(f"  CELL : N={ts_s['n']:3d} WR={ts_s['wr']:5.1f}% Wilson_LB={ts_s['wilson_lb']:5.1f}% "
                  f"EV={ts_s['ev']:+7.3f} PF={pf_str} "
                  f"PF_LB={ts_s['pf_lower']:.2f} PnL={ts_s['pnl']:+.1f}")
        if agg_stats:
            pf_str_a = "inf" if agg_stats["pf"] is None else f"{agg_stats['pf']:.2f}"
            print(f"  AGG  : N={agg_stats['n']:3d} WR={agg_stats['wr']:5.1f}% "
                  f"EV={agg_stats['ev']:+7.3f} PF={pf_str_a}")
        for sn in ["Asia","London","Overlap","NY"]:
            s_s = sess_breakdown.get(sn)
            if not s_s:
                print(f"  {sn:8}: —")
                continue
            print(f"  {sn:8}: N={s_s['n']:3d} WR={s_s['wr']:5.1f}% EV={s_s['ev']:+7.3f}")
        gate_str = " ".join([
            f"N≥30:{'✓' if gate_n else '✗'}",
            f"EV>0:{'✓' if gate_ev else '✗'}",
            f"Wilson>BEV:{'✓' if gate_wilson else '✗'}",
            f"PF_LB>1:{'✓' if gate_pf else '✗'}",
        ])
        verdict = "🟢 PASS — LIVE promote 候補" if gate_pass else "🔴 FAIL — shadow 継続"
        print(f"  GATE : {gate_str}  →  {verdict}")

    # Write outputs
    out_dir = PROJECT / "knowledge-base" / "raw" / "bt-results"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_path = out_dir / f"cell-promotion-{date}.json"
    json_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\n✓ JSON: {json_path}")
    print(f"  Elapsed: {(datetime.now()-t0).total_seconds():.0f}s")

if __name__ == "__main__":
    main()
