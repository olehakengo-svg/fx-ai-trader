"""orb_ny_open_short: short-only variant of orb_ny_open.

Phase 1 forensic (P3W1, 2026-05-11) found SHORT-only has N=22 WR=68.2% EV=+5.81
on SPX500_USD M5 over 90 days. LONG was negative (-160 sum). Phase 2 shadow
candidate is this short-only variant.

Bonferroni metadata: m=2 (we tested long+short directions in Wave 1 and
selected short). Recorded in extra_json by the shadow runner, not by this
module.
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
    "entry_time", "exit_time", "side", "entry_price", "exit_price", "units",
    "pnl_point",
)


def generate_trades(candles: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Generate short-only ORB trades from M5 candle data.

    Same opening-range definition and SL/TP walk-forward as orb_ny_open,
    but only emits a trade when close < range_low (down-breakdown). Up-breakouts
    are ignored entirely.
    """
    p = {**DEFAULT_PARAMS, **(params or {})}

    cols = list(_REQUIRED_COLS)
    if len(candles) == 0:
        return pd.DataFrame(columns=cols)

    df = candles.reset_index(drop=True).copy()

    if df["time"].dt.tz is None:
        df["time"] = df["time"].dt.tz_localize("UTC")
    else:
        df["time"] = df["time"].dt.tz_convert("UTC")

    open_h: int = int(p["session_open_hour"])
    open_m: int = int(p["session_open_minute"])
    range_bars: int = int(p["range_bars"])
    close_h: int = int(p["session_close_hour"])
    sl_mult: float = float(p["sl_range_mult"])
    tp_mult: float = float(p["tp_range_mult"])
    units: int = int(p["units"])

    range_start = dtime(open_h, open_m, 0)
    range_end_min = open_m + range_bars * 5
    range_end_h = open_h + range_end_min // 60
    range_end_m = range_end_min % 60
    range_last_bar = dtime(
        open_h + (open_m + (range_bars - 1) * 5) // 60,
        (open_m + (range_bars - 1) * 5) % 60,
        0,
    )
    signal_start = dtime(range_end_h, range_end_m, 0)
    entry_cutoff = dtime(20, 0, 0)
    session_close = dtime(close_h, 0, 0)

    df["_date"] = df["time"].dt.date
    dates = df["_date"].unique()
    dates.sort()

    trades: list[dict] = []

    for day in dates:
        day_df = df[df["_date"] == day].copy().reset_index(drop=True)
        bar_times = day_df["time"].dt.time

        range_mask = (bar_times >= range_start) & (bar_times <= range_last_bar)
        range_df = day_df[range_mask]

        if len(range_df) < range_bars:
            continue

        range_high = float(range_df["high"].max())
        range_low = float(range_df["low"].min())
        range_height = range_high - range_low

        if range_height <= 0.0:
            continue

        signal_mask = (bar_times >= signal_start) & (bar_times < entry_cutoff)
        signal_df = day_df[signal_mask].reset_index(drop=True)

        signal_fired = False
        trade: dict | None = None

        for sig_i in range(len(signal_df)):
            sig_bar = signal_df.iloc[sig_i]
            close_val = float(sig_bar["close"])

            # SHORT-ONLY: ignore up-breakouts; only act on down-breakdowns.
            if close_val < range_low:
                side = "short"
            else:
                continue

            sig_time = sig_bar["time"]
            after_mask = day_df["time"] > sig_time
            entry_candidates = day_df[after_mask]
            if entry_candidates.empty:
                break

            entry_row = entry_candidates.iloc[0]
            entry_bar_time = entry_row["time"].time()

            if entry_bar_time >= entry_cutoff:
                break

            entry_price = float(entry_row["open"])

            sl = entry_price + sl_mult * range_height
            tp = entry_price - tp_mult * range_height

            after_entry_mask = day_df["time"] >= entry_row["time"]
            walk_df = day_df[after_entry_mask].reset_index(drop=True)

            exit_price: float | None = None
            exit_time = entry_row["time"]

            for wj in range(len(walk_df)):
                wbar = walk_df.iloc[wj]
                hi = float(wbar["high"])
                lo = float(wbar["low"])
                bar_t = wbar["time"].time()

                if bar_t >= session_close:
                    exit_price = float(wbar["close"])
                    exit_time = wbar["time"]
                    break

                sl_hit = hi >= sl
                tp_hit = lo <= tp
                if sl_hit:
                    exit_price = sl
                    exit_time = wbar["time"]
                    break
                if tp_hit:
                    exit_price = tp
                    exit_time = wbar["time"]
                    break

            if exit_price is None:
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
                "pnl_point":   entry_price - exit_price,  # short: profit when exit < entry
            }
            signal_fired = True
            break

        if signal_fired and trade is not None:
            trades.append(trade)

    return pd.DataFrame(trades, columns=cols)


# Register into the global strategy catalog on import.
catalog.register("orb_ny_open_short", generate_trades)
