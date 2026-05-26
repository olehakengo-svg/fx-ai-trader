#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
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


def _default_db_path() -> str:
    return os.environ.get("DB_PATH") or os.environ.get("DEMO_DB_PATH") or str(ROOT / "demo_trades.db")


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
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill oanda_trades.strategy from nearest sent oanda_audit rows."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--db", default=_default_db_path())
    parser.add_argument("--window-minutes", type=int, default=5)
    args = parser.parse_args()

    db = DemoDB(args.db)
    before = _stored_strategy_stats(db)
    result = db.backfill_oanda_trade_strategy_from_audit(
        apply=args.apply,
        window_minutes=args.window_minutes,
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
