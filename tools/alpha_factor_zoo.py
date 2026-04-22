#!/usr/bin/env python3
"""Alpha Factor Zoo — qlib Alpha158 サブセット FX 適用 (read-only scanner)

目的:
  qlib の kbar + rolling window feature を FX OHLC に適用し、
  Information Coefficient (IC = Spearman corr(factor_t, return_{t+h})) を
  Bonferroni 補正 + bootstrap p 値で評価する。

非侵襲:
  - live path / BT logic には一切触れない
  - BTDataCache から OHLC を読むだけ
  - 結果は raw/bt-results/alpha-factor-zoo-{date}.md に書き出し

Usage:
    python3 tools/alpha_factor_zoo.py [--pairs USD_JPY,EUR_USD] [--tf 15m] [--days 365]

判断プロトコル (CLAUDE.md):
  - 1 日 BT で判断停止
  - 有意 factor 発見 → 365d × walk-forward で再検証 (別セッション)
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.bt_data_cache import BTDataCache

DEFAULT_PAIRS = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]
DEFAULT_TF = "15m"
DEFAULT_DAYS = 365
DEFAULT_HORIZONS = [1, 5, 10, 16]  # bars ahead (16 = 4h @ 15m = 主要エッジの hold)
ROLLING_WINDOWS = [5, 10, 20, 30, 60]
BOOTSTRAP_N = 100
SEED = 42


def compute_kbar_features(df: pd.DataFrame) -> pd.DataFrame:
    """qlib kbar 9 features (open/close/high/low 正規化)."""
    o, c, h, l = df["Open"], df["Close"], df["High"], df["Low"]
    eps = 1e-12
    feats = pd.DataFrame(index=df.index)
    feats["KMID"] = (c - o) / (o + eps)
    feats["KLEN"] = (h - l) / (o + eps)
    feats["KMID2"] = (c - o) / (h - l + eps)
    feats["KUP"] = (h - np.maximum(o, c)) / (o + eps)
    feats["KUP2"] = (h - np.maximum(o, c)) / (h - l + eps)
    feats["KLOW"] = (np.minimum(o, c) - l) / (o + eps)
    feats["KLOW2"] = (np.minimum(o, c) - l) / (h - l + eps)
    feats["KSFT"] = (2 * c - h - l) / (o + eps)
    feats["KSFT2"] = (2 * c - h - l) / (h - l + eps)
    return feats


def compute_rolling_features(df: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    """qlib rolling features (MA, STD, ROC, QTLU, QTLD, RSV)."""
    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    eps = 1e-12
    feats = pd.DataFrame(index=df.index)
    for w in windows:
        # Momentum & trend
        feats[f"MA{w}"] = c.rolling(w).mean() / (c + eps) - 1
        feats[f"STD{w}"] = c.rolling(w).std() / (c + eps)
        feats[f"ROC{w}"] = c.pct_change(w)
        # Quantile features
        feats[f"QTLU{w}"] = c.rolling(w).quantile(0.8) / (c + eps) - 1
        feats[f"QTLD{w}"] = c.rolling(w).quantile(0.2) / (c + eps) - 1
        # Raw Stochastic Value: (C - min(L, w)) / (max(H, w) - min(L, w))
        rolling_max_h = h.rolling(w).max()
        rolling_min_l = l.rolling(w).min()
        feats[f"RSV{w}"] = (c - rolling_min_l) / (rolling_max_h - rolling_min_l + eps)
    return feats


def compute_ic(factor: pd.Series, returns: pd.Series, horizon: int) -> float:
    """Spearman rank correlation between factor_t and return_{t+h}."""
    fwd_ret = returns.shift(-horizon)
    aligned = pd.concat([factor, fwd_ret], axis=1).dropna()
    if len(aligned) < 30:
        return np.nan
    # Spearman rank correlation
    return aligned.iloc[:, 0].corr(aligned.iloc[:, 1], method="spearman")


def bootstrap_pvalue(factor: pd.Series, returns: pd.Series, horizon: int,
                     observed_ic: float, n_boot: int = BOOTSTRAP_N) -> float:
    """Permutation-based p-value for IC (two-sided)."""
    fwd_ret = returns.shift(-horizon)
    aligned = pd.concat([factor, fwd_ret], axis=1).dropna()
    if len(aligned) < 30:
        return np.nan
    rng = np.random.default_rng(SEED)
    f_vals = aligned.iloc[:, 0].values
    r_vals = aligned.iloc[:, 1].values
    null_ics = np.empty(n_boot)
    for i in range(n_boot):
        permuted = rng.permutation(r_vals)
        null_ics[i] = pd.Series(f_vals).corr(pd.Series(permuted), method="spearman")
    # two-sided
    return float(np.mean(np.abs(null_ics) >= abs(observed_ic)))


def scan_pair(pair: str, tf: str, days: int, horizons: list[int]) -> list[dict]:
    """Compute all factor × horizon IC for one pair."""
    cache = BTDataCache()
    df = cache.get(pair, tf, days=days)
    if df is None or len(df) < 200:
        print(f"  [skip] {pair}/{tf}: insufficient data")
        return []

    # Column normalization (BTDataCache returns Open/High/Low/Close/Volume)
    if "Close" not in df.columns:
        # Some sources use lowercase
        df = df.rename(columns={c: c.capitalize() for c in df.columns})

    returns = df["Close"].pct_change()

    kbar_feats = compute_kbar_features(df)
    roll_feats = compute_rolling_features(df, ROLLING_WINDOWS)
    all_feats = pd.concat([kbar_feats, roll_feats], axis=1)

    results = []
    for fname in all_feats.columns:
        factor = all_feats[fname]
        for h in horizons:
            ic = compute_ic(factor, returns, h)
            if np.isnan(ic):
                continue
            pval = bootstrap_pvalue(factor, returns, h, ic)
            results.append({
                "pair": pair,
                "tf": tf,
                "factor": fname,
                "horizon": h,
                "n": int(len(factor.dropna())),
                "ic": float(ic),
                "pvalue": float(pval) if not np.isnan(pval) else None,
            })
    print(f"  [done] {pair}/{tf}: {len(results)} (factor × horizon) cells")
    return results


def by_fdr_threshold(pvalues: list[float], alpha: float = 0.01) -> tuple[float, np.ndarray]:
    """Benjamini-Yekutieli FDR: returns (threshold, reject_mask).

    BY is conservative variant of BH that holds under arbitrary dependence.
    p_(i) <= (i / (m * c(m))) * alpha, where c(m) = sum(1/k for k in 1..m).
    """
    p_arr = np.asarray([p if p is not None else 1.0 for p in pvalues], dtype=float)
    m = len(p_arr)
    if m == 0:
        return np.nan, np.zeros(0, dtype=bool)
    c_m = np.sum(1.0 / np.arange(1, m + 1))
    order = np.argsort(p_arr)
    sorted_p = p_arr[order]
    ranks = np.arange(1, m + 1)
    thresholds = (ranks / (m * c_m)) * alpha
    reject_sorted = sorted_p <= thresholds
    # BH/BY: find the largest k such that p_(k) <= threshold_k; reject all <= k
    if not reject_sorted.any():
        reject_mask_sorted = np.zeros(m, dtype=bool)
        cut_threshold = 0.0
    else:
        k_max = np.max(np.where(reject_sorted)[0])
        reject_mask_sorted = np.zeros(m, dtype=bool)
        reject_mask_sorted[: k_max + 1] = True
        cut_threshold = float(sorted_p[k_max])
    # unsort back to original order
    reject_mask = np.zeros(m, dtype=bool)
    reject_mask[order] = reject_mask_sorted
    return cut_threshold, reject_mask


def render_markdown(results: list[dict], pairs: list[str], tf: str, days: int,
                    horizons: list[int]) -> str:
    """Write results to markdown report."""
    df = pd.DataFrame(results)
    if len(df) == 0:
        return "# Alpha Factor Zoo — 結果なし\n"

    # Bonferroni correction: alpha / (N_factors × N_pairs × N_horizons)
    n_tests = len(df)
    bonferroni_alpha = 0.01 / n_tests
    df["sig_bonf"] = df["pvalue"].apply(
        lambda p: (p is not None) and (p < bonferroni_alpha))
    # Benjamini-Yekutieli FDR (holds under arbitrary dependence)
    by_threshold, by_mask = by_fdr_threshold(list(df["pvalue"]), alpha=0.01)
    df["sig_by_fdr"] = by_mask
    df["abs_ic"] = df["ic"].abs()
    df_sorted = df.sort_values("abs_ic", ascending=False)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_bonf_sig = int(df["sig_bonf"].sum())
    n_by_sig = int(df["sig_by_fdr"].sum())
    lines = [
        f"# Alpha Factor Zoo — IC Scan",
        f"",
        f"- **Generated**: {now}",
        f"- **Pairs**: {', '.join(pairs)}",
        f"- **TF**: {tf}",
        f"- **Lookback**: {days} days",
        f"- **Horizons (bars)**: {horizons}",
        f"- **Bootstrap**: {BOOTSTRAP_N} permutations",
        f"- **Total tests**: {n_tests}",
        f"- **Bonferroni α**: {bonferroni_alpha:.2e} → {n_bonf_sig} cells sig",
        f"- **BY-FDR α=0.01 cutoff p**: {by_threshold:.3e} → {n_by_sig} cells sig",
        f"",
        f"## Source",
        f"qlib Alpha158 サブセット (kbar 9 + rolling [5,10,20,30,60] × [MA, STD, ROC, QTLU, QTLD, RSV])",
        f"",
        f"## Top 20 |IC| (全 pair × horizon)",
        f"| Rank | Pair | TF | Factor | Horizon | N | IC | p-value | Bonf.sig |",
        f"|-----:|------|----|--------|--------:|--:|---:|--------:|:-:|",
    ]
    # add BY-FDR column to top 20 table
    lines[-2] = "| Rank | Pair | TF | Factor | Horizon | N | IC | p-value | Bonf | BY-FDR |"
    lines[-1] = "|-----:|------|----|--------|--------:|--:|---:|--------:|:-:|:-:|"
    for i, row in enumerate(df_sorted.head(20).itertuples(), 1):
        pval_str = f"{row.pvalue:.3g}" if row.pvalue is not None else "—"
        bonf_mark = "✅" if row.sig_bonf else ""
        by_mark = "✅" if row.sig_by_fdr else ""
        lines.append(
            f"| {i} | {row.pair} | {row.tf} | {row.factor} | {row.horizon} | "
            f"{row.n} | {row.ic:+.4f} | {pval_str} | {bonf_mark} | {by_mark} |"
        )

    # Bonferroni-significant subset
    sig_df = df_sorted[df_sorted["sig_bonf"]]
    lines.append("")
    lines.append(f"## Bonferroni-Significant Factors (p < {bonferroni_alpha:.2e})")
    if len(sig_df) == 0:
        lines.append("- **該当なし** (null 仮説を棄却できる factor なし)")
    else:
        lines.append(f"- **{len(sig_df)} cells** が Bonferroni 補正後有意")
        lines.append("")
        lines.append("| Pair | TF | Factor | Horizon | IC | p-value |")
        lines.append("|------|----|--------|--------:|---:|--------:|")
        for row in sig_df.head(30).itertuples():
            lines.append(
                f"| {row.pair} | {row.tf} | {row.factor} | {row.horizon} | "
                f"{row.ic:+.4f} | {row.pvalue:.3g} |"
            )

    # BY-FDR-significant subset (less conservative than Bonferroni, allows correlated tests)
    by_sig_df = df_sorted[df_sorted["sig_by_fdr"] & ~df_sorted["sig_bonf"]]
    lines.append("")
    lines.append(f"## BY-FDR-Significant Factors (not caught by Bonferroni)")
    lines.append(f"- BY-FDR は Bonferroni より gentle。本スキャン {n_tests} cells の一般相関構造で有効。")
    lines.append(f"- BY-FDR p_cutoff = {by_threshold:.3e}")
    if len(by_sig_df) == 0:
        lines.append("- **該当なし** (Bonferroni でカバー済み or signal なし)")
    else:
        lines.append(f"- **{len(by_sig_df)} cells** が BY-FDR のみで有意 (Bonferroni では漏れた)")
        lines.append("")
        lines.append("| Pair | TF | Factor | Horizon | IC | p-value |")
        lines.append("|------|----|--------|--------:|---:|--------:|")
        for row in by_sig_df.head(30).itertuples():
            lines.append(
                f"| {row.pair} | {row.tf} | {row.factor} | {row.horizon} | "
                f"{row.ic:+.4f} | {row.pvalue:.3g} |"
            )

    lines += [
        "",
        "## 判断プロトコル遵守 (CLAUDE.md)",
        "- **本スキャンは 1 回 BT** → 実装判断は **保留** (lesson-reactive-changes)",
        "- Bonferroni 有意 factor は 365d walk-forward で再検証する",
        "- 既存戦略の entry_filter と合成する場合、Live N≥30 まで Shadow のみ",
        "",
        "## Source",
        "- qlib Alpha158: https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py",
        "- Generated by: `tools/alpha_factor_zoo.py`",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Alpha Factor Zoo — qlib subset IC scanner")
    parser.add_argument("--pairs", default=",".join(DEFAULT_PAIRS),
                        help="Comma-separated pairs (e.g., USD_JPY,EUR_USD)")
    parser.add_argument("--tf", default=DEFAULT_TF, help="Timeframe")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="Lookback days")
    parser.add_argument("--horizons", default=",".join(map(str, DEFAULT_HORIZONS)),
                        help="Forward return horizons in bars")
    parser.add_argument("--output", default=None,
                        help="Output markdown path (default: auto)")
    args = parser.parse_args()

    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]
    horizons = [int(x) for x in args.horizons.split(",") if x.strip()]

    print(f"{'='*60}")
    print(f"  Alpha Factor Zoo — qlib subset")
    print(f"  Pairs: {pairs}")
    print(f"  TF={args.tf}, days={args.days}, horizons={horizons}")
    print(f"{'='*60}")

    all_results = []
    for pair in pairs:
        print(f"\n[scan] {pair}/{args.tf}...")
        try:
            results = scan_pair(pair, args.tf, args.days, horizons)
            all_results.extend(results)
        except Exception as e:
            print(f"  ❌ {pair}: {e}")

    md = render_markdown(all_results, pairs, args.tf, args.days, horizons)
    if args.output is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = _PROJECT_ROOT / "knowledge-base" / "raw" / "bt-results" / f"alpha-factor-zoo-{date_str}.md"
    else:
        out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"\n✅ Report written: {out_path}")
    print(f"   ({len(all_results)} cells scanned)")


if __name__ == "__main__":
    main()
