"""Tests for orb_ny_open: NY-open Opening Range Breakout strategy.

TDD: tests written before implementation.

Test coverage:
  1. test_default_params_complete
  2. test_handles_empty_candles
  3. test_required_columns_present
  4. test_long_signal_on_clean_breakout_day
  5. test_short_signal_on_clean_breakdown_day
  6. test_no_signal_when_range_holds_all_day
  7. test_only_one_trade_per_day
  8. test_skips_days_with_insufficient_range_bars
"""
from __future__ import annotations

import pandas as pd
import pytest

from cfd_trader.strategies.ported import orb_ny_open as strat


# ---------------------------------------------------------------------------
# Candle factory helpers
# ---------------------------------------------------------------------------

def _bar(time: str, open_: float, high: float, low: float, close: float) -> dict:
    return {
        "time": pd.Timestamp(time, tz="UTC"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": 100,
        "complete": True,
    }


def _make_candles(bars: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(bars)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


# ---------------------------------------------------------------------------
# 1. Default params complete
# ---------------------------------------------------------------------------

def test_default_params_complete() -> None:
    required_keys = {
        "session_open_hour",
        "session_open_minute",
        "range_bars",
        "entry_window_bars",
        "sl_range_mult",
        "tp_range_mult",
        "session_close_hour",
        "units",
    }
    assert required_keys.issubset(set(strat.DEFAULT_PARAMS.keys()))


# ---------------------------------------------------------------------------
# 2. Handles empty candles
# ---------------------------------------------------------------------------

def test_handles_empty_candles() -> None:
    empty = pd.DataFrame(
        columns=["time", "open", "high", "low", "close", "volume", "complete"]
    )
    trades = strat.generate_trades(empty, strat.DEFAULT_PARAMS)
    assert isinstance(trades, pd.DataFrame)
    assert len(trades) == 0


# ---------------------------------------------------------------------------
# 3. Required output columns present
# ---------------------------------------------------------------------------

def test_required_columns_present() -> None:
    required = {"entry_time", "exit_time", "side", "entry_price", "exit_price", "units"}
    # A day with a clean breakout so we get at least one trade
    bars = []
    # Opening range bars: 14:30 - 14:55 UTC (6 bars), range = 5000-5010
    for i in range(6):
        t = f"2026-01-05 14:{30 + i * 5:02d}:00"
        bars.append(_bar(t, 5005.0, 5010.0, 5000.0, 5005.0))
    # 15:00 bar closes above range_high → long signal
    bars.append(_bar("2026-01-05 15:00:00", 5005.0, 5015.0, 5000.0, 5012.0))
    # 15:05 bar — entry bar
    bars.append(_bar("2026-01-05 15:05:00", 5012.0, 5030.0, 5010.0, 5025.0))
    # A few more bars so walk-forward can complete
    for i in range(2, 12):
        t = f"2026-01-05 15:{i * 5:02d}:00"
        bars.append(_bar(t, 5025.0, 5040.0, 5020.0, 5035.0))

    df = _make_candles(bars)
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)
    assert required.issubset(set(trades.columns))


# ---------------------------------------------------------------------------
# 4. Long signal on clean breakout day
# ---------------------------------------------------------------------------

def test_long_signal_on_clean_breakout_day() -> None:
    """
    Opening range 14:30-14:55: high=5010, low=5000.
    Bar at 15:00 closes at 5012 (> range_high 5010) → long signal.
    Entry at 15:05 open = 5012.
    range_height = 10, SL = 5002, TP = 5022.
    Walk-forward: bar at 15:05 touches TP (high=5030 >= 5022).
    """
    bars = []
    # 6 opening range bars
    for i in range(6):
        t = f"2026-01-05 14:{30 + i * 5:02d}:00"
        bars.append(_bar(t, 5005.0, 5010.0, 5000.0, 5005.0))
    # 15:00 signal bar: closes above range_high
    bars.append(_bar("2026-01-05 15:00:00", 5010.0, 5015.0, 5005.0, 5012.0))
    # 15:05 entry bar (entry open = 5012), and TP is hit here
    bars.append(_bar("2026-01-05 15:05:00", 5012.0, 5030.0, 5010.0, 5025.0))
    # Padding
    for i in range(2, 5):
        bars.append(_bar(f"2026-01-05 15:{i * 5:02d}:00", 5025.0, 5040.0, 5020.0, 5035.0))

    df = _make_candles(bars)
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)

    assert len(trades) == 1, f"expected 1 trade, got {len(trades)}"
    t = trades.iloc[0]
    assert t["side"] == "long"
    assert t["entry_time"] == pd.Timestamp("2026-01-05 15:05:00", tz="UTC")
    assert t["entry_price"] == pytest.approx(5012.0)


# ---------------------------------------------------------------------------
# 5. Short signal on clean breakdown day
# ---------------------------------------------------------------------------

def test_short_signal_on_clean_breakdown_day() -> None:
    """
    Opening range 14:30-14:55: high=5010, low=5000.
    Bar at 15:00 closes at 4998 (< range_low 5000) → short signal.
    Entry at 15:05 open = 4998.
    range_height = 10, SL = 5008, TP = 4988.
    Walk-forward: bar at 15:05 touches TP (low=4985 <= 4988).
    """
    bars = []
    for i in range(6):
        t = f"2026-01-05 14:{30 + i * 5:02d}:00"
        bars.append(_bar(t, 5005.0, 5010.0, 5000.0, 5005.0))
    # 15:00 signal bar: closes below range_low
    bars.append(_bar("2026-01-05 15:00:00", 5000.0, 5002.0, 4995.0, 4998.0))
    # 15:05 entry bar, TP hit
    bars.append(_bar("2026-01-05 15:05:00", 4998.0, 5000.0, 4985.0, 4990.0))
    # Padding
    for i in range(2, 5):
        bars.append(_bar(f"2026-01-05 15:{i * 5:02d}:00", 4990.0, 4995.0, 4980.0, 4988.0))

    df = _make_candles(bars)
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)

    assert len(trades) == 1, f"expected 1 trade, got {len(trades)}"
    t = trades.iloc[0]
    assert t["side"] == "short"
    assert t["entry_time"] == pd.Timestamp("2026-01-05 15:05:00", tz="UTC")
    assert t["entry_price"] == pytest.approx(4998.0)


# ---------------------------------------------------------------------------
# 6. No signal when range holds all day
# ---------------------------------------------------------------------------

def test_no_signal_when_range_holds_all_day() -> None:
    """
    Opening range: high=5010, low=5000.
    All post-15:00 closes stay within [5000, 5010] → zero trades.
    """
    bars = []
    for i in range(6):
        t = f"2026-01-05 14:{30 + i * 5:02d}:00"
        bars.append(_bar(t, 5005.0, 5010.0, 5000.0, 5005.0))
    # 60 bars from 15:00 to 19:55, all closes inside range
    for i in range(60):
        minute = 15 * 60 + i * 5
        h = minute // 60
        m = minute % 60
        bars.append(_bar(f"2026-01-05 {h:02d}:{m:02d}:00", 5005.0, 5009.0, 5001.0, 5005.0))

    df = _make_candles(bars)
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)
    assert len(trades) == 0


# ---------------------------------------------------------------------------
# 7. Only one trade per day
# ---------------------------------------------------------------------------

def test_only_one_trade_per_day() -> None:
    """
    Bar at 15:00 breaks up (long signal), bar at 17:00 breaks down.
    Only the first signal (long) must be taken.
    """
    bars = []
    # Opening range: 5000-5010
    for i in range(6):
        t = f"2026-01-05 14:{30 + i * 5:02d}:00"
        bars.append(_bar(t, 5005.0, 5010.0, 5000.0, 5005.0))
    # 15:00 close > range_high → long signal
    bars.append(_bar("2026-01-05 15:00:00", 5010.0, 5015.0, 5005.0, 5012.0))
    # Entry bar at 15:05
    bars.append(_bar("2026-01-05 15:05:00", 5012.0, 5025.0, 5010.0, 5020.0))
    # Bars 15:10 - 16:55 (all inside range or above, no SL/TP hit yet)
    for i in range(2, 24):
        minute = 15 * 60 + i * 5
        h = minute // 60
        m = minute % 60
        bars.append(_bar(f"2026-01-05 {h:02d}:{m:02d}:00", 5015.0, 5025.0, 5012.0, 5018.0))
    # 17:00 bar closes below range_low → would fire short (but second signal)
    bars.append(_bar("2026-01-05 17:00:00", 5000.0, 5002.0, 4990.0, 4995.0))
    # More bars: eventually TP hit for the long
    for i in range(25, 60):
        minute = 15 * 60 + i * 5
        h = minute // 60
        m = minute % 60
        bars.append(_bar(f"2026-01-05 {h:02d}:{m:02d}:00", 5020.0, 5030.0, 5010.0, 5025.0))

    df = _make_candles(bars)
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)

    assert len(trades) == 1, f"expected 1 trade (first signal only), got {len(trades)}"
    assert trades.iloc[0]["side"] == "long"


# ---------------------------------------------------------------------------
# 8. Skip days with insufficient opening range bars
# ---------------------------------------------------------------------------

def test_skips_days_with_insufficient_range_bars() -> None:
    """
    Only 3 bars in the 14:30-14:55 window (< range_bars=6).
    Strategy must skip this day → zero trades.
    """
    bars = []
    # Only 3 opening range bars (holiday / data gap)
    for i in range(3):
        t = f"2026-01-05 14:{30 + i * 5:02d}:00"
        bars.append(_bar(t, 5005.0, 5010.0, 5000.0, 5005.0))
    # Post-open bars that would break out if the range had been established
    for i in range(6):
        t = f"2026-01-05 15:{i * 5:02d}:00"
        bars.append(_bar(t, 5010.0, 5020.0, 5005.0, 5015.0))

    df = _make_candles(bars)
    trades = strat.generate_trades(df, strat.DEFAULT_PARAMS)
    assert len(trades) == 0
