import math

import pandas as pd

from tools.bt import s4_connors_raschke as s4


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


def test_setup_detection_uses_previous_utc_trading_day_ranges():
    daily = pd.DataFrame(
        {
            "open": [109.8, 110.0, 109.2],
            "high": [110.0, 110.1, 110.2],
            "low": [109.0, 109.0, 109.0],
            "close": [109.15, 109.95, 110.0],
        },
        index=pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07"], utc=True),
    )

    setups = s4.detect_setups(daily)

    assert setups[pd.Timestamp("2026-01-05", tz="UTC")] == "bearish"
    assert setups[pd.Timestamp("2026-01-06", tz="UTC")] is None
    assert setups[pd.Timestamp("2026-01-07", tz="UTC")] == "bullish"


def test_short_entry_requires_penetration_then_reclaim_close_next_bar_or_later():
    day = pd.Timestamp("2026-01-06", tz="UTC")
    bars = _bars(
        [
            ("2026-01-06 00:00", 109.20, 109.25, 108.98, 108.99),
            ("2026-01-06 00:05", 108.99, 109.10, 108.97, 109.02),
            ("2026-01-06 00:10", 109.02, 109.05, 108.99, 109.01),
        ]
    )
    setup = s4.SetupDay(
        day=pd.Timestamp("2026-01-05", tz="UTC"),
        direction="SHORT",
        high=110.0,
        low=109.0,
        open=109.8,
        close=109.15,
        next_day=day,
    )

    trade = s4.simulate_setup_day(
        bars,
        setup,
        penetration_tick=10,
        exit_method="fixed_time",
        session_boundary="H24",
    )

    assert trade is not None
    assert trade.direction == "SHORT"
    assert trade.entry_ts == pd.Timestamp("2026-01-06 00:05", tz="UTC")
    assert math.isclose(trade.entry_price, 109.02)


def test_trailing_exit_for_long_uses_half_previous_range_from_best_price():
    day = pd.Timestamp("2026-01-06", tz="UTC")
    bars = _bars(
        [
            ("2026-01-06 00:00", 110.05, 110.08, 110.00, 110.04),
            ("2026-01-06 00:05", 110.04, 110.05, 109.95, 109.98),
            ("2026-01-06 00:10", 109.98, 110.70, 109.97, 110.60),
            ("2026-01-06 00:15", 110.60, 110.65, 110.05, 110.10),
        ]
    )
    setup = s4.SetupDay(
        day=pd.Timestamp("2026-01-05", tz="UTC"),
        direction="LONG",
        high=110.0,
        low=109.0,
        open=109.1,
        close=109.9,
        next_day=day,
    )

    trade = s4.simulate_setup_day(
        bars,
        setup,
        penetration_tick=10,
        exit_method="50_trailing",
        session_boundary="H24",
    )

    assert trade is not None
    assert trade.exit_ts == pd.Timestamp("2026-01-06 00:15", tz="UTC")
    assert trade.exit_reason == "trail_50"
    assert math.isclose(trade.pnl_pip, 12.0)


def test_bonferroni_uses_locked_27_cells_and_bev_wr():
    assert s4.BONFERRONI_M == 27
    assert math.isclose(s4.bonferroni_adjusted_p(0.01), 0.27)
    assert math.isclose(s4.BEV_WR_USDJPY, 0.344)


def test_walk_forward_split_is_time_ordered_half_split():
    trades = [
        s4.Trade(
            entry_ts=pd.Timestamp(f"2026-01-0{i + 1} 00:00", tz="UTC"),
            exit_ts=pd.Timestamp(f"2026-01-0{i + 1} 01:00", tz="UTC"),
            direction="LONG",
            entry_price=100.0,
            exit_price=100.0 + pnl * 0.01,
            pnl_pip=pnl,
            pnl_pct=pnl / 10000,
            holding_minutes=60,
            setup_day=pd.Timestamp(f"2026-01-0{i + 1}", tz="UTC"),
            exit_reason="unit",
        )
        for i, pnl in enumerate([10.0, -5.0, 8.0, -2.0])
    ]

    wf = s4.walk_forward_50_50(trades)

    assert wf["is_n"] == 2
    assert wf["oos_n"] == 2
    assert math.isclose(wf["is_pf"], 2.0)
    assert math.isclose(wf["oos_pf"], 4.0)
    assert math.isclose(wf["oos_is_pf_ratio"], 2.0)


def test_catalog_without_definitive_eight_event_list_fails_loudly(tmp_path):
    catalog = tmp_path / "catalog.md"
    catalog.write_text("直近介入 2024-07-12 only\n", encoding="utf-8")

    try:
        s4.load_intervention_dates(catalog)
    except s4.InterventionListMissing as exc:
        assert "INTERVENTION_LIST_MISSING" in str(exc)
    else:
        raise AssertionError("expected InterventionListMissing")
