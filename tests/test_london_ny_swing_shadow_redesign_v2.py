from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.london_ny_swing import LondonNySwing


def _df(*, signal_close: float, signal_open: float | None = None,
        current_close: float = 1.10130) -> pd.DataFrame:
    n = 110
    idx = pd.date_range(end="2026-05-05 13:15", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.10040)
    high = np.full(n, 1.10080)
    low = np.full(n, 1.10020)
    close = np.full(n, 1.10045)

    today = pd.Timestamp("2026-05-05").date()
    london_mask = (idx.date == today) & (idx.hour >= 7) & (idx.hour < 12)
    high[london_mask] = 1.10100
    low[london_mask] = 1.10000
    open_[london_mask] = 1.10040
    close[london_mask] = 1.10050

    # Closed signal bar for live mode (df.iloc[-2]).
    open_[-2] = signal_close - 0.00015 if signal_open is None else signal_open
    close[-2] = signal_close
    high[-2] = max(signal_close, open_[-2]) + 0.00005
    low[-2] = min(signal_close, open_[-2]) - 0.00005

    # Current/in-progress or BT signal bar (df.iloc[-1]).
    open_[-1] = current_close - 0.00010
    close[-1] = current_close
    high[-1] = current_close + 0.00005
    low[-1] = current_close - 0.00020

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.00050),
            "atr7": np.full(n, 0.00050),
            "ema9": np.full(n, 1.10090),
            "ema21": np.full(n, 1.10060),
            "ema50": np.full(n, 1.10030),
            "adx": np.full(n, 24.0),
            "adx_pos": np.full(n, 26.0),
            "adx_neg": np.full(n, 18.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        ema50=float(row["ema50"]),
        adx=float(row["adx"]),
        adx_pos=float(row["adx_pos"]),
        adx_neg=float(row["adx_neg"]),
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "bull"},
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_current_context_trigger(monkeypatch):
    monkeypatch.delenv("LONDON_NY_SWING_REDESIGN_V2", raising=False)
    LondonNySwing.reset_dedup_state()

    # Legacy uses ctx.entry/current context, so it can fire even when the
    # preceding closed bar has not broken the London high.
    cand = LondonNySwing().evaluate(
        _ctx(_df(signal_close=1.10102, current_close=1.10130), backtest_mode=False)
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("LONDON_NY_SWING_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_live_ignores_intrabar_entry_when_closed_bar_has_not_broken(monkeypatch):
    monkeypatch.setenv("LONDON_NY_SWING_REDESIGN_V2", "1")
    LondonNySwing.reset_dedup_state()

    cand = LondonNySwing().evaluate(
        _ctx(_df(signal_close=1.10102, current_close=1.10130), backtest_mode=False)
    )

    assert cand is None


def test_v2_live_uses_closed_signal_bar_and_execution_entry(monkeypatch):
    monkeypatch.setenv("LONDON_NY_SWING_REDESIGN_V2", "1")
    LondonNySwing.reset_dedup_state()

    cand = LondonNySwing().evaluate(
        _ctx(_df(signal_close=1.10120, current_close=1.10130), backtest_mode=False)
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.sl, 5) == 1.10085
    assert round(cand.tp, 5) == 1.10280
    assert any("closed signal bar" in reason for reason in cand.reasons)


def test_v2_per_bar_dedup_blocks_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("LONDON_NY_SWING_REDESIGN_V2", "1")
    LondonNySwing.reset_dedup_state()
    strategy = LondonNySwing()
    ctx = _ctx(_df(signal_close=1.10102, current_close=1.10130), backtest_mode=True)

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert first.signal == "BUY"
    assert second is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    london_ny = Candidate("BUY", 70, 1.0, 2.0, [], "london_ny_swing", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("LONDON_NY_SWING_REDESIGN_V2", "1")
    monkeypatch.delenv("LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, london_ny], other) == []

    monkeypatch.setenv("LONDON_NY_SWING_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, london_ny], other) == [london_ny]
