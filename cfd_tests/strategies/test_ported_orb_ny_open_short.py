"""orb_ny_open_short: short-only variant of orb_ny_open."""
from __future__ import annotations

import pandas as pd

from cfd_trader.strategies.ported import orb_ny_open_short as strat


def _day_with_breakdown() -> pd.DataFrame:
    """A 90-bar M5 day where 14:30-14:55 forms range 5000-5010, then 15:00 closes at 4998."""
    times = pd.to_datetime(
        pd.date_range("2026-05-11T14:30:00Z", periods=90, freq="5min", tz="UTC")
    )
    closes = [5005.0] * 6 + [4998.0] + [4995.0] * 83
    df = pd.DataFrame({
        "time": times,
        "open":  closes,
        "high":  [c + 1.0 for c in closes],
        "low":   [c - 1.0 for c in closes],
        "close": closes,
        "volume": [10] * 90,
        "complete": [True] * 90,
    })
    # First six bars actually need range 5000-5010
    for i in range(6):
        df.at[i, "high"] = 5010.0 if i % 2 == 0 else 5005.0
        df.at[i, "low"]  = 5000.0 if i % 2 == 1 else 5002.0
        df.at[i, "close"] = 5005.0
    return df


def _day_with_breakout_up() -> pd.DataFrame:
    """A day where range is 5000-5010 then breakout UP to 5020 — strategy must IGNORE."""
    times = pd.to_datetime(
        pd.date_range("2026-05-11T14:30:00Z", periods=90, freq="5min", tz="UTC")
    )
    closes = [5005.0] * 6 + [5020.0] + [5025.0] * 83
    df = pd.DataFrame({
        "time": times,
        "open":  closes,
        "high":  [c + 1.0 for c in closes],
        "low":   [c - 1.0 for c in closes],
        "close": closes,
        "volume": [10] * 90,
        "complete": [True] * 90,
    })
    for i in range(6):
        df.at[i, "high"] = 5010.0
        df.at[i, "low"]  = 5000.0
        df.at[i, "close"] = 5005.0
    return df


def test_default_params_complete() -> None:
    p = strat.DEFAULT_PARAMS
    for key in ("session_open_hour", "session_open_minute", "range_bars",
                "entry_window_bars", "sl_range_mult", "tp_range_mult",
                "session_close_hour", "units"):
        assert key in p


def test_required_columns_present() -> None:
    df = _day_with_breakdown()
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)
    required = {"entry_time", "exit_time", "side", "entry_price", "exit_price", "units"}
    assert required.issubset(set(trades.columns))


def test_emits_short_trade_on_downward_breakdown() -> None:
    df = _day_with_breakdown()
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)
    assert len(trades) == 1
    assert trades.iloc[0]["side"] == "short"


def test_ignores_upward_breakout() -> None:
    df = _day_with_breakout_up()
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)
    # Strategy is short-only: an upward breakout must produce ZERO trades.
    assert len(trades) == 0


def test_handles_empty_candles() -> None:
    empty = pd.DataFrame(columns=["time","open","high","low","close","volume","complete"])
    trades = strat.generate_trades(empty, strat.DEFAULT_PARAMS)
    assert len(trades) == 0


def test_strategy_registered_in_catalog() -> None:
    from cfd_trader.strategies import catalog
    # Import side-effect registers the strategy.
    import cfd_trader.strategies.ported.orb_ny_open_short  # noqa: F401
    assert "orb_ny_open_short" in catalog.STRATEGIES
