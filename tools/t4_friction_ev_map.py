#!/usr/bin/env python3
"""WS-Diag T4: friction-adjusted EV map over active entry_type × pair × dir.

Population = shadow, post-FIDELITY_CUTOFF, CLOSED, non-XAU, deduped by the
T8 forensic #3 estimand key (entry_type, instrument, direction, bar_ts) where
bar_ts = entry_time floored to the row's tf bar. This removes the engine-
reconstruction per-bar re-emit inflation (dedup death) so the map reflects what
a dedup-executing system would actually trade.

gross EV = mean shadow pnl_pips (paper; BE/Trail-inflated — screen only).
net EV   = gross EV − per-pair theoretical RT friction (friction-analysis.md).

Read-only. The demo_trades snapshot DB is an ephemeral production export
(tools/render_trades_snapshot.py); pass its path via --db.

Usage:
    python3 tools/t4_friction_ev_map.py --db <render-trades-snapshot>.db [--out result.json]

Result 2026-07-07 (render-trades-20260707b.db): net+ = 1/39 entry_types,
3/89 cells; sole net+ (vix_carry_unwind×USD_JPY×SELL) is live-negative.
See knowledge-base/wiki/analyses/friction-adjusted-ev-map-2026-07-07.md
"""
import argparse
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone

CUTOFF = "2026-04-16T08:00:00"  # _FIDELITY_CUTOFF

RT_FRICTION = {"USD_JPY": 2.14, "EUR_USD": 2.00, "GBP_USD": 4.53,
               "EUR_JPY": 2.50, "EUR_GBP": 3.0}
BEV_WR = {"USD_JPY": 0.344, "EUR_USD": 0.397, "GBP_USD": 0.379,
          "EUR_JPY": 0.337, "EUR_GBP": 0.571}
TF_MIN = {"15m": 15, "5m": 5, "1m": 1, "1h": 60, "30m": 30, "4h": 240,
          "M15": 15, "M5": 5, "H1": 60, None: 15, "": 15}


def rt_friction(inst):
    return RT_FRICTION.get(inst, 3.0)


def wilson_lo(wins, n, z=1.96):
    if n == 0:
        return float("nan")
    p = wins / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    rad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (center - rad) / denom


def bar_floor(entry_time, tf):
    m = TF_MIN.get(tf, 15)
    try:
        ts = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
    except Exception:
        return entry_time[:16]
    return ts.replace(minute=(ts.minute // m) * m, second=0,
                      microsecond=0).isoformat()


def build_map(db_path, cutoff=CUTOFF, min_n=30):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """SELECT entry_type, instrument, direction, pnl_pips, tf, entry_time,
                  COALESCE(dedup_violation,0) AS dv
           FROM demo_trades
           WHERE COALESCE(is_shadow,0)=1 AND status='CLOSED'
             AND pnl_pips IS NOT NULL AND instrument NOT LIKE 'XAU%'
             AND entry_time >= ?""",
        (cutoff,),
    ).fetchall()
    con.close()

    raw_n = len(rows)
    seen, deduped, dup_dropped = set(), [], 0
    for r in rows:
        key = (r["entry_type"], r["instrument"], r["direction"],
               bar_floor(r["entry_time"], r["tf"]))
        if key in seen:
            dup_dropped += 1
            continue
        seen.add(key)
        deduped.append(r)
    dv_flagged = sum(1 for r in rows if r["dv"] == 1)

    cells = defaultdict(list)
    for r in deduped:
        cells[(r["entry_type"], r["instrument"], r["direction"])].append(r["pnl_pips"])
    cell_rows = []
    for (et, inst, d), pnls in cells.items():
        n = len(pnls)
        wins = sum(1 for x in pnls if x > 0)
        gross = sum(pnls) / n
        cell_rows.append({
            "entry_type": et, "pair": inst, "dir": d, "n": n,
            "wr": round(100 * wins / n, 1), "gross_ev_pips": round(gross, 3),
            "friction_rt": rt_friction(inst),
            "net_ev_pips": round(gross - rt_friction(inst), 3),
            "sum_gross": round(sum(pnls), 1),
            "wilson_lo": round(wilson_lo(wins, n), 3), "bev_wr": BEV_WR.get(inst),
        })

    et_pool = defaultdict(list)
    for r in deduped:
        et_pool[r["entry_type"]].append((r["instrument"], r["pnl_pips"]))
    et_rows = []
    for et, lst in et_pool.items():
        n = len(lst)
        wins = sum(1 for _, p in lst if p > 0)
        et_rows.append({
            "entry_type": et, "n": n, "wr": round(100 * wins / n, 1),
            "gross_ev": round(sum(p for _, p in lst) / n, 3),
            "net_ev": round(sum(p - rt_friction(i) for i, p in lst) / n, 3),
            "sum_gross": round(sum(p for _, p in lst), 1),
        })
    cell_rows.sort(key=lambda x: -x["net_ev_pips"])
    et_rows.sort(key=lambda x: -x["net_ev"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": db_path.split("/")[-1], "cutoff": cutoff, "min_n": min_n,
        "population": {"raw": raw_n, "dedup_violation_flagged": dv_flagged,
                       "estimand_dup_dropped": dup_dropped, "deduped": len(deduped)},
        "friction_rt": RT_FRICTION,
        "entry_type_level": et_rows, "cell_level": cell_rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="render-trades snapshot .db")
    ap.add_argument("--out", default=None)
    ap.add_argument("--min-n", type=int, default=30)
    args = ap.parse_args()
    res = build_map(args.db, min_n=args.min_n)
    p = res["population"]
    print(f"Shadow (post-cutoff, CLOSED, non-XAU): raw={p['raw']} "
          f"dedup_violation={p['dedup_violation_flagged']} "
          f"estimand_dropped={p['estimand_dup_dropped']} deduped={p['deduped']} "
          f"(−{100*p['estimand_dup_dropped']/max(p['raw'],1):.1f}%)")
    print(f"\n{'entry_type':<32}{'N':>6}{'WR%':>7}{'grossEV':>9}{'netEV':>9}")
    for r in res["entry_type_level"]:
        if r["n"] < args.min_n:
            continue
        flag = "  ← net+" if r["net_ev"] > 0 else ""
        print(f"{r['entry_type']:<32}{r['n']:>6}{r['wr']:>7}{r['gross_ev']:>9}{r['net_ev']:>9}{flag}")
    pos = [r for r in res["cell_level"] if r["n"] >= args.min_n and r["net_ev_pips"] > 0]
    print(f"\nnet-positive cells (N>={args.min_n}): {len(pos)}")
    for r in pos:
        print(f"  {r['entry_type']}×{r['pair']}×{r['dir']}: N={r['n']} "
              f"WR={r['wr']}% net={r['net_ev_pips']:+.2f}p")
    if args.out:
        with open(args.out, "w") as f:
            json.dump(res, f, indent=2, default=str)
        print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
