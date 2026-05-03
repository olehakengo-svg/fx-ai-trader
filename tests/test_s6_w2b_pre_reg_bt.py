import math
import sqlite3

import pandas as pd
import pytest

from tools import s6_w2b_pre_reg_bt as bt


def _bars(rows):
    return pd.DataFrame(
        {
            "open": [r[1] for r in rows],
            "high": [r[2] for r in rows],
            "low": [r[3] for r in rows],
            "close": [r[4] for r in rows],
        },
        index=pd.to_datetime([r[0] for r in rows], utc=True),
    )


def _linear_bars(n=40, base=100.0):
    ts0 = pd.Timestamp("2026-01-01 11:55", tz="UTC")
    rows = []
    for i in range(n):
        px = base + i * 0.001
        rows.append((ts0 + pd.Timedelta(minutes=5 * i), px, px + 0.005, px - 0.005, px + 0.001))
    return _bars(rows)


def _signal(pattern_id=8, direction="BUY", signal_ts="2026-01-01T12:00:00+00:00", sl=99.90, tp=100.30):
    return bt.Signal(
        signal_id=pattern_id,
        pattern_id=pattern_id,
        pattern_name=bt.CANDIDATES_BY_PATTERN[pattern_id].pattern_name,
        direction=direction,
        pair="USD_JPY",
        timeframe="M5",
        signal_ts=signal_ts,
        sl_px=sl,
        frozen_tp_px=tp,
    )


def test_sqlite_ddl_embeds_locked_w2b_tables_and_candidate_check():
    assert "chart_pattern_w2b_trades" in bt.SQLITE_DDL
    assert "chart_pattern_w2b_verdicts" in bt.SQLITE_DDL
    assert "candidate_id IN ('C1','C2','C3')" in bt.SQLITE_DDL
    assert "UNIQUE(candidate_id, intrabar_resolve, eval_split)" in bt.SQLITE_DDL


def test_candidate_set_is_locked_to_three_cells_and_bonferroni_m3():
    assert list(bt.CANDIDATES) == ["C1", "C2", "C3"]
    assert {c.pattern_id for c in bt.CANDIDATES.values()} == {8, 9, 11}
    assert bt.BONFERRONI_ALPHA == pytest.approx(0.05 / 3)


def test_rr_125_tp_recompute_for_buy_uses_entry_and_sl_distance():
    assert bt.recompute_tp("BUY", entry_px=100.00, sl_px=99.90) == pytest.approx(100.125)


def test_rr_125_tp_recompute_for_sell_uses_entry_and_sl_distance():
    assert bt.recompute_tp("SELL", entry_px=100.00, sl_px=100.10) == pytest.approx(99.875)


def test_hour_of_day_spread_injection_uses_signal_hour():
    assert bt.spread_for_signal_hour("2026-01-01T13:55:00+00:00", {12: 1.2, 13: 1.8}) == pytest.approx(1.8)


def test_time_filter_keeps_12_to_before_16_utc_only():
    assert not bt.is_london_ny_overlap("2026-01-01T11:59:00+00:00")
    assert bt.is_london_ny_overlap("2026-01-01T12:00:00+00:00")
    assert bt.is_london_ny_overlap("2026-01-01T15:59:00+00:00")
    assert not bt.is_london_ny_overlap("2026-01-01T16:00:00+00:00")


def test_entry_uses_next_bar_open_after_signal_ts():
    bars = _linear_bars()
    trade = bt.simulate_trade(_signal(signal_ts="2026-01-01T12:00:00+00:00", sl=99.50), bars, {12: 1.5}, "SL_FIRST")
    assert trade.entry_ts == "2026-01-01T12:05:00+00:00"
    assert trade.entry_px == pytest.approx(float(bars["open"].iloc[2]))


def test_signal_at_1555_is_excluded_because_next_bar_entry_is_1600():
    bars = _bars([("2026-01-01 15:55", 100.0, 100.01, 99.99, 100.0), ("2026-01-01 16:00", 100.0, 100.20, 99.99, 100.1)])
    assert bt.simulate_trade(_signal(signal_ts="2026-01-01T15:55:00+00:00"), bars, {15: 1.5}, "SL_FIRST") is None


def test_intrabar_dual_resolve_changes_same_bar_exit_reason():
    bars = _bars([("2026-01-01 12:00", 100.00, 100.01, 99.99, 100.00), ("2026-01-01 12:05", 100.00, 100.20, 99.80, 100.10)])
    sig = _signal(sl=99.90)
    assert bt.simulate_trade(sig, bars, {12: 1.0}, "SL_FIRST").exit_reason == "SL"
    assert bt.simulate_trade(sig, bars, {12: 1.0}, "TP_FIRST").exit_reason == "TP"


def test_buy_tp_pnl_subtracts_empirical_spread():
    bars = _bars([("2026-01-01 12:00", 100.00, 100.01, 99.99, 100.00), ("2026-01-01 12:05", 100.00, 100.20, 99.99, 100.10)])
    trade = bt.simulate_trade(_signal(sl=99.90), bars, {12: 1.25}, "SL_FIRST")
    assert trade.exit_reason == "TP"
    assert trade.pnl_pips == pytest.approx(12.5 - 1.25)


def test_sell_sl_tp_and_pnl_geometry():
    bars = _bars([("2026-01-01 12:00", 100.00, 100.01, 99.99, 100.00), ("2026-01-01 12:05", 100.00, 100.20, 99.80, 99.90)])
    sig = _signal(pattern_id=11, direction="SELL", sl=100.10, tp=99.80)
    trade = bt.simulate_trade(sig, bars, {12: 1.0}, "TP_FIRST")
    assert trade.tp_px == pytest.approx(99.875)
    assert trade.exit_reason == "TP"
    assert trade.pnl_pips == pytest.approx(12.5 - 1.0)


def test_timeout_exits_at_close_and_keeps_trade_after_30_bars():
    trade = bt.simulate_trade(_signal(sl=99.00), _linear_bars(n=35), {12: 1.5}, "SL_FIRST")
    assert trade.exit_reason == "TIMEOUT"
    assert trade.hold_bars == 30
    assert trade.exit_ts == "2026-01-01T14:35:00+00:00"


def test_mafe_mfe_are_entry_price_based():
    bars = _bars(
        [
            ("2026-01-01 12:00", 100.00, 100.01, 99.99, 100.00),
            ("2026-01-01 12:05", 100.00, 100.08, 99.96, 100.01),
            ("2026-01-01 12:10", 100.00, 100.13, 99.98, 100.12),
        ]
    )
    trade = bt.simulate_trade(_signal(sl=99.90), bars, {12: 1.5}, "SL_FIRST")
    assert trade.mafe_pips == pytest.approx(4.0)
    assert trade.mfe_pips == pytest.approx(13.0)


def test_oos_single_split_boundary():
    assert bt.oos_label("2022-12-31T23:55:00+00:00") == "TRAIN"
    assert bt.oos_label("2023-01-01T00:00:00+00:00") == "OOS"


def test_walk_forward_fold_boundaries():
    assert bt.wf_fold("2019-01-01T00:00:00+00:00") == 1
    assert bt.wf_fold("2021-01-01T00:00:00+00:00") == 2
    assert bt.wf_fold("2023-01-01T00:00:00+00:00") == 3
    assert bt.wf_fold("2018-12-31T23:55:00+00:00") is None


def test_oos_n_below_30_is_insufficient_even_if_profitable():
    verdict, reason = bt.decide_verdict(bt.stats_for_pnls([10.0] * 29, []), wf_pfs=[2.0, 2.0, 2.0])
    assert verdict == "INSUFFICIENT"
    assert "N<30" in reason


def test_reject_when_wilson_or_pf_fails():
    verdict, reason = bt.decide_verdict(bt.stats_for_pnls([-1.0, 1.0] * 20, []), wf_pfs=[2.0, 2.0, 2.0])
    assert verdict == "REJECT"
    assert "Wilson" in reason or "PF" in reason


def test_shadow_when_oos_core_passes_but_promote_pf_gate_fails():
    stats = bt.AggregateStats(40, 0.7, 1.0, 1.3, 0.55, 0.50, 0.001, 0.2, -5.0)
    verdict, _ = bt.decide_verdict(stats, wf_pfs=[2.0, 2.0, 2.0])
    assert verdict == "SHADOW"


def test_load_spread_profile_reads_existing_w2a_table(tmp_path):
    db = tmp_path / "chart_patterns.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE chart_pattern_bt_spread_profile (pair TEXT, hour_utc INTEGER, avg_round_trip_spread_pips REAL, source TEXT)")
        con.executemany("INSERT INTO chart_pattern_bt_spread_profile VALUES (?, ?, ?, ?)", [("USD_JPY", h, 1.0 + h / 100.0, "demo_trades_empirical") for h in range(24)])
    assert bt.load_spread_profile(db, "USD_JPY")[15] == pytest.approx(1.15)


def test_write_results_appends_w2b_tables_without_touching_frozen_table(tmp_path):
    db = tmp_path / "chart_patterns.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE chart_pattern_signals (id INTEGER PRIMARY KEY)")
        con.execute("INSERT INTO chart_pattern_signals VALUES (1)")
    trade = bt.Trade("C1", 1, 8, "USD_JPY", "M5", "BUY", "SL_FIRST", "2023-01-01T00:00:00+00:00", 100.0, 99.9, 100.125, "2023-01-01T00:05:00+00:00", 100.125, "TP", 1.0, 11.5, 0.0, 12.5, 1, "OOS", 3)
    verdict = bt.VerdictRow("C1", 8, "SL_FIRST", "OOS_1", 1, 1.0, 11.5, math.inf, 1.0, 0.1, 0.001, bt.BONFERRONI_ALPHA, 1.0, 0.0, "INSUFFICIENT", "N<30")
    bt.write_results(db, [trade], [verdict])
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM chart_pattern_signals").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM chart_pattern_w2b_trades").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM chart_pattern_w2b_verdicts").fetchone()[0] == 1
