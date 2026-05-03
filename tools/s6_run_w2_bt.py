#!/usr/bin/env python3
"""Driver for S6 Wave 2 chart pattern backtests."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import s6_chart_pattern_bt as bt


DEFAULT_DB = Path("data/chart_patterns.db")
DEFAULT_PARQUET = Path("data/cache/massive/USD_JPY_5m.parquet")


def _parse_patterns(raw: str | None) -> set[int] | None:
    if not raw:
        return None
    values = {int(part.strip()) for part in raw.split(",") if part.strip()}
    unknown = values - set(range(1, 13))
    if unknown:
        raise ValueError(f"unknown pattern ids: {sorted(unknown)}")
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default="USD_JPY")
    parser.add_argument("--tf", default="M5")
    parser.add_argument("--mode", choices=["isolated", "arbitrated", "reversed"], required=True)
    parser.add_argument("--patterns", help="comma-separated pattern ids")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    args = parser.parse_args(argv)

    patterns = _parse_patterns(args.patterns)
    if args.mode == "reversed" and patterns is None:
        patterns = {2, 5}

    signal_count = len(bt.load_signals(args.db, args.pair, args.tf, patterns=patterns))
    trades, results = bt.run_backtest(args.db, args.parquet, args.pair, args.tf, args.mode, patterns=patterns)
    bt.write_results(args.db, trades, results, args.mode)

    print(f"S6_W2_BT mode={args.mode} pair={args.pair} tf={args.tf} signals={signal_count} fills={len(trades)} verdict_rows={len(results)}")
    for row in results:
        pf = "inf" if row.stats.pf is not None and row.stats.pf == float("inf") else f"{(row.stats.pf or 0):.3f}"
        print(
            f"{row.pattern_id:02d} {row.pattern_name}: N={row.stats.n} WR={row.stats.wr:.3f} "
            f"EV={row.stats.ev_pips:+.2f} PF={pf} Wlo={row.stats.wilson_lo_95:.3f} "
            f"BonfP={row.stats.bonferroni_p:.5g} Kelly={row.stats.kelly:+.3f} {row.verdict.verdict}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
