"""Regression: phase1b sentiment↔OHLC join must survive datetime-unit mismatch.

Root cause (2026-07-25): the MASSIVE cache refresh rewrote 12/14 pairs' 1h
parquet at millisecond resolution (datetime64[ms, UTC]) while the OANDA-Labs
sentiment history stays at nanosecond resolution (datetime64[ns, UTC]).
pandas>=2.0 ``merge_asof`` refuses to join keys whose datetime units differ
("incompatible merge keys ... datetime64[ms, UTC] and datetime64[ns, UTC]"),
so ``join_sentiment_to_ohlc`` silently produced 0 joined rows for every ms pair
and the daily E1 supply-line verdict collapsed to NULL on 2 of 14 pairs only.

The join must be resolution-agnostic: normalize both merge keys to a common
unit before ``merge_asof``. These tests pin that behavior.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase1b_oanda_contrarian_bt as m  # noqa: E402


def _sentiment_ns(pair: str) -> pd.DataFrame:
    """Sentiment frame with ns-resolution UTC timestamps (as stored on disk)."""
    times = pd.to_datetime(
        ["2026-06-01 00:00", "2026-06-01 04:00", "2026-06-01 08:00", "2026-06-01 12:00"],
        utc=True,
    ).as_unit("ns")
    return pd.DataFrame(
        {
            "pair": pair,
            "time_utc": times,
            "short_pct": [70.0, 65.0, 60.0, 55.0],
            "long_pct": [30.0, 35.0, 40.0, 45.0],
        }
    )


def _h4_ohlc(unit: str) -> pd.DataFrame:
    """H4 OHLC frame indexed at the requested datetime resolution."""
    idx = pd.to_datetime(
        ["2026-06-01 04:00", "2026-06-01 08:00", "2026-06-01 12:00", "2026-06-01 16:00"],
        utc=True,
    ).as_unit(unit)
    idx.name = "bar_close_utc"
    return pd.DataFrame(
        {
            "Open": [1.10, 1.11, 1.12, 1.13],
            "High": [1.11, 1.12, 1.13, 1.14],
            "Low": [1.09, 1.10, 1.11, 1.12],
            "Close": [1.105, 1.115, 1.125, 1.135],
        },
        index=idx,
    )


def test_join_survives_ms_ohlc_vs_ns_sentiment():
    """The failing production case: ms OHLC index + ns sentiment."""
    joined = m.join_sentiment_to_ohlc("EUR_USD", _sentiment_ns("EUR_USD"), _h4_ohlc("ms"))
    assert not joined.empty, "ms/ns merge dropped all rows (dtype-mismatch regression)"
    assert {"short_pct", "long_pct", "Close"}.issubset(joined.columns)
    # backward merge_asof forward-fills the latest known sentiment onto each bar
    assert joined["short_pct"].notna().all()


def test_join_still_works_when_units_already_match():
    """The 2 pairs that worked before (ns/ns) must keep working."""
    joined = m.join_sentiment_to_ohlc("EUR_CHF", _sentiment_ns("EUR_CHF"), _h4_ohlc("ns"))
    assert not joined.empty
    assert joined["short_pct"].notna().all()


@pytest.mark.parametrize("ohlc_unit", ["ms", "us", "ns", "s"])
def test_join_resolution_agnostic(ohlc_unit):
    """Join must not depend on the OHLC parquet's on-disk datetime unit."""
    joined = m.join_sentiment_to_ohlc("USD_JPY", _sentiment_ns("USD_JPY"), _h4_ohlc(ohlc_unit))
    assert not joined.empty, f"unit={ohlc_unit} produced an empty join"
