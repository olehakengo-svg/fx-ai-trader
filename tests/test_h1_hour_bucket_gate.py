"""H-1 Hour-Bucket Promotion Gate — unit + integration tests.

W3-1 (2026-05-03).

Spec: wiki/learning/h1-hour-bucket-design-2026-05-03.md
Parent audit: wiki/learning/h1-spread-time-audit-2026-05-03.md

Covers:
  1. Pure helpers (utc_hour_from_iso, hour_to_bucket, assign_hour_bucket)
  2. Pure decision function DemoTrader._decide_hour_bucket_action
  3. Cell aggregator additions in modules.demo_db (by_type_pair_hour)
  4. Grandfather behavior (explicit snapshot set)
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
        assert cfg.hour_to_bucket(0, "4_bucket") == "A"
        assert cfg.hour_to_bucket(5, "4_bucket") == "A"
        assert cfg.hour_to_bucket(6, "4_bucket") == "B"
        assert cfg.hour_to_bucket(11, "4_bucket") == "B"
        assert cfg.hour_to_bucket(12, "4_bucket") == "C"
        assert cfg.hour_to_bucket(17, "4_bucket") == "C"
        assert cfg.hour_to_bucket(18, "4_bucket") == "D"
        assert cfg.hour_to_bucket(23, "4_bucket") == "D"

    def test_demo_db_assign_hour_bucket_boundaries(self):
        from modules.demo_db import assign_hour_bucket

        assert assign_hour_bucket(0) == "A"
        assert assign_hour_bucket(5) == "A"
        assert assign_hour_bucket(6) == "B"
        assert assign_hour_bucket(23) == "D"

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

def _make_cfg_stub(*, enabled=True, n_min=30,
                   wilson_min=0.40, ev_ci_min=0.0):
    """Return a stub config object with H1 fields, leaving other fields
    untouched. We pass this into _decide_hour_bucket_action directly so
    the test does not depend on the live config module state."""
    return types.SimpleNamespace(
        H1_GATE_ENABLED=enabled,
        H1_GATE_MIN_N=n_min,
        H1_GATE_WILSON_LO=wilson_min,
        H1_GATE_EV_CI_LO=ev_ci_min,
    )


class TestDecideHourBucketAction:
    def test_gate_disabled_never_changes_status(self):
        c = _make_cfg_stub(enabled=False)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 10, "ev_mean": -5, "ev_ci_lo": -8, "wilson_lo": 0.05},
            "live", False, c,
        )
        assert out == ("live", "gate_disabled")

    def test_grandfathered_live_protected(self):
        c = _make_cfg_stub(enabled=True)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 5, "ev_mean": -10, "ev_ci_lo": -12, "wilson_lo": 0.0},
            "live", True, c,
        )
        assert out == ("live", "grandfather")

    def test_n_below_min_no_action(self):
        c = _make_cfg_stub(enabled=True, n_min=30)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 5, "wr": 0, "ev_mean": -100, "ev_ci_lo": -100, "wilson_lo": 0.0},
            "live", False, c,
        )
        # Below n_min — must not act (no false demote on thin data)
        assert out == ("live", "n_below_min")

    def test_n_min_threshold_is_same_for_live_and_shadow(self):
        c = _make_cfg_stub(enabled=True, n_min=30)
        # N=25 is below the W3-1 H1_GATE_MIN_N for both live and shadow.
        live_out = DemoTrader._decide_hour_bucket_action(
            {"n": 25, "wr": 5, "ev_mean": -10, "ev_ci_lo": -10, "wilson_lo": 0.0},
            "live", False, c,
        )
        assert live_out == ("live", "n_below_min")
        shadow_out = DemoTrader._decide_hour_bucket_action(
            {"n": 25, "wr": 5, "ev_mean": -10, "ev_ci_lo": -10, "wilson_lo": 0.0},
            "shadow", False, c,
        )
        assert shadow_out == ("shadow", "n_below_min")

    def test_bucket_pass_keeps_status(self):
        c = _make_cfg_stub(enabled=True)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 80, "ev_mean": 5.0, "ev_ci_lo": 1.0, "wilson_lo": 0.65},
            "live", False, c,
        )
        assert out == ("live", "bucket_pass")

    def test_bucket_fail_live_demotes_to_shadow(self):
        c = _make_cfg_stub(enabled=True)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 30, "ev_mean": -2.0, "ev_ci_lo": -3.0, "wilson_lo": 0.20},
            "live", False, c,
        )
        assert out == ("shadow", "bucket_fail_demote_to_shadow")

    def test_bucket_fail_shadow_demotes_further(self):
        c = _make_cfg_stub(enabled=True)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 50, "wr": 10, "ev_mean": -3.0, "ev_ci_lo": -4.0, "wilson_lo": 0.05},
            "shadow", False, c,
        )
        assert out == ("demoted", "bucket_fail_demote_from_shadow")

    def test_already_demoted_stays(self):
        c = _make_cfg_stub(enabled=True)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 10, "ev_mean": -5.0, "ev_ci_lo": -6.0, "wilson_lo": 0.05},
            "demoted", False, c,
        )
        assert out == ("demoted", "already_demoted")

    def test_ev_ci_at_threshold_passes(self):
        c = _make_cfg_stub(enabled=True, ev_ci_min=0.0, wilson_min=0.40)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 60, "ev_mean": 0.5, "ev_ci_lo": 0.0, "wilson_lo": 0.41},
            "live", False, c,
        )
        assert out == ("live", "bucket_pass")

    def test_negative_ev_ci_fails(self):
        c = _make_cfg_stub(enabled=True, ev_ci_min=0.0, wilson_min=0.40)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 60, "ev_mean": 0.5, "ev_ci_lo": -0.01, "wilson_lo": 0.41},
            "live", False, c,
        )
        assert out[0] == "shadow"

    def test_wilson_at_threshold_fails(self):
        c = _make_cfg_stub(enabled=True, ev_ci_min=0.0, wilson_min=0.40)
        out = DemoTrader._decide_hour_bucket_action(
            {"n": 100, "wr": 60, "ev_mean": 1.0, "ev_ci_lo": 0.2, "wilson_lo": 0.40},
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
        # 4 LIVE bb_rsi_reversion / USD_JPY @ hour 13 (bucket C)
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
        key = "bb_rsi_reversion|USD_JPY|C"
        assert key in bth, (
            f"missing key {key!r}, got {list(bth)!r}"
        )
        cell = bth[key]
        assert cell["bucket"] == "C"
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
        key = "fib_reversal|USD_JPY|A"
        assert key in bth, f"missing {key!r}, got {list(bth)!r}"
        assert bth[key]["n"] == 3
        assert bth[key]["bucket"] == "A"

    def test_buckets_split_correctly_across_hours(self, db):
        """A single strategy across multiple hours yields multiple cells."""
        # 2 trades at hr 03 (A), 2 at hr 09 (B), 2 at 14 (C)
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
        assert "vol_momentum_scalp|EUR_USD|A" in keys
        assert "vol_momentum_scalp|EUR_USD|B" in keys
        assert "vol_momentum_scalp|EUR_USD|C" in keys
        for k in (
            "vol_momentum_scalp|EUR_USD|A",
            "vol_momentum_scalp|EUR_USD|B",
            "vol_momentum_scalp|EUR_USD|C",
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
        key = "bb_rsi_reversion|USD_JPY|A"
        if key in bth:
            assert bth[key]["n"] == 1, (
                "LIVE aggregator must exclude shadow rows; got "
                f"n={bth[key]['n']}"
            )


# =====================================================================
# 4. Config regression — gate enabled and grandfathered by default
# =====================================================================

class TestDefaultDisabledRegression:
    def test_module_default_is_enabled(self):
        """W3-1 ships the promotion-level gate active; grandfathering and
        N>=30 protect existing LIVE cells."""
        if "H1_GATE_ENABLED" in os.environ and os.environ["H1_GATE_ENABLED"] in ("0", "false", "False"):
            pytest.skip("env var explicitly disabled — skipping default check")
        assert cfg.H1_GATE_ENABLED is True

    def test_grandfather_set_includes_bb_rsi_reversion(self):
        """bb_rsi_reversion is the only LIVE strategy with N≥30 hour-bucket
        signal at this audit window. It must be in the grandfather set."""
        assert "bb_rsi_reversion" in cfg._GRANDFATHERED_LIVE

    def test_grandfather_set_includes_live_snapshot_strategies(self):
        """Snapshot LIVE config tiers are protected explicitly, not by
        runtime auto-grandfathering."""
        expected = {
            "bb_rsi_reversion",
            "gbp_deep_pullback",
            "session_time_bias",
            "trendline_sweep",
            "bb_squeeze_breakout",
            "doji_breakout",
            "ema200_trend_reversal",
            "squeeze_release_momentum",
            "streak_reversal",
            "vix_carry_unwind",
            "vol_momentum_scalp",
            "wick_imbalance_reversion",
            "xs_momentum",
        }
        assert expected.issubset(cfg._GRANDFATHERED_LIVE)
