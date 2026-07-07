from modules.shadow_demote_registry import (
    SHADOW_DEMOTED_CELLS,
    SHADOW_RETIRED_STRATEGIES,
    is_shadow_demoted,
)


def test_r2_critical_cells_are_demoted():
    expected = {
        ("bb_rsi_reversion", "EUR_USD"),
        ("bb_rsi_reversion", "GBP_USD"),
        ("bb_rsi_reversion", "USD_JPY"),
        ("ema_trend_scalp", "EUR_USD"),
        ("ema_trend_scalp", "GBP_USD"),
        ("ema_trend_scalp", "USD_JPY"),
        ("engulfing_bb", "USD_JPY"),
        ("sr_channel_reversal", "EUR_USD"),
        ("sr_channel_reversal", "USD_JPY"),
        ("sr_fib_confluence", "EUR_JPY"),
        ("sr_fib_confluence", "GBP_JPY"),
        ("sr_fib_confluence", "USD_JPY"),
        ("engulfing_bb", "USD_CHF"),
        ("london_breakout", "USD_CHF"),
        ("three_bar_reversal", "USD_CHF"),
        ("vol_surge_detector", "USD_CHF"),
    }

    assert expected == SHADOW_DEMOTED_CELLS


def test_usdchf_hourly_bleeder_cells_demoted():
    # 2026-07-02 (rule:R2): daytrade_1h_usdchf mode audit — the four
    # still-emitting bleeder cells on the USD_CHF hourly surface
    # (remainder after the 2026-06-12 strategy retirements).
    assert is_shadow_demoted("london_breakout", "USD_CHF")
    assert is_shadow_demoted("vol_surge_detector", "USD_CHF")
    assert is_shadow_demoted("three_bar_reversal", "USD_CHF")
    assert is_shadow_demoted("engulfing_bb", "USD_CHF")
    # Per-cell stop, not a strategy retirement: the same strategies stay
    # alive on their other pairs (vol_surge_detector is SCALP_SENTINEL
    # live on USD_JPY).
    assert not is_shadow_demoted("london_breakout", "GBP_USD")
    assert not is_shadow_demoted("vol_surge_detector", "USD_JPY")
    assert not is_shadow_demoted("three_bar_reversal", "EUR_USD")


def test_shadow_demote_registry_pair_specific_examples():
    assert is_shadow_demoted("bb_rsi_reversion", "EUR_USD")
    # 2026-06-12 audit #2: bb_rsi_reversion is strategy-level retired, so
    # pairs outside the per-cell list are blocked too.
    assert is_shadow_demoted("bb_rsi_reversion", "EUR_JPY")
    # 2026-06-12 audit #5: sr_fib_confluence is now strategy-level retired,
    # so GBP_USD (not in the per-cell JPY list) is blocked too.
    assert is_shadow_demoted("sr_fib_confluence", "GBP_USD")
    assert is_shadow_demoted("sr_fib_confluence", "EUR_JPY")
    assert is_shadow_demoted("ema_trend_scalp", "usd_jpy")


def test_retired_strategies_block_all_instruments():
    # 2026-06-12 edge-factor audits #1-#5: permanent retirements.
    assert SHADOW_RETIRED_STRATEGIES == frozenset({
        "ema_trend_scalp",
        "bb_rsi_reversion",
        "fib_reversal",
        "sr_channel_reversal",
        "sr_fib_confluence",
    })
    # #5 sr_fib_confluence: per-cell registry only listed the 3 JPY crosses;
    # majors (EUR_USD/GBP_USD/EUR_GBP) kept firing. Strategy-level closes it.
    assert is_shadow_demoted("sr_fib_confluence", "EUR_GBP")
    # #3 fib_reversal: was the biggest active shadow bleeder (30d N=251).
    assert is_shadow_demoted("fib_reversal", "EUR_USD")
    assert is_shadow_demoted("fib_reversal", "USD_CHF")
    # #4 sr_channel_reversal: per-cell registry only listed EUR_USD/USD_JPY,
    # so GBP_USD/USD_CHF kept leaking (30d N=159). Strategy-level closes it.
    assert is_shadow_demoted("sr_channel_reversal", "GBP_USD")
    assert is_shadow_demoted("sr_channel_reversal", "USD_CHF")
    # The anti-hunt redesign survivor is a different thesis — stays alive.
    assert not is_shadow_demoted("sr_anti_hunt_bounce", "EUR_JPY")
    assert not is_shadow_demoted("dt_sr_channel_reversal", "GBP_USD")
    # USD_CHF was the live leak via daytrade_1h_usdchf (55 trades in 30d,
    # WR 3.6%, PF 0.03) — not covered by the per-cell entries.
    assert is_shadow_demoted("ema_trend_scalp", "USD_CHF")
    # Future/unknown pairs are blocked too.
    assert is_shadow_demoted("ema_trend_scalp", "AUD_NZD")
    assert is_shadow_demoted("ema_trend_scalp", "")
    # bb_rsi_reversion #2: USD_CHF leaked 22 shadow trades via the same
    # hourly slot before the 2026-06-08 whitelist; whitelist itself is
    # env-bypassable, the registry entry is not.
    assert is_shadow_demoted("bb_rsi_reversion", "USD_CHF")
    assert is_shadow_demoted("bb_rsi_reversion", "USD_JPY")
    # The DT-geometry family representative stays alive.
    assert not is_shadow_demoted("dt_bb_rsi_mr", "USD_CHF")
    assert not is_shadow_demoted("dt_bb_rsi_mr", "USD_JPY")
