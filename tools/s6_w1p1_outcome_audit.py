#!/usr/bin/env python3
"""S6 W1P1 chart-pattern outcome labeling audit.

This script labels pre-generated chart-pattern signals only. It does not run a
backtest and never updates chart_pattern_signals.
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


OUTCOME_DDL = """
CREATE TABLE IF NOT EXISTS chart_pattern_outcomes (
    signal_id INTEGER PRIMARY KEY,
    outcome TEXT NOT NULL CHECK (outcome IN ('TP','SL','TO','DM')),
    exit_ts TEXT,
    bars_held INTEGER NOT NULL,
    pnl_pips REAL,
    audited_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(signal_id) REFERENCES chart_pattern_signals(id)
);
CREATE INDEX IF NOT EXISTS idx_cpo_outcome ON chart_pattern_outcomes(outcome);
"""

PAIR_SYMMETRY = [
    ("ascending_triangle", "BUY", "descending_triangle", "SELL"),
    ("rising_wedge", "BUY", "falling_wedge", "SELL"),
    ("bull_flag", "BUY", "bear_flag", "SELL"),
    ("double_bottom", "BUY", "double_top", "SELL"),
    ("triple_bottom", "BUY", "triple_top", "SELL"),
    ("inverse_head_shoulders", "BUY", "head_shoulders", "SELL"),
]


@dataclass(frozen=True)
class Signal:
    signal_id: int
    pattern_name: str
    direction: str
    signal_ts: pd.Timestamp
    entry_px: float
    sl_px: float
    tp_px: float


@dataclass(frozen=True)
class Outcome:
    signal_id: int
    outcome: str
    exit_ts: str | None
    bars_held: int
    pnl_pips: float | None


def normalize_bars(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.rename(columns={c: c.lower() for c in out.columns})
    missing = {"high", "low", "close"} - set(out.columns)
    if missing:
        raise ValueError(f"parquet missing OHLC columns: {sorted(missing)}")
    out.index = pd.to_datetime(out.index, utc=True)
    return out.sort_index()


def read_signals(db_path: Path) -> list[Signal]:
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            """
            SELECT id, pattern_name, direction, signal_ts, entry_px, sl_px, tp_px
            FROM chart_pattern_signals
            ORDER BY id
            """
        ).fetchall()
    return [
        Signal(
            signal_id=int(row[0]),
            pattern_name=str(row[1]),
            direction=str(row[2]),
            signal_ts=pd.Timestamp(row[3]).tz_convert("UTC"),
            entry_px=float(row[4]),
            sl_px=float(row[5]),
            tp_px=float(row[6]),
        )
        for row in rows
    ]


def pnl_pips(direction: str, entry_px: float, exit_px: float) -> float:
    sign = 1.0 if direction == "BUY" else -1.0
    return (exit_px - entry_px) * sign / 0.01


def label_signal(
    signal: Signal,
    index: pd.DatetimeIndex,
    highs,
    lows,
    closes,
    max_horizon_bars: int,
) -> Outcome:
    start = int(index.searchsorted(signal.signal_ts, side="right"))
    if start >= len(index):
        return Outcome(signal.signal_id, "DM", None, 0, None)

    available = min(max_horizon_bars, len(index) - start)
    for offset in range(available):
        pos = start + offset
        high = float(highs[pos])
        low = float(lows[pos])
        bars_held = offset + 1

        # Conservative same-bar handling: unknown M5 path is rounded to SL.
        if low <= signal.sl_px <= high:
            return Outcome(
                signal.signal_id,
                "SL",
                index[pos].isoformat(),
                bars_held,
                pnl_pips(signal.direction, signal.entry_px, signal.sl_px),
            )
        if low <= signal.tp_px <= high:
            return Outcome(
                signal.signal_id,
                "TP",
                index[pos].isoformat(),
                bars_held,
                pnl_pips(signal.direction, signal.entry_px, signal.tp_px),
            )

    if available < max_horizon_bars:
        return Outcome(signal.signal_id, "DM", None, available, None)

    exit_pos = start + max_horizon_bars - 1
    exit_px = float(closes[exit_pos])
    return Outcome(
        signal.signal_id,
        "TO",
        index[exit_pos].isoformat(),
        max_horizon_bars,
        pnl_pips(signal.direction, signal.entry_px, exit_px),
    )


def label_outcomes(parquet_path: Path, signals_path: Path, max_horizon_bars: int) -> list[Outcome]:
    bars = normalize_bars(pd.read_parquet(parquet_path))
    signals = read_signals(signals_path)
    highs = bars["high"].to_numpy()
    lows = bars["low"].to_numpy()
    closes = bars["close"].to_numpy()
    return [label_signal(s, bars.index, highs, lows, closes, max_horizon_bars) for s in signals]


def write_outcomes(output_path: Path, outcomes: list[Outcome]) -> None:
    with sqlite3.connect(output_path) as con:
        con.executescript(OUTCOME_DDL)
        con.execute("DELETE FROM chart_pattern_outcomes")
        con.executemany(
            """
            INSERT INTO chart_pattern_outcomes(signal_id, outcome, exit_ts, bars_held, pnl_pips)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(o.signal_id, o.outcome, o.exit_ts, o.bars_held, o.pnl_pips) for o in outcomes],
        )
        signal_count = con.execute("SELECT COUNT(*) FROM chart_pattern_signals").fetchone()[0]
        outcome_count = con.execute("SELECT COUNT(*) FROM chart_pattern_outcomes").fetchone()[0]
        if signal_count != outcome_count:
            raise RuntimeError(f"outcome count mismatch: signals={signal_count} outcomes={outcome_count}")


def fetch_summary(con: sqlite3.Connection) -> dict:
    distribution = con.execute(
        """
        SELECT s.pattern_name, s.direction, o.outcome, COUNT(*)
        FROM chart_pattern_signals s
        JOIN chart_pattern_outcomes o ON o.signal_id = s.id
        GROUP BY s.pattern_name, s.direction, o.outcome
        ORDER BY s.pattern_name, s.direction, o.outcome
        """
    ).fetchall()
    hit_rates = con.execute(
        """
        WITH base AS (
          SELECT s.pattern_name p, s.direction d, o.outcome o
          FROM chart_pattern_signals s
          JOIN chart_pattern_outcomes o ON o.signal_id = s.id
          WHERE o.outcome != 'DM'
        )
        SELECT p, d,
               SUM(CASE o WHEN 'TP' THEN 1 ELSE 0 END) tp,
               SUM(CASE o WHEN 'SL' THEN 1 ELSE 0 END) sl,
               SUM(CASE o WHEN 'TO' THEN 1 ELSE 0 END) to_,
               COUNT(*) n,
               1.0 * SUM(CASE o WHEN 'TP' THEN 1 ELSE 0 END) / COUNT(*) hr
        FROM base
        GROUP BY p, d
        ORDER BY hr DESC
        """
    ).fetchall()
    pnl_frame = pd.read_sql_query(
        """
        SELECT s.pattern_name, o.pnl_pips
        FROM chart_pattern_signals s
        JOIN chart_pattern_outcomes o ON o.signal_id = s.id
        WHERE o.outcome != 'DM' AND o.pnl_pips IS NOT NULL
        """,
        con,
    )
    medians = pnl_frame.groupby("pattern_name")["pnl_pips"].median().sort_index()
    median_all = float(pnl_frame["pnl_pips"].median())
    total = con.execute("SELECT COUNT(*) FROM chart_pattern_outcomes").fetchone()[0]
    dm = con.execute("SELECT COUNT(*) FROM chart_pattern_outcomes WHERE outcome='DM'").fetchone()[0]
    non_dm = total - dm
    return {
        "distribution": distribution,
        "hit_rates": hit_rates,
        "medians": medians,
        "total": total,
        "dm": dm,
        "non_dm": non_dm,
        "median_all": median_all,
    }


def verdict(summary: dict) -> tuple[str, dict]:
    hit_rates = summary["hit_rates"]
    hr_map = {(row[0], row[1]): float(row[6]) for row in hit_rates}
    pairs = []
    symmetric_pairs = 0
    for left_name, left_dir, right_name, right_dir in PAIR_SYMMETRY:
        left = hr_map.get((left_name, left_dir))
        right = hr_map.get((right_name, right_dir))
        diff = None if left is None or right is None else abs(left - right)
        ok = diff is not None and diff <= 0.10
        symmetric_pairs += int(ok)
        pairs.append((left_name, left_dir, left, right_name, right_dir, right, diff, ok))

    total = int(summary["total"])
    dm = int(summary["dm"])
    non_dm = int(summary["non_dm"])
    dm_rate = dm / total if total else 1.0
    gt_50 = sum(1 for row in hit_rates if float(row[6]) > 0.50)
    median_all = float(summary["median_all"])

    coverage_state = "ACCEPT" if total >= 22094 and dm_rate <= 0.01 else "NEEDS_MORE_EVIDENCE" if dm_rate <= 0.05 else "REJECT"
    non_dm_state = "ACCEPT" if non_dm >= 21800 else "NEEDS_MORE_EVIDENCE" if non_dm >= 20000 else "REJECT"
    hit_rate_state = "ACCEPT" if gt_50 >= 6 else "NEEDS_MORE_EVIDENCE" if gt_50 >= 3 else "REJECT"
    symmetry_state = "ACCEPT" if symmetric_pairs == 6 else "NEEDS_MORE_EVIDENCE" if symmetric_pairs >= 4 else "REJECT"
    median_state = "ACCEPT" if median_all > 0 else "REJECT"

    states = [coverage_state, non_dm_state, hit_rate_state, symmetry_state, median_state]
    checks = {
        "coverage_state": coverage_state,
        "non_dm_state": non_dm_state,
        "hit_rate_state": hit_rate_state,
        "symmetry_state": symmetry_state,
        "median_state": median_state,
        "dm_rate": dm_rate,
        "gt_50": gt_50,
        "symmetric_pairs": symmetric_pairs,
        "median_all": float(median_all),
        "pairs": pairs,
    }
    if all(state == "ACCEPT" for state in states):
        return "ACCEPT", checks
    if any(state == "REJECT" for state in states):
        return "REJECT", checks
    return "NEEDS_MORE_EVIDENCE", checks


def print_report(db_path: Path) -> None:
    with sqlite3.connect(db_path) as con:
        summary = fetch_summary(con)
    label, checks = verdict(summary)

    print(f"VERDICT: {label}")
    print(f"total={summary['total']} dm={summary['dm']} dm_rate={checks['dm_rate']:.4%} non_dm={summary['non_dm']}")
    print(
        f"hit_rate_gt_50={checks['gt_50']} symmetric_pairs={checks['symmetric_pairs']}/6 "
        f"median_all_pnl_pips={checks['median_all']:.4f}"
    )
    print()
    print("=== outcome distribution ===")
    for row in summary["distribution"]:
        print(f"  {row[0]:25s} {row[1]:4s} {row[2]:3s} {row[3]:>5d}")
    print()
    print("=== hit_rate per (pattern, direction), DM excluded ===")
    for row in summary["hit_rates"]:
        print(
            f"  {row[0]:25s} {row[1]:4s} TP={row[2]:>4d} SL={row[3]:>4d} "
            f"TO={row[4]:>4d} N={row[5]:>5d} hit_rate={100.0 * row[6]:>5.1f}%"
        )
    print()
    print("=== bull/bear pair symmetry ===")
    for left_name, left_dir, left, right_name, right_dir, right, diff, ok in checks["pairs"]:
        left_txt = "NA" if left is None else f"{100.0 * left:.1f}%"
        right_txt = "NA" if right is None else f"{100.0 * right:.1f}%"
        diff_txt = "NA" if diff is None else f"{100.0 * diff:.1f}pp"
        print(f"  {left_name}:{left_dir} {left_txt} vs {right_name}:{right_dir} {right_txt} diff={diff_txt} ok={ok}")
    print()
    print("=== median pnl_pips per pattern ===")
    for pattern, value in summary["medians"].items():
        print(f"  {pattern:25s} median_pnl_pips={value:>8.4f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", required=True, type=Path)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-horizon-bars", required=True, type=int)
    parser.add_argument("--report-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_horizon_bars <= 0:
        raise ValueError("--max-horizon-bars must be positive")

    if not args.report_only:
        if args.signals.resolve() != args.output.resolve():
            shutil.copy2(args.signals, args.output)
        outcomes = label_outcomes(args.parquet, args.signals, args.max_horizon_bars)
        write_outcomes(args.output, outcomes)
    print_report(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
