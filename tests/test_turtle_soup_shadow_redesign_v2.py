from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.turtle_soup import TurtleSoup

LEVEL = 1.1010
ATR = 0.0010


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=130, freq="15min", tz="UTC")
    rows = [
        {"Open": 1.1002, "High": 1.1006, "Low": 1.0999, "Close": 1.1003}
        for _ in range(130)
    ]
    rows[-3] = {"Open": 1.1009, "High": 1.1035, "Low": 1.1000, "Close": 1.1012}
    if closed_signal:
        rows[-2] = {"Open": 1.1014, "High": 1.1015, "Low": 1.1004, "Close": 1.1006}
    else:
        rows[-2] = {"Open": 1.1008, "High": 1.1015, "Low": 1.1004, "Close": 1.1012}
    if current_signal:
        rows[-1] = {"Open": 1.1014, "High": 1.1015, "Low": 1.1004, "Close": 1.1006}
    else:
        rows[-1] = {"Open": 1.1008, "High": 1.1010, "Low": 1.1004, "Close": 1.1009}
    df = pd.DataFrame(rows, index=idx)
    df["atr"] = ATR
    df["adx"] = 20.0
    return df


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=ATR,
        adx=20.0,
        df=df,
        symbol="GBPUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def _strategy() -> TurtleSoup:
    strategy = TurtleSoup()
    strategy._find_fractal_levels = lambda df, n, lookback: ([(LEVEL, 20), (LEVEL, 40)], [])
    strategy._cluster_levels = lambda levels, atr: [(LEVEL, 2)] if levels else []
    return strategy


def test_v2_default_off_preserves_current_bar_reclaim(monkeypatch):
    monkeypatch.delenv("TURTLE_SOUP_REDESIGN_V2", raising=False)

    cand = _strategy().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "SELL"
    assert not any("TURTLE_SOUP_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_signal_and_ignores_current_bar(monkeypatch):
    monkeypatch.setenv("TURTLE_SOUP_REDESIGN_V2", "1")

    cand = _strategy().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.sl > 1.1035
    assert cand.tp < cand.sl
    assert any("closed_bar_time=2026-05-05T07:00:00+00:00" in reason for reason in cand.reasons)


def test_v2_rejects_current_bar_only_reclaim(monkeypatch):
    monkeypatch.setenv("TURTLE_SOUP_REDESIGN_V2", "1")

    cand = _strategy().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_live_dedups_same_symbol_signal_closed_bar(monkeypatch):
    monkeypatch.setenv("TURTLE_SOUP_REDESIGN_V2", "1")
    TurtleSoup._v2_seen_closed_bar_keys.clear()
    strategy = _strategy()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="BUY", confidence=80, sl=1.0, tp=2.0, reasons=[], entry_type="other", score=9.0)
    turtle = Candidate(
        signal="SELL",
        confidence=70,
        sl=2.0,
        tp=1.0,
        reasons=[],
        entry_type="turtle_soup",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("TURTLE_SOUP_REDESIGN_V2", "1")
    monkeypatch.delenv("TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, turtle], other) == []

    monkeypatch.setenv("TURTLE_SOUP_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, turtle], other) == [turtle]
