from __future__ import annotations

import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.v_reversal import VReversal


def _df(*, closed_signal: bool, current_signal: bool) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 07:15", periods=20, freq="15min", tz="UTC")
    rows = []
    for i in range(20):
        close = 156.37 - i * 0.02
        rows.append(
            {
                "Open": close + 0.01,
                "High": close + 0.02,
                "Low": close - 0.02,
                "Close": close,
                "bb_pband": 0.45,
                "rsi": 50.0,
                "stoch_k": 50.0,
                "macd_hist": -0.05,
                "atr": 0.08,
                "atr7": 0.08,
            }
        )

    rows[-3].update({"Close": 156.04, "stoch_k": 10.0, "bb_pband": 0.22, "rsi": 34.0, "macd_hist": -0.10})
    rows[-2].update(
        {
            "Open": 156.04 if closed_signal else 156.11,
            "High": 156.13,
            "Low": 155.99,
            "Close": 156.10 if closed_signal else 156.05,
            "bb_pband": 0.10 if closed_signal else 0.45,
            "rsi": 24.0 if closed_signal else 50.0,
            "stoch_k": 15.0 if closed_signal else 10.0,
            "macd_hist": -0.02 if closed_signal else -0.05,
        }
    )
    rows[-1].update(
        {
            "Open": 156.06 if current_signal else 156.12,
            "High": 156.15,
            "Low": 156.02,
            "Close": 156.12 if current_signal else 156.08,
            "bb_pband": 0.10 if current_signal else 0.45,
            "rsi": 24.0 if current_signal else 50.0,
            "stoch_k": 15.0 if current_signal else 50.0,
            "macd_hist": 0.02 if current_signal else -0.03,
        }
    )
    return pd.DataFrame(rows, index=idx)


def _ctx(df: pd.DataFrame, *, backtest_mode: bool = True) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi"]),
        rsi9=float(row["rsi"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_k"]),
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
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
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
    monkeypatch.delenv("V_REVERSAL_REDESIGN_V2", raising=False)

    cand = VReversal().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("V_REVERSAL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_closed_bar_signal_and_ignores_current_bar(monkeypatch):
    monkeypatch.setenv("V_REVERSAL_REDESIGN_V2", "1")

    cand = VReversal().evaluate(_ctx(_df(closed_signal=True, current_signal=False)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.tp, 2) == 156.20
    assert any("closed_bar_time=2026-05-05 07:00:00+00:00" in reason for reason in cand.reasons)
    assert any("V_REVERSAL_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_rejects_if_closed_bar_has_no_signal_even_when_current_bar_does(monkeypatch):
    monkeypatch.setenv("V_REVERSAL_REDESIGN_V2", "1")

    cand = VReversal().evaluate(_ctx(_df(closed_signal=False, current_signal=True)))

    assert cand is None


def test_v2_live_dedups_same_symbol_signal_closed_bar(monkeypatch):
    monkeypatch.setenv("V_REVERSAL_REDESIGN_V2", "1")
    VReversal._v2_seen_closed_bar_keys.clear()
    strategy = VReversal()
    ctx = _ctx(_df(closed_signal=True, current_signal=False), backtest_mode=False)

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    engine = ScalperEngine()
    other = Candidate("SELL", 80, 2.0, 1.0, ["other"], "other", 9.0)
    v_reversal = Candidate("BUY", 70, 1.0, 2.0, ["v"], "v_reversal", 4.0)

    monkeypatch.setenv("V_REVERSAL_REDESIGN_V2", "1")
    monkeypatch.delenv("V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, v_reversal], other) == []

    monkeypatch.setenv("V_REVERSAL_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, v_reversal], other) == [v_reversal]
