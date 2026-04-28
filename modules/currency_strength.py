"""Currency Strength Index — basket-level relative strength for USD/EUR/GBP/JPY.

各通貨の強さ = 該当通貨を含むペア returns の平均 (signed)。
USD strength = avg(USDJPY_ret, -EURUSD_ret, -GBPUSD_ret)
JPY strength = avg(-USDJPY_ret, -EURJPY_ret, -GBPJPY_ret)

これにより basket-level の momentum/MR を pair-level signal と分離可能。
"""
from __future__ import annotations
from typing import Dict, Optional

import numpy as np
import pandas as pd


# Pair → (currency_pos, currency_neg) mapping
PAIR_MAP = {
    "USD_JPY": ("USD", "JPY"),
    "EUR_USD": ("EUR", "USD"),
    "GBP_USD": ("GBP", "USD"),
    "EUR_JPY": ("EUR", "JPY"),
    "GBP_JPY": ("GBP", "JPY"),
}


def basket_strength(pair_returns: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
    """Compute strength series for each currency.

    Args:
        pair_returns: {"USD_JPY": pd.Series of returns, ...}

    Returns:
        {"USD": series, "EUR": series, "GBP": series, "JPY": series}
    """
    contributions = {"USD": [], "EUR": [], "GBP": [], "JPY": []}
    for pair, ret in pair_returns.items():
        if pair not in PAIR_MAP:
            continue
        pos, neg = PAIR_MAP[pair]
        contributions[pos].append(ret)
        contributions[neg].append(-ret)

    strength = {}
    for ccy, series_list in contributions.items():
        if series_list:
            strength[ccy] = pd.concat(series_list, axis=1).mean(axis=1)
    return strength


def basket_strength_percentile(strength: pd.Series, window: int = 96) -> pd.Series:
    """Rolling percentile of strength (0-1)."""
    return strength.rolling(window).rank(pct=True)
