from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade.alpha_wick_imbalance import WickImbalanceReversion


def _df(*, n=20, closed_signal=True, current_signal=False) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.1000)
    close = np.full(n, 1.1001)
    high = np.full(n, 1.1002)
    low = np.full(n, 1.0998)

    # V2 WIR window: df.iloc[-10:-2] for default window=8.
    for i in range(n - 10, n - 2):
        open_[i] = 1.1000
        close[i] = 1.1001
        high[i] = 1.1016
        low[i] = 1.0999

    if closed_signal:
        open_[-2] = 1.1008
        close[-2] = 1.1001
    else:
        open_[-2] = 1.1001
        close[-2] = 1.1008
    high[-2] = max(open_[-2], close[-2]) + 0.0002
    low[-2] = min(open_[-2], close[-2]) - 0.0002

    if current_signal:
        open_[-1] = 1.1008
        close[-1] = 1.1001
    else:
        open_[-1] = 1.1001
        close[-1] = 1.1008
    high[-1] = max(open_[-1], close[-1]) + 0.0002
    low[-1] = min(open_[-1], close[-1]) - 0.0002

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, htf_agreement="bull") -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        bb_width_pct=0.30,
        symbol="GBPUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": htf_agreement},
        backtest_mode=True,
        bar_time=df.index[-1],
    )


def test_default_path_keeps_live_behavior_off(monkeypatch):
    monkeypatch.delenv("WICK_IMBALANCE_REVERSION_REDESIGN_V2", raising=False)
    monkeypatch.delenv("ALPHA_WICK_IMBALANCE_REDESIGN_V2", raising=False)

    got = WickImbalanceReversion().evaluate(
        _ctx(_df(closed_signal=True, current_signal=True), htf_agreement="bull")
    )

    assert got is None


def test_v2_uses_closed_confirmation_and_removes_htf_hard_block(monkeypatch):
    monkeypatch.setenv("WICK_IMBALANCE_REVERSION_REDESIGN_V2", "1")

    got = WickImbalanceReversion().evaluate(
        _ctx(_df(closed_signal=True, current_signal=False), htf_agreement="bull")
    )

    assert got is not None
    assert got.signal == "SELL"
    assert any("V2 closed-bar confirmation" in reason for reason in got.reasons)


def test_v2_does_not_use_current_intrabar_confirmation(monkeypatch):
    monkeypatch.setenv("WICK_IMBALANCE_REVERSION_REDESIGN_V2", "1")

    got = WickImbalanceReversion().evaluate(
        _ctx(_df(closed_signal=False, current_signal=True), htf_agreement="mixed")
    )

    assert got is None


def test_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    from strategies.daytrade import DaytradeEngine

    engine = DaytradeEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "xs_momentum", 5.0)
    wick = Candidate("SELL", 60, 1.2, 0.9, ["wick"], "wick_imbalance_reversion", 4.5)

    monkeypatch.delenv("WICK_IMBALANCE_REVERSION_REDESIGN_V2", raising=False)
    monkeypatch.delenv("WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    monkeypatch.delenv("ALPHA_WICK_IMBALANCE_REDESIGN_V2", raising=False)
    monkeypatch.delenv("ALPHA_WICK_IMBALANCE_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, wick], best) == []

    monkeypatch.setenv("WICK_IMBALANCE_REVERSION_REDESIGN_V2", "1")
    monkeypatch.setenv("WICK_IMBALANCE_REVERSION_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, wick], best) == [wick]
