from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.orb_trap import OrbTrap


def _df(*, entry: float, prev_high: float, atr: float) -> pd.DataFrame:
    idx = pd.date_range(start="2026-05-05 02:00", periods=25, freq="15min", tz="UTC")
    open_ = np.full(25, 1.1005)
    high = np.full(25, 1.1008)
    low = np.full(25, 1.1002)
    close = np.full(25, 1.1005)

    # London opening range: 07:00-07:30 UTC.
    for i in (20, 21):
        open_[i] = 1.1005
        high[i] = 1.1010
        low[i] = 1.1000
        close[i] = 1.1004

    # 07:45 UTC: confirmed close above OR high, then 08:00 returns inside OR.
    open_[23] = 1.1009
    high[23] = prev_high
    low[23] = 1.1008
    close[23] = 1.1012

    open_[24] = 1.1010
    high[24] = 1.1010
    low[24] = min(entry, 1.1007)
    close[24] = entry

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(25, 1000.0),
            "atr": np.full(25, atr),
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
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        ema9=1.1004,
        ema21=1.1006,
        adx=18.0,
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "mixed"},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_legacy_min_rr_tp_extension(monkeypatch):
    monkeypatch.delenv("ORB_TRAP_REDESIGN_V2", raising=False)

    cand = OrbTrap().evaluate(_ctx(_df(entry=1.1009, prev_high=1.1015, atr=0.0005)))

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.tp < 1.1000
    assert not any("ORB_TRAP_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_min_rr_shortfall_instead_of_extending_past_or_edge(monkeypatch):
    monkeypatch.setenv("ORB_TRAP_REDESIGN_V2", "1")

    cand = OrbTrap().evaluate(_ctx(_df(entry=1.1009, prev_high=1.1015, atr=0.0005)))

    assert cand is None


def test_v2_keeps_valid_or_edge_tp_when_rr_is_sufficient(monkeypatch):
    monkeypatch.setenv("ORB_TRAP_REDESIGN_V2", "1")

    cand = OrbTrap().evaluate(_ctx(_df(entry=1.1009, prev_high=1.10105, atr=0.0004)))

    assert cand is not None
    assert cand.signal == "SELL"
    assert cand.tp == 1.1000
    assert any("ORB_TRAP_REDESIGN_V2" in reason for reason in cand.reasons)


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="BUY", confidence=80, sl=1.0, tp=2.0, reasons=[], entry_type="other", score=9.0)
    orb = Candidate(
        signal="SELL",
        confidence=70,
        sl=2.0,
        tp=1.0,
        reasons=[],
        entry_type="orb_trap",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("ORB_TRAP_REDESIGN_V2", "1")
    monkeypatch.delenv("ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, orb], other) == []

    monkeypatch.setenv("ORB_TRAP_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, orb], other) == [orb]
