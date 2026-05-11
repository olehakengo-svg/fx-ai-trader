"""shadow.replay: pure replay function."""
from __future__ import annotations

import pandas as pd

from cfd_trader.shadow.replay import replay_strategy

# Side-effect: registers orb_ny_open_short in the catalog.
import cfd_trader.strategies.ported.orb_ny_open_short  # noqa: F401


def _make_breakdown_day() -> pd.DataFrame:
    times = pd.to_datetime(
        pd.date_range("2026-05-11T14:30:00Z", periods=90, freq="5min", tz="UTC")
    )
    closes = [5005.0] * 6 + [4998.0] + [4995.0] * 83
    df = pd.DataFrame({
        "time": times, "open": closes,
        "high": [c + 1.0 for c in closes], "low": [c - 1.0 for c in closes],
        "close": closes, "volume": [10] * 90, "complete": [True] * 90,
    })
    for i in range(6):
        df.at[i, "high"] = 5010.0
        df.at[i, "low"]  = 5000.0
        df.at[i, "close"] = 5005.0
    return df


def test_replay_returns_trades_and_cursor() -> None:
    candles = _make_breakdown_day()
    trades, cursor = replay_strategy(
        strategy_name="orb_ny_open_short", candles=candles,
    )
    assert len(trades) == 1
    assert trades.iloc[0]["side"] == "short"
    assert cursor == str(candles["time"].max())


def test_replay_empty_candles_returns_empty_trades_and_none_cursor() -> None:
    empty = pd.DataFrame(columns=["time","open","high","low","close","volume","complete"])
    trades, cursor = replay_strategy(
        strategy_name="orb_ny_open_short", candles=empty,
    )
    assert len(trades) == 0
    assert cursor is None


def test_replay_unknown_strategy_raises_keyerror() -> None:
    candles = _make_breakdown_day()
    import pytest
    with pytest.raises(KeyError):
        replay_strategy(strategy_name="nonexistent", candles=candles)
