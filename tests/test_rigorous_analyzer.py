"""Unit tests for RigorousAnalyzer — BE-WR formula and family-wise correction."""
from __future__ import annotations

import pandas as pd
import pytest

from research.edge_discovery.rigorous_analyzer import RigorousAnalyzer


def _make_df(rows):
    """rows: list of dicts with entry_type, instrument, pnl_pips, entry_time."""
    df = pd.DataFrame(rows)
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
    df["is_shadow"] = 0
    return df


# ──────────────────────────────────────────────────────
# _compute_breakeven_wr formula
# ──────────────────────────────────────────────────────
class TestBreakEvenWR:
    def test_cost_free_symmetric(self):
        """With cost=0 and equal win/loss: BE-WR = 0.5."""
        an = RigorousAnalyzer(df=pd.DataFrame(), cost_pips_roundtrip=0.0)
        s = pd.Series([3.0, 3.0, -3.0, -3.0])
        assert abs(an._compute_breakeven_wr(s) - 0.5) < 1e-9

    def test_cost_free_asymmetric(self):
        """win=3, loss=1, cost=0 → BE-WR = 1/(3+1) = 0.25."""
        an = RigorousAnalyzer(df=pd.DataFrame(), cost_pips_roundtrip=0.0)
        s = pd.Series([3.0, -1.0])
        assert abs(an._compute_breakeven_wr(s) - 0.25) < 1e-9

    def test_cost_symmetric_formula(self):
        """Validates corrected formula: BE-WR = (loss+cost)/(win+loss).

        Regression test for the bug where cost was added to denominator
        (former implementation used win+loss+cost in denom, under-estimated BE-WR).
        """
        an = RigorousAnalyzer(df=pd.DataFrame(), cost_pips_roundtrip=1.0)
        # win_avg=5, loss_avg=5 → BE = (5+1)/(5+5) = 0.6
        s = pd.Series([5.0, 5.0, -5.0, -5.0])
        assert abs(an._compute_breakeven_wr(s) - 0.6) < 1e-9

    def test_cost_penalty_direction(self):
        """Higher cost must produce higher BE-WR (more wins needed)."""
        s = pd.Series([3.0, -3.0])
        an_lo = RigorousAnalyzer(df=pd.DataFrame(), cost_pips_roundtrip=0.5)
        an_hi = RigorousAnalyzer(df=pd.DataFrame(), cost_pips_roundtrip=2.0)
        be_lo = an_lo._compute_breakeven_wr(s)
        be_hi = an_hi._compute_breakeven_wr(s)
        assert be_hi > be_lo, f"higher cost should raise BE-WR: lo={be_lo} hi={be_hi}"

    def test_all_wins_fallback(self):
        """No losses → use default breakeven_wr."""
        an = RigorousAnalyzer(df=pd.DataFrame(), breakeven_wr=0.5)
        s = pd.Series([1.0, 2.0, 3.0])
        assert an._compute_breakeven_wr(s) == 0.5

    def test_clamp_upper(self):
        """Extremely small wins vs large losses + huge cost → clamp at 0.90."""
        an = RigorousAnalyzer(df=pd.DataFrame(), cost_pips_roundtrip=100.0)
        s = pd.Series([0.1, -10.0])
        be = an._compute_breakeven_wr(s)
        assert be <= 0.90 + 1e-9


# ──────────────────────────────────────────────────────
# Family-wise correction (analyze_cross + analyze_dimensions share family)
# ──────────────────────────────────────────────────────
class TestFamilyWiseCorrection:
    def _synth_df(self, n_trades_per_strat=40, n_strats=5):
        """Synthetic dataset with multiple strategies, instruments, sessions.

        Makes one strategy (strat_0) structurally profitable so we can check
        that corrections behave sensibly when cross analysis adds more tests.
        """
        import numpy as np
        rng = np.random.RandomState(42)
        rows = []
        for si in range(n_strats):
            for k in range(n_trades_per_strat):
                mean = 0.5 if si == 0 else -0.1
                pnl = rng.normal(mean, 2.0)
                rows.append({
                    "entry_type": f"strat_{si}",
                    "instrument": "USD_JPY" if k % 2 == 0 else "EUR_USD",
                    "session": "tokyo" if k % 3 == 0 else "london_morn",
                    "pnl_pips": pnl,
                    "entry_time": f"2026-04-0{1 + k % 9}T{(k * 17) % 24:02d}:00:00",
                })
        df = pd.DataFrame(rows)
        df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
        df["is_shadow"] = 0
        df["is_win"] = (df["pnl_pips"] > 0).astype(int)
        return df

    def test_analyze_cross_uses_combined_family(self):
        """After analyze_dimensions + analyze_cross, Bonferroni uses total n_tests.

        Regression test: previous implementation corrected each batch
        separately (inflated false-positive rate for cross cells).
        Now finalize() re-runs corrections over the combined family.
        """
        df = self._synth_df()
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0)
        an.analyze_dimensions(["entry_type", "instrument"])
        n_after_dims = len(an.all_pockets)
        an.analyze_cross("entry_type", "instrument", min_n=5)
        n_after_cross = len(an.all_pockets)
        assert n_after_cross > n_after_dims, "cross should add more pockets"

        # Bonferroni threshold must be alpha / total_family_size
        expected_bonf = an.alpha / n_after_cross
        # Check: every pocket's bonf_significant flag reflects the global threshold
        for p in an.all_pockets:
            if p.p_value < expected_bonf:
                assert p.bonf_significant is True, (
                    f"pocket {p.key} with p={p.p_value} < {expected_bonf} "
                    f"should be Bonf-significant under combined family"
                )
            else:
                assert p.bonf_significant is False, (
                    f"pocket {p.key} with p={p.p_value} >= {expected_bonf} "
                    f"should NOT be Bonf-significant under combined family"
                )

    def test_finalize_idempotent(self):
        """finalize() can be called multiple times without changing results."""
        df = self._synth_df()
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0)
        an.analyze_dimensions(["entry_type"])
        snapshot = [(p.bonf_significant, p.fdr_significant, p.recommendation)
                    for p in an.all_pockets]
        an.finalize()
        snapshot2 = [(p.bonf_significant, p.fdr_significant, p.recommendation)
                     for p in an.all_pockets]
        assert snapshot == snapshot2

    def test_empty_analyzer_safe(self):
        df = pd.DataFrame(columns=["entry_type", "pnl_pips", "entry_time", "is_shadow"])
        an = RigorousAnalyzer(df=df)
        an.analyze_dimensions(["entry_type"])
        assert an.all_pockets == []
        an.finalize()  # Should not raise
        assert an.report() is not None


# ──────────────────────────────────────────────────────
# Regime conditioning + reweighting
# (conditional-edge-estimand-2026-04-17.md)
# ──────────────────────────────────────────────────────
class TestRegimeConditioning:
    def _make_regime_df(self, regimes_and_pnl):
        """regimes_and_pnl: list of (regime, pnl) tuples."""
        import numpy as np
        rows = []
        base_time = pd.Timestamp("2026-04-10T00:00:00Z")
        for i, (r, pnl) in enumerate(regimes_and_pnl):
            rows.append({
                "entry_type": "strat_A",
                "instrument": "EUR_USD",
                "pnl_pips": pnl,
                "entry_time": base_time + pd.Timedelta(minutes=i * 30),
                "is_shadow": 0,
                "regime_independent": r,
            })
        df = pd.DataFrame(rows)
        df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
        return df

    def test_no_pi_no_reweight(self):
        """Without pi_long_run, θ_reweighted stays None (backward compatible)."""
        df = self._make_regime_df([("up_trend", 1.0)] * 20)
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        assert p.theta_reweighted is None
        assert p.regime_support is None

    def test_full_support_classification(self):
        """All 3 regimes with n>=30 → FULL."""
        rows = []
        for r in ["up_trend", "down_trend", "range"]:
            rows.extend([(r, 0.5)] * 30)
        df = self._make_regime_df(rows)
        pi = {"up_trend": 0.4, "down_trend": 0.4, "range": 0.2}
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0, pi_long_run=pi)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        assert p.regime_support == "FULL"

    def test_partial_support_classification(self):
        """All regimes n>=10 but some <30 → PARTIAL."""
        rows = [("up_trend", 0.5)] * 40 + [("down_trend", 0.5)] * 15 + [("range", 0.5)] * 15
        df = self._make_regime_df(rows)
        pi = {"up_trend": 0.4, "down_trend": 0.4, "range": 0.2}
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0, pi_long_run=pi)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        assert p.regime_support == "PARTIAL"

    def test_insufficient_support_classification(self):
        """Any regime with n<10 → INSUFFICIENT."""
        rows = [("up_trend", 0.5)] * 50 + [("down_trend", 0.5)] * 5
        # range: 0 samples
        df = self._make_regime_df(rows)
        pi = {"up_trend": 0.4, "down_trend": 0.4, "range": 0.2}
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0, pi_long_run=pi)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        assert p.regime_support == "INSUFFICIENT"

    def test_reweighted_theta_formula(self):
        """θ_reweighted = Σ_r π(r)/w_sum · Ê[pnl|r] with renormalization.

        40 trades up @ +2, 40 trades down @ -1, 40 trades range @ +0
        π = {up: 0.5, down: 0.3, range: 0.2}
        Expected: 0.5*2 + 0.3*(-1) + 0.2*0 = 0.7p
        """
        rows = [("up_trend", 2.0)] * 40 + [("down_trend", -1.0)] * 40 + [("range", 0.0)] * 40
        df = self._make_regime_df(rows)
        pi = {"up_trend": 0.5, "down_trend": 0.3, "range": 0.2}
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0, pi_long_run=pi)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        expected = 0.5 * 2.0 + 0.3 * (-1.0) + 0.2 * 0.0
        assert abs(p.theta_reweighted - expected) < 1e-6, (
            f"expected {expected}, got {p.theta_reweighted}"
        )

    def test_reweighted_drops_missing_regime(self):
        """If a regime has no data, it's dropped and π renormalized over present regimes."""
        # Only up and down present, no range
        rows = [("up_trend", 2.0)] * 40 + [("down_trend", -2.0)] * 40
        df = self._make_regime_df(rows)
        pi = {"up_trend": 0.4, "down_trend": 0.4, "range": 0.2}
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0, pi_long_run=pi)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        # Renormalized: up=0.5, down=0.5 → θ = 0
        assert abs(p.theta_reweighted - 0.0) < 1e-6

    def test_insufficient_overrides_recommendation(self):
        """INSUFFICIENT support → forced WEAK even if Bonferroni significant.

        Strongly positive up_trend data to trigger Bonferroni significance,
        insufficient other regimes.
        """
        rows = [("up_trend", 3.0)] * 100 + [("down_trend", 3.0)] * 5
        # range missing → INSUFFICIENT
        df = self._make_regime_df(rows)
        pi = {"up_trend": 0.4, "down_trend": 0.4, "range": 0.2}
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0, pi_long_run=pi)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        assert p.regime_support == "INSUFFICIENT"
        assert p.recommendation == "WEAK", (
            f"INSUFFICIENT support should force WEAK, got {p.recommendation}"
        )

    def test_negative_theta_overrides_positive_marginal(self):
        """Marginal positive but reweighted θ* < 0 → forced WEAK.

        Construct sample where sample regime mix (heavy up_trend) gives positive
        marginal, but reweighting with π heavy on down_trend flips sign.
        """
        # Sample: 100 up @ +3, 30 down @ -8 → marginal = (100*3 + 30*(-8)) / 130 = +0.46
        # With 30 range trades @ 0 too (to satisfy support)
        rows = (
            [("up_trend", 3.0)] * 100
            + [("down_trend", -8.0)] * 30
            + [("range", 0.0)] * 30
        )
        df = self._make_regime_df(rows)
        # Make Bonferroni likely: check p_value low
        # π heavy on down_trend → negative θ* expected
        pi = {"up_trend": 0.2, "down_trend": 0.6, "range": 0.2}
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0, pi_long_run=pi)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        # θ* = 0.2*3 + 0.6*(-8) + 0.2*0 = 0.6 - 4.8 = -4.2
        assert p.theta_reweighted < 0
        # Even if marginal positive → forced WEAK
        assert p.recommendation == "WEAK"

    def test_se_reweighted_nonzero(self):
        """SE is populated and positive when regimes have variance."""
        import numpy as np
        rng = np.random.RandomState(0)
        rows = []
        for r, mean in [("up_trend", 1.0), ("down_trend", -0.5), ("range", 0.2)]:
            for _ in range(50):
                rows.append((r, float(rng.normal(mean, 1.5))))
        df = self._make_regime_df(rows)
        pi = {"up_trend": 0.4, "down_trend": 0.4, "range": 0.2}
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0, pi_long_run=pi)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        assert p.se_reweighted is not None
        assert p.se_reweighted > 0

    def test_regime_breakdown_populated(self):
        """regime_breakdown contains n, avg, std for each present regime."""
        rows = [("up_trend", 1.0)] * 40 + [("down_trend", -1.0)] * 40 + [("range", 0.0)] * 40
        df = self._make_regime_df(rows)
        pi = {"up_trend": 0.4, "down_trend": 0.4, "range": 0.2}
        an = RigorousAnalyzer(df=df, cost_pips_roundtrip=0.0, pi_long_run=pi)
        an.analyze_dimensions(["entry_type"])
        p = an.all_pockets[0]
        assert "up_trend" in p.regime_breakdown
        assert p.regime_breakdown["up_trend"]["n"] == 40
        assert abs(p.regime_breakdown["up_trend"]["avg"] - 1.0) < 1e-9
