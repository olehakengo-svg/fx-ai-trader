from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.ema_cross import EmaCross


def _df(*, closed_signal: bool, current_signal: bool, n: int = 14) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 15:00", periods=n, freq="15min", tz="UTC")

    open_ = np.full(n, 1.1010)
    close = np.full(n, 1.1011)
    high = np.full(n, 1.1015)
    low = np.full(n, 1.1008)
    ema9 = np.full(n, 1.1014)
    ema21 = np.full(n, 1.1006)
    macdh = np.full(n, 0.0001)
    rsi = np.full(n, 55.0)
    adx = np.full(n, 30.0)

    ema9[:-5] = 1.1000
    ema21[:-5] = 1.1008

    # One BUY cross that is valid relative to both the full df (-5) and the
    # V2 closed-bar df (ctx.df.iloc[:-1], where it is -4).
    ema9[-6] = 1.1000
    ema21[-6] = 1.1008
    ema9[-5] = 1.1012
    ema21[-5] = 1.1007
    high[-5] = 1.1024

    # Pullback after the cross.
    low[-4] = 1.1009
    low[-3] = 1.1008

    # Closed signal bar at original -2.
    open_[-2] = 1.1010 if closed_signal else 1.1018
    close[-2] = 1.1018 if closed_signal else 1.1010
    high[-2] = 1.1020
    low[-2] = 1.1009
    macdh[-2] = 0.0002 if closed_signal else -0.0002
    rsi[-2] = 56.0 if closed_signal else 72.0
    ema9[-2] = 1.1015
    ema21[-2] = 1.1007

    # Current/intrabar row at original -1.
    open_[-1] = 1.1010 if current_signal else 1.1018
    close[-1] = 1.1018 if current_signal else 1.1010
    high[-1] = 1.1021
    low[-1] = 1.1009
    macdh[-1] = 0.0002 if current_signal else -0.0002
    rsi[-1] = 56.0 if current_signal else 72.0
    ema9[-1] = 1.1015
    ema21[-1] = 1.1007

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
            "ema50": np.full(n, 1.0995),
            "ema200": np.full(n, 1.0980),
            "adx": adx,
            "adx_pos": np.full(n, 32.0),
            "adx_neg": np.full(n, 15.0),
            "rsi": rsi,
            "rsi5": rsi,
            "rsi9": rsi,
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 55.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": macdh,
            "bb_upper": np.full(n, 1.1040),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0960),
            "bb_pband": np.full(n, 0.75),
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
        ema_score=(float(row["ema9"]) - float(row["ema21"])) / float(row["atr"]),
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
    monkeypatch.delenv("EMA_CROSS_REDESIGN_V2", raising=False)

    cand = EmaCross().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("EMA_CROSS_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_and_ignores_current_intrabar(monkeypatch):
    monkeypatch.setenv("EMA_CROSS_REDESIGN_V2", "1")
    EmaCross.reset_dedup_state()

    cand = EmaCross().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert any("EMA_CROSS_REDESIGN_V2" in reason for reason in cand.reasons)
    assert any("signal_bar_time=2026-05-05 14:45:00+00:00" in reason for reason in cand.reasons)


def test_v2_rejects_when_only_current_intrabar_confirms(monkeypatch):
    monkeypatch.setenv("EMA_CROSS_REDESIGN_V2", "1")
    EmaCross.reset_dedup_state()

    cand = EmaCross().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_live_dedups_same_symbol_direction_signal_bar(monkeypatch):
    monkeypatch.setenv("EMA_CROSS_REDESIGN_V2", "1")
    EmaCross.reset_dedup_state()
    strategy = EmaCross()
    df = _df(closed_signal=True, current_signal=False)
    ctx = _ctx(df, backtest_mode=False, bar_time=df.index[-1])

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = DaytradeEngine()
    best = Candidate("SELL", 70, 1.2, 1.0, ["best"], "other", 7.0)
    ema = Candidate("BUY", 65, 1.0, 1.2, ["ema"], "ema_cross", 4.0)

    monkeypatch.setenv("EMA_CROSS_REDESIGN_V2", "1")
    monkeypatch.delenv("EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, ema], best) == []

    monkeypatch.setenv("EMA_CROSS_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, ema], best) == [ema]
