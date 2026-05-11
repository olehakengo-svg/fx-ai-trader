"""Minimal indices-native BT engine.

Contract:
    strategy(candles_df, params) -> trades_df
    trades_df columns (required): entry_time, exit_time, side, entry_price, exit_price, units

Engine adds: pnl_point, equity_after columns and produces a BTResult.
"""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from cfd_trader.data.oanda_client import InstrumentSpec
from cfd_trader.engine.bt_result import BTResult
from cfd_trader.engine.stats import (
    wilson_lo, profit_factor, kelly_fraction,
    max_drawdown, single_year_concentration,
)

StrategyFn = Callable[[pd.DataFrame, dict], pd.DataFrame]


REQUIRED_TRADE_COLS = (
    "entry_time", "exit_time", "side", "entry_price", "exit_price", "units",
)


def _validate_trades(trades: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_TRADE_COLS if c not in trades.columns]
    if missing:
        raise ValueError(f"strategy trades missing columns: {missing}")


def _compute_pnl_point(row: pd.Series) -> float:
    side = row["side"]
    diff = float(row["exit_price"]) - float(row["entry_price"])
    if side == "long":
        return diff
    elif side == "short":
        return -diff
    raise ValueError(f"unknown side: {side!r}")


def run_bt(
    *,
    strategy: StrategyFn,
    strategy_name: str,
    candles: pd.DataFrame,
    spec: InstrumentSpec,
    tf: str,
    params: dict,
    data_source: str = "oanda",
) -> tuple[BTResult, pd.DataFrame]:
    trades = strategy(candles, params).copy()
    if len(trades) > 0:
        _validate_trades(trades)
        trades["pnl_point"] = trades.apply(_compute_pnl_point, axis=1).astype(float)
        trades["equity_after"] = trades["pnl_point"].cumsum()
    else:
        for col in ("pnl_point", "equity_after"):
            trades[col] = pd.Series(dtype=float)

    n = int(len(trades))
    if n == 0:
        result = BTResult(
            strategy_name=strategy_name, instrument=spec.oanda_v20_name, tf=tf,
            start_iso=str(candles["time"].min()) if len(candles) else "",
            end_iso=str(candles["time"].max()) if len(candles) else "",
            n=0, wr=0.0, ev_point=0.0, pf=0.0, wilson_lo=0.0,
            kelly_fraction=0.0, max_dd_point=0.0,
            single_year_concentration=0.0,
            data_source=data_source,
            metadata_json='{"bonferroni_m": 1}',
        )
        return result, trades

    wins = int((trades["pnl_point"] > 0).sum())
    wr = wins / n
    ev_point = float(trades["pnl_point"].mean())
    pf = profit_factor(trades)
    wlo = wilson_lo(wins=wins, n=n)
    win_pnl = trades.loc[trades["pnl_point"] > 0, "pnl_point"]
    loss_pnl = trades.loc[trades["pnl_point"] < 0, "pnl_point"]
    avg_win = float(win_pnl.mean()) if len(win_pnl) else 0.0
    avg_loss = float(-loss_pnl.mean()) if len(loss_pnl) else 0.0
    kelly = kelly_fraction(wr=wr, avg_win_point=avg_win, avg_loss_point=avg_loss)
    dd = max_drawdown(trades["equity_after"])
    syc = single_year_concentration(trades)

    result = BTResult(
        strategy_name=strategy_name, instrument=spec.oanda_v20_name, tf=tf,
        start_iso=str(candles["time"].min()),
        end_iso=str(candles["time"].max()),
        n=n, wr=wr, ev_point=ev_point, pf=pf, wilson_lo=wlo,
        kelly_fraction=kelly, max_dd_point=dd,
        single_year_concentration=syc,
        data_source=data_source,
        metadata_json='{"bonferroni_m": 1}',
    )
    return result, trades
