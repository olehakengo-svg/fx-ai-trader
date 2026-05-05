from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.gold_pips import GoldPipsHunter


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    n = 10
    idx = pd.date_range(end="2026-05-05 07:09", periods=n, freq="1min", tz="UTC")

    open_ = np.array([1999.0, 1999.2, 1999.1, 1999.3, 1999.4,
                      1999.5, 1999.6, 1999.7, 1999.8, 1999.9])
    close = open_ + 0.20
    high = np.maximum(open_, close) + 0.10
    low = np.minimum(open_, close) - 0.10

    # Previous bar for the closed signal bar.
    open_[7] = 1999.80
    close[7] = 1999.70
    high[7] = 1999.90
    low[7] = 1999.60

    if closed_signal:
        open_[8] = 1999.70
        close[8] = 2000.30
        high[8] = 2000.40
        low[8] = 1999.40
    else:
        open_[8] = 1999.80
        close[8] = 1999.95
        high[8] = 2000.00
        low[8] = 1999.70

    if current_signal:
        open_[9] = 1999.95
        close[9] = 2000.40
        high[9] = 2000.50
        low[9] = 1999.80
    else:
        open_[9] = 2000.30
        close[9] = 2000.35
        high[9] = 2000.45
        low[9] = 2000.25

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 1.0),
            "atr7": np.full(n, 1.0),
            "ema9": np.full(n, 2000.10),
            "ema21": np.full(n, 2000.00),
            "ema50": np.full(n, 1999.80),
            "ema200": np.full(n, 1999.50),
            "adx": np.full(n, 26.0),
            "adx_pos": np.full(n, 28.0),
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
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="XAUUSD",
        tf="1m",
        hour_utc=7,
        is_jpy=False,
        pip_mult=100,
        df=df,
        backtest_mode=True,
        bar_time=df.index[-1],
    )


def test_v2_default_off_preserves_legacy_current_bar_signal(monkeypatch):
    monkeypatch.delenv("GOLD_PIPS_REDESIGN_V2", raising=False)
    GoldPipsHunter.reset_dedup_state()

    cand = GoldPipsHunter().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("GOLD_PIPS_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_current_bar_only_signal(monkeypatch):
    monkeypatch.setenv("GOLD_PIPS_REDESIGN_V2", "1")
    GoldPipsHunter.reset_dedup_state()

    cand = GoldPipsHunter().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_uses_closed_signal_bar_next_entry_and_rr_guard(monkeypatch):
    monkeypatch.setenv("GOLD_PIPS_REDESIGN_V2", "1")
    GoldPipsHunter.reset_dedup_state()

    cand = GoldPipsHunter().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.sl, 2) == 1999.20
    assert round(cand.tp, 2) == 2002.15
    assert (cand.tp - 2000.35) >= 1.5 * (2000.35 - cand.sl)
    assert any("GOLD_PIPS_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_per_bar_dedup_blocks_repeat(monkeypatch):
    monkeypatch.setenv("GOLD_PIPS_REDESIGN_V2", "1")
    GoldPipsHunter.reset_dedup_state()
    s = GoldPipsHunter()
    ctx = _ctx(_df(closed_signal=True, current_signal=False))

    assert s.evaluate(ctx) is not None
    assert s.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    gold = Candidate("BUY", 70, 1.0, 2.0, [], "gold_pips_hunter", 4.0)
    engine = ScalperEngine()

    monkeypatch.setenv("GOLD_PIPS_REDESIGN_V2", "1")
    monkeypatch.delenv("GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, gold], other) == []

    monkeypatch.setenv("GOLD_PIPS_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, gold], other) == [gold]
