from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.context import SignalContext
from strategies.daytrade.mqe_gbpusd_fix import MqeGbpusdFix


def _df(end: str = "2026-05-28 15:30") -> pd.DataFrame:
    n = 8
    idx = pd.date_range(end=end, periods=n, freq="15min", tz="UTC")
    close = np.array([1.2600, 1.2602, 1.2604, 1.2606, 1.2608, 1.2610, 1.2612, 1.2614])
    return pd.DataFrame(
        {
            "Open": close - 0.00005,
            "High": close + 0.00020,
            "Low": close - 0.00020,
            "Close": close,
            "Volume": np.full(n, 1000.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=0.0008,
        atr7=0.0008,
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="GBPUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
    )


def test_v2_default_off_keeps_legacy_1500_window(monkeypatch):
    monkeypatch.delenv("MQE_GBPUSD_FIX_REDESIGN_V2", raising=False)
    MqeGbpusdFix.reset_dedup_state()

    cand = MqeGbpusdFix().evaluate(_ctx(_df("2026-05-28 15:15")))

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.max_hold_bars is None
    assert not any("MQE_GBPUSD_FIX_REDESIGN_V2" in r for r in cand.reasons)


def test_v2_rejects_pre_1530_fix_bar(monkeypatch):
    monkeypatch.setenv("MQE_GBPUSD_FIX_REDESIGN_V2", "1")
    MqeGbpusdFix.reset_dedup_state()

    cand = MqeGbpusdFix().evaluate(_ctx(_df("2026-05-28 15:15")))

    assert cand is None


def test_v2_accepts_1530_window_and_attaches_time_stop(monkeypatch):
    monkeypatch.setenv("MQE_GBPUSD_FIX_REDESIGN_V2", "1")
    MqeGbpusdFix.reset_dedup_state()

    cand = MqeGbpusdFix().evaluate(_ctx(_df("2026-05-28 15:30")))

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.max_hold_bars == 6
    assert any("15:30-16:00 dedup + 6bar time stop" in r for r in cand.reasons)


def test_v2_one_trade_per_month_end_fix_window(monkeypatch):
    monkeypatch.setenv("MQE_GBPUSD_FIX_REDESIGN_V2", "1")
    MqeGbpusdFix.reset_dedup_state()
    strategy = MqeGbpusdFix()

    assert strategy.evaluate(_ctx(_df("2026-05-28 15:30"), backtest_mode=False)) is not None
    assert strategy.evaluate(_ctx(_df("2026-05-28 15:45"), backtest_mode=False)) is None


def test_v2_dedup_can_be_reset_for_fresh_bt_run(monkeypatch):
    monkeypatch.setenv("MQE_GBPUSD_FIX_REDESIGN_V2", "1")
    MqeGbpusdFix.reset_dedup_state()
    strategy = MqeGbpusdFix()

    assert strategy.evaluate(_ctx(_df("2026-05-28 15:30"))) is not None
    assert strategy.evaluate(_ctx(_df("2026-05-28 15:30"))) is None

    MqeGbpusdFix.reset_dedup_state()
    assert strategy.evaluate(_ctx(_df("2026-05-28 15:30"))) is not None
