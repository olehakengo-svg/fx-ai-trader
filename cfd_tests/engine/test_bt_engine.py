"""bt_engine: end-to-end simulation on synthetic candles + tiny strategy."""
from __future__ import annotations

import pandas as pd
import pytest

from cfd_trader.data.oanda_client import SPX500_USD_SPEC
from cfd_trader.engine.bt_engine import run_bt
from cfd_trader.engine.bt_result import BTResult


def make_candles() -> pd.DataFrame:
    times = pd.to_datetime(
        [f"2026-05-01T00:0{i}:00Z" for i in range(0, 8)], utc=True
    )
    return pd.DataFrame({
        "time": times,
        "open":  [5000.0, 5001.0, 5002.0, 5003.0, 5002.0, 5001.0, 5000.0, 4999.0],
        "high":  [5001.0, 5003.0, 5004.0, 5004.0, 5003.0, 5002.0, 5001.0, 5000.0],
        "low":   [4999.0, 5000.0, 5001.0, 5001.0, 5000.0, 4999.0, 4998.0, 4998.0],
        "close": [5001.0, 5002.0, 5003.0, 5002.0, 5001.0, 5000.0, 4999.0, 4998.0],
        "volume": [10] * 8,
        "complete": [True] * 8,
    })


def fixed_strategy(candles: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Long entry at row 0, exit at row 3. Long entry at row 4, exit at row 7."""
    return pd.DataFrame([
        {"entry_time": candles.iloc[0]["time"], "exit_time": candles.iloc[3]["time"],
         "side": "long", "entry_price": 5000.0, "exit_price": 5002.0, "units": 1},
        {"entry_time": candles.iloc[4]["time"], "exit_time": candles.iloc[7]["time"],
         "side": "long", "entry_price": 5001.0, "exit_price": 4998.0, "units": 1},
    ])


def test_run_bt_returns_bt_result_and_trades() -> None:
    candles = make_candles()
    result, trades = run_bt(
        strategy=fixed_strategy, strategy_name="fixed",
        candles=candles, spec=SPX500_USD_SPEC, tf="M5", params={},
    )
    assert isinstance(result, BTResult)
    assert isinstance(trades, pd.DataFrame)
    assert {"pnl_point", "equity_after"}.issubset(set(trades.columns))


def test_run_bt_pnl_point_for_long_trades() -> None:
    candles = make_candles()
    _, trades = run_bt(
        strategy=fixed_strategy, strategy_name="fixed",
        candles=candles, spec=SPX500_USD_SPEC, tf="M5", params={},
    )
    # Trade 1: long 5000 -> 5002 = +2.0
    # Trade 2: long 5001 -> 4998 = -3.0
    assert trades.iloc[0]["pnl_point"] == pytest.approx(2.0)
    assert trades.iloc[1]["pnl_point"] == pytest.approx(-3.0)


def test_run_bt_metrics_match_manual_calc() -> None:
    candles = make_candles()
    result, _ = run_bt(
        strategy=fixed_strategy, strategy_name="fixed",
        candles=candles, spec=SPX500_USD_SPEC, tf="M5", params={},
    )
    # N=2, wins=1, WR=0.5, EV = (2 + -3)/2 = -0.5
    assert result.n == 2
    assert result.wr == pytest.approx(0.5)
    assert result.ev_point == pytest.approx(-0.5)


def test_run_bt_short_trade_pnl() -> None:
    candles = make_candles()
    def short_strategy(c: pd.DataFrame, _params: dict) -> pd.DataFrame:
        return pd.DataFrame([{
            "entry_time": c.iloc[0]["time"], "exit_time": c.iloc[3]["time"],
            "side": "short", "entry_price": 5003.0, "exit_price": 5000.0, "units": 1,
        }])
    _, trades = run_bt(
        strategy=short_strategy, strategy_name="short",
        candles=candles, spec=SPX500_USD_SPEC, tf="M5", params={},
    )
    # short 5003 -> 5000 = +3.0 (price down = profit)
    assert trades.iloc[0]["pnl_point"] == pytest.approx(3.0)


def test_run_bt_empty_trades_returns_zero_result() -> None:
    candles = make_candles()
    def no_trades(c: pd.DataFrame, _params: dict) -> pd.DataFrame:
        return pd.DataFrame(columns=["entry_time","exit_time","side","entry_price","exit_price","units"])
    result, trades = run_bt(
        strategy=no_trades, strategy_name="empty",
        candles=candles, spec=SPX500_USD_SPEC, tf="M5", params={},
    )
    assert result.n == 0
    assert result.ev_point == 0.0
    assert len(trades) == 0
