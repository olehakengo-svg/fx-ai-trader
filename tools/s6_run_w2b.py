#!/usr/bin/env python3
"""Run S6 Wave 2b pre-registration BT for locked top-3 candidates."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.s6_w2b_pre_reg_bt import run_backtest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default="USD_JPY")
    parser.add_argument("--tf", default="M5")
    parser.add_argument("--db", type=Path, default=Path("data/chart_patterns.db"))
    parser.add_argument("--parquet", type=Path, default=Path("data/cache/massive/USD_JPY_5m.parquet"))
    args = parser.parse_args(argv)

    trades, verdicts = run_backtest(args.db, args.parquet, args.pair, args.tf, write_db=True)
    print(f"W2B_TRADES={len(trades)}")
    print(f"W2B_VERDICTS={len(verdicts)}")
    for row in verdicts:
        print(
            f"{row.candidate_id} {row.intrabar_resolve} {row.eval_split} "
            f"N={row.n} EV={row.ev_pips:.2f} PF={row.pf if row.pf is not None else 'NA'} "
            f"VERDICT={row.verdict}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
