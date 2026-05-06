from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.mtf_counter_trend_scalp import MtfCounterTrendScalp


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    idx = pd.date_range("2026-05-05 10:00", periods=3, freq="min", tz="UTC")
    rows = [
        {
            "Open": 100.030,
            "High": 100.040,
            "Low": 99.990,
            "Close": 100.000,
        },
        {
            "Open": 99.990 if closed_signal else 100.030,
            "High": 100.060,
            "Low": 99.980,
            "Close": 100.040 if closed_signal else 100.000,
        },
        {
            "Open": 99.995 if current_signal else 100.060,
            "High": 100.080,
            "Low": 99.990,
            "Close": 100.055 if current_signal else 100.050,
        },
    ]
    df = pd.DataFrame(rows, index=idx)
    for col, val in {
        "atr": 0.020,
        "atr7": 0.020,
        "ema9": 100.0,
        "ema21": 100.0,
        "ema50": 100.0,
        "ema200": 100.0,
        "rsi": 45.0,
        "rsi5": 45.0,
        "adx": 20.0,
        "bb_pband": 0.50,
    }.items():
        df[col] = val
    df["stoch_k"] = [40.0, 60.0 if closed_signal else 40.0, 60.0 if current_signal else 40.0]
    df["stoch_d"] = [60.0, 40.0 if closed_signal else 60.0, 40.0 if current_signal else 60.0]
    return df


def _htf(*, m15_closed=True, m5_closed=True) -> dict:
    return {
        "m15": {
            "adx": 28.0,
            "ema9": 99.90,
            "ema21": 100.10,
            "is_closed": m15_closed,
        },
        "m5": {
            "bbpb": 0.05,
            "high": 100.100,
            "low": 99.950,
            "rsi_div_bull": True,
            "rsi_div_bear": False,
            "rsi14": 32.0,
            "is_closed": m5_closed,
        },
    }


def _ctx(*, closed_signal: bool, current_signal: bool, backtest_mode=True,
         m15_closed=True, m5_closed=True) -> SignalContext:
    df = _df(closed_signal=closed_signal, current_signal=current_signal)
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        adx=float(row["adx"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="USDJPY=X",
        tf="1m",
        hour_utc=10,
        is_jpy=True,
        pip_mult=100,
        htf=_htf(m15_closed=m15_closed, m5_closed=m5_closed),
        df=df,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
    )


def _patch_friction(monkeypatch):
    import strategies.scalp.mtf_counter_trend_scalp as mod

    monkeypatch.setattr(mod, "hour_mult_for", lambda _hour: 0.80)


def test_v2_default_off_keeps_current_bar_confirmation(monkeypatch):
    _patch_friction(monkeypatch)
    monkeypatch.delenv("MTF_COUNTER_TREND_SCALP_REDESIGN_V2", raising=False)
    strategy = MtfCounterTrendScalp()
    ctx = _ctx(closed_signal=False, current_signal=True)

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is not None
    assert first.signal == "BUY"
    assert not any("MTF_COUNTER_TREND_SCALP_REDESIGN_V2" in r for r in first.reasons)


def test_v2_ignores_in_progress_current_bar_trigger(monkeypatch):
    _patch_friction(monkeypatch)
    monkeypatch.setenv("MTF_COUNTER_TREND_SCALP_REDESIGN_V2", "1")

    cand = MtfCounterTrendScalp().evaluate(_ctx(closed_signal=False, current_signal=True))

    assert cand is None


def test_v2_uses_closed_1m_signal_bar_with_current_execution(monkeypatch):
    _patch_friction(monkeypatch)
    monkeypatch.setenv("MTF_COUNTER_TREND_SCALP_REDESIGN_V2", "1")

    cand = MtfCounterTrendScalp().evaluate(_ctx(closed_signal=True, current_signal=False))

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.sl < _ctx(closed_signal=True, current_signal=False).entry < cand.tp
    assert any("closed 1m signal_bar_time=2026-05-05 10:01:00+00:00" in r for r in cand.reasons)
    assert any("execution uses current bar" in r for r in cand.reasons)


def test_v2_requires_closed_htf_snapshots(monkeypatch):
    _patch_friction(monkeypatch)
    monkeypatch.setenv("MTF_COUNTER_TREND_SCALP_REDESIGN_V2", "1")

    assert MtfCounterTrendScalp().evaluate(
        _ctx(closed_signal=True, current_signal=False, m5_closed=False)
    ) is None
    assert MtfCounterTrendScalp().evaluate(
        _ctx(closed_signal=True, current_signal=False, m15_closed=False)
    ) is None


def test_v2_live_dedups_same_signal_bar(monkeypatch):
    _patch_friction(monkeypatch)
    monkeypatch.setenv("MTF_COUNTER_TREND_SCALP_REDESIGN_V2", "1")
    MtfCounterTrendScalp.reset_dedup_state()
    strategy = MtfCounterTrendScalp()
    ctx = _ctx(closed_signal=True, current_signal=False, backtest_mode=False)

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("SELL", 70, 1.2, 1.0, ["best"], "bb_rsi_reversion", 7.0)
    mtf = Candidate("BUY", 65, 1.0, 1.2, ["mtf"], "mtf_counter_trend_scalp", 4.0)

    monkeypatch.setenv("MTF_COUNTER_TREND_SCALP_REDESIGN_V2", "1")
    monkeypatch.delenv("MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, mtf], best) == []

    monkeypatch.setenv("MTF_COUNTER_TREND_SCALP_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, mtf], best) == [mtf]
