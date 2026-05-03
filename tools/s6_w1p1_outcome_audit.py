#!/usr/bin/env python3
"""S6 W1P1 outcome labeling for chart pattern signals.

This is not a backtest. It labels each W1P0 signal by the first future M5
bar event among TP, SL, time-out, or data-missing using the pre-registered
24h horizon.
"""
from __future__ import annotations

import argparse
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

PIP_SIZE = 0.01


@dataclass(frozen=True)
class Signal:
    signal_id: int
    signal_ts: str
    direction: str
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", required=True)
    parser.add_argument("--signals", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-horizon-bars", type=int, default=288)
    return parser.parse_args()


def load_bars(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df = df.rename(columns={c: c.lower() for c in df.columns})
    missing = {"high", "low", "close"} - set(df.columns)
    if missing:
        raise ValueError(f"parquet is missing OHLC columns: {sorted(missing)}")
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index()


def load_signals(db_path: Path) -> list[Signal]:
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            """
            SELECT id, signal_ts, direction, entry_px, sl_px, tp_px
            FROM chart_pattern_signals
            ORDER BY id
            """
        ).fetchall()
    return [
        Signal(
            signal_id=int(row[0]),
            signal_ts=str(row[1]),
            direction=str(row[2]),
            entry_px=float(row[3]),
            sl_px=float(row[4]),
            tp_px=float(row[5]),
        )
        for row in rows
    ]


def label_signal(signal: Signal, bars: pd.DataFrame, max_horizon_bars: int) -> Outcome:
    signal_ts = pd.Timestamp(signal.signal_ts)
    if signal_ts.tzinfo is None:
        signal_ts = signal_ts.tz_localize("UTC")
    else:
        signal_ts = signal_ts.tz_convert("UTC")

    # Rule 1: start with the M5 bar immediately after signal_ts.
    start_pos = int(bars.index.searchsorted(signal_ts, side="right"))
    if start_pos >= len(bars):
        return Outcome(signal.signal_id, "DM", None, 0, None)

    horizon_end_pos = start_pos + max_horizon_bars - 1
    observed_end_pos = min(horizon_end_pos, len(bars) - 1)
    lows = bars["low"].to_numpy()
    highs = bars["high"].to_numpy()
    closes = bars["close"].to_numpy()

    for pos in range(start_pos, observed_end_pos + 1):
        sl_hit = lows[pos] <= signal.sl_px <= highs[pos]
        tp_hit = lows[pos] <= signal.tp_px <= highs[pos]
        bars_held = pos - start_pos + 1
        exit_ts = bars.index[pos].isoformat()
        if sl_hit:
            return Outcome(
                signal.signal_id,
                "SL",
                exit_ts,
                bars_held,
                pnl_pips(signal.direction, signal.entry_px, signal.sl_px),
            )
        if tp_hit:
            return Outcome(
                signal.signal_id,
                "TP",
                exit_ts,
                bars_held,
                pnl_pips(signal.direction, signal.entry_px, signal.tp_px),
            )

    if horizon_end_pos >= len(bars):
        bars_held = len(bars) - start_pos
        return Outcome(signal.signal_id, "DM", None, bars_held, None)

    exit_px = float(closes[horizon_end_pos])
    return Outcome(
        signal.signal_id,
        "TO",
        bars.index[horizon_end_pos].isoformat(),
        max_horizon_bars,
        pnl_pips(signal.direction, signal.entry_px, exit_px),
    )


def pnl_pips(direction: str, entry_px: float, exit_px: float) -> float:
    sign = 1.0 if direction == "BUY" else -1.0
    return (exit_px - entry_px) * sign / PIP_SIZE


def write_outcomes(db_path: Path, outcomes: list[Outcome]) -> None:
    rows = [
        (o.signal_id, o.outcome, o.exit_ts, o.bars_held, o.pnl_pips)
        for o in outcomes
    ]
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(OUTCOME_DDL)
        con.execute("DELETE FROM chart_pattern_outcomes")
        con.executemany(
            """
            INSERT INTO chart_pattern_outcomes (
                signal_id, outcome, exit_ts, bars_held, pnl_pips
            ) VALUES (?,?,?,?,?)
            """,
            rows,
        )
        con.commit()


def main() -> int:
    args = parse_args()
    if args.max_horizon_bars <= 0:
        raise SystemExit("--max-horizon-bars must be positive")

    signals_path = Path(args.signals)
    output_path = Path(args.output)
    if signals_path.resolve() != output_path.resolve():
        raise SystemExit("W1P1 is locked to writing outcomes into the same SQLite DB as --signals")

    bars = load_bars(Path(args.parquet))
    signals = load_signals(signals_path)
    outcomes = [label_signal(signal, bars, args.max_horizon_bars) for signal in signals]
    write_outcomes(output_path, outcomes)

    counts: dict[str, int] = {}
    for outcome in outcomes:
        counts[outcome.outcome] = counts.get(outcome.outcome, 0) + 1
    print(
        "labeled "
        f"{len(outcomes)} signals: "
        + ", ".join(f"{k}={counts.get(k, 0)}" for k in ["TP", "SL", "TO", "DM"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
