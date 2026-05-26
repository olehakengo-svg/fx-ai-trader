#!/usr/bin/env python3
"""Stage-3 edge-cell LIVE watchdog (API-driven, hot-fix 2026-05-26).

Spec: knowledge-base/wiki/decisions/edge-cells-stage3-live-promote-2026-05-26.md

All state read/write goes through /api/admin/edge_cell/state (token-auth via
EDGE_CELL_ADMIN_TOKEN). The previous SQLite-direct approach failed on Render
cron workers because they don't mount the fx-ai-trader /var/data disk.

Dry-run by default. Render cron runs with --apply --to-discord.
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API = os.environ.get("API_BASE", "https://fx-ai-trader.onrender.com")
DEFAULT_LIMIT = 10000
LOCK_DATE = "2026-05-26"
MIN_N = 10
ACCOUNT_DD_TRIGGER_PCT = 0.08
DAILY_CELL_DISABLE_JPY = -6_822.0
ROLLING_5D_DD_TRIGGER_PCT = 0.05

_SSL_CTX = ssl.create_default_context()
_SAFE_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=_SSL_CTX),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(ts: Any) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def fetch_json(url: str, user_agent: str, *, headers: dict | None = None,
               method: str = "GET", body: bytes | None = None) -> Any:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"refusing invalid URL: {url!r}")
    hdrs = {"User-Agent": user_agent}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs, method=method, data=body)
    with _SAFE_OPENER.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_trades(api: str, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    qs = urllib.parse.urlencode({
        "limit": int(limit),
        "date_from": LOCK_DATE,
        "status": "closed",
    })
    payload = fetch_json(
        f"{api.rstrip('/')}/api/demo/trades?{qs}",
        "edge-cell-watchdog/2.0",
    )
    if isinstance(payload, dict):
        return payload.get("trades", []) or []
    if isinstance(payload, list):
        return payload
    return []


def fetch_state(api: str, token: str) -> dict[str, Any]:
    """Read all per-cell stages + lock_nav + current_nav via admin endpoint."""
    return fetch_json(
        f"{api.rstrip('/')}/api/admin/edge_cell/state",
        "edge-cell-watchdog/2.0",
        headers={"X-Admin-Token": token},
    )


def post_state(api: str, token: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
    """Batch-update per-cell stages via admin endpoint."""
    body = json.dumps({"actions": actions}).encode("utf-8")
    return fetch_json(
        f"{api.rstrip('/')}/api/admin/edge_cell/state",
        "edge-cell-watchdog/2.0",
        headers={"X-Admin-Token": token, "Content-Type": "application/json"},
        method="POST",
        body=body,
    )


def _trade_cell_id(trade: dict[str, Any]) -> str:
    return str(trade.get("edge_cell_id") or "").strip()


def _pnl_pips(trade: dict[str, Any]) -> float:
    try:
        return float(trade.get("pnl_pips") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _pnl_jpy(trade: dict[str, Any]) -> float:
    for key in ("pnl_jpy", "realized_pl_jpy", "pl_jpy"):
        if trade.get(key) is not None:
            try:
                return float(trade.get(key) or 0.0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _trade_time(trade: dict[str, Any]) -> datetime | None:
    return parse_iso(trade.get("exit_time") or trade.get("entry_time") or trade.get("created_at"))


def live_edge_trades(trades: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Filter to Live (is_shadow=0) CLOSED trades grouped by edge_cell_id.

    CRITICAL per LIVE/Shadow 分離必須 lesson: only is_shadow=0 trades count.
    """
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        if int(trade.get("is_shadow") or 0) != 0:
            continue
        if str(trade.get("status") or "").upper() != "CLOSED":
            continue
        cell_id = _trade_cell_id(trade)
        if not cell_id:
            continue
        cells[cell_id].append(trade)
    return dict(cells)


def max_drawdown(values: list[float]) -> float:
    peak = 0.0
    equity = 0.0
    max_dd = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def metrics_for(trades: list[dict[str, Any]], generated_at: datetime,
                lock_nav_jpy: float) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda t: _trade_time(t) or datetime.min.replace(tzinfo=timezone.utc))
    pnls = [_pnl_pips(t) for t in ordered]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_loss = -sum(losses)
    pf = None
    if gross_loss > 0:
        pf = sum(wins) / gross_loss
    elif wins:
        pf = float("inf")

    five_day_cutoff = generated_at - timedelta(days=5)
    pnl_jpy_5d = [
        _pnl_jpy(t)
        for t in ordered
        if (_trade_time(t) or generated_at) >= five_day_cutoff
    ]
    today = generated_at.date()
    today_jpy = sum(
        _pnl_jpy(t)
        for t in ordered
        if (_trade_time(t) or generated_at).date() == today
    )
    active_dates = {
        (_trade_time(t) or generated_at).date().isoformat()
        for t in ordered
        if (_trade_time(t) or generated_at) >= generated_at - timedelta(days=7)
    }
    n = len(pnls)
    dd_5d_jpy = max_drawdown(pnl_jpy_5d)
    dd_5d_pct = dd_5d_jpy / lock_nav_jpy if lock_nav_jpy > 0 else 0.0
    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "wr": (len(wins) / n) if n else 0.0,
        "ev_pips": (sum(pnls) / n) if n else 0.0,
        "profit_factor": pf,
        "pnl_pips_sum": sum(pnls),
        "pnl_jpy_today": today_jpy,
        "rolling_5d_dd_jpy": dd_5d_jpy,
        "rolling_5d_dd_pct": dd_5d_pct,
        "zero_fill_7d": len(active_dates) == 0,
    }


def compute_account_dd_pct(lock_nav: float, current_nav: float | None) -> float:
    """DD from LOCK NAV snapshot to current NAV.

    Returns fraction (0.05 = 5%). Positive means equity dropped from lock.
    If lock_nav unknown (0), return 0.
    """
    if not lock_nav or lock_nav <= 0 or current_nav is None:
        return 0.0
    return max(0.0, (lock_nav - current_nav) / lock_nav)


def evaluate(
    trades: list[dict[str, Any]],
    state: dict[str, Any],
    *,
    cell_ids: list[str],
) -> dict[str, Any]:
    generated_at = _now()
    ts = generated_at.isoformat()
    lock_nav = float(state.get("lock_nav_jpy") or 0.0)
    current_nav = state.get("current_nav_jpy")
    if current_nav is not None:
        try:
            current_nav = float(current_nav)
        except (TypeError, ValueError):
            current_nav = None
    stages = {cid: int(state.get("stages", {}).get(cid, 1)) for cid in cell_ids}
    by_cell = live_edge_trades(trades)
    cells: dict[str, Any] = {}
    actions: list[dict[str, Any]] = []
    account_dd_pct = compute_account_dd_pct(lock_nav, current_nav)

    # Global kill: account DD > 8% from LOCK snapshot → disable everything.
    global_disable = account_dd_pct > ACCOUNT_DD_TRIGGER_PCT
    if global_disable:
        for cid in cell_ids:
            if stages[cid] != 0:
                actions.append({
                    "cell_id": cid,
                    "new_stage": 0,
                    "reason": f"ACCOUNT_DD_GT_8_FROM_LOCK_{account_dd_pct*100:.1f}%",
                })

    for cid in cell_ids:
        m = metrics_for(by_cell.get(cid, []), generated_at, lock_nav)
        stage = stages[cid]
        verdict = "HOLD"
        reasons: list[str] = []

        if global_disable:
            verdict = "DISABLE"
            reasons.append(f"ACCOUNT_DD_GT_8_FROM_LOCK_{account_dd_pct*100:.1f}%")
        else:
            if m["n"] >= MIN_N and m["wr"] < 0.28:
                verdict = "DISABLE"
                reasons.append("WR_BELOW_28")
            if m["n"] >= MIN_N and m["ev_pips"] < -1.0:
                verdict = "DISABLE"
                reasons.append("EV_NEGATIVE")
            if m["pnl_jpy_today"] < DAILY_CELL_DISABLE_JPY:
                verdict = "DISABLE"
                reasons.append("DAILY_CELL_PNL_BELOW_-6822")
            if verdict != "DISABLE":
                if m["n"] >= MIN_N and m["profit_factor"] is not None and m["profit_factor"] < 1.0:
                    verdict = "DECREMENT"
                    reasons.append("PF_BELOW_1")
                if m["rolling_5d_dd_pct"] > ROLLING_5D_DD_TRIGGER_PCT:
                    verdict = "DECREMENT"
                    reasons.append("ROLLING_5D_DD_GT_5")
            if m["zero_fill_7d"]:
                reasons.append("ZERO_FILL_7D_ALERT_ONLY")

        if verdict == "DISABLE" and not global_disable:
            actions.append({
                "cell_id": cid,
                "new_stage": 0,
                "reason": reasons[0] if reasons else "DISABLE",
            })
        elif verdict == "DECREMENT":
            actions.append({
                "cell_id": cid,
                "new_stage": max(1, stage - 1),
                "reason": reasons[0] if reasons else "DECREMENT",
            })

        cells[cid] = {
            "stage": stage,
            "metrics": m,
            "verdict": verdict,
            "reasons": reasons,
        }

    return {
        "generated_at": ts,
        "lock_date": LOCK_DATE,
        "global": {
            "lock_nav_jpy": lock_nav,
            "current_nav_jpy": current_nav,
            "account_dd_pct_from_lock": account_dd_pct,
            "global_disable": global_disable,
            "watchdog_kv_global_disable": bool(state.get("global_disabled")),
        },
        "actions": actions,
        "cells": cells,
    }


def write_audit(payload: dict[str, Any]) -> Path | None:
    """Best-effort local audit write. Fails silently on read-only filesystems."""
    try:
        out_dir = PROJECT_ROOT / "knowledge-base" / "raw" / "audits" / "edge-cell-watchdog"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{date.today().isoformat()}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        return path
    except Exception:
        return None


def notify_discord(payload: dict[str, Any], applied: list[dict[str, Any]],
                   webhook: str | None) -> None:
    if not webhook:
        return
    changed = [a for a in applied if a.get("changed")]
    if not changed and not payload["global"].get("global_disable"):
        return
    lines = [f"Edge-cell watchdog @ {payload['generated_at']}:"]
    g = payload["global"]
    lines.append(
        f"NAV lock=¥{g.get('lock_nav_jpy',0):,.0f} current=¥{g.get('current_nav_jpy') or 0:,.0f} "
        f"DD={g.get('account_dd_pct_from_lock', 0)*100:.2f}%"
    )
    for a in changed[:15]:
        lines.append(
            f"{a['cell_id']}: S{a['old_stage']} -> S{a['new_stage']} ({a.get('reason','')})"
        )
    data = json.dumps({"content": "\n".join(lines)[:1900]}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "edge-cell-watchdog/2.0"},
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
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Explicit no-write mode (default)")
    parser.add_argument("--to-discord", action="store_true")
    args = parser.parse_args()

    apply = bool(args.apply)
    token = os.environ.get("EDGE_CELL_ADMIN_TOKEN", "")
    if not token:
        print("ERROR: EDGE_CELL_ADMIN_TOKEN env var not set", file=sys.stderr)
        return 2

    try:
        state = fetch_state(args.api, token)
    except Exception as exc:
        print(f"ERROR: state fetch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    cell_ids = [f"E{i}" for i in range(1, 13)]
    try:
        trades = fetch_trades(args.api, args.limit)
    except Exception as exc:
        print(f"ERROR: trades fetch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    payload = evaluate(trades, state, cell_ids=cell_ids)
    applied: list[dict[str, Any]] = []
    if apply and payload["actions"]:
        try:
            resp = post_state(args.api, token, payload["actions"])
            applied = resp.get("applied", []) or []
        except Exception as exc:
            print(f"ERROR: state post failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2

    payload["applied"] = applied
    audit_path = write_audit(payload)
    if audit_path is not None:
        payload["audit_path"] = str(audit_path.relative_to(PROJECT_ROOT))

    if args.to_discord and apply:
        notify_discord(payload, applied, os.environ.get("DISCORD_WEBHOOK_URL"))

    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
