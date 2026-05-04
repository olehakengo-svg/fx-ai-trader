import math

import pandas as pd

from tools.bt import b3_turtle_soup as b3


def _bars(rows):
    idx = pd.to_datetime([r[0] for r in rows], utc=True)
    return pd.DataFrame(
        {
            "open": [r[1] for r in rows],
            "high": [r[2] for r in rows],
            "low": [r[3] for r in rows],
            "close": [r[4] for r in rows],
            "volume": 100,
        },
        index=idx,
    )


def test_setup_detection_uses_previous_20_trading_days_donchian():
    idx = pd.date_range("2026-01-01", periods=22, freq="D", tz="UTC")
    daily = pd.DataFrame(
        {
            "open": [100.0] * 22,
            "high": [100.0 + i * 0.1 for i in range(22)],
            "low": [99.0 - i * 0.1 for i in range(22)],
            "close": [100.0] * 22,
        },
        index=idx,
    )

    setups = b3.build_setup_days(daily, intervention_dates=set())

    assert setups[0].day == idx[20]
    assert math.isclose(setups[0].donchian_high, max(daily.iloc[:20]["high"]))
    assert math.isclose(setups[0].donchian_low, min(daily.iloc[:20]["low"]))


def test_short_entry_after_up_breakout_failure_within_window():
    day = pd.Timestamp("2026-02-01", tz="UTC")
    bars = _bars(
        [
            ("2026-02-01 00:00", 109.90, 110.02, 109.88, 110.01),
            ("2026-02-01 00:05", 110.01, 110.03, 109.93, 109.94),
            ("2026-02-01 00:10", 109.94, 109.96, 109.80, 109.82),
        ]
    )
    setup = b3.SetupDay(day=day, donchian_high=110.0, donchian_low=109.0, donchian_range=1.0, prev_close=109.5)

    trade = b3.simulate_setup_day(bars, setup, failure_window=2, exit_method="fixed_time", session_boundary="H24")

    assert trade is not None
    assert trade.direction == "SHORT"
    assert trade.breakout_ts == pd.Timestamp("2026-02-01 00:00", tz="UTC")
    assert trade.entry_ts == pd.Timestamp("2026-02-01 00:05", tz="UTC")
    assert math.isclose(trade.entry_price, 109.94)


def test_long_entry_after_down_breakout_failure_within_window():
    day = pd.Timestamp("2026-02-01", tz="UTC")
    bars = _bars(
        [
            ("2026-02-01 00:00", 109.10, 109.12, 108.98, 108.99),
            ("2026-02-01 00:05", 108.99, 109.08, 108.97, 109.06),
            ("2026-02-01 00:10", 109.06, 109.20, 109.05, 109.18),
        ]
    )
    setup = b3.SetupDay(day=day, donchian_high=110.0, donchian_low=109.0, donchian_range=1.0, prev_close=109.5)

    trade = b3.simulate_setup_day(bars, setup, failure_window=2, exit_method="fixed_time", session_boundary="H24")

    assert trade is not None
    assert trade.direction == "LONG"
    assert trade.entry_ts == pd.Timestamp("2026-02-01 00:05", tz="UTC")
    assert math.isclose(trade.entry_price, 109.06)


def test_trailing_exit_for_short_uses_full_donchian_range_from_best_price():
    day = pd.Timestamp("2026-02-01", tz="UTC")
    bars = _bars(
        [
            ("2026-02-01 00:00", 109.90, 110.02, 109.88, 110.01),
            ("2026-02-01 00:05", 110.01, 110.03, 109.93, 109.94),
            ("2026-02-01 00:10", 109.94, 109.95, 108.80, 108.90),
            ("2026-02-01 00:15", 108.90, 109.85, 108.88, 109.82),
        ]
    )
    setup = b3.SetupDay(day=day, donchian_high=110.0, donchian_low=109.0, donchian_range=1.0, prev_close=109.5)

    trade = b3.simulate_setup_day(bars, setup, failure_window=2, exit_method="100_trailing", session_boundary="H24")

    assert trade is not None
    assert trade.exit_ts == pd.Timestamp("2026-02-01 00:15", tz="UTC")
    assert trade.exit_reason == "trail_100"
    assert math.isclose(trade.pnl_pip, 12.0)


def test_fixed_time_and_stop_exit_paths():
    day = pd.Timestamp("2026-02-01", tz="UTC")
    fixed = _bars(
        [
            ("2026-02-01 15:50", 109.90, 110.02, 109.88, 110.01),
            ("2026-02-01 15:55", 110.01, 110.03, 109.93, 109.94),
            ("2026-02-01 16:00", 109.94, 109.95, 109.80, 109.82),
        ]
    )
    setup = b3.SetupDay(day=day, donchian_high=110.0, donchian_low=109.0, donchian_range=1.0, prev_close=109.5)
    fixed_trade = b3.simulate_setup_day(fixed, setup, failure_window=2, exit_method="fixed_time", session_boundary="London_close_16UTC")
    assert fixed_trade is not None
    assert fixed_trade.exit_reason == "session_close"
    assert fixed_trade.exit_ts == pd.Timestamp("2026-02-01 16:00", tz="UTC")

    stopped = _bars(
        [
            ("2026-02-01 00:00", 109.90, 110.02, 109.88, 110.01),
            ("2026-02-01 00:05", 110.01, 110.03, 109.93, 109.94),
            ("2026-02-01 00:10", 109.94, 110.08, 109.90, 110.07),
        ]
    )
    stop_trade = b3.simulate_setup_day(stopped, setup, failure_window=2, exit_method="fixed_time", session_boundary="H24")
    assert stop_trade is not None
    assert stop_trade.exit_reason == "stop"
    assert math.isclose(stop_trade.exit_price, 110.07)


def test_bonferroni_uses_locked_27_cells_and_bev_wr():
    assert b3.BONFERRONI_M == 27
    assert math.isclose(b3.bonferroni_adjusted_p(0.01), 0.27)
    assert math.isclose(b3.BEV_WR_USDJPY, 0.344)
    assert len(b3.grid_cells()) == 27
    assert b3.PRIMARY_CELL in b3.grid_cells()


def test_walk_forward_split_is_time_ordered_half_split():
    trades = [
        b3.Trade(
            entry_ts=pd.Timestamp(f"2026-01-0{i + 1} 00:00", tz="UTC"),
            exit_ts=pd.Timestamp(f"2026-01-0{i + 1} 01:00", tz="UTC"),
            direction="LONG",
            breakout_ts=pd.Timestamp(f"2026-01-0{i + 1} 00:00", tz="UTC"),
            breakout_price=100.0,
            entry_price=100.0,
            exit_price=100.0 + pnl * 0.01,
            stop_price=99.5,
            pnl_pip=pnl,
            pnl_pct=pnl / 10000,
            holding_minutes=60,
            setup_day=pd.Timestamp(f"2026-01-0{i + 1}", tz="UTC"),
            exit_reason="unit",
        )
        for i, pnl in enumerate([10.0, -5.0, 8.0, -2.0])
    ]

    wf = b3.walk_forward_50_50(trades)

    assert wf["is_n"] == 2
    assert wf["oos_n"] == 2
    assert math.isclose(wf["is_pf"], 2.0)
    assert math.isclose(wf["oos_pf"], 4.0)
    assert math.isclose(wf["oos_is_pf_ratio"], 2.0)


def test_intervention_list_load_exact_eight_and_missing_fails(tmp_path):
    good = tmp_path / "good.md"
    good.write_text(
        "#### B-2. Connors-Raschke\n"
        "2022-09-22 2022-10-21 2022-10-24 2024-04-29\n"
        "2024-05-01 2024-05-02 2024-07-11 2024-07-12\n"
        "#### B-3. next\n",
        encoding="utf-8",
    )
    dates, source = b3.load_intervention_dates([good])
    assert source == good
    assert len(dates) == 8
    assert "2024-07-12" in dates

    bad = tmp_path / "bad.md"
    bad.write_text("#### B-2. Connors-Raschke\n2024-07-12\n", encoding="utf-8")
    try:
        b3.load_intervention_dates([bad])
    except b3.InterventionListMissing as exc:
        assert "INTERVENTION_LIST_MISSING" in str(exc)
    else:
        raise AssertionError("expected InterventionListMissing")
