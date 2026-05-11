"""Pure-math BT stats used by BTEngine and gates.py.

Stateless. No I/O. PnL is denominated in points (Section 5.H).
"""
from __future__ import annotations

import math

import pandas as pd


def wilson_lo(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return max(0.0, (center - half) / denom)


def profit_factor(trades: pd.DataFrame) -> float:
    if "pnl_point" not in trades.columns or len(trades) == 0:
        return 0.0
    pnl = trades["pnl_point"].astype(float)
    gross_win = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    if gross_win == 0.0:
        return 0.0
    if gross_loss == 0.0:
        return math.inf
    return gross_win / gross_loss


def kelly_fraction(*, wr: float, avg_win_point: float, avg_loss_point: float) -> float:
    if avg_loss_point <= 0.0 or avg_win_point <= 0.0:
        return 0.0
    b = avg_win_point / avg_loss_point
    p = wr
    q = 1.0 - p
    f_star = (b * p - q) / b
    return max(0.0, f_star)


def max_drawdown(equity_curve: pd.Series) -> float:
    if len(equity_curve) == 0:
        return 0.0
    running_peak = equity_curve.cummax()
    dd = running_peak - equity_curve
    return float(dd.max())


def single_year_concentration(trades: pd.DataFrame) -> float:
    if len(trades) == 0 or "entry_time" not in trades.columns:
        return 0.0
    total = float(trades["pnl_point"].sum())
    if total == 0.0:
        return 0.0
    years = pd.DatetimeIndex(trades["entry_time"]).year
    yearly = trades.groupby(years)["pnl_point"].sum()
    return float(yearly.max() / total) if total > 0 else float(yearly.min() / total)
