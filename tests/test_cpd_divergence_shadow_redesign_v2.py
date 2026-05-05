from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade.cpd_divergence import CpdDivergence


def _ohlcv_from_returns(base: float, returns: np.ndarray, idx: pd.DatetimeIndex) -> pd.DataFrame:
    close = base * np.cumprod(1 + returns)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.0002,
            "Low": close * 0.9998,
            "Close": close,
            "Volume": np.full(len(close), 1000.0),
        },
        index=idx,
    )


def _ctx(*, closed_signal: bool, current_signal: bool, n: int = 100) -> SignalContext:
    idx = pd.date_range("2026-05-04 00:00", periods=n, freq="15min", tz="UTC")
    rng = np.random.default_rng(7)
    gbp_returns = rng.normal(0, 0.00025, n)
    eur_returns = rng.normal(0, 0.00025, n)

    eur_returns[-2] = 0.005 if closed_signal else 0.0
    gbp_returns[-2] = 0.0
    eur_returns[-1] = 0.005 if current_signal else 0.0
    gbp_returns[-1] = 0.0

    gbp_df = _ohlcv_from_returns(1.3037, gbp_returns, idx)
    eur_df = _ohlcv_from_returns(1.1073, eur_returns, idx)
    row = gbp_df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=0.0010,
        adx=20.0,
        df=gbp_df,
        symbol="GBPUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        layer3={"cpd_leader_df": eur_df},
        backtest_mode=True,
        bar_time=gbp_df.index[-1],
    )


def test_v2_default_off_still_uses_current_bar(monkeypatch):
    monkeypatch.delenv("CPD_DIVERGENCE_REDESIGN_V2", raising=False)
    CpdDivergence.reset_dedup_state()

    cand = CpdDivergence().evaluate(_ctx(closed_signal=False, current_signal=True))

    assert cand is not None
    assert cand.signal == "BUY"


def test_v2_uses_closed_bar_not_current_intrabar(monkeypatch):
    monkeypatch.setenv("CPD_DIVERGENCE_REDESIGN_V2", "1")
    CpdDivergence.reset_dedup_state()

    cand = CpdDivergence().evaluate(_ctx(closed_signal=True, current_signal=False))

    assert cand is not None
    assert cand.signal == "BUY"


def test_v2_does_not_use_current_intrabar_spike(monkeypatch):
    monkeypatch.setenv("CPD_DIVERGENCE_REDESIGN_V2", "1")
    CpdDivergence.reset_dedup_state()

    cand = CpdDivergence().evaluate(_ctx(closed_signal=False, current_signal=True))

    assert cand is None


def test_v2_per_bar_dedup_blocks_repeat_emit(monkeypatch):
    monkeypatch.setenv("CPD_DIVERGENCE_REDESIGN_V2", "1")
    CpdDivergence.reset_dedup_state()
    strategy = CpdDivergence()
    ctx = _ctx(closed_signal=True, current_signal=False)

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is None


def test_v2_leader_data_is_cut_to_signal_bar(monkeypatch):
    monkeypatch.setenv("CPD_DIVERGENCE_REDESIGN_V2", "1")
    CpdDivergence.reset_dedup_state()
    ctx = _ctx(closed_signal=False, current_signal=False)
    leader = ctx.layer3["cpd_leader_df"].copy()
    leader.loc[leader.index[-1], "Close"] *= 1.01
    ctx.layer3["cpd_leader_df"] = leader

    cand = CpdDivergence().evaluate(ctx)

    assert cand is None


def test_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    from strategies.daytrade import DaytradeEngine

    engine = DaytradeEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "xs_momentum", 5.0)
    cpd = Candidate("BUY", 60, 1.0, 1.2, ["cpd"], "cpd_divergence", 4.5)

    monkeypatch.delenv("CPD_DIVERGENCE_REDESIGN_V2", raising=False)
    monkeypatch.delenv("CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, cpd], best) == []

    monkeypatch.setenv("CPD_DIVERGENCE_REDESIGN_V2", "1")
    monkeypatch.setenv("CPD_DIVERGENCE_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, cpd], best) == [cpd]
