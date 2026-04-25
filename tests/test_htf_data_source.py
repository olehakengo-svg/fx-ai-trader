"""Unit tests for modules.htf_data_source.

OANDA を実呼び出ししないよう FakeOandaClient で DI する。
"""
from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")

from modules import htf_data_source as hds


class FakeOandaClient:
    """Minimal OandaClient stub for tests."""

    def __init__(self, *, configured: bool = True, payload=None, success: bool = True,
                 raise_exc: Exception | None = None):
        self.configured = configured
        self._payload = payload or {}
        self._success = success
        self._raise = raise_exc
        self.calls: list[dict] = []

    def get_candles(self, instrument, granularity, count, price):
        self.calls.append({
            "instrument": instrument,
            "granularity": granularity,
            "count": count,
            "price": price,
        })
        if self._raise is not None:
            raise self._raise
        return self._success, self._payload


def _sample_candles(n: int = 5, complete_count: int | None = None) -> list:
    """Generate n synthetic OANDA candles. Last (n - complete_count) are incomplete."""
    if complete_count is None:
        complete_count = n
    out = []
    base_ts = pd.Timestamp("2026-04-26T00:00:00Z")
    for i in range(n):
        out.append({
            "time": (base_ts + pd.Timedelta(hours=4 * i)).isoformat(),
            "complete": i < complete_count,
            "volume": 1000 + i,
            "mid": {
                "o": f"{150.000 + i * 0.01:.3f}",
                "h": f"{150.050 + i * 0.01:.3f}",
                "l": f"{149.950 + i * 0.01:.3f}",
                "c": f"{150.020 + i * 0.01:.3f}",
            },
        })
    return out


@pytest.fixture(autouse=True)
def _reset_cache():
    hds.clear_cache()
    yield
    hds.clear_cache()


# ─── _normalize_instrument ────────────────────────────────────────────

@pytest.mark.parametrize("inp,want", [
    ("USDJPY=X", "USD_JPY"),
    ("EURUSD=X", "EUR_USD"),
    ("USD_JPY", "USD_JPY"),
    ("usdjpy=x", "USD_JPY"),
])
def test_normalize_instrument(inp, want):
    assert hds._normalize_instrument(inp) == want


# ─── happy path ───────────────────────────────────────────────────────

def test_fetch_returns_dataframe_with_native_source():
    cli = FakeOandaClient(payload={"candles": _sample_candles(4)})
    df = hds.fetch_htf_candles("USDJPY=X", "H4", 4, client=cli, use_cache=False)
    assert df is not None
    assert len(df) == 4
    assert df.attrs["source"] == "oanda_native"
    assert df.attrs["instrument"] == "USD_JPY"
    assert df.attrs["granularity"] == "H4"
    # Both lowercase and capitalized columns present
    for c in ["open", "high", "low", "close", "volume",
              "Open", "High", "Low", "Close", "Volume"]:
        assert c in df.columns
    # Sorted ascending
    assert df.index.is_monotonic_increasing


def test_fetch_calls_oanda_with_correct_params():
    cli = FakeOandaClient(payload={"candles": _sample_candles(2)})
    hds.fetch_htf_candles("EURUSD=X", "D", 50, client=cli, use_cache=False)
    assert len(cli.calls) == 1
    assert cli.calls[0] == {
        "instrument": "EUR_USD",
        "granularity": "D",
        "count": 50,
        "price": "M",
    }


# ─── look-ahead protection ────────────────────────────────────────────

def test_incomplete_bars_dropped():
    """Incomplete bars must be excluded (look-ahead bias prevention)."""
    candles = _sample_candles(5, complete_count=3)  # last 2 incomplete
    cli = FakeOandaClient(payload={"candles": candles})
    df = hds.fetch_htf_candles("USDJPY=X", "H4", 5, client=cli, use_cache=False)
    assert df is not None
    assert len(df) == 3, "incomplete bars should be dropped"


def test_all_incomplete_returns_none():
    candles = _sample_candles(3, complete_count=0)
    cli = FakeOandaClient(payload={"candles": candles})
    df = hds.fetch_htf_candles("USDJPY=X", "H4", 3, client=cli, use_cache=False)
    assert df is None


# ─── failure modes ───────────────────────────────────────────────────

def test_unconfigured_client_returns_none():
    cli = FakeOandaClient(configured=False)
    df = hds.fetch_htf_candles("USDJPY=X", "H4", 4, client=cli, use_cache=False)
    assert df is None


def test_oanda_error_returns_none():
    cli = FakeOandaClient(success=False, payload={"error": 403})
    df = hds.fetch_htf_candles("USDJPY=X", "H4", 4, client=cli, use_cache=False)
    assert df is None


def test_oanda_exception_returns_none():
    cli = FakeOandaClient(raise_exc=RuntimeError("network down"))
    df = hds.fetch_htf_candles("USDJPY=X", "H4", 4, client=cli, use_cache=False)
    assert df is None


def test_invalid_granularity_returns_none():
    cli = FakeOandaClient(payload={"candles": _sample_candles(4)})
    df = hds.fetch_htf_candles("USDJPY=X", "INVALID", 4, client=cli, use_cache=False)
    assert df is None
    # Should not even call OANDA
    assert len(cli.calls) == 0


def test_empty_candles_returns_none():
    cli = FakeOandaClient(payload={"candles": []})
    df = hds.fetch_htf_candles("USDJPY=X", "H4", 4, client=cli, use_cache=False)
    assert df is None


def test_malformed_candle_skipped():
    candles = _sample_candles(3)
    candles.append({"time": "x", "complete": True})  # missing mid
    candles.append({"complete": True, "mid": {"o": "1", "h": "1", "l": "1", "c": "1"}})  # missing time
    cli = FakeOandaClient(payload={"candles": candles})
    df = hds.fetch_htf_candles("USDJPY=X", "H4", 5, client=cli, use_cache=False)
    assert df is not None
    assert len(df) == 3, "only well-formed complete candles included"


# ─── caching ─────────────────────────────────────────────────────────

def test_cache_hit_avoids_second_fetch():
    cli = FakeOandaClient(payload={"candles": _sample_candles(3)})
    df1 = hds.fetch_htf_candles("USDJPY=X", "H4", 3, client=cli, use_cache=True)
    df2 = hds.fetch_htf_candles("USDJPY=X", "H4", 3, client=cli, use_cache=True)
    assert df1 is not None and df2 is not None
    assert len(cli.calls) == 1, "second call should hit cache"
    assert df1 is df2  # same object reference


def test_cache_disabled_calls_every_time():
    cli = FakeOandaClient(payload={"candles": _sample_candles(3)})
    hds.fetch_htf_candles("USDJPY=X", "H4", 3, client=cli, use_cache=False)
    hds.fetch_htf_candles("USDJPY=X", "H4", 3, client=cli, use_cache=False)
    assert len(cli.calls) == 2


def test_cache_stats_reports_entries():
    cli = FakeOandaClient(payload={"candles": _sample_candles(2)})
    hds.fetch_htf_candles("USDJPY=X", "H4", 2, client=cli, use_cache=True)
    stats = hds.cache_stats()
    assert stats["size"] == 1
    assert stats["entries"][0]["instrument"] == "USD_JPY"
    assert stats["entries"][0]["granularity"] == "H4"
    assert stats["entries"][0]["rows"] == 2
