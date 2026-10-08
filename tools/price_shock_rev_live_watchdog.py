#!/usr/bin/env python3
"""Price-Shock Rev Live N>=10 watchdog.

Fetches or reads closed demo trades, isolates the five Price-Shock Rev Live
rows (is_shadow=0), and writes an auto-demotion state file when N>=10 and
either EV<0 or Wilson lower<0.40.

NOTE (rule:R3 2026-10-08, registry ps-watchdog-demotion-state-unreachable):
on Render this runs as a cron with its *own* filesystem, so the state file it
writes is NOT visible to the web service. The binding DEMOTE path is the
in-process evaluation inside DemoTrader (same predicate via
modules/price_shock_rev_watchdog_core.py). This tool is the Discord readout
+ a local/manual override writer; its output is advisory on Render.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Single source of truth for the predicate — the trading process evaluates the
# same functions in-process (DemoTrader._refresh_price_shock_rev_in_process_demotions),
# so cron and engine can never disagree on N / EV / Wilson / population
# (registry ps-watchdog-demotion-state-unreachable, rule:R3 2026-10-08).
from modules.price_shock_rev_watchdog_core import (  # noqa: E402
    DEFAULT_PAGE_SIZE,
    MIN_LIVE_N,
    WATCHED_CELLS,
    WILSON_MIN,
    fetch_closed_trades_paged,
    filter_live_cell,
    metrics_for,
    run,
    verdict_for,
    wilson_lower,
)

__all__ = [
    "DEFAULT_PAGE_SIZE", "MIN_LIVE_N", "WATCHED_CELLS", "WILSON_MIN",
    "fetch_trades", "filter_live_cell", "load_trades_from_sqlite", "metrics_for",
    "run", "verdict_for", "wilson_lower", "write_state", "notify_discord", "parse_iso",
]

DEFAULT_API = "https://fx-ai-trader.onrender.com"
DEFAULT_LIMIT = DEFAULT_PAGE_SIZE  # per-page size (all pages are fetched)
DEFAULT_STATE = PROJECT_ROOT / "data" / "price_shock_rev_auto_demotions.json"

_SSL_CTX = ssl.create_default_context()
_SAFE_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=_SSL_CTX),
)


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def fetch_trades(api: str, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    """All closed trades, paged by `limit` (was: one page of 5000 — on 2026-10-08
    that reached back only to 2026-07-27 while ps live activation is 2026-05-18,
    so older fills silently dropped out of N; Codex P2 PR #306)."""
    return fetch_closed_trades_paged(
        api,
        opener=lambda req, timeout: _SAFE_OPENER.open(req, timeout=timeout),
        user_agent="price-shock-rev-live-watchdog/1.1",
        page_size=int(limit),
    )


def load_trades_from_sqlite(db_path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT entry_type, instrument, is_shadow, status, pnl_pips,
                      created_at, entry_time, exit_time
               FROM demo_trades
               WHERE status='CLOSED'"""
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def write_state(path: Path, demotions: list[dict[str, Any]]) -> None:
    existing: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("demotions", []):
            existing[(row.get("entry_type", ""), row.get("instrument", ""))] = row
    except FileNotFoundError:
        pass
    except Exception:
        pass
    for row in demotions:
        existing[(row["entry_type"], row["instrument"])] = row
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "tools/price_shock_rev_live_watchdog.py",
                "demotions": list(existing.values()),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def notify_discord(results: dict[str, Any], webhook: str | None) -> None:
    if not webhook:
        return
    lines = []
    for cell in results.values():
        m = cell["metrics"]
        if cell["verdict"] == "DEMOTE":
            lines.append(
                f"🚨 Price-Shock Rev {cell['entry_type']}: "
                f"Live N={m['n']} EV={m['ev_pips']:+.2f} → AUTO DEMOTE"
            )
        elif cell["verdict"] == "HOLD":
            lines.append(
                f"✅ Price-Shock Rev {cell['entry_type']}: "
                f"Live N={m['n']} EV={m['ev_pips']:+.2f} → 継続"
            )
    if not lines:
        return
    data = json.dumps({"content": "\n".join(lines)[:1900]}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "price-shock-watchdog/1.0"},
        method="POST",
    )
    try:
        with _SAFE_OPENER.open(req, timeout=10):
            pass
    except (urllib.error.URLError, TimeoutError, OSError):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="page size for /api/demo/trades (all pages are fetched)")
    parser.add_argument("--db", type=Path, help="Read closed trades from SQLite instead of Render API")
    parser.add_argument("--apply", action="store_true", help="Write auto-demotion state file")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--to-discord", action="store_true")
    args = parser.parse_args()

    try:
        trades = load_trades_from_sqlite(args.db) if args.db else fetch_trades(args.api, args.limit)
    except Exception as exc:
        print(f"ERROR: trade load failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    results, demotions, exit_code = run(trades)
    if args.apply and demotions:
        write_state(args.state, demotions)
    if args.to_discord:
        notify_discord(results, os.environ.get("DISCORD_WEBHOOK_URL"))
    print(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "min_live_n": MIN_LIVE_N,
        "wilson_min": WILSON_MIN,
        "applied": bool(args.apply and demotions),
        "demotions": demotions,
        "cells": results,
    }, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
