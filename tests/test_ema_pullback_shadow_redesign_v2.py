from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.ema_pullback import EmaPullback


def _df(*, closed_signal: bool, current_signal: bool, n: int = 8) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 15:00", periods=n, freq="15min", tz="UTC")

    open_ = np.full(n, 1.1010)
    close = np.full(n, 1.1012)
    high = np.full(n, 1.1018)
    low = np.full(n, 1.1008)

    ema9 = np.full(n, 1.1010)
    ema21 = np.full(n, 1.1006)

    # Previous bar for the closed signal bar.
    close[-3] = 1.1010
    low[-3] = 1.1007
    high[-3] = 1.1015

    # Closed signal bar at original -2.
    open_[-2] = 1.1010 if closed_signal else 1.1018
    close[-2] = 1.1018 if closed_signal else 1.1010
    high[-2] = 1.1020
    low[-2] = 1.1009

    # Current/intrabar row at original -1.
    open_[-1] = 1.1010 if current_signal else 1.1018
    close[-1] = 1.1018 if current_signal else 1.1010
    high[-1] = 1.1020
    low[-1] = 1.1007

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
            "ema200": np.full(n, 1.0990),
            "adx": np.full(n, 30.0),
            "adx_pos": np.full(n, 32.0),
            "adx_neg": np.full(n, 15.0),
            "rsi": np.full(n, 55.0),
            "rsi5": np.full(n, 55.0),
            "rsi9": np.full(n, 55.0),
            "stoch_k": np.full(n, 60.0),
            "stoch_d": np.full(n, 45.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.full(n, 0.0002),
            "bb_upper": np.full(n, 1.1040),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0960),
            "bb_pband": np.full(n, 0.55),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True, bar_time=None) -> SignalContext:
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
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "bull", "h4": {"score": 0.8}, "d1": {"label": "データ不足", "score": 0.0}},
        backtest_mode=backtest_mode,
        bar_time=bar_time if bar_time is not None else df.index[-1],
    )


def test_v2_default_off_preserves_current_bar_confirmation(monkeypatch):
    monkeypatch.delenv("EMA_PULLBACK_REDESIGN_V2", raising=False)

    cand = EmaPullback().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("EMA_PULLBACK_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_and_ignores_current_intrabar(monkeypatch):
    monkeypatch.setenv("EMA_PULLBACK_REDESIGN_V2", "1")
    EmaPullback.reset_dedup_state()

    cand = EmaPullback().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.sl == min(1.1009, 1.1006 - 0.0010 * 0.6)
    assert any("EMA_PULLBACK_REDESIGN_V2" in reason for reason in cand.reasons)
    assert any("signal_bar_time=2026-05-05 14:45:00+00:00" in reason for reason in cand.reasons)


def test_v2_rejects_when_only_current_intrabar_confirms(monkeypatch):
    monkeypatch.setenv("EMA_PULLBACK_REDESIGN_V2", "1")
    EmaPullback.reset_dedup_state()

    cand = EmaPullback().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_live_dedups_same_symbol_direction_signal_bar(monkeypatch):
    monkeypatch.setenv("EMA_PULLBACK_REDESIGN_V2", "1")
    EmaPullback.reset_dedup_state()
    strategy = EmaPullback()
    df = _df(closed_signal=True, current_signal=False)
    ctx = _ctx(df, backtest_mode=False, bar_time=df.index[-1])

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("SELL", 70, 1.2, 1.0, ["best"], "other", 7.0)
    ema = Candidate("BUY", 65, 1.0, 1.2, ["ema"], "ema_pullback", 4.0)

    monkeypatch.setenv("EMA_PULLBACK_REDESIGN_V2", "1")
    monkeypatch.delenv("EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, ema], best) == []

    monkeypatch.setenv("EMA_PULLBACK_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, ema], best) == [ema]
