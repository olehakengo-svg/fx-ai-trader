import pytest

from tools.gate_progression_audit import (
    compare_risk_dashboard,
    filter_closed_live_trades,
    portfolio_simulation,
    summarize_trades,
    verdict_for,
)


def _trade(entry_type, pnl, outcome, is_shadow=0, instrument="USD_JPY", hour=9):
    return {
        "trade_id": f"{entry_type}-{pnl}-{outcome}-{is_shadow}",
        "entry_type": entry_type,
        "instrument": instrument,
        "outcome": outcome,
        "pnl_pips": pnl,
        "status": "CLOSED",
        "is_shadow": is_shadow,
        "entry_time": f"2026-05-01T{hour:02d}:00:00+00:00",
        "exit_time": f"2026-05-01T{hour:02d}:30:00+00:00",
    }


def test_filter_closed_live_trades_keeps_live_decided_rows_only():
    rows = [
        _trade("live", 10, "WIN", is_shadow=0),
        _trade("xau", -100, "LOSS", is_shadow=0, instrument="XAU_USD"),
        _trade("shadow", 10, "WIN", is_shadow=1),
        {**_trade("open", 10, "WIN", is_shadow=0), "status": "OPEN"},
        _trade("bad_outcome", 10, "OPEN", is_shadow=0),
        {**_trade("null_pnl", 0, "WIN", is_shadow=0), "pnl_pips": None},
    ]

    filtered = filter_closed_live_trades({"trades": rows})

    assert [r["entry_type"] for r in filtered] == ["live"]


def test_summarize_trades_computes_aggregate_gate_metrics():
    rows = [
        _trade("s1", 12, "WIN"),
        _trade("s1", 8, "WIN"),
        _trade("s1", -10, "LOSS"),
        _trade("s2", -6, "LOSS"),
        _trade("s2", 0, "BREAKEVEN"),
    ]

    summary = summarize_trades(rows, mc_iterations=100, mc_horizon_days=60)
    aggregate = summary["aggregate"]

    assert aggregate["n"] == 5
    assert aggregate["wins"] == 2
    assert aggregate["losses"] == 2
    assert aggregate["wr"] == pytest.approx(0.4)
    assert aggregate["ev_pips"] == pytest.approx(0.8)
    assert aggregate["pf"] == pytest.approx(1.25)
    assert aggregate["kelly"] == pytest.approx(0.0)
    assert "s1" in summary["strategies"]
    assert summary["strategies"]["s1"]["n"] == 3


def test_verdict_prefers_more_evidence_when_live_n_below_accept_floor():
    aggregate = {
        "n": 99,
        "kelly": 0.20,
        "mc_ruin_60d": 0.10,
        "wilson_lo": 0.60,
        "ev_pips": 1.0,
        "pf": 1.4,
        "max_dd_pct": 0.05,
    }

    verdict, reasons = verdict_for(aggregate)

    assert verdict == "NEEDS_MORE_EVIDENCE"
    assert any("N<100" in reason for reason in reasons)


def test_verdict_rejects_negative_ev_and_low_wilson():
    aggregate = {
        "n": 120,
        "kelly": 0.0,
        "mc_ruin_60d": 0.50,
        "wilson_lo": 0.40,
        "ev_pips": -0.1,
        "pf": 0.9,
        "max_dd_pct": 0.05,
    }

    verdict, reasons = verdict_for(aggregate)

    assert verdict == "REJECT"
    assert any("EV<0" in reason for reason in reasons)


def test_compare_risk_dashboard_accepts_nested_api_shape():
    local = {"kelly": 0.1234, "mc_ruin_60d": 0.4567}
    risk = {
        "kelly": {"full_kelly": 0.12},
        "monte_carlo": {"ruin_probability": 0.45, "n_trades_forward": 300},
    }

    comparison = compare_risk_dashboard(local, risk)

    assert comparison["kelly"]["within_5pct"] is True
    assert comparison["mc_ruin"]["within_5pct"] is True
    assert comparison["api_mc_n_trades_forward"] == 300


def test_portfolio_simulation_promotes_s2_shadow_without_mutating_baseline():
    live = [_trade("live_a", 10, "WIN"), _trade("live_a", -5, "LOSS")]
    shadow = [_trade("turtle_s2", 10, "WIN", is_shadow=1)]

    result = portfolio_simulation(live, shadow, promote_entry_contains="s2", mc_iterations=50)

    assert result["added_shadow_n"] == 1
    assert result["baseline"]["n"] == 2
    assert result["with_promoted_shadow"]["n"] == 3
