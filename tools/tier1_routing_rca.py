#!/usr/bin/env python3
"""Tier 1 routing anomaly RCA from oanda_audit rows.

Read-only forensic script. The important invariant is that oanda_audit rows
must be split by bridge_status before grouping: 'sent' rows carry strategy
names, while 'filled' rows may carry OANDA mode labels such as PYR_BUY.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CUTOFF = datetime(2026, 4, 8, tzinfo=timezone.utc)
DEFAULT_OANDA_AUDIT_URL = "https://fx-ai-trader.onrender.com/api/oanda/audit?limit=100000"

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
SIGNAL_STATUSES = {"sent", "blocked", "skipped"}


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
    return text


def _as_rows(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        if isinstance(payload.get("audit"), list):
            rows = payload["audit"]
        elif isinstance(payload.get("rows"), list):
            rows = payload["rows"]
        elif isinstance(payload.get("trades"), list):
            rows = payload["trades"]
        else:
            raise ValueError("payload must contain audit, rows, or trades list")
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("payload must be a list or object")
    return [row for row in rows if isinstance(row, dict)]


def load_rows(path: str | Path) -> list[dict]:
    path = Path(path)
    if path.suffix in {".db", ".sqlite", ".sqlite3"}:
        return load_rows_from_sqlite(path)
    payload = json.loads(path.read_text())
    rows = _as_rows(payload)
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
        payload = json.loads(resp.read().decode("utf-8"))
    return _as_rows(payload)


def _empty_cell(strategy: str, instrument: str) -> dict:
    return {
        "strategy": strategy,
        "instrument": instrument,
        "signal_n": 0,
        "sent_n": 0,
        "filled_n": 0,
        "block_n": 0,
        "pass_through_rate": 0.0,
        "sent_to_fill_rate": 0.0,
        "block_reasons": Counter(),
        "periods": {
            "pre": {"signal_n": 0, "sent_n": 0, "filled_n": 0, "block_n": 0, "block_reasons": Counter()},
            "post": {"signal_n": 0, "sent_n": 0, "filled_n": 0, "block_n": 0, "block_reasons": Counter()},
            "unknown": {"signal_n": 0, "sent_n": 0, "filled_n": 0, "block_n": 0, "block_reasons": Counter()},
        },
        "top_block_reason": ("none", 0, 0.0),
    }


def analyze_audit_rows(rows: list[dict]) -> dict:
    sent_parent: dict[str, tuple[str, str]] = {}
    sent_parent_period: dict[str, str] = {}
    cells: dict[tuple[str, str], dict] = {
        cell: _empty_cell(*cell) for cell in TARGET_CELLS
    }
    status_counts = Counter()
    non_live_rows = 0

    for row in rows:
        status = _normalize_status(row)
        if not status:
            continue
        status_counts[status] += 1
        if row.get("is_live") is False:
            non_live_rows += 1
            continue
        if status == "sent":
            key = _cell_key(row)
            demo_trade_id = str(row.get("demo_trade_id") or "").strip()
            if demo_trade_id:
                sent_parent[demo_trade_id] = key
                sent_parent_period[demo_trade_id] = _period(row)

    for row in rows:
        status = _normalize_status(row)
        if not status:
            continue
        if row.get("is_live") is False:
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
        period_bucket = cell["periods"][period]
        if status in SIGNAL_STATUSES:
            cell["signal_n"] += 1
            period_bucket["signal_n"] += 1
        if status == "sent":
            cell["sent_n"] += 1
            period_bucket["sent_n"] += 1
        elif status == "filled":
            cell["filled_n"] += 1
            period_bucket["filled_n"] += 1
        elif status in BLOCK_STATUSES:
            reason = _normalize_reason(row.get("block_reason"))
            cell["block_n"] += 1
            cell["block_reasons"][reason] += 1
            period_bucket["block_n"] += 1
            period_bucket["block_reasons"][reason] += 1

    for cell in cells.values():
        if cell["signal_n"]:
            cell["pass_through_rate"] = cell["filled_n"] / cell["signal_n"]
        if cell["sent_n"]:
            cell["sent_to_fill_rate"] = cell["filled_n"] / cell["sent_n"]
        if cell["block_n"]:
            reason, n = cell["block_reasons"].most_common(1)[0]
            cell["top_block_reason"] = (reason, n, n / cell["block_n"])

    overall_reasons = Counter()
    for cell in cells.values():
        overall_reasons.update(cell["block_reasons"])
    if overall_reasons:
        reason, n = overall_reasons.most_common(1)[0]
        top_overall = (reason, n, n / sum(overall_reasons.values()))
    else:
        top_overall = ("none", 0, 0.0)

    return {
        "cells": cells,
        "status_counts": status_counts,
        "non_live_rows": non_live_rows,
        "top_overall_block_reason": top_overall,
    }


def _fmt_pct(value: float) -> str:
    if math.isnan(value):
        return "n/a"
    return f"{value * 100:.2f}%"


def _top_reason_text(counter: Counter, total: int) -> str:
    if total <= 0 or not counter:
        return "none (0 / 0, 0.00%)"
    reason, n = counter.most_common(1)[0]
    return f"{reason} ({n} / {total}, {_fmt_pct(n / total)})"


def _top_reasons_table(counter: Counter, total: int) -> list[str]:
    lines = [
        "| reason | N | share |",
        "|---|---:|---:|",
    ]
    if total <= 0 or not counter:
        lines.append("| none | 0 | 0.00% |")
        return lines
    for reason, n in counter.most_common(10):
        lines.append(f"| {reason} | {n} | {_fmt_pct(n / total)} |")
    return lines


def _verdict(result: dict) -> tuple[str, list[str]]:
    top_reason, top_n, top_share = result["top_overall_block_reason"]
    total_signal = sum(cell["signal_n"] for cell in result["cells"].values())
    total_block = sum(cell["block_n"] for cell in result["cells"].values())
    total_sent = sum(cell["sent_n"] for cell in result["cells"].values())
    reasons = []
    if total_signal == 0 and total_sent == 0:
        return "REJECT", ["対象 cell の oanda_audit signal/sent 行が0で、signal 生成前提が崩れている。"]
    if total_block == 0:
        return "NEEDS_MORE_EVIDENCE", ["対象 cell の blocked/skipped 行が0で、gate別 block 比率を特定できない。"]
    reasons.append(f"Top block reason={top_reason} ({top_n}/{total_block}, {_fmt_pct(top_share)})")
    if top_share >= 0.60:
        return "ACCEPT", reasons
    if top_share < 0.30:
        reasons.append("Top reason share <30% で分散。hour/session dimension が必要。")
        return "NEEDS_MORE_EVIDENCE", reasons
    reasons.append("Top reason は30%以上だが60%未満で、単一支配 gate とは言えない。")
    return "NEEDS_MORE_EVIDENCE", reasons


def render_report(result: dict, *, source: str) -> str:
    cells = result["cells"]
    verdict, reasons = _verdict(result)
    total_signal = sum(cell["signal_n"] for cell in cells.values())
    total_sent = sum(cell["sent_n"] for cell in cells.values())
    total_filled = sum(cell["filled_n"] for cell in cells.values())
    total_block = sum(cell["block_n"] for cell in cells.values())
    pass_rate = total_filled / total_signal if total_signal else 0.0
    sent_fill_rate = total_filled / total_sent if total_sent else 0.0
    overall_reasons = Counter()
    for cell in cells.values():
        overall_reasons.update(cell["block_reasons"])
    top_reason, top_n, top_share = result["top_overall_block_reason"]

    lines = [
        "# Tier 1 LIVE routing anomaly RCA - 2026-05-04",
        "",
        f"Verdict: {verdict}",
        f"Top block reason: {top_reason} ({top_n} / {total_block}, {_fmt_pct(top_share)})",
        f"Pass-through rate: {total_filled} / {total_signal} = {_fmt_pct(pass_rate)}",
        f"Sent-to-fill rate: {total_filled} / {total_sent} = {_fmt_pct(sent_fill_rate)}",
        "",
        "## Source / separation",
        "",
        f"- Source: `{source}`",
        "- `bridge_status='sent'` は strategy 名、`bridge_status='filled'` は OANDA mode 名の可能性があるため、GROUP BY 前に分離。",
        "- `filled` は同一 `demo_trade_id` の `sent` 親 row へ解決してから cell に帰属。",
        "- `blocked/skipped` の `block_reason` は gate 分布用。Shadow/非live row (`is_live=false`) は除外。",
        f"- Status counts: {dict(sorted(result['status_counts'].items()))}",
        f"- Excluded non-live audit rows: {result['non_live_rows']}",
        "",
        "## Cell pass-through",
        "",
        "| Cell | signal N | sent N | filled N | blocked/skipped N | pass-through | sent-fill | top block reason |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for strategy, instrument in TARGET_CELLS:
        cell = cells[(strategy, instrument)]
        lines.append(
            f"| {strategy} / {instrument} | {cell['signal_n']} | {cell['sent_n']} | "
            f"{cell['filled_n']} | {cell['block_n']} | {_fmt_pct(cell['pass_through_rate'])} | "
            f"{_fmt_pct(cell['sent_to_fill_rate'])} | {_top_reason_text(cell['block_reasons'], cell['block_n'])} |"
        )

    lines += [
        "",
        "## Pre/post-cutoff comparison",
        "",
        "| Cell | period | signal N | sent N | filled N | blocked/skipped N | pass-through | top block reason |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for strategy, instrument in TARGET_CELLS:
        cell = cells[(strategy, instrument)]
        for period in ("pre", "post", "unknown"):
            bucket = cell["periods"][period]
            if not any(bucket[key] for key in ("signal_n", "sent_n", "filled_n", "block_n")):
                continue
            rate = bucket["filled_n"] / bucket["signal_n"] if bucket["signal_n"] else 0.0
            lines.append(
                f"| {strategy} / {instrument} | {period} | {bucket['signal_n']} | {bucket['sent_n']} | "
                f"{bucket['filled_n']} | {bucket['block_n']} | {_fmt_pct(rate)} | "
                f"{_top_reason_text(bucket['block_reasons'], bucket['block_n'])} |"
            )

    lines += [
        "",
        "## Gate block distribution",
        "",
        *_top_reasons_table(overall_reasons, total_block),
        "",
        "## Hypothesis verdicts",
        "",
        f"- H1: {'ACCEPT' if verdict == 'ACCEPT' else 'NEEDS_MORE_EVIDENCE'} - {'; '.join(reasons)}",
        "- H2: pre/post table above. 判定は top reason と share の期間差を参照。",
        f"- H3: {'REJECT' if total_signal else 'ACCEPT'} - 対象 cell の signal-path rows N={total_signal}。",
        "",
        "## Recommended fix",
        "",
    ]
    if verdict == "ACCEPT":
        lines.append(f"- R3 patch candidate: `{top_reason}` gate を対象 cell 限定で再評価。緩和/除外/時間帯制限の実装は別 task。")
    elif total_signal == 0:
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
        "ELITE_LIVE_CELLS:",
    ]
    lines += [f"  - {strategy} / {instrument}" for strategy, instrument in ELITE_LIVE_CELLS]
    lines.append("PAIR_PROMOTED_REFERENCE:")
    lines += [f"  - {strategy} / {instrument}" for strategy, instrument in PAIR_PROMOTED_REFERENCE]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", help="JSON containing oanda_audit rows; /api/demo/trades alone is insufficient")
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

    source = args.trades
    try:
        rows = load_rows(args.trades)
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError, sqlite3.Error, ValueError) as exc:
        if "bridge_status" not in str(exc):
            print(f"input error: {exc}", file=sys.stderr)
            return 2
        try:
            rows = fetch_oanda_audit(args.audit_url)
            source = args.audit_url
            print(f"input lacked bridge_status; fetched oanda_audit from {args.audit_url}", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as fetch_exc:
            print(f"input error: {exc}", file=sys.stderr)
            print(f"oanda_audit fetch failed: {fetch_exc}", file=sys.stderr)
            return 2

    result = analyze_audit_rows(rows)
    report = render_report(result, source=source)
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
