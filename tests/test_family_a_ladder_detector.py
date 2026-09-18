"""Freeze pins for the family A statement_ladder detector (台帳 #27).

These tests exist to make the 2026-09-18 pre-registration freeze binding:
a later edit to the parameters, the retrospective-L5 remap or the gates
must break a test, not slip through silently.
"""
import datetime as dt
import pathlib

import pytest

from tools import family_a_ladder_detector as det


# --- frozen constants -------------------------------------------------------
def test_frozen_parameters():
    assert (det.T_CARRY_BD, det.R_REARM_BD, det.H_HORIZON_BD) == (5, 20, 20)
    assert det.TRIGGER_LEVEL == 4
    assert det.GATE_A_MAX_ARMED_FRACTION == 0.25
    assert det.GATE_B_MIN_EVENTS == 5
    assert det.GATE_B_MIN_DISTINCT_YEARS == 2


# --- adversarial finding A-1: retrospective L5 is not a ladder rung ---------
@pytest.mark.parametrize(
    "matched,expected",
    [
        # 2023-09-13: L5 narration only, no talk level -> 0
        ("L5:介入を行い/介入を行った", 0),
        # 2022-10-03: retrospective L5 but genuine 断固 on the same day -> 4
        ("L1:注視;L2:過度な変動;L3:投機;L4:断固;L5:介入を行い", 4),
        # 2026-09-08: retrospective L5 over a bare 注視 -> 1
        ("L1:注視;L5:介入を実施", 1),
        # 2024-10-01: abstract/normative use -> 3 (its 投機 level)
        ("L3:投機;L5:介入を行う", 3),
        # leading language survives at 5
        ("L1:注視;L5:レートチェック", 5),
    ],
)
def test_effective_level_remap(matched, expected):
    assert det.effective_level(5, matched) == expected


def test_effective_level_passthrough_below_5():
    assert det.effective_level(4, "L4:断固") == 4
    assert det.effective_level(0, "") == 0


def test_retrospective_l5_cannot_trigger_alone():
    """A conference that only narrates a past intervention must not arm."""
    conf = {dt.date(2026, 3, 2): det.effective_level(5, "L1:注視;L5:介入を実施")}
    out = det.build(dt.date(2026, 3, 1), dt.date(2026, 4, 30), conference_levels=conf)
    assert out.events == []


# --- calendar ---------------------------------------------------------------
def test_business_day_calendar():
    assert det.is_business_day(dt.date(2026, 9, 18))       # Friday
    assert not det.is_business_day(dt.date(2026, 9, 19))   # Saturday
    assert not det.is_business_day(dt.date(2026, 1, 1))    # 元日
    assert not det.is_business_day(dt.date(2026, 12, 31))  # 御用納め後


# --- T / R / H --------------------------------------------------------------
def test_carry_forward_is_exactly_T_business_days():
    d0 = dt.date(2026, 3, 2)  # Monday
    out = det.build(d0, dt.date(2026, 4, 30), conference_levels={d0: 4})
    bd = [d for d in out.days]
    i0 = bd.index(d0)
    # conference day + T carried days hold the level, the next one drops
    assert all(out.level[bd[i0 + k]] == 4 for k in range(det.T_CARRY_BD + 1))
    assert out.level[bd[i0 + det.T_CARRY_BD + 1]] == 0


def test_rearm_suppresses_within_R_and_allows_after():
    d0 = dt.date(2026, 3, 2)
    days = det.business_days(d0, dt.date(2026, 7, 31))
    near = days[days.index(d0) + 10]
    far = days[days.index(d0) + 25]
    out_near = det.build(d0, dt.date(2026, 7, 31), conference_levels={d0: 4, near: 4})
    out_far = det.build(d0, dt.date(2026, 7, 31), conference_levels={d0: 4, far: 4})
    assert out_near.events == [d0]
    assert out_far.events == [d0, far]


def test_single_event_arms_H_plus_one_days():
    d0 = dt.date(2026, 3, 2)
    out = det.build(d0, dt.date(2026, 7, 31), conference_levels={d0: 4})
    assert len(out.armed) == det.H_HORIZON_BD + 1


# --- gates ------------------------------------------------------------------
def test_pass1_gates_shape():
    d0 = dt.date(2026, 3, 2)
    out = det.build(d0, dt.date(2026, 7, 31), conference_levels={d0: 4})
    g = det.pass1_gates(out)
    assert g["n_events"] == 1
    assert g["gate_b_supply"] is False          # 1 event < 5
    assert g["gate_a_specificity"] is True
    assert g["pass2_unlocked"] is False


# --- structural pin: the frozen detector must stay label-free ---------------
def test_detector_never_touches_labels_or_prices():
    src = pathlib.Path(det.__file__).read_text(encoding="utf-8")
    code = "\n".join(
        ln for ln in src.splitlines() if not ln.lstrip().startswith("#")
    )
    for forbidden in ("interventions_daily", "amount_yen", "oanda", "close", "pip"):
        assert forbidden not in code.lower(), f"label/price leak: {forbidden}"


# --- adversarial finding A-2: rearm is event-to-event, not level-based ------
def test_rearm_is_event_to_event_not_level_based():
    """Carry-forward must not inflate the refractory period to R + T."""
    d0 = dt.date(2026, 3, 2)
    days = det.business_days(d0, dt.date(2026, 7, 31))
    # +21 bd: inside the old (level-based, R+T=25) refractory, outside R
    far = days[days.index(d0) + 21]
    out = det.build(d0, dt.date(2026, 7, 31), conference_levels={d0: 4, far: 4})
    assert out.events == [d0, far]


def test_event_hit_windows_partition_cleanly():
    """Minimum separation R+1 = 21 bd exceeds H = 20, so windows never overlap."""
    d0 = dt.date(2026, 3, 2)
    days = det.business_days(d0, dt.date(2026, 7, 31))
    second = days[days.index(d0) + det.R_REARM_BD + 1]
    out = det.build(d0, dt.date(2026, 7, 31), conference_levels={d0: 4, second: 4})
    assert out.events == [d0, second]
    # armed days = 2 disjoint windows of H+1 days each
    assert len(out.armed) == 2 * (det.H_HORIZON_BD + 1)
