"""Tests for shadow-data promotion gate (cell_edge_audit v2 criteria).

Covers:
  - DemoTrader._binomial_two_sided_p (statistic helper)
  - DemoTrader._shadow_promotion_decision (pure decision function)
  - DemoTrader._evaluate_shadow_promotions (DB-backed integration)

The promotion gate that this exercises is the fix for
``lesson-sentinel-n-measurement-bug``: ``get_trades_for_learning`` filters
``is_shadow=1`` trades, so Sentinel / FORCE_DEMOTED strategies could never
accumulate the N needed to promote. The shadow path now reads
``get_shadow_trades_for_evaluation`` and applies cell_edge_audit.py v2
criteria (N>=20, wilson_bf_lower>0.50, Bonferroni p<0.05).
"""
import os
import tempfile

import pytest

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


# =====================================================================
#  Pure helpers — no DB required
# =====================================================================

class TestBinomialTwoSidedP:
    def test_zero_n_returns_one(self):
        assert DemoTrader._binomial_two_sided_p(0, 0, 0.5) == 1.0

    def test_perfect_wr_significant(self):
        # 25 wins / 25 trials vs p0=0.5 — extremely significant.
        p = DemoTrader._binomial_two_sided_p(25, 25, 0.5)
        assert p < 1e-5

    def test_wr_at_null_high_p(self):
        # 50/100 against p0=0.5 — z=0 → p ≈ 1.0.
        p = DemoTrader._binomial_two_sided_p(50, 100, 0.5)
        assert p > 0.99

    def test_p_value_bounds(self):
        for w, n in [(0, 30), (5, 30), (15, 30), (30, 30), (1, 1)]:
            p = DemoTrader._binomial_two_sided_p(w, n, 0.5)
            assert 0.0 <= p <= 1.0


class TestShadowPromotionDecision:
    """Cell_edge_audit v2 gate: N>=20 AND wilson_bf_lower>0.50 AND p_bonf<0.05."""

    def test_clear_promote_strong_edge(self):
        # 80% WR over N=30, single test → all gates pass.
        d = DemoTrader._shadow_promotion_decision(
            n=30, wins=26, num_tests=1,
        )
        assert d["promoted"] is True
        assert d["passes"]["n"] is True
        assert d["passes"]["wilson"] is True
        assert d["passes"]["bonferroni"] is True
        assert d["wilson_bf_lower"] > 0.50

    def test_block_n_below_20(self):
        # N=15: even at WR=100% the N gate fails.
        d = DemoTrader._shadow_promotion_decision(
            n=15, wins=15, num_tests=1,
        )
        assert d["promoted"] is False
        assert d["passes"]["n"] is False

    def test_block_wilson_below_0_50(self):
        # 60% WR over N=20 → Wilson_BF lower is well below 0.50
        # because Z=3.29 (Bonferroni) widens the band considerably.
        d = DemoTrader._shadow_promotion_decision(
            n=20, wins=12, num_tests=1,
        )
        assert d["promoted"] is False
        assert d["passes"]["wilson"] is False
        assert d["wilson_bf_lower"] <= 0.50

    def test_block_bonferroni_correction(self):
        # Marginal raw-p edge (p_raw ~ 0.04 say) gets killed by num_tests=10.
        # At N=20, wins=15 → raw p ≈ 0.025 (two-sided), bonf 10x ≈ 0.25.
        d = DemoTrader._shadow_promotion_decision(
            n=20, wins=15, num_tests=10,
        )
        assert d["passes"]["bonferroni"] is False
        assert d["promoted"] is False
        # Without Bonferroni penalty, raw p would have passed.
        d_alone = DemoTrader._shadow_promotion_decision(
            n=20, wins=15, num_tests=1,
        )
        assert d_alone["p_value_raw"] < 0.05

    def test_negative_kelly_blocks_when_provided(self):
        d = DemoTrader._shadow_promotion_decision(
            n=30, wins=26, num_tests=1, kelly_f=-0.05,
        )
        assert d["promoted"] is False
        assert d["kelly_blocked"] is True

    def test_none_kelly_does_not_block(self):
        d = DemoTrader._shadow_promotion_decision(
            n=30, wins=26, num_tests=1, kelly_f=None,
        )
        assert d["promoted"] is True
        assert d["kelly_blocked"] is False

    def test_friction_gate_when_both_provided(self):
        # ev=0.3 < friction_pip=1.0 → ev gate fails even with perfect stats.
        d = DemoTrader._shadow_promotion_decision(
            n=30, wins=28, num_tests=1, ev=0.3, friction_pip=1.0,
        )
        assert d["passes"]["ev"] is False
        assert d["promoted"] is False


# =====================================================================
#  Integration — DemoTrader._evaluate_shadow_promotions over real DB
# =====================================================================

@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = DemoDB(db_path=path)
    yield d
    os.unlink(path)


def _open_close_shadow(db: DemoDB, entry_type: str, instrument: str,
                       win: bool) -> str:
    entry, sl, tp = 150.0, 149.5, 150.5
    exit_price = tp if win else sl
    tid = db.open_trade("BUY", entry, sl, tp, entry_type, 60,
                        instrument=instrument, is_shadow=True)
    db.close_trade(tid, exit_price, "TP_HIT" if win else "SL_HIT")
    return tid


class _FakeTrader:
    """Minimal stand-in that exercises _evaluate_shadow_promotions
    without booting the full DemoTrader background-thread machinery."""

    _FIDELITY_CUTOFF = ""  # disables the after_date filter
    _BT_COST_PER_TRADE = 1.0

    def __init__(self, db):
        self._db = db
        self._promoted_types: dict = {}

    # Methods we need from DemoTrader, bound directly:
    _wilson_bf_lower = staticmethod(DemoTrader._wilson_bf_lower)
    _binomial_two_sided_p = staticmethod(DemoTrader._binomial_two_sided_p)
    _strategy_friction_pips = staticmethod(DemoTrader._strategy_friction_pips)
    _shadow_promotion_decision = classmethod(
        DemoTrader._shadow_promotion_decision.__func__
    )
    _evaluate_shadow_promotions = DemoTrader._evaluate_shadow_promotions
    _WILSON_BF_Z = DemoTrader._WILSON_BF_Z


class TestEvaluateShadowPromotions:
    def test_strong_shadow_edge_promotes_sentinel(self, db):
        # 26 wins / 30 trials (~87% WR) on a single strategy.
        for _ in range(26):
            _open_close_shadow(db, "trend_rebound", "USD_JPY", True)
        for _ in range(4):
            _open_close_shadow(db, "trend_rebound", "USD_JPY", False)

        trader = _FakeTrader(db)
        changes, change_log = [], []
        trader._evaluate_shadow_promotions(changes, change_log, set())

        info = trader._promoted_types.get("trend_rebound")
        assert info is not None, "shadow strategy missing from _promoted_types"
        assert info["status"] == "promoted"
        assert info["source"] == "shadow_eval"
        assert info["n"] == 30
        assert info["wilson_bf_lower"] > 0.50
        # log-side artefacts
        assert any("trend_rebound[shadow]" in c for c in changes)
        assert any(e.get("scope") == "strategy_shadow" for e in change_log)

    def test_weak_shadow_data_does_not_promote(self, db):
        # 12 wins / 20 trials (60% WR): clears N>=20 but Wilson_BF falls short.
        for _ in range(12):
            _open_close_shadow(db, "marginal_strat", "USD_JPY", True)
        for _ in range(8):
            _open_close_shadow(db, "marginal_strat", "USD_JPY", False)

        trader = _FakeTrader(db)
        changes, change_log = [], []
        trader._evaluate_shadow_promotions(changes, change_log, set())

        info = trader._promoted_types.get("marginal_strat")
        assert info is not None
        assert info["status"] == "pending"
        assert info["source"] == "shadow_eval"

    def test_smc_protected_skipped(self, db):
        # Strong shadow edge but the strategy is in SMC_PROTECTED → skip.
        for _ in range(26):
            _open_close_shadow(db, "smc_break", "USD_JPY", True)
        for _ in range(4):
            _open_close_shadow(db, "smc_break", "USD_JPY", False)

        trader = _FakeTrader(db)
        changes, change_log = [], []
        trader._evaluate_shadow_promotions(
            changes, change_log, {"smc_break"},
        )

        assert "smc_break" not in trader._promoted_types
        assert changes == []

    def test_live_promotion_not_overwritten(self, db):
        # Live loop already promoted this strategy this cycle. Shadow
        # data should not clobber the live status (no `source` set →
        # treated as live-derived).
        for _ in range(26):
            _open_close_shadow(db, "live_winner", "USD_JPY", True)
        for _ in range(4):
            _open_close_shadow(db, "live_winner", "USD_JPY", False)

        trader = _FakeTrader(db)
        trader._promoted_types["live_winner"] = {
            "status": "promoted", "n": 50, "wr": 70.0, "ev": 1.5,
            # no `source` field → live-derived
        }
        changes, change_log = [], []
        trader._evaluate_shadow_promotions(changes, change_log, set())

        info = trader._promoted_types["live_winner"]
        assert info.get("source") != "shadow_eval"
        assert info["n"] == 50  # untouched
        assert changes == []

    def test_bonferroni_kicks_in_with_many_strategies(self, db):
        # Edge-of-significance strategy fails when many strategies are tested.
        # Strategy A: 15/20 wins (raw p ≈ 0.025).
        for _ in range(15):
            _open_close_shadow(db, "edge_strat", "USD_JPY", True)
        for _ in range(5):
            _open_close_shadow(db, "edge_strat", "USD_JPY", False)
        # Add 9 noise strategies so num_tests=10 → Bonferroni inflates p.
        for i in range(9):
            for _ in range(20):
                _open_close_shadow(db, f"noise_{i}", "USD_JPY", True)
            for _ in range(20):
                _open_close_shadow(db, f"noise_{i}", "USD_JPY", False)

        trader = _FakeTrader(db)
        changes, change_log = [], []
        trader._evaluate_shadow_promotions(changes, change_log, set())

        info = trader._promoted_types["edge_strat"]
        assert info["status"] != "promoted"
        # Bonferroni-corrected p must exceed 0.05 in this batch.
        assert info["p_bonferroni"] >= 0.05

    def test_no_shadow_data_is_noop(self, db):
        # Empty shadow DB: function returns without writing anything.
        trader = _FakeTrader(db)
        changes, change_log = [], []
        trader._evaluate_shadow_promotions(changes, change_log, set())
        assert trader._promoted_types == {}
        assert changes == []
        assert change_log == []

    def test_does_not_pollute_n_cache(self, db):
        # Shadow path must NOT touch _strategy_n_cache (lot sizing input).
        for _ in range(26):
            _open_close_shadow(db, "trend_rebound", "USD_JPY", True)
        for _ in range(4):
            _open_close_shadow(db, "trend_rebound", "USD_JPY", False)

        trader = _FakeTrader(db)
        trader._strategy_n_cache = {}  # if the method touched it, key appears
        changes, change_log = [], []
        trader._evaluate_shadow_promotions(changes, change_log, set())

        assert "trend_rebound" not in trader._strategy_n_cache
