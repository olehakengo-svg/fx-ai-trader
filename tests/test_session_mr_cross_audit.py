import math
import os
from types import SimpleNamespace

import pandas as pd

from scripts.run_session_mr_cross_wave1_audit_bt import (
    ExitPolicy,
    PAIR_SPREAD_PIPS,
    _simulate_exit,
    pair_spread_pips,
)


def _df(rows):
    idx = pd.date_range("2026-05-01T00:00:00Z", periods=len(rows), freq="5min")
    return pd.DataFrame(rows, index=idx)


def _sig(side="BUY", entry=1.0000, sl=0.9990, tp=1.0010):
    return SimpleNamespace(
        side=side,
        entry=entry,
        sl=sl,
        tp=tp,
        signal_ts=pd.Timestamp("2026-05-01T00:00:00Z"),
        entry_ts=pd.Timestamp("2026-05-01T00:05:00Z"),
        friction_pips=0.6,
        friction_source="params.entry_cost_pips_fallback",
    )


def test_pair_spread_pips_lookup_uses_pre_registered_cross_table():
    expected = {
        "EUR_NZD": 3.0,
        "AUD_NZD": 2.5,
        "AUD_CAD": 2.5,
        "NZD_CAD": 5.0,
        "EUR_GBP": 1.2,
    }
    assert PAIR_SPREAD_PIPS == expected
    for pair, spread in expected.items():
        assert pair_spread_pips(pair) == (spread, "PAIR_SPREAD_PIPS")


def test_sl_first_hard_ordering_wins_same_bar_conflict():
    data = _df([
        {"Open": 1.0000, "High": 1.0020, "Low": 0.9980, "Close": 1.0000},
    ])
    trade = _simulate_exit(
        data,
        0,
        _sig("BUY", entry=1.0000, sl=0.9990, tp=1.0010),
        "EUR_NZD",
        ExitPolicy("audit_ab", pair_friction=True, sl_first_hard=True, bid_ask=False),
    )
    assert trade["exit_reason"] == "SL"
    assert trade["same_bar_both_hit"] is True
    assert trade["net_pips"] < 0


def test_bid_ask_adjustment_buy_entry_and_tp_exit_signs():
    data = _df([
        {"Open": 1.0000, "High": 1.0020, "Low": 0.9995, "Close": 1.0005},
    ])
    sig = _sig("BUY", entry=1.0000, sl=0.9980, tp=1.0010)
    trade = _simulate_exit(
        data,
        0,
        sig,
        "EUR_NZD",
        ExitPolicy("audit_abc", pair_friction=True, sl_first_hard=True, bid_ask=True),
    )
    half = PAIR_SPREAD_PIPS["EUR_NZD"] / 2 / 10000
    assert trade["entry"] == sig.entry + half
    assert trade["exit"] == sig.tp - half
    assert trade["friction_pips"] == 0.0
    assert math.isclose(trade["net_pips"], 7.0, abs_tol=1e-9)


def test_bid_ask_adjustment_sell_entry_and_tp_exit_signs():
    data = _df([
        {"Open": 1.0000, "High": 1.0005, "Low": 0.9980, "Close": 0.9995},
    ])
    sig = _sig("SELL", entry=1.0000, sl=1.0020, tp=0.9990)
    trade = _simulate_exit(
        data,
        0,
        sig,
        "EUR_NZD",
        ExitPolicy("audit_abc", pair_friction=True, sl_first_hard=True, bid_ask=True),
    )
    half = PAIR_SPREAD_PIPS["EUR_NZD"] / 2 / 10000
    assert trade["entry"] == sig.entry - half
    assert trade["exit"] == sig.tp + half
    assert trade["friction_pips"] == 0.0
    assert math.isclose(trade["net_pips"], 7.0, abs_tol=1e-9)


def test_variant_trade_schema_contains_required_audit_fields():
    data = _df([
        {"Open": 1.0000, "High": 1.0020, "Low": 0.9995, "Close": 1.0005},
    ])
    trade = _simulate_exit(
        data,
        0,
        _sig(),
        "EUR_NZD",
        ExitPolicy("audit_a", pair_friction=True, sl_first_hard=False, bid_ask=False),
    )
    assert {
        "variant",
        "entry",
        "mid_entry",
        "exit",
        "exit_reason",
        "same_bar_both_hit",
        "raw_pips",
        "friction_pips",
        "spread_pips",
        "friction_source",
        "net_pips",
    } <= set(trade)


def test_baseline_exit_matches_existing_wave1_runner_exit():
    before = {k: os.environ.get(k) for k in ("BT_MODE", "BT_REQUIRE_MASSIVE_CACHE", "NO_AUTOSTART")}
    import scripts.run_session_mr_cross_wave1_bt as baseline_runner

    for key, value in before.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    data = _df([
        {"Open": 1.0000, "High": 1.0020, "Low": 0.9995, "Close": 1.0005},
    ])
    sig = _sig("BUY", entry=1.0000, sl=0.9980, tp=1.0010)
    new_trade = _simulate_exit(
        data,
        0,
        sig,
        "EUR_NZD",
        ExitPolicy("baseline", pair_friction=False, sl_first_hard=False, bid_ask=False),
    )
    old_trade = baseline_runner._simulate_exit(data, 0, sig, "EUR_NZD")
    for key in ("exit_reason", "entry", "exit", "raw_pips", "friction_pips", "net_pips"):
        assert new_trade[key] == old_trade[key]
