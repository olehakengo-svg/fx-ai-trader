from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.sr_break_retest import SrBreakRetest


SR = 100.0


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    n = 90
    idx = pd.date_range(end="2026-05-05 07:15", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 99.82)
    high = np.full(n, 99.88)
    low = np.full(n, 99.76)
    close = np.full(n, 99.82)
    ema9 = np.full(n, 99.90)

    # Stable fractal SR level available before the breakout.
    high[20] = SR
    close[20] = 99.86
    open_[20] = 99.84

    # Breakout sequence: pre-bar below SR, breakout bar closes above SR.
    open_[-6] = 99.82
    high[-6] = 99.94
    low[-6] = 99.76
    close[-6] = 99.88

    open_[-5] = 99.90
    high[-5] = 100.28
    low[-5] = 99.86
    close[-5] = 100.22

    # Pullback setup bars after breakout.
    open_[-4] = 100.18
    high[-4] = 100.24
    low[-4] = 100.02
    close[-4] = 100.08
    open_[-3] = 100.06
    high[-3] = 100.16
    low[-3] = 99.98
    close[-3] = 100.02

    open_[-2] = 99.99 if closed_signal else 100.06
    high[-2] = 100.12
    low[-2] = 99.96
    close[-2] = 100.07 if closed_signal else 99.98
    ema9[-2] = 100.02

    open_[-1] = 99.99 if current_signal else 100.08
    high[-1] = 100.12
    low[-1] = 99.97
    close[-1] = 100.07 if current_signal else 100.03
    ema9[-1] = 100.02

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "atr": np.full(n, 0.20),
            "atr7": np.full(n, 0.20),
            "ema9": ema9,
            "ema21": np.full(n, 99.96),
            "ema50": np.full(n, 99.90),
            "ema200": np.full(n, 99.70),
            "rsi": np.full(n, 55.0),
            "macd_hist": np.full(n, 0.01),
            "bb_pband": np.full(n, 0.55),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True,
         weighted_levels: list | None = None) -> SignalContext:
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
        adx=25.0,
        adx_pos=31.0,
        adx_neg=14.0,
        rsi=float(row["rsi"]),
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
        htf={"agreement": "mixed"},
        layer3={"sr_weighted_levels": weighted_levels or []},
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_current_bar_retest(monkeypatch):
    monkeypatch.delenv("SR_BREAK_RETEST_REDESIGN_V2", raising=False)

    cand = SrBreakRetest().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("SR_BREAK_RETEST_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_signal_bar_and_ignores_current_bar(monkeypatch):
    monkeypatch.setenv("SR_BREAK_RETEST_REDESIGN_V2", "1")

    cand = SrBreakRetest().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.sl < SR < cand.tp
    assert any("signal_bar=2026-05-05 07:00:00+00:00" in reason for reason in cand.reasons)
    assert any("次バー以降で約定" in reason for reason in cand.reasons)


def test_v2_populates_sr_meta_from_weighted_level(monkeypatch):
    monkeypatch.setenv("SR_BREAK_RETEST_REDESIGN_V2", "1")

    cand = SrBreakRetest().evaluate(
        _ctx(
            _df(closed_signal=True, current_signal=False),
            weighted_levels=[
                {
                    "price": SR,
                    "strength": 0.91,
                    "touches": 7,
                    "days_span": 4.0,
                    "is_strong": True,
                }
            ],
        )
    )

    assert cand is not None
    assert cand.sr_meta == {
        "strength": 0.91,
        "touches": 7,
        "days_span": 4.0,
        "is_strong": True,
        "distance_atr": 0.35,
    }


def test_v2_rejects_if_closed_bar_has_no_retest_even_when_current_bar_does(monkeypatch):
    monkeypatch.setenv("SR_BREAK_RETEST_REDESIGN_V2", "1")

    cand = SrBreakRetest().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_live_dedups_same_symbol_side_closed_bar_sr_bucket(monkeypatch):
    monkeypatch.setenv("SR_BREAK_RETEST_REDESIGN_V2", "1")
    SrBreakRetest.reset_dedup_state()
    strategy = SrBreakRetest()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    sr_break = Candidate("BUY", 70, 1.0, 2.0, [], "sr_break_retest", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("SR_BREAK_RETEST_REDESIGN_V2", "1")
    monkeypatch.delenv("SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, sr_break], other) == []

    monkeypatch.setenv("SR_BREAK_RETEST_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, sr_break], other) == [sr_break]
