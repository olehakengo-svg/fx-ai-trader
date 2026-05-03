#!/usr/bin/env python3
"""H1 hour-bucket 3-month counterfactual analyzer.

Primary source is Render production `/api/demo/trades`.
If production fetch fails, this tool still writes a reviewable markdown report
that records the blocking error and the exact fetch parameters.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.demo_trader import DemoTrader
from research.edge_discovery.production_fetcher import (
    ProductionFetchError,
    fetch_closed_trades,
)


DATE_FROM = "2026-02-01"
DATE_TO = "2026-05-01"
IS_END = "2026-04-01"
OUTPUT_DEFAULT = (
    "knowledge-base/wiki/learning/"
    "h1-hour-bucket-counterfactual-3month-2026-05-03.md"
)
EXPLICIT_GRANDFATHER = frozenset({"bb_rsi_reversion"})
HOUR_CELL_N_MIN = 30
HOUR_WILSON_MIN = 0.40
FALSE_DEMOTION_MAX = 0.20
BUCKETS = (
    ("Asia", 0, 6),
    ("London", 7, 12),
    ("NY-overlap", 13, 16),
    ("Off", 17, 23),
)


@dataclass(frozen=True)
class CellKey:
    entry_type: str
    instrument: str
    hour_bucket: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date-from", default=DATE_FROM)
    parser.add_argument("--date-to", default=DATE_TO)
    parser.add_argument("--is-end", default=IS_END)
    parser.add_argument("--limit", type=int, default=10000)
    parser.add_argument("--input-json", default=None)
    parser.add_argument("--output", default=OUTPUT_DEFAULT)
    parser.add_argument("--output-json", default=None)
    return parser.parse_args()


def hour_bucket_from_ts(value) -> str | None:
    dt = parse_ts(value)
    if dt is None:
        return None
    hour = dt.astimezone(timezone.utc).hour
    for label, start, end in BUCKETS:
        if start <= hour <= end:
            return label
    return None


def parse_ts(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_closed_outcome(row: dict) -> bool:
    return (row.get("outcome") or "").upper() in {"WIN", "LOSS"}


def strict_live_trade(row: dict) -> bool:
    trade_id = str(row.get("oanda_trade_id") or "").strip()
    return (
        is_closed_outcome(row)
        and int(row.get("is_shadow") or 0) == 0
        and bool(trade_id)
    )


def strict_shadow_trade(row: dict) -> bool:
    instrument = str(row.get("instrument") or "")
    return (
        is_closed_outcome(row)
        and int(row.get("is_shadow") or 0) == 1
        and "XAU" not in instrument
    )


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1.0 + (z * z) / n
    centre = p + (z * z) / (2.0 * n)
    spread = z * math.sqrt(p * (1.0 - p) / n + (z * z) / (4.0 * n * n))
    return max(0.0, (centre - spread) / den)


def ev_ci_lower(pnls: list[float], z: float = 1.959963984540054) -> float:
    n = len(pnls)
    if n <= 0:
        return 0.0
    mean = sum(pnls) / n
    if n == 1:
        return mean
    variance = sum((x - mean) ** 2 for x in pnls) / (n - 1)
    se = math.sqrt(variance / n)
    return mean - z * se


def binomial_two_sided_pvalue(wins: int, n: int, p0: float = 0.5) -> float:
    if n <= 0:
        return 1.0
    mean = n * p0
    var = n * p0 * (1.0 - p0)
    if var <= 0:
        return 1.0
    z = (wins - mean) / math.sqrt(var)
    p = 2.0 * (1.0 - NormalDist().cdf(abs(z)))
    return max(0.0, min(1.0, p))


def profit_factor(pnls: Iterable[float]) -> float | None:
    gp = sum(x for x in pnls if x > 0)
    gl = abs(sum(x for x in pnls if x < 0))
    if gl == 0:
        return None if gp == 0 else math.inf
    return gp / gl


def kelly_fraction(pnls: list[float]) -> float | None:
    wins = [x for x in pnls if x > 0]
    losses = [abs(x) for x in pnls if x < 0]
    n = len(pnls)
    if n == 0 or not wins or not losses:
        return None
    p = len(wins) / n
    b = (sum(wins) / len(wins)) / (sum(losses) / len(losses))
    if b <= 0:
        return None
    return p - (1.0 - p) / b


def split_is_oos(rows: list[dict], is_end: str) -> tuple[list[dict], list[dict]]:
    cut = parse_ts(f"{is_end}T00:00:00+00:00")
    is_rows, oos_rows = [], []
    for row in rows:
        dt = parse_ts(row.get("entry_time"))
        if dt is None:
            continue
        if dt < cut:
            is_rows.append(row)
        else:
            oos_rows.append(row)
    return is_rows, oos_rows


def split_label_range(date_from: str, date_to: str, is_end: str) -> tuple[str, str]:
    """Return display labels for IS and OOS ranges.

    `is_end` is the first OOS date, matching `split_is_oos`.
    """
    cut = parse_ts(f"{is_end}T00:00:00+00:00")
    if cut is None:
        return (
            f"IS `{date_from}` to unknown",
            f"OOS unknown to `{date_to}`",
        )
    is_last = (cut - timedelta(days=1)).date().isoformat()
    oos_start = cut.date().isoformat()
    return (
        f"IS `{date_from}` to `{is_last}`",
        f"OOS `{oos_start}` to `{date_to}`",
    )


def summarize_rows(rows: list[dict], family_size: int, is_end: str) -> dict:
    pnls = [float(row.get("pnl_pips") or 0.0) for row in rows]
    wins = sum(1 for row in rows if (row.get("outcome") or "").upper() == "WIN")
    n = len(rows)
    wr = wins / n if n else 0.0
    ev = sum(pnls) / n if n else 0.0
    p_raw = binomial_two_sided_pvalue(wins, n)
    p_bonf = min(1.0, p_raw * max(1, family_size))
    is_rows, oos_rows = split_is_oos(rows, is_end)
    pf = profit_factor(pnls)
    kelly = kelly_fraction(pnls)
    return {
        "n": n,
        "wins": wins,
        "wr": wr,
        "ev": ev,
        "pf": pf,
        "kelly": kelly,
        "wr_wilson_lo": wilson_lower(wins, n),
        "ev_ci_lo": ev_ci_lower(pnls),
        "p_value_raw": p_raw,
        "p_value_bonf": p_bonf,
        "is_n": len(is_rows),
        "is_wr": (sum(1 for row in is_rows if (row.get("outcome") or "").upper() == "WIN") / len(is_rows)) if is_rows else 0.0,
        "is_ev": (sum(float(row.get("pnl_pips") or 0.0) for row in is_rows) / len(is_rows)) if is_rows else 0.0,
        "oos_n": len(oos_rows),
        "oos_wr": (sum(1 for row in oos_rows if (row.get("outcome") or "").upper() == "WIN") / len(oos_rows)) if oos_rows else 0.0,
        "oos_ev": (sum(float(row.get("pnl_pips") or 0.0) for row in oos_rows) / len(oos_rows)) if oos_rows else 0.0,
    }


def new_bucket_decision(stats: dict, current: str, grandfathered: bool) -> tuple[str, str]:
    if grandfathered:
        return current, "grandfather"
    if stats["n"] < HOUR_CELL_N_MIN:
        return current, "insufficient_data"
    if stats["wr_wilson_lo"] > HOUR_WILSON_MIN and stats["ev_ci_lo"] >= 0.0:
        return current, "bucket_pass"
    if current == "live":
        return "shadow", "bucket_fail_demote_to_shadow"
    if current in {"shadow", "pending"}:
        return "demoted", "bucket_fail_demote_from_shadow"
    return current, "already_demoted"


def group_cells(rows: list[dict], family_size: int, is_end: str) -> dict[CellKey, dict]:
    groups: dict[CellKey, list[dict]] = defaultdict(list)
    for row in rows:
        entry_type = str(row.get("entry_type") or "").strip()
        instrument = str(row.get("instrument") or "").strip()
        bucket = hour_bucket_from_ts(row.get("entry_time"))
        if not entry_type or not instrument or bucket is None:
            continue
        groups[CellKey(entry_type, instrument, bucket)].append(row)
    return {
        key: summarize_rows(group_rows, family_size=family_size, is_end=is_end)
        for key, group_rows in groups.items()
    }


def strategy_pair_summary(rows: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        entry_type = str(row.get("entry_type") or "").strip()
        instrument = str(row.get("instrument") or "").strip()
        if not entry_type or not instrument:
            continue
        grouped[f"{entry_type}|{instrument}"].append(row)
    out = {}
    for key, group_rows in grouped.items():
        wins = sum(1 for row in group_rows if (row.get("outcome") or "").upper() == "WIN")
        n = len(group_rows)
        ev = sum(float(row.get("pnl_pips") or 0.0) for row in group_rows) / n if n else 0.0
        entry_type, instrument = key.split("|", 1)
        out[key] = {
            "entry_type": entry_type,
            "instrument": instrument,
            "n": n,
            "wr": round(100.0 * wins / n, 1) if n else 0.0,
            "ev": round(ev, 2),
        }
    return out


def strategy_shadow_status(shadow_rows: list[dict]) -> dict[str, dict]:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for row in shadow_rows:
        entry_type = str(row.get("entry_type") or "").strip()
        if entry_type:
            by_type[entry_type].append(row)
    by_type_pair = strategy_pair_summary(shadow_rows)
    num_tests = max(1, len(by_type))
    out = {}
    for entry_type, rows in by_type.items():
        wins = sum(1 for row in rows if (row.get("outcome") or "").upper() == "WIN")
        n = len(rows)
        wr = round(100.0 * wins / n, 1) if n else 0.0
        ev = sum(float(row.get("pnl_pips") or 0.0) for row in rows) / n if n else 0.0
        friction = DemoTrader._strategy_friction_pips(entry_type, by_type_pair, mode="DT")
        kelly = kelly_fraction([float(row.get("pnl_pips") or 0.0) for row in rows])
        decision = DemoTrader._shadow_promotion_decision(
            n=n,
            wins=wins,
            num_tests=num_tests,
            kelly_f=kelly,
            ev=ev,
            friction_pip=friction,
        )
        out[entry_type] = {
            "status": "promoted" if decision["promoted"] else "pending",
            "n": n,
            "wr": wr,
            "ev": ev,
            "friction_pip": friction,
            "decision": decision,
        }
    return out


def evaluate_counterfactual(rows: list[dict], date_from: str, date_to: str, is_end: str) -> dict:
    in_window = []
    lo = parse_ts(f"{date_from}T00:00:00+00:00")
    hi = parse_ts(f"{date_to}T00:00:00+00:00")
    for row in rows:
        dt = parse_ts(row.get("entry_time"))
        if dt is None:
            continue
        if lo <= dt < hi and is_closed_outcome(row):
            in_window.append(row)

    live_rows = [row for row in in_window if strict_live_trade(row)]
    shadow_rows = [row for row in in_window if strict_shadow_trade(row)]
    shadow_status = strategy_shadow_status(shadow_rows)
    shadow_family = max(1, len({row.get("entry_type") for row in shadow_rows if row.get("entry_type")}) * 4)
    live_family = max(1, len({row.get("entry_type") for row in live_rows if row.get("entry_type")}) * 4)
    shadow_cells = group_cells(shadow_rows, family_size=shadow_family, is_end=is_end)
    live_cells = group_cells(live_rows, family_size=live_family, is_end=is_end)
    live_strategies = {key.entry_type for key in live_cells}

    evaluated_shadow_cells = []
    false_demote_num = 0
    false_demote_den = 0
    insufficient = []
    for key, stats in sorted(shadow_cells.items(), key=lambda item: (item[0].entry_type, item[0].instrument, item[0].hour_bucket)):
        baseline = shadow_status.get(key.entry_type, {"status": "pending"})
        current = "live" if baseline["status"] == "promoted" else baseline["status"]
        grandfathered = key.entry_type in EXPLICIT_GRANDFATHER or key.entry_type in live_strategies
        new_status, reason = new_bucket_decision(stats, current=current, grandfathered=grandfathered)
        if current == "live" and stats["n"] >= HOUR_CELL_N_MIN:
            false_demote_den += 1
            if new_status != "live":
                false_demote_num += 1
        if stats["n"] < HOUR_CELL_N_MIN:
            insufficient.append((key, stats, "shadow"))
        evaluated_shadow_cells.append({
            "entry_type": key.entry_type,
            "instrument": key.instrument,
            "hour_bucket": key.hour_bucket,
            "scope": "shadow",
            "baseline_status": baseline["status"],
            "current_status": current,
            "new_status": new_status,
            "reason": reason,
            "grandfathered": grandfathered,
            **stats,
        })

    evaluated_live_cells = []
    for key, stats in sorted(live_cells.items(), key=lambda item: (item[0].entry_type, item[0].instrument, item[0].hour_bucket)):
        grandfathered = True
        current = "live"
        new_status, reason = new_bucket_decision(stats, current=current, grandfathered=grandfathered)
        if stats["n"] < HOUR_CELL_N_MIN:
            insufficient.append((key, stats, "live"))
        evaluated_live_cells.append({
            "entry_type": key.entry_type,
            "instrument": key.instrument,
            "hour_bucket": key.hour_bucket,
            "scope": "live",
            "baseline_status": "live",
            "current_status": current,
            "new_status": new_status,
            "reason": reason,
            "grandfathered": grandfathered,
            **stats,
        })

    return {
        "date_from": date_from,
        "date_to": date_to,
        "is_end": is_end,
        "total_rows": len(in_window),
        "live_rows": len(live_rows),
        "shadow_rows": len(shadow_rows),
        "shadow_family_size": shadow_family,
        "live_family_size": live_family,
        "shadow_status": shadow_status,
        "shadow_cells": evaluated_shadow_cells,
        "live_cells": evaluated_live_cells,
        "false_demote_num": false_demote_num,
        "false_demote_den": false_demote_den,
        "false_demote_rate": (false_demote_num / false_demote_den) if false_demote_den else None,
        "insufficient_cells": insufficient,
        "grandfather_live_strategies": sorted(live_strategies | set(EXPLICIT_GRANDFATHER)),
    }


def render_markdown(result: dict, blocked_error: str | None = None) -> str:
    now = datetime.now(timezone.utc).isoformat()
    is_label, oos_label = split_label_range(
        result["date_from"], result["date_to"], result["is_end"]
    )
    lines = [
        "# H1 Hour-Bucket 3-Month Counterfactual",
        "",
        f"- Generated: `{now}`",
        f"- Window: `{result['date_from']}` to `{result['date_to']}` (UTC, end-exclusive)",
        f"- OOS split: {is_label}, {oos_label}",
    ]
    if blocked_error:
        lines.extend([
            f"- Status: `BLOCKED`",
            f"- Blocker: production fetch failed: `{blocked_error}`",
            "",
            "## Outcome",
            "",
            "The required Render production dataset could not be fetched in this environment, so no 3-month counterfactual statistics were computed.",
            "",
            "## Evidence Needed Next",
            "",
            f"1. A successful fetch of `/api/demo/trades?status=closed&limit=10000&date_from={result['date_from']}&date_to={result['date_to']}` from a network-enabled environment.",
            "2. The resulting JSON payload, or the ability to rerun this tool where the Render hostname resolves.",
            "",
        ])
        return "\n".join(lines)

    lines.extend([
        f"- Status: `OK`",
        f"- Total closed rows in window: `{result['total_rows']}`",
        f"- Strict LIVE rows: `{result['live_rows']}` (`is_shadow=0 AND oanda_trade_id IS NOT NULL`)",
        f"- Strict SHADOW rows: `{result['shadow_rows']}` (`is_shadow=1`, non-XAU)",
        f"- Bonferroni family size (shadow): `{result['shadow_family_size']}`",
        "",
        "## Summary",
        "",
    ])
    rate = result["false_demote_rate"]
    rate_text = "n/a" if rate is None else f"{rate * 100:.1f}%"
    verdict = "PASS" if rate is None or rate < FALSE_DEMOTION_MAX else "FAIL"
    lines.extend([
        f"- False demotion rate: `{rate_text}` (`{result['false_demote_num']}/{result['false_demote_den']}`) -> `{verdict}` vs 20% threshold.",
        f"- Grandfather verification targets: `{', '.join(result['grandfather_live_strategies'])}`",
        f"- Insufficient-data cells (`N<30`): `{len(result['insufficient_cells'])}`",
        "",
        "## Live Grandfather Verification",
        "",
    ])
    if result["live_cells"]:
        lines.append("| strategy | pair | bucket | N | WR | EV | WR Wilson lo | EV CI lo | result |")
        lines.append("|---|---|---|---:|---:|---:|---:|---:|---|")
        for row in result["live_cells"]:
            lines.append(
                f"| {row['entry_type']} | {row['instrument']} | {row['hour_bucket']} | "
                f"{row['n']} | {row['wr']*100:.1f}% | {row['ev']:+.3f} | "
                f"{row['wr_wilson_lo']:.3f} | {row['ev_ci_lo']:+.3f} | {row['reason']} |"
            )
    else:
        lines.append("No strict LIVE rows were present in the analysis window.")
    lines.extend([
        "",
        "## Shadow Dry-Run",
        "",
        "| strategy | pair | bucket | baseline | new | N | WR | EV | PF | Kelly | WR Wilson lo | EV CI lo | p_bonf | IS N/EV | OOS N/EV | reason |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ])
    for row in result["shadow_cells"]:
        pf = "inf" if row["pf"] == math.inf else ("-" if row["pf"] is None else f"{row['pf']:.2f}")
        kelly = "-" if row["kelly"] is None else f"{row['kelly']:.3f}"
        lines.append(
            f"| {row['entry_type']} | {row['instrument']} | {row['hour_bucket']} | "
            f"{row['baseline_status']} | {row['new_status']} | {row['n']} | "
            f"{row['wr']*100:.1f}% | {row['ev']:+.3f} | {pf} | {kelly} | "
            f"{row['wr_wilson_lo']:.3f} | {row['ev_ci_lo']:+.3f} | {row['p_value_bonf']:.4f} | "
            f"{row['is_n']}/{row['is_ev']:+.3f} | {row['oos_n']}/{row['oos_ev']:+.3f} | {row['reason']} |"
        )
    lines.extend([
        "",
        "## Insufficient Data Cells",
        "",
        "| scope | strategy | pair | bucket | N | WR | EV | note |",
        "|---|---|---|---|---:|---:|---:|---|",
    ])
    for key, stats, scope in result["insufficient_cells"]:
        lines.append(
            f"| {scope} | {key.entry_type} | {key.instrument} | {key.hour_bucket} | "
            f"{stats['n']} | {stats['wr']*100:.1f}% | {stats['ev']:+.3f} | insufficient data |"
        )
    return "\n".join(lines)


def load_rows(args: argparse.Namespace) -> list[dict]:
    if args.input_json:
        with open(args.input_json) as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload.get("trades", [])
        return payload
    df = fetch_closed_trades(
        date_from=args.date_from,
        date_to=args.date_to,
        limit=args.limit,
        include_xau=False,
        include_shadow=True,
    )
    return df.to_dict("records")


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result_meta = {
        "date_from": args.date_from,
        "date_to": args.date_to,
        "is_end": args.is_end,
    }
    try:
        rows = load_rows(args)
        result = evaluate_counterfactual(rows, args.date_from, args.date_to, args.is_end)
        markdown = render_markdown(result)
        payload = result
        exit_code = 0
    except ProductionFetchError as exc:
        markdown = render_markdown(result_meta, blocked_error=str(exc))
        payload = {"status": "blocked", "error": str(exc), **result_meta}
        exit_code = 2
    output.write_text(markdown)
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(payload, indent=2, default=str))
    print(f"WROTE: {output}")
    if exit_code:
        print(payload["error"])
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
