"""VDR JPY shadow redesign v2 flag tests."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.vdr_jpy import VdrJpy


def _ctx(
    symbol="USDJPY=X",
    entry=150.50,
    vwap=150.00,
    atr=0.20,
    open_price=None,
    n_bars=60,
):
    dates = pd.date_range("2026-01-01", periods=n_bars, freq="15min")
    closes = np.linspace(vwap - 0.4, entry, n_bars)
    df = pd.DataFrame(
        {
            "Open": closes - 0.04,
            "High": closes + 0.10,
            "Low": closes - 0.10,
            "Close": closes,
            "Volume": [1000] * n_bars,
            "vwap": [vwap] * n_bars,
        },
        index=dates,
    )
    return SignalContext(
        entry=entry,
        open_price=entry + 0.05 if open_price is None else open_price,
        atr=atr,
        adx=20.0,
        df=df,
        symbol=symbol,
        tf="15m",
        is_jpy=True,
        pip_mult=100,
    )


def test_default_off_preserves_v1_usdjpy_threshold_and_hard_candle_gate(monkeypatch):
    monkeypatch.delenv("VDR_JPY_REDESIGN_V2", raising=False)
    strategy = VdrJpy()

    cand = strategy.evaluate(_ctx(entry=150.35, open_price=150.40))

    assert cand is not None
    assert cand.entry_type == "vdr_jpy"
    assert cand.max_hold_bars is None
    assert not any("VDR_JPY_REDESIGN_V2" in reason for reason in cand.reasons)
    assert strategy.evaluate(_ctx(entry=150.50, open_price=150.45)) is None


def test_v2_uses_pair_specific_usdjpy_threshold(monkeypatch):
    monkeypatch.setenv("VDR_JPY_REDESIGN_V2", "1")
    strategy = VdrJpy()

    usd = strategy.evaluate(_ctx(symbol="USDJPY=X", entry=150.35, open_price=150.40))
    eur = strategy.evaluate(_ctx(symbol="EURJPY=X", entry=160.35, vwap=160.00, open_price=160.40))

    assert usd is None
    assert eur is not None
    assert any(">1.5" in reason for reason in eur.reasons)


def test_v2_softens_candle_confirmation_and_sets_time_exit_contract(monkeypatch):
    monkeypatch.setenv("VDR_JPY_REDESIGN_V2", "1")
    strategy = VdrJpy()

    confirmed = strategy.evaluate(_ctx(entry=150.50, open_price=150.55))
    penalized = strategy.evaluate(_ctx(entry=150.50, open_price=150.45))

    assert confirmed is not None
    assert penalized is not None
    assert confirmed.max_hold_bars == 2
    assert penalized.max_hold_bars == 2
    assert penalized.score < confirmed.score
    assert any("score penalty" in reason for reason in penalized.reasons)
    assert any("VDR_JPY_REDESIGN_V2" in reason for reason in penalized.reasons)


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 151.0, 150.0, [], "other", 9.0)
    vdr = Candidate("BUY", 70, 150.0, 151.0, [], "vdr_jpy", 4.0)
    engine = DaytradeEngine()

    monkeypatch.setenv("VDR_JPY_REDESIGN_V2", "1")
    monkeypatch.delenv("VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, vdr], other) == []

    monkeypatch.setenv("VDR_JPY_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, vdr], other) == [vdr]
