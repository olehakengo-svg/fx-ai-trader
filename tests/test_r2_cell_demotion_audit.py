import pytest

from tools.r2_cell_demotion_audit import (
    apply_actions,
    build_cell_records,
    classify_cells,
    filter_closed_live_trades,
    summarize_trades,
)


def _trade(strategy, instrument, hour, pnl, outcome=None, is_shadow=0, trade_id=None):
    if outcome is None:
        outcome = "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BREAKEVEN")
    suffix = trade_id or f"{strategy}-{instrument}-{hour}-{pnl}-{is_shadow}"
    return {
        "trade_id": suffix,
        "entry_type": strategy,
        "instrument": instrument,
        "entry_time": f"2026-05-01T{hour:02d}:00:00+00:00",
        "exit_time": f"2026-05-01T{hour:02d}:30:00+00:00",
        "status": "CLOSED",
        "outcome": outcome,
        "pnl_pips": pnl,
        "is_shadow": is_shadow,
    }


def test_filter_closed_live_trades_excludes_shadow_open_xau_and_null_pnl():
    rows = [
        _trade("s", "USD_JPY", 1, 1, is_shadow=0),
        _trade("shadow", "USD_JPY", 1, 1, is_shadow=1),
        {**_trade("open", "USD_JPY", 1, 1), "status": "OPEN"},
        _trade("xau", "XAU_USD", 1, -100),
        {**_trade("null", "USD_JPY", 1, 0), "pnl_pips": None},
    ]

    filtered = filter_closed_live_trades({"trades": rows})

    assert [row["entry_type"] for row in filtered] == ["s"]


def test_build_cell_records_and_classify_stop_lot_half_keep_watch():
    rows = []
    rows += [_trade("stop", "USD_JPY", 1, -5, trade_id=f"stop-l-{i}") for i in range(5)]
    rows += [_trade("stop", "USD_JPY", 1, 1, trade_id="stop-w-1")]
    rows += [_trade("half", "USD_JPY", 2, -1, trade_id=f"half-l-{i}") for i in range(8)]
    rows += [_trade("half", "USD_JPY", 2, 1, trade_id=f"half-w-{i}") for i in range(2)]
    rows += [_trade("keep", "USD_JPY", 3, 2, trade_id=f"keep-w-{i}") for i in range(6)]
    rows += [_trade("keep", "USD_JPY", 3, -1, trade_id=f"keep-l-{i}") for i in range(2)]
    rows += [_trade("watch", "USD_JPY", 4, -1, trade_id=f"watch-l-{i}") for i in range(4)]

    cells = build_cell_records(rows)
    classified = classify_cells(cells, max_cuts=30)
    actions = {cell["cell_id"]: cell["action"] for cell in classified}

    assert actions["stop|USD_JPY|01"] == "STOP_OANDA"
    assert actions["half|USD_JPY|02"] == "LOT_HALF"
    assert actions["keep|USD_JPY|03"] == "KEEP"
    assert actions["watch|USD_JPY|04"] == "WATCH"


def test_apply_actions_removes_stop_and_halves_lot_pnl():
    rows = [
        _trade("stop", "USD_JPY", 1, -5, trade_id="stop-1"),
        _trade("half", "USD_JPY", 2, -4, trade_id="half-1"),
        _trade("keep", "USD_JPY", 3, 8, trade_id="keep-1"),
    ]
    cells = [
        {"cell_id": "stop|USD_JPY|01", "action": "STOP_OANDA", "trade_ids": ["stop-1"]},
        {"cell_id": "half|USD_JPY|02", "action": "LOT_HALF", "trade_ids": ["half-1"]},
        {"cell_id": "keep|USD_JPY|03", "action": "KEEP", "trade_ids": ["keep-1"]},
    ]

    adjusted = apply_actions(rows, cells)

    assert [row["trade_id"] for row in adjusted] == ["half-1", "keep-1"]
    assert adjusted[0]["pnl_pips"] == pytest.approx(-2)
    assert summarize_trades(adjusted, mc_iterations=1000, mc_horizon_days=60)["aggregate"]["n"] == 2
