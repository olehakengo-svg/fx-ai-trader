from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.tokyo_nakane_momentum import TokyoNakaneMomentum


def _df(final_time: str = "2026-05-06 01:00") -> pd.DataFrame:
    idx = pd.date_range(end=final_time, periods=20, freq="15min", tz="UTC")
    n = len(idx)
    open_ = np.full(n, 150.18)
    high = np.full(n, 150.24)
    low = np.full(n, 150.12)
    close = np.full(n, 150.18)

    open_[-5] = 150.20
    high[-5] = 150.22
    low[-5] = 150.13
    close[-5] = 150.18

    open_[-4] = 150.18
    high[-4] = 150.19
    low[-4] = 150.11
    close[-4] = 150.16

    open_[-3] = 150.16
    high[-3] = 150.17
    low[-3] = 150.10
    close[-3] = 150.15

    open_[-2] = 150.15
    high[-2] = 150.17
    low[-2] = 150.12
    close[-2] = 150.14

    open_[-1] = 150.15
    high[-1] = 150.20
    low[-1] = 150.14
    close[-1] = 150.18

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.05),
            "atr7": np.full(n, 0.05),
            "ema9": np.full(n, 150.19),
            "ema21": np.full(n, 150.16),
            "ema50": np.full(n, 150.10),
            "ema200": np.full(n, 150.00),
            "adx": np.full(n, 24.0),
            "adx_pos": np.full(n, 25.0),
            "adx_neg": np.full(n, 20.0),
            "rsi": np.full(n, 56.0),
            "rsi5": np.full(n, 56.0),
            "rsi9": np.full(n, 56.0),
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 50.0),
            "macd_hist": np.zeros(n),
            "bb_pband": np.full(n, 0.55),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, symbol: str = "USDJPY=X",
         htf_agreement: str = "mixed") -> SignalContext:
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
        ema200=float(row["ema200"]),
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
        bbpb=float(row["bb_pband"]),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol=symbol,
        tf="15m",
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        htf={"agreement": htf_agreement},
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_legacy_jpy_cross_gate(monkeypatch):
    monkeypatch.delenv("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2", raising=False)

    cand = TokyoNakaneMomentum().evaluate(
        _ctx(_df(), symbol="EURJPY=X", htf_agreement="mixed")
    )

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2" in r for r in cand.reasons)


def test_v2_blocks_jpy_crosses_and_keeps_usdjpy(monkeypatch):
    monkeypatch.setenv("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2", "1")

    assert TokyoNakaneMomentum().evaluate(
        _ctx(_df(), symbol="EURJPY=X", htf_agreement="mixed")
    ) is None

    cand = TokyoNakaneMomentum().evaluate(
        _ctx(_df(), symbol="USDJPY=X", htf_agreement="mixed")
    )

    assert cand is not None
    assert cand.entry_type == "tokyo_nakane_momentum"
    assert any("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2" in r for r in cand.reasons)


def test_v2_softens_htf_bear_hard_block(monkeypatch):
    df = _df()
    ctx = _ctx(df, symbol="USDJPY=X", htf_agreement="bear")

    monkeypatch.delenv("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2", raising=False)
    assert TokyoNakaneMomentum().evaluate(ctx) is None

    monkeypatch.setenv("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2", "1")
    cand = TokyoNakaneMomentum().evaluate(ctx)
    mixed = TokyoNakaneMomentum().evaluate(_ctx(df, symbol="USDJPY=X", htf_agreement="mixed"))

    assert cand is not None
    assert mixed is not None
    assert cand.score == mixed.score - 0.5
    assert any("hard blockせずscore -0.5" in r for r in cand.reasons)


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 151.0, 150.0, [], "other", 9.0)
    nakane = Candidate("BUY", 70, 150.0, 151.0, [], "tokyo_nakane_momentum", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2", "1")
    monkeypatch.delenv("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, nakane], other) == []

    monkeypatch.setenv("TOKYO_NAKANE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, nakane], other) == [nakane]
