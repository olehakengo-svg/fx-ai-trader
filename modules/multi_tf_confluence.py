"""Multi-Timeframe Confluence (MTC) — utility for cross-TF MR signal stacking.

仮説: 1 TF で MR signal は 50-55% WR (noise 大)。15m + 1h で同方向 extreme
が同時発生する瞬間は signal-to-noise 比劇的改善。

Utility 形式: 既存戦略の confidence/score にブースト注入 (Bonferroni cost ゼロ)。
"""
from __future__ import annotations
from typing import Optional

import numpy as np
import pandas as pd


def htf_aggregate(df_15m: pd.DataFrame, ratio: int = 4) -> pd.DataFrame:
    """Aggregate 15m → 1h (ratio=4). Returns OHLC of higher TF."""
    if df_15m is None or len(df_15m) < ratio:
        return None
    n_full = len(df_15m) - (len(df_15m) % ratio)
    df = df_15m.iloc[-n_full:].copy()
    df["bucket"] = np.arange(len(df)) // ratio
    agg = df.groupby("bucket").agg({
        "Open": "first", "High": "max", "Low": "min", "Close": "last",
    })
    return agg


def bbpb_at_tf(df: pd.DataFrame, period: int = 20,
               nbdev: float = 2.0) -> float:
    """Compute BB%B for the latest bar at given timeframe."""
    if df is None or len(df) < period:
        return 0.5
    closes = df["Close"].astype(float)
    sma = closes.rolling(period).mean().iloc[-1]
    sd = closes.rolling(period).std().iloc[-1]
    if not np.isfinite(sd) or sd == 0:
        return 0.5
    upper = sma + nbdev * sd
    lower = sma - nbdev * sd
    bbpb = (closes.iloc[-1] - lower) / (upper - lower) if upper > lower else 0.5
    return float(np.clip(bbpb, 0, 1))


def rsi_at_tf(df: pd.DataFrame, period: int = 14) -> float:
    """Compute RSI(14) for latest bar at given timeframe."""
    if df is None or len(df) < period + 1:
        return 50.0
    closes = df["Close"].astype(float)
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-12)
    rsi = 100 - 100 / (1 + rs)
    return float(rsi.iloc[-1])


def confluence_score(df_15m: pd.DataFrame,
                     bbpb_buy_thres: float = 0.30,
                     bbpb_sell_thres: float = 0.70,
                     rsi_buy_thres: float = 35,
                     rsi_sell_thres: float = 65) -> dict:
    """Compute MTC confluence for 15m vs 1h.

    Returns:
      {
        "buy_score": 0-2 (0=none, 1=15m only, 2=both TFs aligned),
        "sell_score": 0-2,
        "bbpb_15m", "bbpb_1h", "rsi_15m", "rsi_1h"
      }
    """
    bbpb_15 = bbpb_at_tf(df_15m, 20)
    rsi_15 = rsi_at_tf(df_15m, 14)
    df_1h = htf_aggregate(df_15m, ratio=4)
    bbpb_1h = bbpb_at_tf(df_1h, 20) if df_1h is not None else 0.5
    rsi_1h = rsi_at_tf(df_1h, 14) if df_1h is not None else 50

    # BUY confluence: BBpb < threshold ∧ RSI < threshold
    buy_15 = bbpb_15 <= bbpb_buy_thres and rsi_15 < rsi_buy_thres
    buy_1h = bbpb_1h <= bbpb_buy_thres and rsi_1h < rsi_buy_thres
    buy_score = (1 if buy_15 else 0) + (1 if buy_1h else 0)

    sell_15 = bbpb_15 >= bbpb_sell_thres and rsi_15 > rsi_sell_thres
    sell_1h = bbpb_1h >= bbpb_sell_thres and rsi_1h > rsi_sell_thres
    sell_score = (1 if sell_15 else 0) + (1 if sell_1h else 0)

    return {
        "buy_score": buy_score, "sell_score": sell_score,
        "bbpb_15m": round(bbpb_15, 3), "bbpb_1h": round(bbpb_1h, 3),
        "rsi_15m": round(rsi_15, 1), "rsi_1h": round(rsi_1h, 1),
    }
