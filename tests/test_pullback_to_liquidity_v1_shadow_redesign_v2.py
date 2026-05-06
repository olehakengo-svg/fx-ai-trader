from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.pullback_to_liquidity_v1 import PullbackToLiquidityV1


def _df(*, current_low: float, n: int = 24) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 15:00", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.1014)
    high = np.full(n, 1.1020)
    low = np.full(n, 1.1014)
    close = np.full(n, 1.1016)
    volume = np.full(n, 1000.0)

    swing_pos = -10
    low[swing_pos] = 1.1000
    high[swing_pos] = 1.1018
    open_[swing_pos] = 1.1012
    close[swing_pos] = 1.1010

    open_[-1] = 1.1016
    high[-1] = 1.1024
    low[-1] = current_low
    close[-1] = 1.1022
    volume[-1] = 1400.0

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, pip_mult: int = 10000) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        htf={"agreement": "bull"},
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=pip_mult,
        df=df,
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=15,
    )


def test_v2_default_off_preserves_percentage_liquidity_touch(monkeypatch):
    monkeypatch.delenv("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2", raising=False)

    cand = PullbackToLiquidityV1().evaluate(_ctx(_df(current_low=1.1009)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2" in r for r in cand.reasons)


def test_v2_rejects_touch_outside_fixed_five_pips(monkeypatch):
    monkeypatch.setenv("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2", "1")

    cand = PullbackToLiquidityV1().evaluate(_ctx(_df(current_low=1.1009)))

    assert cand is None


def test_v2_accepts_touch_inside_fixed_five_pips(monkeypatch):
    monkeypatch.setenv("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2", "1")

    cand = PullbackToLiquidityV1().evaluate(_ctx(_df(current_low=1.1005)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert any("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2" in r for r in cand.reasons)
    assert any("tolerance=0.00050" in r for r in cand.reasons)


def test_daytrade_engine_default_off_does_not_register_live_strategy(monkeypatch):
    monkeypatch.delenv("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2", raising=False)

    names = [strategy.name for strategy in DaytradeEngine().strategies]

    assert "pullback_to_liquidity_v1" not in names


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = DaytradeEngine()
    best = Candidate("SELL", 70, 1.2, 1.0, ["best"], "other", 7.0)
    p2l = Candidate("BUY", 70, 1.0, 1.2, ["p2l"], "pullback_to_liquidity_v1", 4.0)

    monkeypatch.setenv("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2", "1")
    monkeypatch.delenv("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, p2l], best) == []

    monkeypatch.setenv("PULLBACK_TO_LIQUIDITY_V1_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, p2l], best) == [p2l]
