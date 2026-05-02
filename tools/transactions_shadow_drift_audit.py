#!/usr/bin/env python3
"""
Transactions Shadow Drift Audit
================================

Cross-checks the OANDA server-side transaction ledger against local
demo_trades labelling to surface the is_shadow drift bug:

    demo_trades.is_shadow=1  AND  oanda_trade_id IS NOT NULL

These rows look like Shadow in aggregate queries (so they hide from
Live PnL summaries) yet were actually filled at OANDA. memory: obs
S467 / 2026-05-01 fib_reversal C1 promote investigation.

This script also pulls the authoritative ORDER_FILL records from
OANDA so we have an external second-source for the same window
(catches local DB rows that were never written, e.g. Apr 30 01:46
oanda=380159).

Usage
-----
    python3 tools/transactions_shadow_drift_audit.py            # last 30d
    python3 tools/transactions_shadow_drift_audit.py --days 7
    python3 tools/transactions_shadow_drift_audit.py --from 2026-04-01 --to 2026-05-01
    python3 tools/transactions_shadow_drift_audit.py --json    # machine-readable

Exit code: 1 if any drifted rows are found, 0 otherwise.

Env requirements
----------------
    OANDA_TOKEN, OANDA_ACCOUNT_ID  (read by OandaClient)

Output
------
    1. Local SQL drift count + per-strategy breakdown (is_shadow=1 with
       oanda_trade_id) — leakage estimate.
    2. OANDA-side ORDER_FILL count for the window — sanity baseline.
    3. Mismatch list: oanda_trade_id present in local DB but missing
       from OANDA transactions, and vice versa.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

_PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(_PROJECT_ROOT))

from modules.oanda_client import OandaClient  # noqa: E402


def _rfc3339(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _local_db_path() -> Path:
    candidates = [
        _PROJECT_ROOT / "demo_trades.db",
        _PROJECT_ROOT / "data" / "demo_trades.db",
        _PROJECT_ROOT / "data" / "demo.db",
        _PROJECT_ROOT / "demo.db",
    ]
    for p in candidates:
        if p.exists() and p.stat().st_size > 0:
            return p
    raise FileNotFoundError(
        "demo_trades.db/demo.db not found. Run from a checkout that has the "
        "DB or set DEMO_DB_PATH env var."
    )


def query_local_drift(db_path: Path, from_iso: str, to_iso: str) -> dict:
    """Find demo_trades rows with is_shadow=1 yet oanda_trade_id set."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            SELECT trade_id, entry_type, instrument, direction,
                   entry_time, oanda_trade_id, is_shadow, pnl_pips,
                   outcome, status
            FROM demo_trades
            WHERE is_shadow = 1
              AND oanda_trade_id IS NOT NULL
              AND oanda_trade_id != ''
              AND entry_time >= ?
              AND entry_time <  ?
            ORDER BY entry_time
            """,
            (from_iso, to_iso),
        )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    by_strategy: dict = defaultdict(lambda: {"n": 0, "pnl": 0.0})
    for r in rows:
        s = r.get("entry_type") or "?"
        by_strategy[s]["n"] += 1
        try:
            by_strategy[s]["pnl"] += float(r.get("pnl_pips") or 0.0)
        except (TypeError, ValueError):
            pass
    return {"rows": rows, "by_strategy": dict(by_strategy)}


def fetch_oanda_fills(client: OandaClient, from_iso: str,
                      to_iso: str) -> list[dict]:
    """Walk TransactionList pages and fetch ORDER_FILL details via IDRange."""
    types = ["ORDER_FILL"]
    ok, listing = client.list_transactions(
        from_time=from_iso, to_time=to_iso, types=types, page_size=1000,
    )
    if not ok:
        raise RuntimeError(f"list_transactions failed: {listing}")
    pages = listing.get("pages") or []
    fills: list[dict] = []
    for page_url in pages:
        # page url shape: .../transactions/idrange?from=NNN&to=MMM&type=ORDER_FILL
        from_id = page_url.split("from=")[1].split("&")[0]
        to_id = page_url.split("to=")[1].split("&")[0]
        ok, body = client.get_transactions_id_range(
            from_id=from_id, to_id=to_id, types=types,
        )
        if not ok:
            raise RuntimeError(
                f"get_transactions_id_range({from_id},{to_id}) failed: {body}"
            )
        fills.extend(body.get("transactions") or [])
    if not pages:
        # Window had zero transactions; OANDA returns no pages.
        return []
    return fills


def reconcile(local_drift_rows: list[dict],
              oanda_fills: list[dict]) -> dict:
    """Find local oanda_trade_ids not in OANDA's ledger and vice versa."""
    local_ids = {
        str(r["oanda_trade_id"]) for r in local_drift_rows
        if r.get("oanda_trade_id")
    }
    oanda_ids: set[str] = set()
    for f in oanda_fills:
        for opened in (f.get("tradeOpened") or []) if isinstance(
            f.get("tradeOpened"), list
        ) else ([f.get("tradeOpened")] if f.get("tradeOpened") else []):
            tid = (opened or {}).get("tradeID")
            if tid:
                oanda_ids.add(str(tid))
    return {
        "local_only": sorted(local_ids - oanda_ids),
        "oanda_only_count": len(oanda_ids - local_ids),
        "common": len(local_ids & oanda_ids),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30,
                    help="Look-back window in days (ignored if --from given)")
    ap.add_argument("--from", dest="from_date", help="YYYY-MM-DD inclusive")
    ap.add_argument("--to", dest="to_date", help="YYYY-MM-DD exclusive")
    ap.add_argument("--json", action="store_true",
                    help="Emit machine-readable JSON")
    ap.add_argument("--no-oanda", action="store_true",
                    help="Skip OANDA-side fetch (local DB only)")
    args = ap.parse_args()

    if args.from_date:
        start = _parse_date(args.from_date)
        end = _parse_date(args.to_date) if args.to_date else (
            datetime.now(timezone.utc)
        )
    else:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=args.days)

    from_iso, to_iso = _rfc3339(start), _rfc3339(end)
    db_path = Path(os.environ.get("DEMO_DB_PATH") or _local_db_path())

    local = query_local_drift(db_path, from_iso, to_iso)

    out: dict = {
        "window": {"from": from_iso, "to": to_iso},
        "db_path": str(db_path),
        "local_drift": {
            "row_count": len(local["rows"]),
            "by_strategy": local["by_strategy"],
        },
    }

    if not args.no_oanda:
        client = OandaClient()
        if not client.configured:
            raise SystemExit(
                "OandaClient not configured: set OANDA_TOKEN and "
                "OANDA_ACCOUNT_ID in env"
            )
        fills = fetch_oanda_fills(client, from_iso, to_iso)
        out["oanda_fills"] = {"count": len(fills)}
        out["reconciliation"] = reconcile(local["rows"], fills)

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        w = out["window"]
        print(f"Window: {w['from']} → {w['to']}")
        print(f"DB: {out['db_path']}")
        print(f"Local drift rows (is_shadow=1 ∧ oanda_trade_id≠''): "
              f"{out['local_drift']['row_count']}")
        for s, agg in sorted(out["local_drift"]["by_strategy"].items(),
                             key=lambda kv: -kv[1]["n"]):
            print(f"  {s:32s} n={agg['n']:4d}  pnl={agg['pnl']:+.1f}p")
        if "oanda_fills" in out:
            print(f"OANDA ORDER_FILL count: {out['oanda_fills']['count']}")
            r = out["reconciliation"]
            print(f"  common ids:        {r['common']}")
            print(f"  local-only ids:    {len(r['local_only'])}"
                  f"  ({r['local_only'][:5]}{'…' if len(r['local_only']) > 5 else ''})")
            print(f"  oanda-only count:  {r['oanda_only_count']}")

    return 1 if out["local_drift"]["row_count"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
