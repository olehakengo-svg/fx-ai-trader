from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.session_vol_expansion import SessionVolExpansion


def _df(*, signal_close: float = 1.10020,
        signal_open: float = 1.09960,
        final_time: str = "2026-05-05 07:45",
        current_close: float | None = None) -> pd.DataFrame:
    idx = pd.date_range(end=final_time, periods=130, freq="1min", tz="UTC")
    n = len(idx)
    open_ = np.full(n, 1.09955)
    high = np.full(n, 1.09975)
    low = np.full(n, 1.09935)
    close = np.full(n, 1.09955)

    # Asia/older context has enough range energy.
    high[:70] = 1.10080
    low[:70] = 1.09900
    open_[:70] = 1.09980
    close[:70] = 1.09980

    # Pre-breakout compression range, excluding the signal bar.
    open_[-31:-1] = 1.09970
    high[-31:-1] = 1.10000
    low[-31:-1] = 1.09990
    close[-31:-1] = 1.09995

    open_[-1] = signal_open
    close[-1] = signal_close
    high[-1] = max(signal_open, signal_close) + 0.00005
    low[-1] = min(signal_open, signal_close) - 0.00005

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
            "ema50": np.full(n, 1.09960),
            "adx": np.full(n, 26.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, symbol: str = "EURUSD=X",
         backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
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
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol=symbol,
        tf="1m",
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        htf={"agreement": "bull"},
        session={"spread_pip": 0.2},
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_default_off_preserves_existing_self_referential_range(monkeypatch):
    monkeypatch.delenv("SESSION_VOL_EXPANSION_REDESIGN_V2", raising=False)
    SessionVolExpansion.reset_dedup_state()

    cand = SessionVolExpansion().evaluate(_ctx(_df()))

    assert cand is None


def test_v2_breakout_uses_closed_prior_range_excluding_signal_bar(monkeypatch):
    monkeypatch.setenv("SESSION_VOL_EXPANSION_REDESIGN_V2", "1")
    SessionVolExpansion.reset_dedup_state()

    cand = SessionVolExpansion().evaluate(_ctx(_df()))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.entry_type == "session_vol_expansion"
    assert round(cand.sl, 5) == 1.09885
    assert round(cand.tp, 5) == 1.10170
    assert any("SESSION_VOL_EXPANSION_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_blocks_jpy_and_live_current_intrabar_breakout(monkeypatch):
    monkeypatch.setenv("SESSION_VOL_EXPANSION_REDESIGN_V2", "1")
    SessionVolExpansion.reset_dedup_state()

    assert SessionVolExpansion().evaluate(
        _ctx(_df(), symbol="USDJPY=X")
    ) is None

    closed_no_break = _df(signal_close=1.10002, final_time="2026-05-05 07:45")
    current_break = _df(signal_close=1.10002, final_time="2026-05-05 07:46", current_close=1.10035)
    current_break.iloc[:-1] = closed_no_break.iloc[1:].to_numpy()

    assert SessionVolExpansion().evaluate(
        _ctx(current_break, backtest_mode=False)
    ) is None


def test_v2_dedups_same_symbol_signal_bar_direction(monkeypatch):
    monkeypatch.setenv("SESSION_VOL_EXPANSION_REDESIGN_V2", "1")
    SessionVolExpansion.reset_dedup_state()
    ctx = _ctx(_df())
    strategy = SessionVolExpansion()

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    sve = Candidate("BUY", 70, 1.0, 2.0, [], "session_vol_expansion", 4.0)
    engine = ScalperEngine()

    monkeypatch.setenv("SESSION_VOL_EXPANSION_REDESIGN_V2", "1")
    monkeypatch.delenv("SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, sve], other) == []

    monkeypatch.setenv("SESSION_VOL_EXPANSION_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, sve], other) == [sve]
