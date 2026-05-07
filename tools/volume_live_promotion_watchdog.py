#!/usr/bin/env python3
"""Volume Live Promotion Watchdog.

Emergency PAIR_PROMOTED cells from 2026-05-07 use a deliberately relaxed
Shadow EV/PF gate to preserve OANDA API tier volume. This watchdog is the R2
safety valve: once a promoted cell reaches Live N>=10, any negative Live EV
is a demotion event.
"""
from __future__ import annotations

import argparse
import json
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
PROMOTED_AT = "2026-05-07T00:00:00+00:00"
MIN_LIVE_N = 10

WATCHED_CELLS: list[dict[str, str]] = [
    {"entry_type": "vix_carry_unwind", "instrument": "USD_JPY", "promoted_at": PROMOTED_AT},
    {"entry_type": "mqe_gbpusd_fix", "instrument": "GBP_USD", "promoted_at": PROMOTED_AT},
    {"entry_type": "sr_fib_confluence", "instrument": "GBP_USD", "promoted_at": PROMOTED_AT},
    {"entry_type": "xs_momentum", "instrument": "GBP_USD", "promoted_at": PROMOTED_AT},
    {"entry_type": "session_time_bias", "instrument": "EUR_USD", "promoted_at": PROMOTED_AT},
    {"entry_type": "vsg_jpy_reversal", "instrument": "EUR_JPY", "promoted_at": PROMOTED_AT},
    {"entry_type": "trend_rebound", "instrument": "USD_JPY", "promoted_at": PROMOTED_AT},
    {"entry_type": "bb_squeeze_breakout", "instrument": "EUR_USD", "promoted_at": PROMOTED_AT},
    {"entry_type": "dt_sr_channel_reversal", "instrument": "EUR_JPY", "promoted_at": PROMOTED_AT},
    {"entry_type": "dt_bb_rsi_mr", "instrument": "USD_JPY", "promoted_at": PROMOTED_AT},
]

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
    url = f"{api.rstrip('/')}/api/demo/trades?limit={int(limit)}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print(f"ERROR: refusing invalid API URL: {url!r}", file=sys.stderr)
        sys.exit(2)
    req = urllib.request.Request(
        url, headers={"User-Agent": "volume-live-promotion-watchdog/1.0"}
    )
    try:
        with _SAFE_OPENER.open(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: API fetch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
    if isinstance(payload, dict):
        return payload.get("trades", []) or []
    if isinstance(payload, list):
        return payload
    return []


def filter_cell_trades(
    trades: list[dict[str, Any]],
    *,
    entry_type: str,
    instrument: str,
    promoted_at: datetime,
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for trade in trades:
        if str(trade.get("entry_type") or "") != entry_type:
            continue
        if str(trade.get("instrument") or "") != instrument:
            continue
        if int(trade.get("is_shadow", 0) or 0) != 0:
            continue
        if str(trade.get("status") or "").upper() != "CLOSED":
            continue
        ts = parse_iso(str(trade.get("created_at") or trade.get("entry_time") or ""))
        if ts is None or ts < promoted_at:
            continue
        kept.append(trade)
    return kept


def metrics_for(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [float(t.get("pnl_pips") or 0.0) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_loss = -sum(losses)
    pf = None
    if gross_loss > 0:
        pf = sum(wins) / gross_loss
    elif wins:
        pf = float("inf")
    n = len(pnls)
    mean = (sum(pnls) / n) if n else 0.0
    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "wr": (len(wins) / n) if n else 0.0,
        "ev_pips": mean,
        "profit_factor": pf,
    }


def verdict_for(metrics: dict[str, Any]) -> str:
    if metrics["n"] < MIN_LIVE_N:
        return "WATCH"
    if metrics["ev_pips"] < 0:
        return "DEMOTE"
    return "HOLD"


def run(
    trades: list[dict[str, Any]],
    *,
    cells: list[dict[str, str]] = WATCHED_CELLS,
) -> tuple[dict[str, dict[str, Any]], list[tuple[str, str]], int]:
    results: dict[str, dict[str, Any]] = {}
    demotions: list[tuple[str, str]] = []
    for cell in cells:
        promoted_at = parse_iso(cell["promoted_at"])
        if promoted_at is None:
            raise ValueError(f"bad promoted_at: {cell!r}")
        cell_trades = filter_cell_trades(
            trades,
            entry_type=cell["entry_type"],
            instrument=cell["instrument"],
            promoted_at=promoted_at,
        )
        metrics = metrics_for(cell_trades)
        verdict = verdict_for(metrics)
        key = f"{cell['entry_type']} x {cell['instrument']}"
        results[key] = {
            "entry_type": cell["entry_type"],
            "instrument": cell["instrument"],
            "promoted_at": cell["promoted_at"],
            "metrics": metrics,
            "verdict": verdict,
        }
        if verdict == "DEMOTE":
            demotions.append((cell["entry_type"], cell["instrument"]))
    return results, demotions, 1 if demotions else 0


def _tuple_literal(cell: tuple[str, str]) -> str:
    return f'("{cell[0]}", "{cell[1]}")'


def _replace_set_block(source: str, set_name: str, transform) -> str:
    marker = f"    {set_name} = {{\n"
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"{set_name} marker not found")
    body_start = start + len(marker)
    end = source.find("\n    }", body_start)
    if end < 0:
        raise ValueError(f"{set_name} closing marker not found")
    body = source[body_start:end]
    return source[:body_start] + transform(body) + source[end:]


def _set_block_contains(source: str, set_name: str, literal: str) -> bool:
    marker = f"    {set_name} = {{\n"
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"{set_name} marker not found")
    body_start = start + len(marker)
    end = source.find("\n    }", body_start)
    if end < 0:
        raise ValueError(f"{set_name} closing marker not found")
    body = source[body_start:end]
    return any(
        line.strip().startswith(literal + ",")
        for line in body.splitlines()
    )


def apply_auto_demotions_to_source(source: str, demotions: list[tuple[str, str]]) -> str:
    """Remove demoted cells from _PAIR_PROMOTED and add them to _PAIR_DEMOTED.

    This is intentionally narrow and line-oriented because demo_trader.py keeps
    tier state in literal tuple sets. It is idempotent for repeated watchdog runs.
    """
    literals = [_tuple_literal(cell) for cell in demotions]

    def remove_from_pair_promoted(body: str) -> str:
        kept = []
        for line in body.splitlines(keepends=True):
            stripped = line.strip()
            if any(stripped.startswith(literal + ",") for literal in literals):
                continue
            kept.append(line)
        return "".join(kept)

    updated = _replace_set_block(source, "_PAIR_PROMOTED", remove_from_pair_promoted)
    for cell in demotions:
        literal = _tuple_literal(cell)
        if _set_block_contains(updated, "_PAIR_DEMOTED", literal):
            continue

        def add_to_pair_demoted(body: str, literal: str = literal) -> str:
            return (
                f"        {literal},  # AUTO R2 DEMOTE: Live N>={MIN_LIVE_N} EV<0\n"
                + body
            )

        updated = _replace_set_block(updated, "_PAIR_DEMOTED", add_to_pair_demoted)
    return updated


def apply_auto_demotions(path: Path, demotions: list[tuple[str, str]]) -> None:
    source = path.read_text(encoding="utf-8")
    updated = apply_auto_demotions_to_source(source, demotions)
    if updated != source:
        path.write_text(updated, encoding="utf-8")


def _smoke() -> int:
    fake: list[dict[str, Any]] = []
    for i in range(10):
        fake.append({
            "entry_type": "vix_carry_unwind",
            "instrument": "USD_JPY",
            "is_shadow": 0,
            "status": "CLOSED",
            "pnl_pips": -1.0,
            "created_at": "2026-05-07T01:00:00Z",
        })
    for i in range(9):
        fake.append({
            "entry_type": "mqe_gbpusd_fix",
            "instrument": "GBP_USD",
            "is_shadow": 0,
            "status": "CLOSED",
            "pnl_pips": -5.0,
            "created_at": "2026-05-07T01:00:00Z",
        })
    fake.append({
        "entry_type": "vix_carry_unwind",
        "instrument": "USD_JPY",
        "is_shadow": 1,
        "status": "CLOSED",
        "pnl_pips": 999.0,
        "created_at": "2026-05-07T01:00:00Z",
    })
    results, demotions, exit_code = run(fake)
    assert demotions == [("vix_carry_unwind", "USD_JPY")]
    assert results["mqe_gbpusd_fix x GBP_USD"]["verdict"] == "WATCH"
    assert exit_code == 1
    print("smoke: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--apply", action="store_true",
                        help="Apply auto-demotions to modules/demo_trader.py")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        return _smoke()

    trades = fetch_trades(args.api, args.limit)
    results, demotions, exit_code = run(trades)
    if args.apply and demotions:
        apply_auto_demotions(PROJECT_ROOT / "modules" / "demo_trader.py", demotions)
    print(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "min_live_n": MIN_LIVE_N,
        "demotions": [{"entry_type": s, "instrument": p} for s, p in demotions],
        "applied": bool(args.apply and demotions),
        "cells": results,
        "exit_code": exit_code,
    }, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
