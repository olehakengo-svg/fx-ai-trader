"""
P1 Promotion Engine Verification Tests
=======================================

Tests for the statistical and risk analytics functions that drive
the P1 promotion/demotion engine:
  - Binomial test for win-rate significance
  - Bayesian posterior for win-rate estimation
  - Historical VaR / CVaR
  - Monte Carlo ruin probability
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np

from modules.stats_utils import binomial_test_wr, bayesian_wr_posterior
from modules.risk_analytics import calculate_var_cvar, monte_carlo_ruin


# =====================================================================
#  Binomial Test (3 tests)
# =====================================================================

class TestBinomialTest:
    def test_binomial_significant_above_threshold(self):
        """N=30, W=20 (WR=67%) with null_wr=0.45 should be significant."""
        result = binomial_test_wr(wins=20, n=30, null_wr=0.45)
        assert result["significant"] is True, (
            f"Expected significant=True for WR=67%, null=45%, "
            f"got p_value={result['p_value']}"
        )

    def test_binomial_not_significant_near_null(self):
        """N=30, W=14 (WR=47%) with null_wr=0.45 should not be significant."""
        result = binomial_test_wr(wins=14, n=30, null_wr=0.45)
        assert result["significant"] is False, (
            f"Expected significant=False for WR=47%, null=45%, "
            f"got p_value={result['p_value']}"
        )

    def test_binomial_p_value_range(self):
        """p_value must always be in [0, 1] for any input."""
        test_cases = [
            (0, 30, 0.45),
            (15, 30, 0.45),
            (30, 30, 0.45),
            (5, 10, 0.50),
            (1, 1, 0.50),
        ]
        for wins, n, null_wr in test_cases:
            result = binomial_test_wr(wins=wins, n=n, null_wr=null_wr)
            assert 0 <= result["p_value"] <= 1, (
                f"p_value={result['p_value']} out of [0,1] "
                f"for wins={wins}, n={n}, null_wr={null_wr}"
            )


# =====================================================================
#  Bayesian Posterior (3 tests)
# =====================================================================

class TestBayesianPosterior:
    def test_bayesian_uniform_prior(self):
        """With N=0 and uniform prior Beta(1,1), posterior_mean should be 0.5."""
        result = bayesian_wr_posterior(wins=0, n=0)
        assert abs(result["posterior_mean"] - 0.5) < 0.01, (
            f"Expected posterior_mean ~ 0.5, got {result['posterior_mean']}"
        )

    def test_bayesian_strong_evidence(self):
        """N=50, W=30 (WR=60%) should yield p_wr_above_45 > 0.90."""
        result = bayesian_wr_posterior(wins=30, n=50)
        assert result["p_wr_above_45"] > 0.90, (
            f"Expected P(WR>45%) > 0.90 for 30/50, "
            f"got {result['p_wr_above_45']}"
        )

    def test_bayesian_ci_covers_true_rate(self):
        """N=100, W=55 (WR=55%) -> 90% CI should contain 0.55."""
        result = bayesian_wr_posterior(wins=55, n=100)
        ci_low, ci_high = result["ci_90"]
        assert ci_low <= 0.55 <= ci_high, (
            f"90% CI [{ci_low}, {ci_high}] does not contain true rate 0.55"
        )


# =====================================================================
#  VaR / CVaR (3 tests)
# =====================================================================

class TestVarCvar:
    def test_cvar_exceeds_var(self):
        """CVaR (Expected Shortfall) should be >= VaR for any distribution.

        Both are reported as positive loss magnitudes in this implementation.
        """
        np.random.seed(123)
        pnl = list(np.random.normal(0, 10, 200))
        result = calculate_var_cvar(pnl)
        assert result["cvar95"] >= result["var95"], (
            f"CVaR95={result['cvar95']} should be >= VaR95={result['var95']}"
        )

    def test_var_known_distribution(self):
        """Uniform(-10, 10) -> VaR95 should be approximately 9.0.

        The 5th percentile of Uniform(-10,10) is -9.0,
        so VaR95 (reported as positive) should be ~9.0.
        """
        np.random.seed(42)
        pnl = list(np.random.uniform(-10, 10, 10000))
        result = calculate_var_cvar(pnl)
        assert abs(result["var95"] - 9.0) < 0.5, (
            f"VaR95={result['var95']}, expected ~9.0 for Uniform(-10,10)"
        )

    def test_var_all_positive(self):
        """All-positive PnL should yield VaR95 <= 0 (no loss at 5th percentile).

        When all values are positive, the 5th percentile is positive,
        so negating it gives a negative VaR (i.e., no loss).
        """
        pnl = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
        result = calculate_var_cvar(pnl)
        assert result["var95"] <= 0, (
            f"VaR95={result['var95']} should be <= 0 for all-positive PnL"
        )


# =====================================================================
#  Monte Carlo Ruin (3 tests)
# =====================================================================

class TestMonteCarloRuin:
    def test_mc_positive_ev_low_ruin(self):
        """Strongly positive PnL data should produce low ruin probability."""
        # Trades with strong positive expectation: mean ~ +8
        pnl = [10.0, 8.0, 12.0, -2.0, 9.0, 11.0, 7.0, -1.0, 13.0, 6.0,
               10.0, 8.0, 12.0, -2.0, 9.0, 11.0, 7.0, -1.0, 13.0, 6.0]
        result = monte_carlo_ruin(
            pnl, initial_capital=1000.0, ruin_dd_pct=0.50,
            n_simulations=5000, n_trades_forward=300, seed=42,
        )
        assert result["ruin_probability"] < 0.5, (
            f"Ruin prob={result['ruin_probability']} should be < 0.5 "
            f"for strongly positive EV data"
        )

    def test_mc_negative_ev_high_ruin(self):
        """Strongly negative PnL data should produce high ruin probability."""
        # Trades with strong negative expectation: mean ~ -8
        pnl = [-10.0, -8.0, -12.0, 2.0, -9.0, -11.0, -7.0, 1.0, -13.0, -6.0,
               -10.0, -8.0, -12.0, 2.0, -9.0, -11.0, -7.0, 1.0, -13.0, -6.0]
        result = monte_carlo_ruin(
            pnl, initial_capital=1000.0, ruin_dd_pct=0.50,
            n_simulations=5000, n_trades_forward=300, seed=42,
        )
        assert result["ruin_probability"] > 0.5, (
            f"Ruin prob={result['ruin_probability']} should be > 0.5 "
            f"for strongly negative EV data"
        )

    def test_mc_reproducibility(self):
        """Same seed should produce identical ruin probability."""
        pnl = [5.0, -3.0, 4.0, -2.0, 6.0, -1.0, 3.0, -4.0, 7.0, -2.0]
        kwargs = dict(
            initial_capital=1000.0, ruin_dd_pct=0.50,
            n_simulations=2000, n_trades_forward=200, seed=99,
        )
        result1 = monte_carlo_ruin(pnl, **kwargs)
        result2 = monte_carlo_ruin(pnl, **kwargs)
        assert result1["ruin_probability"] == result2["ruin_probability"], (
            f"Run1={result1['ruin_probability']} != "
            f"Run2={result2['ruin_probability']} with same seed"
        )
