"""S/R Detector — KDE-based level detection + obviousness scoring.

KDE で価格密度のピークを抽出し、touch_count / round_number 近接 / 鮮度 で
"retail にとっての見えやすさ"（obviousness）を 0-1 でスコア化する。

既存の modules.indicators.find_sr_levels_weighted（pivot + tolerance）を
補完する位置付け。fib_reversal 等の既存戦略は計算式フィボや pivot ベース
だが、こちらは "実際にタッチが集中した場所" を density で抽出する。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde


@dataclass
class SRLevel:
    """S/R 水平線 1 本の構造化表現。"""
    price: float
    touch_count: int        # ε許容内でこの level をタッチした bar 数
    age_bars: int           # 最初のタッチからの経過 bar 数
    obviousness: float      # 0-1: retail から見て "明らか" な度合い
    kde_density: float      # KDE の生密度（peak 強度）


def _pip_size(instrument: str) -> float:
    """Pip size by instrument convention (JPY pairs: 0.01, others: 0.0001)."""
    if "JPY" in instrument.upper():
        return 0.01
    return 0.0001


def kde_cluster_levels(
    df: pd.DataFrame,
    bandwidth: float = 0.05,
    grid_density: int = 500,
    min_density: float = 1.0,
) -> List[float]:
    """Return KDE density peaks over swing-relevant prices."""
    if len(df) < 5:
        return []

    prices = np.concatenate([df["High"].values, df["Low"].values])
    prices = prices[~np.isnan(prices)]
    if len(prices) < 3:
        return []

    p_min, p_max = float(prices.min()), float(prices.max())
    if p_max - p_min < 1e-9:
        return [float(prices[0])]

    try:
        kde = gaussian_kde(prices, bw_method=bandwidth / (p_max - p_min))
    except (np.linalg.LinAlgError, ValueError):
        return []

    grid = np.linspace(p_min, p_max, grid_density)
    densities = kde(grid)

    peaks = []
    for i in range(1, len(densities) - 1):
        if densities[i] > densities[i - 1] and densities[i] > densities[i + 1]:
            if densities[i] >= min_density:
                peaks.append((float(grid[i]), float(densities[i])))

    if not peaks:
        gmax_idx = int(np.argmax(densities))
        peaks = [(float(grid[gmax_idx]), float(densities[gmax_idx]))]

    peaks.sort(key=lambda x: -x[1])
    return [p[0] for p in peaks]


def score_obviousness(
    price: float,
    touch_count: int,
    age_bars: int,
    pip_size: float = 0.01,
) -> float:
    """0-1 score: how "obvious" this level is to retail traders.

    成分:
      - round-number proximity (40%)
      - touch_count (40%): log scale
      - age (20%): bell shape
    """
    pip_units = price / pip_size
    dist_to_100 = min(pip_units % 100, 100 - (pip_units % 100))
    dist_to_50 = min(pip_units % 50, 50 - (pip_units % 50))
    round_score = max(0.0, 1.0 - dist_to_50 / 25.0)
    if dist_to_100 < 5:
        round_score = min(1.0, round_score + 0.2)

    touch_score = min(1.0, np.log1p(max(0, touch_count - 1)) / np.log1p(9))

    age_score = float(np.exp(-((age_bars - 200) ** 2) / (2 * 200 * 200)))

    return float(0.40 * round_score + 0.40 * touch_score + 0.20 * age_score)


def _count_touches(df: pd.DataFrame, level: float, tolerance: float) -> int:
    low = df["Low"].values
    high = df["High"].values
    return int(np.sum((low <= level + tolerance) & (high >= level - tolerance)))


def _first_touch_bar(df: pd.DataFrame, level: float, tolerance: float) -> int:
    low = df["Low"].values
    high = df["High"].values
    hits = (low <= level + tolerance) & (high >= level - tolerance)
    if not hits.any():
        return 0
    first_idx = int(np.argmax(hits))
    return len(df) - 1 - first_idx


def detect_sr_levels(
    df: pd.DataFrame,
    instrument: str,
    bandwidth_pips: float = 5.0,
    touch_tolerance_pips: float = 3.0,
    min_touches: int = 2,
    max_levels: int = 20,
    adaptive_bandwidth: bool = True,
) -> List[SRLevel]:
    """Detect S/R levels via KDE clustering, enriched with touch/age/obviousness.

    Adaptive bandwidth: scales with price range to handle wide-range trending
    data (JPY pairs over 365d) without collapsing to a single peak.
    """
    pip = _pip_size(instrument)
    tolerance = touch_tolerance_pips * pip

    if len(df) < 5:
        return []

    if adaptive_bandwidth:
        prices_for_range = np.concatenate([df["High"].values, df["Low"].values])
        prices_for_range = prices_for_range[~np.isnan(prices_for_range)]
        if len(prices_for_range) >= 2:
            data_range = float(prices_for_range.max() - prices_for_range.min())
            range_in_pips = data_range / pip
            adaptive_pips = max(bandwidth_pips, range_in_pips * 0.005)
            bandwidth = adaptive_pips * pip
        else:
            bandwidth = bandwidth_pips * pip
    else:
        bandwidth = bandwidth_pips * pip

    raw_peaks = kde_cluster_levels(df, bandwidth=bandwidth, min_density=0.0)
    if raw_peaks:
        prices_arr = np.concatenate([df["High"].values, df["Low"].values])
        prices_arr = prices_arr[~np.isnan(prices_arr)]
        p_min, p_max = float(prices_arr.min()), float(prices_arr.max())
        span = p_max - p_min if p_max > p_min else 1.0
        try:
            kde_for_filter = gaussian_kde(prices_arr, bw_method=bandwidth / span)
            densities = np.array([float(kde_for_filter(p)[0]) for p in raw_peaks])
            max_d = densities.max() if len(densities) else 0.0
            if max_d > 0:
                keep_mask = densities >= max_d * 0.05
                raw_peaks = [p for p, keep in zip(raw_peaks, keep_mask) if keep]
        except (np.linalg.LinAlgError, ValueError):
            pass
    if not raw_peaks:
        return []

    prices = np.concatenate([df["High"].values, df["Low"].values])
    prices = prices[~np.isnan(prices)]
    p_min, p_max = float(prices.min()), float(prices.max())
    span = p_max - p_min if p_max > p_min else 1.0
    try:
        kde = gaussian_kde(prices, bw_method=bandwidth / span)
    except (np.linalg.LinAlgError, ValueError):
        return []

    levels: List[SRLevel] = []
    for peak_price in raw_peaks:
        touch_count = _count_touches(df, peak_price, tolerance)
        if touch_count < min_touches:
            continue
        age_bars = _first_touch_bar(df, peak_price, tolerance)
        density = float(kde(peak_price)[0])
        obv = score_obviousness(peak_price, touch_count, age_bars, pip_size=pip)
        levels.append(SRLevel(
            price=float(peak_price),
            touch_count=touch_count,
            age_bars=age_bars,
            obviousness=obv,
            kde_density=density,
        ))

    levels.sort(key=lambda lv: -lv.kde_density)
    return levels[:max_levels]
