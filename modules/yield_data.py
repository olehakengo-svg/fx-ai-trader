"""Yield Data fetcher — Treasury futures (ZN = 10Y T-Note) intraday OHLC.

YDP (Yield Differential Pair Move) 戦略の data layer.
ZN=F price ↑ ⟺ US10Y yield ↓ (mechanical inverse) — yield_change の proxy として使う。

データソース: yfinance (free) — Yahoo Finance Futures
ZN=F の取引時間: CBOT 23:00-04:00 (Tokyo time, Sun-Fri)
              Asia hours は薄い、London/NY hours で liquidity 集中

Usage:
    from modules.yield_data import fetch_zn_intraday
    df = fetch_zn_intraday(interval="15m", days=30)
    # df has Open/High/Low/Close/Volume + DatetimeIndex (UTC)
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

_CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "cache" / "yield"


def fetch_zn_intraday(
    interval: str = "15m",
    days: int = 30,
    use_cache: bool = True,
    cache_max_age_hours: int = 1,
) -> pd.DataFrame:
    """Fetch ZN=F (10Y T-Note futures) OHLC bars.

    Args:
        interval: "1m", "5m", "15m", "30m", "1h", "1d"
        days: lookback days
        use_cache: read parquet cache if available and fresh
        cache_max_age_hours: cache freshness threshold

    Returns:
        DataFrame with columns Open/High/Low/Close/Volume, DatetimeIndex UTC.
    """
    cache_path = _CACHE_DIR / f"ZN_F_{interval}.parquet"
    if use_cache and cache_path.exists():
        age_h = (pd.Timestamp.now() - pd.Timestamp(cache_path.stat().st_mtime, unit="s")
                 ).total_seconds() / 3600
        if age_h < cache_max_age_hours:
            df = pd.read_parquet(cache_path)
            cutoff = pd.Timestamp.now(tz=df.index.tz) - pd.Timedelta(days=days)
            return df[df.index >= cutoff]

    import yfinance as yf

    # yfinance の period mapping (intraday は最大 60d; 15m は ~60d)
    if days <= 7:
        period = "5d" if days >= 5 else "1d"
    elif days <= 30:
        period = "1mo"
    elif days <= 60:
        period = "2mo"
    else:
        period = "60d"  # intraday max for 15m

    df = yf.download("ZN=F", period=period, interval=interval, progress=False)
    if df is None or df.empty:
        raise RuntimeError(f"yfinance returned no data for ZN=F {interval} {period}")

    # yfinance returns MultiIndex columns since 0.2.x; flatten
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

    # Ensure UTC tz
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    # Cache
    if use_cache:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path)

    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    return df[df.index >= cutoff]


def yield_change_pct(df_zn: pd.DataFrame, lookback_bars: int = 1) -> pd.Series:
    """Convert ZN price change to approximate yield change (pct).

    Approximation: Δyield_pct ≈ -Δprice_pct × (modified_duration)
    For 10Y T-Note: modified duration ≈ 8.5 years
    So Δyield (in %) ≈ -Δprice/price × (1/duration) × 100

    But for our directional purpose, we just need the SIGN inverted:
    yield_change > 0 ⟺ price_change < 0
    """
    price_change = df_zn["Close"].pct_change(lookback_bars)
    # Inverse sign: yield up = ZN down
    return -price_change


def yield_change_abs(df_zn: pd.DataFrame, lookback_bars: int = 1) -> pd.Series:
    """Approximate absolute yield change in bps.

    For 10Y T-Note: 1% price ≈ 12 bps yield change (1/8.5 years)
    So Δyield_bps ≈ -Δprice/price × 12
    """
    price_change = df_zn["Close"].pct_change(lookback_bars)
    return -price_change * 12 * 100  # in bps
