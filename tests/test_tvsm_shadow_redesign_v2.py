from __future__ import annotations

from datetime import datetime, timezone

import pytest

from strategies.base import Candidate
from strategies.micro_scalp.base import CostModel, TickBar
from strategies.micro_scalp.tvsm import TickVolumeSpikeMomentum
from strategies.scalp import ScalperEngine


def _ts(hour: int, i: int) -> float:
    base = datetime(2026, 5, 5, hour, 0, 0, tzinfo=timezone.utc).timestamp()
    return base + i


def _bars(*, hour: int = 8, spread_price: float | None = None) -> list[TickBar]:
    bars = []
    price = 1.10000
    for i in range(305):
        open_ = price
        close = price + 0.00001
        high = max(open_, close) + 0.00010
        low = min(open_, close) - 0.00010
        volume = 100 + (i % 5)

        if i == 302:
            open_ = price
            close = price + 0.00008
            high = close + 0.00010
            low = open_ - 0.00010
            volume = 500
        elif i == 303:
            open_ = price + 0.00008
            close = open_ + 0.00004
            high = close + 0.00010
            low = open_ - 0.00010
        elif i == 304:
            open_ = price + 0.00012
            close = open_ + 0.00004
            high = close + 0.00010
            low = open_ - 0.00010

        bid = ask = None
        if spread_price is not None:
            bid = close - spread_price / 2.0
            ask = close + spread_price / 2.0

        bars.append(
            TickBar(
                ts=_ts(hour, i),
                open=open_,
                high=high,
                low=low,
                close=close,
                tick_volume=volume,
                bid=bid,
                ask=ask,
            )
        )
        price = close
    return bars


def _strategy(symbol: str = "EUR_USD", spread_pips: float = 0.1) -> TickVolumeSpikeMomentum:
    cost = CostModel(
        spread_pips=spread_pips,
        latency_ms=0,
        slippage_per_ms=0,
        symbol=symbol,
    )
    return TickVolumeSpikeMomentum(cost, spike_z=3.0, tp_atr_mult=3.0)


def test_v2_default_off_preserves_legacy_all_pair_signal(monkeypatch):
    monkeypatch.delenv("TVSM_REDESIGN_V2", raising=False)

    sig = _strategy(symbol="AUD_NZD").evaluate(_bars(hour=2))

    assert sig is not None
    assert sig.side == "BUY"
    assert "TVSM_REDESIGN_V2" not in sig.reason


def test_v2_rejects_non_major_pair_before_trigger(monkeypatch):
    monkeypatch.setenv("TVSM_REDESIGN_V2", "1")

    sig = _strategy(symbol="AUD_NZD").evaluate(_bars(hour=8))

    assert sig is None


def test_v2_rejects_outside_london_ny_density_window(monkeypatch):
    monkeypatch.setenv("TVSM_REDESIGN_V2", "1")

    sig = _strategy(symbol="EUR_USD").evaluate(_bars(hour=2))

    assert sig is None


def test_v2_rejects_low_atr_cost_regime(monkeypatch):
    monkeypatch.setenv("TVSM_REDESIGN_V2", "1")

    sig = _strategy(symbol="EUR_USD", spread_pips=30.0).evaluate(
        _bars(hour=8, spread_price=0.0030)
    )

    assert sig is None


def test_v2_accepts_major_pair_session_and_viable_atr(monkeypatch):
    monkeypatch.setenv("TVSM_REDESIGN_V2", "1")

    sig = _strategy(symbol="EUR_USD").evaluate(_bars(hour=8))

    assert sig is not None
    assert sig.side == "BUY"
    assert "TVSM_REDESIGN_V2" in sig.reason


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    tvsm = Candidate("BUY", 70, 1.0, 2.0, [], "tvsm", 4.0)
    engine = ScalperEngine()

    monkeypatch.setenv("TVSM_REDESIGN_V2", "1")
    monkeypatch.delenv("TVSM_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, tvsm], other) == []

    monkeypatch.setenv("TVSM_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, tvsm], other) == [tvsm]
