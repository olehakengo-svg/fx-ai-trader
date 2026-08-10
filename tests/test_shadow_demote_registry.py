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
        # 2026-08-05 (rule:R2): persistent-CRITICAL batch, see
        # wiki/decisions/r2-shadow-demote-2026-08-05.md
        ("dt_sr_channel_reversal", "AUD_JPY"),
        ("engulfing_bb", "EUR_USD"),
        ("london_breakout", "GBP_USD"),
        ("ma_regime_switch", "USD_JPY"),
        ("sr_break_retest", "EUR_JPY"),
        ("sr_break_retest", "GBP_JPY"),
        ("sr_break_retest", "GBP_USD"),
        ("vol_momentum_scalp", "GBP_USD"),
        ("vol_momentum_scalp", "USD_JPY"),
        ("xs_momentum", "EUR_USD"),
        # 2026-08-10 (rule:R2): batch 2, see
        # wiki/decisions/r2-shadow-demote-2026-08-10.md
        ("engulfing_bb", "GBP_USD"),
        ("xs_momentum", "GBP_USD"),
        ("xs_momentum", "USD_JPY"),
    }

    assert expected == SHADOW_DEMOTED_CELLS


def test_r2_batch_2026_08_10_deferred_cells_resolved_to_demote():
    # The 08-05 batch deferred xs_momentum GBP_USD/USD_JPY under the
    # 24h-persistence rule (sign flipped within 5h, PF 0.89/0.98). The frozen
    # next-cycle rule resolved to DEMOTE: CRITICAL in all 17 alerts from
    # 08-06 02:23 through 08-10 01:38 UTC, EV never returning positive.
    assert is_shadow_demoted("xs_momentum", "GBP_USD")
    assert is_shadow_demoted("xs_momentum", "USD_JPY")
    # N-crossing type, same batch: WARN with EV <= -0.79 across 08-03..08-05,
    # CRITICAL from 08-05 14:03 onward.
    assert is_shadow_demoted("engulfing_bb", "GBP_USD")
    # Cell-level stop must not leak to the strategies' healthy pairs. The
    # engulfing_bb example moved into the demoted set in this batch, so the
    # leak-check uses cells that are still accumulating (WARN/OK in the
    # 08-10 alert): dt_sr_channel_reversal x USD_JPY, three_bar_reversal x
    # USD_JPY.
    assert not is_shadow_demoted("vol_momentum_scalp", "EUR_USD")
    assert not is_shadow_demoted("sr_break_retest", "AUD_JPY")
    assert not is_shadow_demoted("dt_sr_channel_reversal", "USD_JPY")
    assert not is_shadow_demoted("three_bar_reversal", "USD_JPY")


def test_engulfing_bb_and_xs_momentum_stay_cell_level_not_retired():
    # Both strategies now have every currently-emitting cell demoted, but
    # they are deliberately NOT added to SHADOW_RETIRED_STRATEGIES: that set
    # is reserved for edge-factor-audit retirements (N>=450 with a mechanism
    # verdict), whereas this batch is the alert-gate machine rule. The
    # consequence is a known leak surface — a future mode adding a new pair
    # would resume emission — tracked in the 08-10 decision doc.
    assert "engulfing_bb" not in SHADOW_RETIRED_STRATEGIES
    assert "xs_momentum" not in SHADOW_RETIRED_STRATEGIES
    assert not is_shadow_demoted("engulfing_bb", "AUD_JPY")
    assert not is_shadow_demoted("xs_momentum", "AUD_JPY")


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
    # live on USD_JPY). london_breakout x GBP_USD moved to the demoted set
    # in the 2026-08-05 batch, so the leak-check example is EUR_USD now.
    assert not is_shadow_demoted("london_breakout", "EUR_USD")
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
