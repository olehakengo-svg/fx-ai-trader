"""Pure replay of a registered strategy over a candle DataFrame."""
from __future__ import annotations

import pandas as pd

from cfd_trader.strategies import catalog


def replay_strategy(
    *, strategy_name: str, candles: pd.DataFrame
) -> tuple[pd.DataFrame, str | None]:
    fn = catalog.get(strategy_name)  # raises KeyError if missing
    if len(candles) == 0:
        return pd.DataFrame(columns=[
            "entry_time","exit_time","side","entry_price","exit_price","units",
        ]), None
    trades = fn(candles, params={})
    cursor = str(candles["time"].max())
    return trades, cursor
