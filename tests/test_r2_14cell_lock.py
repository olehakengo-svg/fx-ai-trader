from pathlib import Path

from tools.tier_integrity_check import parse_all


# R2 demote-lock cells. Started as a 14-cell lock at the original R2 audit;
# cells have been intentionally revived under specific programmes:
#  - 2026-05-07 volume emergency: vix_carry_unwind×USD_JPY (shadow N=58 EV=+9.54
#    PF=1.65), trend_rebound×USD_JPY (shadow N=17 EV=+1.14 PF=1.52)
#  - 2026-06-01 (commit 088b3ccf, rule:R2): session_time_bias×GBP_USD London
#    cell-conditional revival (Shadow N=45 Wlo=0.251 EV=+0.98 PF=1.19, symmetric
#    to EUR_USD London revival)
# All revivals have a live N>=10 EV<0 auto-demote guard so the lock can re-
# engage if the shadow evidence inverts in production. The fixture below
# tracks the *current* locked set; growing it requires the R2 audit gate
# documented in wiki/decisions/.
DEMOTE_LOCK_12 = {
    ("vwap_mean_reversion", "GBP_USD"),
    ("sr_channel_reversal", "USD_JPY"),
    ("bb_rsi_reversion", "USD_JPY"),
    ("bb_squeeze_breakout", "USD_JPY"),
    ("bb_rsi_reversion", "EUR_USD"),
    ("vol_surge_detector", "USD_JPY"),
    ("engulfing_bb", "USD_JPY"),
    ("engulfing_bb", "EUR_USD"),
    ("v_reversal", "USD_JPY"),
    ("sr_channel_reversal", "EUR_USD"),
    ("stoch_trend_pullback", "USD_JPY"),
}

# Cells that must never appear in pair_promoted because they remain demote-
# locked. bb_squeeze_breakout×USD_JPY is the canonical case here. The earlier
# fixture also listed vix_carry_unwind×USD_JPY but that pairing is now an
# intentional volume-emergency promote (see DEMOTE_LOCK_12 docstring).
PROMOTED_CONFLICTS = {
    ("bb_squeeze_breakout", "USD_JPY"),
}

# Backwards-compat alias kept so external tooling/import paths that already
# referenced the old name don't break silently.
DEMOTE_LOCK_14 = DEMOTE_LOCK_12


def _tier_sets():
    source = Path("modules/demo_trader.py").read_text()
    return parse_all(source)


def test_r2_demote_lock_14_cells_are_pair_demoted():
    sets = _tier_sets()

    assert DEMOTE_LOCK_12 <= sets["pair_demoted"]


def test_r2_conflict_cells_are_removed_from_pair_promoted():
    sets = _tier_sets()

    assert PROMOTED_CONFLICTS.isdisjoint(sets["pair_promoted"])


def test_r2_demoted_cells_have_no_pair_level_live_overrides():
    sets = _tier_sets()

    assert DEMOTE_LOCK_12.isdisjoint(sets["pair_lot_boost"])
    assert DEMOTE_LOCK_12.isdisjoint(sets["quick_harvest_exempt"])
