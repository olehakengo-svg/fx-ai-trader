from __future__ import annotations

import numpy as np
import pandas as pd

from modules.backtest_engine import BacktestEngine
from modules.fx_graph import compute_currency_value, triangular_residual
from modules.stats_utils import profit_factor


def test_currency_value_recovers_synthetic_truth():
    true_log_v = pd.DataFrame({
        "USD": [0.0],
        "EUR": [0.1],
        "GBP": [0.2],
        "JPY": [-0.3],
    })
    log_prices = pd.DataFrame({
        "USD_JPY": [true_log_v.USD[0] - true_log_v.JPY[0]],
        "EUR_USD": [true_log_v.EUR[0] - true_log_v.USD[0]],
        "GBP_USD": [true_log_v.GBP[0] - true_log_v.USD[0]],
        "EUR_JPY": [true_log_v.EUR[0] - true_log_v.JPY[0]],
        "GBP_JPY": [true_log_v.GBP[0] - true_log_v.JPY[0]],
    })

    result = compute_currency_value(log_prices)

    assert np.allclose(result.values, true_log_v.values, atol=1e-9)


def test_triangular_residual_zero_for_no_arb_data():
    idx = pd.date_range("2026-01-01", periods=3, freq="h", tz="UTC")
    true_log_v = pd.DataFrame(
        {
            "USD": [0.00, 0.01, -0.02],
            "EUR": [0.10, 0.08, 0.11],
            "GBP": [0.20, 0.18, 0.16],
            "JPY": [-0.30, -0.27, -0.25],
        },
        index=idx,
    )
    true_log_v = true_log_v.sub(true_log_v.mean(axis=1), axis=0)
    log_prices = pd.DataFrame(index=idx)
    log_prices["USD_JPY"] = true_log_v["USD"] - true_log_v["JPY"]
    log_prices["EUR_USD"] = true_log_v["EUR"] - true_log_v["USD"]
    log_prices["GBP_USD"] = true_log_v["GBP"] - true_log_v["USD"]
    log_prices["EUR_JPY"] = true_log_v["EUR"] - true_log_v["JPY"]
    log_prices["GBP_JPY"] = true_log_v["GBP"] - true_log_v["JPY"]

    log_v = compute_currency_value(log_prices)
    alpha = triangular_residual(log_prices, log_v)

    assert np.allclose(alpha.values, 0.0, atol=1e-9)


def test_exec_lag_jitter_breaks_lookahead_strategy():
    squeeze_release_momentum = (
        [{"sig": "BUY", "entry_open": 100.0, "entry_close": 101.0, "exit_price": 100.7}] * 20
        + [{"sig": "BUY", "entry_open": 100.0, "entry_close": 101.0, "exit_price": 99.8}] * 20
    )
    asia_range_fade_v1 = (
        [{"sig": "BUY", "entry_open": 100.0, "entry_close": 100.0, "exit_price": 100.7}] * 20
        + [{"sig": "BUY", "entry_open": 100.0, "entry_close": 100.0, "exit_price": 99.8}] * 20
    )

    pf_off = profit_factor(
        BacktestEngine.apply_exec_lag_jitter_to_pnls(
            squeeze_release_momentum, exec_lag_jitter=0.0
        )
    )
    pf_on = profit_factor(
        BacktestEngine.apply_exec_lag_jitter_to_pnls(
            squeeze_release_momentum, exec_lag_jitter=0.5
        )
    )
    assert (pf_off - pf_on) >= 0.30

    pf_off_h = profit_factor(
        BacktestEngine.apply_exec_lag_jitter_to_pnls(
            asia_range_fade_v1, exec_lag_jitter=0.0
        )
    )
    pf_on_h = profit_factor(
        BacktestEngine.apply_exec_lag_jitter_to_pnls(
            asia_range_fade_v1, exec_lag_jitter=0.5
        )
    )
    assert abs(pf_off_h - pf_on_h) < 0.05
