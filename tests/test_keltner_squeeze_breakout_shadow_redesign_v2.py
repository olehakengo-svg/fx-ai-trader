from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.hourly import HourlyEngine
from strategies.hourly.keltner_squeeze_breakout import KeltnerSqueezeBreakout


def _df(*, n=30, signal_at=-1) -> pd.DataFrame:
    idx = pd.date_range(end="2026-05-05 12:00", periods=n, freq="1h", tz="UTC")
    open_ = np.full(n, 1.1001)
    close = np.full(n, 1.1002)
    high = np.full(n, 1.1005)
    low = np.full(n, 1.0995)
    squeeze_on = np.full(n, False)

    sig_idx = signal_at if signal_at >= 0 else n + signal_at
    for pos in range(max(0, sig_idx - 3), sig_idx):
        squeeze_on[pos] = True

    open_[sig_idx] = 1.1002
    close[sig_idx] = 1.1012
    high[sig_idx] = 1.1014
    low[sig_idx] = 1.1000
    squeeze_on[sig_idx] = False

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0010),
            "atr7": np.full(n, 0.0010),
            "ema9": np.full(n, 1.1010),
            "ema21": np.full(n, 1.1005),
            "ema50": np.full(n, 1.1000),
            "ema200": np.full(n, 1.0990),
            "adx": np.full(n, 18.0),
            "adx_pos": np.full(n, 30.0),
            "adx_neg": np.full(n, 15.0),
            "rsi": np.full(n, 55.0),
            "rsi5": np.full(n, 55.0),
            "rsi9": np.full(n, 55.0),
            "stoch_k": np.full(n, 55.0),
            "stoch_d": np.full(n, 55.0),
            "macd_hist": np.linspace(0.0001, 0.0030, n),
            "bb_pband": np.full(n, 0.7),
            "squeeze_on": squeeze_on,
            "kelt_upper": np.full(n, 1.1010),
            "kelt_mid": np.full(n, 1.1000),
            "kelt_lower": np.full(n, 1.0990),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, backtest_mode=True, bar_time=None) -> SignalContext:
    row = df.iloc[-1]
    prev = df.iloc[-2]
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
    monkeypatch.delenv("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2", raising=False)
    KeltnerSqueezeBreakout.reset_dedup_state()
    ctx = _ctx(_df(signal_at=-1), bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    first = KeltnerSqueezeBreakout().evaluate(ctx)
    second = KeltnerSqueezeBreakout().evaluate(ctx)

    assert first is not None
    assert first.signal == "BUY"
    assert second is not None
    assert not any("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2" in reason for reason in first.reasons)


def test_v2_uses_last_closed_bar_not_current_intrabar(monkeypatch):
    monkeypatch.setenv("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2", "1")
    KeltnerSqueezeBreakout.reset_dedup_state()
    df = _df(signal_at=-2)
    df.iloc[-1, df.columns.get_loc("Open")] = 1.1005
    df.iloc[-1, df.columns.get_loc("Close")] = 1.1006

    got = KeltnerSqueezeBreakout().evaluate(_ctx(df, bar_time=df.index[-1]))

    assert got is not None
    assert got.signal == "BUY"
    assert round(got.sl, 5) == 1.09920
    assert round(got.tp, 5) == 1.10360
    assert any("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2" in reason for reason in got.reasons)


def test_v2_rejects_current_intrabar_breakout(monkeypatch):
    monkeypatch.setenv("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2", "1")
    KeltnerSqueezeBreakout.reset_dedup_state()

    got = KeltnerSqueezeBreakout().evaluate(
        _ctx(_df(signal_at=-1), bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))
    )

    assert got is None


def test_v2_live_without_bar_time_is_blocked(monkeypatch):
    monkeypatch.setenv("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2", "1")
    KeltnerSqueezeBreakout.reset_dedup_state()

    got = KeltnerSqueezeBreakout().evaluate(_ctx(_df(signal_at=-2), backtest_mode=False, bar_time=None))

    assert got is None


def test_v2_dedups_same_symbol_signal_bar(monkeypatch):
    monkeypatch.setenv("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2", "1")
    KeltnerSqueezeBreakout.reset_dedup_state()
    ctx = _ctx(_df(signal_at=-2), bar_time=pd.Timestamp("2026-05-05 12:00", tz="UTC"))

    first = KeltnerSqueezeBreakout().evaluate(ctx)
    second = KeltnerSqueezeBreakout().evaluate(ctx)

    assert first is not None
    assert second is None


def test_v2_shadow_worker_registration_is_idempotent_after_h1_shadow_ramp(monkeypatch):
    engine = HourlyEngine()
    best = Candidate("BUY", 60, 1.0, 1.2, ["best"], "donchian_momentum_breakout", 5.5)
    ksb = Candidate("BUY", 60, 1.0, 1.2, ["ksb"], "keltner_squeeze_breakout", 5.0)

    monkeypatch.delenv("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2", raising=False)
    monkeypatch.delenv("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([best, ksb], best) == [ksb]

    monkeypatch.setenv("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2", "1")
    monkeypatch.setenv("KELTNER_SQUEEZE_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([best, ksb], best) == [ksb]
