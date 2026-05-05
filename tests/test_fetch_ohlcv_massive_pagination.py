from datetime import datetime, timezone

import pandas as pd

import modules.data as data_mod


def _row(ts, close):
    return {
        "t": int(pd.Timestamp(ts).timestamp() * 1000),
        "o": close - 0.1,
        "h": close + 0.2,
        "l": close - 0.2,
        "c": close,
        "v": 10,
    }


def test_chunked_fetch_full_12_years(monkeypatch):
    chunks = []

    def fake_fetch_chunk(massive_ticker, mult, timespan, chunk_start, chunk_end, api_key):
        chunks.append((chunk_start, chunk_end))
        return [_row(chunk_start, len(chunks))]

    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(data_mod, "_massive_utc_now", lambda: datetime(2026, 5, 5, tzinfo=timezone.utc))
    monkeypatch.setattr(data_mod, "_fetch_chunk", fake_fetch_chunk)
    monkeypatch.setattr(data_mod.time, "sleep", lambda seconds: None)

    df = data_mod.fetch_ohlcv_massive("GBP_JPY", "15m", days=4380)

    assert len(chunks) == 7
    assert chunks[0][0] == datetime(2014, 5, 5, tzinfo=timezone.utc)
    assert chunks[-1][1] == datetime(2026, 5, 5, tzinfo=timezone.utc)
    assert all(start < end for start, end in chunks)
    assert all(chunks[i][1] == chunks[i + 1][0] for i in range(len(chunks) - 1))
    assert list(df["Close"]) == list(range(1, 8))
    assert df.index.is_monotonic_increasing


def test_chunk_rate_limit_sleep_called(monkeypatch):
    sleeps = []

    def fake_fetch_chunk(massive_ticker, mult, timespan, chunk_start, chunk_end, api_key):
        return [_row(chunk_start, 1.0)]

    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(data_mod, "_massive_utc_now", lambda: datetime(2026, 5, 5, tzinfo=timezone.utc))
    monkeypatch.setattr(data_mod, "_fetch_chunk", fake_fetch_chunk)
    monkeypatch.setattr(data_mod.time, "sleep", lambda seconds: sleeps.append(seconds))

    data_mod.fetch_ohlcv_massive("USD_JPY", "15m", days=4380)

    assert sleeps == [0.5] * 6


def test_chunk_dedup_overlapping_boundaries(monkeypatch):
    boundary = pd.Timestamp("2024-05-04T00:00:00Z")

    def fake_fetch_chunk(massive_ticker, mult, timespan, chunk_start, chunk_end, api_key):
        if chunk_start.year == 2022:
            return [_row("2024-05-03T23:45:00Z", 1.0), _row(boundary, 2.0)]
        return [_row(boundary, 3.0), _row("2024-05-04T00:15:00Z", 4.0)]

    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(data_mod, "_massive_utc_now", lambda: datetime(2024, 5, 5, tzinfo=timezone.utc))
    monkeypatch.setattr(data_mod, "_fetch_chunk", fake_fetch_chunk)
    monkeypatch.setattr(data_mod.time, "sleep", lambda seconds: None)

    df = data_mod.fetch_ohlcv_massive("USD_JPY", "15m", days=730)

    assert df.index.tolist() == [
        pd.Timestamp("2024-05-03T23:45:00Z"),
        boundary,
        pd.Timestamp("2024-05-04T00:15:00Z"),
    ]
    assert df.loc[boundary, "Close"] == 3.0
