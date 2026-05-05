from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.context import SignalContext
from strategies.daytrade.xs_momentum import XsMomentum


def _df(*, n=40, closed_signal=True, last_signal=True) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    close = np.full(n, 1.1000)
    open_ = np.full(n, 1.1000)

    # Keep both BT/current and live-closed lookback closes far enough below any
    # intended signal bar.
    close[-21] = 1.1000
    open_[-21] = 1.1000
    close[-22] = 1.1000
    open_[-22] = 1.1000

    def set_signal(i: int):
        open_[i] = 1.1015
        close[i] = 1.1030

    def set_neutral(i: int):
        open_[i] = 1.1000
        close[i] = 1.1002

    set_signal(-2) if closed_signal else set_neutral(-2)
    set_signal(-1) if last_signal else set_neutral(-1)

    high = np.maximum(open_, close) + 0.0005
    low = np.minimum(open_, close) - 0.0005
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": np.full(n, 1.1020),
            "ema21": np.full(n, 1.1010),
            "ema50": np.full(n, 1.1005),
            "ema200": np.full(n, 1.1000),
            "adx": np.full(n, 25.0),
            "adx_pos": np.full(n, 25.0),
            "adx_neg": np.full(n, 20.0),
            "rsi": np.full(n, 55.0),
            "rsi5": np.full(n, 55.0),
            "rsi9": np.full(n, 55.0),
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 55.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.zeros(n),
            "bb_upper": np.full(n, 1.1040),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0960),
            "bb_pband": np.full(n, 0.75),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool, bar_time=None) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        ema50=float(row["ema50"]),
        ema200=float(row["ema200"]),
        adx=float(row["adx"]),
        adx_pos=float(row["adx_pos"]),
        adx_neg=float(row["adx_neg"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        rsi9=float(row["rsi9"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        macdh=float(row["macd_hist"]),
        bbpb=float(row["bb_pband"]),
        symbol="GBPUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )


def test_v2_default_off_allows_existing_repeat(monkeypatch):
    monkeypatch.delenv("XS_MOMENTUM_REDESIGN_V2", raising=False)
    XsMomentum.reset_dedup_state()
    s = XsMomentum()
    ctx = _ctx(_df(), backtest_mode=True, bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    assert s.evaluate(ctx) is not None
    assert s.evaluate(ctx) is not None


def test_v2_per_bar_dedup_blocks_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("XS_MOMENTUM_REDESIGN_V2", "1")
    XsMomentum.reset_dedup_state()
    s = XsMomentum()
    ctx = _ctx(_df(), backtest_mode=True, bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    first = s.evaluate(ctx)
    second = s.evaluate(ctx)

    assert first is not None
    assert first.signal == "BUY"
    assert second is None


def test_v2_live_ignores_in_progress_bar_trigger(monkeypatch):
    monkeypatch.setenv("XS_MOMENTUM_REDESIGN_V2", "1")
    XsMomentum.reset_dedup_state()
    s = XsMomentum()
    ctx = _ctx(_df(closed_signal=False, last_signal=True), backtest_mode=False)

    assert s.evaluate(ctx) is None


def test_v2_live_uses_closed_bar_trigger(monkeypatch):
    monkeypatch.setenv("XS_MOMENTUM_REDESIGN_V2", "1")
    XsMomentum.reset_dedup_state()
    s = XsMomentum()
    ctx = _ctx(_df(closed_signal=True, last_signal=False), backtest_mode=False)

    cand = s.evaluate(ctx)

    assert cand is not None
    assert cand.signal == "BUY"
