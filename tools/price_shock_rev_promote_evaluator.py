#!/usr/bin/env python3
"""Price-Shock Rev Live N>=30 lot-ramp proposal evaluator.

This tool proposes only. It never changes lot multipliers.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API = "https://fx-ai-trader.onrender.com"
DEFAULT_LIMIT = 10000
MIN_LIVE_N = 30
WILSON_MIN = 0.50
BONFERRONI_M = 5
BONFERRONI_ALPHA = 0.01
WINDOW_DAYS = 42

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


def binomial_p_greater_or_equal(wins: int, n: int, p: float = 0.5) -> float:
    if n <= 0:
        return 1.0
    return min(
        1.0,
        sum(math.comb(n, k) * (p ** k) * ((1.0 - p) ** (n - k)) for k in range(wins, n + 1)),
    )


def fetch_trades(api: str, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    url = f"{api.rstrip('/')}/api/demo/trades?status=closed&limit={int(limit)}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"refusing invalid API URL: {url!r}")
    req = urllib.request.Request(
        url, headers={"User-Agent": "price-shock-rev-promote-evaluator/1.0"}
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


def _trade_time(trade: dict[str, Any]) -> datetime | None:
    return parse_iso(str(trade.get("exit_time") or trade.get("created_at") or trade.get("entry_time") or ""))


def six_week_windows(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dated = [(dt, float(t.get("pnl_pips") or 0.0)) for t in trades if (dt := _trade_time(t))]
    if not dated:
        return []
    dated.sort(key=lambda item: item[0])
    start = dated[0][0]
    end = dated[-1][0]
    windows = []
    cursor = start
    while cursor + timedelta(days=WINDOW_DAYS) <= end + timedelta(seconds=1):
        hi = cursor + timedelta(days=WINDOW_DAYS)
        pnls = [p for dt, p in dated if cursor <= dt < hi]
        if pnls:
            windows.append({
                "start": cursor.isoformat(),
                "end": hi.isoformat(),
                "n": len(pnls),
                "ev_pips": sum(pnls) / len(pnls),
            })
        cursor += timedelta(days=7)
    if not windows:
        pnls = [p for _, p in dated]
        windows.append({
            "start": start.isoformat(),
            "end": end.isoformat(),
            "n": len(pnls),
            "ev_pips": sum(pnls) / len(pnls),
        })
    return windows


def metrics_for(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [float(t.get("pnl_pips") or 0.0) for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    p_raw = binomial_p_greater_or_equal(wins, n, 0.5)
    windows = six_week_windows(trades)
    return {
        "n": n,
        "wins": wins,
        "losses": n - wins,
        "wr": (wins / n) if n else 0.0,
        "wilson_lower": wilson_lower(wins, n),
        "ev_pips": (sum(pnls) / n) if n else 0.0,
        "p_value_raw": p_raw,
        "p_value_bonferroni": min(1.0, p_raw * BONFERRONI_M),
        "six_week_windows": windows,
        "six_week_ev_all_positive": bool(windows) and all(w["ev_pips"] > 0 for w in windows),
    }


def verdict_for(metrics: dict[str, Any]) -> str:
    if metrics["n"] < MIN_LIVE_N:
        return "WATCH"
    if (
        metrics["wilson_lower"] >= WILSON_MIN
        and metrics["p_value_bonferroni"] < BONFERRONI_ALPHA
        and metrics["six_week_ev_all_positive"]
    ):
        return "PROPOSE_RAMP"
    return "HOLD_MIN_LOT"


def run(trades: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cells: dict[str, Any] = {}
    proposals: list[dict[str, Any]] = []
    for entry_type, instrument in WATCHED_CELLS:
        cell_trades = filter_live_cell(trades, entry_type, instrument)
        metrics = metrics_for(cell_trades)
        verdict = verdict_for(metrics)
        cell = {
            "entry_type": entry_type,
            "instrument": instrument,
            "metrics": metrics,
            "verdict": verdict,
        }
        cells[f"{entry_type} x {instrument}"] = cell
        if verdict == "PROPOSE_RAMP":
            proposals.append(cell)
    return cells, proposals


def notify_discord(proposals: list[dict[str, Any]], webhook: str | None) -> None:
    if not webhook or not proposals:
        return
    lines = [
        f"📈 Price-Shock Rev {p['entry_type']}: Live N={p['metrics']['n']} 達成、lot ramp 提案 司令塔へ"
        for p in proposals
    ]
    data = json.dumps({"content": "\n".join(lines)[:1900]}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "price-shock-promote/1.0"},
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
    parser.add_argument("--to-discord", action="store_true")
    args = parser.parse_args()
    try:
        trades = load_trades_from_sqlite(args.db) if args.db else fetch_trades(args.api, args.limit)
    except Exception as exc:
        print(f"ERROR: trade load failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    cells, proposals = run(trades)
    if args.to_discord:
        notify_discord(proposals, os.environ.get("DISCORD_WEBHOOK_URL"))
    print(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "min_live_n": MIN_LIVE_N,
        "wilson_min": WILSON_MIN,
        "bonferroni_m": BONFERRONI_M,
        "bonferroni_alpha": BONFERRONI_ALPHA,
        "proposals": [
            {"entry_type": p["entry_type"], "instrument": p["instrument"]}
            for p in proposals
        ],
        "cells": cells,
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
