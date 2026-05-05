from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.gold_vol_break import GoldVolBreak


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    n = 32
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 2000.00)
    close = np.full(n, 2000.20)
    high = np.full(n, 2000.45)
    low = np.full(n, 1999.85)

    if closed_signal:
        open_[-2] = 2002.00
        close[-2] = 2003.00
        high[-2] = 2003.20
        low[-2] = 2001.80

    if current_signal:
        open_[-1] = 2002.00
        close[-1] = 2003.10
        high[-1] = 2003.30
        low[-1] = 2001.90
    else:
        open_[-1] = 2002.00
        close[-1] = 2002.20
        high[-1] = 2002.35
        low[-1] = 2001.90

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.90),
            "atr7": np.full(n, 1.00),
            "ema9": np.full(n, 2000.50),
            "ema21": np.full(n, 2000.00),
            "ema50": np.full(n, 1999.50),
            "ema200": np.full(n, 1999.00),
            "adx": np.full(n, 24.0),
            "adx_pos": np.full(n, 30.0),
            "adx_neg": np.full(n, 18.0),
            "rsi": np.full(n, 55.0),
            "rsi5": np.full(n, 55.0),
            "rsi9": np.full(n, 55.0),
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 45.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.full(n, 0.10),
            "bb_upper": np.full(n, 2002.0),
            "bb_mid": np.full(n, 2000.0),
            "bb_lower": np.full(n, 1998.0),
            "bb_pband": np.full(n, 0.60),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame) -> SignalContext:
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
        bb_upper=float(row["bb_upper"]),
        bb_mid=float(row["bb_mid"]),
        bb_lower=float(row["bb_lower"]),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="XAUUSD",
        tf="15m",
        is_jpy=False,
        pip_mult=100,
        df=df,
        htf={"agreement": "bull"},
        backtest_mode=True,
        bar_time=df.index[-1],
    )


def test_v2_default_off_preserves_legacy_current_bar_signal(monkeypatch):
    monkeypatch.delenv("GOLD_VOL_BREAK_REDESIGN_V2", raising=False)
    GoldVolBreak.reset_dedup_state()

    cand = GoldVolBreak().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("GOLD_VOL_BREAK_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_current_bar_only_signal(monkeypatch):
    monkeypatch.setenv("GOLD_VOL_BREAK_REDESIGN_V2", "1")
    GoldVolBreak.reset_dedup_state()

    cand = GoldVolBreak().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_uses_closed_signal_bar_with_current_entry(monkeypatch):
    monkeypatch.setenv("GOLD_VOL_BREAK_REDESIGN_V2", "1")
    GoldVolBreak.reset_dedup_state()

    cand = GoldVolBreak().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.sl, 2) == 2001.20
    assert round(cand.tp, 2) == 2005.20
    assert any("GOLD_VOL_BREAK_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_per_signal_bar_dedup_blocks_repeat(monkeypatch):
    monkeypatch.setenv("GOLD_VOL_BREAK_REDESIGN_V2", "1")
    GoldVolBreak.reset_dedup_state()
    strategy = GoldVolBreak()
    ctx = _ctx(_df(closed_signal=True, current_signal=False))

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    gold = Candidate("BUY", 70, 1.0, 2.0, [], "gold_vol_break", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("GOLD_VOL_BREAK_REDESIGN_V2", "1")
    monkeypatch.delenv("GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, gold], other) == []

    monkeypatch.setenv("GOLD_VOL_BREAK_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, gold], other) == [gold]
