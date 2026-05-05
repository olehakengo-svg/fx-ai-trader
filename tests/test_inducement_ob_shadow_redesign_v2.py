from __future__ import annotations

from types import SimpleNamespace

from strategies.base import Candidate
from strategies.daytrade import DaytradeEngine
from strategies.daytrade.inducement_ob import InducementOrderBlock


def test_v2_default_off_preserves_legacy_ob_boundary_stop(monkeypatch):
    monkeypatch.delenv("INDUCEMENT_OB_REDESIGN_V2", raising=False)
    strategy = InducementOrderBlock()
    ob = {"ob_low": 1.1000, "ob_high": 1.1020}
    liq_grab = {"sweep_extreme": 1.0975}

    sl = strategy._compute_stop_loss(
        SimpleNamespace(),
        "BUY",
        ob,
        liq_grab,
        atr=0.0010,
        pip_unit=0.0001,
    )

    assert round(sl, 5) == 1.09980


def test_v2_buy_stop_moves_outside_sweep_extreme_with_atr_buffer(monkeypatch):
    monkeypatch.setenv("INDUCEMENT_OB_REDESIGN_V2", "1")
    strategy = InducementOrderBlock()
    ob = {"ob_low": 1.1000, "ob_high": 1.1020}
    liq_grab = {"sweep_extreme": 1.0975}

    sl = strategy._compute_stop_loss(
        SimpleNamespace(),
        "BUY",
        ob,
        liq_grab,
        atr=0.0010,
        pip_unit=0.0001,
    )

    assert round(sl, 5) == 1.09720


def test_v2_sell_stop_moves_outside_sweep_extreme_with_atr_buffer(monkeypatch):
    monkeypatch.setenv("INDUCEMENT_OB_REDESIGN_V2", "1")
    strategy = InducementOrderBlock()
    ob = {"ob_low": 1.1000, "ob_high": 1.1020}
    liq_grab = {"sweep_extreme": 1.1045}

    sl = strategy._compute_stop_loss(
        SimpleNamespace(),
        "SELL",
        ob,
        liq_grab,
        atr=0.0010,
        pip_unit=0.0001,
    )

    assert round(sl, 5) == 1.10480


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate(signal="SELL", confidence=80, sl=2.0, tp=1.0, reasons=[], entry_type="other", score=9.0)
    inducement = Candidate(
        signal="BUY",
        confidence=70,
        sl=1.0,
        tp=2.0,
        reasons=[],
        entry_type="inducement_ob",
        score=4.0,
    )
    engine = DaytradeEngine()

    monkeypatch.setenv("INDUCEMENT_OB_REDESIGN_V2", "1")
    monkeypatch.delenv("INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, inducement], other) == []

    monkeypatch.setenv("INDUCEMENT_OB_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, inducement], other) == [inducement]
