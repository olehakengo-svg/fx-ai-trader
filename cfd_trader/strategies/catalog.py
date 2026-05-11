"""Strategy registry for cfd-trader.

A strategy is a callable: (candles_df, params_dict) -> trades_df.
Phase 1 registers exactly one strategy (the rank-1 from
docs/phase1-strategy-candidates.md). Future phases append to this dict.
"""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd

StrategyFn = Callable[[pd.DataFrame, dict], pd.DataFrame]

STRATEGIES: dict[str, StrategyFn] = {}


def register(name: str, fn: StrategyFn) -> None:
    if name in STRATEGIES:
        raise ValueError(f"strategy already registered: {name}")
    STRATEGIES[name] = fn


def get(name: str) -> StrategyFn:
    if name not in STRATEGIES:
        raise KeyError(f"unknown strategy: {name!r}. Registered: {sorted(STRATEGIES)}")
    return STRATEGIES[name]
