"""fib_reversal × USD_JPY × 1m sub-conditional Bonferroni audit.

aggressive-edge-deployment-2026-04-28 plan A4.

Pre-registered grid (HARKing 防止 — DO NOT modify after first run):
  Sessions (UTC hour binning): Tokyo (0-5), London (6-11), NY/LDN (12-16), NY/Late (17-23)
  Directions: BUY, SELL
  K = 4 sessions × 2 directions = 8 cells

Per-cell gates:
  N >= 10
  EV (post-friction 1.5pip) > 0
  Wilson lower bound at z_BF (Bonferroni-corrected for K=8) > 0.294 (BEV)

Survivors are reported as candidates for sub-conditional sentinel deployment.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Pre-registered (do not edit retroactively)
SESSIONS = [
    ("Tokyo", 0, 5),
    ("London", 6, 11),
    ("NY_LDN", 12, 16),
    ("NY_Late", 17, 23),
]
DIRECTIONS = ["BUY", "SELL"]
ENTRY_TYPE = "fib_reversal"
INSTRUMENT = "USD_JPY"
TF = "1m"
DAYS = 30
FRICTION_PIP = 1.5  # round-trip
BEV = 0.294


def _bonf_z(K: int, alpha: float = 0.05) -> float:
    from scipy.stats import norm
    return float(norm.ppf(1 - (alpha / K) / 2))


def _wilson_lower(wins: int, n: int, z: float) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / den)


def fetch_cell(db_path: str, session_label: str, h_lo: int, h_hi: int,
               direction: str, days: int) -> list:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""
        SELECT pnl_pips, is_shadow
        FROM demo_trades
        WHERE status='CLOSED'
          AND entry_type=?
          AND instrument=?
          AND tf=?
          AND direction=?
          AND CAST(strftime('%H', entry_time) AS INTEGER) BETWEEN ? AND ?
          AND exit_time >= datetime('now', ?)
          AND instrument NOT LIKE '%XAU%'
    """, (ENTRY_TYPE, INSTRUMENT, TF, direction, h_lo, h_hi, f"-{days} days")).fetchall()
    conn.close()
    return [(float(p or 0), int(s or 0)) for p, s in rows]


def evaluate_cell(trades: list, K: int) -> dict:
    pnls_gross = [p for p, _ in trades]
    pnls_net = [p - FRICTION_PIP for p in pnls_gross]
    n = len(pnls_net)
    if n == 0:
        return {"n": 0, "decision": "INSUFFICIENT_N"}
    wins = sum(1 for p in pnls_net if p > 0)
    losses_sum = sum(abs(p) for p in pnls_net if p < 0)
    wins_sum = sum(p for p in pnls_net if p > 0)
    wr = wins / n
    ev = sum(pnls_net) / n
    pf = (wins_sum / losses_sum) if losses_sum > 0 else float("inf")
    z_bf = _bonf_z(K)
    wL = _wilson_lower(wins, n, z_bf)
    n_live = sum(1 for _, s in trades if s == 0)
    n_shadow = n - n_live
    pass_n = n >= 10
    pass_ev = ev > 0
    pass_wilson = wL > BEV
    if pass_n and pass_ev and pass_wilson:
        decision = "SENTINEL_CANDIDATE"
    elif pass_n and pass_ev:
        decision = "WEAK_EDGE"
    else:
        decision = "REJECTED"
    return {
        "n": n,
        "n_live": n_live,
        "n_shadow": n_shadow,
        "wr": round(wr, 4),
        "ev_gross": round(sum(pnls_gross) / n, 3),
        "ev_net": round(ev, 3),
        "pf_net": round(pf, 3) if pf != float("inf") else "inf",
        "wilson_bf_lower": round(wL, 4),
        "z_bf": round(z_bf, 3),
        "pass_n": pass_n,
        "pass_ev": pass_ev,
        "pass_wilson": pass_wilson,
        "decision": decision,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="demo_trades.db")
    ap.add_argument("--days", type=int, default=DAYS)
    ap.add_argument("--out", default="raw/audits/fib_reversal_subcond_2026-04-28.json")
    args = ap.parse_args()

    K = len(SESSIONS) * len(DIRECTIONS)  # 8
    print(f"[fib_reversal subcond] K_bonferroni={K} (4 sessions × 2 directions)")
    print(f"  pre-registered grid: HARKing protection ON")
    print(f"  cell: {ENTRY_TYPE} × {INSTRUMENT} × {TF}, last {args.days}d, friction={FRICTION_PIP}pip")
    print()
    results = {}
    survivors = []
    for sess_label, h_lo, h_hi in SESSIONS:
        for direction in DIRECTIONS:
            cell_key = f"{sess_label}_{direction}"
            trades = fetch_cell(args.db, sess_label, h_lo, h_hi, direction, args.days)
            cell = evaluate_cell(trades, K)
            results[cell_key] = cell
            print(f"  {cell_key:<20} N={cell['n']:>3} (live={cell.get('n_live',0)}/sh={cell.get('n_shadow',0)}) "
                  f"WR={cell.get('wr','?'):>6} EV_net={cell.get('ev_net','?'):>7} "
                  f"PF={cell.get('pf_net','?'):>5} WL_BF={cell.get('wilson_bf_lower','?'):>6} "
                  f"→ {cell['decision']}")
            if cell["decision"] == "SENTINEL_CANDIDATE":
                survivors.append(cell_key)

    out_path = Path(_PROJECT_ROOT) / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "audit": "fib_reversal_subcond",
        "pre_registered_grid": {"sessions": SESSIONS, "directions": DIRECTIONS, "K": K},
        "params": {"entry_type": ENTRY_TYPE, "instrument": INSTRUMENT, "tf": TF,
                   "days": args.days, "friction_pip": FRICTION_PIP, "bev": BEV},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "survivors": survivors,
    }
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print()
    if survivors:
        print(f"✅ {len(survivors)} survivor cell(s) at K={K} Bonferroni:")
        for s in survivors:
            print(f"  - {s}")
        print(f"\nResult: {out_path}")
    else:
        print(f"⚠️ No survivors at K={K} Bonferroni gate")
        print(f"Result: {out_path}")


if __name__ == "__main__":
    main()
