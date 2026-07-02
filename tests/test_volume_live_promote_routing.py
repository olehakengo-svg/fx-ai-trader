from __future__ import annotations

from modules.demo_trader import DemoTrader
from strategies.base import Candidate
from strategies.daytrade import DaytradeEngine
from tools import sync_kb_index
from tools import volume_live_promotion_watchdog as watchdog


# 2026-05-07 volume_emergency promote: 10 cells under shadow EV/PF
# exception. R2 volume_live_promotion_watchdog demotes any cell at
# Live N>=10 EV<0.
# REMOVED 2026-05-11 clean-live audit:
# - vix_carry_unwind × USD_JPY (Live N=11 EV=-2.15 Wilson_BF_lo=0.190)
#   R2 watchdog rule satisfied (Live N>=10, EV<0). → PAIR_DEMOTED.
#   See modules/demo_trader.py 2026-05-11 audit comment block.
# REMOVED 2026-05-18 C audit:
# - trend_rebound × USD_JPY (21d shadow N=60 WR=33.3% EV=-1.29p PF=0.66,
#   WF=0/3) → FORCE_DEMOTED (THESIS_INVALID).
# REMOVED 2026-05-29 (rule:R2 cell forensic):
# - xs_momentum × GBP_USD: Shadow N=81 (BUY EV=-2.25 / SELL EV=+0.21),
#   no Wilson_lo>0.30 cell; current cohort (post 2026-05-21) Shadow N=91
#   WR=14.3% EV=-5.15 → catastrophic regime degradation. Moved to
#   _PAIR_DEMOTED. EUR_USD pair likewise demoted (not in this list).
#   See knowledge-base/wiki/decisions/xs-momentum-pair-demote-2026-05-29.md.
# REMOVED 2026-07-02 (rule:R2 residual-path closure):
# - session_time_bias × EUR_USD: strategy REJECTED all pairs by 12y
#   MASSIVE BT (2026-06-11) + E2/E8 stage=0, yet PAIR_PROMOTED kept a
#   live path open. 30d clean live N=18 WR=33.3% -63.6pip (#1 strategy
#   drag). The 2026-05-29 London cell filter did not stop the bleed.
#   Shadow continues via _UNIVERSAL_SENTINEL. Re-promote: R1 only.
#   See tests/test_cell_forensic_2026_05_29_pin.py +
#   decisions/claude-codex-division-of-labor-2026-07-02.md session.
# REMOVED 2026-07-02 (rule:R2 live-bleeder demotion):
# - dt_sr_channel_reversal × EUR_JPY: 30d clean live N=10 WR=40% -30.9pip
#   (prod stats 2026-07-02). See decisions/live-bleeder-demotions-2026-07-02.md.
VOLUME_CELLS = [
    ("mqe_gbpusd_fix", "GBP_USD"),
    ("sr_fib_confluence", "GBP_USD"),
    ("vsg_jpy_reversal", "EUR_JPY"),
    ("bb_squeeze_breakout", "EUR_USD"),
    ("dt_bb_rsi_mr", "USD_JPY"),
]


class _OandaModeDefault:
    def get_strategy_mode(self, _entry_type):
        return ""


def _minimal_trader():
    trader = DemoTrader.__new__(DemoTrader)
    trader._oanda = _OandaModeDefault()
    trader._promoted_types = {}
    trader._runtime_pair_demoted = set()
    return trader


def test_volume_cells_are_pair_promoted_without_static_demote_conflicts():
    trader = _minimal_trader()

    for strategy, instrument in VOLUME_CELLS:
        assert (strategy, instrument) in DemoTrader._PAIR_PROMOTED
        assert (strategy, instrument) not in DemoTrader._PAIR_DEMOTED
        # Cell-conditional cells gate `_is_promoted` on the current UTC
        # session window (`_PAIR_SESSION_FILTER`). Asserting the bare
        # boolean here would be time-of-day dependent, so for those cells
        # we only verify the tier membership + the session-filter entry.
        if (strategy, instrument) in DemoTrader._PAIR_SESSION_FILTER:
            sessions = DemoTrader._PAIR_SESSION_FILTER[(strategy, instrument)]
            assert sessions, (
                f"{(strategy, instrument)} has an empty _PAIR_SESSION_FILTER "
                f"entry — should either be removed or list >=1 session."
            )
        else:
            assert trader._is_promoted(strategy, instrument) is True

    promoted_strategies = {strategy for strategy, _instrument in VOLUME_CELLS}
    assert promoted_strategies.isdisjoint(DemoTrader._FORCE_DEMOTED)


def test_mqe_and_vsg_do_not_double_emit_through_shadow_always():
    engine = DaytradeEngine()
    best = Candidate("BUY", 80, 1.0, 2.0, [], "other", 9.0)
    mqe = Candidate("SELL", 70, 1.0, 2.0, [], "mqe_gbpusd_fix", 4.0)
    vsg = Candidate("SELL", 70, 1.0, 2.0, [], "vsg_jpy_reversal", 4.0)

    assert engine.split_shadow_always([best, mqe, vsg], best) == []


def test_volume_watchdog_demotes_live_n10_negative_ev_and_ignores_shadow():
    trades = []
    for _ in range(10):
        trades.append({
            "entry_type": "vix_carry_unwind",
            "instrument": "USD_JPY",
            "is_shadow": 0,
            "status": "CLOSED",
            "pnl_pips": -1.0,
            "created_at": "2026-05-07T01:00:00Z",
        })
    trades.append({
        "entry_type": "vix_carry_unwind",
        "instrument": "USD_JPY",
        "is_shadow": 1,
        "status": "CLOSED",
        "pnl_pips": 999.0,
        "created_at": "2026-05-07T01:00:00Z",
    })

    results, demotions, exit_code = watchdog.run(trades)

    assert demotions == [("vix_carry_unwind", "USD_JPY")]
    assert results["vix_carry_unwind x USD_JPY"]["metrics"]["n"] == 10
    assert results["vix_carry_unwind x USD_JPY"]["metrics"]["ev_pips"] == -1.0
    assert exit_code == 1


def test_volume_watchdog_auto_demotion_source_edit_is_idempotent():
    source = '''
class DemoTrader:
    _PAIR_DEMOTED = {
        # historical note: ("vix_carry_unwind", "USD_JPY") was once demoted
    }
    _PAIR_PROMOTED = {
        ("vix_carry_unwind", "USD_JPY"),
        ("mqe_gbpusd_fix", "GBP_USD"),
    }
'''
    updated = watchdog.apply_auto_demotions_to_source(
        source, [("vix_carry_unwind", "USD_JPY")]
    )
    updated_again = watchdog.apply_auto_demotions_to_source(
        updated, [("vix_carry_unwind", "USD_JPY")]
    )

    assert '("vix_carry_unwind", "USD_JPY")' in updated
    assert '("mqe_gbpusd_fix", "GBP_USD")' in updated
    assert updated.count('("vix_carry_unwind", "USD_JPY"),') == 1
    assert updated_again == updated


def test_sync_kb_index_ignores_commented_tier_tuples():
    source = '''
class DemoTrader:
    _PAIR_PROMOTED = {
        # ("stale_strategy", "USD_JPY"),
        ("live_strategy", "EUR_USD"),
    }
'''

    assert sync_kb_index._parse_tuple_set(source, "_PAIR_PROMOTED") == {
        ("live_strategy", "EUR_USD")
    }
