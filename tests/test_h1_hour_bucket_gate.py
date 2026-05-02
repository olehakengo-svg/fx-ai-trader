"""H-1 Hour-Bucket Cell-Level Promotion Gate — unit + integration tests.

Wave 2 task W2-4 (2026-05-03).

Spec: wiki/learning/h1-hour-bucket-design-2026-05-03.md
Parent audit: wiki/learning/h1-spread-time-audit-2026-05-03.md

Covers:
  1. Pure helpers (utc_hour_from_iso, hour_to_bucket) in modules.config
  2. Pure decision function DemoTrader._decide_hour_bucket_action
  3. Cell aggregator additions in modules.demo_db (by_type_pair_hour)
  4. Grandfather behavior (explicit set + runtime auto-grandfather)
  5. Default OFF guarantees no behavior change (regression)
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from modules import config as cfg
from modules.demo_trader import DemoTrader


# =====================================================================
# 1. Pure helpers — utc_hour_from_iso, hour_to_bucket
# =====================================================================

class TestUtcHourFromIso:
    def test_typical_iso_string(self):
        assert cfg.utc_hour_from_iso("2026-04-15T13:42:11+00:00") == 13

    def test_naive_iso_string(self):
        assert cfg.utc_hour_from_iso("2026-04-15T07:30:00") == 7

    def test_midnight(self):
        assert cfg.utc_hour_from_iso("2026-04-15T00:00:00") == 0

    def test_invalid_returns_none(self):
        assert cfg.utc_hour_from_iso("not-a-date") is None
        assert cfg.utc_hour_from_iso("") is None
        assert cfg.utc_hour_from_iso(None) is None


class TestHourToBucket:
    def test_4_bucket_boundaries(self):
        # A_00-05: 0-5 inclusive, 6 excluded
        assert cfg.hour_to_bucket(0, "4_bucket") == "A_00-05"
        assert cfg.hour_to_bucket(5, "4_bucket") == "A_00-05"
        assert cfg.hour_to_bucket(6, "4_bucket") == "B_06-11"
        assert cfg.hour_to_bucket(11, "4_bucket") == "B_06-11"
        assert cfg.hour_to_bucket(12, "4_bucket") == "C_12-17"
        assert cfg.hour_to_bucket(17, "4_bucket") == "C_12-17"
        assert cfg.hour_to_bucket(18, "4_bucket") == "D_18-23"
        assert cfg.hour_to_bucket(23, "4_bucket") == "D_18-23"

    def test_24_bucket(self):
        assert cfg.hour_to_bucket(13, "24_bucket") == "H13"
        assert cfg.hour_to_bucket(0, "24_bucket") == "H00"
        assert cfg.hour_to_bucket(23, "24_bucket") == "H23"

    def test_invalid_hour(self):
        assert cfg.hour_to_bucket(-1) is None
        assert cfg.hour_to_bucket(24) is None
        assert cfg.hour_to_bucket(None) is None
        assert cfg.hour_to_bucket("abc") is None


# =====================================================================
# 2. Pure decision function — _decide_hour_bucket_action
# =====================================================================

def _make_cfg_stub(*, enabled=True, n_min_live=30, n_min_shadow=20,
                   wilson_min=0.40, ev_min=-0.5):
    """Return a stub config object with H1 fields, leaving other fields
    untouched. We pass this into _decide_hour_bucket_action directly so
    the test does not depend on the live config module state."""
    return types.SimpleNamespace(
        H1_GATE_ENABLED=enabled,
        H1_BUCKET_N_MIN=n_min_live,
        H1_BUCKET_N_MIN_SHADOW=n_min_shadow,
        H1_BUCKET_WILSON_MIN=wilson_min,
        H1_BUCKET_EV_MIN_PIP=ev_min,
    )


class TestDecideHourBucketAction:
    def test_gate_disabled_never_changes_status(self):
        c = _make_cfg_stub(enabled=False)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 10, "ev": -5, "wilson_lo": 0.05},
            "live", False, c,
        )
        assert out == ("live", "gate_disabled")

    def test_grandfathered_live_protected(self):
        c = _make_cfg_stub(enabled=True)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 5, "ev": -10, "wilson_lo": 0.0},
            "live", True, c,
        )
        assert out == ("live", "grandfather")

    def test_n_below_min_no_action(self):
        c = _make_cfg_stub(enabled=True, n_min_live=30)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 5, "wr": 0, "ev": -100, "wilson_lo": 0.0},
            "live", False, c,
        )
        # Below n_min — must not act (no false demote on thin data)
        assert out == ("live", "n_below_min")

    def test_n_min_threshold_differs_for_live_vs_shadow(self):
        c = _make_cfg_stub(enabled=True, n_min_live=30, n_min_shadow=20)
        # N=25 — below live threshold but above shadow threshold
        # A live cell would be n_below_min, shadow cell evaluates the gate
        live_out = DemoTrader._decide_hour_bucket_action(
            {"n": 25, "wr": 5, "ev": -10, "wilson_lo": 0.0},
            "live", False, c,
        )
        assert live_out == ("live", "n_below_min")
        shadow_out = DemoTrader._decide_hour_bucket_action(
            {"n": 25, "wr": 5, "ev": -10, "wilson_lo": 0.0},
            "shadow", False, c,
        )
        assert shadow_out == ("demoted", "bucket_fail_demote_from_shadow")

    def test_bucket_pass_keeps_status(self):
        c = _make_cfg_stub(enabled=True)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 80, "ev": 5.0, "wilson_lo": 0.65},
            "live", False, c,
        )
        assert out == ("live", "bucket_pass")

    def test_bucket_fail_live_demotes_to_shadow(self):
        c = _make_cfg_stub(enabled=True)
        # Wilson lo below threshold
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 30, "ev": -2.0, "wilson_lo": 0.20},
            "live", False, c,
        )
        assert out == ("shadow", "bucket_fail_demote_to_shadow")

    def test_bucket_fail_shadow_demotes_further(self):
        c = _make_cfg_stub(enabled=True)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 50, "wr": 10, "ev": -3.0, "wilson_lo": 0.05},
            "shadow", False, c,
        )
        assert out == ("demoted", "bucket_fail_demote_from_shadow")

    def test_already_demoted_stays(self):
        c = _make_cfg_stub(enabled=True)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 10, "ev": -5.0, "wilson_lo": 0.05},
            "demoted", False, c,
        )
        assert out == ("demoted", "already_demoted")

    def test_ev_just_above_threshold_passes(self):
        # Boundary: ev_min=-0.5 → -0.49 passes (> not >=)
        c = _make_cfg_stub(enabled=True, ev_min=-0.5, wilson_min=0.40)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 60, "ev": -0.49, "wilson_lo": 0.41},
            "live", False, c,
        )
        assert out == ("live", "bucket_pass")

    def test_ev_at_threshold_fails(self):
        # Boundary: ev > ev_min strict — equals should fail
        c = _make_cfg_stub(enabled=True, ev_min=-0.5, wilson_min=0.40)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 60, "ev": -0.5, "wilson_lo": 0.41},
            "live", False, c,
        )
        assert out[0] == "shadow"

    def test_wilson_at_threshold_fails(self):
        c = _make_cfg_stub(enabled=True, ev_min=-0.5, wilson_min=0.40)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 60, "ev": 1.0, "wilson_lo": 0.40},
            "live", False, c,
        )
        assert out[0] == "shadow"


# =====================================================================
# 3. Aggregator integration — by_type_pair_hour (demo_db)
# =====================================================================

class TestByTypePairHourAggregation:
    """The dim should appear in both LIVE (get_trades_for_learning) and
    SHADOW (get_shadow_trades_for_evaluation) aggregator outputs."""

    @pytest.fixture
    def db(self, tmp_path):
        from modules.demo_db import DemoDB
        path = str(tmp_path / "h1_test.db")
        d = DemoDB(db_path=path)
        yield d

    def _direct_insert(self, db, *, trade_id, entry_type, instrument,
                       entry_time, exit_time, pnl_pips, outcome,
                       is_shadow=0):
        """Bypass the open/close flow to fully control entry_time
        (open_trade uses datetime.now(), which would always be in the
        current hour). Direct SQL into demo_trades."""
        with db._safe_conn() as conn:  # noqa: SLF001 — test scaffold
            conn.execute(
                """INSERT INTO demo_trades
                (trade_id, status, direction, entry_price, entry_time,
                 exit_price, exit_time, sl, tp, pnl_pips, pnl_r, outcome,
                 entry_type, confidence, tf, instrument, mode, is_shadow,
                 dedup_violation, close_reason)
                VALUES (?, 'CLOSED', 'BUY', 150.0, ?, 150.0, ?, 149.7,
                        150.5, ?, ?, ?, ?, 65, '5m', ?, 'scalp_5m', ?, 0,
                        'TP')""",
                (trade_id, entry_time, exit_time, pnl_pips,
                 pnl_pips / 3.0, outcome, entry_type, instrument, is_shadow),
            )
            conn.commit()

    def test_live_aggregator_emits_by_type_pair_hour(self, db):
        """LIVE rows aggregate into by_type_pair_hour at promotion-stage."""
        # 4 LIVE bb_rsi_reversion / USD_JPY @ hour 13 (bucket C_12-17)
        for i in range(4):
            self._direct_insert(
                db,
                trade_id=f"L{i:03d}",
                entry_type="bb_rsi_reversion",
                instrument="USD_JPY",
                entry_time=f"2026-04-15T13:0{i}:00+00:00",
                exit_time=f"2026-04-15T13:3{i}:00+00:00",  # >60s seed gate
                pnl_pips=5.0 if i < 3 else -3.0,
                outcome="WIN" if i < 3 else "LOSS",
                is_shadow=0,
            )
        result = db.get_trades_for_learning(min_trades=1)
        assert result.get("ready"), f"DB fixture not ready: {result}"
        bth = result.get("by_type_pair_hour", {})
        assert bth, "by_type_pair_hour must be populated"
        key = "bb_rsi_reversion|USD_JPY|C_12-17"
        assert key in bth, (
            f"missing key {key!r}, got {list(bth)!r}"
        )
        cell = bth[key]
        assert cell["bucket"] == "C_12-17"
        assert cell["entry_type"] == "bb_rsi_reversion"
        assert cell["instrument"] == "USD_JPY"
        assert cell["n"] == 4

    def test_shadow_path_emits_by_type_pair_hour(self, db):
        """SHADOW path aggregates parallel by_type_pair_hour."""
        for i in range(3):
            self._direct_insert(
                db,
                trade_id=f"S{i:03d}",
                entry_type="fib_reversal",
                instrument="USD_JPY",
                entry_time=f"2026-04-15T03:0{i}:00+00:00",
                exit_time=f"2026-04-15T03:3{i}:00+00:00",
                pnl_pips=8.0,
                outcome="WIN",
                is_shadow=1,
            )
        result = db.get_shadow_trades_for_evaluation()
        assert result.get("ready"), f"shadow DB not ready: {result}"
        bth = result.get("by_type_pair_hour", {})
        assert bth, "shadow by_type_pair_hour must be populated"
        key = "fib_reversal|USD_JPY|A_00-05"
        assert key in bth, f"missing {key!r}, got {list(bth)!r}"
        assert bth[key]["n"] == 3
        assert bth[key]["bucket"] == "A_00-05"

    def test_buckets_split_correctly_across_hours(self, db):
        """A single strategy across multiple hours yields multiple cells."""
        # 2 trades at hr 03 (A_00-05), 2 at hr 09 (B_06-11), 2 at 14 (C_12-17)
        plan = [(0, 3), (1, 3), (2, 9), (3, 9), (4, 14), (5, 14)]
        for tid, hr in plan:
            self._direct_insert(
                db,
                trade_id=f"L{tid:03d}",
                entry_type="vol_momentum_scalp",
                instrument="EUR_USD",
                entry_time=f"2026-04-15T{hr:02d}:00:00+00:00",
                exit_time=f"2026-04-15T{hr:02d}:30:00+00:00",
                pnl_pips=2.5,
                outcome="WIN",
                is_shadow=0,
            )
        result = db.get_trades_for_learning(min_trades=1)
        bth = result.get("by_type_pair_hour", {})
        keys = sorted(bth.keys())
        assert "vol_momentum_scalp|EUR_USD|A_00-05" in keys
        assert "vol_momentum_scalp|EUR_USD|B_06-11" in keys
        assert "vol_momentum_scalp|EUR_USD|C_12-17" in keys
        for k in (
            "vol_momentum_scalp|EUR_USD|A_00-05",
            "vol_momentum_scalp|EUR_USD|B_06-11",
            "vol_momentum_scalp|EUR_USD|C_12-17",
        ):
            assert bth[k]["n"] == 2, f"{k}: expected n=2"

    def test_live_shadow_separation_holds(self, db):
        """LIVE aggregator must not include is_shadow=1 rows
        (feedback_live_shadow_separation)."""
        # 1 LIVE + 2 SHADOW for same cell
        self._direct_insert(
            db, trade_id="L01", entry_type="bb_rsi_reversion",
            instrument="USD_JPY",
            entry_time="2026-04-15T03:00:00+00:00",
            exit_time="2026-04-15T03:30:00+00:00",
            pnl_pips=5.0, outcome="WIN", is_shadow=0,
        )
        for i in range(2):
            self._direct_insert(
                db, trade_id=f"S{i:02d}",
                entry_type="bb_rsi_reversion", instrument="USD_JPY",
                entry_time=f"2026-04-15T03:1{i}:00+00:00",
                exit_time=f"2026-04-15T03:4{i}:00+00:00",
                pnl_pips=-3.0, outcome="LOSS", is_shadow=1,
            )
        result = db.get_trades_for_learning(min_trades=1)
        bth = result.get("by_type_pair_hour", {})
        key = "bb_rsi_reversion|USD_JPY|A_00-05"
        if key in bth:
            assert bth[key]["n"] == 1, (
                "LIVE aggregator must exclude shadow rows; got "
                f"n={bth[key]['n']}"
            )


# =====================================================================
# 4. Default OFF regression — no _promoted_types changes when disabled
# =====================================================================

class TestDefaultDisabledRegression:
    def test_module_default_is_disabled(self):
        """Code-level default must be OFF — config can be flipped via env
        but the safe ship state is gate disabled."""
        # If H1_GATE_ENABLED env var is unset, default should be False.
        if "H1_GATE_ENABLED" in os.environ and os.environ["H1_GATE_ENABLED"] in ("1", "true", "True"):
            pytest.skip("env var explicitly enabled — skipping default check")
        assert cfg.H1_GATE_ENABLED is False

    def test_grandfather_set_includes_bb_rsi_reversion(self):
        """bb_rsi_reversion is the only LIVE strategy with N≥30 hour-bucket
        signal at this audit window. It must be in the grandfather set."""
        assert "bb_rsi_reversion" in cfg.H1_GRANDFATHERED_LIVE
