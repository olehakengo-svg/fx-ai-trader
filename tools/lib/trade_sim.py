"""Shared trade-outcome simulation — DRY 化された SL/TP + friction P&L.

Phase 1-6 の各 audit (vsg/sr/vdr/mqe/cpd_refine) で重複実装されていた
hypothetical trade simulation を共通化。

Usage:
    from tools.lib.trade_sim import simulate_cell_trades, friction_pip

    trades = simulate_cell_trades(
        df, signals_idx, direction="BUY",
        sl_atr=1.0, tp_atr=1.5, max_hold_bars=8,
        pair="USD_JPY"
    )
    # trades = list of {entry, exit, outcome, pnl_gross, pnl_net, hold_bars}

Look-ahead 防止:
- Entry: bar(t).Open (signals_idx は bar(t-1) で feature 計算済の前提)
- SL/TP: ATR(t-1) を使用 (bar(t-1) の ATR 値)
- Exit: bar(t+1) 以降の High/Low で hit 判定
"""
from __future__ import annotations
from typing import List, Optional
import numpy as np
import pandas as pd


def pip_size(pair: str) -> float:
    """Pip size: 0.01 for JPY, 0.0001 for non-JPY."""
    return 0.01 if "JPY" in pair.upper() else 0.0001


def session_for_utc_hour(hour: int) -> str:
    """UTC hour → session bucket (matches friction_model_v2 conventions)."""
    if 0 <= hour < 7:
        return "tokyo"
    elif 7 <= hour < 13:
        return "london"
    elif 13 <= hour < 21:
        return "ny"
    else:
        return "overnight"


def friction_pip_default(pair: str, session: str = "default") -> float:
    """Conservative roundtrip friction in pips. Falls back if friction_model_v2
    unavailable or returns invalid value."""
    try:
        from modules.friction_model_v2 import friction_for
        result = friction_for(pair, mode="DT", session=session)
        if result and "adjusted_rt_pips" in result:
            v = float(result["adjusted_rt_pips"])
            if 0 < v < 20:
                return v
    except Exception:
        pass
    # Fallback defaults
    if "JPY" in pair.upper():
        return 1.5
    return 1.5


def simulate_single_trade(
    df: pd.DataFrame,
    entry_idx: int,
    direction: str,
    atr_at_signal: float,
    sl_atr_mult: float = 1.0,
    tp_atr_mult: float = 1.5,
    max_hold_bars: int = 8,
    pair: str = "USD_JPY",
    apply_friction: bool = True,
) -> Optional[dict]:
    """Simulate one trade with SL/TP exit logic.

    Args:
        df: OHLCV DataFrame with Open/High/Low/Close columns
        entry_idx: Index in df where SIGNAL was generated. Entry price = df[entry_idx+1].Open.
        direction: "BUY" or "SELL"
        atr_at_signal: ATR value at bar(entry_idx) — used for SL/TP distance
        sl_atr_mult: SL distance = sl_atr_mult × ATR
        tp_atr_mult: TP distance = tp_atr_mult × ATR
        max_hold_bars: Max bars to hold before timeout exit
        pair: Currency pair for friction calc
        apply_friction: Subtract friction from P&L

    Returns:
        dict {entry, exit, outcome, pnl_gross_pip, pnl_net_pip, hold_bars}
        or None if entry not feasible (e.g., end of data)
    """
    if entry_idx + 1 >= len(df):
        return None
    if not (np.isfinite(atr_at_signal) and atr_at_signal > 0):
        return None

    entry_bar = df.iloc[entry_idx + 1]
    entry_price = float(entry_bar["Open"])
    pip = pip_size(pair)

    if direction == "BUY":
        sl_price = entry_price - sl_atr_mult * atr_at_signal
        tp_price = entry_price + tp_atr_mult * atr_at_signal
    else:
        sl_price = entry_price + sl_atr_mult * atr_at_signal
        tp_price = entry_price - tp_atr_mult * atr_at_signal

    # Walk forward for SL/TP hit
    outcome = "TIMEOUT"
    exit_price = None
    exit_idx = None
    end_idx = min(entry_idx + 1 + max_hold_bars, len(df) - 1)
    for j in range(entry_idx + 1, end_idx + 1):
        bar = df.iloc[j]
        bh = float(bar["High"])
        bl = float(bar["Low"])
        if direction == "BUY":
            # Conservative: if both could hit in same bar, assume SL hit first
            if bl <= sl_price:
                outcome, exit_price, exit_idx = "SL", sl_price, j
                break
            if bh >= tp_price:
                outcome, exit_price, exit_idx = "TP", tp_price, j
                break
        else:
            if bh >= sl_price:
                outcome, exit_price, exit_idx = "SL", sl_price, j
                break
            if bl <= tp_price:
                outcome, exit_price, exit_idx = "TP", tp_price, j
                break

    if exit_price is None:
        # Timeout — exit at end_idx Close
        exit_price = float(df.iloc[end_idx]["Close"])
        exit_idx = end_idx

    if direction == "BUY":
        pnl_gross_pip = (exit_price - entry_price) / pip
    else:
        pnl_gross_pip = (entry_price - exit_price) / pip

    if apply_friction:
        # Determine session at entry bar
        ts = df.index[entry_idx + 1]
        sess = session_for_utc_hour(ts.hour) if hasattr(ts, "hour") else "default"
        friction = friction_pip_default(pair, session=sess)
        pnl_net_pip = pnl_gross_pip - friction
    else:
        friction = 0.0
        pnl_net_pip = pnl_gross_pip

    return {
        "entry_idx": entry_idx,
        "exit_idx": exit_idx,
        "entry_ts": df.index[entry_idx + 1],
        "exit_ts": df.index[exit_idx],
        "entry_price": entry_price,
        "exit_price": exit_price,
        "direction": direction,
        "outcome": outcome,
        "pnl_gross_pip": float(pnl_gross_pip),
        "pnl_net_pip": float(pnl_net_pip),
        "friction_pip": float(friction),
        "hold_bars": exit_idx - entry_idx,
    }


def simulate_cell_trades(
    df: pd.DataFrame,
    signal_indices: list,
    direction: str,
    atr_series: pd.Series,
    sl_atr_mult: float = 1.0,
    tp_atr_mult: float = 1.5,
    max_hold_bars: int = 8,
    pair: str = "USD_JPY",
    apply_friction: bool = True,
    dedup: bool = True,
) -> List[dict]:
    """Vectorized simulation for a list of signal bars.

    Args:
        df: OHLCV DataFrame with DatetimeIndex
        signal_indices: list of bar indices where signal generated
        direction: "BUY" / "SELL"
        atr_series: ATR(14) series aligned with df
        ...: see simulate_single_trade

        dedup: if True, dedupe so each bar can have at most 1 entry
               (skips signals while a prior trade is still open)

    Returns:
        list of trade dicts (one per signal that resulted in a trade)
    """
    trades = []
    last_exit_idx = -1
    sorted_indices = sorted(signal_indices)
    for idx in sorted_indices:
        if dedup and idx <= last_exit_idx:
            continue  # skip overlapping signals
        if idx >= len(df) or idx >= len(atr_series):
            continue
        atr = float(atr_series.iloc[idx])
        t = simulate_single_trade(
            df, idx, direction, atr,
            sl_atr_mult=sl_atr_mult, tp_atr_mult=tp_atr_mult,
            max_hold_bars=max_hold_bars, pair=pair,
            apply_friction=apply_friction,
        )
        if t is not None:
            trades.append(t)
            if dedup:
                last_exit_idx = t["exit_idx"]
    return trades


def aggregate_trade_stats(trades: List[dict]) -> dict:
    """Compute WR/EV/PF/Sharpe/Kelly from trade list."""
    if not trades:
        return {
            "n_trades": 0, "wr": 0.0, "ev_net_pip": 0.0,
            "pf": None, "kelly": None, "sharpe_per_event": 0.0,
        }
    pnls = np.array([t["pnl_net_pip"] for t in trades])
    n = len(pnls)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    n_wins = int((pnls > 0).sum())
    wr = n_wins / n if n > 0 else 0.0
    ev = float(pnls.mean())
    std = float(pnls.std()) if n > 1 else 0.0
    sharpe_pe = ev / std if std > 0 else 0.0
    pf = (sum(wins) / abs(sum(losses))) if len(losses) > 0 and sum(losses) != 0 else None
    if len(wins) > 0 and len(losses) > 0:
        b = float(np.mean(wins) / abs(np.mean(losses)))
        kelly = (wr * b - (1 - wr)) / b if b > 0 else None
    else:
        kelly = None
    return {
        "n_trades": n,
        "wr": round(wr, 4),
        "n_wins": n_wins,
        "ev_net_pip": round(ev, 3),
        "std_pip": round(std, 3),
        "pf": round(pf, 3) if pf is not None else None,
        "kelly": round(kelly, 4) if kelly is not None else None,
        "sharpe_per_event": round(sharpe_pe, 4),
        "max_pip": round(float(pnls.max()), 2),
        "min_pip": round(float(pnls.min()), 2),
    }
