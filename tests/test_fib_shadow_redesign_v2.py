from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade.dt_fib_reversal import DtFibReversal


def _df(*, include_forming_spike: bool = False) -> pd.DataFrame:
    n = 82 if include_forming_spike else 81
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.0040)
    high = np.full(n, 1.0060)
    low = np.full(n, 1.0020)
    close = np.full(n, 1.0040)
    rsi = np.full(n, 50.0)
    macdh = np.full(n, 0.0)

    # Closed-bar fib swing: low first, high later => uptrend, 61.8% near 1.00382.
    low[-80] = 1.0000
    high[-12] = 1.0100
    open_[-1] = 1.0036
    close[-1] = 1.00385
    rsi[-1] = 40.0
    macdh[-2] = 0.0001
    macdh[-1] = 0.0002

    if include_forming_spike:
        # A still-forming current bar must not redraw the closed-bar fib levels.
        open_[-1] = 1.0040
        close[-1] = 1.0041
        high[-1] = 1.0200
        rsi[-1] = 55.0
        macdh[-1] = -0.0001
        open_[-2] = 1.0036
        close[-2] = 1.00385
        rsi[-2] = 40.0
        macdh[-3] = 0.0001
        macdh[-2] = 0.0002

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": np.full(n, 1.0042),
            "ema21": np.full(n, 1.0038),
            "ema50": np.full(n, 1.0030),
            "ema200": np.full(n, 1.0020),
            "adx": np.full(n, 20.0),
            "adx_pos": np.full(n, 25.0),
            "adx_neg": np.full(n, 20.0),
            "rsi": rsi,
            "rsi5": rsi,
            "rsi9": rsi,
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 45.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": macdh,
            "bb_upper": np.full(n, 1.0080),
            "bb_mid": np.full(n, 1.0040),
            "bb_lower": np.full(n, 1.0000),
            "bb_pband": np.full(n, 0.45),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool, bar_time=None) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
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
        macdh_prev=float(prev["macd_hist"]),
        bbpb=float(row["bb_pband"]),
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "mixed"},
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )


def test_v2_default_off_allows_existing_repeat(monkeypatch):
    monkeypatch.delenv("FIB_REDESIGN_V2", raising=False)
    DtFibReversal.reset_dedup_state()
    s = DtFibReversal()
    ctx = _ctx(_df(), backtest_mode=True, bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    assert s.evaluate(ctx) is not None
    assert s.evaluate(ctx) is not None


def test_v2_uses_closed_signal_bar_not_forming_bar(monkeypatch):
    monkeypatch.setenv("FIB_REDESIGN_V2", "1")
    DtFibReversal.reset_dedup_state()
    s = DtFibReversal()
    df = _df(include_forming_spike=True)
    ctx = _ctx(df, backtest_mode=False, bar_time=df.index[-2])

    cand = s.evaluate(ctx)

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.entry_type == "dt_fib_reversal"
    assert cand.sl <= ctx.entry - 1.2 * ctx.atr7


def test_v2_per_bar_dedup_blocks_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("FIB_REDESIGN_V2", "1")
    DtFibReversal.reset_dedup_state()
    s = DtFibReversal()
    df = _df()
    ctx = _ctx(df, backtest_mode=True, bar_time=df.index[-1])

    first = s.evaluate(ctx)
    second = s.evaluate(ctx)

    assert first is not None
    assert second is None


def test_v2_live_intrabar_without_bar_time_is_blocked(monkeypatch):
    monkeypatch.setenv("FIB_REDESIGN_V2", "1")
    DtFibReversal.reset_dedup_state()
    s = DtFibReversal()
    ctx = _ctx(_df(), backtest_mode=False, bar_time=None)

    assert s.evaluate(ctx) is None


def test_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    from strategies.daytrade import DaytradeEngine

    engine = DaytradeEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "xs_momentum", 5.0)
    fib = Candidate("BUY", 60, 1.0, 1.2, ["fib"], "dt_fib_reversal", 4.5)

    monkeypatch.delenv("FIB_REDESIGN_V2", raising=False)
    monkeypatch.delenv("FIB_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, fib], best) == []

    monkeypatch.setenv("FIB_REDESIGN_V2", "1")
    monkeypatch.setenv("FIB_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, fib], best) == [fib]
