from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.asia_range_fade_v1 import AsiaRangeFadeV1


def _df(*, prior_range_pips: float, current_high: float) -> pd.DataFrame:
    n = 26
    idx = pd.date_range(end="2026-05-05 03:00", periods=n, freq="15min", tz="UTC")
    low = np.full(n, 1.1000)
    high = np.full(n, 1.1000 + prior_range_pips / 10000.0)
    open_ = np.full(n, 1.1002)
    close = np.full(n, 1.1002)

    # Signal bar: upper-wick rejection at or beyond the prior/current range high.
    high[-1] = current_high
    low[-1] = 1.10056
    open_[-1] = current_high - 0.00004
    close[-1] = 1.10057

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0005),
            "rsi": np.full(n, 75.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        rsi=float(row["rsi"]),
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_legacy_current_bar_range_boundary(monkeypatch):
    monkeypatch.delenv("ASIA_RANGE_FADE_V1_REDESIGN_V2", raising=False)

    # Prior 24 bars are a 4-pip range, below LOCK minimum. The current
    # rejection bar extends the high enough for the legacy window to pass.
    cand = AsiaRangeFadeV1().evaluate(_ctx(_df(prior_range_pips=4.0, current_high=1.10065)))

    assert cand is not None
    assert cand.signal == "SELL"


def test_v2_uses_closed_prior_range_and_rejects_self_created_boundary(monkeypatch):
    monkeypatch.setenv("ASIA_RANGE_FADE_V1_REDESIGN_V2", "1")

    cand = AsiaRangeFadeV1().evaluate(_ctx(_df(prior_range_pips=4.0, current_high=1.10065)))

    assert cand is None


def test_v2_still_fades_touch_of_valid_closed_prior_range(monkeypatch):
    monkeypatch.setenv("ASIA_RANGE_FADE_V1_REDESIGN_V2", "1")

    cand = AsiaRangeFadeV1().evaluate(_ctx(_df(prior_range_pips=6.0, current_high=1.10065)))

    assert cand is not None
    assert cand.signal == "SELL"
    assert round(cand.sl, 5) == 1.10085
    assert any("closed prior range" in reason for reason in cand.reasons)


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="BUY", confidence=80, sl=1.0, tp=2.0, reasons=[], entry_type="other", score=9.0)
    asia = Candidate(
        signal="SELL",
        confidence=70,
        sl=2.0,
        tp=1.0,
        reasons=[],
        entry_type="asia_range_fade_v1",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("ASIA_RANGE_FADE_V1_REDESIGN_V2", "1")
    monkeypatch.delenv("ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, asia], other) == []

    monkeypatch.setenv("ASIA_RANGE_FADE_V1_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, asia], other) == [asia]
