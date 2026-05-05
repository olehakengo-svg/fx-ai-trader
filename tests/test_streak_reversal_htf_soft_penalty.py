from __future__ import annotations

import numpy as np
import pandas as pd

import app


class _NoCandidateDaytradeEngine:
    def evaluate_all(self, _ctx):
        return []

    def select_best(self, _candidates):
        return None

    def split_shadow_always(self, _candidates, _best):
        return []


def _streak_df(direction: str) -> pd.DataFrame:
    n = 90
    idx = pd.date_range("2026-05-05 12:00", periods=n, freq="15min", tz="UTC")
    close = np.full(n, 150.00)
    open_ = np.full(n, 150.00)

    if direction == "SELL":
        open_[-3:] = [150.00, 150.02, 150.04]
        close[-3:] = [150.01, 150.03, 150.05]
    elif direction == "BUY":
        open_[-3:] = [150.05, 150.03, 150.01]
        close[-3:] = [150.04, 150.02, 150.00]
    else:
        raise ValueError(direction)

    high = np.maximum(open_, close) + 0.03
    low = np.minimum(open_, close) - 0.03
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.08),
            "atr7": np.full(n, 0.08),
            "ema9": np.full(n, 150.00),
            "ema21": np.full(n, 150.00),
            "ema50": np.full(n, 150.00),
            "ema200": np.full(n, 150.00),
            "adx": np.full(n, 20.0),
            "adx_pos": np.full(n, 20.0),
            "adx_neg": np.full(n, 20.0),
            "rsi": np.full(n, 50.0),
            "rsi5": np.full(n, 50.0),
            "rsi9": np.full(n, 50.0),
            "stoch_k": np.full(n, 50.0),
            "stoch_d": np.full(n, 50.0),
            "macd": np.zeros(n),
            "macd_sig": np.zeros(n),
            "macd_hist": np.zeros(n),
            "bb_upper": np.full(n, 150.20),
            "bb_mid": np.full(n, 150.00),
            "bb_lower": np.full(n, 149.80),
            "bb_pband": np.full(n, 0.50),
        },
        index=idx,
    )


def _patch_streak_isolation(monkeypatch):
    import strategies.daytrade as daytrade_mod

    monkeypatch.setenv("STREAK_REVERSAL_HTF_SOFT_PENALTY", "1")
    monkeypatch.setattr(app, "is_trade_prohibited", lambda *_args, **_kwargs: {"prohibited": False})
    monkeypatch.setattr(app, "get_master_bias", lambda *_args, **_kwargs: {"direction": "neutral", "label": "test", "score": 0})
    monkeypatch.setattr(app, "detect_market_regime", lambda *_args, **_kwargs: {"regime": "NORMAL"})
    monkeypatch.setattr(app, "compute_layer2_score", lambda *_args, **_kwargs: {"score": 0.0})
    monkeypatch.setattr(app, "compute_layer3_score", lambda *_args, **_kwargs: {"score": 0.0})
    monkeypatch.setattr(app, "find_sr_levels_weighted", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(app, "_calc_fibonacci_levels", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(app, "calc_sl_tp_v3", lambda entry, signal, *_args, **_kwargs: (entry - 0.05, entry + 0.10) if signal == "BUY" else (entry + 0.05, entry - 0.10))
    monkeypatch.setattr(daytrade_mod, "DaytradeEngine", _NoCandidateDaytradeEngine)


def _compute(direction: str, htf_agreement: str, monkeypatch):
    _patch_streak_isolation(monkeypatch)
    df = _streak_df(direction)
    return app.compute_daytrade_signal(
        df,
        tf="15m",
        sr_levels=[],
        symbol="USDJPY=X",
        backtest_mode=True,
        bar_time=df.index[-1],
        htf_cache={
            "htf": {"agreement": htf_agreement, "label": f"test {htf_agreement}"},
            "layer1": {"direction": "neutral", "label": "test", "score": 0},
        },
    )


def test_htf_bull_sell_streak_emits_soft_penalty_signal(monkeypatch):
    got = _compute("SELL", "bull", monkeypatch)

    assert got["signal"] == "SELL"
    assert got["confidence"] == 25


def test_htf_bull_sell_streak_keeps_entry_type(monkeypatch):
    got = _compute("SELL", "bull", monkeypatch)

    assert got["entry_type"] == "streak_reversal"
    assert any("[Streak]" in reason and "HTF soft penalty" in reason for reason in got["reasons"])


def test_htf_bear_buy_streak_emits_soft_penalty_signal(monkeypatch):
    got = _compute("BUY", "bear", monkeypatch)

    assert got["signal"] == "BUY"
    assert got["confidence"] == 25


def test_htf_bear_buy_streak_keeps_entry_type(monkeypatch):
    got = _compute("BUY", "bear", monkeypatch)

    assert got["entry_type"] == "streak_reversal"
    assert any("[Streak]" in reason and "HTF soft penalty" in reason for reason in got["reasons"])
