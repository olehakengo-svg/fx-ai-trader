import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.mtf_regime_range_cascade_scalp import MtfRegimeRangeCascadeScalp


def _df():
    idx = pd.date_range("2026-05-05 10:00", periods=6, freq="min", tz="UTC")
    return pd.DataFrame(
        {
            "Open": [100.00, 100.00, 100.00, 100.00, 99.960, 100.000],
            "High": [100.03, 100.03, 100.02, 100.01, 99.990, 100.010],
            "Low": [99.98, 99.98, 99.97, 99.96, 99.940, 99.990],
            "Close": [100.00, 100.00, 100.00, 100.00, 99.970, 100.000],
            "atr": [0.010] * 6,
            "atr7": [0.010] * 6,
            "rsi": [50.0, 50.0, 50.0, 50.0, 31.0, 50.0],
            "rsi5": [50.0, 50.0, 50.0, 25.0, 31.0, 50.0],
            "stoch_k": [50.0, 50.0, 50.0, 20.0, 25.0, 50.0],
            "stoch_d": [50.0, 50.0, 50.0, 25.0, 24.0, 50.0],
            "bb_upper": [100.050] * 6,
            "bb_mid": [100.000] * 6,
            "bb_lower": [99.950] * 6,
            "bb_pband": [0.50, 0.50, 0.50, 0.05, 0.20, 0.50],
        },
        index=idx,
    )


def _ctx(backtest_mode=True):
    df = _df()
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
        bbpb=float(row["bb_pband"]),
        bb_upper=float(row["bb_upper"]),
        bb_mid=float(row["bb_mid"]),
        bb_lower=float(row["bb_lower"]),
        prev_close=float(df.iloc[-2]["Close"]),
        prev_open=float(df.iloc[-2]["Open"]),
        prev_high=float(df.iloc[-2]["High"]),
        prev_low=float(df.iloc[-2]["Low"]),
        df=df,
        htf={
            "m15": {"adx": 16.0, "ema_slope": 0.0, "hurst_64": 0.85, "atr": 0.010},
            "m5": {
                "bbpb": 0.50,
                "swing_low": 99.940,
                "swing_high": 100.060,
                "low": 99.950,
                "high": 100.040,
                "atr": 0.010,
            },
        },
        symbol="USDJPY=X",
        hour_utc=10,
        pip_mult=100,
        backtest_mode=backtest_mode,
        bar_time=df.index[-1],
    )


def _patch_common(monkeypatch):
    import strategies.scalp.mtf_regime_range_cascade_scalp as mod

    monkeypatch.setattr(mod, "should_block", lambda *args, **kwargs: (False, {}))


def test_redesign_v2_uses_closed_reclaim_bar(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.delenv("MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2", raising=False)

    strategy = MtfRegimeRangeCascadeScalp()
    assert strategy.evaluate(_ctx()) is None

    monkeypatch.setenv("MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2", "1")
    cand = strategy.evaluate(_ctx())

    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.entry_type == "mtf_regime_range_cascade_scalp"
    assert any("closed 1m range-edge reclaim BUY" in r for r in cand.reasons)
    assert any("regime_cohort=range_wide" in r for r in cand.reasons)
    assert any("signal_bar_time=2026-05-05 10:04:00+00:00" in r for r in cand.reasons)


def test_redesign_v2_blocks_range_tight_cohort(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setenv("MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2", "1")
    ctx = _ctx()
    ctx.htf["m15"]["hurst_64"] = 0.60

    assert MtfRegimeRangeCascadeScalp().evaluate(ctx) is None


def test_redesign_v2_live_dedups_same_signal_bar(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setenv("MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2", "1")
    MtfRegimeRangeCascadeScalp.reset_dedup_state()

    strategy = MtfRegimeRangeCascadeScalp()
    ctx = _ctx(backtest_mode=False)

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is None


def test_redesign_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    engine = ScalperEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "bb_rsi_reversion", 6.0)
    range_cascade = Candidate(
        "BUY", 60, 1.0, 1.2, ["range"], "mtf_regime_range_cascade_scalp", 5.0
    )

    monkeypatch.delenv("MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2", raising=False)
    monkeypatch.delenv("MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, range_cascade], best) == []

    monkeypatch.setenv("MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2", "1")
    monkeypatch.setenv("MTF_REGIME_RANGE_CASCADE_SCALP_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, range_cascade], best) == [range_cascade]
