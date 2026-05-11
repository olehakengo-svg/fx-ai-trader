"""confluence_scalp: simplified port from fx-ai-trader.

Original W4-EDA verdict: LIVE.
Original source: /Users/jg-n-012/test/fx-ai-trader/strategies/scalp/confluence_scalp.py

Entry rule (Phase 1 simplification):
  - long  if close > EMA20 > EMA50 AND RSI(14) > 50
  - short if close < EMA20 < EMA50 AND RSI(14) < 50
  - SL = entry - 1.5 * ATR(14)  (long)  / entry + 1.5 * ATR(14)  (short)
  - TP = entry + 2.0 * ATR(14)  (long)  / entry - 2.0 * ATR(14)  (short)
  - One position at a time (no new signal while a trade is open).

Differences from fx-ai-trader source:
  - Dropped: MACD, ADX, Stoch, BB%B, CHoCH/MSB detection, session gate
             (UTC 12-17), MFE guard (ATR/spread ratio), HTF hard block,
             v2 dedup cache.
  - Trend: EMA9/21 in original → EMA20/50 here (cleaner trend signal
    on M5 data for indices).
  - Oscillator: RSI5 extremes (original) → RSI(14) midline cross here.
  - Signal logic: Triple Confluence (A+B+C) → dual confluence (trend+RSI).
  - SL/TP multiples: ATR7 × 1.2/2.5 (original) → ATR14 × 1.5/2.0 here.
  - This is intentional Phase 1 scope. Phase 2+ may re-port the full
    indicator stack.
"""
from __future__ import annotations

import pandas as pd

from cfd_trader.strategies import catalog


DEFAULT_PARAMS: dict = {
    "ema_fast": 20,
    "ema_slow": 50,
    "rsi_period": 14,
    "atr_period": 14,
    "sl_atr_mult": 1.5,
    "tp_atr_mult": 2.0,
    "max_holding_bars": 200,
    "units": 1,
}


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-9)
    return 100.0 - 100.0 / (1.0 + rs)


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def generate_trades(candles: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Generate trades from candle data using simplified confluence logic.

    Parameters
    ----------
    candles:
        DataFrame with columns: time, open, high, low, close, volume, complete.
    params:
        Override dict for DEFAULT_PARAMS keys.

    Returns
    -------
    DataFrame with columns:
        entry_time, exit_time, side, entry_price, exit_price, units.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    cols = ["entry_time", "exit_time", "side", "entry_price", "exit_price", "units"]
    min_bars = max(p["ema_slow"], p["atr_period"]) + 5
    if len(candles) < min_bars:
        return pd.DataFrame(columns=cols)

    df = candles.reset_index(drop=True).copy()
    df["ema_fast"] = _ema(df["close"], p["ema_fast"])
    df["ema_slow"] = _ema(df["close"], p["ema_slow"])
    df["rsi"] = _rsi(df["close"], p["rsi_period"])
    df["atr"] = _atr(df, p["atr_period"])

    trades: list[dict] = []
    # Start after indicators have enough warm-up bars
    i = max(p["ema_slow"], p["atr_period"]) + 1
    n = len(df)

    while i < n - 1:
        row = df.iloc[i]
        side: str | None = None

        if (row["close"] > row["ema_fast"] > row["ema_slow"]
                and row["rsi"] > 50.0):
            side = "long"
        elif (row["close"] < row["ema_fast"] < row["ema_slow"]
                and row["rsi"] < 50.0):
            side = "short"

        if side is None:
            i += 1
            continue

        atr = float(row["atr"])
        if atr <= 0.0:
            i += 1
            continue

        # Enter at next bar's open
        entry_idx = i + 1
        if entry_idx >= n:
            break
        entry = df.iloc[entry_idx]
        entry_price = float(entry["open"])

        if side == "long":
            sl = entry_price - p["sl_atr_mult"] * atr
            tp = entry_price + p["tp_atr_mult"] * atr
        else:
            sl = entry_price + p["sl_atr_mult"] * atr
            tp = entry_price - p["tp_atr_mult"] * atr

        # Walk forward to find first SL/TP touch.
        # Tie-break (both touched same bar): use SL (conservative).
        exit_price: float | None = None
        exit_time = entry["time"]
        last_idx = min(entry_idx + p["max_holding_bars"], n - 1)

        for j in range(entry_idx, last_idx + 1):
            bar = df.iloc[j]
            hi = float(bar["high"])
            lo = float(bar["low"])
            if side == "long":
                if lo <= sl:  # SL hit first (conservative tie-break)
                    exit_price = sl
                    exit_time = bar["time"]
                    break
                if hi >= tp:
                    exit_price = tp
                    exit_time = bar["time"]
                    break
            else:  # short
                if hi >= sl:  # SL hit first (conservative tie-break)
                    exit_price = sl
                    exit_time = bar["time"]
                    break
                if lo <= tp:
                    exit_price = tp
                    exit_time = bar["time"]
                    break

        if exit_price is None:
            # Max holding period reached — exit at close
            exit_bar = df.iloc[last_idx]
            exit_price = float(exit_bar["close"])
            exit_time = exit_bar["time"]
            jump_to = last_idx + 1
        else:
            jump_to = j + 1  # one bar after exit

        trades.append(
            {
                "entry_time": entry["time"],
                "exit_time": exit_time,
                "side": side,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "units": p["units"],
            }
        )
        # One position at a time: advance past exit before seeking next signal
        i = jump_to

    return pd.DataFrame(trades, columns=cols)


# Register into the global strategy catalog on import.
catalog.register("confluence_scalp", generate_trades)
