from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade.alpha_intraday_seasonality import IntradaySeasonality


def _df(*, days=240, ret=-0.0010, noise=0.00005) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:00", periods=days * 24, freq="1h", tz="UTC")
    open_ = np.full(len(idx), 1.1000)
    close = np.full(len(idx), 1.1000)
    high = np.full(len(idx), 1.1008)
    low = np.full(len(idx), 1.0992)

    target_dow = idx[-1].weekday()
    target_hour = idx[-1].hour
    k = 0
    for i, ts in enumerate(idx[:-1]):
        if ts.weekday() == target_dow and ts.hour == target_hour:
            r = ret + (noise if k % 2 == 0 else -noise)
            close[i] = open_[i] * (1.0 + r)
            high[i] = max(open_[i], close[i]) + 0.0002
            low[i] = min(open_[i], close[i]) - 0.0002
            k += 1

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, htf_agreement="mixed") -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=0.0010,
        htf={"agreement": htf_agreement},
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        bar_time=df.index[-1],
    )


def test_default_path_keeps_htf_hard_block(monkeypatch):
    monkeypatch.delenv("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2", raising=False)

    got = IntradaySeasonality().evaluate(_ctx(_df(ret=-0.0010), htf_agreement="bull"))

    assert got is None


def test_v2_softens_htf_block_for_bucket_tail(monkeypatch):
    monkeypatch.setenv("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2", "1")

    got = IntradaySeasonality().evaluate(_ctx(_df(ret=-0.0010), htf_agreement="bull"))

    assert got is not None
    assert got.signal == "SELL"
    assert any("V2 thin seasonality" in reason for reason in got.reasons)


def test_v2_requires_at_least_30_same_weekday_hour_samples(monkeypatch):
    monkeypatch.setenv("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2", "1")

    got = IntradaySeasonality().evaluate(_ctx(_df(days=120, ret=0.0010), htf_agreement="mixed"))

    assert got is None


def test_v2_uses_distribution_geometry_not_atr_bracket(monkeypatch):
    monkeypatch.setenv("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2", "1")

    got = IntradaySeasonality().evaluate(_ctx(_df(ret=0.0010), htf_agreement="mixed"))

    assert got is not None
    assert got.signal == "BUY"
    assert got.tp - 1.1000 < 0.0015
    assert 1.1000 - got.sl < 0.0015


def test_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    from strategies.daytrade import DaytradeEngine

    engine = DaytradeEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "xs_momentum", 5.0)
    seasonality = Candidate("SELL", 60, 1.2, 0.9, ["ais"], "intraday_seasonality", 4.5)

    monkeypatch.delenv("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2", raising=False)
    monkeypatch.delenv("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, seasonality], best) == []

    monkeypatch.setenv("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2", "1")
    monkeypatch.setenv("ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, seasonality], best) == [seasonality]
