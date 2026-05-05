from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.dt_bb_rsi_mr import DtBbRsiMR


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=4, freq="15min", tz="UTC")
    rows = [
        {
            "Open": 156.12,
            "High": 156.14,
            "Low": 156.04,
            "Close": 156.06,
            "bb_pband": 0.45,
            "rsi": 50.0,
            "stoch_k": 24.0,
            "stoch_d": 28.0,
            "macd_hist": -0.10,
            "atr": 0.08,
        },
        {
            "Open": 156.08,
            "High": 156.11,
            "Low": 155.98,
            "Close": 156.00,
            "bb_pband": 0.35,
            "rsi": 48.0,
            "stoch_k": 20.0,
            "stoch_d": 26.0,
            "macd_hist": -0.05,
            "atr": 0.08,
        },
        {
            "Open": 156.02 if closed_signal else 156.08,
            "High": 156.11,
            "Low": 155.96,
            "Close": 156.07 if closed_signal else 156.00,
            "bb_pband": 0.20 if closed_signal else 0.55,
            "rsi": 35.0 if closed_signal else 50.0,
            "stoch_k": 31.0 if closed_signal else 50.0,
            "stoch_d": 28.0 if closed_signal else 50.0,
            "macd_hist": 0.08 if closed_signal else 0.00,
            "atr": 0.08,
        },
        {
            "Open": 156.00 if current_signal else 156.08,
            "High": 156.12,
            "Low": 155.95,
            "Close": 156.06 if current_signal else 156.00,
            "bb_pband": 0.20 if current_signal else 0.55,
            "rsi": 35.0 if current_signal else 50.0,
            "stoch_k": 31.0 if current_signal else 50.0,
            "stoch_d": 28.0 if current_signal else 50.0,
            "macd_hist": 0.10 if current_signal else 0.00,
            "atr": 0.08,
        },
    ]
    return pd.DataFrame(rows, index=idx)


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi"]),
        rsi9=float(row["rsi"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        adx=18.0,
        macdh=float(row["macd_hist"]),
        macdh_prev=float(prev["macd_hist"]),
        macdh_prev2=float(df.iloc[-3]["macd_hist"]),
        bbpb=float(row["bb_pband"]),
        bb_lower=float(row["Close"]) - 0.12,
        bb_mid=float(row["Close"]) + 0.04,
        bb_upper=float(row["Close"]) + 0.16,
        bb_width_pct=0.5,
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        symbol="USDJPY=X",
        tf="15m",
        is_jpy=True,
        pip_mult=100,
        df=df,
        regime={"regime": "RANGE"},
        htf={"agreement": "mixed"},
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_current_bar_signal(monkeypatch):
    monkeypatch.delenv("DT_BB_RSI_MR_REDESIGN_V2", raising=False)

    cand = DtBbRsiMR().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("DT_BB_RSI_MR_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_signal_and_ignores_current_bar(monkeypatch):
    monkeypatch.setenv("DT_BB_RSI_MR_REDESIGN_V2", "1")

    cand = DtBbRsiMR().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert any("closed_bar_time=2026-05-05 07:00:00+00:00" in reason for reason in cand.reasons)
    assert any("DT_BB_RSI_MR_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_if_closed_bar_has_no_signal_even_when_current_bar_does(monkeypatch):
    monkeypatch.setenv("DT_BB_RSI_MR_REDESIGN_V2", "1")

    cand = DtBbRsiMR().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_live_dedups_same_symbol_signal_closed_bar(monkeypatch):
    monkeypatch.setenv("DT_BB_RSI_MR_REDESIGN_V2", "1")
    DtBbRsiMR._v2_seen_closed_bar_keys.clear()
    strategy = DtBbRsiMR()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    dt_bb = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="dt_bb_rsi_mr",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("DT_BB_RSI_MR_REDESIGN_V2", "1")
    monkeypatch.delenv("DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, dt_bb], other) == []

    monkeypatch.setenv("DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, dt_bb], other) == [dt_bb]
