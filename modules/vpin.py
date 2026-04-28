"""VPIN — Volume-synchronized Probability of Informed Trading.

Easley-O'Hara-de Prado 2012 framework. BVC (Bulk Volume Classification) で
tick data 不要、bar 単位 OHLCV から実装可能。

Pipeline:
  1. BVC: each bar's volume → buy_vol / sell_vol split using price-change z-score
  2. Equal-volume buckets: aggregate into buckets of constant total volume
  3. VPIN: rolling |buy_imbalance| / total_volume over N buckets

VPIN > 0.7 → toxic flow → forecast volatility / reversal probability rises.
"""
from __future__ import annotations
from typing import List, Optional

import numpy as np
import pandas as pd


def bvc_split(df: pd.DataFrame, sigma_window: int = 30) -> pd.DataFrame:
    """Bulk Volume Classification: split each bar's volume into buy/sell.

    Formula (Easley-de Prado):
      z_i = (c_i - c_{i-1}) / σ_returns
      buy_frac_i = Φ(z_i / σ_z)   (normal CDF)
      buy_vol_i = volume_i × buy_frac_i
      sell_vol_i = volume_i × (1 - buy_frac_i)

    Args:
        df: OHLCV DataFrame with Close and Volume columns
        sigma_window: rolling window for return std estimation

    Returns:
        DataFrame with added buy_vol / sell_vol columns
    """
    from scipy.stats import norm

    df = df.copy()
    returns = df["Close"].diff()
    rolling_std = returns.rolling(sigma_window, min_periods=10).std()
    # z-score normalized
    z = returns / rolling_std.replace(0, np.nan)
    z = z.fillna(0)
    # Φ(z) gives buy fraction
    buy_frac = norm.cdf(z)
    df["buy_vol"] = df["Volume"] * buy_frac
    df["sell_vol"] = df["Volume"] * (1 - buy_frac)
    df["buy_imbalance"] = df["buy_vol"] - df["sell_vol"]
    return df


def equal_volume_buckets(df: pd.DataFrame,
                          bucket_size: Optional[float] = None,
                          buckets_per_day: int = 50) -> List[dict]:
    """Aggregate bar-level buy/sell volume into equal-volume buckets.

    Args:
        df: DataFrame with Volume / buy_vol / sell_vol
        bucket_size: target volume per bucket (default = mean_daily_vol / buckets_per_day)
        buckets_per_day: target buckets per session day

    Returns:
        list of bucket dicts: {start_idx, end_idx, total_vol, buy_vol, sell_vol, imbalance}
    """
    if bucket_size is None:
        # Estimate daily volume by grouping by date
        if hasattr(df.index, "date"):
            dates = df.index.date
            unique_dates = list(set(dates))
            if len(unique_dates) > 0:
                vol_by_date = pd.Series(df["Volume"].values).groupby(
                    pd.Series(dates)).sum()
                mean_daily = float(vol_by_date.mean())
                bucket_size = mean_daily / buckets_per_day
            else:
                bucket_size = float(df["Volume"].mean()) * 5
        else:
            bucket_size = float(df["Volume"].mean()) * 5

    if not np.isfinite(bucket_size) or bucket_size <= 0:
        return []

    buckets = []
    cur_vol = 0.0
    cur_buy = 0.0
    cur_sell = 0.0
    cur_start = 0
    for i, row in enumerate(df.itertuples()):
        v = float(getattr(row, "Volume", 0))
        bv = float(getattr(row, "buy_vol", 0))
        sv = float(getattr(row, "sell_vol", 0))
        cur_vol += v
        cur_buy += bv
        cur_sell += sv
        if cur_vol >= bucket_size:
            buckets.append({
                "start_idx": cur_start,
                "end_idx": i,
                "end_ts": df.index[i],
                "total_vol": cur_vol,
                "buy_vol": cur_buy,
                "sell_vol": cur_sell,
                "imbalance": abs(cur_buy - cur_sell),
                "imbalance_ratio": (abs(cur_buy - cur_sell) / cur_vol) if cur_vol > 0 else 0,
            })
            cur_vol = 0.0
            cur_buy = 0.0
            cur_sell = 0.0
            cur_start = i + 1
    return buckets


def vpin_series(buckets: List[dict], window: int = 50) -> pd.Series:
    """Rolling VPIN over `window` buckets.

    VPIN_t = (1/N) × Σ |buy_vol_i - sell_vol_i| / total_vol_i
    Returns Series indexed by bucket end timestamps.
    """
    if not buckets:
        return pd.Series(dtype=float)
    timestamps = [b["end_ts"] for b in buckets]
    ratios = [b["imbalance_ratio"] for b in buckets]
    s = pd.Series(ratios, index=timestamps)
    return s.rolling(window, min_periods=max(10, window // 2)).mean()


def compute_vpin(df: pd.DataFrame,
                  bucket_per_day: int = 50,
                  window: int = 50,
                  sigma_window: int = 30) -> pd.Series:
    """Convenience wrapper: BVC → buckets → VPIN series."""
    df_bvc = bvc_split(df, sigma_window=sigma_window)
    buckets = equal_volume_buckets(df_bvc, buckets_per_day=bucket_per_day)
    return vpin_series(buckets, window=window)
