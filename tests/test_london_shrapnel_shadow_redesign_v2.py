from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.london_shrapnel import LondonShrapnel


def _df(*, closed_sweep: bool, current_legacy_signal: bool = False) -> pd.DataFrame:
    n = 30
    idx = pd.date_range(end="2026-05-05 13:15", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.10000)
    high = np.full(n, 1.10030)
    low = np.full(n, 1.09970)
    close = np.full(n, 1.10005)
    atr7 = np.full(n, 0.00050)
    bb_lower = np.full(n, 1.09950)
    bb_mid = np.full(n, 1.10010)
    bb_upper = np.full(n, 1.10070)
    bb_pband = np.full(n, 0.12)
    rsi5 = np.full(n, 35.0)

    # Prior liquidity reference for V2: df.iloc[-3].
    low[-3] = 1.09950
    high[-3] = 1.10070

    # Closed signal bar for V2: df.iloc[-2].
    open_[-2] = 1.09960
    close[-2] = 1.09972
    high[-2] = 1.09980
    low[-2] = 1.09870 if closed_sweep else 1.09940

    # Current bar/execution row. Legacy uses this row directly.
    if current_legacy_signal:
        open_[-1] = 1.10075
        close[-1] = 1.10085
        high[-1] = 1.10090
        low[-1] = 1.09995
    else:
        open_[-1] = 1.09980
        close[-1] = 1.09982
        high[-1] = 1.09990
        low[-1] = 1.09970

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": atr7,
            "atr7": atr7,
            "rsi": np.full(n, 35.0),
            "rsi5": rsi5,
            "stoch_k": np.full(n, 25.0),
            "stoch_d": np.full(n, 20.0),
            "macd_hist": np.zeros(n),
            "bb_lower": bb_lower,
            "bb_mid": bb_mid,
            "bb_upper": bb_upper,
            "bb_pband": bb_pband,
            "adx": np.full(n, 22.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(df.iloc[-2]["macd_hist"]),
        macdh_prev2=float(df.iloc[-3]["macd_hist"]),
        bbpb=float(row["bb_pband"]),
        bb_lower=float(row["bb_lower"]),
        bb_mid=float(row["bb_mid"]),
        bb_upper=float(row["bb_upper"]),
        adx=float(row["adx"]),
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_legacy_current_bar_trigger(monkeypatch):
    monkeypatch.delenv("LONDON_SHRAPNEL_REDESIGN_V2", raising=False)
    LondonShrapnel.reset_dedup_state()

    cand = LondonShrapnel().evaluate(
        _ctx(_df(closed_sweep=False, current_legacy_signal=True))
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("LONDON_SHRAPNEL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_requires_closed_bar_sweep_plus_reclaim(monkeypatch):
    monkeypatch.setenv("LONDON_SHRAPNEL_REDESIGN_V2", "1")
    LondonShrapnel.reset_dedup_state()

    cand = LondonShrapnel().evaluate(
        _ctx(_df(closed_sweep=False, current_legacy_signal=True))
    )

    assert cand is None


def test_v2_fires_on_closed_sweep_and_uses_execution_entry(monkeypatch):
    monkeypatch.setenv("LONDON_SHRAPNEL_REDESIGN_V2", "1")
    LondonShrapnel.reset_dedup_state()

    cand = LondonShrapnel().evaluate(_ctx(_df(closed_sweep=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.sl, 5) == 1.09860
    assert round(cand.tp, 5) == 1.10010
    assert any("closed-bar lower sweep + reclaim" in reason for reason in cand.reasons)


def test_v2_per_bar_dedup_blocks_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("LONDON_SHRAPNEL_REDESIGN_V2", "1")
    LondonShrapnel.reset_dedup_state()
    strategy = LondonShrapnel()
    ctx = _ctx(_df(closed_sweep=True))

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    shrapnel = Candidate("BUY", 70, 1.0, 2.0, [], "london_shrapnel", 4.0)
    engine = ScalperEngine()

    monkeypatch.setenv("LONDON_SHRAPNEL_REDESIGN_V2", "1")
    monkeypatch.delenv("LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, shrapnel], other) == []

    monkeypatch.setenv("LONDON_SHRAPNEL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, shrapnel], other) == [shrapnel]
