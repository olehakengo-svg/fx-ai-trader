#!/usr/bin/env python3
"""Stage-3 edge-cell LIVE watchdog.

Dry-run by default. Render cron runs with --apply --to-discord.
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
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_API = os.environ.get("API_BASE", "https://fx-ai-trader.onrender.com")
DEFAULT_DB = Path(os.environ.get("DB_PATH", PROJECT_ROOT / "demo_trades.db"))
DEFAULT_LIMIT = 10000
LOCK_DATE = "2026-05-26"
MIN_N = 10
ACCOUNT_EQUITY_JPY = 454_816.0
DAILY_CELL_DISABLE_JPY = -6_822.0

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


def fetch_json(url: str, user_agent: str) -> Any:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"refusing invalid URL: {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
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
        "edge-cell-watchdog/1.0",
    )
    if isinstance(payload, dict):
        return payload.get("trades", []) or []
    if isinstance(payload, list):
        return payload
    return []


def fetch_risk_dashboard(api: str) -> dict[str, Any]:
    try:
        payload = fetch_json(
            f"{api.rstrip('/')}/api/risk/dashboard",
            "edge-cell-watchdog/1.0",
        )
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


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


def metrics_for(trades: list[dict[str, Any]], generated_at: datetime) -> dict[str, Any]:
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
    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "wr": (len(wins) / n) if n else 0.0,
        "ev_pips": (sum(pnls) / n) if n else 0.0,
        "profit_factor": pf,
        "pnl_pips_sum": sum(pnls),
        "pnl_jpy_today": today_jpy,
        "rolling_5d_dd_jpy": max_drawdown(pnl_jpy_5d),
        "rolling_5d_dd_pct": max_drawdown(pnl_jpy_5d) / ACCOUNT_EQUITY_JPY,
        "zero_fill_7d": len(active_dates) == 0,
    }


def kv_get(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM system_kv WHERE key=?", (key,)).fetchone()
    return str(row[0]) if row else default


def kv_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO system_kv (key, value) VALUES (?, ?)", (key, value))


def ensure_kv(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS system_kv (key TEXT PRIMARY KEY, value TEXT DEFAULT '')"
    )


def _stage_for(conn: sqlite3.Connection, cell_id: str) -> int:
    try:
        return int(kv_get(conn, f"edge_cell_stage:{cell_id}", "1"))
    except ValueError:
        return 1


def _set_stage(conn: sqlite3.Connection, cell_id: str, stage: int, reason: str, ts: str) -> bool:
    old = _stage_for(conn, cell_id)
    if old == stage and kv_get(conn, f"edge_cell_disabled_reason:{cell_id}", "") == reason:
        return False
    kv_set(conn, f"edge_cell_stage:{cell_id}", str(stage))
    kv_set(conn, f"edge_cell_stage_changed_at:{cell_id}", ts)
    if reason:
        kv_set(conn, f"edge_cell_disabled_reason:{cell_id}", reason)
    return True


def decrement_stage(conn: sqlite3.Connection, cell_id: str, reason: str, ts: str) -> dict[str, Any]:
    old = _stage_for(conn, cell_id)
    new = max(1, old - 1)
    changed = _set_stage(conn, cell_id, new, reason, ts)
    return {"cell_id": cell_id, "action": "DECREMENT", "old_stage": old, "new_stage": new, "reason": reason, "changed": changed}


def disable_cell(conn: sqlite3.Connection, cell_id: str, reason: str, ts: str) -> dict[str, Any]:
    old = _stage_for(conn, cell_id)
    changed = _set_stage(conn, cell_id, 0, reason, ts)
    return {"cell_id": cell_id, "action": "DISABLE", "old_stage": old, "new_stage": 0, "reason": reason, "changed": changed}


def disable_all_cells(conn: sqlite3.Connection, reason: str, ts: str, cell_ids: list[str]) -> list[dict[str, Any]]:
    return [disable_cell(conn, cell_id, reason, ts) for cell_id in cell_ids]


def _risk_30d_dd_pct(risk: dict[str, Any]) -> float:
    for key in ("dd_30d_pct", "drawdown_30d_pct", "account_dd_30d_pct", "max_dd_30d_pct"):
        if risk.get(key) is not None:
            try:
                value = float(risk[key])
                return value / 100.0 if value > 1 else value
            except (TypeError, ValueError):
                pass
    return 0.0


def evaluate(
    trades: list[dict[str, Any]],
    risk: dict[str, Any],
    conn: sqlite3.Connection,
    *,
    apply: bool,
) -> dict[str, Any]:
    generated_at = _now()
    ts = generated_at.isoformat()
    ensure_kv(conn)
    from modules.edge_cell_promote import EDGE_CELLS

    cell_ids = [cell.cell_id for cell in EDGE_CELLS]
    by_cell = live_edge_trades(trades)
    cells: dict[str, Any] = {}
    actions: list[dict[str, Any]] = []

    if _risk_30d_dd_pct(risk) > 0.08:
        if apply:
            actions.extend(disable_all_cells(conn, "ACCOUNT_30D_DD_GT_8", ts, cell_ids))
        else:
            actions.extend({
                "cell_id": cell_id,
                "action": "DISABLE",
                "old_stage": _stage_for(conn, cell_id),
                "new_stage": 0,
                "reason": "ACCOUNT_30D_DD_GT_8",
                "changed": True,
            } for cell_id in cell_ids)

    for cell_id in cell_ids:
        m = metrics_for(by_cell.get(cell_id, []), generated_at)
        stage = _stage_for(conn, cell_id)
        verdict = "HOLD"
        reasons: list[str] = []

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
            if m["rolling_5d_dd_pct"] > 0.05:
                verdict = "DECREMENT"
                reasons.append("ROLLING_5D_DD_GT_5")
        if m["zero_fill_7d"]:
            reasons.append("ZERO_FILL_7D_ALERT_ONLY")

        action = None
        reason = reasons[0] if reasons else ""
        if verdict == "DISABLE":
            action = disable_cell(conn, cell_id, reason, ts) if apply else {
                "cell_id": cell_id, "action": "DISABLE", "old_stage": stage,
                "new_stage": 0, "reason": reason, "changed": stage != 0,
            }
            actions.append(action)
        elif verdict == "DECREMENT":
            action = decrement_stage(conn, cell_id, reason, ts) if apply else {
                "cell_id": cell_id, "action": "DECREMENT", "old_stage": stage,
                "new_stage": max(1, stage - 1), "reason": reason,
                "changed": stage > 1,
            }
            actions.append(action)

        cells[cell_id] = {
            "stage": stage,
            "metrics": m,
            "verdict": verdict,
            "reasons": reasons,
        }

    if apply:
        conn.commit()
    return {
        "generated_at": ts,
        "lock_date": LOCK_DATE,
        "dry_run": not apply,
        "global": {
            "account_30d_dd_pct": _risk_30d_dd_pct(risk),
        },
        "actions": actions,
        "state_changes": [a for a in actions if a.get("changed")],
        "cells": cells,
    }


def write_audit(payload: dict[str, Any]) -> Path:
    out_dir = PROJECT_ROOT / "knowledge-base" / "raw" / "audits" / "edge-cell-watchdog"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{date.today().isoformat()}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def notify_discord(payload: dict[str, Any], webhook: str | None) -> None:
    if not webhook or not payload.get("state_changes"):
        return
    lines = ["Edge-cell watchdog state changes:"]
    for action in payload["state_changes"]:
        lines.append(
            f"{action['cell_id']}: {action['action']} "
            f"S{action['old_stage']} -> S{action['new_stage']} ({action['reason']})"
        )
    data = json.dumps({"content": "\n".join(lines)[:1900]}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "edge-cell-watchdog/1.0"},
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
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Explicit no-write mode (default)")
    parser.add_argument("--to-discord", action="store_true")
    args = parser.parse_args()

    apply = bool(args.apply)
    try:
        trades = fetch_trades(args.api, args.limit)
        risk = fetch_risk_dashboard(args.api)
    except Exception as exc:
        print(f"ERROR: API fetch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(str(args.db) if apply else ":memory:")
    try:
        payload = evaluate(trades, risk, conn, apply=apply)
    finally:
        conn.close()
    audit_path = write_audit(payload)
    payload["audit_path"] = str(audit_path.relative_to(PROJECT_ROOT))
    if args.to_discord and apply:
        notify_discord(payload, os.environ.get("DISCORD_WEBHOOK_URL"))
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
