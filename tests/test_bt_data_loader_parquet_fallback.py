from datetime import datetime, timezone

import pandas as pd
import pytest

from modules import data as data_mod


def _sample_ohlcv(n: int = 1200) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
    base = 150.0 + pd.Series(range(n), dtype=float) * 0.002
    return pd.DataFrame(
        {
            "Open": base.values,
            "High": (base + 0.05).values,
            "Low": (base - 0.05).values,
            "Close": (base + 0.01).values,
            "Volume": 100.0,
        },
        index=idx,
    )


def test_fetch_ohlcv_uses_parquet_after_online_failures(monkeypatch, capsys):
    data_mod._data_cache.clear()
    parquet_df = _sample_ohlcv()
    calls = []

    monkeypatch.setenv("MASSIVE_API_KEY", "test")
    monkeypatch.setenv("OANDA_TOKEN", "test")
    monkeypatch.delenv("TWELVEDATA_API_KEY", raising=False)

    def fail_massive(symbol, interval, days):
        calls.append("massive")
        raise RuntimeError("massive down")

    def fail_oanda(symbol, interval, days):
        calls.append("oanda")
        raise RuntimeError("oanda down")

    def fail_yf(symbol, period, interval):
        calls.append("yfinance")
        raise RuntimeError("yf down")

    def fake_parquet(symbol, interval, days, min_bars):
        calls.append("parquet")
        return parquet_df, datetime(2026, 5, 3, 4, 49, tzinfo=timezone.utc)

    monkeypatch.setattr(data_mod, "fetch_ohlcv_massive", fail_massive)
    monkeypatch.setattr(data_mod, "fetch_ohlcv_oanda", fail_oanda)
    monkeypatch.setattr(data_mod, "_fetch_raw", fail_yf)
    monkeypatch.setattr(data_mod, "_load_parquet_cache_fallback", fake_parquet)

    got = data_mod.fetch_ohlcv("USDJPY=X", period="180d", interval="5m")

    assert calls[:4] == ["massive", "oanda", "yfinance", "parquet"]
    assert len(got) == len(parquet_df)
    out = capsys.readouterr().out
    assert "offline-cached data" in out
    assert "USDJPY=X" in out


def test_fetch_ohlcv_raises_clear_error_when_parquet_cache_missing(monkeypatch):
    data_mod._data_cache.clear()

    monkeypatch.setenv("MASSIVE_API_KEY", "test")
    monkeypatch.setenv("OANDA_TOKEN", "test")
    monkeypatch.delenv("TWELVEDATA_API_KEY", raising=False)

    monkeypatch.setattr(
        data_mod,
        "fetch_ohlcv_massive",
        lambda symbol, interval, days: (_ for _ in ()).throw(RuntimeError("massive down")),
    )
    monkeypatch.setattr(
        data_mod,
        "fetch_ohlcv_oanda",
        lambda symbol, interval, days: (_ for _ in ()).throw(RuntimeError("oanda down")),
    )
    monkeypatch.setattr(
        data_mod,
        "_fetch_raw",
        lambda symbol, period, interval: (_ for _ in ()).throw(RuntimeError("yf down")),
    )
    monkeypatch.setattr(
        data_mod,
        "_load_parquet_cache_fallback",
        lambda symbol, interval, days, min_bars: (None, None),
    )

    with pytest.raises(ValueError, match="local parquet cache unavailable"):
        data_mod.fetch_ohlcv("USDJPY=X", period="180d", interval="5m")
