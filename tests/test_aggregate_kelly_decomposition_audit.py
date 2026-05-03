import pytest

from tools.aggregate_kelly_decomposition_audit import (
    AggregateSnapshot,
    assign_flag,
    binomial_one_sided_lower_p,
    build_snapshot,
    classify_session_utc,
    compare_snapshot,
    normalize_regime_label,
)


def test_classify_session_utc_matches_bt_mapping():
    assert classify_session_utc("2026-04-29T00:30:00+00:00") == "Asia_early"
    assert classify_session_utc("2026-04-29T03:30:00+00:00") == "Tokyo"
    assert classify_session_utc("2026-04-29T08:30:00+00:00") == "London"
    assert classify_session_utc("2026-04-29T14:30:00+00:00") == "overlap_LN"
    assert classify_session_utc("2026-04-29T18:30:00+00:00") == "NY"
    assert classify_session_utc("2026-04-29T22:30:00+00:00") == "Sydney"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("trend_up_strong", "bull"),
        ("trend_down_weak", "bear"),
        ("range_tight", "range"),
        ("uncertain", "mixed"),
        ("", "unknown"),
        (None, "unknown"),
    ],
)
def test_normalize_regime_label(raw, expected):
    assert normalize_regime_label(raw) == expected


def test_assign_flag_uses_conservative_demote_rule():
    assert assign_flag(n=8, ev_pip=-0.2, wilson_upper=0.28, bev_wr=0.344) == "DEMOTE"
    assert assign_flag(n=8, ev_pip=-0.2, wilson_upper=0.30, bev_wr=0.344) == "WATCH"
    assert assign_flag(n=5, ev_pip=-0.2, wilson_upper=0.10, bev_wr=0.344) == "WATCH"
    assert assign_flag(n=8, ev_pip=0.1, wilson_upper=0.10, bev_wr=0.344) == "OK"


def test_binomial_one_sided_lower_p_detects_clear_underperformance():
    assert binomial_one_sided_lower_p(0, 10, 0.344) < 0.05
    assert binomial_one_sided_lower_p(6, 10, 0.344) > 0.05


def test_build_snapshot_computes_expected_aggregate_fields():
    rows = [
        {"outcome": "WIN", "pnl_pips": 12.0},
        {"outcome": "WIN", "pnl_pips": 8.0},
        {"outcome": "LOSS", "pnl_pips": -10.0},
        {"outcome": "LOSS", "pnl_pips": -6.0},
    ]
    snap = build_snapshot(rows)
    assert snap.n == 4
    assert snap.wins == 2
    assert snap.losses == 2
    assert snap.wr == pytest.approx(0.5)
    assert snap.ev_pip == pytest.approx(1.0)
    assert snap.pnl_pip == pytest.approx(4.0)
    assert snap.edge == pytest.approx(0.125)
    assert snap.full_kelly == pytest.approx(0.1)


def test_compare_snapshot_reports_mismatch_outside_tolerance():
    actual = AggregateSnapshot(
        n=23,
        wins=12,
        losses=11,
        wr=12 / 23,
        ev_pip=1.409,
        pnl_pip=32.4,
        edge=0.0,
        full_kelly=0.0,
    )
    problems = compare_snapshot(actual)
    assert any("N mismatch" in p for p in problems)
    assert any("WR mismatch" in p for p in problems)
    assert any("EV mismatch" in p for p in problems)
