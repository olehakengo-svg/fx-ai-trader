"""Tests for tools/auto_force_demoted_recovery.py.

Recovery gate (matches cell_edge_audit v2 promotion + stricter N):
  N >= 30 AND Wilson_BF lower (Z=3.29) > 0.50 AND Bonferroni p < 0.05
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from modules.demo_db import DemoDB
from tools import auto_force_demoted_recovery as afdr


# ─── Fixtures ──────────────────────────────────────────────────────────
@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = DemoDB(db_path=path)
    yield d
    os.unlink(path)


@pytest.fixture
def tier_master(tmp_path: Path) -> Path:
    """A minimal tier-master.json containing intraday_seasonality + a non-recovering peer."""
    data = {
        "generated_at": "2026-04-27T00:00:00+00:00",
        "elite_live": [],
        "force_demoted": ["intraday_seasonality", "ema_cross"],
        "scalp_sentinel": [],
        "universal_sentinel": [],
        "pair_promoted": [],
        "pair_demoted": [],
    }
    p = tmp_path / "tier-master.json"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p


def _open_close(db: DemoDB, entry_type: str, win: bool,
                instrument: str = "USD_JPY", direction: str = "BUY",
                is_shadow: bool = True) -> str:
    """Helper: shadow trade with deterministic outcome (5-pip TP / SL on USD_JPY)."""
    if direction == "BUY":
        entry, sl, tp = 150.00, 149.95, 150.05
        exit_price = tp if win else sl
    else:
        entry, sl, tp = 150.00, 150.05, 149.95
        exit_price = tp if win else sl
    tid = db.open_trade(direction, entry, sl, tp, entry_type, 60,
                        instrument=instrument, is_shadow=is_shadow)
    db.close_trade(tid, exit_price, "TP_HIT" if win else "SL_HIT")
    return tid


def _seed_shadow_record(db: DemoDB, entry_type: str, n_wins: int, n_losses: int):
    for _ in range(n_wins):
        _open_close(db, entry_type, win=True)
    for _ in range(n_losses):
        _open_close(db, entry_type, win=False)


# ─── Stat helper unit tests ────────────────────────────────────────────
class TestEvaluateRecovery:
    def test_strong_edge_qualifies(self):
        # 50/60 = 83% WR, comfortably above the Wilson_BF=0.50 threshold even at Z=3.29
        rec = afdr.evaluate_recovery(n=60, wins=50, n_tests=18)
        assert rec["qualifies"] is True
        assert rec["wilson_bf_lower"] > 0.50
        assert rec["p_value_bonferroni"] < 0.05

    def test_below_min_n_blocks_recovery(self):
        # Same 83% WR but only N=20 — must be blocked by MIN_N=30 even though stats look good
        rec = afdr.evaluate_recovery(n=20, wins=17, n_tests=18)
        assert rec["qualifies"] is False
        assert rec["n"] < afdr.MIN_N

    def test_marginal_wr_blocked_by_wilson_bf(self):
        # 55% WR @ N=30 — passes raw 50% but Wilson_BF lower (Z=3.29) is well below 0.50
        rec = afdr.evaluate_recovery(n=30, wins=17, n_tests=18)
        assert rec["wilson_bf_lower"] < 0.50
        assert rec["qualifies"] is False

    def test_bonferroni_blocks_when_family_large(self):
        # 65% WR @ N=30 — significant raw, but with N_tests=100 Bonferroni may still flag,
        # confirm the formula is multiplicative and capped at 1.0.
        rec = afdr.evaluate_recovery(n=30, wins=20, n_tests=10000)
        assert rec["p_value_bonferroni"] <= 1.0
        # Either Wilson_BF or Bonferroni blocks at this family size.
        assert rec["qualifies"] is False


# ─── Integration with tier-master.json ─────────────────────────────────
class TestRunRecovery:
    def test_qualifying_strategy_is_removed(self, db, tier_master):
        # intraday_seasonality: 50W / 10L (N=60, WR=83%) — clearly qualifies
        _seed_shadow_record(db, "intraday_seasonality", n_wins=50, n_losses=10)
        # ema_cross: 15W / 15L (N=30, WR=50%) — does not qualify
        _seed_shadow_record(db, "ema_cross", n_wins=15, n_losses=15)

        summary = afdr.run_recovery(db, tier_master, dry_run=False)

        assert summary["recovered"] == ["intraday_seasonality"]
        assert summary["wrote_tier_master"] is True

        new_data = json.loads(tier_master.read_text())
        assert "intraday_seasonality" not in new_data["force_demoted"]
        assert "ema_cross" in new_data["force_demoted"]

        # algo_change_log got one row of the right type
        changes = db.get_algo_changes(limit=10)
        assert any(
            c["change_type"] == "auto_recovery_from_force_demoted"
            and "intraday_seasonality" in (c["description"] or "")
            for c in changes
        )

        # backup exists
        assert summary["backup"] is not None
        assert Path(summary["backup"]).exists()

    def test_no_qualifying_strategy_no_change(self, db, tier_master):
        # Both strategies fall well below the gate
        _seed_shadow_record(db, "intraday_seasonality", n_wins=15, n_losses=15)
        _seed_shadow_record(db, "ema_cross", n_wins=10, n_losses=20)
        before = tier_master.read_text()

        summary = afdr.run_recovery(db, tier_master, dry_run=False)

        assert summary["recovered"] == []
        assert summary["wrote_tier_master"] is False
        assert summary["backup"] is None
        assert tier_master.read_text() == before

        changes = db.get_algo_changes(limit=10)
        assert not any(
            c["change_type"] == "auto_recovery_from_force_demoted" for c in changes
        )

    def test_dry_run_does_not_write(self, db, tier_master):
        _seed_shadow_record(db, "intraday_seasonality", n_wins=50, n_losses=10)
        before = tier_master.read_text()

        summary = afdr.run_recovery(db, tier_master, dry_run=True)

        assert summary["recovered"] == ["intraday_seasonality"]
        assert summary["wrote_tier_master"] is False
        assert tier_master.read_text() == before
        # No algo_change_log entry on dry-run
        changes = db.get_algo_changes(limit=10)
        assert not any(
            c["change_type"] == "auto_recovery_from_force_demoted" for c in changes
        )

    def test_xau_trades_excluded(self, db, tier_master):
        # All XAU shadow wins should be excluded -> intraday_seasonality should NOT recover
        for _ in range(60):
            _open_close(db, "intraday_seasonality", win=True, instrument="XAU_USD")
        summary = afdr.run_recovery(db, tier_master, dry_run=True)
        evals = {e["strategy"]: e for e in summary["evaluations"]}
        assert evals["intraday_seasonality"]["n"] == 0
        assert summary["recovered"] == []
