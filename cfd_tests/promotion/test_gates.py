"""gates.py: v2.1 BT sanity floor + H1 Gate constants."""
from __future__ import annotations

from cfd_trader.engine.bt_result import BTResult
from cfd_trader.promotion.gates import (
    H1_N_MIN, H1_KELLY_MIN, H1_WILSON_LO_MIN,
    BTSanityVerdict, bt_sanity_verdict,
)


def make_result(*, ev_point: float, pf: float = 1.0, n: int = 50) -> BTResult:
    return BTResult(
        strategy_name="test", instrument="SPX500_USD", tf="M5",
        start_iso="2026-02-11T00:00:00Z", end_iso="2026-05-11T00:00:00Z",
        n=n, wr=0.5, ev_point=ev_point, pf=pf, wilson_lo=0.3,
        kelly_fraction=0.1, max_dd_point=10.0, single_year_concentration=0.5,
        data_source="oanda",
    )


def test_h1_gate_constants_match_spec() -> None:
    assert H1_N_MIN == 30
    assert H1_KELLY_MIN == 0.40
    assert H1_WILSON_LO_MIN == 0.0


def test_bt_sanity_pass_when_ev_is_positive() -> None:
    v = bt_sanity_verdict(make_result(ev_point=0.5))
    assert v == BTSanityVerdict.PASS


def test_bt_sanity_pass_when_ev_is_zero() -> None:
    # v2.1: catastrophic floor is PnL SIGN REVERSAL only. EV=0 is acceptable.
    v = bt_sanity_verdict(make_result(ev_point=0.0))
    assert v == BTSanityVerdict.PASS


def test_bt_sanity_fail_only_when_ev_strictly_negative() -> None:
    v = bt_sanity_verdict(make_result(ev_point=-0.01))
    assert v == BTSanityVerdict.FAIL_CATASTROPHIC


def test_bt_sanity_does_not_assert_pf_floor() -> None:
    # v2.1: PF below 0.85 is NOT a sanity failure (shadow is the truth).
    r = make_result(ev_point=0.1, pf=0.3)
    assert bt_sanity_verdict(r) == BTSanityVerdict.PASS


def test_bt_sanity_does_not_assert_n_floor() -> None:
    # v2.1: small N is not a sanity failure either; only EV sign matters.
    r = make_result(ev_point=0.1, n=5)
    assert bt_sanity_verdict(r) == BTSanityVerdict.PASS
