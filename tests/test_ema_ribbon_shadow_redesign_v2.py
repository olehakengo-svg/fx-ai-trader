from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.ema_ribbon import EmaRibbonRide


def _df(*, closed_signal: bool, current_signal: bool, n: int = 8) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 15:00", periods=n, freq="15min", tz="UTC")

    open_ = np.full(n, 1.1010)
    close = np.full(n, 1.1012)
    high = np.full(n, 1.1015)
    low = np.full(n, 1.1007)

    ema9 = np.full(n, 1.1010)
    ema21 = np.full(n, 1.1004)
    ema50 = np.full(n, 1.1000)
    ema200 = np.full(n, 1.0990)

    # Previous bar for closed signal context.
    close[-3] = 1.1010

    # Closed signal bar at original -2.
    open_[-2] = 1.1008 if closed_signal else 1.1014
    close[-2] = 1.1012 if closed_signal else 1.1010
    high[-2] = 1.1014
    low[-2] = 1.1006

    # Current/intrabar row at original -1.
    open_[-1] = 1.1009 if current_signal else 1.1014
    close[-1] = 1.1013 if current_signal else 1.1019
    high[-1] = 1.1015 if current_signal else 1.1020
    low[-1] = 1.1007 if current_signal else 1.1012

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
            "ema50": ema50,
            "ema200": ema200,
            "adx": np.full(n, 31.0),
            "adx_pos": np.full(n, 34.0),
            "adx_neg": np.full(n, 16.0),
            "rsi": np.full(n, 50.0),
            "rsi5": np.full(n, 50.0),
            "rsi9": np.full(n, 50.0),
            "stoch_k": np.full(n, 35.0),
            "stoch_d": np.full(n, 25.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.full(n, 0.0002),
            "bb_upper": np.full(n, 1.1040),
            "bb_mid": np.full(n, 1.1010),
            "bb_lower": np.full(n, 1.0980),
            "bb_pband": np.full(n, 0.55),
            "bb_width": np.linspace(0.0010, 0.0020, n),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True, bar_time=None) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ctx = SignalContext(
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
        bb_width=float(row["bb_width"]),
        bb_width_pct=0.5,
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "bull", "h4": {"score": 0.8}},
        backtest_mode=backtest_mode,
        bar_time=bar_time if bar_time is not None else df.index[-1],
        hour_utc=15,
    )
    ctx.high = float(row["High"])
    ctx.low = float(row["Low"])
    return ctx


def test_v2_default_off_preserves_current_bar_confirmation(monkeypatch):
    monkeypatch.delenv("EMA_RIBBON_REDESIGN_V2", raising=False)

    cand = EmaRibbonRide().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("EMA_RIBBON_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_and_r_floor_geometry(monkeypatch):
    monkeypatch.setenv("EMA_RIBBON_REDESIGN_V2", "1")
    EmaRibbonRide.reset_dedup_state()
    df = _df(closed_signal=True, current_signal=False)

    cand = EmaRibbonRide().evaluate(_ctx(df))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.sl == 1.1001
    assert round(cand.tp, 7) == 1.1046
    assert any("EMA_RIBBON_REDESIGN_V2" in reason for reason in cand.reasons)
    assert any("signal_bar_time=2026-05-05 14:45:00+00:00" in reason for reason in cand.reasons)


def test_v2_rejects_when_only_current_intrabar_confirms(monkeypatch):
    monkeypatch.setenv("EMA_RIBBON_REDESIGN_V2", "1")
    EmaRibbonRide.reset_dedup_state()

    cand = EmaRibbonRide().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_live_dedups_same_symbol_direction_signal_bar(monkeypatch):
    monkeypatch.setenv("EMA_RIBBON_REDESIGN_V2", "1")
    EmaRibbonRide.reset_dedup_state()
    strategy = EmaRibbonRide()
    df = _df(closed_signal=True, current_signal=False)
    ctx = _ctx(df, backtest_mode=False, bar_time=df.index[-1])

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("SELL", 70, 1.2, 1.0, ["best"], "other", 7.0)
    ema = Candidate("BUY", 65, 1.0, 1.2, ["ema"], "ema_ribbon_ride", 4.0)

    monkeypatch.setenv("EMA_RIBBON_REDESIGN_V2", "1")
    monkeypatch.delenv("EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, ema], best) == []

    monkeypatch.setenv("EMA_RIBBON_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, ema], best) == [ema]
