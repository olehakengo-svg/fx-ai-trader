from __future__ import annotations

from modules.demo_trader import DemoTrader
from strategies.base import Candidate
from strategies.daytrade import DaytradeEngine
from tools import sync_kb_index
from tools import volume_live_promotion_watchdog as watchdog


VOLUME_CELLS = [
    ("vix_carry_unwind", "USD_JPY"),
    ("mqe_gbpusd_fix", "GBP_USD"),
    ("sr_fib_confluence", "GBP_USD"),
    ("xs_momentum", "GBP_USD"),
    ("session_time_bias", "EUR_USD"),
    ("vsg_jpy_reversal", "EUR_JPY"),
    ("trend_rebound", "USD_JPY"),
    ("bb_squeeze_breakout", "EUR_USD"),
    ("dt_sr_channel_reversal", "EUR_JPY"),
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
