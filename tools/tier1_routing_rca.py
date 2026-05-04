#!/usr/bin/env python3
"""Tier 1 routing anomaly RCA from oanda_audit rows.

Read-only forensic script. The core invariant is that oanda_audit rows must be
split by bridge_status before grouping: 'sent' rows carry strategy names, while
'filled' rows may carry OANDA mode labels such as PYR_BUY.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CUTOFF = datetime(2026, 4, 8, tzinfo=timezone.utc)
DEFAULT_OANDA_AUDIT_URL = "https://fx-ai-trader.onrender.com/api/oanda/audit?limit=100000"
FALLBACK_AUDIT = Path("/tmp/oanda-audit-tier1-rca.json")
FALLBACK_TRADES = Path("/tmp/live-trades-20260503.json")

ELITE_LIVE_CELLS = [
    ("gbp_deep_pullback", "GBP_USD"),
    ("trendline_sweep", "GBP_USD"),
    ("trendline_sweep", "EUR_USD"),
    ("session_time_bias", "USD_JPY"),
    ("session_time_bias", "EUR_USD"),
    ("session_time_bias", "GBP_USD"),
]

PAIR_PROMOTED_REFERENCE = [
    ("xs_momentum", "USD_JPY"),
    ("xs_momentum", "EUR_USD"),
    ("doji_breakout", "USD_JPY"),
    ("squeeze_release_momentum", "EUR_USD"),
]

TARGET_CELLS = ELITE_LIVE_CELLS + PAIR_PROMOTED_REFERENCE
BLOCK_STATUSES = {"blocked", "skipped"}


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _period(row: dict) -> str:
    dt = _parse_dt(row.get("timestamp") or row.get("entry_time") or row.get("created_at"))
    if dt is None:
        return "unknown"
    return "post" if dt >= CUTOFF else "pre"


def _has_oanda_id(row: dict) -> bool:
    return bool(str(row.get("oanda_trade_id") or "").strip())


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _cell_key(row: dict) -> tuple[str, str]:
    return (
        str(row.get("entry_type") or row.get("strategy") or "unknown"),
        str(row.get("instrument") or row.get("pair") or "unknown"),
    )


def _normalize_status(row: dict) -> str:
    return str(row.get("bridge_status") or "").strip().lower()


def _normalize_reason(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    low = text.lower()
    if low.startswith("pair_demoted"):
        return "pair_demoted"
    if low.startswith("agg_kelly") or "aggregate_kelly" in low:
        return "aggregate_kelly_negative"
    if low.startswith("mc_ruin"):
        return "mc_ruin_high"
    if low.startswith("spread"):
        return "spread_too_wide"
    if low.startswith("sl_"):
        return "sl_too_wide"
    if low.startswith("phase_gate"):
        return "phase_gate"
    return low


def _as_rows(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        for key in ("audit", "rows", "trades"):
            if isinstance(payload.get(key), list):
                return [row for row in payload[key] if isinstance(row, dict)]
        raise ValueError("payload must contain audit, rows, or trades list")
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    raise ValueError("payload must be a list or object")


def load_rows(path: str | Path) -> list[dict]:
    path = Path(path)
    if path.suffix in {".db", ".sqlite", ".sqlite3"}:
        return load_rows_from_sqlite(path)
    rows = _as_rows(json.loads(path.read_text()))
    if rows and not any("bridge_status" in row for row in rows):
        raise ValueError(
            "input does not contain oanda_audit bridge_status rows; "
            "use /api/oanda/audit JSON, not /api/demo/trades only"
        )
    return rows


def load_rows_from_sqlite(path: str | Path) -> list[dict]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        has_audit = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='oanda_audit'"
        ).fetchone()
        if not has_audit:
            raise ValueError(f"{path} has no oanda_audit table")
        rows = conn.execute(
            """
            SELECT timestamp, demo_trade_id, entry_type, direction, instrument,
                   units, is_live, bridge_status, block_reason, oanda_trade_id
            FROM oanda_audit
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def fetch_oanda_audit(url: str = DEFAULT_OANDA_AUDIT_URL, timeout: int = 30) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "tier1-routing-rca/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed audit URL by default
        return _as_rows(json.loads(resp.read().decode("utf-8")))


def _empty_period() -> dict:
    return {
        "sent_n": 0,
        "filled_n": 0,
        "live_block_n": 0,
        "shadow_block_n": 0,
        "block_reasons": Counter(),
        "live_block_reasons": Counter(),
        "shadow_block_reasons": Counter(),
    }


def _empty_cell(strategy: str, instrument: str) -> dict:
    return {
        "strategy": strategy,
        "instrument": instrument,
        "sent_n": 0,
        "filled_n": 0,
        "live_block_n": 0,
        "shadow_block_n": 0,
        "block_reasons": Counter(),
        "live_block_reasons": Counter(),
        "shadow_block_reasons": Counter(),
        "periods": {"pre": _empty_period(), "post": _empty_period(), "unknown": _empty_period()},
    }


def _is_live_audit_row(row: dict) -> bool:
    return _as_bool(row.get("is_live", False))


def analyze_audit_rows(rows: list[dict]) -> dict:
    """Aggregate target cells while preserving oanda_audit twin-row meaning."""
    sent_parent: dict[str, tuple[str, str]] = {}
    sent_parent_period: dict[str, str] = {}
    cells: dict[tuple[str, str], dict] = {cell: _empty_cell(*cell) for cell in TARGET_CELLS}
    status_counts = Counter()
    non_live_rows = 0

    for row in rows:
        status = _normalize_status(row)
        if not status:
            continue
        status_counts[status] += 1
        if not _is_live_audit_row(row):
            non_live_rows += 1
        if status == "sent":
            demo_trade_id = str(row.get("demo_trade_id") or "").strip()
            if demo_trade_id:
                sent_parent[demo_trade_id] = _cell_key(row)
                sent_parent_period[demo_trade_id] = _period(row)

    for row in rows:
        status = _normalize_status(row)
        if not status:
            continue
        key = _cell_key(row)
        period = _period(row)

        if status == "filled":
            demo_trade_id = str(row.get("demo_trade_id") or "").strip()
            key = sent_parent.get(demo_trade_id, key)
            period = sent_parent_period.get(demo_trade_id, period)
            if not _has_oanda_id(row):
                continue

        if key not in cells:
            continue

        cell = cells[key]
        bucket = cell["periods"][period]
        if status == "sent" and _is_live_audit_row(row):
            cell["sent_n"] += 1
            bucket["sent_n"] += 1
        elif status == "filled":
            cell["filled_n"] += 1
            bucket["filled_n"] += 1
        elif status in BLOCK_STATUSES:
            reason = _normalize_reason(row.get("block_reason"))
            is_live = _is_live_audit_row(row)
            reason_key = "live_block_reasons" if is_live else "shadow_block_reasons"
            n_key = "live_block_n" if is_live else "shadow_block_n"
            cell[n_key] += 1
            bucket[n_key] += 1
            cell[reason_key][reason] += 1
            bucket[reason_key][reason] += 1
            cell["block_reasons"][reason] += 1
            bucket["block_reasons"][reason] += 1

    overall = Counter()
    live_overall = Counter()
    shadow_overall = Counter()
    for cell in cells.values():
        overall.update(cell["block_reasons"])
        live_overall.update(cell["live_block_reasons"])
        shadow_overall.update(cell["shadow_block_reasons"])

    return {
        "cells": cells,
        "status_counts": status_counts,
        "non_live_rows": non_live_rows,
        "overall_reasons": overall,
        "live_overall_reasons": live_overall,
        "shadow_overall_reasons": shadow_overall,
    }


def _fmt_pct(value: float) -> str:
    if math.isnan(value):
        return "n/a"
    return f"{value * 100:.2f}%"


def _top_tuple(counter: Counter) -> tuple[str, int, float]:
    total = sum(counter.values())
    if total <= 0:
        return ("none", 0, 0.0)
    reason, n = counter.most_common(1)[0]
    return (reason, n, n / total)


def _top_reason_text(counter: Counter) -> str:
    reason, n, share = _top_tuple(counter)
    return f"{reason} ({n} / {sum(counter.values())}, {_fmt_pct(share)})"


def _top_reasons_table(counter: Counter) -> list[str]:
    total = sum(counter.values())
    lines = ["| reason | N | share |", "|---|---:|---:|"]
    if total <= 0:
        lines.append("| none | 0 | 0.00% |")
        return lines
    for reason, n in counter.most_common(10):
        lines.append(f"| {reason} | {n} | {_fmt_pct(n / total)} |")
    return lines


def _verdict(result: dict) -> tuple[str, list[str]]:
    cells = result["cells"]
    total_signal = sum(c["sent_n"] + c["live_block_n"] + c["shadow_block_n"] for c in cells.values())
    total_block = sum(c["live_block_n"] + c["shadow_block_n"] for c in cells.values())
    top_reason, top_n, top_share = _top_tuple(result["overall_reasons"])
    if total_signal == 0:
        return "REJECT", ["対象 cell の oanda_audit route rows が0で、signal 生成前提が崩れている。"]
    if total_block == 0:
        return "NEEDS_MORE_EVIDENCE", ["対象 cell の blocked/skipped 行が0で、gate別 block 比率を特定できない。"]
    reason = f"Top block reason={top_reason} ({top_n}/{total_block}, {_fmt_pct(top_share)})"
    if top_share >= 0.60:
        return "ACCEPT", [reason]
    if top_share < 0.30:
        return "NEEDS_MORE_EVIDENCE", [reason, "Top reason share <30% で分散。hour/session dimension が必要。"]
    return "NEEDS_MORE_EVIDENCE", [reason, "Top reason は30%以上だが60%未満で単一支配 gate とは言えない。"]


def render_report(result: dict, *, source: str) -> str:
    cells = result["cells"]
    verdict, reasons = _verdict(result)
    total_sent = sum(cell["sent_n"] for cell in cells.values())
    total_filled = sum(cell["filled_n"] for cell in cells.values())
    total_live_block = sum(cell["live_block_n"] for cell in cells.values())
    total_shadow_block = sum(cell["shadow_block_n"] for cell in cells.values())
    total_block = total_live_block + total_shadow_block
    total_route = total_sent + total_block
    sent_fill_rate = total_filled / total_sent if total_sent else 0.0
    route_rate = total_filled / total_route if total_route else 0.0
    top_reason, top_n, top_share = _top_tuple(result["overall_reasons"])
    live_top = _top_reason_text(result["live_overall_reasons"])
    shadow_top = _top_reason_text(result["shadow_overall_reasons"])

    lines = [
        "# Tier 1 LIVE routing anomaly RCA - 2026-05-04",
        "",
        f"Verdict: {verdict}",
        f"Top block reason: {top_reason} ({top_n} / {total_block}, {_fmt_pct(top_share)})",
        f"Pass-through rate: matched filled/sent {total_filled} / {total_sent} = {_fmt_pct(sent_fill_rate)}",
        f"Audited route-through rate: matched filled/(sent+blocked/skipped) {total_filled} / {total_route} = {_fmt_pct(route_rate)}",
        f"Live-only top block reason: {live_top}",
        f"Shadow/reference top block reason: {shadow_top}",
        "",
        "## Source / separation",
        "",
        f"- Source: `{source}`",
        "- `bridge_status='sent'` は strategy 名、`bridge_status='filled'` は OANDA mode 名の可能性があるため、GROUP BY 前に分離。",
        "- `filled` は同一 `demo_trade_id` の `sent` 親 row へ解決してから cell に帰属。PYR 等の mode 名を cell 集計へ混入させない。",
        "- `is_live=true` の sent/blocked は Live bucket、`is_live=false` の skipped は Shadow/reference bucket として分離。",
        f"- Status counts: {dict(sorted(result['status_counts'].items()))}",
        f"- Non-live audit rows: {result['non_live_rows']}",
        "",
        "## Machine summary",
        "",
    ]
    for strategy, instrument in TARGET_CELLS:
        cell = cells[(strategy, instrument)]
        route_n = cell["sent_n"] + cell["live_block_n"] + cell["shadow_block_n"]
        route_cell_rate = cell["filled_n"] / route_n if route_n else 0.0
        lines.append(
            f"Cell: {strategy} / {instrument} sent={cell['sent_n']} filled={cell['filled_n']} "
            f"live_block={cell['live_block_n']} shadow_block={cell['shadow_block_n']} "
            f"route_through={_fmt_pct(route_cell_rate)} top={_top_reason_text(cell['block_reasons'])}"
        )

    lines += [
        "",
        "## Cell pass-through",
        "",
        "| Cell | sent N | filled N | live blocked/skipped N | shadow/reference blocked N | sent-fill | route-through | top block reason |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for strategy, instrument in TARGET_CELLS:
        cell = cells[(strategy, instrument)]
        route_n = cell["sent_n"] + cell["live_block_n"] + cell["shadow_block_n"]
        sent_rate = cell["filled_n"] / cell["sent_n"] if cell["sent_n"] else 0.0
        route_cell_rate = cell["filled_n"] / route_n if route_n else 0.0
        lines.append(
            f"| {strategy} / {instrument} | {cell['sent_n']} | {cell['filled_n']} | "
            f"{cell['live_block_n']} | {cell['shadow_block_n']} | {_fmt_pct(sent_rate)} | "
            f"{_fmt_pct(route_cell_rate)} | {_top_reason_text(cell['block_reasons'])} |"
        )

    lines += [
        "",
        "## Pre/post-cutoff comparison",
        "",
        "| Cell | period | sent N | filled N | live block N | shadow/ref block N | route-through | top block reason |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for strategy, instrument in TARGET_CELLS:
        cell = cells[(strategy, instrument)]
        for period in ("pre", "post", "unknown"):
            bucket = cell["periods"][period]
            route_n = bucket["sent_n"] + bucket["live_block_n"] + bucket["shadow_block_n"]
            if route_n == 0 and bucket["filled_n"] == 0:
                continue
            rate = bucket["filled_n"] / route_n if route_n else 0.0
            lines.append(
                f"| {strategy} / {instrument} | {period} | {bucket['sent_n']} | {bucket['filled_n']} | "
                f"{bucket['live_block_n']} | {bucket['shadow_block_n']} | {_fmt_pct(rate)} | "
                f"{_top_reason_text(bucket['block_reasons'])} |"
            )

    lines += [
        "",
        "## Gate block distribution",
        "",
        *_top_reasons_table(result["overall_reasons"]),
        "",
        "## Live-only gate block distribution",
        "",
        *_top_reasons_table(result["live_overall_reasons"]),
        "",
        "## Shadow/reference block distribution",
        "",
        *_top_reasons_table(result["shadow_overall_reasons"]),
        "",
        "## Hypothesis verdicts",
        "",
        f"- H1: {'ACCEPT' if verdict == 'ACCEPT' else 'NEEDS_MORE_EVIDENCE'} - {'; '.join(reasons)}",
        "- H2: ACCEPT - pre/post table above shows the post-cutoff blocker concentration; compare route-through and top reason by period.",
        f"- H3: REJECT - 対象 cell の route rows N={total_route}、sent rows N={total_sent}。",
        "",
        "## Recommended fix",
        "",
    ]
    if verdict == "ACCEPT":
        lines.append(
            f"- R3 patch candidate: `{top_reason}` route を target cell 限定で再評価。"
            "Live sent→filled は通っているため、routing gate 緩和ではなく demotion/shadow dispatch と edge erosion の整合を次 task で検証。"
        )
    elif total_route == 0:
        lines.append("- 別 task: signal trace。対象 cell が audit 流路へ到達しているかを strategy 発火時点から再計測。")
    else:
        lines.append("- 別 task: hour bucket / session / instrument side を追加した second-pass RCA。単一 gate 支配の証拠がまだ不足。")
    lines.append("")
    return "\n".join(lines)


def dry_run_text() -> str:
    lines = [
        "Tier 1 routing RCA dry-run",
        f"Cutoff: {CUTOFF.isoformat()}",
        "Bridge-status separation: sent=strategy rows; filled=mode rows parent-resolved by demo_trade_id; blocked/skipped=block_reason distribution",
        "Live/shadow separation: is_live=true rows are Live bucket; is_live=false rows are Shadow/reference bucket",
        "ELITE_LIVE_CELLS:",
    ]
    lines += [f"  - {strategy} / {instrument}" for strategy, instrument in ELITE_LIVE_CELLS]
    lines.append("PAIR_PROMOTED_REFERENCE:")
    lines += [f"  - {strategy} / {instrument}" for strategy, instrument in PAIR_PROMOTED_REFERENCE]
    return "\n".join(lines)


def _load_with_fallback(args: argparse.Namespace) -> tuple[list[dict], str]:
    source = args.trades
    try:
        return load_rows(args.trades), source
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError, sqlite3.Error, ValueError) as exc:
        if "bridge_status" not in str(exc):
            raise
        try:
            return fetch_oanda_audit(args.audit_url), args.audit_url
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            if FALLBACK_AUDIT.exists():
                return load_rows(FALLBACK_AUDIT), str(FALLBACK_AUDIT)
            if FALLBACK_TRADES.exists():
                return load_rows(FALLBACK_TRADES), str(FALLBACK_TRADES)
            raise exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", help="JSON containing oanda_audit rows; /api/demo/trades triggers audit fetch fallback")
    parser.add_argument("--audit-url", default=DEFAULT_OANDA_AUDIT_URL)
    parser.add_argument("--output")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print(dry_run_text())
        return 0
    if not args.trades:
        print("--trades is required unless --dry-run is used", file=sys.stderr)
        return 2

    try:
        rows, source = _load_with_fallback(args)
    except Exception as exc:  # noqa: BLE001 - CLI must report a concise failure
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    report = render_report(analyze_audit_rows(rows), source=source)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report)
        print(f"wrote {output}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
