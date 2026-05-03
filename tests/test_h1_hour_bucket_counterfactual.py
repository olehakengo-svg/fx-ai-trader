from __future__ import annotations

from tools import h1_hour_bucket_counterfactual as mod


def _row(**overrides):
    row = {
        "entry_type": "fib_reversal",
        "instrument": "USD_JPY",
        "entry_time": "2026-02-10T13:00:00+00:00",
        "outcome": "WIN",
        "pnl_pips": 5.0,
        "is_shadow": 1,
        "oanda_trade_id": "",
    }
    row.update(overrides)
    return row


def test_hour_bucket_boundaries():
    assert mod.hour_bucket_from_ts("2026-02-01T00:00:00+00:00") == "Asia"
    assert mod.hour_bucket_from_ts("2026-02-01T06:59:59+00:00") == "Asia"
    assert mod.hour_bucket_from_ts("2026-02-01T07:00:00+00:00") == "London"
    assert mod.hour_bucket_from_ts("2026-02-01T12:59:59+00:00") == "London"
    assert mod.hour_bucket_from_ts("2026-02-01T13:00:00+00:00") == "NY-overlap"
    assert mod.hour_bucket_from_ts("2026-02-01T16:59:59+00:00") == "NY-overlap"
    assert mod.hour_bucket_from_ts("2026-02-01T17:00:00+00:00") == "Off"
    assert mod.hour_bucket_from_ts("2026-02-01T23:59:59+00:00") == "Off"


def test_strict_live_filter_requires_oanda_id():
    assert mod.strict_live_trade(_row(is_shadow=0, oanda_trade_id="123", outcome="WIN"))
    assert not mod.strict_live_trade(_row(is_shadow=0, oanda_trade_id="", outcome="WIN"))
    assert not mod.strict_live_trade(_row(is_shadow=1, oanda_trade_id="123", outcome="WIN"))


def test_new_bucket_decision_paths():
    pass_stats = {"n": 30, "wr_wilson_lo": 0.41, "ev_ci_lo": 0.01}
    fail_stats = {"n": 30, "wr_wilson_lo": 0.30, "ev_ci_lo": -0.10}
    thin_stats = {"n": 29, "wr_wilson_lo": 0.80, "ev_ci_lo": 0.20}
    assert mod.new_bucket_decision(pass_stats, "live", False) == ("live", "bucket_pass")
    assert mod.new_bucket_decision(fail_stats, "live", False) == ("shadow", "bucket_fail_demote_to_shadow")
    assert mod.new_bucket_decision(fail_stats, "shadow", False) == ("demoted", "bucket_fail_demote_from_shadow")
    assert mod.new_bucket_decision(thin_stats, "live", False) == ("live", "insufficient_data")
    assert mod.new_bucket_decision(fail_stats, "live", True) == ("live", "grandfather")


def test_split_label_range_uses_is_end_as_oos_start():
    is_label, oos_label = mod.split_label_range("2026-02-01", "2026-05-01", "2026-04-01")
    assert is_label == "IS `2026-02-01` to `2026-03-31`"
    assert oos_label == "OOS `2026-04-01` to `2026-05-01`"


def test_evaluate_counterfactual_counts_false_demotions(monkeypatch):
    rows = []
    monkeypatch.setattr(
        mod,
        "strategy_shadow_status",
        lambda shadow_rows: {"fib_reversal": {"status": "promoted"}},
    )
    for i in range(10):
        rows.append(_row(entry_type="fib_reversal", entry_time=f"2026-02-10T13:{i:02d}:00+00:00", pnl_pips=5.0, outcome="WIN"))
    for i in range(20):
        rows.append(_row(entry_type="fib_reversal", entry_time=f"2026-04-10T13:{i:02d}:00+00:00", pnl_pips=-5.0, outcome="LOSS"))
    result = mod.evaluate_counterfactual(rows, "2026-02-01", "2026-05-01", "2026-04-01")
    assert result["false_demote_den"] == 1
    assert result["false_demote_num"] == 1
    assert result["shadow_cells"][0]["new_status"] == "shadow"


def test_render_markdown_blocked_contains_evidence_request():
    md = mod.render_markdown(
        {"date_from": "2026-02-01", "date_to": "2026-05-01", "is_end": "2026-04-01"},
        blocked_error="Network error fetching x",
    )
    assert "Status: `BLOCKED`" in md
    assert "Evidence Needed Next" in md
