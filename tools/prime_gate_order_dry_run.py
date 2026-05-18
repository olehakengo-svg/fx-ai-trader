#!/usr/bin/env python3
"""Replay PRIME gate order against recent Render demo trades.

This is an observational dry-run only: it reads the public demo trades API,
reclassifies each recent trade with the local PRIME classifier, then applies
the 2026-05-18 gate-order hot-fix in memory.
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.request
from urllib.error import HTTPError, URLError
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.confidence_q4_gate import should_shadow as q4_should_shadow  # noqa: E402
from modules.prime_gate import _PRIMES, classify_prime  # noqa: E402


API_URL = "https://fx-ai-trader.onrender.com/api/demo/trades?limit=3000"
PRIME_ORDER = [
    "stoch_trend_pullback_PRIME",
    "fib_reversal_PRIME",
    "stoch_trend_pullback_LONDON_LOWVOL",
    "bb_rsi_reversion_NY_ATRQ2",
    "sr_fib_confluence_GBP_ADXQ2",
    "engulfing_bb_TOKYO_EARLY",
]
EXPECTED_MIN_AB_FIRES = 6 if any(row[2] in ("A", "B") for row in _PRIMES) else 0


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _loads_maybe(value: Any) -> Any:
    if isinstance(value, str) and value.strip().startswith(("{", "[")):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def _rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("trades", "data", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
    return []


def _fetch(url: str) -> List[Dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": "fx-ai-trader-prime-dry-run/1.0"})
    last_error: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return _rows(payload)
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 * attempt)
                continue
            break
    if last_error:
        raise last_error
    return _rows(payload)


def _signal(row: Dict[str, Any]) -> str:
    return str(row.get("direction") or row.get("signal") or row.get("side") or "").upper()


def _confidence(row: Dict[str, Any]) -> float:
    try:
        return float(row.get("confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


def _sig(row: Dict[str, Any]) -> Dict[str, Any]:
    regime = _loads_maybe(row.get("regime"))
    if not isinstance(regime, dict):
        regime = {}
    return {
        "signal": _signal(row),
        "confidence": _confidence(row),
        "regime": regime,
    }


def _is_shadow(row: Dict[str, Any]) -> bool:
    value = row.get("is_shadow")
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _pnl(row: Dict[str, Any]) -> float:
    for key in ("pnl_pips", "pips", "profit_pips"):
        try:
            return float(row.get(key) or 0.0)
        except (TypeError, ValueError):
            continue
    return 0.0


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return (centre - margin) / denom


def _new_gate_live(row: Dict[str, Any], prime: Optional[Dict[str, Any]]) -> bool:
    entry_type = str(row.get("entry_type") or "")
    prime_live_lock = bool(prime and prime.get("tier") in ("A", "B"))

    is_shadow = False
    is_promoted = False
    if entry_type == "vwap_mean_reversion" and not prime_live_lock:
        is_shadow = True
    if entry_type == "bb_rsi_reversion" and not prime_live_lock:
        is_shadow = True
    if not prime_live_lock and q4_should_shadow(entry_type, _confidence(row)):
        is_shadow = True
    if prime_live_lock:
        is_shadow = False
        is_promoted = True
    if not is_promoted and not is_shadow:
        is_shadow = True
    return is_promoted and not is_shadow


def replay(rows: Iterable[Dict[str, Any]], now: datetime) -> Dict[str, Any]:
    cutoff = now - timedelta(days=30)
    stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "matches": 0,
        "fires": 0,
        "new_fires": 0,
        "pnl": 0.0,
        "wins": 0,
        "closed": 0,
        "tier": "",
        "lot": 0.0,
    })

    total_rows = 0
    recent_rows = 0
    for row in rows:
        total_rows += 1
        dt = _parse_dt(row.get("created_at") or row.get("entry_time") or row.get("opened_at"))
        if dt is None or dt < cutoff:
            continue
        recent_rows += 1
        entry_type = str(row.get("entry_type") or "")
        instrument = str(row.get("instrument") or "")
        prime = classify_prime(entry_type, instrument, _sig(row), dt)
        if not prime:
            continue

        name = str(prime["name"])
        stat = stats[name]
        stat["matches"] += 1
        stat["tier"] = prime["tier"]
        stat["lot"] = float(prime["lot_multiplier"])
        if _new_gate_live(row, prime):
            stat["fires"] += 1
            stat["pnl"] += _pnl(row) * float(prime["lot_multiplier"])
            if _is_shadow(row):
                stat["new_fires"] += 1
            if str(row.get("status") or "").upper() == "CLOSED":
                stat["closed"] += 1
                if _pnl(row) > 0:
                    stat["wins"] += 1

    return {
        "total_rows": total_rows,
        "recent_rows": recent_rows,
        "stats": stats,
    }


def main() -> int:
    rows = _fetch(API_URL)
    result = replay(rows, datetime.now(timezone.utc))
    stats = result["stats"]

    print("=== Dry-run replay (new gate order, 30d Render data) ===")
    print(f"Fetched rows: {result['total_rows']}  recent_30d: {result['recent_rows']}")
    total_fires = 0
    total_new = 0
    total_pnl = 0.0
    total_wins = 0
    total_closed = 0
    for name in PRIME_ORDER:
        stat = stats.get(name, {})
        tier = stat.get("tier") or ("C" if name == "engulfing_bb_TOKYO_EARLY" else "?")
        fires = int(stat.get("fires", 0))
        if tier == "C":
            fires = 0
        pnl = float(stat.get("pnl", 0.0))
        note = " (Tier C never)" if tier == "C" else ""
        print(f"PRIME {tier}: {name:<36} fires={fires:<3d} est_pnl={pnl:+.1f}p{note}")
        total_fires += fires
        total_new += int(stat.get("new_fires", 0))
        total_pnl += pnl
        total_wins += int(stat.get("wins", 0))
        total_closed += int(stat.get("closed", 0))

    wlo = _wilson_lower(total_wins, total_closed)
    print(f"Total NEW LIVE fires (est): {total_new}")
    print(f"Total PRIME A/B LIVE fires (est): {total_fires}")
    print(f"Spread/slippage adjusted PnL est: {total_pnl:+.1f}p")
    print(f"Wilson_lo est: {wlo:.3f} (closed={total_closed}, wins={total_wins})")

    if total_fires < EXPECTED_MIN_AB_FIRES:
        print(
            "WARNING: PRIME A/B LIVE fire estimate below pre-reg expectation "
            f"(>={EXPECTED_MIN_AB_FIRES}/30d)"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
