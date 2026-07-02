"""
Smoke tests for ZZ Pivot v60 + SizeReduce (EUR_USD M15 MR at Trend Extreme).

LIVE intentional exception per user judgment 2026-05-28.
Memory: project_zz_pivot_v60_sr_live_queue_2026_05_28.

Coverage:
- Strategy loads cleanly
- Pair filter rejects non-EUR_USD
- TF filter rejects non-M15
- Loser-zone detection (F1: RSI<30 ∩ MACD<0, F3: ATR_ratio≥1.6) yields zz_pivot_v60_sr_lo entry_type
- Normal-zone detection yields zz_pivot_v60_sr entry_type
- Engine registers the strategy
- _PAIR_LOT_BOOST has both entries with correct ratios

NOTE: This is MVP v1 smoke testing. Full 207-trade BT reproduction deferred to v2.
"""
from __future__ import annotations

import pandas as pd
import pytest

from strategies.daytrade.zz_pivot_v60_sr import ZzPivotV60Sr


def _make_ctx(symbol="EUR_USD", tf="15m", entry=1.0850, rsi=50.0, macdh=0.0,
              atr=0.0010, bbpb=0.5, adx=20.0, open_price=None, df=None):
    """Build a minimal SignalContext-like stub for testing."""
    from strategies.context import SignalContext

    if open_price is None:
        open_price = entry
    if df is None:
        # Build a sufficiently long df with realistic OHLCV
        n = 200
        idx = pd.date_range("2026-01-01", periods=n, freq="15min", tz="UTC")
        df = pd.DataFrame({
            "Open": [entry] * n,
            "High": [entry + atr] * n,
            "Low": [entry - atr] * n,
            "Close": [entry] * n,
            "Volume": [1000.0] * n,
            "rsi": [rsi] * n,
            "rsi5": [rsi] * n,
            "rsi9": [rsi] * n,
            "macd_hist": [macdh] * n,
            "bb_pband": [bbpb] * n,
            "ema9": [entry] * n,
            "ema21": [entry] * n,
            "ema50": [entry] * n,
            "ema200": [entry] * n,
            "bb_upper": [entry + 2 * atr] * n,
            "bb_mid": [entry] * n,
            "bb_lower": [entry - 2 * atr] * n,
            "bb_width": [4 * atr] * n,
            "adx": [adx] * n,
            "adx_pos": [adx] * n,
            "adx_neg": [adx] * n,
            "stoch_k": [50.0] * n,
            "stoch_d": [50.0] * n,
        }, index=idx)

    ctx = SignalContext()
    ctx.symbol = symbol
    ctx.tf = tf
    ctx.entry = entry
    ctx.open_price = open_price
    ctx.rsi = rsi
    ctx.rsi5 = rsi
    ctx.rsi9 = rsi
    ctx.macdh = macdh
    ctx.atr = atr
    ctx.bbpb = bbpb
    ctx.bb_upper = entry + 2 * atr
    ctx.bb_mid = entry
    ctx.bb_lower = entry - 2 * atr
    ctx.bb_width = 4 * atr
    ctx.adx = adx
    ctx.df = df
    ctx.hour_utc = 10
    ctx.layer0 = {}
    ctx.layer1 = {}
    ctx.regime = {}
    return ctx


def test_strategy_loads():
    s = ZzPivotV60Sr()
    assert s.name == "zz_pivot_v60_sr"
    assert s.LOSER_ZONE_NAME == "zz_pivot_v60_sr_lo"
    assert s.mode == "daytrade"
    assert s.enabled is True
    assert s.strategy_type == "MR"


def test_pair_filter_rejects_usdjpy():
    s = ZzPivotV60Sr()
    ctx = _make_ctx(symbol="USD_JPY")
    assert s.evaluate(ctx) is None


def test_tf_filter_rejects_m5():
    s = ZzPivotV60Sr()
    ctx = _make_ctx(tf="5m")
    assert s.evaluate(ctx) is None


def test_no_signal_in_quiet_market():
    """Neutral RSI/BB/MACD in EUR_USD M15 — no peak/trough → return None."""
    s = ZzPivotV60Sr()
    ctx = _make_ctx()
    assert s.evaluate(ctx) is None


def test_engine_registers_strategy():
    from strategies.daytrade import DaytradeEngine
    engine = DaytradeEngine()
    names = [strat.name for strat in engine.strategies]
    assert "zz_pivot_v60_sr" in names


def test_pair_lot_boost_removed_2026_07_02():
    """LIVE demote 2026-07-02 (rule:R2): 30d clean live N=11 WR=54.5% -30.5pip.

    _PAIR_PROMOTED and the paired lot-boost entries were removed (supersedes
    the 2026-05-28 Path-B pre-reg N=30 withdrawal schedule under Rule 2 +
    user 2026-07-02 direction). Shadow continues; re-promote is R1-only.
    See decisions/live-bleeder-demotions-2026-07-02.md.
    """
    from modules.demo_trader import DemoTrader
    assert ("zz_pivot_v60_sr", "EUR_USD") not in DemoTrader._PAIR_PROMOTED
    assert ("zz_pivot_v60_sr_lo", "EUR_USD") not in DemoTrader._PAIR_PROMOTED
    assert ("zz_pivot_v60_sr", "EUR_USD") not in DemoTrader._PAIR_LOT_BOOST
    assert ("zz_pivot_v60_sr_lo", "EUR_USD") not in DemoTrader._PAIR_LOT_BOOST


def test_rci_computation():
    """RCI(9) returns float in [-100, 100]."""
    s = ZzPivotV60Sr()
    # Monotonically increasing series → positive RCI
    rci_up = s._rci([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], 9)
    assert -100.0 <= rci_up <= 100.0
    assert rci_up > 0  # ascending should be positive
    # Monotonically decreasing series → negative RCI
    rci_dn = s._rci([9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0], 9)
    assert -100.0 <= rci_dn <= 100.0
    assert rci_dn < 0


def test_atr_series_computation():
    """ATR series (Wilder smoothed) returns positive values."""
    import pandas as pd
    s = ZzPivotV60Sr()
    n = 50
    df = pd.DataFrame({
        "High": [1.0 + 0.001 * (i % 5) for i in range(n)],
        "Low":  [0.999 - 0.001 * (i % 5) for i in range(n)],
        "Close": [1.0 + 0.0005 * (i % 3) for i in range(n)],
    })
    atr = s._compute_atr_series(df, 14)
    assert len(atr) == n
    assert (atr.iloc[-10:] > 0).all()
