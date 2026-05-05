from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.lin_reg_channel import LinRegChannel


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    n = 46
    idx = pd.date_range(end="2026-05-05 14:15", periods=n, freq="15min", tz="UTC")
    x = np.arange(n)
    base = 1.1000 + 0.0001 * x
    close = base + 0.0001 * np.sin(x * 0.9)
    open_ = close - 0.00002
    high = close + 0.00006
    low = close - 0.00003

    if closed_signal:
        close[-2] = base[-2] - 0.00015
        open_[-2] = close[-2] - 0.00008
    else:
        close[-2] = base[-2] + 0.00010
        open_[-2] = close[-2] + 0.00008
    high[-2] = close[-2] + 0.00006
    low[-2] = close[-2] - 0.00003

    if current_signal:
        close[-1] = base[-1] - 0.00015
        open_[-1] = close[-1] - 0.00008
    else:
        close[-1] = base[-1] - 0.000575
        open_[-1] = close[-1] + 0.00008
    high[-1] = close[-1] + 0.00006
    low[-1] = close[-1] - 0.00003

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": close + 0.00008,
            "ema21": close - 0.00008,
            "rsi": np.full(n, 50.0),
            "macd_hist": np.zeros(n),
            "adx": np.full(n, 25.0),
            "bb_pband": np.full(n, 0.5),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        rsi=float(row["rsi"]),
        adx=float(row["adx"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "mixed"},
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_current_bar_signal(monkeypatch):
    monkeypatch.delenv("LIN_REG_CHANNEL_REDESIGN_V2", raising=False)

    cand = LinRegChannel().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("LIN_REG_CHANNEL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_signal_and_next_bar_entry(monkeypatch):
    monkeypatch.setenv("LIN_REG_CHANNEL_REDESIGN_V2", "1")
    LinRegChannel.reset_dedup_state()

    df = _df(closed_signal=True, current_signal=False)
    cand = LinRegChannel().evaluate(_ctx(df))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.entry_type == "lin_reg_channel"
    assert cand.sl < df.iloc[-1]["Close"]
    assert cand.tp > df.iloc[-1]["Close"]
    assert any("signal_bar_time=2026-05-05 14:00:00+00:00" in reason for reason in cand.reasons)
    assert any("no_RR_TP_extension" in reason for reason in cand.reasons)


def test_v2_rejects_if_only_current_intrabar_signals(monkeypatch):
    monkeypatch.setenv("LIN_REG_CHANNEL_REDESIGN_V2", "1")
    LinRegChannel.reset_dedup_state()

    cand = LinRegChannel().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_live_dedups_same_symbol_direction_signal_bar(monkeypatch):
    monkeypatch.setenv("LIN_REG_CHANNEL_REDESIGN_V2", "1")
    LinRegChannel.reset_dedup_state()
    strategy = LinRegChannel()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    lrc = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="lin_reg_channel",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("LIN_REG_CHANNEL_REDESIGN_V2", "1")
    monkeypatch.delenv("LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, lrc], other) == []

    monkeypatch.setenv("LIN_REG_CHANNEL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, lrc], other) == [lrc]
