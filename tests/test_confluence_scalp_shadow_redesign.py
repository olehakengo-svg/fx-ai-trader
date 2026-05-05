from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.context import SignalContext
from strategies.scalp.confluence_scalp import ConfluenceScalp


def _df(*, n=40, closed_signal=True, last_signal=True) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:15", periods=n, freq="15min", tz="UTC")

    open_ = np.full(n, 1.1000)
    high = np.full(n, 1.1007)
    low = np.full(n, 1.0993)
    close = np.full(n, 1.1000)

    ema9 = np.full(n, 1.0998)
    ema21 = np.full(n, 1.1002)
    rsi5 = np.full(n, 50.0)
    bbpb = np.full(n, 0.50)
    macdh = np.full(n, 0.0)

    def set_buy_signal(i: int):
        open_[i] = 1.1000
        close[i] = 1.1006
        high[i] = 1.1008
        low[i] = 1.0997
        ema9[i - 1] = 1.0998
        ema21[i - 1] = 1.1002
        ema9[i] = 1.1005
        ema21[i] = 1.1000
        rsi5[i] = 35.0
        bbpb[i] = 0.20
        macdh[i - 2] = -0.0002
        macdh[i - 1] = -0.0003
        macdh[i] = -0.0001

    def set_neutral(i: int):
        open_[i] = 1.1000
        close[i] = 1.1000
        high[i] = 1.1006
        low[i] = 1.0994
        ema9[i] = 1.0998
        ema21[i] = 1.1002
        rsi5[i] = 50.0
        bbpb[i] = 0.50
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
            "ema9": ema9,
            "ema21": ema21,
            "ema50": np.full(n, 1.1000),
            "ema200": np.full(n, 1.1000),
            "adx": np.full(n, 26.0),
            "adx_pos": np.full(n, 25.0),
            "adx_neg": np.full(n, 20.0),
            "rsi": np.full(n, 50.0),
            "rsi5": rsi5,
            "rsi9": np.full(n, 50.0),
            "stoch_k": np.full(n, 50.0),
            "stoch_d": np.full(n, 50.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": macdh,
            "bb_upper": np.full(n, 1.1040),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0960),
            "bb_pband": bbpb,
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
        htf={"agreement": "bull"},
        symbol="EURUSD=X",
        tf="15m",
        hour_utc=12,
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )


def test_v2_default_off_allows_existing_repeat(monkeypatch):
    monkeypatch.delenv("CONFLUENCE_SCALP_REDESIGN_V2", raising=False)
    ConfluenceScalp.reset_dedup_state()
    s = ConfluenceScalp()
    ctx = _ctx(_df(closed_signal=True, last_signal=True), backtest_mode=True)

    assert s.evaluate(ctx) is not None
    assert s.evaluate(ctx) is not None


def test_v2_per_bar_dedup_blocks_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_SCALP_REDESIGN_V2", "1")
    ConfluenceScalp.reset_dedup_state()
    s = ConfluenceScalp()
    bar_time = pd.Timestamp("2026-05-05 12:15", tz="UTC")
    ctx = _ctx(_df(closed_signal=True, last_signal=True), backtest_mode=True, bar_time=bar_time)

    first = s.evaluate(ctx)
    second = s.evaluate(ctx)

    assert first is not None
    assert first.signal == "BUY"
    assert second is None


def test_v2_live_ignores_in_progress_bar_trigger(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_SCALP_REDESIGN_V2", "1")
    ConfluenceScalp.reset_dedup_state()
    s = ConfluenceScalp()
    ctx = _ctx(_df(closed_signal=False, last_signal=True), backtest_mode=False)

    assert s.evaluate(ctx) is None


def test_v2_live_uses_closed_bar_trigger(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_SCALP_REDESIGN_V2", "1")
    ConfluenceScalp.reset_dedup_state()
    s = ConfluenceScalp()
    ctx = _ctx(_df(closed_signal=True, last_signal=False), backtest_mode=False)

    cand = s.evaluate(ctx)

    assert cand is not None
    assert cand.signal == "BUY"
