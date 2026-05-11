"""tier_engine: shadow stat aggregator with Bonferroni correction."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cfd_trader.audit.oanda_audit import init_db, record_entry, OandaAuditEntry
from cfd_trader.promotion.tier_engine import TierReport, evaluate


def _seed_short_trades(db: str, n_wins: int, n_losses: int) -> None:
    extra = json.dumps({"bonferroni_m": 2, "selection_reason": "short_only_post_hoc"})
    for i in range(n_wins):
        record_entry(db, OandaAuditEntry(
            ts=f"2026-05-1{i+1}T14:30:00Z", instrument="SPX500_USD",
            strategy_name="orb_ny_open_short", bridge_status="filled",
            side="short", units=1, signal_price=5000.0, entry_price=5000.0,
            is_shadow=1, mode="SHADOW", extra_json=extra,
            exit_ts=f"2026-05-1{i+1}T15:30:00Z", exit_price=4990.0, pnl_point=10.0,
        ))
    for i in range(n_losses):
        record_entry(db, OandaAuditEntry(
            ts=f"2026-05-2{i+1}T14:30:00Z", instrument="SPX500_USD",
            strategy_name="orb_ny_open_short", bridge_status="filled",
            side="short", units=1, signal_price=5000.0, entry_price=5000.0,
            is_shadow=1, mode="SHADOW", extra_json=extra,
            exit_ts=f"2026-05-2{i+1}T15:30:00Z", exit_price=5010.0, pnl_point=-10.0,
        ))


def test_evaluate_returns_tier_report(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    _seed_short_trades(str(db), n_wins=15, n_losses=7)
    report = evaluate(str(db), strategy_name="orb_ny_open_short")
    assert isinstance(report, TierReport)
    assert report.n == 22
    assert report.wr == pytest.approx(15 / 22, rel=1e-4)


def test_evaluate_zero_trades_returns_empty_report(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    report = evaluate(str(db), strategy_name="orb_ny_open_short")
    assert report.n == 0
    assert report.h1_gate_distance == 30  # need 30, have 0


def test_evaluate_bonferroni_lowers_wilson(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    _seed_short_trades(str(db), n_wins=15, n_losses=7)
    report = evaluate(str(db), strategy_name="orb_ny_open_short")
    # Bonferroni m=2 should produce a LOWER (more conservative) wilson_lo
    # than the uncorrected value.
    assert report.wilson_lo_bonferroni < report.wilson_lo_raw


def test_evaluate_h1_gate_distance(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    _seed_short_trades(str(db), n_wins=15, n_losses=7)
    report = evaluate(str(db), strategy_name="orb_ny_open_short")
    # H1 Gate N_min=30, have N=22, distance=8
    assert report.h1_gate_distance == 8
