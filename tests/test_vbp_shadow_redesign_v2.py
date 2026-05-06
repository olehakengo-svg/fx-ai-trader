from __future__ import annotations

import pytest

from strategies.base import Candidate
from strategies.micro_scalp.base import CostModel, TickBar
from strategies.micro_scalp.vbp import VolatilityBreakoutPullback
from strategies.scalp import ScalperEngine


def _bars() -> list[TickBar]:
    bars = []
    price = 1.10000
    for i in range(35):
        open_ = price
        close = price
        high = 1.10000
        low = 1.09900

        if i == 25:
            open_ = 1.10020
            close = 1.10100
            high = 1.10120
            low = 1.10010
        elif i == 26:
            open_ = 1.10100
            close = 1.10110
            high = 1.10140
            low = 1.10080
        elif i == 27:
            open_ = 1.10110
            close = 1.10055
            high = 1.10095
            low = 1.10030
        elif 28 <= i < 32:
            open_ = 1.10055
            close = 1.10060
            high = 1.10075
            low = 1.10035
        elif i >= 32:
            open_ = 1.10060 + (i - 32) * 0.00005
            close = open_ + 0.00010
            high = close + 0.00005
            low = open_ - 0.00005

        bars.append(
            TickBar(
                ts=float(i),
                open=open_,
                high=high,
                low=low,
                close=close,
                tick_volume=100,
            )
        )
        price = close
    return bars


def _strategy() -> VolatilityBreakoutPullback:
    cost = CostModel(spread_pips=0.1, latency_ms=0, slippage_per_ms=0, symbol="EUR_USD")
    return VolatilityBreakoutPullback(cost, lookback_sec=12, pullback_ratio=0.5)


def test_v2_default_off_preserves_legacy_self_included_range_miss(monkeypatch):
    monkeypatch.delenv("VBP_REDESIGN_V2", raising=False)
    monkeypatch.setattr(VolatilityBreakoutPullback, "_atr", staticmethod(lambda bars, n: 0.00020))

    sig = _strategy().evaluate(_bars())

    assert sig is None


def test_v2_uses_candidate_prior_range_and_finds_pullback_rebound(monkeypatch):
    monkeypatch.setenv("VBP_REDESIGN_V2", "1")
    monkeypatch.setattr(VolatilityBreakoutPullback, "_atr", staticmethod(lambda bars, n: 0.00020))

    sig = _strategy().evaluate(_bars())

    assert sig is not None
    assert sig.side == "BUY"
    assert sig.entry == pytest.approx(1.100805)
    assert sig.sl == pytest.approx(1.10020)
    assert sig.tp == pytest.approx(1.102805)
    assert "VBP_REDESIGN_V2" in sig.reason


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    vbp = Candidate("BUY", 70, 1.0, 2.0, [], "vbp", 4.0)
    engine = ScalperEngine()

    monkeypatch.setenv("VBP_REDESIGN_V2", "1")
    monkeypatch.delenv("VBP_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, vbp], other) == []

    monkeypatch.setenv("VBP_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, vbp], other) == [vbp]
