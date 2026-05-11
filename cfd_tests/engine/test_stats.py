"""Pure-math BT stats: Wilson CI, profit factor, Kelly, drawdown."""
from __future__ import annotations

import math

import pandas as pd
import pytest

from cfd_trader.engine.stats import (
    wilson_lo,
    profit_factor,
    kelly_fraction,
    max_drawdown,
    single_year_concentration,
)


def test_wilson_lo_50_wins_100_trials_is_below_half() -> None:
    lo = wilson_lo(wins=50, n=100, z=1.96)
    assert 0.39 < lo < 0.41


def test_wilson_lo_zero_trials_returns_zero() -> None:
    assert wilson_lo(wins=0, n=0) == 0.0


def test_profit_factor_basic() -> None:
    trades = pd.DataFrame({"pnl_point": [10.0, -5.0, 8.0, -2.0]})
    # gross_win=18, gross_loss=7 -> PF=18/7 ~= 2.5714
    assert profit_factor(trades) == pytest.approx(18.0 / 7.0, rel=1e-4)


def test_profit_factor_no_losses_returns_inf() -> None:
    trades = pd.DataFrame({"pnl_point": [10.0, 5.0, 3.0]})
    assert math.isinf(profit_factor(trades))


def test_profit_factor_no_wins_returns_zero() -> None:
    trades = pd.DataFrame({"pnl_point": [-10.0, -5.0]})
    assert profit_factor(trades) == 0.0


def test_kelly_fraction_known_input() -> None:
    # WR=0.6, avg_win=10, avg_loss=5  ->  b=2, p=0.6, q=0.4, f*= (b*p - q)/b = (1.2-0.4)/2 = 0.4
    f = kelly_fraction(wr=0.6, avg_win_point=10.0, avg_loss_point=5.0)
    assert f == pytest.approx(0.4, rel=1e-4)


def test_kelly_fraction_negative_edge_clipped_to_zero() -> None:
    # WR=0.3, b=1 -> f*= (0.3 - 0.7)/1 = -0.4  -> clipped to 0
    f = kelly_fraction(wr=0.3, avg_win_point=5.0, avg_loss_point=5.0)
    assert f == 0.0


def test_max_drawdown_basic() -> None:
    equity = pd.Series([100.0, 110.0, 105.0, 90.0, 95.0, 120.0])
    # peak=110, trough=90, dd=110-90=20 in points
    assert max_drawdown(equity) == pytest.approx(20.0, rel=1e-4)


def test_max_drawdown_monotonic_no_drawdown() -> None:
    equity = pd.Series([100.0, 110.0, 120.0])
    assert max_drawdown(equity) == 0.0


def test_single_year_concentration_returns_max_year_share() -> None:
    trades = pd.DataFrame({
        "entry_time": pd.to_datetime(
            ["2024-05-01", "2024-06-01", "2024-07-01", "2025-01-01"], utc=True
        ),
        "pnl_point": [10.0, 5.0, 3.0, 2.0],  # 2024 pnl=18, 2025 pnl=2, total=20
    })
    # 2024 share = 18/20 = 0.9
    assert single_year_concentration(trades) == pytest.approx(0.9, rel=1e-4)


def test_single_year_concentration_empty_trades_returns_zero() -> None:
    trades = pd.DataFrame({"entry_time": pd.to_datetime([], utc=True), "pnl_point": []})
    assert single_year_concentration(trades) == 0.0
