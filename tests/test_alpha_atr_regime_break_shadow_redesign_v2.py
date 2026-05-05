from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade.alpha_atr_regime_break import AtrRegimeBreak


def _df(*, n=130, signal_at=-1, signal_dir="SELL", weak_signal_bar=False) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.1000)
    close = np.full(n, 1.1001)
    high = np.full(n, 1.1006)
    low = np.full(n, 1.0996)

    atr = np.empty(n)
    for i in range(n):
        atr[i] = 0.0010 + (0.00010 if i % 2 == 0 else -0.00010)
    for i in range(n - 14, n):
        atr[i] = 0.0010 + (0.000001 if i % 2 == 0 else -0.000001)

    sig_idx = signal_at if signal_at >= 0 else n + signal_at
    prev_idx = sig_idx - 1
    atr[prev_idx] = 0.0010
    atr[sig_idx] = 0.0016

    if signal_dir == "SELL":
        open_[sig_idx] = 1.1008
        close[sig_idx] = 1.1002 if not weak_signal_bar else 1.10076
        high[sig_idx] = 1.1010
        low[sig_idx] = 1.0995
    else:
        open_[sig_idx] = 1.1002
        close[sig_idx] = 1.1008 if not weak_signal_bar else 1.10024
        high[sig_idx] = 1.1012
        low[sig_idx] = 1.0998

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": atr,
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, htf_agreement="bull") -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": htf_agreement},
        backtest_mode=True,
        bar_time=df.index[-1],
    )


def test_default_path_keeps_htf_hard_block(monkeypatch):
    monkeypatch.delenv("ALPHA_ATR_REGIME_BREAK_REDESIGN_V2", raising=False)

    got = AtrRegimeBreak().evaluate(_ctx(_df(signal_at=-1, signal_dir="SELL"), htf_agreement="bull"))

    assert got is None


def test_v2_uses_closed_signal_bar_and_removes_htf_hard_block(monkeypatch):
    monkeypatch.setenv("ALPHA_ATR_REGIME_BREAK_REDESIGN_V2", "1")
    df = _df(signal_at=-2, signal_dir="SELL")
    df.iloc[-1, df.columns.get_loc("Open")] = 1.1002
    df.iloc[-1, df.columns.get_loc("Close")] = 1.1009

    got = AtrRegimeBreak().evaluate(_ctx(df, htf_agreement="bull"))

    assert got is not None
    assert got.signal == "SELL"
    assert any("V2 closed-bar signal" in reason for reason in got.reasons)


def test_v2_does_not_use_current_intrabar_signal(monkeypatch):
    monkeypatch.setenv("ALPHA_ATR_REGIME_BREAK_REDESIGN_V2", "1")
    df = _df(signal_at=-1, signal_dir="BUY")

    got = AtrRegimeBreak().evaluate(_ctx(df, htf_agreement="mixed"))

    assert got is None


def test_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    from strategies.daytrade import DaytradeEngine

    engine = DaytradeEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "xs_momentum", 5.0)
    atr = Candidate("SELL", 60, 1.2, 0.9, ["atr"], "atr_regime_break", 4.5)

    monkeypatch.delenv("ALPHA_ATR_REGIME_BREAK_REDESIGN_V2", raising=False)
    monkeypatch.delenv("ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, atr], best) == []

    monkeypatch.setenv("ALPHA_ATR_REGIME_BREAK_REDESIGN_V2", "1")
    monkeypatch.setenv("ALPHA_ATR_REGIME_BREAK_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, atr], best) == [atr]
