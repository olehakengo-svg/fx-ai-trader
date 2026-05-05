from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.london_breakout import LondonBreakout


def _df(*, asia_spike_high: float, fixed_high: float | None = None,
        signal_close: float = 1.1012) -> pd.DataFrame:
    n = 600
    idx = pd.date_range(end="2026-05-05 08:00", periods=n, freq="1min", tz="UTC")
    open_ = np.full(n, 1.1002)
    high = np.full(n, 1.1010)
    low = np.full(n, 1.1000)
    close = np.full(n, 1.1003)

    fixed_high = asia_spike_high if fixed_high is None else fixed_high
    asia_mask = (idx.hour >= 0) & (idx.hour < 7) & (idx.date == pd.Timestamp("2026-05-05").date())
    high[asia_mask] = fixed_high
    low[asia_mask] = 1.1000

    # Put the fixed-window spike outside the legacy 120-minute rolling window.
    spike_pos = idx.get_loc(pd.Timestamp("2026-05-05 02:00", tz="UTC"))
    high[spike_pos] = asia_spike_high

    # Keep late Asia/London bars low so legacy rolling range can differ.
    late_mask = idx >= pd.Timestamp("2026-05-05 06:01", tz="UTC")
    high[late_mask] = 1.1010
    low[late_mask] = 1.1000

    close[-1] = signal_close
    open_[-1] = signal_close - 0.0001
    high[-1] = 1.1010

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(n, 1000.0),
            "atr": np.full(n, 0.0005),
            "atr7": np.full(n, 0.0005),
            "ema9": np.full(n, 1.1010),
            "ema21": np.full(n, 1.1005),
            "adx": np.full(n, 22.0),
        },
        index=idx,
    )


def _ctx(df: pd.DataFrame, *, entry: float | None = None) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"] if entry is None else entry),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        adx=float(row["adx"]),
        symbol="EURUSD=X",
        tf="1m",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        backtest_mode=True,
        bar_time=df.index[-1],
        hour_utc=df.index[-1].hour,
    )


def test_v2_default_off_preserves_legacy_rolling_range(monkeypatch):
    monkeypatch.delenv("LONDON_BREAKOUT_REDESIGN_V2", raising=False)

    cand = LondonBreakout().evaluate(_ctx(_df(asia_spike_high=1.1030, fixed_high=1.1010)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert not any("LONDON_BREAKOUT_REDESIGN_V2" in reason for reason in cand.reasons)


def test_v2_uses_fixed_asia_window_and_rejects_non_asia_breakout(monkeypatch):
    monkeypatch.setenv("LONDON_BREAKOUT_REDESIGN_V2", "1")

    cand = LondonBreakout().evaluate(_ctx(_df(asia_spike_high=1.1030, fixed_high=1.1010)))

    assert cand is None


def test_v2_fires_on_closed_bar_break_of_valid_fixed_asia_high(monkeypatch):
    monkeypatch.setenv("LONDON_BREAKOUT_REDESIGN_V2", "1")

    cand = LondonBreakout().evaluate(_ctx(_df(asia_spike_high=1.1010, signal_close=1.1012)))

    assert cand is not None
    assert cand.signal == "BUY"
    assert round(cand.sl, 5) == 1.10085
    assert any("fixed Asia high" in reason for reason in cand.reasons)


def test_v2_ignores_intrabar_entry_when_closed_close_has_not_broken(monkeypatch):
    monkeypatch.setenv("LONDON_BREAKOUT_REDESIGN_V2", "1")

    df = _df(asia_spike_high=1.1010, signal_close=1.10102)
    cand = LondonBreakout().evaluate(_ctx(df, entry=1.1012))

    assert cand is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    london = Candidate("BUY", 70, 1.0, 2.0, [], "london_breakout", 4.0)
    engine = ScalperEngine()

    monkeypatch.setenv("LONDON_BREAKOUT_REDESIGN_V2", "1")
    monkeypatch.delenv("LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, london], other) == []

    monkeypatch.setenv("LONDON_BREAKOUT_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, london], other) == [london]
