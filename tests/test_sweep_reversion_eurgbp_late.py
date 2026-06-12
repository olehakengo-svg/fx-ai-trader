"""Tests for sweep_reversion_eurgbp_late (12y grid survivor, LIVE exception 2026-06-12).

Covers: signal fire/no-fire matrix, Candidate contract, dedup/cooldown,
env kill switch, demo_trader LIVE eligibility + tier resolution.
"""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from strategies.daytrade.sweep_reversion_eurgbp_late import SweepReversionEurgbpLate
from strategies.context import SignalContext


BARS = 130  # > MIN_HISTORY (115)
BASE = 0.8500


def _df(*, last_hour_utc=21, sweep=True, reclaim=True, last_minute=30):
    """Synthetic EUR_GBP 15m frame ending at given UTC hour."""
    end = pd.Timestamp(2026, 6, 11, last_hour_utc, last_minute, tz="UTC")
    idx = pd.date_range(end=end, periods=BARS, freq="15min")
    close = np.full(BARS, BASE)
    high = close + 0.0005
    low = close - 0.0005
    opn = close.copy()
    swing_lo = BASE - 0.0005  # rolling min of prior lows
    if sweep:
        low[-1] = swing_lo - 0.0004  # well below swing_lo - 0.05*ATR(~0.00005)
    close_last = BASE if reclaim else swing_lo - 0.0004
    close[-1] = close_last
    high[-1] = BASE + 0.0005
    opn[-1] = BASE - 0.0001
    return pd.DataFrame(
        {"Open": opn, "High": high, "Low": low, "Close": close}, index=idx
    )


def _ctx(df, symbol="EURGBP=X"):
    ctx = SignalContext()
    ctx.symbol = symbol
    ctx.df = df
    ctx.entry = float(df["Close"].iloc[-1])
    ctx.backtest_mode = True  # closed_idx = -1
    return ctx


def _strat():
    return SweepReversionEurgbpLate()


# ── fire ──────────────────────────────────────────────────────────
def test_fires_on_late_sweep_reclaim():
    cand = _strat().evaluate(_ctx(_df()))
    assert cand is not None
    assert cand.signal == "BUY"
    assert cand.entry_type == "sweep_reversion_eurgbp_late"


def test_candidate_exit_contract():
    cand = _strat().evaluate(_ctx(_df()))
    assert cand.max_hold_bars == 48
    assert cand.sl < cand.tp
    entry = BASE
    assert cand.sl < entry < cand.tp


def test_fires_at_hour_23():
    cand = _strat().evaluate(_ctx(_df(last_hour_utc=23)))
    assert cand is not None


# ── no-fire matrix ────────────────────────────────────────────────
def test_no_fire_wrong_pair():
    assert _strat().evaluate(_ctx(_df(), symbol="EURUSD=X")) is None


def test_no_fire_outside_late_window():
    for h in (3, 10, 15, 20):
        assert _strat().evaluate(_ctx(_df(last_hour_utc=h))) is None, f"h={h} fired"


def test_no_fire_without_sweep():
    assert _strat().evaluate(_ctx(_df(sweep=False))) is None


def test_no_fire_without_reclaim():
    assert _strat().evaluate(_ctx(_df(reclaim=False))) is None


def test_no_fire_short_history():
    df = _df().iloc[-50:]
    assert _strat().evaluate(_ctx(df)) is None


def test_env_kill_switch(monkeypatch):
    monkeypatch.setenv("SWEEP_REVERSION_EURGBP_ENABLE", "0")
    assert _strat().evaluate(_ctx(_df())) is None


# ── dedup / cooldown ──────────────────────────────────────────────
def test_per_bar_dedup():
    strat = _strat()
    df = _df()
    assert strat.evaluate(_ctx(df)) is not None
    assert strat.evaluate(_ctx(df)) is None  # same bar → dedup


def test_cooldown_12_bars():
    strat = _strat()
    df1 = _df(last_minute=30)
    assert strat.evaluate(_ctx(df1)) is not None
    # 1 bar later (15min) — inside 12-bar (3h) cooldown
    df2 = _df(last_minute=45)
    assert strat.evaluate(_ctx(df2)) is None


def test_fires_again_after_cooldown():
    strat = _strat()
    assert strat.evaluate(_ctx(_df(last_hour_utc=21, last_minute=30))) is not None
    # next day, same window (>> 3h cooldown)
    end = pd.Timestamp(2026, 6, 12, 21, 30, tz="UTC")
    idx = pd.date_range(end=end, periods=BARS, freq="15min")
    df = _df()
    df.index = idx
    assert strat.evaluate(_ctx(df)) is not None


# ── demo_trader LIVE eligibility ──────────────────────────────────
def test_live_eligible_env_off_default():
    from modules.demo_trader import DemoTrader
    assert DemoTrader._sweep_reversion_eurgbp_live_eligible(
        "sweep_reversion_eurgbp_late", "EUR_GBP") is False or \
        DemoTrader._SWEEP_REVERSION_EURGBP_LIVE_ENABLE  # env may be set in CI


def test_live_eligible_env_on(monkeypatch):
    from modules.demo_trader import DemoTrader
    monkeypatch.setattr(DemoTrader, "_SWEEP_REVERSION_EURGBP_LIVE_ENABLE", True)
    assert DemoTrader._sweep_reversion_eurgbp_live_eligible(
        "sweep_reversion_eurgbp_late", "EUR_GBP") is True
    # 他戦略 / 他ペアは False (暴発防止)
    assert DemoTrader._sweep_reversion_eurgbp_live_eligible(
        "session_time_bias", "EUR_GBP") is False
    assert DemoTrader._sweep_reversion_eurgbp_live_eligible(
        "sweep_reversion_eurgbp_late", "EUR_USD") is False


def test_resolve_tier_env_on(monkeypatch):
    from modules.demo_trader import DemoTrader
    monkeypatch.setattr(DemoTrader, "_SWEEP_REVERSION_EURGBP_LIVE_ENABLE", True)
    tier = DemoTrader._resolve_tier(
        DemoTrader.__new__(DemoTrader), "sweep_reversion_eurgbp_late", "EUR_GBP")
    assert tier == "SWEEP_REVERSION_EURGBP_LIVE"


# ── Codex review 2026-06-12 pin tests (gate constants are function-locals) ──
def _demo_trader_source():
    import inspect
    import modules.demo_trader as dt
    return inspect.getsource(dt)


def test_pin_eurgbp_allstop_whitelist():
    """Codex Critical#1: EUR_GBP 全停止 gate の whitelist に本戦略が居ること。
    外れると env LIVE override に到達する前に return し、一切発火しなくなる。"""
    src = _demo_trader_source()
    import re
    m = re.search(r"_EURGBP_DAILY_MR_WHITELIST = \{[^}]+\}", src)
    assert m, "_EURGBP_DAILY_MR_WHITELIST not found"
    assert "sweep_reversion_eurgbp_late" in m.group(0)


def test_pin_sltp_preserve_set():
    """Codex Critical#2: SL=4×ATR/TP=6×ATR は research 分布保存の契約。
    _1H_PRESERVE_SLTP から外れると共有 DT 経路が ~1×ATR に上書きする。"""
    src = _demo_trader_source()
    import re
    m = re.search(r"_1H_PRESERVE_SLTP = \{[^}]+\}", src)
    assert m, "_1H_PRESERVE_SLTP not found"
    assert "sweep_reversion_eurgbp_late" in m.group(0)


def test_pin_c1_early_exit_exemption():
    """Codex Important#3: C1 (保持時間50%で含み損→早期損切り) 免除。
    research は 48-bar close-to-close 計測で、6-12h 回復 loser が WR に寄与する。"""
    src = _demo_trader_source()
    idx = src.find('!= "sweep_reversion_eurgbp_late"')
    assert idx > 0, "C1 exemption for sweep_reversion_eurgbp_late missing"
    # 免除が C1 ブロックの条件部に居ること (TIME_DECAY_EXIT の手前、実測距離 1346 chars)
    assert "TIME_DECAY_EXIT" in src[idx:idx + 2000]


def test_pin_max_hold_12h():
    """_ENTRY_TYPE_MAX_HOLD に 12h (43200s) が登録されていること。"""
    src = _demo_trader_source()
    assert '"sweep_reversion_eurgbp_late": 12 * 3600' in src
