from __future__ import annotations

import sys
from datetime import datetime, timezone

from modules.confidence_q4_gate import should_shadow as q4_should_shadow
from modules.prime_gate import classify_prime


def _sig(signal="BUY", confidence=65, atr_ratio=0.98, close_vs_ema200=0.01, adx=23.0):
    return {
        "signal": signal,
        "confidence": confidence,
        "regime": {
            "atr_ratio": atr_ratio,
            "close_vs_ema200": close_vs_ema200,
            "adx": adx,
        },
    }


def _dt(hour: int) -> datetime:
    return datetime(2026, 5, 18, hour, tzinfo=timezone.utc)


def _fake_prime(tier="A", lot_multiplier=0.3):
    return {
        "name": f"fake_prime_{tier}",
        "base": "fake_entry",
        "tier": tier,
        "lot_multiplier": lot_multiplier,
        "features": {},
    }


def _use_fake_prime(monkeypatch, tier="A", lot_multiplier=0.3):
    monkeypatch.setattr(
        sys.modules[__name__],
        "classify_prime",
        lambda entry_type, instrument, sig, entry_dt: _fake_prime(tier, lot_multiplier),
    )


def _replay_gate(entry_type, instrument, sig, entry_dt, *, base_promoted=False, env_enabled=True):
    prime = classify_prime(entry_type, instrument, sig, entry_dt)
    prime_live_lock = bool(prime and prime.get("tier") in ("A", "B"))
    if prime_live_lock and not env_enabled:
        prime_live_lock = False

    is_shadow = False
    is_promoted = base_promoted

    if entry_type == "vwap_mean_reversion" and not prime_live_lock:
        is_shadow = True
        is_promoted = False

    if entry_type == "bb_rsi_reversion" and not prime_live_lock:
        is_shadow = True
        is_promoted = False

    if not prime_live_lock and q4_should_shadow(entry_type, float(sig.get("confidence", 0) or 0)):
        is_shadow = True
        is_promoted = False

    if prime_live_lock:
        is_shadow = False
        is_promoted = True

    if not is_promoted and not is_shadow:
        is_shadow = True

    return {
        "prime": prime,
        "is_shadow": is_shadow,
        "is_promoted": is_promoted,
    }


def test_prime_a_bypasses_q4(monkeypatch):
    _use_fake_prime(monkeypatch, "A", 0.3)

    result = _replay_gate(
        "fib_reversal",
        "EUR_USD",
        _sig(confidence=65, close_vs_ema200=0.01),
        _dt(10),
    )

    assert result["prime"]["tier"] == "A"
    assert result["is_promoted"] is True
    assert result["is_shadow"] is False


def test_prime_b_bypasses_bb_rsi_trip(monkeypatch):
    _use_fake_prime(monkeypatch, "B", 0.1)

    result = _replay_gate(
        "bb_rsi_reversion",
        "USD_JPY",
        _sig(confidence=62, atr_ratio=0.98),
        _dt(13),
    )

    assert result["prime"]["tier"] == "B"
    assert result["is_promoted"] is True
    assert result["is_shadow"] is False


def test_prime_b_bypasses_q4(monkeypatch):
    _use_fake_prime(monkeypatch, "B", 0.1)

    result = _replay_gate(
        "bb_rsi_reversion",
        "USD_JPY",
        _sig(confidence=80, atr_ratio=0.98),
        _dt(14),
    )

    assert result["prime"]["tier"] == "B"
    assert result["is_promoted"] is True
    assert result["is_shadow"] is False


def test_prime_c_stays_shadow():
    result = _replay_gate(
        "engulfing_bb",
        "USD_JPY",
        _sig(confidence=72),
        _dt(1),
    )

    assert result["prime"]["name"] == "engulfing_bb_TOKYO_EARLY"
    assert result["prime"]["tier"] == "C"
    assert result["is_promoted"] is False
    assert result["is_shadow"] is True


def test_non_prime_q4_still_blocked():
    result = _replay_gate(
        "ema_trend_scalp",
        "USD_JPY",
        _sig(confidence=80),
        _dt(9),
        base_promoted=True,
    )

    assert result["prime"] is None
    assert result["is_promoted"] is False
    assert result["is_shadow"] is True


def test_non_prime_bb_rsi_still_tripped():
    result = _replay_gate(
        "bb_rsi_reversion",
        "USD_JPY",
        _sig(confidence=62, atr_ratio=0.98),
        _dt(9),
        base_promoted=True,
    )

    assert result["prime"] is None
    assert result["is_promoted"] is False
    assert result["is_shadow"] is True


def test_prime_override_disabled_env(monkeypatch):
    _use_fake_prime(monkeypatch, "B", 0.1)

    result = _replay_gate(
        "bb_rsi_reversion",
        "USD_JPY",
        _sig(confidence=80, atr_ratio=0.98),
        _dt(13),
        env_enabled=False,
    )

    assert result["prime"]["tier"] == "B"
    assert result["is_promoted"] is False
    assert result["is_shadow"] is True
