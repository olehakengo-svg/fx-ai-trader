#!/usr/bin/env python3
"""SFT-1C quarter-end JPY repatriation literal BT."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.bt.sft1_month_end_usd_rebalance import (
    BONFERRONI_M,
    INTERVENTION_DATES,
    Trade,
    assert_locked_grid,
    evaluate_strategy,
    locked_grid_cells,
    simulate_fixed_window_trade,
)


QUARTER_GRID = {
    "entry_days": [3, 5, 7],
    "exit_hour_utc": [15, 17, 19],
}
PRIMARY_CELL = {"entry_days": 5, "exit_hour_utc": 17}
PRIMARY_PAIRS = ["USDJPY"]


def _last_jp_business_days(calendar: pd.DataFrame, month_end_date: pd.Timestamp, n: int) -> list[pd.Timestamp]:
    month_start = month_end_date.normalize().replace(day=1)
    mask = (
        (calendar["date_utc"] >= month_start)
        & (calendar["date_utc"] <= month_end_date.normalize())
        & calendar["jp_business_day"]
    )
    return list(calendar.loc[mask, "date_utc"].tail(n))


def _interval_has_intervention(entry: pd.Timestamp, exit_: pd.Timestamp) -> bool:
    days = pd.date_range(entry.normalize(), exit_.normalize(), freq="D", tz="UTC")
    return any(day.date().isoformat() in INTERVENTION_DATES for day in days)


def run_quarter_end_cell(
    calendar: pd.DataFrame,
    pair_data: dict[str, pd.DataFrame],
    cell: dict[str, int],
    spread_multiplier: float,
) -> list[Trade]:
    trades: list[Trade] = []
    if "USDJPY" not in pair_data:
        return trades
    events = calendar[calendar["quarter_end_jp"]]
    for _, event in events.iterrows():
        business_days = _last_jp_business_days(calendar, event["date_utc"], cell["entry_days"])
        if not business_days:
            continue
        entry_day = business_days[0]
        exit_anchor = event["date_utc"].normalize() + pd.Timedelta(hours=cell["exit_hour_utc"])
        if _interval_has_intervention(entry_day, exit_anchor):
            continue
        trade = simulate_fixed_window_trade(
            df=pair_data["USDJPY"],
            pair="USDJPY",
            strategy="SFT-C",
            event_date=event["date_utc"].date().isoformat(),
            anchor_ts=entry_day,
            direction="SHORT",
            entry_offset_min=0,
            exit_min=int((exit_anchor - entry_day) / pd.Timedelta(minutes=1)),
            spread_multiplier=spread_multiplier,
            cell=cell,
        )
        if trade is not None:
            trades.append(trade)
    return trades


def print_dry_run() -> None:
    assert_locked_grid(PRIMARY_CELL, QUARTER_GRID)
    print("SFT-1C quarter_end_jpy_repat DRY RUN")
    print(f"BONFERRONI_M={BONFERRONI_M}")
    print(f"PRIMARY_CELL={PRIMARY_CELL}")
    print("GRID:")
    for cell in locked_grid_cells(QUARTER_GRID):
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
        slug="quarter-end-jpy-repat",
        strategy_name="quarter_end_jpy_repat",
        primary_cell=PRIMARY_CELL,
        grid=QUARTER_GRID,
        required_pairs=PRIMARY_PAIRS,
        cell_runner=run_quarter_end_cell,
    )
    print(f"{result['scenario_verdict']} {result['scenario_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
