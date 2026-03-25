"""Tests for run_strategy_evaluation in app.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np


def _make_mock_ohlcv(n=500):
    """Create a realistic mock OHLCV DataFrame for evaluation tests."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="5min")
    base = 150.0
    returns = np.random.normal(0, 0.0005, n)
    close = base * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.normal(0, 0.0003, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.0003, n)))
    open_ = close * (1 + np.random.normal(0, 0.0001, n))
    volume = np.random.randint(100, 10000, n).astype(float)
    return pd.DataFrame({
        "Open": open_, "High": high, "Low": low,
        "Close": close, "Volume": volume,
    }, index=dates)


def _mock_scalp_result():
    """Return a plausible backtest result dict."""
    return {
        "win_rate": 35.0,
        "total_trades": 100,
        "expected_value": 0.12,
        "ev_per_trade": 0.12,
        "sharpe": 1.2,
        "max_drawdown": 8.5,
        "entry_breakdown": {"ema_cross": 30, "bb_bounce": 70},
    }


class TestRunStrategyEvaluation:
    @patch("app.run_scalp_backtest")
    @patch("app.fetch_ohlcv")
    def test_returns_expected_top_level_keys(self, mock_fetch, mock_bt):
        mock_fetch.return_value = _make_mock_ohlcv(500)
        mock_bt.return_value = _mock_scalp_result()

        from app import run_strategy_evaluation
        result = run_strategy_evaluation("USDJPY=X", interval="5m", lookback_days=45)

        assert "error" not in result, f"Got error: {result.get('error')}"
        expected_keys = [
            "strategy", "baseline_random", "baseline_bah",
            "monte_carlo", "significance", "kpi_targets",
            "interval", "lookback_days",
        ]
        for key in expected_keys:
            assert key in result, f"Missing top-level key '{key}'"

    @patch("app.run_scalp_backtest")
    @patch("app.fetch_ohlcv")
    def test_strategy_section_keys(self, mock_fetch, mock_bt):
        mock_fetch.return_value = _make_mock_ohlcv(500)
        mock_bt.return_value = _mock_scalp_result()

        from app import run_strategy_evaluation
        result = run_strategy_evaluation("USDJPY=X", interval="5m", lookback_days=45)

        strat = result["strategy"]
        for key in ("win_rate", "win_rate_ci", "total_trades", "ev_per_trade", "sharpe"):
            assert key in strat, f"Missing strategy key '{key}'"

    @patch("app.run_scalp_backtest")
    @patch("app.fetch_ohlcv")
    def test_baseline_random_keys(self, mock_fetch, mock_bt):
        mock_fetch.return_value = _make_mock_ohlcv(500)
        mock_bt.return_value = _mock_scalp_result()

        from app import run_strategy_evaluation
        result = run_strategy_evaluation("USDJPY=X", interval="5m", lookback_days=45)

        rand = result["baseline_random"]
        assert "win_rate" in rand
        assert "total_trades" in rand
        assert isinstance(rand["win_rate"], (int, float))

    @patch("app.run_scalp_backtest")
    @patch("app.fetch_ohlcv")
    def test_significance_section(self, mock_fetch, mock_bt):
        mock_fetch.return_value = _make_mock_ohlcv(500)
        mock_bt.return_value = _mock_scalp_result()

        from app import run_strategy_evaluation
        result = run_strategy_evaluation("USDJPY=X", interval="5m", lookback_days=45)

        sig = result["significance"]
        assert "vs_random" in sig
        assert "vs_breakeven" in sig
        assert "verdict" in sig
        assert "p_value" in sig["vs_random"]
        assert "z_stat" in sig["vs_random"]
        assert isinstance(sig["vs_random"]["significant"], bool)

    @patch("app.run_scalp_backtest")
    @patch("app.fetch_ohlcv")
    def test_kpi_targets_section(self, mock_fetch, mock_bt):
        mock_fetch.return_value = _make_mock_ohlcv(500)
        mock_bt.return_value = _mock_scalp_result()

        from app import run_strategy_evaluation
        result = run_strategy_evaluation("USDJPY=X", interval="5m", lookback_days=45)

        kpi = result["kpi_targets"]
        assert "wr_target_pass" in kpi
        assert "beats_random" in kpi
        assert isinstance(kpi["wr_target_pass"], bool)
        assert isinstance(kpi["beats_random"], bool)

    @patch("app.run_scalp_backtest")
    @patch("app.fetch_ohlcv")
    def test_returns_error_on_insufficient_data(self, mock_fetch, mock_bt):
        mock_fetch.return_value = _make_mock_ohlcv(50)  # Too few bars
        mock_bt.return_value = _mock_scalp_result()

        from app import run_strategy_evaluation
        result = run_strategy_evaluation("USDJPY=X", interval="5m", lookback_days=5)

        # With only 50 bars and dropna from add_indicators, should get error
        assert "error" in result

    @patch("app.run_scalp_backtest")
    @patch("app.fetch_ohlcv")
    def test_monte_carlo_ci_values(self, mock_fetch, mock_bt):
        mock_fetch.return_value = _make_mock_ohlcv(500)
        mock_bt.return_value = _mock_scalp_result()

        from app import run_strategy_evaluation
        result = run_strategy_evaluation("USDJPY=X", interval="5m", lookback_days=45)

        mc = result["monte_carlo"]
        assert "ci_95_low" in mc
        assert "ci_95_high" in mc
        assert mc["ci_95_low"] <= mc["ci_95_high"]
