import pytest

from tools.r2_tier1_hour_bucket_extension import (
    apply_stop_ids,
    build_extension_candidates,
    greedy_extension,
    run_audit,
    verdict_for,
)


def _trade(
    strategy,
    instrument,
    pnl,
    *,
    hour=9,
    outcome=None,
    is_shadow=0,
    oanda_trade_id="150360",
    trade_id=None,
    entry_time=None,
):
    if outcome is None:
        outcome = "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BREAKEVEN")
    return {
        "trade_id": trade_id or f"{strategy}-{instrument}-{hour}-{pnl}-{is_shadow}-{oanda_trade_id}",
        "entry_type": strategy,
        "instrument": instrument,
        "entry_time": entry_time or f"2026-05-01T{hour:02d}:00:00+00:00",
        "exit_time": entry_time or f"2026-05-01T{hour:02d}:30:00+00:00",
        "status": "CLOSED",
        "outcome": outcome,
        "pnl_pips": pnl,
        "is_shadow": is_shadow,
        "oanda_trade_id": oanda_trade_id,
    }


def test_build_extension_candidates_includes_tier1_pair_and_hour_overlay_n3():
    rows = [
        _trade("gbp_deep_pullback", "GBP_USD", -4, hour=6, trade_id="t1"),
        _trade("gbp_deep_pullback", "GBP_USD", -3, hour=7, trade_id="t2"),
        _trade("gbp_deep_pullback", "GBP_USD", 1, hour=8, trade_id="t3"),
        _trade("bb_rsi_reversion", "USD_JPY", -2, hour=16, trade_id="h1"),
        _trade("bb_rsi_reversion", "USD_JPY", -2, hour=16, trade_id="h2"),
        _trade("bb_rsi_reversion", "USD_JPY", 1, hour=16, trade_id="h3"),
        _trade("small", "USD_JPY", -10, hour=1, trade_id="small"),
    ]

    candidates, m_add = build_extension_candidates(rows)

    assert m_add == 2
    assert {cell["cell_id"] for cell in candidates} == {
        "gbp_deep_pullback|GBP_USD",
        "bb_rsi_reversion|USD_JPY|16",
    }
    assert next(cell for cell in candidates if cell["dimension"] == "tier1_pair")["n"] == 3


def test_greedy_extension_stops_worst_negative_cell_until_kelly_recovers():
    rows = []
    rows += [_trade("gbp_deep_pullback", "GBP_USD", -10, hour=6, trade_id=f"bad{i}") for i in range(3)]
    rows += [_trade("good", "USD_JPY", 3, hour=9, trade_id=f"win{i}") for i in range(5)]
    rows += [_trade("good", "USD_JPY", -1, hour=10, trade_id=f"loss{i}") for i in range(2)]

    candidates, _m_add = build_extension_candidates(rows)
    selected, post = greedy_extension(rows, candidates, mc_iterations=1000, mc_horizon_days=60)

    stopped = [cell for cell in selected if cell["action"] == "STOP_OANDA"]
    assert [cell["cell_id"] for cell in stopped] == ["gbp_deep_pullback|GBP_USD"]
    assert post["kelly_raw"] >= 0
    assert verdict_for(post, selected) == "ACCEPT"


def test_protected_ssot_pair_is_not_demoted_even_as_negative_hour_overlay():
    rows = []
    rows += [_trade("fib_reversal", "USD_JPY", -3, hour=14, trade_id=f"fib{i}") for i in range(3)]
    rows += [_trade("good", "USD_JPY", 2, hour=9, trade_id=f"good{i}") for i in range(6)]
    candidates, _m_add = build_extension_candidates(rows)

    selected, _post = greedy_extension(rows, candidates, mc_iterations=1000, mc_horizon_days=60)
    fib = next(cell for cell in selected if cell["cell_id"] == "fib_reversal|USD_JPY|14")

    assert fib["action"] == "KEEP"
    assert fib["protected_pair_keep"] is True


def test_apply_stop_ids_removes_only_matching_trade_ids():
    rows = [
        _trade("a", "USD_JPY", -1, trade_id="stop"),
        _trade("b", "USD_JPY", 2, trade_id="keep"),
    ]

    assert [row["trade_id"] for row in apply_stop_ids(rows, {"stop"})] == ["keep"]


def test_run_audit_uses_true_live_only_and_writes_report(tmp_path):
    trades_path = tmp_path / "trades.json"
    base_path = tmp_path / "base.md"
    output_path = tmp_path / "report.md"
    payload = {
        "trades": [
            _trade("base_bad", "USD_JPY", -2, trade_id=f"base{i}") for i in range(5)
        ]
        + [_trade("gbp_deep_pullback", "GBP_USD", -3, hour=6, trade_id=f"tier{i}") for i in range(3)]
        + [_trade("good", "EUR_USD", 2, trade_id=f"good{i}") for i in range(8)]
        + [_trade("shadow", "USD_JPY", -99, is_shadow=1, trade_id="shadow")]
        + [_trade("flag", "USD_JPY", -99, oanda_trade_id="", trade_id="flag")]
    }
    trades_path.write_text(__import__("json").dumps(payload))
    base_path.write_text(
        "| rank | action | lot | keep | strategy | instrument | N |\n"
        "|---:|---|---:|---|---|---|---:|\n"
        "| 1 | STOP_OANDA | 0.0 |  | base_bad | USD_JPY | 5 |\n"
    )

    result = run_audit(
        trades_path=trades_path,
        base_demote_set_path=base_path,
        output_path=output_path,
        mc_iterations=1000,
        mc_horizon_days=60,
    )

    assert result["bucket_summary"]["TRUE_LIVE"]["n"] == 16
    assert result["bucket_summary"]["SHADOW"]["n"] == 1
    assert result["bucket_summary"]["FLAG_DRIFT"]["n"] == 1
    assert output_path.read_text().startswith("# R2 Tier 1 + hour-bucket extension")
