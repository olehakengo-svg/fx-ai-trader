"""Strategy Category Registry

目的:
  戦略ごとに Trend-Following (TF) / Mean-Reversion (MR) / Breakout (BR) などの
  カテゴリを明示し、MassiveSignalEnhancer 等の conf_adj 計算で
  **カテゴリ別に加減点を分岐**できるようにする。

背景 (2026-04-23):
  VWAP 逆校正 (commit b37ee8b) で判明したとおり、現行の signal enhancer は
  TF 前提の加点を全戦略に一律適用していた。shadow 実測で:
    - TF Delta WR -9.0pp
    - MR Delta WR -2.8pp
  TF のほうが重症だが、いずれにせよカテゴリを区別せずに加点するのが誤り。

  さらに TF 内 root-cause 分析 (/tmp/tf_inverse_rootcause.py) で:
    - 「方向一致」フラグ has: Delta -16.2pp
    - 「機関フロー」フラグ has: Delta -10.4pp
    - 「HVN」フラグ has: Delta -6.3pp
  他の signal enhancer 部分 (institutional flow, HVN, MTF alignment gate) も
  同様の TF-biased 設計の疑いが濃厚。

Phase 2 活用計画:
  1. このレジストリを `_vwap_zone_analysis`, `_institutional_flow_analysis`,
     `_volume_profile_analysis` 等に注入し、カテゴリ別 conf_adj に再構成
  2. 各 enhancer は `apply_adj(strategy_cat, raw_adj)` 経由で加点
     - TF: raw_adj をそのまま (今の TF 前提の semantics で動く)
     - MR: 符号反転 or 中立化
     - BR: 未定 (データ蓄積後)

注意:
  - カテゴリの揺れは実測で判断する。このレジストリは **仮説初期値**。
  - 実装前に N>=50/category の Live/Shadow 実測で monotonicity 確認。
  - 未分類戦略は "OTHER" として中立扱い。
"""
from __future__ import annotations

from typing import Dict, Iterable, Literal

Category = Literal["TF", "MR", "BR", "OTHER"]

# Trend-Following: 順張り・ブレイク継続を期待する戦略
TF_STRATEGIES: frozenset[str] = frozenset({
    "ema_pullback",
    "ema_pullback_v2",
    "ema200_trend_reversal",
    "trend_rebound",
    "ema_trend_scalp",
    "trend_break",
    "london_breakout",
    "adx_trend_continuation",
    "gold_trend_momentum",
    "jpy_basket_trend",
})

# Mean-Reversion: レンジ回帰・反発を期待する戦略
MR_STRATEGIES: frozenset[str] = frozenset({
    "bb_rsi_reversion",
    "bb_rsi_mr",
    "dt_bb_rsi_mr",
    "sr_channel_reversal",
    "sr_touch",
    "engulfing_bb",
    "engulfing_bb_lvn_london_ny",
    "fib_reversal",
    "dt_fib_reversal",
    "stoch_trend_pullback",
    "sr_fib_confluence",
    "sr_fib_confluence_tight_sl",
    "london_fix_reversal",
    "london_close_reversal",
    "london_close_reversal_v2",
    "eurgbp_daily_mr",
    "gbp_deep_pullback",
})

# Breakout: レンジ脱出・レベル突破エントリ
BR_STRATEGIES: frozenset[str] = frozenset({
    "london_session_breakout",
    "orb_trap",
    "htf_false_breakout",
    "alpha_atr_regime_break",
    "doji_breakout",
    "liquidity_sweep",
})


def category_of(entry_type: str | None) -> Category:
    """Return strategy category for an entry_type.

    Returns "OTHER" for unknown or None.
    """
    if not entry_type:
        return "OTHER"
    if entry_type in TF_STRATEGIES:
        return "TF"
    if entry_type in MR_STRATEGIES:
        return "MR"
    if entry_type in BR_STRATEGIES:
        return "BR"
    return "OTHER"


# Phase 2 conf_adj policy (initial hypothesis, subject to empirical tuning)
# 実データで monotonicity を確認したら値を調整する
_POLICY: Dict[str, Dict[Category, float]] = {
    # signal enhancer name -> category -> multiplier applied to raw_adj
    "vwap_zone":           {"TF": 1.0, "MR": -1.0, "BR": 0.5, "OTHER": 0.0},
    "vwap_slope":          {"TF": 1.0, "MR": -1.0, "BR": 0.5, "OTHER": 0.0},
    "institutional_flow":  {"TF": 0.0, "MR": 0.0,  "BR": 0.0, "OTHER": 0.0},  # 全中立 (Delta-10.4pp観測)
    "mtf_alignment":       {"TF": 0.0, "MR": 0.0,  "BR": 0.0, "OTHER": 0.0},  # aligned WR 10% 観測で全中立
    "volume_profile_hvn":  {"TF": 0.0, "MR": 0.0,  "BR": 0.0, "OTHER": 0.0},  # Delta-6.3pp 観測
    "volume_profile_lvn":  {"TF": 0.0, "MR": 1.0,  "BR": 0.0, "OTHER": 0.0},  # LVN は MR に薄陽性 (+2.4pp)
}


def apply_policy(enhancer: str, entry_type: str | None, raw_adj: float) -> float:
    """Scale raw conf_adj by category-specific policy.

    現時点では呼び出されていない (VWAP は全中立化中)。Phase 2 で
    `_vwap_zone_analysis` 等が本関数経由で加点する形に段階移行する。
    """
    cat = category_of(entry_type)
    policy = _POLICY.get(enhancer, {})
    scale = policy.get(cat, 0.0)
    return raw_adj * scale


def iter_all_strategies() -> Iterable[tuple[str, Category]]:
    for s in TF_STRATEGIES:
        yield s, "TF"
    for s in MR_STRATEGIES:
        yield s, "MR"
    for s in BR_STRATEGIES:
        yield s, "BR"
