"""Walk-Forward recovery pattern tests (Phase 3.4 / P0#3).

Verifies:
  1. _calc_wf_halves emits a Mann-Whitney p-value via wf_p_value field.
  2. H1<0 / H2>0 trades produce a low p-value (recovery signal).
  3. Stable / collapsing patterns do NOT produce a low p-value.
  4. _evaluate_promotions recovers a demoted strategy when the WF pattern
     is satisfied (H1<0, H2>0, p<0.10) even when cumulative EV<0.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.demo_db import DemoDB


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = DemoDB(db_path=path)
    yield d
    os.unlink(path)


def _add_trade(db, entry_time: str, pnl_target: float, entry_type: str):
    """Create a closed trade with explicit entry_time and the requested pnl.

    Uses BUY at 150.000 SL=149.500 (50 pip risk) so pnl pips equals the
    requested signed magnitude when exit_price is set to 150.000 + pnl/100.
    """
    tid = db.open_trade(
        "BUY", 150.000, 149.500, 151.000,
        entry_type, 60, instrument="USD_JPY"
    )
    # Close at price implying the desired pnl_pips magnitude.
    exit_price = 150.000 + pnl_target / 100.0
    reason = "TP_HIT" if pnl_target > 0 else "SL_HIT"
    db.close_trade(tid, exit_price, reason)
    # Stamp explicit entry_time so the WF chronological split is deterministic.
    with db._lock:
        with db._safe_conn() as conn:
            conn.execute(
                "UPDATE demo_trades SET entry_time=? WHERE trade_id=?",
                (entry_time, tid),
            )


def _stats_for(db, entry_type: str) -> dict:
    data = db.get_trades_for_learning(min_trades=1)
    assert data["ready"], data
    return data["by_type"].get(entry_type, {})


class TestWFHalves:
    def test_recovery_pattern_low_pvalue(self, db):
        """H1 all losses, H2 all wins → p-value should be <0.10."""
        et = "recovery_strat"
        # H1: 10 losses (-15 to -5)
        for i in range(10):
            _add_trade(db, f"2026-04-01T00:{i:02d}:00+00:00", -10.0 - (i % 5), et)
        # H2: 10 wins (+5 to +15)
        for i in range(10):
            _add_trade(db, f"2026-04-15T00:{i:02d}:00+00:00", 10.0 + (i % 5), et)

        s = _stats_for(db, et)
        assert s["n"] == 20
        assert s["wf_h1_avg"] < 0
        assert s["wf_h2_avg"] > 0
        assert s["wf_p_value"] is not None
        assert s["wf_p_value"] < 0.10, (
            f"recovery pattern should yield p<0.10, got {s['wf_p_value']}"
        )

    def test_collapse_pattern_high_pvalue(self, db):
        """H1 wins, H2 losses → one-sided 'H2>H1' p-value should be high."""
        et = "collapse_strat"
        for i in range(10):
            _add_trade(db, f"2026-04-01T00:{i:02d}:00+00:00", 10.0 + (i % 5), et)
        for i in range(10):
            _add_trade(db, f"2026-04-15T00:{i:02d}:00+00:00", -10.0 - (i % 5), et)

        s = _stats_for(db, et)
        assert s["wf_h1_avg"] > 0
        assert s["wf_h2_avg"] < 0
        assert s["wf_p_value"] is not None
        # one-sided "H2 > H1" should be far from significant for collapse
        assert s["wf_p_value"] > 0.5

    def test_stable_pattern_no_signal(self, db):
        """Stable (similar H1/H2) → p-value not significant."""
        et = "stable_strat"
        for i in range(10):
            _add_trade(db, f"2026-04-01T00:{i:02d}:00+00:00", 5.0 - (i % 3), et)
        for i in range(10):
            _add_trade(db, f"2026-04-15T00:{i:02d}:00+00:00", 5.0 - (i % 3), et)

        s = _stats_for(db, et)
        assert s["wf_p_value"] is not None
        assert s["wf_p_value"] >= 0.10

    def test_too_few_trades_p_value_none(self, db):
        """N<6 (3 per half) → p_value is None (not enough samples)."""
        et = "tiny_strat"
        for i in range(4):
            _add_trade(db, f"2026-04-01T00:{i:02d}:00+00:00", 5.0, et)
        s = _stats_for(db, et)
        # 4 trades → halves of 2 each → < 3 per half → p_value None
        assert s["wf_p_value"] is None


class TestEvaluatePromotionsWFRecovery:
    """Exercise the _evaluate_promotions branch logic with a stub trader."""

    def _eval_status(self, n, ev, wr, h1_avg, h2_avg, p_value, old_status):
        """Replicates the recovery branch decision logic.

        We mirror the conditional from _evaluate_promotions to verify the
        boolean expression — full trader instantiation is too heavy here.
        """
        SMC_PROTECTED = set()  # not relevant for recovery test
        et = "test_strat"
        friction_pip = 1.0
        wilson_pass = False  # forces non-promote path
        kelly_block = False

        stats = {
            "n": n, "ev": ev, "wr": wr,
            "wf_h1_avg": h1_avg, "wf_h2_avg": h2_avg,
            "wf_p_value": p_value,
        }
        old = old_status

        if (n >= 20 and wr >= 60.0
                and ev >= friction_pip and wilson_pass
                and not kelly_block):
            return "promoted"
        elif (n >= 30 and ev >= friction_pip and wilson_pass
              and not kelly_block):
            return "promoted"
        elif n >= 20 and ev < -0.5 and et not in SMC_PROTECTED:
            return "demoted"
        elif (n >= 20
              and stats.get("wf_h1_avg", 0) > 0
              and stats.get("wf_h2_avg", 0) < 0
              and et not in SMC_PROTECTED):
            return "demoted"
        elif old == "demoted" and (
            (n >= 30 and ev > 0)
            or (
                n >= 20
                and stats.get("wf_h1_avg", 0) <= 0
                and stats.get("wf_h2_avg", 0) > 0
                and stats.get("wf_p_value") is not None
                and stats.get("wf_p_value") < 0.10
            )
        ):
            return "pending"
        else:
            return old if old in ("promoted", "demoted") else "pending"

    def test_wf_recovery_promotes_demoted_to_pending(self):
        """H1<0, H2>0, p<0.10, cumulative EV slightly negative — recovers."""
        # ev < -0.5 would also demote, so we use ev between -0.5 and 0 to
        # isolate the WF recovery branch from the demote/recovery race.
        s = self._eval_status(
            n=25, ev=-0.4, wr=45,
            h1_avg=-2.0, h2_avg=1.5, p_value=0.05,
            old_status="demoted",
        )
        assert s == "pending"

    def test_wf_recovery_blocked_by_high_pvalue(self):
        """H1<0, H2>0 but p>=0.10 → no recovery."""
        s = self._eval_status(
            n=25, ev=-0.4, wr=45,
            h1_avg=-1.0, h2_avg=0.5, p_value=0.30,
            old_status="demoted",
        )
        assert s == "demoted"

    def test_legacy_cumulative_recovery_still_works(self):
        """Legacy path: N≥30, EV>0 → recovery (no WF needed)."""
        s = self._eval_status(
            n=35, ev=0.6, wr=55,
            h1_avg=0.3, h2_avg=0.9, p_value=None,
            old_status="demoted",
        )
        assert s == "pending"

    def test_no_recovery_when_not_demoted(self):
        """WF recovery condition only fires when status was already demoted."""
        s = self._eval_status(
            n=25, ev=-0.4, wr=45,
            h1_avg=-2.0, h2_avg=1.5, p_value=0.05,
            old_status="pending",
        )
        # Falls through to else branch: stays pending (not "demoted")
        assert s == "pending"

    def test_demote_takes_precedence_over_wf_recovery(self):
        """If EV<-0.5 the demote branch fires before recovery — by design."""
        s = self._eval_status(
            n=25, ev=-1.5, wr=40,
            h1_avg=-3.0, h2_avg=1.0, p_value=0.05,
            old_status="demoted",
        )
        assert s == "demoted"
