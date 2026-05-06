import pandas as pd

from strategies.context import SignalContext
from strategies.scalp.mtf_regime_trend_cascade_scalp import MtfRegimeTrendCascadeScalp


def _df():
    idx = pd.date_range("2026-05-05 10:00", periods=6, freq="min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [99.90, 99.95, 100.00, 100.05, 100.20, 100.20],
            "High": [100.00, 100.05, 100.12, 100.18, 100.35, 100.25],
            "Low": [99.85, 99.90, 99.96, 100.00, 100.16, 100.05],
            "Close": [99.95, 100.00, 100.05, 100.10, 100.30, 100.10],
            "ema21": [99.90, 99.93, 99.96, 99.98, 100.00, 100.00],
            "atr7": [0.10] * 6,
            "atr": [0.10] * 6,
            "ema9": [100.0] * 6,
            "ema50": [99.8] * 6,
            "rsi": [55.0] * 6,
            "macd_hist": [0.0] * 6,
            "bb_pband": [0.5] * 6,
        },
        index=idx,
    )


def _ctx(backtest_mode=True):
    df = _df()
    return SignalContext(
        entry=float(df.iloc[-1]["Close"]),
        open_price=float(df.iloc[-1]["Open"]),
        atr=0.10,
        atr7=0.10,
        ema21=float(df.iloc[-1]["ema21"]),
        prev_close=float(df.iloc[-2]["Close"]),
        df=df,
        htf={
            "m15": {"adx": 22.0, "ema_slope": 0.05, "atr": 0.10},
            "m5": {
                "sma21": 100.0,
                "atr": 0.10,
                "prev_low": 99.99,
                "prev_high": 100.35,
                "prev_close": 100.0,
                "close": 100.12,
                "swing_high": 100.55,
                "swing_low": 99.60,
            },
            "h1": {"ema21": 100.0, "ema50": 99.8},
        },
        symbol="USDJPY=X",
        hour_utc=10,
        pip_mult=100,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
    )


def _patch_common(monkeypatch):
    import strategies.scalp.mtf_regime_trend_cascade_scalp as mod

    monkeypatch.setattr(mod, "should_block", lambda *args, **kwargs: (False, {}))
    monkeypatch.setattr(mod, "classify_15m", lambda m15: mod.REGIME_MODERATE_TREND)
    monkeypatch.setattr(mod, "slope_direction_macro_gated", lambda m15, h1: 1)


def test_redesign_v2_uses_closed_prior_1m_bar_for_bounce(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.delenv("MTF_REGIME_TREND_CASCADE_SCALP_REDESIGN_V2", raising=False)

    strategy = MtfRegimeTrendCascadeScalp()
    assert strategy.evaluate(_ctx()) is None

    monkeypatch.setenv("MTF_REGIME_TREND_CASCADE_SCALP_REDESIGN_V2", "1")
    cand = strategy.evaluate(_ctx())

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.entry_type == "mtf_regime_trend_cascade_scalp"
    assert any("MTF_REGIME_TREND_CASCADE_SCALP_REDESIGN_V2" in r for r in cand.reasons)
    assert any("signal_bar_time=2026-05-05 10:04:00+00:00" in r for r in cand.reasons)


def test_redesign_v2_live_dedups_same_signal_bar(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setenv("MTF_REGIME_TREND_CASCADE_SCALP_REDESIGN_V2", "1")
    MtfRegimeTrendCascadeScalp.reset_dedup_state()

    strategy = MtfRegimeTrendCascadeScalp()
    ctx = _ctx(backtest_mode=False)

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is None
