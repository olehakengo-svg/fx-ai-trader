from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.london_session_breakout import LondonSessionBreakout


def _df(*, signal_close: float, signal_open: float | None = None,
        final_time: str = "2026-05-05 07:45",
        current_close: float | None = None) -> pd.DataFrame:
    idx = pd.date_range(end=final_time, periods=660, freq="15min", tz="UTC")
    n = len(idx)
    open_ = np.full(n, 1.09900)
    high = np.full(n, 1.09920)
    low = np.full(n, 1.09880)
    close = np.full(n, 1.09900)

    for day in sorted(set(idx.date)):
        asia_mask = (idx.date == day) & (idx.hour < 7)
        open_[asia_mask] = 1.09900
        high[asia_mask] = 1.10000
        low[asia_mask] = 1.09800
        close[asia_mask] = 1.09900

    sig_open = signal_close - 0.00025 if signal_open is None else signal_open
    open_[-1] = sig_open
    close[-1] = signal_close
    high[-1] = max(sig_open, signal_close) + 0.00005
    low[-1] = min(sig_open, signal_close) - 0.00005

    if current_close is not None:
        open_[-1] = current_close - 0.00010
        close[-1] = current_close
        high[-1] = current_close + 0.00005
        low[-1] = current_close - 0.00005

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.00050),
            "atr7": np.full(n, 0.00050),
            "ema9": np.full(n, 1.10010),
            "ema21": np.full(n, 1.09980),
            "ema50": np.full(n, 1.09950),
            "adx": np.full(n, 26.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, symbol: str = "EURUSD=X",
         backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    is_jpy = "JPY" in symbol.upper()
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        ema50=float(row["ema50"]),
        adx=float(row["adx"]),
        symbol=symbol,
        tf="15m",
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        htf={"agreement": "bull"},
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_hard_disable(monkeypatch):
    monkeypatch.delenv("LONDON_SESSION_BREAKOUT_REDESIGN_V2", raising=False)
    LondonSessionBreakout.reset_dedup_state()

    cand = LondonSessionBreakout().evaluate(_ctx(_df(signal_close=1.10030)))

    assert cand is None


def test_v2_breakout_fires_for_london_pair_on_closed_07utc_bar(monkeypatch):
    monkeypatch.setenv("LONDON_SESSION_BREAKOUT_REDESIGN_V2", "1")
    LondonSessionBreakout.reset_dedup_state()

    cand = LondonSessionBreakout().evaluate(_ctx(_df(signal_close=1.10030)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.entry_type == "london_session_breakout"
    assert round(cand.sl, 5) == 1.09795
    assert round(cand.tp, 5) == 1.10383
    assert any("LONDON_SESSION_BREAKOUT_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_blocks_jpy_and_non_07utc_bars(monkeypatch):
    monkeypatch.setenv("LONDON_SESSION_BREAKOUT_REDESIGN_V2", "1")
    LondonSessionBreakout.reset_dedup_state()

    assert LondonSessionBreakout().evaluate(
        _ctx(_df(signal_close=1.10030), symbol="USDJPY=X")
    ) is None
    assert LondonSessionBreakout().evaluate(
        _ctx(_df(signal_close=1.10030, final_time="2026-05-05 08:00"))
    ) is None


def test_v2_live_uses_closed_bar_not_current_intrabar(monkeypatch):
    monkeypatch.setenv("LONDON_SESSION_BREAKOUT_REDESIGN_V2", "1")
    LondonSessionBreakout.reset_dedup_state()
    closed = _df(signal_close=1.10002, final_time="2026-05-05 07:45")
    current = _df(signal_close=1.10002, final_time="2026-05-05 08:00", current_close=1.10040)
    current.iloc[:-1] = closed.iloc[1:].to_numpy()

    cand = LondonSessionBreakout().evaluate(_ctx(current, backtest_mode=False))

    assert cand is None


def test_v2_dedup_blocks_same_symbol_date_direction(monkeypatch):
    monkeypatch.setenv("LONDON_SESSION_BREAKOUT_REDESIGN_V2", "1")
    LondonSessionBreakout.reset_dedup_state()
    strategy = LondonSessionBreakout()
    ctx = _ctx(_df(signal_close=1.10030))

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    london = Candidate("BUY", 70, 1.0, 2.0, [], "london_session_breakout", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("LONDON_SESSION_BREAKOUT_REDESIGN_V2", "1")
    monkeypatch.delenv("LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, london], other) == []

    monkeypatch.setenv("LONDON_SESSION_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, london], other) == [london]
