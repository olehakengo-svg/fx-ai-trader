"""Tests for Flask routes in app.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np


def _make_mock_ohlcv(n=300):
    """Create a realistic mock OHLCV DataFrame."""
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


class TestIndexRoute:
    def test_index_returns_200(self, flask_client):
        response = flask_client.get("/")
        assert response.status_code == 200


class TestApiPriceRoute:
    @patch("app.fetch_ohlcv")
    def test_price_returns_200(self, mock_fetch, flask_client):
        """Test /api/price with yfinance fallback (no TWELVEDATA_API_KEY)."""
        df = _make_mock_ohlcv(300)
        mock_fetch.return_value = df

        with patch.dict(os.environ, {}, clear=False):
            # Ensure no TwelveData key so it falls back to yfinance
            os.environ.pop("TWELVEDATA_API_KEY", None)
            response = flask_client.get("/api/price")

        assert response.status_code == 200
        data = response.get_json()
        assert "price" in data
        assert isinstance(data["price"], (int, float))

    @patch("app.fetch_ohlcv")
    def test_price_contains_expected_fields(self, mock_fetch, flask_client):
        df = _make_mock_ohlcv(300)
        mock_fetch.return_value = df

        os.environ.pop("TWELVEDATA_API_KEY", None)
        response = flask_client.get("/api/price")

        assert response.status_code == 200
        data = response.get_json()
        for field in ("price", "open", "high", "low"):
            assert field in data, f"Missing field '{field}' in /api/price response"


class TestApiStrategyModeRoute:
    def test_get_strategy_mode_returns_200(self, flask_client):
        response = flask_client.get("/api/strategy-mode")
        assert response.status_code == 200
        data = response.get_json()
        assert "mode" in data
        assert data["mode"] in ("A", "B")
        assert "profile" in data

    def test_strategy_mode_profile_has_name(self, flask_client):
        response = flask_client.get("/api/strategy-mode")
        data = response.get_json()
        assert "name" in data["profile"]
