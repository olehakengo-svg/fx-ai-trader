#!/usr/bin/env python3
"""Price-Shock Reversion Tier 1 live shadow monitor.

Render shell usage:
    python3 tools/price_shock_live_shadow_monitor.py --weeks 6

The monitor is read-only: it opens SQLite in query mode and never promotes,
demotes, mutates tier-master.md, toggles OANDA_EXECUTION_ENABLED, or changes
is_shadow flags. Promotion/demotion statuses are decision material only.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STRATEGIES = [
    "price_shock_rev_eur_gbp_h1_long",
    "price_shock_rev_eur_aud_h1_long",
    "price_shock_rev_usd_cad_h1_long",
    "price_shock_rev_nzd_jpy_h1_long",
    "price_shock_rev_aud_jpy_h1_long",
]

PROMOTE_RAW_P_THRESHOLD = 0.05 / 5
SHADOW_PATTERN_SQL = "price_shock_rev_%_h1_long"


@dataclass
class StrategyMetrics:
    strategy: str
    n_total: int = 0
    n: int = 0
    wins: int = 0
    wr: float = 0.0
    wilson_lo_95: float = 0.0
    ev_pips: float | None = None
    profit_factor: float | None = None
    kelly: float | None = None
    raw_binom_p: float | None = None
    bonferroni_p: float | None = None
    sl_hits: int = 0
    horizon_exits: int = 0
    sl_hit_ratio: float = 0.0
    horizon_exit_ratio: float = 0.0
    six_week_ev_positive: bool = False
    two_week_ev_negative: bool = False
    promote_criteria: dict[str, bool] | None = None
    demote_criteria: dict[str, bool] | None = None
    status: str = "COLLECTING"


def _fmt_pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def _fmt_num(value: float | None, digits: int = 3, signed: bool = False) -> str:
    if value is None:
        return "n/a"
    sign = "+" if signed else ""
    return f"{value:{sign}.{digits}f}"


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    for candidate in (text, text.replace(" ", "T")):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n)))
    return max(0.0, (centre - spread) / den)


def one_sided_binom_p_ge(wins: int, n: int, p0: float = 0.5) -> float | None:
    if n <= 0:
        return None
    if wins <= 0:
        return 1.0
    prob = 0.0
    for k in range(wins, n + 1):
        prob += math.comb(n, k) * (p0**k) * ((1 - p0) ** (n - k))
    return min(1.0, prob)


def profit_factor(pnls: list[float]) -> float | None:
    gains = sum(p for p in pnls if p > 0)
    losses = abs(sum(p for p in pnls if p < 0))
    if losses == 0:
        return None if gains == 0 else math.inf
    return gains / losses


def kelly_fraction(pnls: list[float], wr: float) -> float | None:
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    if not wins or not losses:
        return None
    avg_win = mean(wins)
    avg_loss = mean(losses)
    if avg_win <= 0 or avg_loss <= 0:
        return None
    return wr - ((1 - wr) / (avg_win / avg_loss))


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}  # nosem


def _detect_trades_table(conn: sqlite3.Connection) -> tuple[str, str]:
    for table in ("trades", "demo_trades"):
        if not _table_exists(conn, table):
            continue
        cols = _columns(conn, table)
        required = {"entry_type", "status", "pnl_pips", "is_shadow"}
        if required.issubset(cols):
            time_col = "opened_at" if "opened_at" in cols else "entry_time"
            if time_col in cols:
                return table, time_col
    raise RuntimeError("No compatible trades/demo_trades table found")


def _fetch_shadow_rows(
    conn: sqlite3.Connection,
    table: str,
    time_col: str,
    weeks: int,
    strategy: str | None,
) -> list[sqlite3.Row]:
    # Critical guard: is_shadow = 1 is intentionally hard-coded in SQL.
    where = [
        "is_shadow = 1",
        "entry_type LIKE ?",
        f"{time_col} >= datetime('now', ?)",  # nosem: time_col is schema-detected
    ]
    params: list[Any] = [SHADOW_PATTERN_SQL, f"-{weeks * 7} days"]
    if strategy:
        where.append("entry_type = ?")
        params.append(strategy)

    query = f"""
        SELECT entry_type, status, pnl_pips, close_reason, {time_col} AS opened_at
        FROM {table}
        WHERE {' AND '.join(where)}
        ORDER BY opened_at
    """  # nosem: table/time_col are schema-detected from SQLite metadata.
    return list(conn.execute(query, params).fetchall())


def _fetch_lock_block_count(conn: sqlite3.Connection, weeks: int) -> int | None:
    if _table_exists(conn, "events"):
        cols = _columns(conn, "events")
        if {"event_type", "reason"}.issubset(cols):
            time_col = "created_at" if "created_at" in cols else None
            if time_col:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM events
                    WHERE event_type = 'trade_blocked'
                      AND reason LIKE 'eur_base_shock_lock%'
                      AND created_at >= datetime('now', ?)
                    """,
                    (f"-{weeks * 7} days",),
                ).fetchone()
                return int(row["n"] or 0)
    if _table_exists(conn, "demo_logs"):
        row = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM demo_logs
            WHERE message LIKE '%eur_base_shock_lock%'
              AND COALESCE(created_at, timestamp) >= datetime('now', ?)
            """,
            (f"-{weeks * 7} days",),
        ).fetchone()
        return int(row["n"] or 0)
    return None


def _fetch_shared_lock_violations(
    conn: sqlite3.Connection,
    table: str,
    time_col: str,
    weeks: int,
) -> int:
    status_col = "status"
    rows = conn.execute(
        f"""
        SELECT entry_type, {time_col} AS opened_at
        FROM {table}
        WHERE is_shadow = 1
          AND LOWER({status_col}) = 'open'
          AND entry_type IN (?, ?)
          AND {time_col} >= datetime('now', ?)
        ORDER BY opened_at
        """,  # nosem: table/time_col are schema-detected.
        (
            "price_shock_rev_eur_gbp_h1_long",
            "price_shock_rev_eur_aud_h1_long",
            f"-{weeks * 7} days",
        ),
    ).fetchall()
    # Any simultaneous open presence of both EUR-base strategies means lock failed.
    open_strategies = {row["entry_type"] for row in rows}
    if {
        "price_shock_rev_eur_gbp_h1_long",
        "price_shock_rev_eur_aud_h1_long",
    }.issubset(open_strategies):
        return 1
    return 0


def _build_weekly_breakdown(rows: list[sqlite3.Row], weeks: int) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=weeks * 7)
    week_starts = [(period_start + timedelta(days=7 * idx)).date().isoformat() for idx in range(weeks)]
    by_week_strategy: dict[tuple[str, str], list[float]] = {}
    win_by_week_strategy: dict[tuple[str, str], int] = {}
    for row in rows:
        if str(row["status"]).lower() != "closed":
            continue
        dt = _parse_dt(row["opened_at"])
        if dt is None:
            continue
        if dt < period_start or dt > now:
            continue
        bucket_idx = min(weeks - 1, max(0, int((dt - period_start).total_seconds() // (7 * 24 * 3600))))
        key = (week_starts[bucket_idx], row["entry_type"])
        pnl = float(row["pnl_pips"] or 0.0)
        by_week_strategy.setdefault(key, []).append(pnl)
        if pnl > 0:
            win_by_week_strategy[key] = win_by_week_strategy.get(key, 0) + 1

    out: list[dict[str, Any]] = []
    for week in week_starts:
        item: dict[str, Any] = {"week": week}
        for strategy in DEFAULT_STRATEGIES:
            pnls = by_week_strategy.get((week, strategy), [])
            wins = win_by_week_strategy.get((week, strategy), 0)
            n = len(pnls)
            item[strategy] = {
                "n": n,
                "wr": (wins / n) if n else None,
                "ev_pips": mean(pnls) if pnls else None,
            }
        out.append(item)
    return out


def _consecutive_week_ev(
    weekly: list[dict[str, Any]],
    strategy: str,
    count: int,
    positive: bool,
) -> bool:
    if len(weekly) < count:
        return False
    tail = weekly[-count:]
    for week in tail:
        ev = week[strategy]["ev_pips"]
        if ev is None:
            return False
        if positive and ev <= 0:
            return False
        if not positive and ev >= 0:
            return False
    return True


def _metrics_for_strategy(
    strategy: str,
    rows: list[sqlite3.Row],
    weekly: list[dict[str, Any]],
    shared_lock_violations: int,
) -> StrategyMetrics:
    strategy_rows = [row for row in rows if row["entry_type"] == strategy]
    closed = [row for row in strategy_rows if str(row["status"]).lower() == "closed"]
    pnls = [float(row["pnl_pips"] or 0.0) for row in closed]
    n = len(pnls)
    wins = sum(1 for pnl in pnls if pnl > 0)
    wr = wins / n if n else 0.0
    raw_p = one_sided_binom_p_ge(wins, n)
    wilson = wilson_lower(wins, n)
    pf = profit_factor(pnls)
    sl_hits = sum(1 for row in closed if str(row["close_reason"] or "").lower() == "sl_2atr")
    horizon_exits = sum(1 for row in closed if str(row["close_reason"] or "").lower() == "horizon")
    six_pos = _consecutive_week_ev(weekly, strategy, 6, positive=True)
    two_neg = _consecutive_week_ev(weekly, strategy, 2, positive=False)
    promote = {
        "n_ge_30": n >= 30,
        "wilson_lo_ge_0_50": wilson >= 0.50,
        "raw_binom_p_lt_0_01": raw_p is not None and raw_p < PROMOTE_RAW_P_THRESHOLD,
        "six_weeks_ev_positive": six_pos,
        "shared_lock_violations_zero": shared_lock_violations == 0,
    }
    demote = {
        "n_ge_15_wilson_lo_lt_0_40": n >= 15 and wilson < 0.40,
        "two_weeks_ev_negative": two_neg,
        "sl_hit_ratio_gt_0_30": n > 0 and (sl_hits / n) > 0.30,
    }

    if demote["n_ge_15_wilson_lo_lt_0_40"]:
        status = "DEMOTE_DEACTIVATE"
    elif demote["sl_hit_ratio_gt_0_30"]:
        status = "DEMOTE_STRUCTURE"
    elif demote["two_weeks_ev_negative"]:
        status = "DEMOTE_REVIEW"
    elif all(promote.values()):
        status = "PROMOTE_READY"
    elif sum(1 for ok in promote.values() if not ok) <= 2:
        status = "PROMOTE_PENDING"
    else:
        status = "COLLECTING"

    return StrategyMetrics(
        strategy=strategy,
        n_total=len(strategy_rows),
        n=n,
        wins=wins,
        wr=wr,
        wilson_lo_95=wilson,
        ev_pips=mean(pnls) if pnls else None,
        profit_factor=pf,
        kelly=kelly_fraction(pnls, wr),
        raw_binom_p=raw_p,
        bonferroni_p=min(1.0, raw_p * 5) if raw_p is not None else None,
        sl_hits=sl_hits,
        horizon_exits=horizon_exits,
        sl_hit_ratio=(sl_hits / n) if n else 0.0,
        horizon_exit_ratio=(horizon_exits / n) if n else 0.0,
        six_week_ev_positive=six_pos,
        two_week_ev_negative=two_neg,
        promote_criteria=promote,
        demote_criteria=demote,
        status=status,
    )


def analyze(db_path: Path, weeks: int, strategy: str | None = None) -> dict[str, Any]:
    if weeks < 1 or weeks > 26:
        raise ValueError("--weeks must be between 1 and 26")
    if strategy and strategy not in DEFAULT_STRATEGIES:
        raise ValueError(f"--strategy must be one of: {', '.join(DEFAULT_STRATEGIES)}")

    with _connect_readonly(db_path) as conn:
        table, time_col = _detect_trades_table(conn)
        rows = _fetch_shadow_rows(conn, table, time_col, weeks, strategy)
        weekly = _build_weekly_breakdown(rows, weeks)
        lock_blocks = _fetch_lock_block_count(conn, weeks)
        lock_violations = _fetch_shared_lock_violations(conn, table, time_col, weeks)

    strategies = [strategy] if strategy else DEFAULT_STRATEGIES
    metrics = [
        _metrics_for_strategy(name, rows, weekly, lock_violations)
        for name in strategies
    ]
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=weeks * 7)
    return {
        "title": "Price-Shock Reversion Tier 1 - Live Shadow Monitor",
        "db_path": str(db_path),
        "table": table,
        "time_column": time_col,
        "weeks": weeks,
        "period_start": start.date().isoformat(),
        "period_end": end.date().isoformat(),
        "strategy_filter": strategy,
        "strategies": [asdict(item) for item in metrics],
        "weekly_breakdown": weekly,
        "shared_lock": {
            "block_count": lock_blocks,
            "violation_count": lock_violations,
            "source": "events/demo_logs" if lock_blocks is not None else "unavailable",
        },
    }


def render_table(result: dict[str, Any]) -> str:
    lines = [
        "=" * 64,
        "Price-Shock Reversion Tier 1 - Live Shadow Monitor",
        f"集計期間: {result['period_end']} <- {result['weeks']} 週 ({result['period_start']} ~ {result['period_end']})",
        f"DB table: {result['table']} ({result['time_column']}), Shadow only: is_shadow = 1",
        "=" * 64,
        "",
    ]
    strategies = result["strategies"]
    if not any(item["n_total"] for item in strategies):
        lines.append("No data: no shadow price_shock_rev_*_h1_long trades in this period.")
    else:
        lines.append(
            f"{'Strategy':38} {'N':>4} {'WR':>7} {'Wilson_lo':>10} {'PF':>7} "
            f"{'Kelly':>8} {'EV(p)':>8} {'Raw_p':>9} {'Bonf_p':>9} {'SL_hit':>8} {'Status':>18}"
        )
        for item in strategies:
            pf = "inf" if item["profit_factor"] == math.inf else _fmt_num(item["profit_factor"], 2)
            lines.append(
                f"{item['strategy'][:38]:38} "
                f"{item['n']:4d} "
                f"{_fmt_pct(item['wr']):>7} "
                f"{_fmt_num(item['wilson_lo_95'], 3):>10} "
                f"{pf:>7} "
                f"{_fmt_num(item['kelly'], 3):>8} "
                f"{_fmt_num(item['ev_pips'], 1, signed=True):>8} "
                f"{_fmt_num(item['raw_binom_p'], 4):>9} "
                f"{_fmt_num(item['bonferroni_p'], 4):>9} "
                f"{_fmt_pct(item['sl_hit_ratio']):>8} "
                f"{item['status']:>18}"
            )

    lock = result["shared_lock"]
    block_text = "n/a" if lock["block_count"] is None else str(lock["block_count"])
    if lock["violation_count"]:
        lock_msg = f"CRITICAL: shared lock violations={lock['violation_count']}"
    else:
        lock_msg = "lock working, no violation"
    lines.extend(["", f"EUR base shock lock blocks: {block_text} ({lock_msg})", ""])

    lines.append(f"週次 breakdown (直近 {result['weeks']} 週):")
    header = ["Week"]
    for strategy in DEFAULT_STRATEGIES:
        short = strategy.replace("price_shock_rev_", "").replace("_h1_long", "")
        header.extend([f"{short}_N", f"{short}_WR", f"{short}_EV"])
    lines.append("  ".join(f"{part:>10}" if part != "Week" else f"{part:10}" for part in header))
    for week in result["weekly_breakdown"]:
        row = [f"{week['week']:10}"]
        for strategy in DEFAULT_STRATEGIES:
            cell = week[strategy]
            row.extend(
                [
                    f"{cell['n']:10d}",
                    f"{_fmt_pct(cell['wr']):>10}",
                    f"{_fmt_num(cell['ev_pips'], 1, signed=True):>10}",
                ]
            )
        lines.append("  ".join(row))

    lines.extend(["", "[Promote criteria status]"])
    criteria_labels = [
        ("n_ge_30", "N >= 30"),
        ("wilson_lo_ge_0_50", "Wilson_lo >= 0.50"),
        ("raw_binom_p_lt_0_01", "Bonferroni m=5 raw p < 0.01"),
        ("six_weeks_ev_positive", "6 weeks EV > 0"),
        ("shared_lock_violations_zero", "Shared lock violations = 0"),
    ]
    total = len(strategies)
    for key, label in criteria_labels:
        passed = sum(1 for item in strategies if item["promote_criteria"][key])
        lines.append(f"- {label}: {passed}/{total} strategies")

    lines.append("")
    lines.append("[Demote criteria check]")
    demoted = [item for item in strategies if item["status"].startswith("DEMOTE_")]
    if demoted:
        for item in demoted:
            lines.append(f"- {item['strategy']}: {item['status']}")
    else:
        lines.append("All clear.")
    return "\n".join(lines)


def default_db_path() -> Path:
    for candidate in (ROOT / "demo_data.db", ROOT / "demo_trades.db"):
        if candidate.exists():
            return candidate
    return ROOT / "demo_data.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", type=int, default=6, help="Aggregation weeks (1-26, default 6)")
    parser.add_argument("--db", type=Path, default=default_db_path(), help="SQLite demo DB path")
    parser.add_argument("--strategy", choices=DEFAULT_STRATEGIES, help="Filter to one strategy")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of table text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = analyze(args.db, args.weeks, args.strategy)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_table(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
