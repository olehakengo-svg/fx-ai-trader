from __future__ import annotations

import pytest

from strategies.base import Candidate
from strategies.micro_scalp.base import CostModel, TickBar
from strategies.micro_scalp.ofi_mr import OrderFlowImbalanceMR
from strategies.scalp import ScalperEngine


def _bars(*, last_close: float = 1.10050, signal_close: float = 1.10100) -> list[TickBar]:
    bars = []
    for i in range(1820):
        close = 1.10000
        if i == 1818:
            close = signal_close
        elif i == 1819:
            close = last_close
        bars.append(
            TickBar(
                ts=float(i),
                open=close,
                high=close + 0.00005,
                low=close - 0.00005,
                close=close,
                tick_volume=100,
            )
        )
    return bars


def _strategy(monkeypatch) -> OrderFlowImbalanceMR:
    cost = CostModel(spread_pips=0.1, latency_ms=0, slippage_per_ms=0, symbol="EUR_USD")
    strat = OrderFlowImbalanceMR(cost, window_sec=3, z_thresh=2.0)

    monkeypatch.setattr(OrderFlowImbalanceMR, "_compute_ofi", staticmethod(lambda bars: 100.0))
    monkeypatch.setattr(OrderFlowImbalanceMR, "_mean_std", staticmethod(lambda values: (0.0, 10.0)))
    monkeypatch.setattr(OrderFlowImbalanceMR, "_atr", staticmethod(lambda bars, n: 0.00020))
    return strat


def test_v2_default_off_preserves_legacy_min_tp_extension(monkeypatch):
    monkeypatch.delenv("OFI_MR_REDESIGN_V2", raising=False)
    monkeypatch.setattr(OrderFlowImbalanceMR, "_vwap", staticmethod(lambda bars: 1.10000))
    strat = _strategy(monkeypatch)

    sig = strat.evaluate(_bars(last_close=1.10050, signal_close=1.10100))

    assert sig is not None
    assert sig.side == "SELL"
    assert sig.tp < 1.10000
    assert sig.tp_pips == pytest.approx(8.0)
    assert "OFI_MR_REDESIGN_V2" not in sig.reason


def test_v2_rejects_when_min_tp_would_cross_vwap(monkeypatch):
    monkeypatch.setenv("OFI_MR_REDESIGN_V2", "1")
    monkeypatch.setattr(OrderFlowImbalanceMR, "_vwap", staticmethod(lambda bars: 1.10000))
    strat = _strategy(monkeypatch)

    sig = strat.evaluate(_bars(last_close=1.10050, signal_close=1.10100))

    assert sig is None


def test_v2_uses_closed_feature_window_and_next_bar_entry(monkeypatch):
    monkeypatch.setenv("OFI_MR_REDESIGN_V2", "1")
    seen_vwap_windows = []

    def _vwap(bars):
        seen_vwap_windows.append([b.ts for b in bars])
        return 1.10000

    monkeypatch.setattr(OrderFlowImbalanceMR, "_vwap", staticmethod(_vwap))
    strat = _strategy(monkeypatch)

    sig = strat.evaluate(_bars(last_close=1.10200, signal_close=1.10100))

    assert sig is not None
    assert seen_vwap_windows[-1] == [1816.0, 1817.0, 1818.0]
    assert sig.entry == pytest.approx(strat.cost.apply_to_entry("SELL", 1.10200))
    assert sig.tp == pytest.approx(1.10000)
    assert sig.tp_pips == pytest.approx((sig.entry - 1.10000) / strat.pip)
    assert "OFI_MR_REDESIGN_V2" in sig.reason


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("BUY", 80, 1.0, 2.0, [], "other", 9.0)
    ofi = Candidate("SELL", 70, 2.0, 1.0, [], "ofi_mr", 4.0)
    engine = ScalperEngine()

    monkeypatch.setenv("OFI_MR_REDESIGN_V2", "1")
    monkeypatch.delenv("OFI_MR_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, ofi], other) == []

    monkeypatch.setenv("OFI_MR_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, ofi], other) == [ofi]
