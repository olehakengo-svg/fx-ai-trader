import pytest

from tools.r2_strategy_instrument_counterfactual import (
    apply_lot_multipliers,
    build_strategy_instrument_cells,
    filter_true_live_rows,
    full_negative_stop_counterfactual,
    greedy_counterfactual,
    is_significant_keep,
    split_buckets,
    verdict_for,
)


def _trade(
    strategy,
    instrument,
    pnl,
    *,
    outcome=None,
    is_shadow=0,
    oanda_trade_id="150360",
    trade_id=None,
    mode="scalp",
    entry_time="2026-05-01T09:00:00+00:00",
):
    if outcome is None:
        outcome = "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BREAKEVEN")
    suffix = trade_id or f"{strategy}-{instrument}-{pnl}-{is_shadow}-{oanda_trade_id}"
    return {
        "trade_id": suffix,
        "entry_type": strategy,
        "instrument": instrument,
        "mode": mode,
        "entry_time": entry_time,
        "exit_time": "2026-05-01T09:30:00+00:00",
        "status": "CLOSED",
        "outcome": outcome,
        "pnl_pips": pnl,
        "is_shadow": is_shadow,
        "oanda_trade_id": oanda_trade_id,
    }


def test_true_live_filter_excludes_flag_drift_shadow_excluded_pair_and_pre_cutoff():
    payload = {
        "trades": [
            _trade("bb_rsi_reversion", "USD_JPY", 1, trade_id="true"),
            _trade("bb_rsi_reversion", "USD_JPY", -1, trade_id="flag", oanda_trade_id=""),
            _trade("bb_rsi_reversion", "USD_JPY", -1, trade_id="shadow", is_shadow=1),
            _trade("bb_rsi_reversion", "EUR_GBP", -1, trade_id="excluded-pair"),
            _trade("bb_rsi_reversion", "XAU_USD", -1, trade_id="excluded-xau"),
            _trade("bb_rsi_reversion", "USD_JPY", -1, trade_id="pre", entry_time="2026-04-07T23:59:59+00:00"),
        ]
    }

    buckets = split_buckets(payload)

    assert [row["trade_id"] for row in buckets["TRUE_LIVE"]] == ["true"]
    assert [row["trade_id"] for row in buckets["FLAG_DRIFT"]] == ["flag"]
    assert [row["trade_id"] for row in buckets["SHADOW"]] == ["shadow"]
    assert [row["trade_id"] for row in filter_true_live_rows(payload)] == ["true"]


def test_build_cells_uses_all_modes_and_strategy_instrument_m():
    rows = [
        _trade("bb_rsi_reversion", "USD_JPY", -1, trade_id="a", mode="daytrade"),
        _trade("bb_rsi_reversion", "USD_JPY", -1, trade_id="b", mode="scalp"),
        _trade("bb_rsi_reversion", "USD_JPY", 1, trade_id="c", mode="scalp_mtf"),
        _trade("bb_rsi_reversion", "USD_JPY", -1, trade_id="d", mode="tokyo"),
        _trade("bb_rsi_reversion", "USD_JPY", 1, trade_id="e", mode="london"),
        _trade("fib_reversal", "EUR_USD", 2, trade_id="f"),
        _trade("fib_reversal", "EUR_USD", 2, trade_id="g"),
        _trade("fib_reversal", "EUR_USD", -1, trade_id="h"),
        _trade("fib_reversal", "EUR_USD", 2, trade_id="i"),
        _trade("fib_reversal", "EUR_USD", -1, trade_id="j"),
        _trade("small_n", "USD_JPY", -100, trade_id="k"),
    ]

    cells = build_strategy_instrument_cells(rows)

    assert {cell["cell_id"] for cell in cells} == {
        "bb_rsi_reversion|USD_JPY",
        "fib_reversal|EUR_USD",
    }
    assert next(cell for cell in cells if cell["cell_id"] == "bb_rsi_reversion|USD_JPY")["n"] == 5
    assert all(cell["alpha_prime"] == pytest.approx(0.05 / 2) for cell in cells)


def test_apply_lot_multipliers_supports_keep_half_and_stop():
    rows = [
        _trade("bb_rsi_reversion", "USD_JPY", -10, trade_id="stop"),
        _trade("fib_reversal", "USD_JPY", -8, trade_id="half"),
        _trade("macdh_reversal", "USD_JPY", 6, trade_id="keep"),
    ]
    cells = [
        {"trade_ids": ["stop"], "lot_multiplier": 0.0},
        {"trade_ids": ["half"], "lot_multiplier": 0.5},
        {"trade_ids": ["keep"], "lot_multiplier": 1.0},
    ]

    adjusted = apply_lot_multipliers(rows, cells)

    assert [row["trade_id"] for row in adjusted] == ["half", "keep"]
    assert adjusted[0]["pnl_pips"] == pytest.approx(-4)
    assert adjusted[1]["pnl_pips"] == pytest.approx(6)


def test_significant_positive_cell_is_protected_from_greedy_demote():
    protected = [_trade("bb_rsi_reversion", "USD_JPY", 1, trade_id=f"p{i}") for i in range(30)]
    drag = [_trade("fib_reversal", "USD_JPY", -1, trade_id=f"d{i}") for i in range(5)]
    rows = protected + drag

    cells = build_strategy_instrument_cells(rows)
    protected_cell = next(cell for cell in cells if cell["cell_id"] == "bb_rsi_reversion|USD_JPY")
    assert is_significant_keep(protected_cell, m=len(cells)) is True

    selected, _post = greedy_counterfactual(rows, cells, mc_iterations=1000, mc_horizon_days=60)
    protected_selected = next(cell for cell in selected if cell["cell_id"] == "bb_rsi_reversion|USD_JPY")

    assert protected_selected["action"] == "KEEP"
    assert protected_selected["lot_multiplier"] == pytest.approx(1.0)
    assert protected_selected["significant_keep"] is True


def test_ssot_keep_cell_is_protected_even_when_pair_pnl_is_slightly_negative():
    rows = [_trade("fib_reversal", "USD_JPY", -1, trade_id=f"fib{i}") for i in range(5)]
    rows += [_trade("vix_carry_unwind", "USD_JPY", -2, trade_id=f"vix-l{i}") for i in range(4)]
    rows += [_trade("vix_carry_unwind", "USD_JPY", 1, trade_id="vix-w0")]

    cells = build_strategy_instrument_cells(rows)
    selected, _post = greedy_counterfactual(rows, cells, mc_iterations=1000, mc_horizon_days=60)
    fib = next(cell for cell in selected if cell["cell_id"] == "fib_reversal|USD_JPY")
    vix = next(cell for cell in selected if cell["cell_id"] == "vix_carry_unwind|USD_JPY")

    assert fib["action"] == "KEEP"
    assert fib["significant_keep"] is True
    assert vix["action"] == "STOP_OANDA"


def test_greedy_uses_half_when_half_reaches_positive_kelly():
    rows = []
    rows += [_trade("bb_rsi_reversion", "USD_JPY", -2, trade_id=f"drag-l{i}") for i in range(4)]
    rows += [_trade("bb_rsi_reversion", "USD_JPY", 1, trade_id=f"drag-w{i}") for i in range(2)]
    rows += [_trade("fib_reversal", "EUR_USD", 3, trade_id=f"good-w{i}") for i in range(2)]
    rows += [_trade("fib_reversal", "EUR_USD", -1, trade_id="good-l0")]

    cells = build_strategy_instrument_cells(rows)
    selected, post = greedy_counterfactual(rows, cells, mc_iterations=1000, mc_horizon_days=60)

    assert selected[0]["action"] == "LOT_HALF"
    assert selected[0]["lot_multiplier"] == pytest.approx(0.5)
    assert post["kelly_raw"] >= 0


def test_verdict_rejects_when_full_negative_stop_still_below_threshold():
    post = {"kelly_raw": -0.20, "mc_ruin_60d": 1.0}
    full_stop = {"kelly_raw": -0.06, "mc_ruin_60d": 1.0}

    assert verdict_for(post, full_stop, []) == "REJECT"


def test_full_negative_stop_removes_only_negative_n5_cells():
    rows = []
    rows += [_trade("bb_rsi_reversion", "USD_JPY", -1, trade_id=f"target{i}") for i in range(5)]
    rows += [_trade("fib_reversal", "EUR_USD", 1, trade_id=f"positive{i}") for i in range(5)]

    cells = build_strategy_instrument_cells(rows)
    full_stop = full_negative_stop_counterfactual(rows, cells, mc_iterations=1000, mc_horizon_days=60)

    assert full_stop["n"] == 5
    assert full_stop["total_pnl_pips"] == pytest.approx(5)
