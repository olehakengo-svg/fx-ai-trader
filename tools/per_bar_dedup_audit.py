#!/usr/bin/env python3
"""
Per-Bar Dedup Audit (rule:R3)
==============================

Detects R3 structural bugs where the same (entry_type, instrument) emits
multiple trades within a single bar — i.e. per-bar dedup gate missing or
mis-wired. Production audit (2026-05-03) found 228 violations across 18
strategy/pair combos, only 110 flagged in `dedup_violation`.

Distinct from the existing `dedup_violation` column (which only covers
the 3 SHADOW_ALWAYS strategies vsg/rsk/mqe per the 2026-04-30 backfill);
this scan covers ALL strategies and is TF-aware.

Bar-window mapping:
    tf='1m'   -> 60 seconds
    tf='5m'   -> 300 seconds
    tf='15m'  -> 900 seconds
    tf='1h'   -> 3600 seconds
    other/null-> 60 seconds (conservative)

Usage:
    python3 tools/per_bar_dedup_audit.py                    # local DB, 30d
    python3 tools/per_bar_dedup_audit.py --prod              # query Render API
    python3 tools/per_bar_dedup_audit.py --prod --days 7
    python3 tools/per_bar_dedup_audit.py --prod --json
    python3 tools/per_bar_dedup_audit.py --prod --strategy sr_anti_hunt_bounce

Exit 1 if any unflagged violations found, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

_PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
_PROD_API = "https://fx-ai-trader.onrender.com/api/demo/trades"

_TF_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400,
}


def _bar_seconds(tf: str | None) -> int:
    return _TF_SECONDS.get((tf or "").strip(), 60)


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def fetch_prod_trades(limit: int = 5000) -> list[dict]:
    req = urllib.request.Request(
        f"{_PROD_API}?limit={limit}",  # nosem
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosem
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("trades", [])


def fetch_local_trades(db_path: Path, since_iso: str) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT trade_id, entry_type, instrument, direction, "
            "       entry_time, tf, pnl_pips, dedup_violation, "
            "       is_shadow, oanda_trade_id "
            "FROM demo_trades WHERE entry_time >= ? "
            "ORDER BY entry_time",
            (since_iso,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def detect_violations(trades: list[dict]) -> list[dict]:
    """Group by (entry_type, instrument) and find consecutive entries
    with delta < that strategy's bar duration."""
    groups: dict = defaultdict(list)
    for t in trades:
        et = t.get("entry_type")
        inst = t.get("instrument")
        ts = _parse_ts(t.get("entry_time") or "")
        if not (et and inst and ts):
            continue
        groups[(et, inst)].append((ts, t))

    violations: list[dict] = []
    for (et, inst), items in groups.items():
        items.sort(key=lambda x: x[0])
        for i in range(1, len(items)):
            prev_ts, prev = items[i - 1]
            cur_ts, cur = items[i]
            tf = cur.get("tf") or prev.get("tf")
            window = _bar_seconds(tf)
            delta = (cur_ts - prev_ts).total_seconds()
            if delta < window:
                violations.append({
                    "entry_type": et,
                    "instrument": inst,
                    "tf": tf,
                    "bar_window_s": window,
                    "delta_s": round(delta, 1),
                    "prev_trade_id": prev.get("trade_id"),
                    "cur_trade_id": cur.get("trade_id"),
                    "cur_entry_time": cur.get("entry_time"),
                    "cur_pnl_pips": cur.get("pnl_pips"),
                    "cur_already_flagged": (cur.get("dedup_violation") or 0) == 1,
                    "cur_is_live": bool((cur.get("oanda_trade_id") or "").strip()),
                })
    return violations


def summarize(violations: list[dict]) -> dict:
    by_combo: dict = defaultdict(
        lambda: {"n": 0, "flagged": 0, "live": 0, "pnl": 0.0,
                 "tf": None, "window_s": None}
    )
    for v in violations:
        key = f"{v['entry_type']}/{v['instrument']}"
        a = by_combo[key]
        a["n"] += 1
        a["flagged"] += int(v["cur_already_flagged"])
        a["live"] += int(v["cur_is_live"])
        try:
            a["pnl"] += float(v["cur_pnl_pips"] or 0.0)
        except (TypeError, ValueError):
            pass
        a["tf"] = v["tf"]
        a["window_s"] = v["bar_window_s"]
    return {
        "total": len(violations),
        "flagged": sum(1 for v in violations if v["cur_already_flagged"]),
        "unflagged": sum(1 for v in violations
                         if not v["cur_already_flagged"]),
        "live_executions": sum(1 for v in violations if v["cur_is_live"]),
        "by_combo": dict(by_combo),
    }


def _local_db_path() -> Path:
    for p in [
        _PROJECT_ROOT / "demo_trades.db",
        _PROJECT_ROOT / "data" / "demo_trades.db",
        _PROJECT_ROOT / "data" / "demo.db",
        _PROJECT_ROOT / "demo.db",
    ]:
        if p.exists() and p.stat().st_size > 0:
            return p
    raise FileNotFoundError("No local demo DB found; pass --prod or set DEMO_DB_PATH")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod", action="store_true",
                    help="Query Render production API instead of local DB")
    ap.add_argument("--limit", type=int, default=5000,
                    help="Prod API limit (default 5000)")
    ap.add_argument("--days", type=int, default=30,
                    help="Local DB lookback in days (ignored with --prod)")
    ap.add_argument("--strategy", default=None,
                    help="Filter to one entry_type")
    ap.add_argument("--json", action="store_true",
                    help="Machine-readable output")
    args = ap.parse_args()

    if args.prod:
        trades = fetch_prod_trades(limit=args.limit)
        source = f"prod API limit={args.limit}"
    else:
        since = (datetime.now(timezone.utc)
                 - timedelta(days=args.days)).isoformat()
        db_path = Path(os.environ.get("DEMO_DB_PATH") or _local_db_path())
        trades = fetch_local_trades(db_path, since)
        source = f"local DB={db_path}, since={since}"

    if args.strategy:
        trades = [t for t in trades if t.get("entry_type") == args.strategy]

    violations = detect_violations(trades)
    summary = summarize(violations)

    out = {
        "source": source,
        "trades_scanned": len(trades),
        "summary": {
            "total_violations": summary["total"],
            "flagged_dedup_violation": summary["flagged"],
            "unflagged_violations": summary["unflagged"],
            "violations_with_oanda_fill": summary["live_executions"],
        },
        "by_combo": summary["by_combo"],
    }

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print(f"Source:                {out['source']}")
        print(f"Trades scanned:        {out['trades_scanned']}")
        print(f"Total violations:      {out['summary']['total_violations']}")
        print(f"  already flagged:     {out['summary']['flagged_dedup_violation']}")
        print(f"  UNFLAGGED:           {out['summary']['unflagged_violations']}")
        print(f"  with OANDA fill:     {out['summary']['violations_with_oanda_fill']}")
        print()
        print(f"{'combo':<42s}{'tf':>5s}{'win':>5s}{'n':>5s}"
              f"{'flag':>6s}{'live':>6s}{'pnl':>10s}")
        items = sorted(out["by_combo"].items(),
                       key=lambda kv: kv[1]["pnl"])  # most negative first
        for k, a in items:
            print(f"{k:<42s}{(a['tf'] or '?'):>5s}{a['window_s']:>5d}"
                  f"{a['n']:>5d}{a['flagged']:>6d}{a['live']:>6d}"
                  f"{a['pnl']:>+9.1f}p")

    return 1 if summary["unflagged"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
