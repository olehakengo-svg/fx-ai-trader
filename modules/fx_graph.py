"""FX currency network graph features.

Hong & Klabjan (2025, arXiv 2508.14784) inspired data-layer features.
No LIVE intervention.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from modules.currency_strength import PAIR_MAP


CURRENCIES_5PAIR = ["USD", "EUR", "GBP", "JPY"]
REQUIRED_5PAIR_COLUMNS = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]


def _design_matrix(
    pair_columns: Sequence[str],
    currencies: Sequence[str] = CURRENCIES_5PAIR,
) -> np.ndarray:
    rows: list[np.ndarray] = []
    ccy_idx = {ccy: i for i, ccy in enumerate(currencies)}

    for pair in pair_columns:
        if pair not in PAIR_MAP:
            raise ValueError(f"unsupported pair for FX graph: {pair}")
        base, quote = PAIR_MAP[pair]
        if base not in ccy_idx or quote not in ccy_idx:
            raise ValueError(f"pair {pair} uses currency outside {list(currencies)}")
        row = np.zeros(len(currencies), dtype=float)
        row[ccy_idx[base]] = 1.0
        row[ccy_idx[quote]] = -1.0
        rows.append(row)

    # Normalization: sum_i log(V_ti) = 0.
    rows.append(np.ones(len(currencies), dtype=float))
    return np.vstack(rows)


def fx_graph_condition_number(pair_columns: Sequence[str] = REQUIRED_5PAIR_COLUMNS) -> float:
    """Condition number of the constrained least-squares system."""
    return float(np.linalg.cond(_design_matrix(pair_columns)))


def compute_currency_value(log_prices: pd.DataFrame) -> pd.DataFrame:
    """Compute MLE currency value log(V_ti) for the 5-pair FX graph.

    Solves log(X_tij) = log(V_i) - log(V_j), subject to
    sum_i log(V_ti) = 0. Input values must be log close prices.
    """
    missing = [c for c in REQUIRED_5PAIR_COLUMNS if c not in log_prices.columns]
    if missing:
        raise ValueError(f"log_prices missing required columns: {missing}")

    work = log_prices.loc[:, REQUIRED_5PAIR_COLUMNS].astype(float)
    if work.isna().any().any():
        work = work.dropna(how="any")

    a = _design_matrix(REQUIRED_5PAIR_COLUMNS)
    values: list[np.ndarray] = []
    for _, row in work.iterrows():
        b = np.append(row.to_numpy(dtype=float), 0.0)
        solution, _, _, _ = np.linalg.lstsq(a, b, rcond=None)
        # Remove any numerical drift in the normalization constraint.
        solution = solution - solution.mean()
        values.append(solution)

    return pd.DataFrame(values, index=work.index, columns=CURRENCIES_5PAIR)


def triangular_residual(
    log_prices: pd.DataFrame,
    log_currency_value: pd.DataFrame,
) -> pd.DataFrame:
    """Compute alpha_tij = log(X_tij) - (log(V_i) - log(V_j)) per pair."""
    aligned_prices, aligned_values = log_prices.align(log_currency_value, axis=0, join="inner")
    missing = [c for c in REQUIRED_5PAIR_COLUMNS if c not in aligned_prices.columns]
    if missing:
        raise ValueError(f"log_prices missing required columns: {missing}")
    missing_ccy = [c for c in CURRENCIES_5PAIR if c not in aligned_values.columns]
    if missing_ccy:
        raise ValueError(f"log_currency_value missing required columns: {missing_ccy}")

    result = pd.DataFrame(index=aligned_prices.index)
    for pair in REQUIRED_5PAIR_COLUMNS:
        base, quote = PAIR_MAP[pair]
        implied = aligned_values[base] - aligned_values[quote]
        result[pair] = aligned_prices[pair].astype(float) - implied
    return result
