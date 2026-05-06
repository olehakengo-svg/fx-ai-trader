from __future__ import annotations

import numpy as np
import pandas as pd

import app
from strategies.base import Candidate
from strategies.daytrade import DaytradeEngine


def _df(*, closed_signal: str | None, current_signal: str | None) -> pd.DataFrame:
    n = 60
    idx = pd.date_range(end="2026-05-05 12:15", periods=n, freq="15min", tz="UTC")
    close = np.full(n, 100.0)
    open_ = np.full(n, 100.0)
    high = np.full(n, 100.08)
    low = np.full(n, 99.92)
    vwap = np.full(n, 100.0)

    close[-3] = 99.8
    if closed_signal == "BUY":
        close[-2] = 97.0
    elif closed_signal == "SELL":
        close[-2] = 103.0
    else:
        close[-2] = 100.0

    if current_signal == "BUY":
        close[-1] = 97.0
    elif current_signal == "SELL":
        close[-1] = 103.0
    else:
        close[-1] = 100.0

    open_[-2:] = close[-2:]
    high = np.maximum(high, close + 0.08)
    low = np.minimum(low, close - 0.08)

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.5),
            "atr7": np.full(n, 0.5),
            "ema9": np.full(n, 100.0),
            "ema21": np.full(n, 100.0),
            "ema50": np.full(n, 100.0),
            "ema200": np.full(n, 100.0),
            "adx": np.full(n, 18.0),
            "adx_pos": np.full(n, 25.0),
            "adx_neg": np.full(n, 25.0),
            "rsi": np.full(n, 50.0),
            "rsi5": np.full(n, 50.0),
            "rsi9": np.full(n, 50.0),
            "stoch_k": np.full(n, 50.0),
            "stoch_d": np.full(n, 50.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.zeros(n),
            "bb_pband": np.full(n, 0.5),
            "bb_upper": np.full(n, 101.0),
            "bb_mid": np.full(n, 100.0),
            "bb_lower": np.full(n, 99.0),
            "bb_width": np.full(n, 0.02),
            "vwap": vwap,
        },
        index=idx,
    )


def _patch_noise(monkeypatch):
    monkeypatch.setattr(app, "find_sr_levels_weighted", lambda *args, **kwargs: [])
    monkeypatch.setattr(DaytradeEngine, "evaluate_all", lambda self, ctx: [])
    monkeypatch.setattr(DaytradeEngine, "select_best", lambda self, candidates: None)
    monkeypatch.setattr(DaytradeEngine, "split_shadow_always", lambda self, candidates, best: [])


def _signal(df: pd.DataFrame, *, backtest_mode: bool, htf_agreement: str = "mixed") -> dict:
    return app.compute_daytrade_signal(
        df,
        tf="15m",
        sr_levels=[],
        symbol="USDJPY=X",
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
        htf_cache={
            "htf": {"agreement": htf_agreement, "label": htf_agreement},
            "layer1": {"label": "test"},
        },
    )


def test_v2_default_off_keeps_vwap_mr_disabled(monkeypatch):
    _patch_noise(monkeypatch)
    monkeypatch.delenv("VWAP_MEAN_REVERSION_REDESIGN_V2", raising=False)

    result = _signal(_df(closed_signal=None, current_signal="BUY"), backtest_mode=False)

    assert result["entry_type"] != "vwap_mean_reversion"


def test_v2_live_uses_closed_bar_and_ignores_current_bar(monkeypatch):
    _patch_noise(monkeypatch)
    monkeypatch.setenv("VWAP_MEAN_REVERSION_REDESIGN_V2", "1")
    app._VWAP_MEAN_REVERSION_V2_SEEN_BAR_KEYS.clear()

    result = _signal(_df(closed_signal="BUY", current_signal=None), backtest_mode=False)

    assert result["entry_type"] == "vwap_mean_reversion"
    assert result["signal"] == "BUY"
    assert any("closed_bar_time=2026-05-05 12:00:00+00:00" in reason for reason in result["reasons"])
    assert any("VWAP-MR V2" in reason for reason in result["reasons"])


def test_v2_live_rejects_if_only_current_bar_signals(monkeypatch):
    _patch_noise(monkeypatch)
    monkeypatch.setenv("VWAP_MEAN_REVERSION_REDESIGN_V2", "1")
    app._VWAP_MEAN_REVERSION_V2_SEEN_BAR_KEYS.clear()

    result = _signal(_df(closed_signal=None, current_signal="BUY"), backtest_mode=False)

    assert result["entry_type"] != "vwap_mean_reversion"


def test_v2_live_dedups_same_closed_bar(monkeypatch):
    _patch_noise(monkeypatch)
    monkeypatch.setenv("VWAP_MEAN_REVERSION_REDESIGN_V2", "1")
    app._VWAP_MEAN_REVERSION_V2_SEEN_BAR_KEYS.clear()
    df = _df(closed_signal="BUY", current_signal=None)

    assert _signal(df, backtest_mode=False)["entry_type"] == "vwap_mean_reversion"
    assert _signal(df, backtest_mode=False)["entry_type"] != "vwap_mean_reversion"


def test_v2_removes_htf_direction_hard_veto(monkeypatch):
    _patch_noise(monkeypatch)
    monkeypatch.setenv("VWAP_MEAN_REVERSION_REDESIGN_V2", "1")
    app._VWAP_MEAN_REVERSION_V2_SEEN_BAR_KEYS.clear()

    result = _signal(_df(closed_signal="SELL", current_signal=None), backtest_mode=False, htf_agreement="bull")

    assert result["entry_type"] == "vwap_mean_reversion"
    assert result["signal"] == "SELL"


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="BUY", confidence=80, sl=1.0, tp=2.0, reasons=[], entry_type="other", score=9.0)
    vmr = Candidate(
        signal="SELL",
        confidence=60,
        sl=2.0,
        tp=1.0,
        reasons=[],
        entry_type="vwap_mean_reversion",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("VWAP_MEAN_REVERSION_REDESIGN_V2", "1")
    monkeypatch.delenv("VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, vmr], other) == []

    monkeypatch.setenv("VWAP_MEAN_REVERSION_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, vmr], other) == [vmr]
