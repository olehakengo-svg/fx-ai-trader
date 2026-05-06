import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.squeeze_release_momentum import SqueezeReleaseMomentum


def _df(*, signal_width=0.012, prev_width=0.010, current_width=0.009,
        signal_pband=0.82, current_pband=0.20, current_open=1.1010) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Open": 1.0985, "High": 1.0992, "Low": 1.0980, "Close": 1.0988,
             "bb_width": 0.0120, "bb_pband": 0.50},
            {"Open": 1.0988, "High": 1.0995, "Low": 1.0983, "Close": 1.0990,
             "bb_width": 0.0118, "bb_pband": 0.50},
            {"Open": 1.0990, "High": 1.0997, "Low": 1.0985, "Close": 1.0992,
             "bb_width": 0.0115, "bb_pband": 0.50},
            {"Open": 1.0992, "High": 1.0998, "Low": 1.0987, "Close": 1.0993,
             "bb_width": 0.0113, "bb_pband": 0.50},
            {"Open": 1.0993, "High": 1.0999, "Low": 1.0988, "Close": 1.0994,
             "bb_width": 0.0112, "bb_pband": 0.50},
            {"Open": 1.0990, "High": 1.1000, "Low": 1.0985, "Close": 1.0995,
             "bb_width": 0.011, "bb_pband": 0.50},
            {"Open": 1.0995, "High": 1.1002, "Low": 1.0990, "Close": 1.0997,
             "bb_width": 0.0105, "bb_pband": 0.50},
            {"Open": 1.0997, "High": 1.1003, "Low": 1.0991, "Close": 1.0998,
             "bb_width": prev_width, "bb_pband": 0.50},
            {"Open": 1.0998, "High": 1.1015, "Low": 1.0996, "Close": 1.1012,
             "bb_width": signal_width, "bb_pband": signal_pband},
            {"Open": current_open, "High": 1.1011, "Low": 1.1006, "Close": 1.1008,
             "bb_width": current_width, "bb_pband": current_pband},
        ],
        index=pd.date_range("2026-05-05 08:45", periods=10, freq="15min", tz="UTC"),
    )


def _ctx(df: pd.DataFrame) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=0.0010,
        ema9=1.1010,
        ema21=1.1005,
        ema50=1.1000,
        ema200=1.0990,
        bbpb=float(row["bb_pband"]),
        bb_width=float(row["bb_width"]),
        regime={"squeeze_bars": 5, "bb_width_pct": 20.0},
        symbol="EURUSD=X",
        tf="15m",
        hour_utc=12,
        is_jpy=False,
        pip_mult=10000,
        df=df,
        bar_time=df.index[-1],
    )


def test_redesign_v2_uses_closed_signal_bar_not_current_bar(monkeypatch):
    monkeypatch.setenv("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2", "1")
    SqueezeReleaseMomentum.reset_dedup_state()
    df = _df()

    got = SqueezeReleaseMomentum().evaluate(_ctx(df))

    assert got is not None
    assert got.signal == "BUY"
    assert any("bbpb=0.82" in reason for reason in got.reasons)


def test_redesign_v2_rejects_when_closed_bar_has_no_release(monkeypatch):
    monkeypatch.setenv("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2", "1")
    SqueezeReleaseMomentum.reset_dedup_state()
    df = _df(signal_width=0.009, prev_width=0.010, current_width=0.015,
             signal_pband=0.82, current_pband=0.82)

    got = SqueezeReleaseMomentum().evaluate(_ctx(df))

    assert got is None


def test_current_default_path_is_unchanged(monkeypatch):
    monkeypatch.delenv("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2", raising=False)
    SqueezeReleaseMomentum.reset_dedup_state()
    df = _df(signal_width=0.009, prev_width=0.010, current_width=0.015,
             signal_pband=0.50, current_pband=0.82, current_open=1.1005)

    got = SqueezeReleaseMomentum().evaluate(_ctx(df))

    assert got is not None
    assert got.signal == "BUY"
    assert any("bbpb=0.82" in reason for reason in got.reasons)


def test_redesign_v2_default_off_allows_existing_repeat(monkeypatch):
    monkeypatch.delenv("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2", raising=False)
    SqueezeReleaseMomentum.reset_dedup_state()
    ctx = _ctx(_df(signal_width=0.009, prev_width=0.010, current_width=0.015,
                  signal_pband=0.50, current_pband=0.82, current_open=1.1005))
    strategy = SqueezeReleaseMomentum()

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is not None


def test_redesign_v2_dedups_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2", "1")
    SqueezeReleaseMomentum.reset_dedup_state()
    ctx = _ctx(_df())
    strategy = SqueezeReleaseMomentum()

    first = strategy.evaluate(ctx)
    second = strategy.evaluate(ctx)

    assert first is not None
    assert second is None


def test_redesign_v2_shadow_worker_registration_is_opt_in(monkeypatch):
    engine = DaytradeEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "ema_cross", 6.0)
    srm = Candidate("BUY", 60, 1.0, 1.2, ["srm"], "squeeze_release_momentum", 5.0)

    monkeypatch.delenv("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2", raising=False)
    monkeypatch.delenv("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, srm], best) == []

    monkeypatch.setenv("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2", "1")
    monkeypatch.setenv("SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, srm], best) == [srm]
