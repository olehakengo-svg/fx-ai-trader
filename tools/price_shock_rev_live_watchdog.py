#!/usr/bin/env python3
"""Price-Shock Rev Live N>=10 watchdog.

Fetches or reads closed demo trades, isolates the five Price-Shock Rev Live
rows (is_shadow=0), and writes an auto-demotion state file when N>=10 and
either EV<0 or Wilson lower<0.40. The state file is consumed by DemoTrader.
"""
from __future__ import annotations

import argparse
import json
import math
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
DEFAULT_API = "https://fx-ai-trader.onrender.com"
DEFAULT_LIMIT = 5000
DEFAULT_STATE = PROJECT_ROOT / "data" / "price_shock_rev_auto_demotions.json"
MIN_LIVE_N = 10
WILSON_MIN = 0.40

WATCHED_CELLS: tuple[tuple[str, str], ...] = (
    ("price_shock_rev_eur_gbp_h1_long", "EUR_GBP"),
    ("price_shock_rev_eur_aud_h1_long", "EUR_AUD"),
    ("price_shock_rev_usd_cad_h1_long", "USD_CAD"),
    ("price_shock_rev_nzd_jpy_h1_long", "NZD_JPY"),
    ("price_shock_rev_aud_jpy_h1_long", "AUD_JPY"),
)

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


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1.0 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def fetch_trades(api: str, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    url = f"{api.rstrip('/')}/api/demo/trades?status=closed&limit={int(limit)}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"refusing invalid API URL: {url!r}")
    req = urllib.request.Request(
        url, headers={"User-Agent": "price-shock-rev-live-watchdog/1.0"}
    )
    with _SAFE_OPENER.open(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if isinstance(payload, dict):
        return payload.get("trades", []) or []
    if isinstance(payload, list):
        return payload
    return []


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


def filter_live_cell(
    trades: list[dict[str, Any]], entry_type: str, instrument: str
) -> list[dict[str, Any]]:
    kept = []
    for trade in trades:
        if str(trade.get("entry_type") or "") != entry_type:
            continue
        if str(trade.get("instrument") or "") != instrument:
            continue
        if int(trade.get("is_shadow") or 0) != 0:
            continue
        if str(trade.get("status") or "").upper() != "CLOSED":
            continue
        kept.append(trade)
    return kept


def metrics_for(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [float(t.get("pnl_pips") or 0.0) for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    return {
        "n": n,
        "wins": wins,
        "losses": n - wins,
        "wr": (wins / n) if n else 0.0,
        "wilson_lower": wilson_lower(wins, n),
        "ev_pips": (sum(pnls) / n) if n else 0.0,
        "cumulative_pnl_pips": sum(pnls),
    }


def verdict_for(metrics: dict[str, Any]) -> str:
    if metrics["n"] < MIN_LIVE_N:
        return "WATCH"
    if metrics["ev_pips"] < 0 or metrics["wilson_lower"] < WILSON_MIN:
        return "DEMOTE"
    return "HOLD"


def run(trades: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    cells: dict[str, Any] = {}
    demotions: list[dict[str, Any]] = []
    for entry_type, instrument in WATCHED_CELLS:
        cell_trades = filter_live_cell(trades, entry_type, instrument)
        metrics = metrics_for(cell_trades)
        verdict = verdict_for(metrics)
        key = f"{entry_type} x {instrument}"
        cell = {
            "entry_type": entry_type,
            "instrument": instrument,
            "metrics": metrics,
            "verdict": verdict,
        }
        cells[key] = cell
        if verdict == "DEMOTE":
            demotions.append({
                "entry_type": entry_type,
                "instrument": instrument,
                "n": metrics["n"],
                "ev_pips": metrics["ev_pips"],
                "wilson_lower": metrics["wilson_lower"],
                "demoted_at": datetime.now(timezone.utc).isoformat(),
            })
    return cells, demotions, 1 if demotions else 0


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
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
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
