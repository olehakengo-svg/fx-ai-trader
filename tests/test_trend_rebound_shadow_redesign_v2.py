from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.trend_rebound import TrendRebound


def _df(*, entry: float, close_10_bars_ago: float, prev_stoch_k: float = 8.0) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=10, freq="15min", tz="UTC")
    closes = [close_10_bars_ago] + [entry - 0.01] * 8 + [entry]
    rows = []
    for i, close in enumerate(closes):
        rows.append(
            {
                "Open": close - 0.01,
                "High": close + 0.04,
                "Low": close - 0.04,
                "Close": close,
                "stoch_k": prev_stoch_k if i == 8 else 10.0,
                "macd_hist": -0.05 + i * 0.01,
            }
        )
    return pd.DataFrame(rows, index=idx)


def _ctx(df: pd.DataFrame, *, side: str, pip_mult: int = 100) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    is_buy = side == "BUY"
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Close"]) - 0.02 if is_buy else float(row["Close"]) + 0.02,
        atr=0.08,
        atr7=0.08,
        ema9=99.90 if is_buy else 100.10,
        ema21=100.00 if is_buy else 100.00,
        rsi=25.0 if is_buy else 75.0,
        rsi5=25.0 if is_buy else 75.0,
        rsi9=25.0 if is_buy else 75.0,
        stoch_k=10.0 if is_buy else 90.0,
        stoch_d=8.0 if is_buy else 92.0,
        adx=30.0,
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        macdh_prev2=float(df.iloc[-3]["macd_hist"]),
        bbpb=0.10 if is_buy else 0.90,
        bb_lower=float(row["Close"]) - 0.10,
        bb_mid=float(row["Close"]),
        bb_upper=float(row["Close"]) + 0.10,
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="USDJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=pip_mult,
        df=df,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_buy_tail_continuation_signal(monkeypatch):
    monkeypatch.delenv("TREND_REBOUND_REDESIGN_V2", raising=False)
    df = _df(entry=100.00, close_10_bars_ago=100.20)

    cand = TrendRebound().evaluate(_ctx(df, side="BUY"))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("TREND_REBOUND_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_buy_when_momentum_is_excessive_down_continuation(monkeypatch):
    monkeypatch.setenv("TREND_REBOUND_REDESIGN_V2", "1")
    df = _df(entry=100.00, close_10_bars_ago=100.20)

    assert TrendRebound().evaluate(_ctx(df, side="BUY")) is None


def test_v2_allows_buy_when_momentum_is_neutral_rebound(monkeypatch):
    monkeypatch.setenv("TREND_REBOUND_REDESIGN_V2", "1")
    df = _df(entry=100.00, close_10_bars_ago=100.05)

    cand = TrendRebound().evaluate(_ctx(df, side="BUY"))

    assert cand is not None
    assert cand.signal == "BUY"
    assert any("TREND_REBOUND_REDESIGN_V2 momentum gate" in reason for reason in cand.reasons)


def test_v2_rejects_sell_when_momentum_is_excessive_up_continuation(monkeypatch):
    monkeypatch.setenv("TREND_REBOUND_REDESIGN_V2", "1")
    df = _df(entry=100.00, close_10_bars_ago=99.80, prev_stoch_k=92.0)

    assert TrendRebound().evaluate(_ctx(df, side="SELL")) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("BUY", 70, 1.0, 2.0, ["best"], "other", 7.0)
    trend = Candidate("SELL", 65, 2.0, 1.0, ["trend"], "trend_rebound", 3.5)

    monkeypatch.setenv("TREND_REBOUND_REDESIGN_V2", "1")
    monkeypatch.delenv("TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, trend], best) == []

    monkeypatch.setenv("TREND_REBOUND_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, trend], best) == [trend]
