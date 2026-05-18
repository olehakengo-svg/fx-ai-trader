from __future__ import annotations

from datetime import datetime, timezone

from modules.prime_gate import classify_prime


def _dt(hour: int) -> datetime:
    return datetime(2026, 5, 18, hour, tzinfo=timezone.utc)


def _sig(signal="BUY", confidence=65.0, atr_ratio=0.98, close_vs_ema200=0.0, adx=23.0):
    return {
        "signal": signal,
        "confidence": confidence,
        "regime": {
            "atr_ratio": atr_ratio,
            "close_vs_ema200": close_vs_ema200,
            "adx": adx,
        },
    }


def test_fib_reversal_prime_match_returns_tier_b_005x():
    result = classify_prime(
        "fib_reversal",
        "EUR_USD",
        _sig(confidence=65.0, close_vs_ema200=0.0),
        _dt(10),
    )

    assert result["name"] == "fib_reversal_PRIME"
    assert result["tier"] == "B"
    assert result["lot_multiplier"] == 0.05


def test_sr_fib_confluence_match_returns_tier_b_005x():
    result = classify_prime(
        "sr_fib_confluence",
        "GBP_USD",
        _sig(adx=20.0),
        _dt(10),
    )

    assert result["name"] == "sr_fib_confluence_GBP_ADXQ2"
    assert result["tier"] == "B"
    assert result["lot_multiplier"] == 0.05


def test_stoch_trend_pullback_prime_still_tier_c():
    result = classify_prime(
        "stoch_trend_pullback",
        "USD_JPY",
        _sig(signal="BUY", atr_ratio=0.90),
        _dt(10),
    )

    assert result["name"] == "stoch_trend_pullback_PRIME"
    assert result["tier"] == "C"
    assert result["lot_multiplier"] == 0.0


def test_bb_rsi_reversion_ny_atrq2_still_tier_c():
    result = classify_prime(
        "bb_rsi_reversion",
        "USD_JPY",
        _sig(atr_ratio=0.98),
        _dt(13),
    )

    assert result["name"] == "bb_rsi_reversion_NY_ATRQ2"
    assert result["tier"] == "C"
    assert result["lot_multiplier"] == 0.0
