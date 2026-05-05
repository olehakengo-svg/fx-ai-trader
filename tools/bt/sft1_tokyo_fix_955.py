#!/usr/bin/env python3
"""SFT-1B Tokyo 9:55 JST JPY demand literal BT."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.bt.sft1_month_end_usd_rebalance import (
    BONFERRONI_M,
    Trade,
    assert_locked_grid,
    evaluate_strategy,
    locked_grid_cells,
    simulate_fixed_window_trade,
)


TOKYO_GRID = {
    "entry_offset_min": [-45, -30, -15],
    "exit_min": [30, 60, 90],
}
PRIMARY_CELL = {"entry_offset_min": -30, "exit_min": 60}
PRIMARY_PAIRS = ["USDJPY"]


def run_tokyo_fix_cell(
    calendar: pd.DataFrame,
    pair_data: dict[str, pd.DataFrame],
    cell: dict[str, int],
    spread_multiplier: float,
) -> list[Trade]:
    trades: list[Trade] = []
    events = calendar[calendar["jp_business_day"]]
    if "USDJPY" not in pair_data:
        return trades
    for _, event in events.iterrows():
        trade = simulate_fixed_window_trade(
            df=pair_data["USDJPY"],
            pair="USDJPY",
            strategy="SFT-B",
            event_date=event["date_utc"].date().isoformat(),
            anchor_ts=event["tokyo_fix_utc"],
            direction="SHORT",
            entry_offset_min=cell["entry_offset_min"],
            exit_min=cell["exit_min"],
            spread_multiplier=spread_multiplier,
            cell=cell,
        )
        if trade is not None:
            trades.append(trade)
    return trades


def print_dry_run() -> None:
    assert_locked_grid(PRIMARY_CELL, TOKYO_GRID)
    print("SFT-1B tokyo_fix_955_jpy_demand DRY RUN")
    print(f"BONFERRONI_M={BONFERRONI_M}")
    print(f"PRIMARY_CELL={PRIMARY_CELL}")
    print("GRID:")
    for cell in locked_grid_cells(TOKYO_GRID):
        marker = " PRIMARY" if cell == PRIMARY_CELL else ""
        print(f"- {cell}{marker}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print_dry_run()
        return 0
    result = evaluate_strategy(
        slug="tokyo-fix-955",
        strategy_name="tokyo_fix_955_jpy_demand",
        primary_cell=PRIMARY_CELL,
        grid=TOKYO_GRID,
        required_pairs=PRIMARY_PAIRS,
        cell_runner=run_tokyo_fix_cell,
    )
    print(f"{result['scenario_verdict']} {result['scenario_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
