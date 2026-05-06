from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.vol_surge import VolSurgeDetector


def _df(*, closed_signal: bool, current_signal: bool, n: int = 40) -> pd.DataFrame:
    idx = pd.date_range("2026-05-05 08:00", periods=n, freq="5min", tz="UTC")
    open_ = np.full(n, 1.1000)
    high = np.full(n, 1.1006)
    low = np.full(n, 1.0994)
    close = np.full(n, 1.1000)
    volume = np.full(n, 100.0)
    bbpb = np.full(n, 0.50)
    rsi5 = np.full(n, 50.0)
    stoch_k = np.full(n, 50.0)
    stoch_d = np.full(n, 50.0)

    def set_climax_buy(i: int) -> None:
        open_[i] = 1.1000
        close[i] = 1.1008
        high[i] = 1.1010
        low[i] = 1.0995
        volume[i] = 300.0
        bbpb[i] = 0.12
        rsi5[i] = 32.0
        stoch_k[i] = 20.0
        stoch_d[i] = 18.0

    if closed_signal:
        set_climax_buy(n - 2)
    if current_signal:
        set_climax_buy(n - 1)

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": np.full(n, 1.1001),
            "ema21": np.full(n, 1.1000),
            "ema50": np.full(n, 1.1000),
            "ema200": np.full(n, 1.0990),
            "adx": np.full(n, 24.0),
            "adx_pos": np.full(n, 26.0),
            "adx_neg": np.full(n, 20.0),
            "rsi": rsi5,
            "rsi5": rsi5,
            "rsi9": rsi5,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "macd_hist": np.zeros(n),
            "bb_upper": np.full(n, 1.1040),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0960),
            "bb_pband": bbpb,
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True) -> SignalContext:
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
        ema200_bull=float(row["Close"]) > float(row["ema200"]),
        adx=float(row["adx"]),
        adx_pos=float(row["adx_pos"]),
        adx_neg=float(row["adx_neg"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        rsi9=float(row["rsi9"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        bbpb=float(row["bb_pband"]),
        bb_upper=float(row["bb_upper"]),
        bb_mid=float(row["bb_mid"]),
        bb_lower=float(row["bb_lower"]),
        prev_close=float(df["Close"].iloc[-2]),
        prev_open=float(df["Open"].iloc[-2]),
        symbol="EURUSD=X",
        tf="5m",
        hour_utc=8,
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
    )


def test_v2_default_off_preserves_current_bar_signal(monkeypatch):
    monkeypatch.delenv("VOL_SURGE_REDESIGN_V2", raising=False)
    VolSurgeDetector.reset_dedup_state()

    cand = VolSurgeDetector().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("VOL_SURGE_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_signal_bar_and_ignores_current_bar(monkeypatch):
    monkeypatch.setenv("VOL_SURGE_REDESIGN_V2", "1")
    VolSurgeDetector.reset_dedup_state()

    cand = VolSurgeDetector().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert any("closed-bar" in reason for reason in cand.reasons)
    assert any("closed_bar_time=2026-05-05 11:10:00+00:00" in reason for reason in cand.reasons)
    assert any("VOL_SURGE_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_blocks_current_bar_only_signal(monkeypatch):
    monkeypatch.setenv("VOL_SURGE_REDESIGN_V2", "1")
    VolSurgeDetector.reset_dedup_state()

    cand = VolSurgeDetector().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_dedups_same_symbol_mode_signal_bar(monkeypatch):
    monkeypatch.setenv("VOL_SURGE_REDESIGN_V2", "1")
    VolSurgeDetector.reset_dedup_state()
    strategy = VolSurgeDetector()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    vol_surge = Candidate("BUY", 70, 1.0, 2.0, [], "vol_surge_detector", 4.0)
    engine = ScalperEngine()

    monkeypatch.setenv("VOL_SURGE_REDESIGN_V2", "1")
    monkeypatch.delenv("VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, vol_surge], other) == []

    monkeypatch.setenv("VOL_SURGE_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, vol_surge], other) == [vol_surge]
