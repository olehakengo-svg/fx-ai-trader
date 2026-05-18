from __future__ import annotations

from datetime import datetime, timezone

from modules.prime_gate import EDGES, _PRIMES, classify_prime


def test_all_primes_are_tier_c():
    assert all(p[2] == "C" for p in _PRIMES)


def test_all_lot_multipliers_zero():
    assert all(p[3] == 0.0 for p in _PRIMES)


def test_classify_prime_returns_tier_c_when_predicate_matches():
    sig = {
        "signal": "BUY",
        "confidence": 60.0,
        "regime": {
            "atr_ratio": 0.90,
            "close_vs_ema200": 0.0,
            "adx": 20.0,
        },
    }

    result = classify_prime(
        "stoch_trend_pullback",
        "USD_JPY",
        sig,
        datetime(2026, 5, 18, 10, tzinfo=timezone.utc),
    )

    assert result["name"] == "stoch_trend_pullback_PRIME"
    assert result["tier"] == "C"
    assert result["lot_multiplier"] == 0.0


def test_edges_match_p1_recomputation():
    assert EDGES == {
        "confidence": [54.0, 64.0, 71.0],
        "rj_adx": [18.525844, 24.084449, 31.282508],
        "rj_atr_ratio": [0.926959, 0.983332, 1.091413],
        "rj_close_vs_ema200": [-0.281692, -0.00188, 0.009222],
    }
