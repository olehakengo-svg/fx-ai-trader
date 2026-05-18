from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.hourly import HourlyEngine
from strategies.hourly.donchian_momentum_breakout import DonchianMomentumBreakout


def _df(*, n=60, signal_at=-1) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="1h", tz="UTC")
    open_ = np.full(n, 1.1950)
    close = np.full(n, 1.1952)
    high = np.full(n, 1.1960)
    low = np.full(n, 1.1940)
    don_high = np.full(n, 1.2000)
    don_low = np.full(n, 1.1960)
    don_mid = np.full(n, 1.1980)

    sig_idx = signal_at if signal_at >= 0 else n + signal_at
    open_[sig_idx] = 1.2002
    close[sig_idx] = 1.2012
    high[sig_idx] = 1.2015
    low[sig_idx] = 1.1995

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": np.full(n, 1.2008),
            "ema21": np.full(n, 1.2000),
            "ema50": np.full(n, 1.1990),
            "ema200": np.full(n, 1.1980),
            "adx": np.full(n, 25.0),
            "adx_pos": np.full(n, 30.0),
            "adx_neg": np.full(n, 15.0),
            "rsi": np.full(n, 55.0),
            "rsi5": np.full(n, 55.0),
            "rsi9": np.full(n, 55.0),
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 55.0),
            "macd_hist": np.full(n, 0.0001),
            "bb_pband": np.full(n, 0.7),
            "don_high48": don_high,
            "don_low48": don_low,
            "don_mid48": don_mid,
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode=True, bar_time=None) -> SignalContext:
    row = df.iloc[-1]
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
        macdh_prev=float(df["macd_hist"].iloc[-2]),
        symbol="EURUSD=X",
        tf="1h",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "bull"},
        backtest_mode=backtest_mode,
        bar_time=bar_time,
    )


def test_default_off_uses_existing_current_bar_path(monkeypatch):
    monkeypatch.delenv("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2", raising=False)
    DonchianMomentumBreakout.reset_dedup_state()
    ctx = _ctx(_df(signal_at=-1), bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    first = DonchianMomentumBreakout().evaluate(ctx)
    second = DonchianMomentumBreakout().evaluate(ctx)

    assert first is not None
    assert first.signal == "BUY"
    assert second is not None


def test_v2_uses_last_closed_bar_not_current_intrabar(monkeypatch):
    monkeypatch.setenv("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2", "1")
    DonchianMomentumBreakout.reset_dedup_state()
    df = _df(signal_at=-2)
    df.iloc[-1, df.columns.get_loc("Open")] = 1.1990
    df.iloc[-1, df.columns.get_loc("Close")] = 1.1988

    got = DonchianMomentumBreakout().evaluate(_ctx(df, bar_time=df.index[-1]))

    assert got is not None
    assert got.signal == "BUY"
    assert any("V2 closed-bar breakout" in reason for reason in got.reasons)


def test_v2_rejects_current_intrabar_breakout(monkeypatch):
    monkeypatch.setenv("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2", "1")
    DonchianMomentumBreakout.reset_dedup_state()

    got = DonchianMomentumBreakout().evaluate(_ctx(_df(signal_at=-1), bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC")))

    assert got is None


def test_v2_live_without_bar_time_is_blocked(monkeypatch):
    monkeypatch.setenv("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2", "1")
    DonchianMomentumBreakout.reset_dedup_state()

    got = DonchianMomentumBreakout().evaluate(_ctx(_df(signal_at=-2), backtest_mode=False, bar_time=None))

    assert got is None


def test_v2_dedups_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2", "1")
    DonchianMomentumBreakout.reset_dedup_state()
    ctx = _ctx(_df(signal_at=-2), bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    first = DonchianMomentumBreakout().evaluate(ctx)
    second = DonchianMomentumBreakout().evaluate(ctx)

    assert first is not None
    assert second is None


def test_v2_shadow_worker_registration_is_idempotent_after_h1_shadow_ramp(monkeypatch):
    engine = HourlyEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "keltner_squeeze_breakout", 5.5)
    dmb = Candidate("BUY", 60, 1.0, 1.2, ["dmb"], "donchian_momentum_breakout", 5.0)

    monkeypatch.delenv("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2", raising=False)
    monkeypatch.delenv("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, dmb], best) == [dmb]

    monkeypatch.setenv("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2", "1")
    monkeypatch.setenv("DONCHIAN_MOMENTUM_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, dmb], best) == [dmb]
