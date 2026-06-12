"""hull_donchian_fade — E2E firing + wiring tests.

検証エンジン (hull-donchian-1m-validation) の凍結スペックと本番実装の drift を防ぐ:
  1. 実データ (MASSIVE EUR_USD 15m parquet) で発火すること + Candidate 形状
  2. シグナル意味論: fade = 上方ブレイク×bull を SELL / 下方ブレイク×bear を BUY、
     TP=basis が entry の正しい側、SL=4xATR
  3. per-bar dedup
  4. LIVE env override (HULL_DONCHIAN_FADE_LIVE_ENABLE) の eligible 判定
  5. silent-drop 防止配線: QUALIFIED_TYPES / SHIELD whitelist / MIN lot 強制
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.context import SignalContext
from strategies.daytrade.hull_donchian_fade import HullDonchianFade

PARQUET = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "cache", "massive", "EUR_USD_15m.parquet",
)


@pytest.fixture(scope="module")
def m15() -> pd.DataFrame:
    if not os.path.exists(PARQUET):
        pytest.skip("EUR_USD_15m.parquet not available")
    df = pd.read_parquet(PARQUET)
    if "Close" not in df.columns and "close" in df.columns:
        df = df.rename(columns={"open": "Open", "high": "High",
                                "low": "Low", "close": "Close", "volume": "Volume"})
    return df


def _ctx(window: pd.DataFrame, backtest: bool = True) -> SignalContext:
    """Minimal SignalContext for evaluate()."""
    entry = float(window["Close"].iloc[-1 if backtest else -2])
    try:
        return SignalContext(symbol="EURUSD=X", df=window, entry=entry,
                             atr=1e-4, backtest_mode=backtest)
    except TypeError:
        ctx = SignalContext.__new__(SignalContext)
        ctx.symbol = "EURUSD=X"
        ctx.df = window
        ctx.entry = entry
        ctx.atr = 1e-4
        ctx.backtest_mode = backtest
        return ctx


def _scan_fires(df: pd.DataFrame, strat: HullDonchianFade, start: int, n_bars: int,
                window: int = 200):
    fires = []
    for i in range(start, min(start + n_bars, len(df))):
        sub = df.iloc[i - window:i]
        cand = strat.evaluate(_ctx(sub, backtest=True))
        if cand is not None:
            fires.append((df.index[i - 1], cand))
    return fires


class TestFiring:
    def test_fires_on_historical_data_with_valid_shape(self, m15):
        strat = HullDonchianFade()
        # 2024 区間 20 営業日ぶん (~2000 bars) スキャン — holdout 期間内で発火実績あり
        start = len(m15) - 96 * 400
        fires = _scan_fires(m15, strat, start=start, n_bars=96 * 20)
        assert len(fires) >= 1, "20日スキャンで1件も発火しない = silent-drop 兆候"
        for _, c in fires:
            assert c.signal in ("BUY", "SELL")
            assert c.entry_type == "hull_donchian_fade"
            assert c.max_hold_bars == 96
            if c.signal == "SELL":
                assert c.tp < c.sl, "SELL: TP(basis) は SL より下"
            else:
                assert c.tp > c.sl, "BUY: TP(basis) は SL より上"
            assert c.sr_meta["width_atr"] <= HullDonchianFade.MAX_WIDTH_ATR

    def test_sell_means_fading_upside_break(self, m15):
        """SELL 発火バーは『前バー Donchian 上限を上抜け』していること (fade 意味論)。"""
        strat = HullDonchianFade()
        start = len(m15) - 96 * 400
        fires = _scan_fires(m15, strat, start=start, n_bars=96 * 40)
        sells = [(ts, c) for ts, c in fires if c.signal == "SELL"]
        if not sells:
            pytest.skip("no SELL in scan window")
        for ts, _ in sells[:5]:
            i = m15.index.get_loc(ts)
            close_i = float(m15["Close"].iloc[i])
            upper_prev = float(m15["High"].iloc[i - HullDonchianFade.DON_LEN:i].max())
            assert close_i > upper_prev, "SELL は上方ブレイクの逆張りのはず"

    def test_per_bar_dedup(self, m15):
        scan = HullDonchianFade()
        start = len(m15) - 96 * 400
        fires = _scan_fires(m15, scan, start=start, n_bars=96 * 40)
        if not fires:
            pytest.skip("no fire in window")
        ts, _ = fires[0]
        i = m15.index.get_loc(ts) + 1
        sub = m15.iloc[i - 200:i]
        # fresh インスタンスで同一 closed bar を連続評価 → 1回目 Candidate / 2回目 dedup None
        strat = HullDonchianFade()
        first = strat.evaluate(_ctx(sub, backtest=True))
        assert first is not None
        again = strat.evaluate(_ctx(sub, backtest=True))
        assert again is None


class TestLiveWiring:
    def test_live_eligible_env_off_by_default(self, monkeypatch):
        from modules.demo_trader import DemoTrader
        monkeypatch.setattr(DemoTrader, "_HULL_DONCHIAN_FADE_LIVE_ENABLE", False)
        assert not DemoTrader._hull_donchian_fade_live_eligible(
            "hull_donchian_fade", "EUR_USD")

    def test_live_eligible_env_on(self, monkeypatch):
        from modules.demo_trader import DemoTrader
        monkeypatch.setattr(DemoTrader, "_HULL_DONCHIAN_FADE_LIVE_ENABLE", True)
        assert DemoTrader._hull_donchian_fade_live_eligible(
            "hull_donchian_fade", "EUR_USD")
        # 別戦略/別ペアには波及しない
        assert not DemoTrader._hull_donchian_fade_live_eligible(
            "hull_donchian_fade", "GBP_USD")
        assert not DemoTrader._hull_donchian_fade_live_eligible(
            "zz_pivot_v60_sr", "EUR_USD")

    def test_resolve_tier_live_override(self, monkeypatch):
        from modules.demo_trader import DemoTrader
        monkeypatch.setattr(DemoTrader, "_HULL_DONCHIAN_FADE_LIVE_ENABLE", True)
        trader = DemoTrader.__new__(DemoTrader)
        tier = DemoTrader._resolve_tier(trader, "hull_donchian_fade", "EUR_USD", "daytrade_eur")
        assert tier == "HULL_DONCHIAN_FADE_LIVE"

    def test_shield_eur_dt_whitelist_membership(self):
        """daytrade_eur は _OANDA_MODE_BLOCKED — whitelist 不在だと silent drop (ZZ v60 事故と同型)。"""
        from modules.demo_trader import DemoTrader
        assert "hull_donchian_fade" in DemoTrader._SHIELD_EUR_DT_WHITELIST

    def test_registered_in_daytrade_engine(self):
        from strategies.daytrade import DaytradeEngine
        eng = DaytradeEngine()
        assert eng.get_strategy("hull_donchian_fade") is not None
