import math

import pandas as pd
import pytest
from scipy.stats import binomtest

from tools import s6_chart_pattern_bt as bt


def _bars(rows):
    idx = pd.to_datetime([r[0] for r in rows], utc=True)
    return pd.DataFrame(
        {
            "open": [r[1] for r in rows],
            "high": [r[2] for r in rows],
            "low": [r[3] for r in rows],
            "close": [r[4] for r in rows],
        },
        index=idx,
    )


def _linear_bars(n=25, base=100.0):
    rows = []
    ts = pd.Timestamp("2026-01-01 00:00", tz="UTC")
    for i in range(n):
        px = base + i * 0.01
        rows.append((ts + pd.Timedelta(minutes=5 * i), px, px + 0.02, px - 0.02, px + 0.005))
    return pd.DataFrame(
        {"open": [r[1] for r in rows], "high": [r[2] for r in rows], "low": [r[3] for r in rows], "close": [r[4] for r in rows]},
        index=pd.to_datetime([r[0] for r in rows], utc=True),
    )


def _signal(pattern_id=1, direction="BUY", signal_ts="2026-01-01 00:00+00:00", sl=99.80, tp=100.30, confidence=0.5):
    spec = bt.PATTERN_BY_ID[pattern_id]
    return bt.Signal(
        signal_id=pattern_id,
        pattern_id=pattern_id,
        pattern_name=spec.name,
        direction=direction,
        pair="USD_JPY",
        timeframe="M5",
        signal_ts=signal_ts,
        sl_px=sl,
        tp_px=tp,
        confidence_score=confidence,
    )


def test_sqlite_schema_embeds_locked_tables_and_unique_verdict_key():
    assert "chart_pattern_bt_trades" in bt.SQLITE_DDL
    assert "chart_pattern_bt_verdicts" in bt.SQLITE_DDL
    assert "UNIQUE(pattern_id, pair, timeframe, bt_run_id)" in bt.SQLITE_DDL


def test_pattern_catalog_locks_12_pattern_directions():
    assert [p.pattern_id for p in bt.PATTERNS] == list(range(1, 13))
    assert [p.direction for p in bt.PATTERNS[:3]] == ["BUY", "BUY", "BUY"]
    assert [p.direction for p in bt.PATTERNS[3:6]] == ["SELL", "SELL", "SELL"]


def test_entry_uses_next_bar_open_not_signal_entry_price():
    df = _linear_bars()
    sig = _signal(signal_ts="2026-01-01 00:00+00:00", sl=99.50, tp=101.00)
    trade = bt.simulate_trade(sig, df)
    assert trade.entry_ts == "2026-01-01T00:05:00+00:00"
    assert trade.entry_px == pytest.approx(100.01)


def test_buy_tp_hit_subtracts_locked_spread():
    df = _bars(
        [
            ("2026-01-01 00:00", 100.00, 100.01, 99.99, 100.00),
            ("2026-01-01 00:05", 100.10, 100.25, 100.08, 100.20),
        ]
    )
    trade = bt.simulate_trade(_signal(sl=99.90, tp=100.20), df)
    assert trade.exit_reason == "TP"
    assert trade.pnl_pips == pytest.approx(8.5)


def test_buy_sl_hit_subtracts_locked_spread():
    df = _bars(
        [
            ("2026-01-01 00:00", 100.00, 100.01, 99.99, 100.00),
            ("2026-01-01 00:05", 100.10, 100.12, 99.94, 100.00),
        ]
    )
    trade = bt.simulate_trade(_signal(sl=99.95, tp=100.30), df)
    assert trade.exit_reason == "SL"
    assert trade.pnl_pips == pytest.approx(-16.5)


def test_buy_timeout_exits_at_entry_plus_20_close():
    df = _linear_bars(n=23, base=100.0)
    trade = bt.simulate_trade(_signal(sl=99.00, tp=102.00), df)
    assert trade.exit_reason == "TIMEOUT"
    assert trade.hold_bars == 20
    assert trade.exit_ts == "2026-01-01T01:45:00+00:00"
    assert trade.exit_px == pytest.approx(df["close"].iloc[21])


def test_sell_tp_hit_subtracts_locked_spread():
    df = _bars(
        [
            ("2026-01-01 00:00", 100.00, 100.01, 99.99, 100.00),
            ("2026-01-01 00:05", 100.10, 100.12, 99.85, 99.90),
        ]
    )
    trade = bt.simulate_trade(_signal(pattern_id=4, direction="SELL", sl=100.30, tp=99.90), df)
    assert trade.exit_reason == "TP"
    assert trade.pnl_pips == pytest.approx(18.5)


def test_sell_sl_hit_subtracts_locked_spread():
    df = _bars(
        [
            ("2026-01-01 00:00", 100.00, 100.01, 99.99, 100.00),
            ("2026-01-01 00:05", 100.10, 100.31, 100.00, 100.20),
        ]
    )
    trade = bt.simulate_trade(_signal(pattern_id=4, direction="SELL", sl=100.30, tp=99.90), df)
    assert trade.exit_reason == "SL"
    assert trade.pnl_pips == pytest.approx(-21.5)


def test_sell_timeout_exits_at_entry_plus_20_close():
    df = _linear_bars(n=23, base=100.0)
    trade = bt.simulate_trade(_signal(pattern_id=4, direction="SELL", sl=102.00, tp=99.00), df)
    assert trade.exit_reason == "TIMEOUT"
    assert trade.pnl_pips == pytest.approx((trade.entry_px - trade.exit_px) * 100 - 1.5)


def test_same_bar_tp_and_sl_uses_conservative_sl_priority():
    df = _bars(
        [
            ("2026-01-01 00:00", 100.00, 100.01, 99.99, 100.00),
            ("2026-01-01 00:05", 100.10, 100.25, 99.90, 100.15),
        ]
    )
    trade = bt.simulate_trade(_signal(sl=99.95, tp=100.20), df)
    assert trade.exit_reason == "SL"


def test_mafe_mfe_for_buy_are_entry_price_based():
    df = _bars(
        [
            ("2026-01-01 00:00", 100.00, 100.01, 99.99, 100.00),
            ("2026-01-01 00:05", 100.10, 100.18, 100.03, 100.10),
            ("2026-01-01 00:10", 100.10, 100.22, 100.08, 100.20),
        ]
    )
    trade = bt.simulate_trade(_signal(sl=99.90, tp=100.20), df)
    assert trade.mafe_pips == pytest.approx(7.0)
    assert trade.mfe_pips == pytest.approx(12.0)


def test_mafe_mfe_for_sell_are_entry_price_based():
    df = _bars(
        [
            ("2026-01-01 00:00", 100.00, 100.01, 99.99, 100.00),
            ("2026-01-01 00:05", 100.10, 100.16, 99.98, 100.10),
            ("2026-01-01 00:10", 100.10, 100.12, 99.88, 99.90),
        ]
    )
    trade = bt.simulate_trade(_signal(pattern_id=4, direction="SELL", sl=100.30, tp=99.90), df)
    assert trade.mafe_pips == pytest.approx(6.0)
    assert trade.mfe_pips == pytest.approx(22.0)


def test_signal_without_entry_plus_20_bar_is_not_fillable_for_timeout():
    df = _linear_bars(n=3, base=100.0)
    assert bt.simulate_trade(_signal(sl=99.00, tp=102.00), df) is None


def test_wilson_lower_matches_known_50_of_100_value():
    assert bt.wilson_lower(50, 100) == pytest.approx(0.4038, abs=0.0001)


def test_bonferroni_p_matches_one_sided_binomial_against_bev():
    assert bt.binomial_edge_p(60, 100, 0.50) == pytest.approx(binomtest(60, 100, 0.50, alternative="greater").pvalue)


def test_kelly_fraction_matches_payoff_formula():
    assert bt.kelly_fraction(0.60, 2.0) == pytest.approx(0.40)


def test_profit_factor_is_inf_when_no_losses():
    stats = bt.aggregate_trades([bt.Trade(pnl_pips=5.0), bt.Trade(pnl_pips=1.0)])
    assert math.isinf(stats.pf)


def test_max_drawdown_uses_running_cumulative_pnl():
    assert bt.max_drawdown_pips([10.0, -25.0, 5.0, -2.0]) == pytest.approx(-25.0)


def test_breakeven_wr_uses_locked_spread_over_avg_tp_plus_sl_distance():
    trades = [bt.Trade(entry_px=100.0, tp_px=100.2, sl_px=99.9), bt.Trade(entry_px=100.0, tp_px=100.1, sl_px=99.8)]
    assert bt.breakeven_wr(trades) == pytest.approx(1.5 / 30.0)


def test_walk_forward_fold_boundaries_are_locked():
    folds = bt.walk_forward_folds()
    assert folds[0].test_start == pd.Timestamp("2019-01-01", tz="UTC")
    assert folds[0].test_end == pd.Timestamp("2021-01-01", tz="UTC")
    assert folds[1].test_start == pd.Timestamp("2021-01-01", tz="UTC")
    assert folds[2].test_end == pd.Timestamp("2026-05-01", tz="UTC")


def test_walk_forward_assigns_trade_to_expected_test_fold():
    trade = bt.Trade(entry_ts="2021-06-01T00:00:00+00:00", pnl_pips=1.0)
    assert bt.fold_for_trade(trade, bt.walk_forward_folds()).fold_id == 2


def test_arbitration_keeps_highest_confidence_then_lowest_pattern_id():
    sigs = [
        _signal(pattern_id=3, signal_ts="2026-01-01 00:00+00:00", confidence=0.8),
        _signal(pattern_id=1, signal_ts="2026-01-01 00:00+00:00", confidence=0.8),
        _signal(pattern_id=2, signal_ts="2026-01-01 00:00+00:00", confidence=0.9),
    ]
    kept = bt.arbitrate_signals(sigs)
    assert [s.pattern_id for s, losers in kept] == [2]
    assert kept[0][1] == 2


def test_arbitration_keeps_independent_timestamps():
    sigs = [_signal(pattern_id=1, signal_ts="2026-01-01 00:00+00:00"), _signal(pattern_id=2, signal_ts="2026-01-01 00:05+00:00")]
    kept = bt.arbitrate_signals(sigs)
    assert len(kept) == 2
    assert all(losers == 0 for _, losers in kept)


def test_reversed_mode_only_flips_wedge_patterns():
    sigs = [_signal(pattern_id=2, direction="BUY"), _signal(pattern_id=5, direction="SELL")]
    reversed_sigs = bt.reverse_wedge_signals(sigs)
    assert [s.direction for s in reversed_sigs] == ["SELL", "BUY"]
    assert reversed_sigs[0].tp_px < reversed_sigs[0].sl_px
    assert reversed_sigs[1].tp_px > reversed_sigs[1].sl_px


def test_reversed_mode_rejects_non_wedge_patterns():
    with pytest.raises(ValueError):
        bt.reverse_wedge_signals([_signal(pattern_id=1)])


def test_verdict_is_insufficient_under_100_trades():
    stats = bt.AggregateStats(n=99, wr=0.90, ev_pips=10, pf=5, wilson_lo_95=0.8, bev_wr=0.1, bonferroni_p=0.0, kelly=0.5, max_dd_pips=0, wf_fold_pfs=[2, 2, 2])
    assert bt.decide_verdict(stats).verdict == "INSUFFICIENT"


def test_verdict_rejects_bonferroni_failure():
    stats = bt.AggregateStats(n=100, wr=0.55, ev_pips=1, pf=1.4, wilson_lo_95=0.45, bev_wr=0.1, bonferroni_p=0.02, kelly=0.1, max_dd_pips=-5, wf_fold_pfs=[2, 2, 2])
    assert bt.decide_verdict(stats).verdict == "REJECT"


def test_verdict_shadow_when_core_passes_but_one_wf_fold_fails():
    stats = bt.AggregateStats(n=100, wr=0.70, ev_pips=3, pf=2.0, wilson_lo_95=0.60, bev_wr=0.2, bonferroni_p=0.001, kelly=0.1, max_dd_pips=-5, wf_fold_pfs=[2, 0.9, 2])
    assert bt.decide_verdict(stats).verdict == "SHADOW"


def test_verdict_promote_requires_all_gates_and_kelly_above_005():
    stats = bt.AggregateStats(n=100, wr=0.70, ev_pips=3, pf=2.0, wilson_lo_95=0.60, bev_wr=0.2, bonferroni_p=0.001, kelly=0.06, max_dd_pips=-5, wf_fold_pfs=[2, 2, 2])
    assert bt.decide_verdict(stats).verdict == "PROMOTE"


@pytest.mark.parametrize("pattern_id", range(1, 13))
def test_self_test_covers_each_pattern_id(pattern_id):
    results = bt.run_self_test()
    assert results[pattern_id] in {"TP", "SL", "TIMEOUT"}
