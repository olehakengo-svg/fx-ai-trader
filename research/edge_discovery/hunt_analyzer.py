"""Hunt Pattern Analyzer — stop-hunt event detection and statistics.

Hunt 定義:
  level±ε 突破（wick が level を越える）
  ∧ 同 bar 内に level 内側でクローズ（突破方向と逆にクローズ）
  ∧ wick excursion > k × ATR
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Literal

import numpy as np
import pandas as pd

from modules.sr_detector import SRLevel


Side = Literal["resistance", "support"]


@dataclass
class HuntStat:
    level_price: float
    side: Side
    n_hunts: int
    wick_excursion_dist: Dict[str, float] = field(default_factory=dict)
    post_hunt_reversal_wr: float = 0.0
    avg_bars_to_reversal: float = 0.0
    n_reversal_success: int = 0
    n_reversal_fail: int = 0


def is_hunt_bar(
    bar: dict,
    level: float,
    atr: float,
    side: Side,
    k_atr: float = 1.0,
) -> bool:
    high = float(bar["High"])
    low = float(bar["Low"])
    close = float(bar["Close"])
    threshold = k_atr * atr

    if side == "resistance":
        wick_excursion = high - level
        return (high > level
                and close < level
                and wick_excursion > threshold)
    else:
        wick_excursion = level - low
        return (low < level
                and close > level
                and wick_excursion > threshold)


def detect_hunt_events(
    df: pd.DataFrame,
    level: float,
    side: Side,
    k_atr: float = 1.0,
    atr_col: str = "atr",
) -> List[dict]:
    if atr_col not in df.columns:
        raise ValueError(f"df missing required column '{atr_col}'")

    events = []
    for i in range(len(df)):
        bar = df.iloc[i]
        atr = float(bar[atr_col])
        if not np.isfinite(atr) or atr <= 0:
            continue
        if not is_hunt_bar(bar, level, atr, side, k_atr=k_atr):
            continue
        if side == "resistance":
            excursion = float(bar["High"]) - level
        else:
            excursion = level - float(bar["Low"])
        events.append({
            "bar_idx": i,
            "timestamp": df.index[i],
            "wick_excursion": excursion,
            "atr": atr,
            "excursion_atr_ratio": excursion / atr if atr > 0 else 0.0,
        })
    return events


def _check_reversal(
    df: pd.DataFrame,
    hunt_idx: int,
    level: float,
    side: Side,
    lookahead: int,
    reversal_atr_threshold: float = 1.0,
    atr_col: str = "atr",
) -> tuple[bool, int]:
    end_idx = min(hunt_idx + lookahead, len(df) - 1)
    atr = float(df.iloc[hunt_idx][atr_col])
    if not np.isfinite(atr) or atr <= 0:
        return False, lookahead + 1
    threshold = reversal_atr_threshold * atr

    for j in range(hunt_idx + 1, end_idx + 1):
        close = float(df.iloc[j]["Close"])
        if side == "resistance":
            if close < level - threshold:
                return True, j - hunt_idx
        else:
            if close > level + threshold:
                return True, j - hunt_idx
    return False, lookahead + 1


def analyze_hunts_for_level(
    df: pd.DataFrame,
    level: SRLevel,
    side: Side,
    k_atr: float = 1.0,
    reversal_lookahead: int = 5,
    reversal_atr_threshold: float = 1.0,
    atr_col: str = "atr",
) -> HuntStat:
    events = detect_hunt_events(df, level.price, side, k_atr=k_atr,
                                atr_col=atr_col)
    stat = HuntStat(level_price=level.price, side=side, n_hunts=len(events))

    if not events:
        return stat

    excursions = np.array([e["wick_excursion"] for e in events])
    stat.wick_excursion_dist = {
        "p50": float(np.percentile(excursions, 50)),
        "p90": float(np.percentile(excursions, 90)),
        "p99": float(np.percentile(excursions, 99)),
        "max": float(excursions.max()),
        "mean": float(excursions.mean()),
    }

    success_count = 0
    bars_list = []
    for ev in events:
        success, bars_to = _check_reversal(
            df, ev["bar_idx"], level.price, side,
            lookahead=reversal_lookahead,
            reversal_atr_threshold=reversal_atr_threshold,
            atr_col=atr_col,
        )
        if success:
            success_count += 1
            bars_list.append(bars_to)

    stat.n_reversal_success = success_count
    stat.n_reversal_fail = len(events) - success_count
    stat.post_hunt_reversal_wr = success_count / len(events) if events else 0.0
    stat.avg_bars_to_reversal = float(np.mean(bars_list)) if bars_list else 0.0

    return stat
