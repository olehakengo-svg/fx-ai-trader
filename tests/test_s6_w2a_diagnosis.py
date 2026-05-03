import math
import sqlite3
from pathlib import Path

import pandas as pd

from tools.s6_w2a_diagnosis import (
    BONFERRONI_ALPHA,
    SpreadHour,
    apply_spread_adjustment,
    bonferroni_m,
    build_spread_profile,
    hour_bucket,
    hypothetical_rr_pnl,
    payoff_bev,
    percentile,
    propose_verdict,
    stats_for_pnls,
)


def make_demo_db(path: Path) -> None:
    with sqlite3.connect(path) as con:
        con.execute(
            """
            CREATE TABLE demo_trades (
                instrument TEXT,
                entry_time TEXT,
                spread_at_entry REAL,
                spread_at_exit REAL
            )
            """
        )
        con.executemany(
            "INSERT INTO demo_trades VALUES (?, ?, ?, ?)",
            [
                ("USD_JPY", "2026-01-01T00:00:00+00:00", 0.7, 0.8),
                ("USD_JPY", "2026-01-01T00:05:00+00:00", 0.8, 0.8),
                ("USD_JPY", "2026-01-01T09:00:00+00:00", 0.5, 0.6),
                ("USD_JPY", "2026-01-01T13:00:00+00:00", 0.6, 0.7),
                ("USD_JPY", "2026-01-01T17:00:00+00:00", 1.1, 1.2),
                ("EUR_USD", "2026-01-01T00:00:00+00:00", 9.0, 9.0),
            ],
        )
        con.commit()


def test_hour_bucket_boundaries():
    assert hour_bucket(0) == "Asia"
    assert hour_bucket(7) == "Asia"
    assert hour_bucket(8) == "London"
    assert hour_bucket(11) == "London"
    assert hour_bucket(12) == "London_NY_overlap"
    assert hour_bucket(15) == "London_NY_overlap"
    assert hour_bucket(16) == "NY+late"
    assert hour_bucket(23) == "NY+late"


def test_spread_profile_builder_returns_24_hours_with_sqlite_source(tmp_path):
    db = tmp_path / "demo.db"
    make_demo_db(db)
    profile = build_spread_profile(db, "USD_JPY")
    assert len(profile) == 24
    assert {p.hour_utc for p in profile} == set(range(24))
    assert profile[0].n_observations == 2
    assert math.isclose(profile[0].avg_round_trip_spread_pips, 1.55)


def test_spread_profile_fills_missing_hour_from_bucket(tmp_path):
    db = tmp_path / "demo.db"
    make_demo_db(db)
    profile = {p.hour_utc: p for p in build_spread_profile(db, "USD_JPY")}
    assert profile[1].n_observations == 0
    assert math.isclose(profile[1].median_round_trip_spread_pips, 1.55)


def test_spread_profile_ignores_other_pairs(tmp_path):
    db = tmp_path / "demo.db"
    make_demo_db(db)
    profile = build_spread_profile(db, "USD_JPY")
    assert max(p.avg_round_trip_spread_pips for p in profile) < 18.0


def test_apply_spread_adjustment_reverses_flat_spread_and_applies_empirical():
    trades = pd.DataFrame(
        {
            "entry_hour": [0],
            "pnl_pips": [3.5],
        }
    )
    adjusted = apply_spread_adjustment(trades, [SpreadHour(0, 10, 1.0, 1.0, 1.0)])
    assert math.isclose(float(adjusted["raw_pnl_pips"].iloc[0]), 5.0)
    assert math.isclose(float(adjusted["pnl_adjusted"].iloc[0]), 4.0)


def test_bonferroni_m_axis_values():
    assert bonferroni_m("spread_adj") == 12
    assert bonferroni_m("rr_optimal") == 60
    assert bonferroni_m("hour_bucket") == 48
    assert bonferroni_m("pivot_quality") == 48
    assert bonferroni_m("regime") == 24


def test_hypothetical_rr_hits_tp_when_mfe_reaches_target():
    row = pd.Series({"pattern_height_pips": 10.0, "sl_dist_pips": 6.0, "mfe_pips": 7.5, "mafe_pips": 1.0, "raw_pnl_pips": 0.0})
    assert math.isclose(hypothetical_rr_pnl(row, 0.75), 6.0)


def test_hypothetical_rr_hits_sl_before_tp_conservatively():
    row = pd.Series({"pattern_height_pips": 10.0, "sl_dist_pips": 6.0, "mfe_pips": 10.0, "mafe_pips": 6.0, "raw_pnl_pips": 0.0})
    assert math.isclose(hypothetical_rr_pnl(row, 1.00), -7.5)


def test_hypothetical_rr_timeout_keeps_existing_raw_then_flat_spread():
    row = pd.Series({"pattern_height_pips": 10.0, "sl_dist_pips": 6.0, "mfe_pips": 2.0, "mafe_pips": 1.0, "raw_pnl_pips": 0.7})
    assert math.isclose(hypothetical_rr_pnl(row, 1.00), -0.8)


def test_payoff_bev_uses_realized_payoff_geometry():
    assert math.isclose(payoff_bev(3.0, 2.0), 0.4)
    assert payoff_bev(0.0, 0.0) == 1.0


def test_stats_for_pnls_returns_ev_pf_and_verdict():
    n, wr, ev, pf, wilson, bev, p, kelly, verdict = stats_for_pnls([2, 2, -1, 3], 12)
    assert n == 4
    assert math.isclose(wr, 0.75)
    assert math.isclose(ev, 1.5)
    assert pf and pf > 2
    assert 0 <= wilson <= wr
    assert 0 <= bev <= 1
    assert 0 <= p <= 1
    assert verdict == "INSUFFICIENT"


def test_propose_verdict_rejects_if_bonferroni_gate_fails():
    verdict = propose_verdict(200, 1.0, 2.0, 0.7, 0.4, BONFERRONI_ALPHA / 12, 12, 0.1)
    assert verdict == "REJECT"


def test_percentile_interpolates():
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
