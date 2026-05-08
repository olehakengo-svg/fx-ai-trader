from modules.shadow_demote_registry import SHADOW_DEMOTED_CELLS, is_shadow_demoted


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
    assert not is_shadow_demoted("bb_rsi_reversion", "EUR_JPY")
    assert not is_shadow_demoted("sr_fib_confluence", "GBP_USD")
    assert is_shadow_demoted("sr_fib_confluence", "EUR_JPY")
    assert is_shadow_demoted("ema_trend_scalp", "usd_jpy")
