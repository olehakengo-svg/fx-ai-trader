from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.mtf_confluence import MtfReversalConfluence


def _df(*, n=40, closed_signal=True, last_signal=True) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:15", periods=n, freq="15min", tz="UTC")

    open_ = np.full(n, 1.1000)
    high = np.full(n, 1.1008)
    low = np.full(n, 1.0992)
    close = np.full(n, 1.1000)
    rsi5 = np.full(n, 50.0)
    stoch_k = np.full(n, 50.0)
    stoch_d = np.full(n, 50.0)
    macdh = np.full(n, 0.0)

    def set_buy_signal(i: int):
        close[i] = 1.1002
        rsi5[i] = 38.0
        stoch_k[i] = 35.0
        stoch_d[i] = 30.0
        macdh[i - 1] = 0.00010
        macdh[i] = 0.00020

    def set_neutral(i: int):
        close[i] = 1.1000
        rsi5[i] = 50.0
        stoch_k[i] = 50.0
        stoch_d[i] = 50.0
        macdh[i] = 0.0

    set_buy_signal(n - 2) if closed_signal else set_neutral(n - 2)
    set_buy_signal(n - 1) if last_signal else set_neutral(n - 1)

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": np.full(n, 1.1001),
            "ema21": np.full(n, 1.1000),
            "ema50": np.full(n, 1.1000),
            "ema200": np.full(n, 1.1000),
            "adx": np.full(n, 24.0),
            "adx_pos": np.full(n, 25.0),
            "adx_neg": np.full(n, 20.0),
            "rsi": np.full(n, 50.0),
            "rsi5": rsi5,
            "rsi9": np.full(n, 50.0),
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": macdh,
            "bb_upper": np.full(n, 1.1040),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0960),
            "bb_pband": np.full(n, 0.50),
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
        ema9_prev=float(df["ema9"].iloc[-2]),
        ema21_prev=float(df["ema21"].iloc[-2]),
        adx=float(row["adx"]),
        adx_pos=float(row["adx_pos"]),
        adx_neg=float(row["adx_neg"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        rsi9=float(row["rsi9"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(df["macd_hist"].iloc[-2]),
        macdh_prev2=float(df["macd_hist"].iloc[-3]),
        bbpb=float(row["bb_pband"]),
        bb_upper=float(row["bb_upper"]),
        bb_mid=float(row["bb_mid"]),
        bb_lower=float(row["bb_lower"]),
        prev_close=float(df["Close"].iloc[-2]),
        prev_open=float(df["Open"].iloc[-2]),
        prev_high=float(df["High"].iloc[-2]),
        prev_low=float(df["Low"].iloc[-2]),
        htf={"h1": {"rsi": 44.0, "score": 1.0}, "h4": {"rsi": 50.0}},
        symbol="EURUSD=X",
        tf="15m",
        hour_utc=12,
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )


def test_v2_default_off_keeps_existing_geometry_and_repeat(monkeypatch):
    monkeypatch.delenv("MTF_CONFLUENCE_REDESIGN_V2", raising=False)
    MtfReversalConfluence.reset_dedup_state()
    strategy = MtfReversalConfluence()
    ctx = _ctx(_df(closed_signal=True, last_signal=True), backtest_mode=True)

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is not None
    assert round(first.tp - ctx.entry, 7) == 0.0015
    assert round(ctx.entry - first.sl, 7) == 0.0005


def test_v2_uses_mr_geometry_and_dedups_same_symbol_strategy_signal_bar(monkeypatch):
    monkeypatch.setenv("MTF_CONFLUENCE_REDESIGN_V2", "1")
    MtfReversalConfluence.reset_dedup_state()
    strategy = MtfReversalConfluence()
    bar_time = pd.Timestamp("2026-05-05 12:15", tz="UTC")
    ctx = _ctx(_df(closed_signal=True, last_signal=True), backtest_mode=True, bar_time=bar_time)

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert first.signal == "BUY"
    assert round(first.tp - ctx.entry, 7) == 0.0008
    assert round(ctx.entry - first.sl, 7) == 0.0012
    assert any("redesign_v2 MR geometry" in r for r in first.reasons)
    assert second is None


def test_v2_live_ignores_in_progress_bar_trigger(monkeypatch):
    monkeypatch.setenv("MTF_CONFLUENCE_REDESIGN_V2", "1")
    MtfReversalConfluence.reset_dedup_state()
    ctx = _ctx(_df(closed_signal=False, last_signal=True), backtest_mode=False)

    assert MtfReversalConfluence().evaluate(ctx) is None


def test_v2_live_uses_closed_bar_trigger(monkeypatch):
    monkeypatch.setenv("MTF_CONFLUENCE_REDESIGN_V2", "1")
    MtfReversalConfluence.reset_dedup_state()
    ctx = _ctx(_df(closed_signal=True, last_signal=False), backtest_mode=False)

    cand = MtfReversalConfluence().evaluate(ctx)

    assert cand is not None
    assert cand.signal == "BUY"


def test_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "bb_rsi_reversion", 6.0)
    mtf = Candidate("BUY", 60, 1.0, 1.2, ["mtf"], "mtf_reversal_confluence", 5.0)

    monkeypatch.delenv("MTF_CONFLUENCE_REDESIGN_V2", raising=False)
    monkeypatch.delenv("MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, mtf], best) == []

    monkeypatch.setenv("MTF_CONFLUENCE_REDESIGN_V2", "1")
    monkeypatch.setenv("MTF_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, mtf], best) == [mtf]
