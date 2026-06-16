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
    }

    assert expected == SHADOW_DEMOTED_CELLS


def test_shadow_demote_registry_pair_specific_examples():
    assert is_shadow_demoted("bb_rsi_reversion", "EUR_USD")
    # 2026-06-12 audit #2: bb_rsi_reversion is strategy-level retired, so
    # pairs outside the per-cell list are blocked too.
    assert is_shadow_demoted("bb_rsi_reversion", "EUR_JPY")
    assert not is_shadow_demoted("sr_fib_confluence", "GBP_USD")
    assert is_shadow_demoted("sr_fib_confluence", "EUR_JPY")
    assert is_shadow_demoted("ema_trend_scalp", "usd_jpy")


def test_retired_strategies_block_all_instruments():
    # 2026-06-12 edge-factor audits #1-#4: permanent retirements.
    assert SHADOW_RETIRED_STRATEGIES == frozenset({
        "ema_trend_scalp",
        "bb_rsi_reversion",
        "fib_reversal",
        "sr_channel_reversal",
    })
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
