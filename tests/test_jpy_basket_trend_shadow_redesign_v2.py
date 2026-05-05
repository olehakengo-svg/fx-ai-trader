from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.jpy_basket_trend import JpyBasketTrend


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    n = 60
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 150.10)
    close = np.full(n, 150.20)
    high = np.full(n, 150.45)
    low = np.full(n, 150.05)

    if closed_signal:
        open_[-2] = 150.18
        close[-2] = 150.40
        high[-2] = 150.44
        low[-2] = 150.16
    else:
        open_[-2] = 150.18
        close[-2] = 150.24
        high[-2] = 150.28
        low[-2] = 150.14

    if current_signal:
        open_[-1] = 150.19
        close[-1] = 150.42
    else:
        open_[-1] = 150.45
        close[-1] = 150.42
    high[-1] = 150.48
    low[-1] = 150.18

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.10),
            "atr7": np.full(n, 0.10),
            "ema9": np.full(n, 150.35),
            "ema21": np.full(n, 150.30),
            "ema50": np.full(n, 150.26),
            "ema200": np.full(n, 150.00),
            "adx": np.full(n, 32.0),
            "adx_pos": np.full(n, 34.0),
            "adx_neg": np.full(n, 18.0),
            "rsi": np.full(n, 58.0),
            "rsi5": np.full(n, 58.0),
            "rsi9": np.full(n, 58.0),
            "stoch_k": np.full(n, 60.0),
            "stoch_d": np.full(n, 50.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.linspace(0.01, 0.20, n),
            "bb_upper": np.full(n, 151.0),
            "bb_mid": np.full(n, 150.0),
            "bb_lower": np.full(n, 149.0),
            "bb_pband": np.full(n, 0.65),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, basket: dict | None = None, htf_agreement: str = "mixed") -> SignalContext:
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
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="USDJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        df=df,
        htf={"agreement": htf_agreement, "jpy_basket": basket or {}},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
        ema200_bull=True,
    )


def _bull_basket() -> dict:
    return {
        "USDJPY": {"ema9": 150.35, "ema21": 150.30, "ema50": 150.26},
        "EURJPY": {"ema9": 162.40, "ema21": 162.10, "ema50": 161.90},
    }


def test_v2_default_off_preserves_legacy_current_bar_proxy_signal(monkeypatch):
    monkeypatch.delenv("JPY_BASKET_TREND_REDESIGN_V2", raising=False)
    JpyBasketTrend.reset_dedup_state()

    cand = JpyBasketTrend().evaluate(
        _ctx(_df(closed_signal=False, current_signal=True), htf_agreement="bull")
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("JPY_BASKET_TREND_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_current_bar_only_signal(monkeypatch):
    monkeypatch.setenv("JPY_BASKET_TREND_REDESIGN_V2", "1")
    JpyBasketTrend.reset_dedup_state()

    cand = JpyBasketTrend().evaluate(
        _ctx(_df(closed_signal=False, current_signal=True), basket=_bull_basket())
    )

    assert cand is None


def test_v2_requires_real_usdjpy_eurjpy_basket_po(monkeypatch):
    monkeypatch.setenv("JPY_BASKET_TREND_REDESIGN_V2", "1")
    JpyBasketTrend.reset_dedup_state()
    basket = _bull_basket()
    basket["EURJPY"] = {"ema9": 161.90, "ema21": 162.10, "ema50": 162.40}

    cand = JpyBasketTrend().evaluate(
        _ctx(_df(closed_signal=True, current_signal=False), basket=basket)
    )

    assert cand is None


def test_v2_uses_closed_bar_basket_signal_and_allows_mixed_htf(monkeypatch):
    monkeypatch.setenv("JPY_BASKET_TREND_REDESIGN_V2", "1")
    JpyBasketTrend.reset_dedup_state()

    cand = JpyBasketTrend().evaluate(
        _ctx(_df(closed_signal=True, current_signal=False), basket=_bull_basket())
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.sl, 2) == 150.23
    assert round(cand.tp, 2) == 150.67
    assert any("real basket PO" in reason for reason in cand.reasons)
    assert any("JPY_BASKET_TREND_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_per_signal_bar_dedup_blocks_repeat(monkeypatch):
    monkeypatch.setenv("JPY_BASKET_TREND_REDESIGN_V2", "1")
    JpyBasketTrend.reset_dedup_state()
    strategy = JpyBasketTrend()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), basket=_bull_basket())

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 151.0, 150.0, [], "other", 9.0)
    jpy = Candidate("BUY", 70, 150.0, 151.0, [], "jpy_basket_trend", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("JPY_BASKET_TREND_REDESIGN_V2", "1")
    monkeypatch.delenv("JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, jpy], other) == []

    monkeypatch.setenv("JPY_BASKET_TREND_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, jpy], other) == [jpy]
