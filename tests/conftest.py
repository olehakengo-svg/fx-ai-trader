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


@pytest.fixture(autouse=True)
def _reset_bt_mode_env():
    """Pop BT_MODE before every test.

    70+ tools/*_shadow_bt.py scripts do `os.environ.setdefault("BT_MODE", "1")`
    at module top level. When pytest collects test files that top-level-import
    those scripts (e.g. `from tools import bb_2sigma_fade_bt as bt`), BT_MODE=1
    leaks into the entire pytest process and corrupts later tests that exercise
    `modules.data.fetch_ohlcv` (which short-circuits to parquet under BT_MODE).
    Tests that genuinely need BT_MODE=1 set it explicitly via
    `monkeypatch.setenv("BT_MODE", "1")` and monkeypatch reverts on teardown."""
    os.environ.pop("BT_MODE", None)
    yield


@pytest.fixture(autouse=True)
def _bypass_seed_exclusion(monkeypatch):
    """Tests use db.open_trade()→db.close_trade() with no delay, producing
    hold<5s rows that look like seed/replay artifacts to the production
    SEED_HOLD_SEC_THRESHOLD filter (added 2026-04-27). Globally patch the SQL
    fragment to a no-op for tests; explicit seed-exclusion tests opt out via
    `monkeypatch.undo()` or by manipulating timestamps directly."""
    try:
        import modules.demo_db as _dd
        monkeypatch.setattr(_dd, "_SEED_EXCLUSION_SQL", "1=1")
    except ImportError:
        pass


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


def require_data_file(path, reason="integration data"):
    """Skip (not fail) when a large untracked data file is absent.

    The MASSIVE *_5m* parquets (~20MB+) are intentionally untracked, so they
    exist on dev machines but not in CI checkouts. Before 2026-07-02 these
    tests hard-asserted existence, which kept main's CI red since ~06-12 and
    silently disabled the CI merge gate. Skipping keeps the "mock-only test
    is forbidden" intent (the test never runs against fakes) while letting
    data-less environments pass. Set FX_REQUIRE_DATA=1 (dev machines / data
    CI) to turn a missing file back into a hard failure.
    """
    import os
    from pathlib import Path as _Path
    import pytest as _pytest
    p = _Path(path)
    if not p.exists():
        if os.environ.get("FX_REQUIRE_DATA", "0") == "1":
            _pytest.fail(f"required data file missing: {p} ({reason})")
        _pytest.skip(f"data file not available in this environment: {p} ({reason})")
    return p
