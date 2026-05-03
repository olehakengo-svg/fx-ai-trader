from __future__ import annotations

from tools import oanda_passthrough_gap_audit as mod


def _row(**overrides):
    base = mod.Row(
        trade_id="t1",
        entry_time="2026-04-27T03:00:00+00:00",
        exit_time="2026-04-27T03:30:00+00:00",
        entry_type="bb_rsi_reversion",
        instrument="USD_JPY",
        direction="BUY",
        confidence=60.0,
        regime="range_tight",
        pnl_pips=-3.0,
        outcome="LOSS",
        mode="scalp",
        gate_group="label_only",
        mtf_alignment="aligned",
        mtf_gate_action="none",
        close_reason="SL_HIT",
        is_shadow=0,
        oanda_trade_id="",
        reasons="",
    )
    data = base.__dict__.copy()
    data.update(overrides)
    return mod.Row(**data)


def test_strict_live_trade_requires_nonempty_oanda_id():
    assert mod.strict_live_trade(_row(oanda_trade_id="123"))
    assert not mod.strict_live_trade(_row(oanda_trade_id=""))


def test_choose_cutoff_prefers_exact_gap_even_with_small_count_drift():
    rows = [
        _row(trade_id="a", exit_time="2026-05-01T00:00:00+00:00", is_shadow=0, oanda_trade_id=""),
        _row(trade_id="b", exit_time="2026-04-30T00:00:00+00:00", is_shadow=0, oanda_trade_id="x"),
        _row(trade_id="c", exit_time="2026-04-29T00:00:00+00:00", is_shadow=1, oanda_trade_id=""),
    ]
    choice = mod.choose_cutoff(rows)
    assert choice.exit_time == "2026-04-30T00:00:00+00:00"


def test_classify_gap_row_uses_tier_shadow_markers():
    tier_ctx = {
        "pair_demoted": [["bb_rsi_reversion", "USD_JPY"]],
        "scalp_sentinel": ["bb_rsi_reversion"],
        "force_demoted": [],
        "universal_sentinel": [],
    }
    classification, evidence = mod.classify_gap_row(_row(), tier_ctx)
    assert classification == "H3_FLAG_DRIFT"
    assert "pair_demoted" in evidence


def test_verdict_prefers_flag_drift_when_h3_dominates():
    summary = {"H3_FLAG_DRIFT": {"n": 39, "wins": 10, "wr": 0.25, "mean_pnl": -1.0, "total_pnl": -39.0}}
    assert mod.verdict_for(summary) == "FLAG_DRIFT_BUG"
