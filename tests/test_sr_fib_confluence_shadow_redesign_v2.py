from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.sr_fib_confluence import SrFibConfluence


def _df(*, closed_bull: bool = True, current_bull: bool = True) -> pd.DataFrame:
    n = 30
    idx = pd.date_range(end="2026-05-05 12:15", periods=n, freq="15min", tz="UTC")
    close = np.full(n, 1.1000)
    open_ = np.full(n, 1.0998)
    high = np.full(n, 1.1006)
    low = np.full(n, 1.0994)
    ema9 = np.full(n, 1.0998)
    ema21 = np.full(n, 1.1000)

    if closed_bull:
        ema9[-2] = 1.1005
        ema21[-2] = 1.1000
    if current_bull:
        ema9[-1] = 1.1005
        ema21[-1] = 1.1000

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": ema9,
            "ema21": ema21,
            "ema50": np.full(n, 1.1000),
            "ema200": np.full(n, 1.1000),
            "adx": np.full(n, 25.0),
            "adx_pos": np.full(n, 26.0),
            "adx_neg": np.full(n, 18.0),
            "rsi": np.full(n, 50.0),
            "rsi5": np.full(n, 50.0),
            "rsi9": np.full(n, 50.0),
            "stoch_k": np.full(n, 50.0),
            "stoch_d": np.full(n, 50.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.zeros(n),
            "bb_upper": np.full(n, 1.1040),
            "bb_mid": np.full(n, 1.1000),
            "bb_lower": np.full(n, 1.0960),
            "bb_pband": np.full(n, 0.50),
        },
        index=idx,
    )


def _v3_df(*, up_impulse: bool = True, adx: float = 25.0) -> pd.DataFrame:
    n = 120
    idx = pd.date_range(end="2026-06-03 12:15", periods=n, freq="15min", tz="UTC")
    open_ = np.full(n, 1.1050)
    high = np.full(n, 1.1060)
    low = np.full(n, 1.1040)
    close = np.full(n, 1.1050)
    if up_impulse:
        low[20] = 1.1000
        high[100] = 1.1100
        close[-1] = 1.10618
    else:
        high[20] = 1.1100
        low[100] = 1.1000
        close[-1] = 1.10382
    open_[-1] = close[-1] - 0.0001
    high[-1] = max(high[-1], close[-1] + 0.0002)
    low[-1] = min(low[-1], close[-1] - 0.0002)

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": np.full(n, 1.1000),
            "ema21": np.full(n, 1.1010),
            "ema50": np.full(n, 1.1000),
            "ema200": np.full(n, 1.1000),
            "adx": np.full(n, adx),
            "adx_pos": np.full(n, 26.0),
            "adx_neg": np.full(n, 18.0),
            "rsi": np.full(n, 50.0),
            "rsi5": np.full(n, 50.0),
            "rsi9": np.full(n, 50.0),
            "stoch_k": np.full(n, 50.0),
            "stoch_d": np.full(n, 50.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.zeros(n),
            "bb_upper": np.full(n, 1.1100),
            "bb_mid": np.full(n, 1.1050),
            "bb_lower": np.full(n, 1.1000),
            "bb_pband": np.full(n, 0.50),
        },
        index=idx,
    )


def _ctx(
    df: pd.DataFrame,
    *,
    layer3: dict,
    backtest_mode: bool = True,
    ema_score: float = 0.5,
) -> SignalContext:
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
        ema9_prev=float(prev["ema9"]),
        ema21_prev=float(prev["ema21"]),
        adx=float(row["adx"]),
        adx_pos=float(row["adx_pos"]),
        adx_neg=float(row["adx_neg"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        rsi9=float(row["rsi9"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        macdh_prev2=float(df.iloc[-3]["macd_hist"]),
        bbpb=float(row["bb_pband"]),
        bb_upper=float(row["bb_upper"]),
        bb_mid=float(row["bb_mid"]),
        bb_lower=float(row["bb_lower"]),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        ema_score=ema_score,
        symbol="EURUSD=X",
        tf="15m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        layer3=layer3,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_legacy_reason_string_and_repeat(monkeypatch):
    monkeypatch.delenv("SR_FIB_CONFLUENCE_REDESIGN_V2", raising=False)
    SrFibConfluence.reset_dedup_state()
    strategy = SrFibConfluence()
    ctx = _ctx(_df(), layer3={"dt_reasons": ["✅ Fib 50.0% support"]})

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is not None


def test_v2_rejects_reason_string_without_structured_gate(monkeypatch):
    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V2", "1")
    SrFibConfluence.reset_dedup_state()
    ctx = _ctx(_df(), layer3={"dt_reasons": ["✅ Fib 50.0% support"]})

    assert SrFibConfluence().evaluate(ctx) is None


def test_v2_accepts_structured_fib_gate_and_dedups(monkeypatch):
    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V2", "1")
    SrFibConfluence.reset_dedup_state()
    strategy = SrFibConfluence()
    ctx = _ctx(
        _df(),
        layer3={
            "fib_level": 1.1002,
            "confluence_type": "fib_retest",
            "signal_bar_time": "2026-05-05 12:15:00+00:00",
        },
    )

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert first.signal == "BUY"
    assert first.entry_type == "sr_fib_confluence"
    assert any("structured fib_retest" in reason for reason in first.reasons)
    assert second is None


def test_v2_accepts_structured_ob_zone(monkeypatch):
    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V2", "1")
    SrFibConfluence.reset_dedup_state()
    ctx = _ctx(
        _df(),
        layer3={
            "ob_zone_low": 1.0997,
            "ob_zone_high": 1.1003,
            "confluence_type": "bull_ob_retest",
        },
    )

    cand = SrFibConfluence().evaluate(ctx)

    assert cand is not None
    assert cand.entry_type == "ob_retest"


def test_v2_live_uses_closed_bar_not_current_bar(monkeypatch):
    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V2", "1")
    SrFibConfluence.reset_dedup_state()
    ctx = _ctx(
        _df(closed_bull=False, current_bull=True),
        layer3={"fib_level": 1.1000, "confluence_type": "fib_retest"},
        backtest_mode=False,
        ema_score=0.5,
    )

    assert SrFibConfluence().evaluate(ctx) is None


def test_v2_shadow_worker_registration_is_double_flagged(monkeypatch):
    engine = DaytradeEngine()
    best = Candidate("BUY", 70, 1.0, 1.2, ["best"], "other", 9.0)
    sr_fib = Candidate("BUY", 60, 1.0, 1.2, ["sr_fib"], "sr_fib_confluence", 5.0)
    ob = Candidate("BUY", 60, 1.0, 1.2, ["ob"], "ob_retest", 5.0)

    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V2", "1")
    monkeypatch.delenv("SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, sr_fib, ob], best) == []

    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, sr_fib, ob], best) == [sr_fib, ob]


def test_v3_takes_precedence_over_v2_and_uses_impulse_not_ema(monkeypatch):
    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V2", "1")
    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V3", "1")
    SrFibConfluence.reset_dedup_state()
    strategy = SrFibConfluence()
    ctx = _ctx(_v3_df(up_impulse=True), layer3={}, ema_score=-10.0)

    cand = strategy.evaluate(ctx)
    duplicate = strategy.evaluate(ctx)

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.entry_type == "sr_fib_confluence"
    assert any("fib_classical_v3" in reason for reason in cand.reasons)
    assert duplicate is None


def test_v3_down_impulse_sells(monkeypatch):
    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V3", "1")
    SrFibConfluence.reset_dedup_state()
    ctx = _ctx(_v3_df(up_impulse=False), layer3={}, ema_score=10.0)

    cand = SrFibConfluence().evaluate(ctx)

    assert cand is not None
    assert cand.signal == "SELL"


def test_v3_rejects_adx_above_chop_band(monkeypatch):
    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V3", "1")
    SrFibConfluence.reset_dedup_state()
    ctx = _ctx(_v3_df(up_impulse=True, adx=31.0), layer3={})

    assert SrFibConfluence().evaluate(ctx) is None


def test_reset_dedup_state_clears_v2_and_v3(monkeypatch):
    monkeypatch.setenv("SR_FIB_CONFLUENCE_REDESIGN_V3", "1")
    SrFibConfluence._v2_seen_signal_keys.add(("v2",))
    SrFibConfluence._v3_seen_signal_keys.add(("v3",))

    SrFibConfluence.reset_dedup_state()

    assert SrFibConfluence._v2_seen_signal_keys == set()
    assert SrFibConfluence._v3_seen_signal_keys == set()
