from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from modules.vol_forecast import (
    clear_vol_forecast_cache,
    fit_har_rv,
    get_vol_forecast_cache_stats,
    predict_har_rv,
    realized_vol_from_returns,
    vol_forecast_mult,
)


def test_har_rv_fit_on_synthetic_ar1_data():
    rng = np.random.default_rng(42)
    n = 400
    values = np.empty(n)
    values[0] = 0.01
    for i in range(1, n):
        values[i] = 0.002 + 0.72 * values[i - 1] + rng.normal(0.0, 0.0004)
    rv = pd.Series(np.maximum(values, 0.0001), index=pd.date_range("2023-01-01", periods=n, freq="D", tz="UTC"))

    params = fit_har_rv(rv)
    pred = predict_har_rv(params, rv.iloc[:-1])

    assert set(params) >= {"beta0", "beta_d", "beta_w", "beta_m"}
    assert params["beta_d"] > 0.45
    assert pred > 0
    assert abs(pred - float(rv.iloc[-1])) < 0.004


def test_closed_bar_guard_rejects_future_history():
    idx = pd.date_range("2024-01-01", periods=40, freq="h", tz="UTC")
    rv = pd.Series(np.linspace(0.001, 0.002, len(idx)), index=idx)
    params = {"beta0": 0.0, "beta_d": 1.0, "beta_w": 0.0, "beta_m": 0.0, "_asof_ts": pd.Timestamp("2024-01-02T12:00:00Z").timestamp()}

    with pytest.raises(ValueError, match="closed-bar"):
        predict_har_rv(params, rv)


def test_floor_ceiling_clip_with_real_cache_data():
    from tests.conftest import require_data_file
    require_data_file("data/cache/massive/USD_JPY_5m.parquet", "MASSIVE M5 integration")
    clear_vol_forecast_cache()
    asof = datetime(2026, 4, 30, 23, 55, tzinfo=timezone.utc)

    low_clip = vol_forecast_mult(
        "USD_JPY",
        "M5",
        asof,
        target_realized_vol=1e-9,
        floor=0.30,
        ceiling=1.50,
        cache_dir="data/cache/massive",
    )
    high_clip = vol_forecast_mult(
        "USD_JPY",
        "M5",
        asof,
        target_realized_vol=1.0,
        floor=0.30,
        ceiling=1.50,
        cache_dir="data/cache/massive",
    )

    assert low_clip == pytest.approx(0.30)
    assert high_clip == pytest.approx(1.50)


def test_cache_deterministic_hit_count_with_real_cache_data():
    from tests.conftest import require_data_file
    require_data_file("data/cache/massive/USD_JPY_5m.parquet", "MASSIVE M5 integration")
    clear_vol_forecast_cache()
    asof = datetime(2026, 4, 30, 23, 55, tzinfo=timezone.utc)

    first = vol_forecast_mult("USD_JPY", "M5", asof, cache_dir="data/cache/massive")
    before = get_vol_forecast_cache_stats()["hits"]
    second = vol_forecast_mult("USD_JPY", "M5", asof, cache_dir="data/cache/massive")
    after = get_vol_forecast_cache_stats()["hits"]

    assert first == second
    assert after == before + 1


def test_insufficient_history_returns_noop_fallback():
    rv = pd.Series(np.linspace(0.001, 0.002, 21), index=pd.date_range("2024-01-01", periods=21, freq="h", tz="UTC"))

    assert predict_har_rv({"beta0": 0.0, "beta_d": 1.0, "beta_w": 0.0, "beta_m": 0.0}, rv) == pytest.approx(1.0)


def test_realized_vol_from_returns_uses_sqrt_sum_squared_window():
    returns = pd.Series([0.03, 0.04, 0.0], index=pd.date_range("2024-01-01", periods=3, freq="D"))

    rv = realized_vol_from_returns(returns, window=2)

    assert rv.iloc[0] == pytest.approx(0.05)
    assert rv.iloc[1] == pytest.approx(0.04)
