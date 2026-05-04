from __future__ import annotations

from tools import tier1_routing_rca as rca


def _row(
    *,
    demo_trade_id: str,
    entry_type: str,
    instrument: str = "GBP_USD",
    bridge_status: str,
    block_reason: str = "",
    oanda_trade_id: str = "",
    timestamp: str = "2026-04-10T00:00:00Z",
    is_live: bool = True,
) -> dict:
    return {
        "timestamp": timestamp,
        "demo_trade_id": demo_trade_id,
        "entry_type": entry_type,
        "instrument": instrument,
        "bridge_status": bridge_status,
        "block_reason": block_reason,
        "oanda_trade_id": oanda_trade_id,
        "is_live": is_live,
    }


def test_sent_strategy_rows_are_not_polluted_by_filled_mode_labels():
    rows = [
        _row(
            demo_trade_id="t1",
            entry_type="PYR_BUY",
            bridge_status="filled",
            oanda_trade_id="OANDA1",
        ),
        _row(
            demo_trade_id="t1",
            entry_type="gbp_deep_pullback",
            bridge_status="sent",
        ),
        _row(
            demo_trade_id="t2",
            entry_type="gbp_deep_pullback",
            bridge_status="blocked",
            block_reason="spread_too_wide",
        ),
    ]

    result = rca.analyze_audit_rows(rows)
    cell = result["cells"][("gbp_deep_pullback", "GBP_USD")]

    assert cell["sent_n"] == 1
    assert cell["filled_n"] == 1
    assert cell["live_block_n"] == 1
    assert ("PYR_BUY", "GBP_USD") not in result["cells"]


def test_block_reason_distribution_and_cutoff_split_are_computed():
    rows = [
        _row(
            demo_trade_id="pre1",
            entry_type="trendline_sweep",
            bridge_status="blocked",
            block_reason="phase_gate",
            timestamp="2026-04-07T23:59:00Z",
        ),
        _row(
            demo_trade_id="post1",
            entry_type="trendline_sweep",
            bridge_status="blocked",
            block_reason="phase_gate",
            timestamp="2026-04-08T00:00:00Z",
        ),
        _row(
            demo_trade_id="post2",
            entry_type="trendline_sweep",
            bridge_status="skipped",
            block_reason="pair_demoted(GBP_USD)",
            timestamp="2026-04-09T00:00:00Z",
            is_live=False,
        ),
    ]

    result = rca.analyze_audit_rows(rows)
    cell = result["cells"][("trendline_sweep", "GBP_USD")]

    assert cell["live_block_n"] == 2
    assert cell["shadow_block_n"] == 1
    assert cell["block_reasons"]["phase_gate"] == 2
    assert cell["block_reasons"]["pair_demoted"] == 1
    assert cell["periods"]["pre"]["live_block_n"] == 1
    assert cell["periods"]["post"]["live_block_n"] == 1
    assert cell["periods"]["post"]["shadow_block_n"] == 1


def test_shadow_tracking_is_separate_from_live_gate_blocks():
    rows = [
        _row(
            demo_trade_id="s1",
            entry_type="session_time_bias",
            instrument="GBP_USD",
            bridge_status="skipped",
            block_reason="shadow_tracking",
            is_live=False,
        ),
        _row(
            demo_trade_id="l1",
            entry_type="session_time_bias",
            instrument="GBP_USD",
            bridge_status="blocked",
            block_reason="aggregate_kelly_negative",
            is_live=True,
        ),
    ]

    result = rca.analyze_audit_rows(rows)
    cell = result["cells"][("session_time_bias", "GBP_USD")]

    assert cell["shadow_block_reasons"] == {"shadow_tracking": 1}
    assert cell["live_block_reasons"] == {"aggregate_kelly_negative": 1}
    assert result["shadow_overall_reasons"] == {"shadow_tracking": 1}
    assert result["live_overall_reasons"] == {"aggregate_kelly_negative": 1}
