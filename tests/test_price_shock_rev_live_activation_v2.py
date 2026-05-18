from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone

from modules.demo_db import DemoDB
from modules.demo_trader import (
    DemoTrader,
    PRICE_SHOCK_REV_MIN_UNITS,
    PRICE_SHOCK_REV_TIER1_PAIRS,
    PRICE_SHOCK_REV_TIER1_TYPES,
)


PRICE_SHOCK_CASES = (
    ("price_shock_rev_eur_gbp_h1_long", "EUR_GBP"),
    ("price_shock_rev_eur_aud_h1_long", "EUR_AUD"),
    ("price_shock_rev_usd_cad_h1_long", "USD_CAD"),
    ("price_shock_rev_nzd_jpy_h1_long", "NZD_JPY"),
    ("price_shock_rev_aud_jpy_h1_long", "AUD_JPY"),
)


def _insert_closed_trade(
    db: DemoDB,
    *,
    trade_id: str,
    entry_type: str,
    instrument: str,
    pnl_pips: float,
    is_shadow: int = 0,
    when: datetime | None = None,
) -> None:
    when = when or datetime(2026, 5, 18, tzinfo=timezone.utc)
    ts = when.isoformat()
    outcome = "WIN" if pnl_pips > 0 else "LOSS"
    with db._safe_conn() as conn:
        conn.execute(
            """INSERT INTO demo_trades
               (trade_id, status, direction, entry_price, entry_time, exit_price,
                exit_time, sl, tp, pnl_pips, pnl_r, outcome, entry_type,
                confidence, is_shadow, oanda_trade_id, instrument)
               VALUES (?, 'CLOSED', 'BUY', 1.0, ?, 1.0, ?, 0.99, 1.01,
                       ?, 0.1, ?, ?, 70, ?, 'OANDA-LIVE', ?)""",
            (trade_id, ts, ts, pnl_pips, outcome, entry_type, is_shadow, instrument),
        )
        conn.commit()


def test_price_shock_rev_force_demote_removed_and_final_gate_keeps_live():
    trader = DemoTrader.__new__(DemoTrader)
    trader._add_log = lambda _msg: None

    assert PRICE_SHOCK_REV_TIER1_TYPES == {case[0] for case in PRICE_SHOCK_CASES}
    assert PRICE_SHOCK_REV_TIER1_PAIRS == set(PRICE_SHOCK_CASES)
    assert PRICE_SHOCK_REV_TIER1_TYPES.isdisjoint(DemoTrader._FORCE_DEMOTED)

    for entry_type, _instrument in PRICE_SHOCK_CASES:
        is_shadow, is_promoted, shadow_at_open = trader._apply_force_demoted_final_gate(
            entry_type=entry_type,
            is_shadow=False,
            is_promoted=True,
            shadow_at_open=False,
        )
        assert is_shadow is False
        assert is_promoted is True
        assert shadow_at_open is False


def test_price_shock_rev_pair_promoted_and_min_lot_literal():
    for entry_type, instrument in PRICE_SHOCK_CASES:
        assert (entry_type, instrument) in DemoTrader._PAIR_PROMOTED
        assert DemoTrader._price_shock_rev_min_units(entry_type, instrument) == PRICE_SHOCK_REV_MIN_UNITS
        assert DemoTrader._lot_floor_ratio_for(
            entry_type=entry_type,
            instrument=instrument,
            configured_pair_boost=None,
            is_sentinel=False,
        ) == PRICE_SHOCK_REV_MIN_UNITS / 10000


def test_hourly_shadow_always_excludes_price_shock_but_keeps_ksb_dmb():
    from strategies.hourly import HourlyEngine

    assert PRICE_SHOCK_REV_TIER1_TYPES.isdisjoint(HourlyEngine._shadow_always)
    assert "keltner_squeeze_breakout" in HourlyEngine._shadow_always
    assert "donchian_momentum_breakout" in HourlyEngine._shadow_always


def test_eur_gbp_eur_aud_shared_lock_blocks_both_directions(tmp_path):
    db = DemoDB(str(tmp_path / "shared-lock.db"))
    eurgbp_id = db.open_trade(
        "BUY", 0.86, 0.85, 0.88, "price_shock_rev_eur_gbp_h1_long",
        70, tf="1h", mode="daytrade_1h_eurgbp", instrument="EUR_GBP",
        is_shadow=False, oanda_trade_id="OANDA-EG",
    )
    open_trades = db.get_open_trades()
    assert eurgbp_id
    assert DemoTrader._eur_base_shock_lock_reason(
        "price_shock_rev_eur_aud_h1_long", open_trades
    ) == "eur_base_shock_lock(price_shock_rev_eur_aud_h1_long_vs_price_shock_rev_eur_gbp_h1_long)"

    db.close_trade(eurgbp_id, 0.87)
    euraud_id = db.open_trade(
        "BUY", 1.65, 1.63, 1.70, "price_shock_rev_eur_aud_h1_long",
        70, tf="1h", mode="daytrade_1h_euraud", instrument="EUR_AUD",
        is_shadow=False, oanda_trade_id="OANDA-EA",
    )
    open_trades = db.get_open_trades()
    assert euraud_id
    assert DemoTrader._eur_base_shock_lock_reason(
        "price_shock_rev_eur_gbp_h1_long", open_trades
    ) == "eur_base_shock_lock(price_shock_rev_eur_gbp_h1_long_vs_price_shock_rev_eur_aud_h1_long)"


def test_live_watchdog_demotes_from_real_sqlite_history(tmp_path):
    import tools.price_shock_rev_live_watchdog as watchdog

    db_path = tmp_path / "watchdog.db"
    db = DemoDB(str(db_path))
    for i in range(10):
        _insert_closed_trade(
            db,
            trade_id=f"loss-{i}",
            entry_type="price_shock_rev_usd_cad_h1_long",
            instrument="USD_CAD",
            pnl_pips=-1.0,
        )
    _insert_closed_trade(
        db,
        trade_id="shadow-ignore",
        entry_type="price_shock_rev_usd_cad_h1_long",
        instrument="USD_CAD",
        pnl_pips=100.0,
        is_shadow=1,
    )

    trades = watchdog.load_trades_from_sqlite(db_path)
    results, demotions, exit_code = watchdog.run(trades)
    state_path = tmp_path / "price_shock_rev_auto_demotions.json"
    watchdog.write_state(state_path, demotions)

    cell = results["price_shock_rev_usd_cad_h1_long x USD_CAD"]
    assert cell["metrics"]["n"] == 10
    assert cell["metrics"]["ev_pips"] == -1.0
    assert cell["verdict"] == "DEMOTE"
    assert exit_code == 1
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["demotions"][0]["entry_type"] == "price_shock_rev_usd_cad_h1_long"


def test_promote_evaluator_bonferroni_and_six_week_ev_from_real_sqlite(tmp_path):
    import tools.price_shock_rev_promote_evaluator as evaluator

    db_path = tmp_path / "promote.db"
    db = DemoDB(str(db_path))
    start = datetime(2026, 5, 18, tzinfo=timezone.utc)
    for i in range(30):
        _insert_closed_trade(
            db,
            trade_id=f"win-{i}",
            entry_type="price_shock_rev_aud_jpy_h1_long",
            instrument="AUD_JPY",
            pnl_pips=2.0 if i < 28 else -1.0,
            when=start + timedelta(days=i * 2),
        )

    trades = evaluator.load_trades_from_sqlite(db_path)
    cells, proposals = evaluator.run(trades)
    cell = cells["price_shock_rev_aud_jpy_h1_long x AUD_JPY"]
    metrics = cell["metrics"]

    expected_raw = sum(math.comb(30, k) * (0.5 ** 30) for k in range(28, 31))
    assert metrics["n"] == 30
    assert metrics["wins"] == 28
    assert abs(metrics["p_value_raw"] - expected_raw) < 1e-12
    assert abs(metrics["p_value_bonferroni"] - min(1.0, expected_raw * 5)) < 1e-12
    assert metrics["wilson_lower"] >= 0.50
    assert metrics["six_week_ev_all_positive"] is True
    assert cell["verdict"] == "PROPOSE_RAMP"
    assert [(p["entry_type"], p["instrument"]) for p in proposals] == [
        ("price_shock_rev_aud_jpy_h1_long", "AUD_JPY")
    ]
