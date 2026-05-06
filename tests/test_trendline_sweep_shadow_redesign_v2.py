from __future__ import annotations

import numpy as np
import pandas as pd

from modules.demo_trader import DemoTrader
from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.trendline_sweep import TrendlineSweep


def _df() -> pd.DataFrame:
    n = 110
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": np.full(n, 1.1000),
            "High": np.full(n, 1.1010),
            "Low": np.full(n, 1.0990),
            "Close": np.full(n, 1.1002),
        },
        index=idx,
    )


def _ctx(symbol: str) -> SignalContext:
    df = _df()
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=0.0010,
        atr7=0.0010,
        adx=24.0,
        adx_pos=26.0,
        adx_neg=20.0,
        rsi=50.0,
        rsi5=50.0,
        rsi9=50.0,
        stoch_k=50.0,
        stoch_d=50.0,
        macdh=0.0,
        macdh_prev=0.0,
        bbpb=0.5,
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol=symbol,
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=12,
    )


def _force_sell_candidate(monkeypatch):
    monkeypatch.setattr(TrendlineSweep, "_find_swing_points", lambda self, df, n, lookback: ([], []))
    monkeypatch.setattr(
        TrendlineSweep,
        "_build_trendlines",
        lambda self, *args, **kwargs: [{"type": "descending", "respect_count": 2}],
    )
    monkeypatch.setattr(
        TrendlineSweep,
        "_detect_sweep_reclaim",
        lambda self, df, tl, atr: {
            "signal": "SELL",
            "sweep_extreme": 1.1020,
            "tl_value": 1.1005,
            "respect": 2,
        },
    )


def test_v2_default_off_preserves_legacy_eurgbp_signal(monkeypatch):
    monkeypatch.delenv("TRENDLINE_SWEEP_REDESIGN_V2", raising=False)
    _force_sell_candidate(monkeypatch)

    cand = TrendlineSweep().evaluate(_ctx("EURGBP=X"))

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.entry_type == "trendline_sweep"
    assert not any("TRENDLINE_SWEEP_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_keeps_eurgbp_signal_for_shadow_collection(monkeypatch):
    monkeypatch.setenv("TRENDLINE_SWEEP_REDESIGN_V2", "1")
    _force_sell_candidate(monkeypatch)

    cand = TrendlineSweep().evaluate(_ctx("EURGBP=X"))

    assert cand is not None
    assert cand.signal == "SELL"
    assert any("TRENDLINE_SWEEP_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_demo_routing_limits_elite_scope_to_eur_and_gbp(monkeypatch):
    monkeypatch.setenv("TRENDLINE_SWEEP_REDESIGN_V2", "1")
    trader = DemoTrader.__new__(DemoTrader)
    trader._oanda = type("OandaStub", (), {"get_strategy_mode": lambda self, entry_type: "auto"})()
    trader._promoted_types = {}

    assert trader._is_elite_live("trendline_sweep", "EUR_USD") is True
    assert trader._is_elite_live("trendline_sweep", "GBP_USD") is True
    assert trader._is_elite_live("trendline_sweep", "EUR_GBP") is False
    assert trader._is_trendline_sweep_v2_shadow_pair("trendline_sweep", "EUR_GBP") is True
    assert trader._is_promoted("trendline_sweep", "EUR_GBP") is False


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("BUY", 80, 1.0, 2.0, [], "other", 9.0)
    tls = Candidate("SELL", 70, 2.0, 1.0, [], "trendline_sweep", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("TRENDLINE_SWEEP_REDESIGN_V2", "1")
    monkeypatch.delenv("TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, tls], other) == []

    monkeypatch.setenv("TRENDLINE_SWEEP_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, tls], other) == [tls]
