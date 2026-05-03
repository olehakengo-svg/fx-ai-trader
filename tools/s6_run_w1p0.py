#!/usr/bin/env python3
"""Wave 1 Phase 0 driver: parquet -> chart-pattern detector -> SQLite."""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.s6_chart_pattern_detector import detect_chart_patterns, ensure_schema, insert_signals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default="USD_JPY")
    parser.add_argument("--tf", default="M5")
    parser.add_argument("--parquet", default="data/cache/massive/USD_JPY_5m.parquet")
    parser.add_argument("--db", default="data/chart_patterns.db")
    args = parser.parse_args(argv)

    parquet = ROOT / args.parquet if not Path(args.parquet).is_absolute() else Path(args.parquet)
    db_path = ROOT / args.db if not Path(args.db).is_absolute() else Path(args.db)
    if not parquet.exists():
        raise FileNotFoundError(f"parquet not found: {parquet}")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    df = pd.read_parquet(parquet)
    signals = detect_chart_patterns(df, pair=args.pair, timeframe=args.tf)

    with sqlite3.connect(db_path) as conn:
        ensure_schema(conn)
        inserted = insert_signals(conn, signals)
        dup_rows = conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT pattern_id, pair, timeframe, pivot_anchor_ts, pivot_opposite_ts, COUNT(*) AS n
                FROM chart_pattern_signals
                GROUP BY 1,2,3,4,5
                HAVING n > 1
            )
            """
        ).fetchone()[0]

    counts = Counter(s.pattern_name for s in signals)
    elapsed = time.perf_counter() - t0
    print(f"loaded={len(df)} detected={len(signals)} inserted={inserted} elapsed_sec={elapsed:.2f} db={db_path}")
    for name, n in sorted(counts.items()):
        print(f"{name:24s} {n:6d}")
    print(f"duplicate_pivot_tuples={dup_rows}")
    if len(signals) < 360:
        print("VERDICT=NEEDS_MORE_EVIDENCE total signals < 360")
    elif any(n < 30 for n in counts.values()) or len(counts) < 12:
        print("VERDICT=NEEDS_MORE_EVIDENCE at least one pattern has N < 30")
    else:
        print("VERDICT=ACCEPT_W1P0_DETECTOR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
