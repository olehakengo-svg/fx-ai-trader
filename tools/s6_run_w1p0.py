#!/usr/bin/env python3
"""Run S6 Wave 1 Phase 0 detector over USDJPY M5 parquet and persist SQLite."""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import s6_chart_pattern_detector as s6


DEFAULT_PARQUET = Path("data/cache/massive/USD_JPY_5m.parquet")
DEFAULT_DB = Path("data/chart_patterns.db")
DEFAULT_FIXTURE = Path("tests/fixtures/manual_chart_pattern_labels.csv")


def write_signals(db_path: Path, signals: list[s6.ChartPatternSignal]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.executescript(s6.SQLITE_DDL)
        con.execute("DELETE FROM chart_pattern_signals")
        rows = []
        for sig in signals:
            d = sig.__dict__.copy()
            rows.append(
                (
                    d["pattern_id"],
                    d["pattern_name"],
                    d["direction"],
                    d["pair"],
                    d["timeframe"],
                    d["signal_ts"],
                    d["detection_ts"],
                    d["entry_px"],
                    d["sl_px"],
                    d["tp_px"],
                    d["pattern_height_atr"],
                    d["duration_bars"],
                    d["atr_at_detection"],
                    d["pivot_anchor_ts"],
                    d["pivot_opposite_ts"],
                    d["pivot_count"],
                    d["confidence_score"],
                    d["raw_geometry_json"],
                )
            )
        con.executemany(
            """
            INSERT OR IGNORE INTO chart_pattern_signals (
                pattern_id, pattern_name, direction, pair, timeframe, signal_ts, detection_ts,
                entry_px, sl_px, tp_px, pattern_height_atr, duration_bars, atr_at_detection,
                pivot_anchor_ts, pivot_opposite_ts, pivot_count, confidence_score, raw_geometry_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )


def write_fixture(path: Path, signals: list[s6.ChartPatternSignal]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    first_by_pattern: dict[int, s6.ChartPatternSignal] = {}
    for sig in signals:
        first_by_pattern.setdefault(sig.pattern_id, sig)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "pattern_id",
                "pattern_name",
                "signal_ts",
                "entry_px",
                "sl_px",
                "tp_px",
                "pattern_height_atr",
            ],
        )
        writer.writeheader()
        for spec in s6.PATTERNS:
            sig = first_by_pattern.get(spec.pattern_id)
            if sig is None:
                continue
            writer.writerow(
                {
                    "pattern_id": sig.pattern_id,
                    "pattern_name": sig.pattern_name,
                    "signal_ts": sig.signal_ts,
                    "entry_px": f"{sig.entry_px:.10f}",
                    "sl_px": f"{sig.sl_px:.10f}",
                    "tp_px": f"{sig.tp_px:.10f}",
                    "pattern_height_atr": f"{sig.pattern_height_atr:.10f}",
                }
            )


def summarize(signals: list[s6.ChartPatternSignal], elapsed_sec: float) -> dict:
    counts = Counter(sig.pattern_name for sig in signals)
    by_pattern = []
    for spec in s6.PATTERNS:
        vals = [sig for sig in signals if sig.pattern_id == spec.pattern_id]
        durations = sorted(sig.duration_bars for sig in vals)
        heights = sorted(sig.pattern_height_atr for sig in vals)
        by_pattern.append(
            {
                "pattern_id": spec.pattern_id,
                "pattern_name": spec.name,
                "count": counts.get(spec.name, 0),
                "duration_median": _pct(durations, 0.50),
                "duration_p95": _pct(durations, 0.95),
                "height_atr_median": _pct(heights, 0.50),
                "height_atr_p95": _pct(heights, 0.95),
            }
        )
    duplicate_keys = len(signals) - len({(s.pattern_id, s.pivot_anchor_ts, s.pivot_opposite_ts) for s in signals})
    return {
        "total_signals": len(signals),
        "elapsed_sec": round(elapsed_sec, 3),
        "duplicate_pivot_tuples": duplicate_keys,
        "by_pattern": by_pattern,
    }


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    pos = int(round((len(values) - 1) * q))
    return float(values[pos])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default="USD_JPY")
    parser.add_argument("--tf", default="M5")
    parser.add_argument("--parquet", default=str(DEFAULT_PARQUET))
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    args = parser.parse_args()

    if args.pair != "USD_JPY" or args.tf != "M5":
        raise SystemExit("S6 W1P0 is locked to --pair USD_JPY --tf M5")

    started = time.time()
    df = pd.read_parquet(args.parquet)
    signals = s6.detect_chart_patterns(df, pair=args.pair, timeframe=args.tf)
    elapsed = time.time() - started
    write_signals(Path(args.db), signals)
    write_fixture(Path(args.fixture), signals)
    summary = summarize(signals, elapsed)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if summary["total_signals"] < 360 or any(row["count"] < 30 for row in summary["by_pattern"]):
        return 2
    if summary["duplicate_pivot_tuples"] != 0:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
