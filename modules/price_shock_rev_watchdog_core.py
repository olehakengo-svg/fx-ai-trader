"""Price-Shock Rev live watchdog — pure evaluation core (rule:R3, 2026-10-08).

Single source of truth for the N>=10 auto-demote predicate that was declared in
knowledge-base/wiki/decisions/price-shock-rev-live-activation-2026-05-18.md:

    live closed N >= 10  and  (EV < 0  or  Wilson lower(95%) < 0.40)  -> DEMOTE

Why this module exists (registry `ps-watchdog-demotion-state-unreachable`,
PR #306 Codex P1): the Render cron `fx-ai-price-shock-rev-watchdog` evaluated
this predicate and wrote `data/price_shock_rev_auto_demotions.json` on the
cron's *own* ephemeral filesystem, while the trading process (web service)
read the same relative path on *its* filesystem — so a DEMOTE verdict never
reached the order gate. The trading process now evaluates the identical
predicate in-process from its own SQLite (``DemoTrader._refresh_price_shock_rev_in_process_demotions``)
using the functions below; the cron keeps running for the Discord readout and
the state file remains a secondary (manual override / local) source.

Population is unchanged from the 05-18 declaration: ``is_shadow == 0`` and
``status == 'CLOSED'`` per (entry_type, instrument) cell. Keep this module free
of Flask / DemoTrader imports so both the cron tool and the engine can use it.
"""
from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

MIN_LIVE_N = 10
WILSON_MIN = 0.40

WATCHED_CELLS: tuple[tuple[str, str], ...] = (
    ("price_shock_rev_eur_gbp_h1_long", "EUR_GBP"),
    ("price_shock_rev_eur_aud_h1_long", "EUR_AUD"),
    ("price_shock_rev_usd_cad_h1_long", "USD_CAD"),
    ("price_shock_rev_nzd_jpy_h1_long", "NZD_JPY"),
    ("price_shock_rev_aud_jpy_h1_long", "AUD_JPY"),
)

# /api/demo/trades paging: the route caps nothing server-side, but a single
# `limit=5000` page only reached back to 2026-07-27 on 2026-10-08 (ps live
# activation is 2026-05-18) — older fills silently fell out of the window.
DEFAULT_PAGE_SIZE = 2000
MAX_PAGES = 200


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1.0 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def filter_live_cell(
    trades: Iterable[dict[str, Any]], entry_type: str, instrument: str
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


def run(trades: Iterable[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    """Evaluate every watched cell. Returns (cells, demotions, exit_code)."""
    trades = list(trades)
    cells: dict[str, Any] = {}
    demotions: list[dict[str, Any]] = []
    for entry_type, instrument in WATCHED_CELLS:
        cell_trades = filter_live_cell(trades, entry_type, instrument)
        metrics = metrics_for(cell_trades)
        verdict = verdict_for(metrics)
        key = f"{entry_type} x {instrument}"
        cells[key] = {
            "entry_type": entry_type,
            "instrument": instrument,
            "metrics": metrics,
            "verdict": verdict,
        }
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


def demoted_cells(trades: Iterable[dict[str, Any]]) -> set[tuple[str, str]]:
    """Set of (entry_type, instrument) whose verdict is DEMOTE (engine-facing)."""
    _cells, demotions, _code = run(trades)
    return {(row["entry_type"], row["instrument"]) for row in demotions}


def _trade_identity(trade: dict[str, Any]) -> Any:
    for key in ("trade_id", "id"):
        value = trade.get(key)
        if value not in (None, ""):
            return (key, value)
    return None


def fetch_closed_trades_paged(
    api: str,
    *,
    opener: Callable[[urllib.request.Request, int], Any],
    user_agent: str,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_pages: int = MAX_PAGES,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Fetch *all* closed trades via `/api/demo/trades?status=closed` with
    `limit`/`offset` paging. Stops at the first short page. Rows are de-duplicated
    by trade_id (a trade closing mid-fetch shifts the DESC ordering by one)."""
    page_size = max(1, int(page_size))
    base = f"{api.rstrip('/')}/api/demo/trades"
    parsed = urllib.parse.urlparse(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"refusing invalid API URL: {base!r}")
    out: list[dict[str, Any]] = []
    seen: set[Any] = set()
    for page in range(max_pages):
        offset = page * page_size
        url = f"{base}?status=closed&limit={page_size}&offset={offset}"
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with opener(req, timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if isinstance(payload, dict):
            rows = payload.get("trades", []) or []
        elif isinstance(payload, list):
            rows = payload
        else:
            rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ident = _trade_identity(row)
            if ident is not None:
                if ident in seen:
                    continue
                seen.add(ident)
            out.append(row)
        if len(rows) < page_size:
            break
    return out
