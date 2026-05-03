from pathlib import Path

from tools.tier_integrity_check import parse_all


DEMOTE_LOCK_14 = {
    ("vwap_mean_reversion", "GBP_USD"),
    ("vix_carry_unwind", "USD_JPY"),
    ("sr_channel_reversal", "USD_JPY"),
    ("bb_rsi_reversion", "USD_JPY"),
    ("session_time_bias", "GBP_USD"),
    ("bb_squeeze_breakout", "USD_JPY"),
    ("bb_rsi_reversion", "EUR_USD"),
    ("vol_surge_detector", "USD_JPY"),
    ("engulfing_bb", "USD_JPY"),
    ("engulfing_bb", "EUR_USD"),
    ("v_reversal", "USD_JPY"),
    ("trend_rebound", "USD_JPY"),
    ("sr_channel_reversal", "EUR_USD"),
    ("stoch_trend_pullback", "USD_JPY"),
}

PROMOTED_CONFLICTS = {
    ("vix_carry_unwind", "USD_JPY"),
    ("bb_squeeze_breakout", "USD_JPY"),
}


def _tier_sets():
    source = Path("modules/demo_trader.py").read_text()
    return parse_all(source)


def test_r2_demote_lock_14_cells_are_pair_demoted():
    sets = _tier_sets()

    assert DEMOTE_LOCK_14 <= sets["pair_demoted"]


def test_r2_conflict_cells_are_removed_from_pair_promoted():
    sets = _tier_sets()

    assert PROMOTED_CONFLICTS.isdisjoint(sets["pair_promoted"])


def test_r2_demoted_cells_have_no_pair_level_live_overrides():
    sets = _tier_sets()

    assert DEMOTE_LOCK_14.isdisjoint(sets["pair_lot_boost"])
    assert DEMOTE_LOCK_14.isdisjoint(sets["quick_harvest_exempt"])
