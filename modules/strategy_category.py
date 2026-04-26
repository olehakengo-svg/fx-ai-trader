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


# Conf_adj policy.
#
# 2026-04-26 Edge Reset Phase 1 (Option A: plumbing only):
#   全エントリを 0.0 (中立) に統一。massive_signals.py からの apply_policy()
#   呼び出しを wire up したが、現時点では behavior 変化ゼロ。
#   Phase 1.5 (次セッション) で shadow N>=15/category の monotonicity を
#   実測してから data-driven に値を tuning する。
#
# 過去の仮説初期値 (commit 9787dd8 当時、reference 用):
#   "vwap_zone":          TF:1.0  MR:-1.0  BR:0.5
#   "vwap_slope":         TF:1.0  MR:-1.0  BR:0.5
#   "volume_profile_lvn": MR:1.0
#   他は 0.0
# これらは BT 楽観バイアス + 検証なしで設定されていたため Phase 1 で凍結。
_POLICY: Dict[str, Dict[Category, float]] = {
    # signal enhancer name -> category -> multiplier applied to raw_adj
    "vwap_zone":           {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "vwap_slope":          {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "institutional_flow":  {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "mtf_alignment":       {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "volume_profile_hvn":  {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "volume_profile_lvn":  {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    # Phase 1.5 candidate keys (app.py compute_daytrade_signal 統合用)
    "ema_alignment":       {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "macd_alignment":      {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    "vwap_deviation":      {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
}


def apply_policy(enhancer: str, entry_type: str | None, raw_adj: float) -> float:
    """Scale raw conf_adj by category-specific policy.

    本関数は 2026-04-26 Phase 1 で massive_signals.py から使用される。
    現時点では _POLICY が全 0.0 のため出力は常に 0.0 (中立化を維持)。

    Phase 1.5 で shadow N>=15/category の monotonicity 実測後に
    _POLICY 値を data-driven に tuning する。

    Parameters
    ----------
    enhancer : str
        signal enhancer 名 (vwap_zone / volume_profile_hvn 等)
    entry_type : str | None
        戦略名。None なら OTHER として中立扱い。
    raw_adj : float
        enhancer が計算した raw な conf 加点候補

    Returns
    -------
    float
        category × enhancer policy で scale された conf_adj
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


# ─────────────────────────────────────────────────────────────────────────
# R2-A Suppress (2026-04-26 Wave 1, rule:R2)
#
# Phase 4d-II nature pooling (`phase4d-II-nature-pooling-result-2026-04-26.md`,
# memory obs 81) で Wilson upper < baseline と判定された 4 cells を
# confidence ×0.5 で抑制する。Bonferroni 不要 (Asymmetric Agility R2 教科書
# 用途、loss prevention only)。
#
# 出典:
#   - stoch_trend_pullback × Overlap × q2: WR 7.7% vs baseline 24.4% (Δ=-16.7pp)
#   - sr_channel_reversal × London × q3:   WR 15.0% vs baseline 27.1% (Δ=-12.1pp)
#   - ema_trend_scalp × London × q0:        WR 17.0% vs baseline 21.4% (Δ=-4.4pp)
#   - vol_surge_detector × Tokyo × q3:      WR 30.4%, Phase 4d-II 最大負 edge
#
# Session name は Phase 4d KB canonical bucket (Tokyo / London / Overlap /
# NewYork) を採用。app.py 側の "NY × London" 等は _normalize_session() で
# 変換する。
# ─────────────────────────────────────────────────────────────────────────

_R2A_SUPPRESS: Dict[tuple, float] = {
    ("stoch_trend_pullback", "Overlap", "q2"): 0.5,
    ("sr_channel_reversal",  "London",  "q3"): 0.5,
    ("ema_trend_scalp",      "London",  "q0"): 0.5,
    ("vol_surge_detector",   "Tokyo",   "q3"): 0.5,
}


def _normalize_session(session_name: str | None) -> str:
    """Map app.py session names to Phase 4d KB canonical buckets.

    app.py `get_session_info()` returns names like "NY × London" /
    "東京 × London" / "New York"; Phase 4d KB uses "Overlap" / "Overlap_TK" /
    "NewYork". This normalizer keeps the lookup table readable.
    """
    if not session_name:
        return ""
    if session_name in ("NY × London", "overlap_LN", "overlap_lnny", "Overlap"):
        return "Overlap"
    if session_name in ("東京 × London", "overlap_TK", "Overlap_TK"):
        return "Overlap_TK"
    if session_name in ("New York", "NewYork", "NY"):
        return "NewYork"
    if session_name in ("Tokyo", "東京"):
        return "Tokyo"
    if session_name in ("London", "ロンドン"):
        return "London"
    return session_name


# Pair-specific spread quintile boundaries (pip).
# Cuts split spreads into q0..q4 (q0 = lowest, q4 = highest).
# Approximate calibration from `friction-analysis.md` per-pair distributions.
# More accurate calibration is U13/U14 (Wave 2): XAU 完全除外後の sqlite-fx
# クエリで N>=30/(pair, session) 確認後に再 calibrate。
_SPREAD_QUINTILE_CUTS: Dict[str, list[float]] = {
    "USD_JPY": [0.4, 0.6, 0.8, 1.2],
    "EUR_USD": [0.4, 0.6, 0.8, 1.2],
    "GBP_USD": [0.8, 1.2, 1.6, 2.4],
    "EUR_JPY": [0.6, 0.9, 1.2, 1.6],
}
_SPREAD_QUINTILE_CUTS_DEFAULT: list[float] = [0.5, 1.0, 1.5, 2.0]


def _normalize_pair(pair: str | None) -> str:
    if not pair:
        return ""
    p = pair.replace("/", "_").replace("=X", "").upper()
    # "USDJPY" / "EURUSD" 等の underscore なし 6 文字形式を "USD_JPY" 形式に正規化
    if "_" not in p and len(p) == 6:
        p = p[:3] + "_" + p[3:]
    return p


def compute_spread_quintile(spread_pips: float | None, pair: str | None) -> str:
    """Return spread quintile label "q0".."q4" for given pair.

    Pair-specific cuts are derived from friction-analysis.md medians; q0 is the
    tightest (lowest spread) bucket, q4 the widest. None / non-finite spreads
    fall back to "q2" (the median bucket) so downstream lookups still work
    rather than raising.
    """
    if spread_pips is None:
        return "q2"
    try:
        sp = float(spread_pips)
    except (TypeError, ValueError):
        return "q2"
    if not (sp == sp) or sp < 0:  # NaN guard via self-equality
        return "q2"

    cuts = _SPREAD_QUINTILE_CUTS.get(_normalize_pair(pair), _SPREAD_QUINTILE_CUTS_DEFAULT)
    for i, c in enumerate(cuts):
        if sp <= c:
            return f"q{i}"
    return "q4"


def apply_r2a_suppress_gate(
    entry_type: str | None,
    session_name: str | None,
    spread_quintile: str | None,
    conf: int | float,
) -> int:
    """R2-A: confidence ×0.5 for Wilson-upper-below-baseline cells.

    Gate is applied AFTER existing confidence calculation. Reversible by
    removing entries from `_R2A_SUPPRESS`. No effect on non-listed cells.

    Parameters
    ----------
    entry_type : str | None
        Strategy name (e.g. "stoch_trend_pullback"). None / unknown → no-op.
    session_name : str | None
        Session name from `get_session_info()["name"]` (app.py L593-619) or a
        Phase 4d KB canonical name. Internally normalized.
    spread_quintile : str | None
        "q0".."q4" — output of `compute_spread_quintile()`.
    conf : int | float
        Pre-suppression confidence (0..95).

    Returns
    -------
    int
        Suppressed confidence. Identical to input when cell not listed.
    """
    if not entry_type:
        return int(conf)
    sess = _normalize_session(session_name)
    key = (entry_type, sess, spread_quintile or "")
    mult = _R2A_SUPPRESS.get(key, 1.0)
    return int(round(float(conf) * mult))
