"""
HMM Regime Detector -- 2-state regime detection for FX markets.

Two classes:
  1. HMMRegimeDetector (legacy) -- threshold-based calm/turbulent for lot sizing
  2. HMMRegime (new, v1) -- Gaussian HMM with Baum-Welch for trending/ranging comparison

Academic references:
  - Hamilton (1989): Markov-switching model for financial markets
  - Nystrup et al (2024, JAM): HMM regime detection reduces MaxDD by 50%
  - Ang & Bekaert (2002): Regime-dependent risk premia

Implementation:
  - numpy only (no hmmlearn dependency)
  - Forward algorithm for state probability estimation
  - Viterbi decoding for most likely state sequence
  - Baum-Welch (EM) for parameter estimation
  - State 0: "ranging" (low volatility, mean-reverting)
  - State 1: "trending" (high volatility, directional)
"""
import numpy as np
from typing import List, Tuple, Dict, Optional


# ═══════════════════════════════════════════════════════
#  Legacy: HMMRegimeDetector (calm/turbulent for lot sizing)
# ═══════════════════════════════════════════════════════

class HMMRegimeDetector:
    """2-state HMM proxy for FX volatility regime detection.

    State 0: calm (low vol)   -> full position (1.0x)
    State 1: turbulent (high vol) -> reduced position (0.3x)

    Uses threshold-based detection as a lightweight HMM approximation
    without requiring hmmlearn or scipy dependencies.
    """

    TURBULENT_THRESHOLD = 1.5
    CALM_THRESHOLD      = 1.0

    CALM_MULTIPLIER     = 1.0
    TURBULENT_MULTIPLIER = 0.3

    def __init__(self, lookback: int = 60):
        self.lookback = lookback
        self._current_state: int = 0
        self._state_probs: List[float] = [1.0, 0.0]
        self._vol_ratio: float = 1.0

    def update(self, returns: list) -> int:
        if len(returns) < self.lookback:
            return self._current_state

        recent = np.array(returns[-20:])
        full = np.array(returns[-self.lookback:])

        current_vol = np.std(recent) if len(recent) > 1 else 0.0

        rolling_vols = []
        for i in range(0, len(full) - 20 + 1, 5):
            window = full[i:i + 20]
            if len(window) > 1:
                rolling_vols.append(np.std(window))

        if not rolling_vols:
            return self._current_state

        median_vol = np.median(rolling_vols)
        ratio = current_vol / median_vol if median_vol > 0 else 1.0
        self._vol_ratio = ratio

        if ratio > self.TURBULENT_THRESHOLD:
            self._current_state = 1
        elif ratio < self.CALM_THRESHOLD:
            self._current_state = 0

        p_turb = min(ratio / 2.0, 1.0)
        self._state_probs = [1.0 - p_turb, p_turb]

        return self._current_state

    @property
    def current_state(self) -> int:
        return self._current_state

    @property
    def state_probs(self) -> Tuple[float, float]:
        return tuple(self._state_probs)

    @property
    def is_turbulent(self) -> bool:
        return self._current_state == 1

    @property
    def is_calm(self) -> bool:
        return self._current_state == 0

    @property
    def lot_multiplier(self) -> float:
        return self.TURBULENT_MULTIPLIER if self.is_turbulent else self.CALM_MULTIPLIER

    @property
    def vol_ratio(self) -> float:
        return self._vol_ratio

    def get_regime_label(self) -> str:
        if self.is_turbulent:
            return f"TURBULENT (vol_ratio={self._vol_ratio:.2f}, lot={self.lot_multiplier:.1f}x)"
        return f"CALM (vol_ratio={self._vol_ratio:.2f}, lot={self.lot_multiplier:.1f}x)"

    def reset(self):
        self._current_state = 0
        self._state_probs = [1.0, 0.0]
        self._vol_ratio = 1.0


# ═══════════════════════════════════════════════════════
#  New: HMMRegime -- 2-state Gaussian HMM (numpy only)
# ═══════════════════════════════════════════════════════

class HMMRegime:
    """2-state Gaussian HMM for trending/ranging regime detection.

    Uses log returns as the observable. State classification:
      - State 0: "ranging"  (low volatility, mean-reverting)
      - State 1: "trending" (high volatility, directional)

    Two operational modes:
      1. Full HMM (after fit): Baum-Welch estimated parameters + forward algorithm
      2. Fallback (no fit): Rolling volatility heuristic (robust, always works)

    All implementation uses numpy only -- no hmmlearn or scipy dependency.
    """

    # Minimum observations for fit
    MIN_FIT_OBS = 100
    # Rolling window for volatility computation
    VOL_WINDOW = 20

    def __init__(self):
        # Per-symbol fitted parameters
        self._params: Dict[str, dict] = {}
        # Agreement tracking: {symbol: {"agree": int, "total": int}}
        self._agreement: Dict[str, dict] = {}

    # ── Baum-Welch (EM) fitting ──────────────────────────

    def fit(self, returns: np.ndarray, symbol: str = "USD_JPY",
            max_iter: int = 50, tol: float = 1e-4) -> dict:
        """Fit 2-state Gaussian HMM on historical returns via Baum-Welch EM.

        Args:
            returns: 1D array of log returns (or simple returns).
            symbol: Instrument identifier for storing parameters.
            max_iter: Maximum EM iterations.
            tol: Convergence tolerance on log-likelihood.

        Returns:
            Dict with fitted parameters and diagnostics.
        """
        returns = np.asarray(returns, dtype=np.float64).ravel()
        # Remove NaN/inf
        mask = np.isfinite(returns)
        returns = returns[mask]

        if len(returns) < self.MIN_FIT_OBS:
            raise ValueError(
                f"Need at least {self.MIN_FIT_OBS} observations, got {len(returns)}"
            )

        T = len(returns)
        K = 2  # number of states

        # ── Initialize parameters with K-means-style split ──
        # Sort returns by rolling volatility to separate regimes
        vol = self._rolling_std(returns, self.VOL_WINDOW)
        median_vol = np.median(vol[self.VOL_WINDOW:])  # skip initial NaN window

        # Assign initial states: low vol -> state 0 (ranging), high vol -> state 1 (trending)
        init_states = (vol > median_vol).astype(int)
        # First VOL_WINDOW elements: assign based on overall median
        init_states[:self.VOL_WINDOW] = 0

        # Initial emission parameters from state assignments
        mu = np.zeros(K)
        sigma = np.zeros(K)
        for k in range(K):
            mask_k = init_states == k
            if np.sum(mask_k) > 2:
                mu[k] = np.mean(returns[mask_k])
                sigma[k] = max(np.std(returns[mask_k]), 1e-8)
            else:
                mu[k] = np.mean(returns) + (k - 0.5) * np.std(returns)
                sigma[k] = max(np.std(returns), 1e-8)

        # Ensure state 1 (trending) has higher volatility
        if sigma[0] > sigma[1]:
            mu[0], mu[1] = mu[1], mu[0]
            sigma[0], sigma[1] = sigma[1], sigma[0]

        # Initial transition matrix: slight persistence bias
        A = np.array([[0.95, 0.05],
                      [0.05, 0.95]])

        # Initial state distribution
        pi = np.array([0.6, 0.4])

        # ── Baum-Welch EM ──
        prev_ll = -np.inf

        for iteration in range(max_iter):
            # E-step: forward-backward
            log_B = self._log_emission(returns, mu, sigma)
            alpha, log_ll = self._forward(log_B, np.log(A + 1e-300), np.log(pi + 1e-300))
            beta = self._backward(log_B, np.log(A + 1e-300))

            # Check convergence
            if abs(log_ll - prev_ll) < tol and iteration > 0:
                break
            prev_ll = log_ll

            # Compute gamma (state posteriors) and xi (transition posteriors)
            gamma = alpha + beta
            gamma -= _logsumexp_2d(gamma)  # normalize across states
            gamma = np.exp(gamma)

            # M-step: update parameters
            for k in range(K):
                gk = gamma[:, k]
                gk_sum = np.sum(gk) + 1e-300
                mu[k] = np.sum(gk * returns) / gk_sum
                diff = returns - mu[k]
                sigma[k] = max(np.sqrt(np.sum(gk * diff**2) / gk_sum), 1e-8)

            # Update transition matrix
            log_A = np.log(A + 1e-300)
            for i in range(K):
                for j in range(K):
                    # xi(t, i, j) = alpha(t,i) * a(i,j) * b(j, o_{t+1}) * beta(t+1, j) / P(O)
                    log_xi = (alpha[:-1, i] + log_A[i, j] +
                              log_B[1:, j] + beta[1:, j])
                    log_xi -= _logsumexp_1d(alpha[:-1, i] + beta[:-1, i])
                    A[i, j] = max(np.sum(np.exp(log_xi)), 1e-300)
                row_sum = np.sum(A[i, :])
                if row_sum > 0:
                    A[i, :] /= row_sum

            # Update initial distribution
            pi = gamma[0, :]
            pi = np.maximum(pi, 1e-300)
            pi /= np.sum(pi)

        # Ensure state 0 = ranging (lower sigma), state 1 = trending (higher sigma)
        if sigma[0] > sigma[1]:
            mu[0], mu[1] = mu[1], mu[0]
            sigma[0], sigma[1] = sigma[1], sigma[0]
            A = A[[1, 0], :][:, [1, 0]]
            pi = pi[[1, 0]]

        params = {
            "mu": mu.tolist(),
            "sigma": sigma.tolist(),
            "A": A.tolist(),
            "pi": pi.tolist(),
            "log_likelihood": float(log_ll),
            "n_iter": iteration + 1,
            "n_obs": T,
            "symbol": symbol,
        }
        self._params[symbol] = params
        return params

    # ── Prediction ───────────────────────────────────────

    def predict(self, returns: np.ndarray, symbol: str = "USD_JPY") -> str:
        """Return 'trending' or 'ranging' for the current regime.

        Uses fitted HMM if available, otherwise falls back to rolling
        volatility heuristic.
        """
        proba = self.predict_proba(returns, symbol)
        return "trending" if proba["trending"] >= 0.5 else "ranging"

    def predict_proba(self, returns: np.ndarray, symbol: str = "USD_JPY") -> dict:
        """Return {'trending': P, 'ranging': 1-P} for the current state.

        Uses fitted HMM forward algorithm if available, otherwise
        rolling volatility heuristic.
        """
        returns = np.asarray(returns, dtype=np.float64).ravel()
        mask = np.isfinite(returns)
        returns = returns[mask]

        if len(returns) < self.VOL_WINDOW:
            return {"trending": 0.5, "ranging": 0.5}

        # If fitted params exist, use forward algorithm
        if symbol in self._params:
            return self._predict_hmm(returns, symbol)

        # Fallback: rolling volatility heuristic
        return self._predict_heuristic(returns)

    def _predict_hmm(self, returns: np.ndarray, symbol: str) -> dict:
        """Predict using fitted HMM parameters and forward algorithm."""
        p = self._params[symbol]
        mu = np.array(p["mu"])
        sigma = np.array(p["sigma"])
        A = np.array(p["A"])
        pi = np.array(p["pi"])

        log_B = self._log_emission(returns, mu, sigma)
        alpha, _ = self._forward(log_B, np.log(A + 1e-300), np.log(pi + 1e-300))

        # Last time step posterior (normalized alpha)
        last_alpha = alpha[-1, :]
        log_norm = _logsumexp_1d(last_alpha)
        probs = np.exp(last_alpha - log_norm)

        return {
            "ranging": float(np.clip(probs[0], 0, 1)),
            "trending": float(np.clip(probs[1], 0, 1)),
        }

    def _predict_heuristic(self, returns: np.ndarray) -> dict:
        """Fallback: rolling volatility vs median heuristic.

        Simple but effective proxy for HMM states:
        - Compute rolling 20-period return std
        - If current std > median(all stds) -> trending
        - If current std <= median -> ranging
        - Smooth with sigmoid for probability output
        """
        vol = self._rolling_std(returns, self.VOL_WINDOW)
        # Use only valid (non-NaN) volatilities
        valid_vol = vol[self.VOL_WINDOW:]
        if len(valid_vol) < 2:
            return {"trending": 0.5, "ranging": 0.5}

        current_vol = valid_vol[-1]
        median_vol = np.median(valid_vol)

        if median_vol <= 0:
            return {"trending": 0.5, "ranging": 0.5}

        # Ratio-based probability with sigmoid smoothing
        ratio = current_vol / median_vol
        # sigmoid centered at 1.0: ratio=1 -> 0.5, ratio=2 -> ~0.88, ratio=0.5 -> ~0.12
        p_trending = 1.0 / (1.0 + np.exp(-3.0 * (ratio - 1.0)))

        return {
            "trending": float(np.clip(p_trending, 0, 1)),
            "ranging": float(np.clip(1.0 - p_trending, 0, 1)),
        }

    # ── Agreement tracking ───────────────────────────────

    def record_agreement(self, symbol: str, rule_regime: str, hmm_regime: str):
        """Track agreement between rule-based and HMM regime detection."""
        if symbol not in self._agreement:
            self._agreement[symbol] = {"agree": 0, "total": 0}
        self._agreement[symbol]["total"] += 1
        # Normalize: rule-based uses RANGE/TREND_BULL/TREND_BEAR
        rule_simplified = "ranging" if rule_regime == "RANGE" else "trending"
        if rule_simplified == hmm_regime:
            self._agreement[symbol]["agree"] += 1

    def get_agreement_rate(self, symbol: str = "USD_JPY") -> float:
        """Return agreement rate (0.0-1.0) for the given symbol."""
        stats = self._agreement.get(symbol, {"agree": 0, "total": 0})
        if stats["total"] == 0:
            return 0.0
        return stats["agree"] / stats["total"]

    def get_status(self) -> dict:
        """Return status for all symbols: fitted state, prediction, agreement."""
        status = {}
        for symbol in set(list(self._params.keys()) + list(self._agreement.keys())):
            s = {
                "fitted": symbol in self._params,
                "agreement_rate": self.get_agreement_rate(symbol),
                "agreement_total": self._agreement.get(symbol, {}).get("total", 0),
            }
            if symbol in self._params:
                p = self._params[symbol]
                s["params"] = {
                    "mu": p["mu"],
                    "sigma": p["sigma"],
                    "n_obs": p["n_obs"],
                    "n_iter": p["n_iter"],
                    "log_likelihood": p["log_likelihood"],
                }
            status[symbol] = s
        return status

    # ── HMM internals (numpy only) ───────────────────────

    @staticmethod
    def _log_emission(obs: np.ndarray, mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
        """Compute log emission probabilities: log N(obs | mu_k, sigma_k).

        Returns:
            (T, K) array of log probabilities.
        """
        T = len(obs)
        K = len(mu)
        log_B = np.zeros((T, K))
        for k in range(K):
            diff = obs - mu[k]
            log_B[:, k] = -0.5 * np.log(2 * np.pi) - np.log(sigma[k]) - 0.5 * (diff / sigma[k])**2
        return log_B

    @staticmethod
    def _forward(log_B: np.ndarray, log_A: np.ndarray, log_pi: np.ndarray):
        """Forward algorithm in log space.

        Args:
            log_B: (T, K) log emission probabilities
            log_A: (K, K) log transition matrix
            log_pi: (K,) log initial state distribution

        Returns:
            alpha: (T, K) log forward probabilities
            log_likelihood: float
        """
        T, K = log_B.shape
        alpha = np.full((T, K), -np.inf)

        # Initialization
        alpha[0, :] = log_pi + log_B[0, :]

        # Recursion
        for t in range(1, T):
            for j in range(K):
                alpha[t, j] = _logsumexp_1d(alpha[t-1, :] + log_A[:, j]) + log_B[t, j]

        log_ll = _logsumexp_1d(alpha[-1, :])
        return alpha, float(log_ll)

    @staticmethod
    def _backward(log_B: np.ndarray, log_A: np.ndarray) -> np.ndarray:
        """Backward algorithm in log space.

        Returns:
            beta: (T, K) log backward probabilities
        """
        T, K = log_B.shape
        beta = np.full((T, K), -np.inf)
        beta[-1, :] = 0.0  # log(1) = 0

        for t in range(T - 2, -1, -1):
            for i in range(K):
                beta[t, i] = _logsumexp_1d(log_A[i, :] + log_B[t+1, :] + beta[t+1, :])

        return beta

    @staticmethod
    def _viterbi(log_B: np.ndarray, log_A: np.ndarray, log_pi: np.ndarray) -> np.ndarray:
        """Viterbi decoding for most likely state sequence.

        Returns:
            states: (T,) array of most likely state indices
        """
        T, K = log_B.shape
        delta = np.full((T, K), -np.inf)
        psi = np.zeros((T, K), dtype=int)

        delta[0, :] = log_pi + log_B[0, :]

        for t in range(1, T):
            for j in range(K):
                scores = delta[t-1, :] + log_A[:, j]
                psi[t, j] = np.argmax(scores)
                delta[t, j] = scores[psi[t, j]] + log_B[t, j]

        # Backtrace
        states = np.zeros(T, dtype=int)
        states[-1] = np.argmax(delta[-1, :])
        for t in range(T - 2, -1, -1):
            states[t] = psi[t + 1, states[t + 1]]

        return states

    @staticmethod
    def _rolling_std(arr: np.ndarray, window: int) -> np.ndarray:
        """Compute rolling standard deviation using numpy only."""
        n = len(arr)
        result = np.full(n, np.nan)
        for i in range(window, n):
            result[i] = np.std(arr[i - window:i])
        return result


# ── Utility: log-sum-exp (numerically stable) ────────

def _logsumexp_1d(x: np.ndarray) -> float:
    """Log-sum-exp for 1D array."""
    x = np.asarray(x, dtype=np.float64)
    m = np.max(x)
    if not np.isfinite(m):
        return float(m)
    return float(m + np.log(np.sum(np.exp(x - m))))


def _logsumexp_2d(x: np.ndarray) -> np.ndarray:
    """Log-sum-exp across axis=1 for 2D array, broadcast back to (T, K)."""
    m = np.max(x, axis=1, keepdims=True)
    return m + np.log(np.sum(np.exp(x - m), axis=1, keepdims=True))
