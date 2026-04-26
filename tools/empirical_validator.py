"""Empirical Validator — Statistical toolkit for shadow data analysis.

目的:
  Phase 1.5 Task 6 (`_POLICY` data-driven tuning) で必要な統計的
  validation 関数を提供する。pooled WR で意思決定する罠 (partial_quant_trap)
  を防止し、Wilson CI / Bonferroni / monotonicity / top-K-drop を強制。

提供関数:
  - wilson_ci: Wilson score interval for binomial proportion
  - bootstrap_ci: bootstrap percentile CI for arbitrary statistic
  - bootstrap_wr_ci: WR (binomial) の bootstrap CI
  - monotonicity_test: bin 順での順序単調性 (Spearman + permutation)
  - top_k_drop_test: 上位 K 件除いた統計の安定性
  - bonferroni_correct: multiple testing 補正
  - aggregate_3d: trades を (axis1, axis2, axis3) で 3D 集計
  - sample_size_for_proportion_diff: 必要 N 計算

設計原則:
  - numpy のみ依存 (scipy.stats は permutation で重いので使わない)
  - 副作用なし: 純粋関数群
  - 戻り値は dict (Phase 1.5 で JSON シリアライズしやすく)
  - 計算量を抑える (1000 リサンプル / 1000 permutation 上限)
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence, Optional

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    _HAS_NUMPY = False


# ─── Wilson CI ────────────────────────────────────────────────────────

def wilson_ci(n_success: int, n_total: int, alpha: float = 0.05) -> dict:
    """Wilson score interval for a binomial proportion.

    Phase 1.5 で WR の信頼区間を計算する標準関数。
    Bayesian-flavor の confidence interval、small N でも安定。

    Returns
    -------
    dict with: p, low, high, n, alpha
    """
    if n_total <= 0:
        return {"p": float("nan"), "low": float("nan"), "high": float("nan"),
                "n": n_total, "alpha": alpha}
    if not (0 <= n_success <= n_total):
        raise ValueError(f"n_success ({n_success}) out of range [0, {n_total}]")

    # 標準正規分布の (1-alpha/2) 分位 — alpha=0.05 → z=1.96
    # scipy なしで approximation: erfinv ベース
    z = _z_for_alpha(alpha)
    p = n_success / n_total
    n = n_total
    denom = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return {
        "p": p,
        "low": max(0.0, center - half),
        "high": min(1.0, center + half),
        "n": n_total,
        "alpha": alpha,
    }


def _z_for_alpha(alpha: float) -> float:
    """Approximate inverse standard normal CDF for two-sided (1-alpha) interval."""
    # よく使う値はテーブル化、それ以外は erf 近似
    if abs(alpha - 0.05) < 1e-9:
        return 1.959964
    if abs(alpha - 0.01) < 1e-9:
        return 2.575829
    if abs(alpha - 0.10) < 1e-9:
        return 1.644854
    # General case: Beasley-Springer-Moro 近似 (簡易版)
    # alpha=0.05 → z=1.96 のように、p=1-alpha/2 の inverse normal CDF
    p = 1 - alpha / 2
    # Acklam approximation
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((a[0] * q + a[1]) * q + a[2]) * q + a[3]) * q + a[4]) * q + a[5]) / \
               ((((b[0] * q + b[1]) * q + b[2]) * q + b[3]) * q + b[4] + 1)
    if p > 1 - 0.02425:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((a[0] * q + a[1]) * q + a[2]) * q + a[3]) * q + a[4]) * q + a[5]) / \
                ((((b[0] * q + b[1]) * q + b[2]) * q + b[3]) * q + b[4] + 1)
    q = p - 0.5
    r = q * q
    return q * (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


# ─── Bootstrap CI ────────────────────────────────────────────────────

def bootstrap_ci(values: Sequence[float], n_resample: int = 1000,
                 alpha: float = 0.05, statistic=None,
                 seed: Optional[int] = None) -> dict:
    """Generic bootstrap percentile CI for any statistic.

    Parameters
    ----------
    values : sequence of float
    n_resample : int
        Number of bootstrap samples (default 1000)
    alpha : float
        Two-sided alpha (default 0.05 → 95% CI)
    statistic : callable
        Function from sample to scalar. Default = np.mean
    seed : int
        For reproducibility

    Returns
    -------
    dict with: estimate, low, high, n, n_resample, alpha
    """
    if not _HAS_NUMPY:
        raise RuntimeError("bootstrap_ci requires numpy")

    arr = np.asarray(list(values), dtype=float)
    n = len(arr)
    if n == 0:
        return {"estimate": float("nan"), "low": float("nan"), "high": float("nan"),
                "n": 0, "n_resample": n_resample, "alpha": alpha}
    if statistic is None:
        statistic = np.mean

    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(n_resample):
        idx = rng.integers(0, n, size=n)
        samples.append(float(statistic(arr[idx])))

    samples = np.array(samples)
    estimate = float(statistic(arr))
    low = float(np.quantile(samples, alpha / 2))
    high = float(np.quantile(samples, 1 - alpha / 2))
    return {
        "estimate": estimate,
        "low": low,
        "high": high,
        "n": n,
        "n_resample": n_resample,
        "alpha": alpha,
    }


def bootstrap_wr_ci(pnls: Sequence[float], n_resample: int = 1000,
                    alpha: float = 0.05, seed: Optional[int] = None) -> dict:
    """Bootstrap CI for win rate (= fraction of pnl > 0)."""
    def wr(arr):
        return float((arr > 0).mean())

    if not _HAS_NUMPY:
        raise RuntimeError("bootstrap_wr_ci requires numpy")
    return bootstrap_ci(pnls, n_resample=n_resample, alpha=alpha,
                        statistic=wr, seed=seed)


# ─── Monotonicity test ────────────────────────────────────────────────

def monotonicity_test(bin_values: Sequence[float], wr_values: Sequence[float],
                      n_permutations: int = 1000, seed: Optional[int] = None) -> dict:
    """Test whether WR varies monotonically with bin index.

    Used to validate that 'higher confidence bin → higher WR' actually holds
    (calibration check). Spearman rank correlation + permutation p-value.

    Parameters
    ----------
    bin_values : sequence of float
        Bin centers/indices (e.g., [0, 1, 2, 3])
    wr_values : sequence of float
        Observed WR for each bin

    Returns
    -------
    dict with: spearman, p_value, monotonic, n_bins
        monotonic: True if |spearman| > 0.7 and p < 0.05
    """
    if not _HAS_NUMPY:
        raise RuntimeError("monotonicity_test requires numpy")
    if len(bin_values) != len(wr_values):
        raise ValueError("bin_values and wr_values must have same length")
    n = len(bin_values)
    if n < 3:
        return {"spearman": float("nan"), "p_value": float("nan"),
                "monotonic": False, "n_bins": n}

    bv = np.asarray(bin_values, dtype=float)
    wv = np.asarray(wr_values, dtype=float)

    obs = _spearman(bv, wv)

    rng = np.random.default_rng(seed)
    null_count = 0
    for _ in range(n_permutations):
        perm = rng.permutation(wv)
        if abs(_spearman(bv, perm)) >= abs(obs):
            null_count += 1
    p_val = (null_count + 1) / (n_permutations + 1)  # add-1 smoothing

    return {
        "spearman": float(obs),
        "p_value": float(p_val),
        "monotonic": bool(abs(obs) > 0.7 and p_val < 0.05),
        "n_bins": n,
    }


def _spearman(x: "np.ndarray", y: "np.ndarray") -> float:
    """Spearman rank correlation."""
    rx = np.argsort(np.argsort(x))
    ry = np.argsort(np.argsort(y))
    cx = rx - rx.mean()
    cy = ry - ry.mean()
    denom = math.sqrt(float((cx * cx).sum()) * float((cy * cy).sum()))
    if denom == 0:
        return 0.0
    return float((cx * cy).sum() / denom)


# ─── Top-K-drop test ─────────────────────────────────────────────────

def top_k_drop_test(values: Sequence[float], k: int = 1,
                    statistic=None) -> dict:
    """Compute statistic with and without top-K values to gauge stability.

    `feedback_partial_quant_trap` 要件: 「上位 1 サンプルを除いて結果が
    崩壊するなら、それは edge ではなく fluke」.

    Returns
    -------
    dict with: full, dropped, drop_pct, k, n
    """
    if not _HAS_NUMPY:
        raise RuntimeError("top_k_drop_test requires numpy")
    if statistic is None:
        statistic = np.mean

    arr = np.asarray(list(values), dtype=float)
    n = len(arr)
    if n == 0:
        return {"full": float("nan"), "dropped": float("nan"),
                "drop_pct": float("nan"), "k": k, "n": 0}
    if k >= n:
        return {"full": float(statistic(arr)), "dropped": float("nan"),
                "drop_pct": float("nan"), "k": k, "n": n}

    full = float(statistic(arr))
    sorted_arr = np.sort(arr)
    dropped_arr = sorted_arr[:-k]
    dropped = float(statistic(dropped_arr))
    drop_pct = (full - dropped) / full * 100 if full != 0 else float("nan")
    return {
        "full": full,
        "dropped": dropped,
        "drop_pct": drop_pct,
        "k": k,
        "n": n,
    }


# ─── Bonferroni correction ───────────────────────────────────────────

def bonferroni_correct(p_values: Sequence[float], alpha: float = 0.05) -> list[bool]:
    """Bonferroni-corrected significance: True iff p < alpha / m (m = #tests).

    Returns list of bool aligned with p_values.
    """
    pv = list(p_values)
    m = len(pv)
    if m == 0:
        return []
    threshold = alpha / m
    return [p is not None and p < threshold for p in pv]


def benjamini_hochberg(p_values: Sequence[float], alpha: float = 0.05) -> list[bool]:
    """Benjamini-Hochberg FDR control. Less conservative than Bonferroni.

    Returns list of bool (significant flags) aligned with input order.
    """
    pv = list(p_values)
    m = len(pv)
    if m == 0:
        return []
    indexed = sorted(enumerate(pv), key=lambda t: t[1])
    sig = [False] * m
    for rank, (orig_idx, p) in enumerate(indexed, start=1):
        if p < (rank / m) * alpha:
            # All up to this rank are significant under BH
            for j in range(rank):
                sig[indexed[j][0]] = True
    return sig


# ─── 3D Aggregation ──────────────────────────────────────────────────

def aggregate_3d(trades: Iterable[dict],
                 axis1: str, axis2: str, axis3: str,
                 pnl_key: str = "pnl_pips") -> list[dict]:
    """Aggregate trades by 3 axes, computing N/WR/EV/Wilson_CI per cell.

    Parameters
    ----------
    trades : iterable of dict
        Each dict must have axis1/axis2/axis3 keys + pnl_key.
    axis1, axis2, axis3 : str
        Keys to group by (e.g., "enhancer", "category", "raw_adj_bin").
    pnl_key : str

    Returns
    -------
    list of dict, one per non-empty cell:
        axis1, axis2, axis3, n, wr, ev, wilson_low, wilson_high
    """
    cells: dict[tuple, list[float]] = {}
    for t in trades:
        a1 = t.get(axis1)
        a2 = t.get(axis2)
        a3 = t.get(axis3)
        p = t.get(pnl_key)
        if p is None:
            continue
        key = (a1, a2, a3)
        cells.setdefault(key, []).append(float(p))

    rows = []
    for (a1, a2, a3), pnls in cells.items():
        n = len(pnls)
        wins = sum(1 for x in pnls if x > 0)
        wr = wins / n if n > 0 else float("nan")
        ev = sum(pnls) / n if n > 0 else float("nan")
        wci = wilson_ci(wins, n) if n > 0 else {"low": float("nan"), "high": float("nan")}
        rows.append({
            axis1: a1, axis2: a2, axis3: a3,
            "n": n, "wr": wr, "ev": ev,
            "wilson_low": wci["low"], "wilson_high": wci["high"],
        })
    rows.sort(key=lambda r: (str(r[axis1]), str(r[axis2]), str(r[axis3])))
    return rows


# ─── Sample size planner ─────────────────────────────────────────────

def sample_size_for_proportion_diff(p1: float, p2: float,
                                    alpha: float = 0.05,
                                    power: float = 0.80) -> int:
    """Required N per group to detect proportion difference (p1 vs p2).

    Two-sided test, equal allocation.
    Reference: Fleiss formula approximation.

    Parameters
    ----------
    p1, p2 : float
        Two proportions to distinguish (e.g., 0.40 vs 0.50)
    alpha : float
        Two-sided alpha (default 0.05)
    power : float
        Statistical power (default 0.80)

    Returns
    -------
    int
        Required sample size per group (rounded up).
    """
    if not (0 < p1 < 1 and 0 < p2 < 1):
        raise ValueError(f"p1, p2 must be in (0, 1): got {p1}, {p2}")
    if p1 == p2:
        return 0  # No difference to detect → indeterminate / ∞
    z_alpha = _z_for_alpha(alpha)
    z_beta = _z_for_alpha(2 * (1 - power))  # z for power
    p_bar = (p1 + p2) / 2
    q_bar = 1 - p_bar
    se_pooled = math.sqrt(2 * p_bar * q_bar)
    se_alt = math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    n = ((z_alpha * se_pooled + z_beta * se_alt) ** 2) / ((p1 - p2) ** 2)
    return int(math.ceil(n))
