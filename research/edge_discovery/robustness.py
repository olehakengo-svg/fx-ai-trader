"""
Robustness checking utilities.

発見した pocket が偶然でないことを検証する:
- split_half_robustness: データを半分に分割し、両方で同じ pocket が出るか
- walk_forward_validate: IS → OOS の walk-forward 検証
- purged_kfold:           purge + embargo 付き K-fold CV (Lopez de Prado)

"Triple-barrier pocket, single-barrier bullshit" — de Prado の言葉通り、
in-sample でのみ光る pocket は research で切り捨てる。
"""
from __future__ import annotations
from typing import Callable
import math


def split_half_robustness(
    bars,
    analyzer_factory: Callable,
    min_n: int = 30,
    min_abs_sharpe: float = 0.3,
) -> dict:
    """データを前半後半に分割し、両方で有意な pocket を返す.

    analyzer_factory(bars_subset) → ConditionalReturnAnalyzer
    を受け取り、前半後半それぞれで pocket を探す。
    両方で出た key (condition_name, condition_value, horizon_bars) を "robust" と判定。
    """
    n = len(bars)
    half = n // 2
    bars_a = bars.iloc[:half] if hasattr(bars, "iloc") else bars[:half]
    bars_b = bars.iloc[half:] if hasattr(bars, "iloc") else bars[half:]

    an_a = analyzer_factory(bars_a)
    an_b = analyzer_factory(bars_b)
    p_a = an_a.find_pockets(min_n=min_n, min_abs_sharpe=min_abs_sharpe)
    p_b = an_b.find_pockets(min_n=min_n, min_abs_sharpe=min_abs_sharpe)

    def key(p):
        return (p.condition_name, p.condition_value, p.horizon_bars)

    keys_a = {key(p) for p in p_a}
    keys_b = {key(p) for p in p_b}
    common = keys_a & keys_b

    # 両方で同じ方向（Sharpe 符号一致）のみが真の robust
    map_a = {key(p): p for p in p_a}
    map_b = {key(p): p for p in p_b}
    robust = []
    for k in common:
        pa, pb = map_a[k], map_b[k]
        if math.copysign(1, pa.sharpe) == math.copysign(1, pb.sharpe):
            robust.append((pa, pb))

    return {
        "n_total_a": len(p_a),
        "n_total_b": len(p_b),
        "n_common": len(common),
        "n_sign_consistent": len(robust),
        "consistency_rate": (
            len(robust) / max(1, min(len(p_a), len(p_b)))
        ),
        "robust_pairs": robust,
    }


def walk_forward_validate(
    bars,
    analyzer_factory: Callable,
    n_folds: int = 4,
    min_n: int = 20,
    min_abs_sharpe: float = 0.3,
) -> dict:
    """Walk-forward validation.

    データを n_folds 等分し、各 fold i: (fold 0..i-1) IS → fold i OOS。
    IS で発見した pocket が OOS で同方向 Sharpe を示すかを検証。
    """
    n = len(bars)
    fold_size = n // n_folds
    results = []
    for i in range(1, n_folds):
        is_end = fold_size * i
        oos_end = min(fold_size * (i + 1), n)
        is_bars = bars.iloc[:is_end] if hasattr(bars, "iloc") else bars[:is_end]
        oos_bars = bars.iloc[is_end:oos_end] if hasattr(bars, "iloc") else bars[is_end:oos_end]
        if len(oos_bars) < min_n:
            continue

        an_is = analyzer_factory(is_bars)
        pockets_is = an_is.find_pockets(min_n=min_n, min_abs_sharpe=min_abs_sharpe)
        if not pockets_is:
            results.append({"fold": i, "is_pockets": 0, "oos_hit_rate": None})
            continue

        # IS で発見した pocket を OOS で再評価
        an_oos = analyzer_factory(oos_bars)
        oos_all = an_oos.compute()

        def key(p):
            return (p.condition_name, p.condition_value, p.horizon_bars)
        oos_map = {key(p): p for p in oos_all}

        hits = 0
        for p_is in pockets_is:
            p_oos = oos_map.get(key(p_is))
            if p_oos is None:
                continue
            if math.copysign(1, p_is.sharpe) == math.copysign(1, p_oos.sharpe):
                hits += 1
        hit_rate = hits / len(pockets_is) if pockets_is else 0.0
        results.append({
            "fold": i,
            "is_pockets": len(pockets_is),
            "oos_hit_rate": hit_rate,
            "expected_chance": 0.5,  # 方向一致の帰無仮説
        })
    return {
        "folds": results,
        "mean_hit_rate": (
            sum(r["oos_hit_rate"] or 0 for r in results) / max(1, len(results))
        ),
    }
