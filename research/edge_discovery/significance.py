"""
Statistical significance corrections for multi-dimensional edge discovery.

既存 `tools/bt_scanner.py` の Bonferroni 判定と同じ流儀に合わせ、
さらに Benjamini-Hochberg FDR と Walk-forward stability を統合。

* Binomial one-sided test: WR > BE-WR
* Bonferroni: α = α0 / n_tests
* BH FDR: expected proportion of false discoveries ≤ q
* WF stability: IS→OOS で同方向・N folds で stable
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional


# ──────────────────────────────────────────────────────
# 基本統計
# ──────────────────────────────────────────────────────
def binomial_one_sided_p(k: int, n: int, p0: float) -> float:
    """H0: p = p0 の下で、k以上の勝ちが出る確率 P(K >= k)."""
    if n <= 0:
        return 1.0
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    # 正規近似 (n >= 30) or 厳密計算 (n < 30)
    if n < 30:
        return _exact_binom_tail(k, n, p0)
    mu = n * p0
    sd = math.sqrt(n * p0 * (1 - p0))
    if sd == 0:
        return 0.0 if k > mu else 1.0
    z = (k - 0.5 - mu) / sd  # continuity correction
    return _norm_sf(z)


def binomial_two_sided_p(k: int, n: int, p0: float) -> float:
    """Two-sided binomial test p-value (symmetric)."""
    if n <= 0:
        return 1.0
    p_upper = binomial_one_sided_p(k, n, p0)
    # P(K <= k) = 1 - P(K >= k+1)
    p_lower = 1.0 - binomial_one_sided_p(k + 1, n, p0) if k < n else 1.0
    return min(1.0, 2.0 * min(p_upper, p_lower))


def _exact_binom_tail(k: int, n: int, p: float) -> float:
    from math import comb
    total = 0.0
    for i in range(k, n + 1):
        total += comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
    return total


def _norm_sf(z: float) -> float:
    """1 - Phi(z)."""
    return 0.5 * math.erfc(z / math.sqrt(2))


# ──────────────────────────────────────────────────────
# Multiple testing corrections
# ──────────────────────────────────────────────────────
def bonferroni_threshold(alpha0: float, n_tests: int) -> float:
    return alpha0 / max(1, n_tests)


def benjamini_hochberg(
    p_values: list[float],
    q: float = 0.10,
) -> list[bool]:
    """Benjamini-Hochberg FDR: returns mask of significant tests at FDR <= q."""
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    # BH: reject if p_(i) <= (i/n) * q for largest such i
    threshold_i = -1
    for rank, (idx, p) in enumerate(indexed, start=1):
        if p <= (rank / n) * q:
            threshold_i = rank
    mask = [False] * n
    if threshold_i < 0:
        return mask
    # reject all with rank <= threshold_i
    for rank, (idx, p) in enumerate(indexed, start=1):
        if rank <= threshold_i:
            mask[idx] = True
    return mask


# ──────────────────────────────────────────────────────
# Cell (pocket) データクラス
# ──────────────────────────────────────────────────────
@dataclass
class PocketStats:
    """1 cell の統計パッケージ.

    Regime conditioning (conditional-edge-estimand-2026-04-17.md):
    - regime_breakdown: regime → {n, avg, std} — 条件付き期待値
    - theta_reweighted: Σ_r π_long_run(r) * Ê[pnl | s, r]  — 真の推定量
    - se_reweighted: stratified 標準誤差
    - regime_support: FULL/PARTIAL/INSUFFICIENT
    これらは analyzer が regime 列を持つ場合のみ populate される.
    """
    key: tuple                   # (dim_name, dim_value, ...) など
    n: int
    wins: int
    wr: float
    avg_pips: float
    total_pips: float
    pf: float
    std_pips: float
    breakeven_wr: float          # コスト込み損益分岐WR
    p_value: float               # binomial test vs breakeven
    bonf_significant: bool = False
    fdr_significant: bool = False
    wf_stable: Optional[bool] = None   # None = 未計測
    recommendation: str = "WEAK"  # STRONG / MODERATE / WEAK
    # Regime conditioning fields (optional; populated if regime data available)
    regime_breakdown: dict = None          # regime → {"n": int, "avg": float, "std": float}
    theta_reweighted: Optional[float] = None
    se_reweighted: Optional[float] = None
    regime_support: Optional[str] = None   # "FULL" / "PARTIAL" / "INSUFFICIENT"

    def __post_init__(self):
        if self.regime_breakdown is None:
            self.regime_breakdown = {}

    def __str__(self) -> str:
        wf = "Y" if self.wf_stable else ("N" if self.wf_stable is False else "-")
        b = "*" if self.bonf_significant else (" " if not self.fdr_significant else "+")
        base = (
            f"{b} {self.recommendation:8s} [{self.key}] "
            f"N={self.n:3d} WR={self.wr:.0%} (BE={self.breakeven_wr:.0%}) "
            f"Avg={self.avg_pips:+6.2f}p Tot={self.total_pips:+7.1f}p "
            f"PF={self.pf:.2f} p={self.p_value:.4f} WF={wf}"
        )
        if self.theta_reweighted is not None:
            rs = (self.regime_support or "?")[:4]
            se_str = (f"±{self.se_reweighted:.2f}"
                      if self.se_reweighted is not None else "")
            base += f" θ*={self.theta_reweighted:+.2f}p{se_str} RS={rs}"
        return base


def build_pocket(key: tuple, pnl_series, breakeven_wr: float = 0.50) -> PocketStats:
    """pnl_pips Series から PocketStats を構築."""
    import pandas as pd
    import numpy as np
    s = pd.Series(pnl_series).dropna()
    n = len(s)
    wins = int((s > 0).sum())
    wr = wins / n if n > 0 else 0.0
    avg = float(s.mean()) if n > 0 else 0.0
    total = float(s.sum())
    std = float(s.std(ddof=1)) if n > 1 else 0.0
    gw = float(s[s > 0].sum())
    gl = -float(s[s < 0].sum())
    pf = gw / gl if gl > 0 else float("inf") if gw > 0 else 0.0
    # Two-sided binomial test: WR != breakeven? (positive/negative 両セル検出)
    p_val = binomial_two_sided_p(wins, n, breakeven_wr)
    return PocketStats(
        key=key, n=n, wins=wins, wr=wr, avg_pips=avg, total_pips=total,
        pf=pf, std_pips=std, breakeven_wr=breakeven_wr, p_value=p_val,
    )


def apply_corrections(
    pockets: list[PocketStats],
    alpha: float = 0.05,
    fdr_q: float = 0.10,
) -> list[PocketStats]:
    """Bonferroni & BH FDR を適用 (in-place に significant フラグ設定)."""
    n_tests = len(pockets)
    if n_tests == 0:
        return pockets
    bonf_thr = bonferroni_threshold(alpha, n_tests)
    p_vals = [p.p_value for p in pockets]
    fdr_mask = benjamini_hochberg(p_vals, q=fdr_q)
    for p, fdr_flag in zip(pockets, fdr_mask):
        p.bonf_significant = p.p_value < bonf_thr
        p.fdr_significant = bool(fdr_flag)
    return pockets


def assign_recommendation(
    pockets: list[PocketStats],
    min_n_strong: int = 30,
) -> list[PocketStats]:
    """bt_scanner 流儀で推奨ラベルを付ける.

    STRONG:   Bonf有意 + EV>0 + WF stable + N>=min_n_strong
    MODERATE: FDR有意 + EV>0 + N>=min_n_strong
    WEAK:     それ以外
    """
    for p in pockets:
        if (p.bonf_significant
            and p.avg_pips > 0
            and p.wf_stable is True
            and p.n >= min_n_strong):
            p.recommendation = "STRONG"
        elif (p.fdr_significant
              and p.avg_pips > 0
              and p.n >= min_n_strong):
            p.recommendation = "MODERATE"
        else:
            p.recommendation = "WEAK"
    return pockets


# ──────────────────────────────────────────────────────
# Walk-forward stability for trade cells
# ──────────────────────────────────────────────────────
def wf_stable_for_cell(
    pnl_series_with_time,
    n_folds: int = 3,
    min_n_per_fold: int = 10,
    require_last_fold_positive: bool = True,
) -> Optional[bool]:
    """時系列順に n_folds 等分し、各 fold で avg_pnl > 0 か確認.

    Input: iterable of (entry_time, pnl_pips) tuples (chronological).
    Returns:
        True  if stable (>=ceil(2/3) folds have avg>0 AND
              require_last_fold_positive ? last fold positive : 常に)
        False otherwise
        None  if insufficient data (per-fold N が min_n_per_fold 未満)

    require_last_fold_positive=True (デフォルト) は重要:
    これがないと +/-/+ パターンの "劣化中" 戦略を STRONG と誤判定する.
    live promote 判断には recency 重みが必須.
    """
    items = list(pnl_series_with_time)
    if not items:
        return None
    items.sort(key=lambda x: x[0])
    n = len(items)
    fold_size = n // n_folds
    if fold_size < min_n_per_fold:
        return None  # データ不足で判定不能
    positive_folds = 0
    valid_folds = 0
    last_fold_avg: Optional[float] = None
    for i in range(n_folds):
        start = i * fold_size
        end = (i + 1) * fold_size if i < n_folds - 1 else n
        fold = items[start:end]
        if len(fold) < min_n_per_fold:
            continue
        valid_folds += 1
        avg = sum(p for _, p in fold) / len(fold)
        if avg > 0:
            positive_folds += 1
        if i == n_folds - 1:
            last_fold_avg = avg
    if valid_folds < 2:
        return None
    threshold = max(2, math.ceil(valid_folds * 2 / 3))
    count_ok = positive_folds >= threshold
    # recency 制約: 最終 fold が negative なら stable とみなさない
    # (劣化中の戦略を誤って STRONG 判定するのを防ぐ)
    if require_last_fold_positive and last_fold_avg is not None and last_fold_avg <= 0:
        return False
    return count_ok
