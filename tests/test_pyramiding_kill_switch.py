"""DISABLE_PYRAMIDING env-var kill-switch (audit 2026-05-01 P0-8 / P1).

The pyramiding emit path was burning EV at -1.56pip/event for 3 weeks
before the prior commit removed it from the eligible list. The audit
asks for an env-var kill-switch so the mechanism can be paused without
editing the eligible set, and so a future operator can restore it from
configuration when EV improves.

The `DISABLE_PYRAMIDING` env var must short-circuit the emit branch
BEFORE any OANDA call. We assert this by inspecting `demo_trader.py`
source — a behavioral end-to-end test would require a full DemoTrader
fixture which is out of scope for this PR. The presence of the gate is
the regression invariant.
"""
from __future__ import annotations

import inspect

import modules.demo_trader as dt_mod


def test_pyramiding_kill_switch_present_in_source():
    """The PYR emit branch must read DISABLE_PYRAMIDING.

    If a future refactor renames or drops the env-var check, this test
    fails and forces re-justification.
    """
    src = inspect.getsource(dt_mod)
    assert "DISABLE_PYRAMIDING" in src, (
        "DemoTrader must check DISABLE_PYRAMIDING env-var before emitting "
        "a pyramid position. See audit 2026-05-01 Pillar 2.4 / 4.7."
    )
    # The check should be a guard on the same branch as
    # _PE_50PCT_ELIGIBLE / _pyramided_trades — verify both tokens are
    # close to each other in the file (within 200 lines).
    idx_disable = src.index("DISABLE_PYRAMIDING")
    idx_eligible = src.index("_PE_50PCT_ELIGIBLE")
    line_disable = src.count("\n", 0, idx_disable)
    line_eligible = src.count("\n", 0, idx_eligible)
    assert abs(line_disable - line_eligible) < 200, (
        f"DISABLE_PYRAMIDING check appears far from _PE_50PCT_ELIGIBLE "
        f"branch (disable@{line_disable}, eligible@{line_eligible}); the "
        f"kill-switch must guard the emit path, not be placed elsewhere."
    )
