from datetime import datetime, timezone

import pandas as pd

from modules import data as data_mod


def _sample_ohlcv(n: int = 1000) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
    base = pd.Series(range(n), dtype=float) * 0.001 + 150.0
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


def test_bt_mode_uses_local_massive_parquet_first(monkeypatch):
    data_mod._data_cache.clear()
    calls = []
    parquet_df = _sample_ohlcv()

    monkeypatch.setenv("BT_MODE", "1")
    monkeypatch.setenv("MASSIVE_API_KEY", "test")
    monkeypatch.setenv("OANDA_TOKEN", "test")
    monkeypatch.setenv("TWELVEDATA_API_KEY", "test")

    def fake_parquet(symbol, interval, days, min_bars):
        calls.append("parquet")
        return parquet_df, datetime(2026, 5, 5, tzinfo=timezone.utc)

    monkeypatch.setattr(data_mod, "_load_parquet_cache_fallback", fake_parquet)
    monkeypatch.setattr(
        data_mod,
        "fetch_ohlcv_massive",
        lambda symbol, interval, days: calls.append("massive") or _sample_ohlcv(),
    )
    monkeypatch.setattr(
        data_mod,
        "fetch_ohlcv_oanda",
        lambda symbol, interval, days: calls.append("oanda") or _sample_ohlcv(),
    )
    monkeypatch.setattr(
        data_mod,
        "fetch_ohlcv_twelvedata",
        lambda symbol, interval: calls.append("twelvedata") or _sample_ohlcv(),
    )
    monkeypatch.setattr(
        data_mod,
        "_fetch_raw",
        lambda symbol, period, interval: calls.append("yfinance") or _sample_ohlcv(),
    )

    got = data_mod.fetch_ohlcv("USDJPY=X", period="10d", interval="5m")

    assert calls == ["parquet"]
    assert len(got) == len(parquet_df)
    assert data_mod._last_data_source["5m"] == "massive-parquet"


def test_bt_mode_off_uses_live_first(monkeypatch):
    data_mod._data_cache.clear()
    calls = []

    monkeypatch.setenv("BT_MODE", "0")
    monkeypatch.setenv("MASSIVE_API_KEY", "test")
    monkeypatch.setenv("OANDA_TOKEN", "test")
    monkeypatch.setenv("TWELVEDATA_API_KEY", "test")

    monkeypatch.setattr(
        data_mod,
        "_load_parquet_cache_fallback",
        lambda symbol, interval, days, min_bars: calls.append("parquet") or (None, None),
    )
    monkeypatch.setattr(
        data_mod,
        "fetch_ohlcv_massive",
        lambda symbol, interval, days: calls.append("massive") or _sample_ohlcv(),
    )
    monkeypatch.setattr(
        data_mod,
        "fetch_ohlcv_oanda",
        lambda symbol, interval, days: calls.append("oanda") or _sample_ohlcv(),
    )
    monkeypatch.setattr(
        data_mod,
        "_fetch_raw",
        lambda symbol, period, interval: calls.append("yfinance") or _sample_ohlcv(),
    )

    got = data_mod.fetch_ohlcv("USDJPY=X", period="10d", interval="5m")

    assert calls == ["massive"]
    assert len(got) == 1000
    assert data_mod._last_data_source["5m"] == "massive"


def test_bt_mode_yahoo_fallback_only_last(monkeypatch):
    data_mod._data_cache.clear()
    calls = []
    yf_df = _sample_ohlcv()

    monkeypatch.setenv("BT_MODE", "1")
    monkeypatch.setenv("MASSIVE_API_KEY", "test")
    monkeypatch.setenv("OANDA_TOKEN", "test")
    monkeypatch.setenv("TWELVEDATA_API_KEY", "test")

    def missing_parquet(symbol, interval, days, min_bars):
        calls.append("parquet")
        return None, None

    def fail_massive(symbol, interval, days):
        calls.append("massive")
        raise RuntimeError("massive down")

    def fail_oanda(symbol, interval, days):
        calls.append("oanda")
        raise RuntimeError("oanda down")

    def fail_twelvedata(symbol, interval):
        calls.append("twelvedata")
        raise RuntimeError("td down")

    def fake_yfinance(symbol, period, interval):
        calls.append("yfinance")
        return yf_df

    monkeypatch.setattr(data_mod, "_load_parquet_cache_fallback", missing_parquet)
    monkeypatch.setattr(data_mod, "fetch_ohlcv_massive", fail_massive)
    monkeypatch.setattr(data_mod, "fetch_ohlcv_oanda", fail_oanda)
    monkeypatch.setattr(data_mod, "fetch_ohlcv_twelvedata", fail_twelvedata)
    monkeypatch.setattr(data_mod, "_fetch_raw", fake_yfinance)

    got = data_mod.fetch_ohlcv("USDJPY=X", period="10d", interval="5m")

    assert calls == ["parquet", "massive", "oanda", "twelvedata", "yfinance"]
    assert len(got) == len(yf_df)
    assert data_mod._last_data_source["5m"] == "yfinance"
