"""orb_ny_open: NY-open Opening Range Breakout strategy for SPX500_USD M5.

Thesis: The first 30 min of the US cash session (NYSE open 14:30 UTC)
establishes an "opening range." A close outside that range during the
remainder of the session (15:00 - 20:00 UTC) signals a directional breakout.
This is an index-native edge — the session structure (US cash hours) provides
informational content that FX pairs lack.

References: Toby Crabel "Day Trading With Short-Term Price Patterns" (1990);
subsequent academic replications on S&P / index futures.

Entry rule:
  - Compute opening range: high and low of the 6 M5 bars from 14:30:00
    to 14:55:00 UTC (inclusive).
  - From 15:00:00 to 19:55:00 UTC (first bar whose close breaks):
      close > range_high → long signal, enter next bar's open.
      close < range_low  → short signal, enter next bar's open.
  - One signal per day; first breakout wins.
  - No new entries at or after 20:00:00 UTC.

SL/TP (range-relative):
  - range_height = range_high - range_low
  - long:  SL = entry - sl_range_mult * range_height
           TP = entry + tp_range_mult * range_height
  - short: SL = entry + sl_range_mult * range_height
           TP = entry - tp_range_mult * range_height
  - Walk-forward: first bar to touch SL or TP exits the trade.
    Tie-break (both touched same bar): SL (conservative).
  - Forced exit at 21:00:00 UTC bar close if SL/TP not hit.

Skip conditions:
  - Days with fewer than range_bars candles in 14:30-14:55 window.
  - Days with no candles in the entry window (15:00-19:55).
"""
from __future__ import annotations

from datetime import time as dtime

import pandas as pd

from cfd_trader.strategies import catalog


DEFAULT_PARAMS: dict = {
    "session_open_hour":   14,
    "session_open_minute": 30,
    "range_bars":           6,    # 30 min / 5 min
    "entry_window_bars":   60,    # 5 hours (15:00 - 19:55)
    "sl_range_mult":        1.0,
    "tp_range_mult":        1.0,
    "session_close_hour":  21,
    "units":                1,
}

_REQUIRED_COLS = (
    "entry_time", "exit_time", "side", "entry_price", "exit_price", "units"
)


def generate_trades(candles: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Generate ORB trades from M5 candle data.

    Parameters
    ----------
    candles:
        DataFrame with columns: time, open, high, low, close, volume, complete.
        'time' must be datetime64 with UTC timezone (or convertible).
    params:
        Override dict for DEFAULT_PARAMS keys.

    Returns
    -------
    DataFrame with columns: entry_time, exit_time, side, entry_price, exit_price, units.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}

    cols = list(_REQUIRED_COLS)
    if len(candles) == 0:
        return pd.DataFrame(columns=cols)

    df = candles.reset_index(drop=True).copy()

    # Ensure time is timezone-aware UTC
    if df["time"].dt.tz is None:
        df["time"] = df["time"].dt.tz_localize("UTC")
    else:
        df["time"] = df["time"].dt.tz_convert("UTC")

    # Constants derived from params
    open_h: int = int(p["session_open_hour"])
    open_m: int = int(p["session_open_minute"])
    range_bars: int = int(p["range_bars"])
    close_h: int = int(p["session_close_hour"])
    sl_mult: float = float(p["sl_range_mult"])
    tp_mult: float = float(p["tp_range_mult"])
    units: int = int(p["units"])

    # Opening range: 14:30 - 14:55 (6 bars, 5-min each)
    # Signal window start: 15:00
    range_start = dtime(open_h, open_m, 0)
    range_end_min = open_m + range_bars * 5  # 30 min after open
    range_end_h = open_h + range_end_min // 60
    range_end_m = range_end_min % 60
    # Last bar of range is at range_start + (range_bars-1)*5min = 14:55
    range_last_bar = dtime(
        open_h + (open_m + (range_bars - 1) * 5) // 60,
        (open_m + (range_bars - 1) * 5) % 60,
        0,
    )
    # Entry window: [signal_start_time, entry_cutoff_time)
    signal_start = dtime(range_end_h, range_end_m, 0)       # 15:00
    entry_cutoff = dtime(20, 0, 0)                           # no entries at/after 20:00
    session_close = dtime(close_h, 0, 0)                    # 21:00 forced exit

    # Group by trading date
    df["_date"] = df["time"].dt.date
    dates = df["_date"].unique()
    dates.sort()

    trades: list[dict] = []

    for day in dates:
        day_df = df[df["_date"] == day].copy().reset_index(drop=True)
        bar_times = day_df["time"].dt.time

        # --- Opening range bars ---
        range_mask = (bar_times >= range_start) & (bar_times <= range_last_bar)
        range_df = day_df[range_mask]

        if len(range_df) < range_bars:
            # Insufficient data for opening range — skip day
            continue

        range_high = float(range_df["high"].max())
        range_low = float(range_df["low"].min())
        range_height = range_high - range_low

        if range_height <= 0.0:
            continue

        # --- Signal detection bars: [signal_start, entry_cutoff) ---
        signal_mask = (bar_times >= signal_start) & (bar_times < entry_cutoff)
        signal_df = day_df[signal_mask].reset_index(drop=True)

        signal_fired = False
        trade: dict | None = None

        for sig_i in range(len(signal_df)):
            sig_bar = signal_df.iloc[sig_i]
            close_val = float(sig_bar["close"])

            if close_val > range_high:
                side = "long"
            elif close_val < range_low:
                side = "short"
            else:
                continue

            # Entry is at the next bar's open (in the full day frame)
            # Find that bar index in day_df
            sig_time = sig_bar["time"]
            after_mask = day_df["time"] > sig_time
            entry_candidates = day_df[after_mask]
            if entry_candidates.empty:
                break

            entry_row = entry_candidates.iloc[0]
            entry_bar_time = entry_row["time"].time()

            # Do not enter if entry bar is at or after entry_cutoff
            if entry_bar_time >= entry_cutoff:
                break

            entry_price = float(entry_row["open"])

            if side == "long":
                sl = entry_price - sl_mult * range_height
                tp = entry_price + tp_mult * range_height
            else:
                sl = entry_price + sl_mult * range_height
                tp = entry_price - tp_mult * range_height

            # Walk-forward: bars from entry bar onwards (inclusive),
            # up to and including the session close bar
            after_entry_mask = day_df["time"] >= entry_row["time"]
            walk_df = day_df[after_entry_mask].reset_index(drop=True)

            exit_price: float | None = None
            exit_time = entry_row["time"]

            for wj in range(len(walk_df)):
                wbar = walk_df.iloc[wj]
                hi = float(wbar["high"])
                lo = float(wbar["low"])
                bar_t = wbar["time"].time()

                # Force exit at or after session close
                if bar_t >= session_close:
                    exit_price = float(wbar["close"])
                    exit_time = wbar["time"]
                    break

                if side == "long":
                    sl_hit = lo <= sl
                    tp_hit = hi >= tp
                    if sl_hit:  # conservative: SL wins tie-break
                        exit_price = sl
                        exit_time = wbar["time"]
                        break
                    if tp_hit:
                        exit_price = tp
                        exit_time = wbar["time"]
                        break
                else:  # short
                    sl_hit = hi >= sl
                    tp_hit = lo <= tp
                    if sl_hit:  # conservative: SL wins tie-break
                        exit_price = sl
                        exit_time = wbar["time"]
                        break
                    if tp_hit:
                        exit_price = tp
                        exit_time = wbar["time"]
                        break

            if exit_price is None:
                # No bar at session_close found; exit at last available bar
                last_bar = walk_df.iloc[-1]
                exit_price = float(last_bar["close"])
                exit_time = last_bar["time"]

            trade = {
                "entry_time":  entry_row["time"],
                "exit_time":   exit_time,
                "side":        side,
                "entry_price": entry_price,
                "exit_price":  exit_price,
                "units":       units,
            }
            signal_fired = True
            break  # one signal per day

        if signal_fired and trade is not None:
            trades.append(trade)

    return pd.DataFrame(trades, columns=cols)


# Register into the global strategy catalog on import.
catalog.register("orb_ny_open", generate_trades)
