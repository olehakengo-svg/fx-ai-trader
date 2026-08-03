"""Regression pin for the 2026-08-03 vix Overlap pilot early demote (rule:R2).

Locks in the demotion of `vix_carry_unwind` × USD_JPY:

- 2026-07-07 pilot-continuation ruling's load-bearing evidence (positive
  shadow EV) collapsed: shadow monthly 04:+537p → 05..07 cumulative −216p.
- Live record post-cutoff: N=26 PnL=−46.9p PF=0.66 (3/4 negative months).
- User approval 2026-08-03 (「進めて」), executed ahead of the
  `vix-sell-pilot-recheck` checkpoint (live SELL N≥20 or 2026-08-31).

Shadow emission continues (原則3). Re-promotion is R1 only (recent-90d
shadow N≥30 EV>0 + Wilson_lo>34.4% + Bonferroni + 365d cell BT + pre-reg).

References:
- knowledge-base/wiki/decisions/vix-pilot-early-demote-2026-08-03.md
- knowledge-base/raw/trade-logs/quant-eval-2026-07-31.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import modules.demo_trader as demo_trader_mod
from modules.demo_trader import DemoTrader
from edge_cell_test_helpers import fixed_datetime

VIX = "vix_carry_unwind"
INST = "USD_JPY"
CELL = (VIX, INST)


def test_vix_not_in_pair_promoted():
    assert CELL not in DemoTrader._PAIR_PROMOTED, (
        "vix_carry_unwind×USD_JPY must stay out of _PAIR_PROMOTED — the "
        "Overlap pilot was demoted 2026-08-03 (rule:R2, user 決裁) after the "
        "07-07 continuation basis (positive shadow EV) collapsed. "
        "Re-promotion is R1 only. See "
        "decisions/vix-pilot-early-demote-2026-08-03.md."
    )


def test_vix_in_pair_demoted():
    assert CELL in DemoTrader._PAIR_DEMOTED, (
        "vix_carry_unwind×USD_JPY must remain PAIR_DEMOTED — live N=26 "
        "−46.9p PF=0.66 + shadow edge decay (05-07 cumulative −216p). See "
        "decisions/vix-pilot-early-demote-2026-08-03.md."
    )


def test_vix_session_filter_and_lot_boost_removed():
    assert CELL not in DemoTrader._PAIR_SESSION_FILTER, (
        "Overlap session filter must stay removed with the pilot (inert "
        "without PAIR_PROMOTED, removed for code consistency)."
    )
    assert CELL not in DemoTrader._PAIR_LOT_BOOST, (
        "1.0x pair lot boost must stay removed with the pilot."
    )


def test_vix_minlot_contract_retained_for_future_r1():
    # Intentionally retained: if an R1 re-promotion ever lands, the 1000u
    # fixed-lot contract must still bind (eligible vs effective lesson).
    assert VIX in DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES


class _OandaModeStub:
    def get_strategy_mode(self, _entry_type):
        return "auto"


def test_vix_not_promoted_even_inside_former_overlap_window(monkeypatch):
    # hour=14 UTC was inside the former Overlap pilot window (12-16).
    monkeypatch.setattr(demo_trader_mod, "datetime", fixed_datetime(14))
    trader = DemoTrader.__new__(DemoTrader)
    trader._oanda = _OandaModeStub()
    trader._promoted_types = {}
    trader._runtime_pair_demoted = set()
    allowed, cause = trader._is_promoted_ex(VIX, INST)
    assert allowed is False
    assert cause == "pair_demoted", (
        "demote must be attributed to pair_demoted (not session_filter) — "
        "the pilot window no longer exists."
    )
