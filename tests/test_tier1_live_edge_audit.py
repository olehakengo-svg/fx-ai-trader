import pytest

from tools.tier1_live_edge_audit import (
    ALPHA_PRIME,
    BEV_WR,
    BONFERRONI_M,
    build_cell_records,
    filter_closed_oanda_live_trades,
    has_oanda_fill,
    verdict_for_cells,
)


def _trade(strategy, instrument, pnl, *, is_shadow=0, oanda_trade_id="oid", status="CLOSED"):
    return {
        "trade_id": f"{strategy}-{instrument}-{pnl}-{is_shadow}-{oanda_trade_id}",
        "entry_type": strategy,
        "instrument": instrument,
        "entry_time": "2026-05-01T09:00:00+00:00",
        "exit_time": "2026-05-01T09:30:00+00:00",
        "status": status,
        "outcome": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BREAKEVEN"),
        "pnl_pips": pnl,
        "is_shadow": is_shadow,
        "oanda_trade_id": oanda_trade_id,
    }


def test_filter_requires_live_oanda_closed_rows():
    rows = [
        _trade("gbp_deep_pullback", "GBP_USD", 3, is_shadow=0, oanda_trade_id="123"),
        _trade("gbp_deep_pullback", "GBP_USD", 3, is_shadow=1, oanda_trade_id="123"),
        _trade("gbp_deep_pullback", "GBP_USD", 3, is_shadow=0, oanda_trade_id=""),
        _trade("gbp_deep_pullback", "GBP_USD", 3, is_shadow=0, oanda_trade_id="123", status="OPEN"),
    ]

    live = filter_closed_oanda_live_trades(rows)

    assert len(live) == 1
    assert has_oanda_fill(live[0]) is True
    assert live[0]["is_shadow"] == 0


def test_build_records_uses_locked_five_cells_and_pair_bev_wr():
    rows = [
        _trade("gbp_deep_pullback", "GBP_USD", 5),
        _trade("gbp_deep_pullback", "GBP_USD", -3),
        _trade("session_time_bias", "USD_JPY", 2),
        _trade("unrelated", "USD_JPY", 100),
    ]
    cells = build_cell_records(filter_closed_oanda_live_trades(rows))

    assert len(cells) == BONFERRONI_M
    by_id = {cell["cell_id"]: cell for cell in cells}
    assert by_id["gbp_deep_pullback|GBP_USD"]["bev_wr"] == pytest.approx(BEV_WR["GBP_USD"])
    assert by_id["session_time_bias|USD_JPY"]["bev_wr"] == pytest.approx(BEV_WR["USD_JPY"])
    assert all(cell["alpha_prime"] == pytest.approx(ALPHA_PRIME) for cell in cells)


def test_delta_from_bt_is_calculated_for_each_cell():
    rows = [
        _trade("gbp_deep_pullback", "GBP_USD", 5),
        _trade("gbp_deep_pullback", "GBP_USD", -3),
    ]
    cell = next(
        c
        for c in build_cell_records(filter_closed_oanda_live_trades(rows))
        if c["cell_id"] == "gbp_deep_pullback|GBP_USD"
    )

    assert cell["wr"] == pytest.approx(0.5)
    assert cell["ev_pips"] == pytest.approx(1.0)
    assert cell["delta_wr"] == pytest.approx(0.5 - 0.75)
    assert cell["delta_ev"] == pytest.approx(1.0 - 1.064)
    assert cell["delta_pf"] == pytest.approx((5 / 3) - 2.00)


def test_bonferroni_m5_positive_edge_gate_accepts_strong_cell():
    rows = [_trade("session_time_bias", "USD_JPY", 2, oanda_trade_id=f"w{i}") for i in range(60)]
    rows += [_trade("session_time_bias", "USD_JPY", -1, oanda_trade_id=f"l{i}") for i in range(5)]
    cell = next(
        c
        for c in build_cell_records(filter_closed_oanda_live_trades(rows))
        if c["cell_id"] == "session_time_bias|USD_JPY"
    )

    assert cell["n"] == 65
    assert cell["wilson_lo"] > BEV_WR["USD_JPY"]
    assert cell["bonferroni_p"] < ALPHA_PRIME
    assert cell["pf"] >= 1.10
    assert cell["accept_cell"] is True


def test_verdict_requires_two_accept_cells():
    cells = []
    for i in range(BONFERRONI_M):
        cells.append(
            {
                "n": 40,
                "wilson_lo": 0.20,
                "bev_wr": 0.35,
                "bonferroni_p": 1.0,
                "accept_cell": False,
            }
        )
    cells[0]["accept_cell"] = True
    cells[0]["wilson_lo"] = 0.80
    cells[0]["bonferroni_p"] = 0.001

    verdict, reasons = verdict_for_cells(cells)
    assert verdict == "NEEDS_MORE_EVIDENCE"
    assert "only 1 cell" in reasons[0]

    cells[1]["accept_cell"] = True
    cells[1]["wilson_lo"] = 0.80
    cells[1]["bonferroni_p"] = 0.001
    assert verdict_for_cells(cells)[0] == "ACCEPT"
