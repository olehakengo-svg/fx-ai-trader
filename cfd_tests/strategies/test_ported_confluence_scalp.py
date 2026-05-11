"""Ported strategy confluence_scalp: smoke + contract + uptrend signal."""
from __future__ import annotations

import pandas as pd

from cfd_trader.strategies.ported import confluence_scalp as strat


def _make_uptrend_candles(n: int = 300) -> pd.DataFrame:
    times = pd.to_datetime(
        pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
    )
    base = pd.Series([5000.0 + i * 0.5 for i in range(n)])
    return pd.DataFrame(
        {
            "time": times,
            "open": base,
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base,
            "volume": [10] * n,
            "complete": [True] * n,
        }
    )


def _make_choppy_candles(n: int = 300) -> pd.DataFrame:
    times = pd.to_datetime(
        pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
    )
    base = pd.Series([5000.0 + (i % 6 - 3) * 0.3 for i in range(n)])
    return pd.DataFrame(
        {
            "time": times,
            "open": base,
            "high": base + 0.5,
            "low": base - 0.5,
            "close": base,
            "volume": [10] * n,
            "complete": [True] * n,
        }
    )


def test_strategy_returns_dataframe_with_required_columns() -> None:
    df = _make_uptrend_candles()
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)
    required = {"entry_time", "exit_time", "side", "entry_price", "exit_price", "units"}
    assert isinstance(trades, pd.DataFrame)
    assert required.issubset(set(trades.columns))


def test_strategy_handles_empty_candles() -> None:
    empty = pd.DataFrame(
        columns=["time", "open", "high", "low", "close", "volume", "complete"]
    )
    trades = strat.generate_trades(empty, strat.DEFAULT_PARAMS)
    assert isinstance(trades, pd.DataFrame)
    assert len(trades) == 0


def test_strategy_default_params_are_dict() -> None:
    assert isinstance(strat.DEFAULT_PARAMS, dict)
    assert "ema_fast" in strat.DEFAULT_PARAMS
    assert "atr_period" in strat.DEFAULT_PARAMS


def test_strategy_emits_long_signals_in_clear_uptrend() -> None:
    df = _make_uptrend_candles(n=400)
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)
    # In a clear monotonic uptrend with ATR > 0, at least one long should fire.
    assert len(trades) >= 1
    assert (trades["side"] == "long").any()
