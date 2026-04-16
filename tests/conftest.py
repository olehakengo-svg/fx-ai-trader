"""Shared fixtures for FX AI Trader tests."""
import sys
import os
import pytest
import pandas as pd
import numpy as np

# Prevent auto-start of live trader when app is imported during tests
os.environ["TESTING"] = "1"

# Ensure the project root is on sys.path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_ohlcv():
    """Generate a realistic OHLCV DataFrame with 300 rows for testing indicators."""
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2024-01-01", periods=n, freq="5min")
    base_price = 150.0
    # Random walk for close prices
    returns = np.random.normal(0, 0.0005, n)
    close = base_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.normal(0, 0.0003, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.0003, n)))
    open_ = close * (1 + np.random.normal(0, 0.0001, n))
    volume = np.random.randint(100, 10000, n).astype(float)

    df = pd.DataFrame({
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=dates)
    return df


@pytest.fixture
def sample_ohlcv_with_indicators(sample_ohlcv):
    """Sample OHLCV data with indicators already added."""
    from app import add_indicators
    return add_indicators(sample_ohlcv)


@pytest.fixture
def flask_client():
    """Create a Flask test client with external calls mocked."""
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
