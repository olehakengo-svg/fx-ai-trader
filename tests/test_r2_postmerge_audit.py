from __future__ import annotations

import pytest

from tools.r2_postmerge_audit import (
    LOCKED_CELLS,
    evaluate,
    filter_true_live,
    load_prereg_snapshot,
)


LOCK_TS = "2026-05-11T00:00:00+00:00"


def _trade(strategy, instrument, hour, pnl, *, shadow=0, oanda="O-1", idx=0):
    return {
        "trade_id": f"{strategy}-{instrument}-{hour}-{idx}",
        "oanda_trade_id": oanda,
        "is_shadow": shadow,
        "status": "CLOSED",
        "outcome": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BREAKEVEN"),
        "entry_type": strategy,
        "instrument": instrument,
        "entry_time": f"2026-05-11T{hour}:00:00+00:00",
        "pnl_pips": pnl,
    }


def _prelock(value=-0.10):
    return {cell: value for cell in LOCKED_CELLS}


def test_bucket_separation_rejects_shadow_with_oanda_id_in_scope():
    strategy, instrument, hour = LOCKED_CELLS[0]
    payload = {"trades": [_trade(strategy, instrument, hour, 1.0, shadow=1, oanda="O-shadow")]}

    with pytest.raises(ValueError, match="SHADOW"):
        filter_true_live(payload, lock_deploy_ts=None, require_post_lock=False)


def test_xau_mixing_rejects_before_metric_computation():
    payload = {"trades": [_trade("gold", "XAU_USD", "01", 1.0)]}

    with pytest.raises(ValueError, match="XAU"):
        filter_true_live(payload, lock_deploy_ts=None, require_post_lock=False)


def test_accept_fixture_all_registered_criteria_pass():
    rows = []
    idx = 0
    for cell_idx, (strategy, instrument, hour) in enumerate(LOCKED_CELLS):
        pnls = [2.0, 2.0] if cell_idx < 10 else [2.0, -1.0]
        for pnl in pnls:
            rows.append(_trade(strategy, instrument, hour, pnl, idx=idx))
            idx += 1

    result = evaluate(filter_true_live({"trades": rows}, lock_deploy_ts=None), prelock=_prelock())

    assert result["verdict"] == "ACCEPT"
    assert set(result["bands"].values()) == {"ACCEPT"}


def test_reject_fixture_negative_raw_kelly_rejects():
    strategy, instrument, hour = LOCKED_CELLS[0]
    rows = []
    for idx in range(30):
        pnl = 1.0 if idx < 7 else -1.0
        rows.append(_trade(strategy, instrument, hour, pnl, idx=idx))

    result = evaluate(filter_true_live({"trades": rows}, lock_deploy_ts=None), prelock=_prelock())

    assert result["verdict"] == "REJECT"
    assert result["bands"]["aggregate_raw_kelly"] == "REJECT"
    assert result["aggregate"]["kelly_raw"] < -0.5


def test_n20_fixture_needs_more_evidence():
    rows = []
    for idx in range(20):
        strategy, instrument, hour = LOCKED_CELLS[idx % len(LOCKED_CELLS)]
        rows.append(_trade(strategy, instrument, hour, 1.0, idx=idx))

    result = evaluate(filter_true_live({"trades": rows}, lock_deploy_ts=None), prelock=_prelock())

    assert result["verdict"] == "NEEDS_MORE_EVIDENCE"
    assert result["bands"]["N_post_lock"] == "NEEDS_MORE_EVIDENCE"


def test_cell_level_comparison_all_15_improve():
    rows = []
    for idx, (strategy, instrument, hour) in enumerate(LOCKED_CELLS):
        rows.append(_trade(strategy, instrument, hour, 1.0, idx=idx))

    result = evaluate(filter_true_live({"trades": rows}, lock_deploy_ts=None), prelock=_prelock(-0.01))

    assert result["bands"]["cell_level_bonferroni"] == "ACCEPT"
    assert len(result["cells"]) == 15
    assert all(cell["kelly_delta"] > 0 for cell in result["cells"])


def test_prereg_snapshot_parser_reads_15_cell_table(tmp_path):
    lines = [
        "| # | strategy | instrument | hour_bucket | N | WR | EV pip | Wilson lo | raw Kelly |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, (strategy, instrument, hour) in enumerate(LOCKED_CELLS, 1):
        lines.append(f"| {idx} | {strategy} | {instrument} | {hour} | 1 | 100.00% | +1.00 | 20.65% | -0.1234 |")
    path = tmp_path / "prereg.md"
    path.write_text("\n".join(lines))

    parsed = load_prereg_snapshot(path)

    assert len(parsed) == 15
    assert parsed[LOCKED_CELLS[0]] == pytest.approx(-0.1234)
