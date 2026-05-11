"""Promotion gates — declarative thresholds + decision functions.

Section 5.A: H1 Gate constants (N>=30, Kelly>=0.40, Wilson_lo>=0.0).
W4 paradigm v2.1 (2026-05-06): BT sanity floor is **PnL sign reversal only**.
PF, N, Wilson_lo, Kelly are **not asserted against BT results**; they apply
to Shadow data, which is the true estimator. BT is a sanity filter that
rejects only catastrophic edge inversion.
"""
from __future__ import annotations

from enum import Enum

from cfd_trader.engine.bt_result import BTResult


# ---------------------------------------------------------------------------
# H1 Gate constants (Shadow -> Live promotion thresholds, NOT applied to BT)
# ---------------------------------------------------------------------------
H1_N_MIN: int = 30
H1_KELLY_MIN: float = 0.40
H1_WILSON_LO_MIN: float = 0.0


class BTSanityVerdict(Enum):
    PASS = "pass"
    FAIL_CATASTROPHIC = "fail_catastrophic"


def bt_sanity_verdict(result: BTResult) -> BTSanityVerdict:
    """v2.1 paradigm: BT sanity is EV sign only.

    Failure means the BT inverted the edge (negative EV). PF, N, Wilson, etc.
    are observed at Shadow time; BT does not gate on them.
    """
    if result.ev_point < 0.0:
        return BTSanityVerdict.FAIL_CATASTROPHIC
    return BTSanityVerdict.PASS
