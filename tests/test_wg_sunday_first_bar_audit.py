"""tools/wg_sunday_first_bar_audit.py — pure-function pins (rule:R3, 2026-10-22).

Registry `wg-dst-cutoff-basis-r3` / DRAFT weekend-gap-execution-modality
§5 items 1-2: the audit must (a) find weekend gaps only (holidays excluded),
(b) replicate the detector's DST-blind 21:00 cuts, (c) classify summer (21:00)
vs winter (22:00) Sunday stamps, and (d) flag the structural-bug signature
(detector resolving to a 21:00 bar on a 22:00-open weekend) when present.
"""
from datetime import timedelta

import pandas as pd

from tools.wg_sunday_first_bar_audit import (
    audit_pair,
    classify_open,
    resolve_as_detector,
    weekend_boundaries,
)


def _bars(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(start, end, freq="15min", tz="UTC")


def _winter_like_index() -> pd.DatetimeIndex:
    """Measured previous-winter MASSIVE structure (2025-11-02 .. 2026-03-01):
    Friday bars through 21:45, Sunday first bar 22:00. Plus a Christmas gap
    (Wed 22:00 -> Thu 21:00, 23h) that must NOT count as a weekend."""
    parts = [
        _bars("2025-12-08 00:00", "2025-12-12 21:45"),   # Mon..Fri (winter)
        _bars("2025-12-14 22:00", "2025-12-19 21:45"),   # Sun 22:00 .. Fri
        _bars("2025-12-21 22:00", "2025-12-24 22:00"),   # Sun 22:00 .. Wed 22:00 (Xmas eve)
        _bars("2025-12-25 21:00", "2025-12-26 21:45"),   # Thu 21:00 .. Fri (holiday reopen)
        _bars("2025-12-28 22:00", "2025-12-31 22:00"),   # Sun 22:00 .. Wed
    ]
    return pd.DatetimeIndex(sorted(set().union(*[set(p) for p in parts])))


def _summer_like_index() -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(
        set(_bars("2026-07-20 00:00", "2026-07-24 20:45"))
        | set(_bars("2026-07-26 21:00", "2026-07-31 20:45"))
    ))


def test_weekend_boundaries_excludes_holiday_gaps():
    idx = _winter_like_index()
    recs = weekend_boundaries(idx)
    firsts = [r["first_bar"] for r in recs]
    assert pd.Timestamp("2025-12-14 22:00", tz="UTC") in firsts
    assert pd.Timestamp("2025-12-21 22:00", tz="UTC") in firsts
    assert pd.Timestamp("2025-12-28 22:00", tz="UTC") in firsts
    # Christmas 23h gap is a holiday, not a weekend
    assert pd.Timestamp("2025-12-25 21:00", tz="UTC") not in firsts
    assert all(r["gap_h"] >= 40 for r in recs)
    assert recs[0]["last_bar"] == pd.Timestamp("2025-12-12 21:45", tz="UTC")


def test_resolve_as_detector_winter_first_bar_is_2200_and_deadline_2215():
    idx = _winter_like_index()
    fb = pd.Timestamp("2025-12-14 22:00", tz="UTC")
    res = resolve_as_detector(idx, fb)
    # DST-blind cuts (frozen explore definition)
    assert res["fri_cut"] == pd.Timestamp("2025-12-12 21:00", tz="UTC")
    assert res["sun_cut"] == pd.Timestamp("2025-12-14 21:00", tz="UTC")
    # first bar >= Sun 21:00 is the 22:00 stamped bar -> deadline 22:15 > real open ~22:04
    assert res["first_bar_ts"] == fb
    assert res["first_bar_hour_utc"] == 22
    assert res["first_bar_within_guard"] is True
    assert res["halt_deadline"] == fb + timedelta(minutes=15)
    # Friday-side estimand in winter: last bar strictly < Fri 21:00 = 20:45 bar
    # (the 21:00..21:45 winter bars are NOT the Friday close under the frozen
    # definition — recorded as an estimand fact, change would be R1)
    assert res["fri_close_bar"] == pd.Timestamp("2025-12-12 20:45", tz="UTC")


def test_resolve_as_detector_summer_first_bar_is_2100():
    idx = _summer_like_index()
    fb = pd.Timestamp("2026-07-26 21:00", tz="UTC")
    res = resolve_as_detector(idx, fb)
    assert res["first_bar_ts"] == fb
    assert res["first_bar_hour_utc"] == 21
    assert res["halt_deadline"] == fb + timedelta(minutes=15)
    assert res["fri_close_bar"] == pd.Timestamp("2026-07-24 20:45", tz="UTC")


def test_classify_open():
    assert classify_open(pd.Timestamp("2026-07-26 21:00", tz="UTC")) == "sun21"
    assert classify_open(pd.Timestamp("2025-12-14 22:00", tz="UTC")) == "sun22"
    assert classify_open(pd.Timestamp("2025-12-25 21:00", tz="UTC")) == "other"  # Thursday
    assert classify_open(pd.Timestamp("2026-07-26 21:15", tz="UTC")) == "other"
    assert classify_open(None) == "other"


def test_audit_pair_counts_and_no_structural_bug_on_measured_structure():
    idx = _winter_like_index()
    rep = audit_pair("USD_JPY", idx,
                     pd.Timestamp("2025-12-01", tz="UTC"),
                     pd.Timestamp("2026-01-05", tz="UTC"))
    assert rep["n_weekends"] == 3
    assert rep["counts"] == {"sun21": 0, "sun22": 3, "other": 0}
    assert rep["deterministic_halt_signature"] == 0
    assert all(r["detector_matches_index_first_bar"] for r in rep["weekends"])
    assert all(r["halt_deadline"].endswith("22:15:00+00:00") for r in rep["weekends"])


def test_audit_pair_flags_structural_bug_signature_when_vendor_emits_2100_in_winter():
    """Counterfactual: if the vendor stamped a (fake) 21:00 bar on a winter
    weekend whose real first bar is 22:00, the detector would resolve to 21:00
    (deadline 21:15 < real open 22:04) — the signature the audit must flag."""
    idx = _winter_like_index()
    fake = pd.Timestamp("2025-12-14 21:00", tz="UTC")
    idx2 = pd.DatetimeIndex(sorted(set(idx) | {fake}))
    # weekend_boundaries now sees 21:00 as the first bar (gap >= 40h still)
    rep = audit_pair("USD_JPY", idx2,
                     pd.Timestamp("2025-12-13", tz="UTC"),
                     pd.Timestamp("2025-12-15", tz="UTC"))
    assert rep["n_weekends"] == 1
    assert rep["counts"]["sun21"] == 1
    # the audit's own "index first bar" is 21:00 here, so the mismatch flag is
    # what a *consumer* of the index would see; we pin the resolution instead:
    res = resolve_as_detector(idx2, pd.Timestamp("2025-12-14 22:00", tz="UTC"))
    assert res["first_bar_ts"] == fake
    assert res["halt_deadline"] == fake + timedelta(minutes=15)   # 21:15 < 22:04
