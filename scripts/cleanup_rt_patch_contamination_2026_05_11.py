"""
One-shot cleanup for 2026-05-11 _rt_patch クロスペア価格汚染インシデント.

Root cause: modules/data.py:_rt_patch was applying USD/JPY _price_cache to all
pairs. When OANDA 401 occurred (4:38-4:57 UTC), the SLTP-Checker saw a Close of
~157.147 (USD/JPY spot) for GBP_USD / GBP_JPY / EUR_JPY DataFrames and
triggered 12 SL_HIT closures at the wrong price.

This script:
  1. Marks the 12 known contaminated trades as EXCLUDED
     (pnl_pips=0, pnl_r=0, outcome=BREAKEVEN,
      close_reason='SL_HIT_CORRUPTED_EXCLUDED').
  2. Recomputes eq_current from remaining CLOSED Live trades (oanda_trade_id != '')
     and updates system_kv (eq_current, dd_lot_mult, defensive_mode).
  3. Idempotent — running twice is safe (skips already-EXCLUDED rows).

USAGE (production Render shell):
    python3 scripts/cleanup_rt_patch_contamination_2026_05_11.py --apply

Without --apply, runs in dry-run mode (prints what would change).

Reference: CHANGELOG 2026-05-11,
           knowledge-base/wiki/lessons/lesson-rt-patch-cross-pair-contamination-2026-05-11.md
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# 12 trade_id prefixes reported corrupted at 2026-05-11 04:38-04:57 UTC.
# (production scan: exit_price clustered around 157.147 across non-USDJPY pairs)
CORRUPTED_PREFIXES = [
    "d76740e5-abe",
    "1cb57e3b-23b",
    "6615286a-531",
    "134b0d3a-e0e",
    "cf369fc6-7e6",
    "6733ca2c-c21",
    "b58c4d0e-c8f",
    "6e485d7e-110",
    "ce4ef924-977",
    "eca8346c-646",
    "fe977117-46e",
    "649d18c1-eef",
]

# Pair-aware sanity bounds. exit_price outside these is implausible
# (USD/JPY ~157 contaminating a 1.36 GBP_USD price is the smoking gun).
PLAUSIBLE_EXIT_RANGES = {
    "GBP_USD": (1.10, 1.45),
    "EUR_USD": (1.00, 1.20),
    "EUR_GBP": (0.78, 0.92),
    "GBP_JPY": (180.0, 220.0),
    "EUR_JPY": (160.0, 200.0),
    "USD_JPY": (140.0, 165.0),  # USD/JPY itself was not contaminated
    "XAU_USD": (1500.0, 3500.0),
}

CONTAMINATION_MARKER = "SL_HIT_CORRUPTED_EXCLUDED"


def _resolve_db_path() -> Path:
    env = os.environ.get("DEMO_DB_PATH")
    if env:
        return Path(env)
    # Match modules/demo_db.py:_resolve_db_path default behavior:
    # /var/data on Render persistent disk, else local.
    for candidate in ("/var/data/demo_trades.db", "demo_trades.db"):
        p = Path(candidate)
        if p.exists():
            return p
    return Path("demo_trades.db")


def find_corrupted(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Locate corrupted rows. Match by prefix AND verify exit_price out-of-range
    for the instrument, so accidental same-prefix collisions on healthy trades
    do NOT get rewritten."""
    rows: list[sqlite3.Row] = []
    for prefix in CORRUPTED_PREFIXES:
        cur = conn.execute(
            "SELECT trade_id, instrument, entry_price, exit_price, pnl_pips, "
            "outcome, close_reason, status "
            "FROM demo_trades WHERE trade_id LIKE ? AND status='CLOSED'",
            (prefix + "%",),
        )
        for row in cur.fetchall():
            if row["close_reason"] == CONTAMINATION_MARKER:
                # Already cleaned in a prior run — idempotent skip
                continue
            lo, hi = PLAUSIBLE_EXIT_RANGES.get(row["instrument"], (0.0, 0.0))
            ex = row["exit_price"]
            if ex is None:
                continue
            if lo <= ex <= hi:
                # exit_price actually plausible for the instrument — refuse to
                # rewrite, surface for manual review instead.
                print(
                    f"  [SKIP] {row['trade_id']} {row['instrument']} "
                    f"exit={ex} is within plausible range {lo}-{hi}; "
                    f"refusing to mark EXCLUDED.",
                    file=sys.stderr,
                )
                continue
            rows.append(row)
    return rows


def mark_excluded(conn: sqlite3.Connection, trade_id: str) -> int:
    """Set the row's exit_price=entry_price, pnl_pips=0, outcome=BREAKEVEN.
    Returns rowcount."""
    cur = conn.execute(
        "UPDATE demo_trades SET "
        "  exit_price = entry_price, "
        "  pnl_pips = 0, "
        "  pnl_r = 0, "
        "  outcome = 'BREAKEVEN', "
        "  close_reason = ? "
        "WHERE trade_id = ? AND status = 'CLOSED'",
        (CONTAMINATION_MARKER, trade_id),
    )
    return cur.rowcount


def delete_excluded(conn: sqlite3.Connection) -> list[str]:
    """Permanently DELETE all rows previously marked SL_HIT_CORRUPTED_EXCLUDED.

    Used when the EXCLUDED placeholder rows still pollute the UI / learning
    datasets (is_shadow=1 rows are still aggregated by Shadow stats and shown
    in Trade Log). Returns the list of deleted trade_ids.
    """
    cur = conn.execute(
        "SELECT trade_id FROM demo_trades WHERE close_reason = ?",
        (CONTAMINATION_MARKER,),
    )
    ids = [r["trade_id"] for r in cur.fetchall()]
    conn.execute(
        "DELETE FROM demo_trades WHERE close_reason = ?",
        (CONTAMINATION_MARKER,),
    )
    return ids


def recompute_equity_state(conn: sqlite3.Connection) -> dict:
    """Recompute eq_current from CLOSED Live trades.
    Returns dict with eq_current, eq_peak (unchanged here, just read), and
    suggested dd_lot_mult / defensive_mode."""
    # Sum pnl_pips of Live (oanda_trade_id != '') CLOSED, non-shadow trades.
    # XAU is included or excluded as per current production accounting; we
    # mirror the demo_trader.py logic which sums all CLOSED Live pnl_pips.
    cur = conn.execute(
        "SELECT COALESCE(SUM(pnl_pips), 0.0) AS s "
        "FROM demo_trades "
        "WHERE status = 'CLOSED' "
        "  AND is_shadow = 0 "
        "  AND oanda_trade_id IS NOT NULL "
        "  AND oanda_trade_id != ''"
    )
    eq_current = float(cur.fetchone()["s"] or 0.0)

    cur = conn.execute("SELECT value FROM system_kv WHERE key = 'eq_peak'")
    row = cur.fetchone()
    eq_peak = float(row["value"]) if row and row["value"] else 0.0

    # If eq_peak < eq_current (after cleanup raised eq_current), snap peak up.
    if eq_current > eq_peak:
        eq_peak = eq_current

    dd_pct = 0.0 if eq_peak <= 0 else max(0.0, (eq_peak - eq_current) / eq_peak)

    # Mirror modules/risk_analytics.get_dd_lot_multiplier thresholds (kept here
    # as a local approximation so this script is dependency-free).
    if dd_pct >= 0.30:
        dd_lot_mult = 0.2
    elif dd_pct >= 0.20:
        dd_lot_mult = 0.4
    elif dd_pct >= 0.10:
        dd_lot_mult = 0.7
    else:
        dd_lot_mult = 1.0
    defensive_mode = dd_lot_mult < 1.0

    return {
        "eq_current": eq_current,
        "eq_peak": eq_peak,
        "dd_pct": dd_pct,
        "dd_lot_mult": dd_lot_mult,
        "defensive_mode": defensive_mode,
    }


def write_equity_state(conn: sqlite3.Connection, state: dict) -> None:
    for key, value in [
        ("eq_current", f"{round(state['eq_current'], 2)}"),
        ("eq_peak", f"{round(state['eq_peak'], 2)}"),
        ("dd_lot_mult", f"{round(state['dd_lot_mult'], 2)}"),
        ("defensive_mode", "1" if state["defensive_mode"] else "0"),
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO system_kv (key, value) VALUES (?, ?)",
            (key, value),
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Actually write changes")
    ap.add_argument("--db", default=None, help="Override DB path")
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else _resolve_db_path()
    print(f"[cleanup] DB: {db_path}  apply={args.apply}")
    if not db_path.exists():
        print(f"[cleanup] DB not found: {db_path}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    rows = find_corrupted(conn)
    print(f"[cleanup] found {len(rows)} corrupted rows to EXCLUDE")
    for r in rows:
        print(
            f"  - {r['trade_id'][:16]}  {r['instrument']:7}  "
            f"entry={r['entry_price']}  exit={r['exit_price']}  "
            f"pnl_pips={r['pnl_pips']}"
        )

    if not args.apply:
        # Still recompute and report what eq_current would become
        state = recompute_equity_state(conn)
        print(
            f"[cleanup] DRY-RUN equity (pre-cleanup): "
            f"eq_current={state['eq_current']:.2f} eq_peak={state['eq_peak']:.2f} "
            f"dd_pct={state['dd_pct']:.1%} dd_lot_mult={state['dd_lot_mult']} "
            f"defensive_mode={state['defensive_mode']}"
        )
        print("[cleanup] run with --apply to write changes")
        return 0

    fixed = 0
    for r in rows:
        fixed += mark_excluded(conn, r["trade_id"])
    conn.commit()
    print(f"[cleanup] marked {fixed} rows EXCLUDED")

    state = recompute_equity_state(conn)
    write_equity_state(conn, state)
    conn.commit()
    print(
        f"[cleanup] wrote system_kv: eq_current={state['eq_current']:.2f} "
        f"eq_peak={state['eq_peak']:.2f} dd_pct={state['dd_pct']:.1%} "
        f"dd_lot_mult={state['dd_lot_mult']} "
        f"defensive_mode={state['defensive_mode']}"
    )
    conn.close()
    print("[cleanup] done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
