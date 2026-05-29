#!/usr/bin/env python3
"""Backfill missing `oanda_trades.strategy` from `oanda_audit`.

Two-phase resolution (most deterministic first):

  1. **Chain via oanda_trade_id → demo_trade_id → sent row** (no time window).
     Catches historical PYR orphans: a PYR child's filled audit row carries
     ``demo_trade_id='PYR_<parent_trade_id>'``. Pre-fix (commits a7b18453 /
     4cd44956 in 2026-05-20/05-26) the PYR open path did not write a 'sent'
     row, so the parent's sent row (looked up directly by demo_trade_id) is
     the only reliable strategy source.

  2. **Nearest-`sent` time-window fallback** via
     ``DemoDB.resolve_oanda_strategy_from_audit``. Same behavior as before.

The chain resolver is implemented here (NOT inside ``modules/demo_db.py``) to
keep the legacy DB module unchanged and avoid touching unrelated SQL patterns
in that file. All queries use parameterized ``?`` placeholders only.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.demo_db import DemoDB  # noqa: E402

TARGET_STRATEGIES = [
    "vix_carry_unwind",
    "trendline_sweep",
    "doji_breakout",
    "gbp_deep_pullback",
    "session_time_bias",
]

# Mode/MODE-name labels that must NEVER be promoted to a strategy attribution.
# Mirrors DemoDB._is_strategy_label so the chain resolver rejects the same set.
_MODE_LABELS = frozenset({
    "scalp", "daytrade", "swing",
    "scalp_5m", "5m_eur", "5m_gbp",
    "daytrade_1h", "daytrade_1h_usdjpy", "daytrade_1h_eurusd",
    "daytrade_1h_gbpusd", "daytrade_1h_gbpjpy", "daytrade_1h_eurjpy",
    "daytrade_1h_eurgbp", "daytrade_1h_audjpy", "daytrade_1h_audusd",
    "daytrade_1h_nzdusd",
    "daytrade_usdjpy", "daytrade_usdcad", "daytrade_usdchf",
    "daytrade_gbpusd", "daytrade_gbpjpy", "daytrade_eur",
    "daytrade_eurjpy", "daytrade_eurgbp", "daytrade_xau",
    "scalp_eur", "scalp_eurjpy", "scalp_xau",
})

# Audit labels for non-strategy code paths (resend, manual) that should not be
# treated as strategy attribution either.
_NON_STRATEGY_AUDIT_LABELS = frozenset({
    "", "resend_pending", "manual", "unknown",
})


def _is_strategy_label(label: str | None) -> bool:
    if not label:
        return False
    s = str(label).strip()
    if not s:
        return False
    if s in _MODE_LABELS or s in _NON_STRATEGY_AUDIT_LABELS:
        return False
    return True


def _default_db_path() -> str:
    return (
        os.environ.get("DB_PATH")
        or os.environ.get("DEMO_DB_PATH")
        or str(ROOT / "demo_trades.db")
    )


def resolve_strategy_via_audit_chain(
    conn: sqlite3.Connection, oanda_trade_id: str
) -> str:
    """Resolve strategy by chaining oanda_trade_id → demo_trade_id → sent row.

    Returns the strategy label if found, else empty string.

    Resolution path:
      1. Find any oanda_audit row with this ``oanda_trade_id``. Its
         ``demo_trade_id`` links the OANDA trade to the demo-side identity.
      2. Look up the matching ``bridge_status='sent'`` row by demo_trade_id.
      3. If demo_trade_id starts with ``PYR_``, also try the parent's
         demo_trade_id (suffix after ``PYR_``).

    All queries use ``?`` placeholders — no string concatenation.
    """
    if not oanda_trade_id:
        return ""
    filled = conn.execute(
        """
        SELECT demo_trade_id FROM oanda_audit
        WHERE oanda_trade_id=?
          AND demo_trade_id IS NOT NULL
          AND demo_trade_id != ''
        ORDER BY id DESC LIMIT 1
        """,
        (str(oanda_trade_id),),
    ).fetchone()
    if filled is None:
        return ""
    demo_trade_id = (
        filled["demo_trade_id"]
        if isinstance(filled, sqlite3.Row)
        else filled[0]
    ) or ""
    if not demo_trade_id:
        return ""
    # Exact demo_trade_id sent row first (covers normal paths where the
    # caller wrote the sent row at execute time).
    sent = conn.execute(
        """
        SELECT entry_type FROM oanda_audit
        WHERE demo_trade_id=? AND bridge_status='sent'
        ORDER BY id DESC LIMIT 1
        """,
        (demo_trade_id,),
    ).fetchone()
    if sent is not None:
        label = (
            sent["entry_type"]
            if isinstance(sent, sqlite3.Row)
            else sent[0]
        ) or ""
        if _is_strategy_label(label):
            return label
    # PYR child fallback: parent's trade_id is the suffix after `PYR_`.
    # Parent's sent row was written at the parent's open time (likely far
    # outside any time window from the PYR child's open_time), so chain
    # resolution is the only reliable path for pre-fix historical PYR orphans.
    if demo_trade_id.startswith("PYR_"):
        parent_id = demo_trade_id[len("PYR_"):]
        if parent_id:
            parent_sent = conn.execute(
                """
                SELECT entry_type FROM oanda_audit
                WHERE demo_trade_id=? AND bridge_status='sent'
                ORDER BY id DESC LIMIT 1
                """,
                (parent_id,),
            ).fetchone()
            if parent_sent is not None:
                label = (
                    parent_sent["entry_type"]
                    if isinstance(parent_sent, sqlite3.Row)
                    else parent_sent[0]
                ) or ""
                if _is_strategy_label(label):
                    return label
    return ""


def _stored_strategy_stats(db: DemoDB) -> dict[str, dict[str, float]]:
    with db._safe_conn() as conn:
        rows = conn.execute(
            """
            SELECT COALESCE(NULLIF(strategy, ''), 'UNKNOWN') AS strategy,
                   COUNT(*) AS n,
                   AVG(realized_pl) AS ev,
                   SUM(realized_pl) AS pnl
            FROM oanda_trades
            WHERE state='CLOSED'
            GROUP BY COALESCE(NULLIF(strategy, ''), 'UNKNOWN')
            """
        ).fetchall()
    return {
        row["strategy"]: {
            "n": int(row["n"] or 0),
            "ev": float(row["ev"] or 0.0),
            "pnl": float(row["pnl"] or 0.0),
        }
        for row in rows
    }


def _comparison(before: dict, after: dict) -> list[dict]:
    rows = []
    seen = set()
    for strategy in TARGET_STRATEGIES:
        old = before.get(strategy, {"n": 0, "ev": 0.0, "pnl": 0.0})
        new = after.get(strategy, {"n": 0, "ev": 0.0, "pnl": 0.0})
        rows.append({
            "strategy": strategy,
            "old_n": old["n"],
            "new_n": new["n"],
            "old_ev": round(old["ev"], 6),
            "new_ev": round(new["ev"], 6),
            "delta_n": new["n"] - old["n"],
            "delta_pnl": round(new["pnl"] - old["pnl"], 6),
        })
        seen.add(strategy)
    # Surface any strategy that gained N from backfill but isn't in TARGET_STRATEGIES.
    for strategy, new in after.items():
        if strategy in seen or strategy == "UNKNOWN":
            continue
        old = before.get(strategy, {"n": 0, "ev": 0.0, "pnl": 0.0})
        if new["n"] != old["n"]:
            rows.append({
                "strategy": strategy,
                "old_n": old["n"],
                "new_n": new["n"],
                "old_ev": round(old["ev"], 6),
                "new_ev": round(new["ev"], 6),
                "delta_n": new["n"] - old["n"],
                "delta_pnl": round(new["pnl"] - old["pnl"], 6),
            })
    return rows


def _scan_missing(db: DemoDB, window_minutes: int, apply: bool) -> dict:
    """Two-phase backfill (chain first, then time-window fallback).

    Returns a dict shaped like ``DemoDB.backfill_oanda_trade_strategy_from_audit``
    so the rest of the script can stay identical.
    """
    updates: list[dict] = []
    by_strategy: dict[str, dict] = {}
    chain_hits = 0
    window_hits = 0
    with db._lock:
        with db._safe_conn() as conn:
            rows = conn.execute(
                """
                SELECT oanda_trade_id, instrument, direction, open_time,
                       realized_pl
                FROM oanda_trades
                WHERE state='CLOSED'
                  AND (strategy IS NULL OR strategy='')
                ORDER BY open_time ASC
                """
            ).fetchall()
            for row in rows:
                oanda_id = row["oanda_trade_id"] or ""
                strategy = ""
                source = ""
                # Phase 1: chain resolution (deterministic).
                chained = resolve_strategy_via_audit_chain(conn, oanda_id)
                if chained:
                    strategy = chained
                    source = "chain"
                    chain_hits += 1
                else:
                    # Phase 2: nearest-sent time window (existing DemoDB API).
                    fallback = db.resolve_oanda_strategy_from_audit(
                        instrument=row["instrument"] or "",
                        direction=row["direction"] or "",
                        open_time=row["open_time"] or "",
                        window_minutes=window_minutes,
                        conn=conn,
                    )
                    if fallback:
                        strategy = fallback
                        source = f"window<={window_minutes}min"
                        window_hits += 1
                if not strategy:
                    continue
                pnl = float(row["realized_pl"] or 0.0)
                updates.append({
                    "oanda_trade_id": oanda_id,
                    "strategy": strategy,
                    "realized_pl": pnl,
                    "source": source,
                })
                agg = by_strategy.setdefault(strategy, {
                    "count": 0,
                    "realized_pl": 0.0,
                    "by_source": {},
                })
                agg["count"] += 1
                agg["realized_pl"] += pnl
                agg["by_source"][source] = agg["by_source"].get(source, 0) + 1
            if apply and updates:
                conn.executemany(
                    "UPDATE oanda_trades SET strategy=? WHERE oanda_trade_id=?",
                    [(u["strategy"], u["oanda_trade_id"]) for u in updates],
                )
                conn.commit()
    return {
        "apply": bool(apply),
        "window_minutes": window_minutes,
        "scanned_missing": len(rows),
        "updated_count": len(updates) if apply else 0,
        "would_update_count": len(updates),
        "distinct_strategies": len(by_strategy),
        "chain_hits": chain_hits,
        "window_hits": window_hits,
        "total_realized_pl_reattributed": round(
            sum(u["realized_pl"] for u in updates), 6
        ),
        "by_strategy": {
            k: {
                "count": v["count"],
                "realized_pl": round(v["realized_pl"], 6),
                "by_source": v["by_source"],
            }
            for k, v in sorted(by_strategy.items())
        },
        "updates": updates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill oanda_trades.strategy via (1) demo_trade_id chain "
            "resolution and (2) nearest-sent time-window fallback."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--db", default=_default_db_path())
    parser.add_argument("--window-minutes", type=int, default=5)
    args = parser.parse_args()

    db = DemoDB(args.db)
    before = _stored_strategy_stats(db)
    result = _scan_missing(
        db,
        window_minutes=args.window_minutes,
        apply=args.apply,
    )
    after = _stored_strategy_stats(db)
    if not args.apply:
        projected = json.loads(json.dumps(before))
        for strategy, agg in result["by_strategy"].items():
            cur = projected.setdefault(strategy, {"n": 0, "ev": 0.0, "pnl": 0.0})
            cur["n"] += int(agg["count"])
            cur["pnl"] += float(agg["realized_pl"])
            cur["ev"] = cur["pnl"] / cur["n"] if cur["n"] else 0.0
        after = projected

    payload = {
        "db": args.db,
        "mode": "apply" if args.apply else "dry-run",
        "summary": result,
        "strategy_old_vs_new": _comparison(before, after),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
