from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.ema200_reversal import Ema200TrendReversal


def _df(*, n=25) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 14:00", periods=n, freq="15min", tz="UTC")
    close = np.full(n, 150.16)
    open_ = np.full(n, 150.14)
    high = np.full(n, 150.20)
    low = np.full(n, 150.10)
    ema200 = np.full(n, 150.00)
    macdh = np.full(n, 0.01)

    close[-4] = 149.94
    close[-3] = 150.08
    close[-2] = 150.12
    close[-1] = 150.16
    macdh[-2] = 0.01
    macdh[-1] = 0.03

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "atr": np.full(n, 0.50),
            "atr7": np.full(n, 0.50),
            "ema9": np.full(n, 150.08),
            "ema21": np.full(n, 150.04),
            "ema50": np.full(n, 150.02),
            "ema200": ema200,
            "rsi": np.full(n, 52.0),
            "macd_hist": macdh,
            "adx": np.full(n, 20.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, symbol="USDJPY=X", bar_time=None) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    is_jpy = "JPY" in symbol.upper()
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        ema50=float(row["ema50"]),
        ema200=float(row["ema200"]),
        rsi=float(row["rsi"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        adx=float(row["adx"]),
        symbol=symbol,
        tf="15m",
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        backtest_mode=True,
        bar_time=bar_time,
    )


def test_v2_default_off_preserves_existing_all_pair_signal(monkeypatch):
    monkeypatch.delenv("EMA200_REVERSAL_REDESIGN_V2", raising=False)
    Ema200TrendReversal.reset_dedup_state()

    cand = Ema200TrendReversal().evaluate(_ctx(_df(), symbol="EURJPY=X"))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("EMA200_REVERSAL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_routes_to_usd_jpy_only(monkeypatch):
    monkeypatch.setenv("EMA200_REVERSAL_REDESIGN_V2", "1")
    Ema200TrendReversal.reset_dedup_state()

    assert Ema200TrendReversal().evaluate(_ctx(_df(), symbol="EURJPY=X")) is None


def test_v2_per_bar_dedup_blocks_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("EMA200_REVERSAL_REDESIGN_V2", "1")
    Ema200TrendReversal.reset_dedup_state()
    strategy = Ema200TrendReversal()
    ctx = _ctx(_df(), symbol="USDJPY=X", bar_time=pd.Timestamp("2026-05-05 14:00", tz="UTC"))

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert first.signal == "BUY"
    assert second is None
    assert any("EMA200_REVERSAL_REDESIGN_V2" in reason for reason in first.reasons)


def test_v2_dedup_falls_back_to_df_latest_index(monkeypatch):
    monkeypatch.setenv("EMA200_REVERSAL_REDESIGN_V2", "1")
    Ema200TrendReversal.reset_dedup_state()
    strategy = Ema200TrendReversal()
    ctx = _ctx(_df(), symbol="USDJPY=X", bar_time=None)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    ema200 = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="ema200_trend_reversal",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("EMA200_REVERSAL_REDESIGN_V2", "1")
    monkeypatch.delenv("EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, ema200], other) == []

    monkeypatch.setenv("EMA200_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, ema200], other) == [ema200]
