# -*- coding: utf-8 -*-
"""Pin: price_shock_rev ×5 carve-out pool R2 demote (2026-10-10).

registry `ps-carveout-regate-post-172` (live_count_decision, prefix
price_shock_rev, since 2026-08-11, n_decide 10) の pre-registered 条件
「clean live N>=10 ∧ EV<-0.5p → R2 demote」が 2026-10-10 に成立
(N=11, EV=-6.08p, WR=36.4%, Wilson_lo=0.152)。親決裁 Track C D-c-1
(2026-07-28) の carve-out を _PAIR_DEMOTED へ移し、agg-Kelly min-lot bypass
からも除去する。shadow 蓄積は継続 (4原則 #3)、再 live 化は R1 (user 決裁)。
決裁記録: knowledge-base/wiki/decisions/ps-carveout-pool-r2-demote-2026-10-10.md
"""
from __future__ import annotations

import pytest

from modules.demo_trader import (
    DemoTrader,
    PRICE_SHOCK_REV_MIN_UNITS,
    PRICE_SHOCK_REV_TIER1_PAIRS,
    PRICE_SHOCK_REV_TIER1_TYPES,
)

PS_CELLS = (
    ("price_shock_rev_eur_gbp_h1_long", "EUR_GBP"),
    ("price_shock_rev_eur_aud_h1_long", "EUR_AUD"),
    ("price_shock_rev_usd_cad_h1_long", "USD_CAD"),
    ("price_shock_rev_nzd_jpy_h1_long", "NZD_JPY"),
    ("price_shock_rev_aud_jpy_h1_long", "AUD_JPY"),
)


@pytest.mark.parametrize("cell", PS_CELLS)
def test_ps_cell_is_pair_demoted_not_promoted(cell):
    assert cell in DemoTrader._PAIR_DEMOTED
    assert cell not in DemoTrader._PAIR_PROMOTED


@pytest.mark.parametrize("cell", PS_CELLS)
def test_ps_cell_runtime_predicate_reports_demoted(cell):
    trader = DemoTrader.__new__(DemoTrader)
    entry_type, instrument = cell
    assert trader._is_pair_demoted_entry(entry_type, instrument) is True


@pytest.mark.parametrize("cell", PS_CELLS)
def test_ps_cell_removed_from_minlot_bypass(cell):
    entry_type, _ = cell
    assert entry_type not in DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES


def test_family_identity_and_min_lot_contract_unchanged():
    # family の識別子 (shadow 蓄積 / watchdog WATCHED_CELLS / seat priority) と
    # MIN lot 契約 literal は不変 — 降格は live 送信の可否だけを変える。
    assert PRICE_SHOCK_REV_TIER1_PAIRS == set(PS_CELLS)
    assert PRICE_SHOCK_REV_TIER1_TYPES == {c[0] for c in PS_CELLS}
    assert PRICE_SHOCK_REV_MIN_UNITS == 1000
    assert PRICE_SHOCK_REV_TIER1_TYPES.isdisjoint(DemoTrader._FORCE_DEMOTED)


def test_other_pair_demoted_entries_untouched():
    assert ("bb_rsi_reversion", "EUR_USD") in DemoTrader._PAIR_DEMOTED
    assert ("ema_cross", "USD_JPY") in DemoTrader._PAIR_DEMOTED
