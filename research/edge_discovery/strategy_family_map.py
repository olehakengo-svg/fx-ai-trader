"""v9.3: Strategy Family Map + MTF Alignment.

各 entry_type を 4 family に分類し, MTF regime + direction + instrument から
"aligned" / "conflict" / "neutral" を判定する.

Family 定義:
  TF (Trend-Follow):   regime 方向と同 direction が aligned
  MR (Mean-Reversion): regime 方向と逆 direction が aligned (fade)
  BO (Breakout):       range_wide 後のブレイク方向 または trend 継続 direction
  SE (Session):        neutral (regime 非依存)

2026-04-17 P0 forensics (本番 N=1511) で 3 戦略の mislabeling 確定 →
  macdh_reversal: MR → TF (trend_up × BUY WR 36% > SELL 27%)
  engulfing_bb:   MR → TF (trend_up × BUY WR 43% > SELL 0%)
  ema_cross:      TF → MR (trend_up × BUY WR 17% < SELL 46%)

2026-04-17 P2: regime-adaptive 分類追加 — 2 戦略で uptrend/downtrend で
behavior が分岐:
  bb_rsi_reversion: uptrend TF-like, downtrend MR-like
  fib_reversal:     uptrend MR-like, downtrend TF-like

詳細: knowledge-base/wiki/analyses/mtf-regime-validation-2026-04-17.md §C
"""
from __future__ import annotations

# Per-strategy family classification.
# Source of truth for v9.3 MTF alignment.
STRATEGY_FAMILY: dict[str, str] = {
    # ── TF (Trend-Follow) ──
    "ema_trend_scalp": "TF",
    "xs_momentum": "TF",
    "vol_momentum_scalp": "TF",
    "stoch_trend_pullback": "TF",
    "donchian_momentum_breakout": "TF",
    "sr_break_retest": "TF",
    "macdh_reversal": "TF",   # P0 re-classified 2026-04-17 (was MR)
    "engulfing_bb": "TF",     # P0 re-classified 2026-04-17 (was MR)

    # ── MR (Mean-Reversion) ──
    "bb_rsi_reversion": "MR",
    "fib_reversal": "MR",
    "h1_fib_reversal": "MR",
    "dt_bb_rsi_mr": "MR",
    "dt_fib_reversal": "MR",
    "dt_sr_channel_reversal": "MR",
    "sr_channel_reversal": "MR",
    "dual_sr_bounce": "MR",
    "streak_reversal": "MR",
    "turtle_soup": "MR",
    "mtf_reversal_confluence": "MR",
    "sr_fib_confluence": "MR",
    "trend_rebound": "MR",
    "orb_trap": "MR",
    "ema_cross": "MR",        # P0 re-classified 2026-04-17 (was TF)

    # ── BO (Breakout) ──
    "bb_squeeze_breakout": "BO",
    "vol_surge_detector": "BO",

    # ── SE (Session) ──
    "session_time_bias": "SE",
}


# P2: regime-adaptive family overrides.
# When a strategy's behavior splits by regime, declare per-regime family here.
# Values override STRATEGY_FAMILY for the given (strategy, regime) pair.
# Evidence source: P0 forensics (/tmp/p0_mr_forensics_report.csv), 2026-04-17.
REGIME_ADAPTIVE_FAMILY: dict[str, dict[str, str]] = {
    "bb_rsi_reversion": {
        # tu_BUY 55% (N=74) > tu_SELL 50% (N=64)  → TF in uptrend
        "trend_up_weak": "TF",
        "trend_up_strong": "TF",
        # td_BUY 44% (N=16) > td_SELL 23% (N=22)  → MR in downtrend (fade)
        "trend_down_weak": "MR",
        "trend_down_strong": "MR",
        # range は default の MR に委ねる
    },
    "fib_reversal": {
        # tu_SELL 48% (N=31) > tu_BUY 25% (N=24)  → MR in uptrend (fade)
        "trend_up_weak": "MR",
        "trend_up_strong": "MR",
        # td_SELL 45% (N=22) > td_BUY 33% (N=33)  → TF in downtrend
        "trend_down_weak": "TF",
        "trend_down_strong": "TF",
    },
}


def effective_family(entry_type: str, mtf_regime: str) -> str:
    """Return the effective family, applying REGIME_ADAPTIVE overrides."""
    if entry_type in REGIME_ADAPTIVE_FAMILY:
        adaptive = REGIME_ADAPTIVE_FAMILY[entry_type]
        if mtf_regime in adaptive:
            return adaptive[mtf_regime]
    return STRATEGY_FAMILY.get(entry_type, "UNKNOWN")


def strategy_aware_alignment(
    entry_type: str,
    mtf_regime: str,
    direction: str,
    instrument: str,
) -> str:
    """Return 'aligned' / 'conflict' / 'neutral' / 'unknown'.

    Args:
        entry_type: strategy name (e.g. 'ema_trend_scalp')
        mtf_regime: one of trend_up_weak, trend_up_strong, trend_down_weak,
                    trend_down_strong, range_tight, range_wide, uncertain
        direction: 'BUY' or 'SELL'
        instrument: e.g. 'USD_JPY' (used for JPY-pair exception)
    """
    fam = effective_family(entry_type, mtf_regime)
    d = (direction or "").upper()
    is_jpy = "JPY" in (instrument or "")

    if fam == "UNKNOWN":
        return "unknown"
    if fam == "SE":
        return "neutral"

    if fam == "TF":
        if mtf_regime in ("trend_up_weak", "trend_up_strong"):
            if mtf_regime == "trend_up_strong" and not is_jpy:
                return "conflict"  # non-JPY strong_up exhaustion
            return "aligned" if d == "BUY" else "conflict"
        if mtf_regime in ("trend_down_weak", "trend_down_strong"):
            if mtf_regime == "trend_down_strong":
                return "conflict" if d == "SELL" else "neutral"
            return "aligned" if d == "SELL" else "conflict"
        if mtf_regime in ("range_tight", "range_wide"):
            return "conflict"
        return "neutral"

    if fam == "MR":
        if mtf_regime == "trend_up_strong":
            if is_jpy:
                return "conflict" if d == "SELL" else "neutral"
            return "aligned" if d == "SELL" else "conflict"
        if mtf_regime == "trend_down_strong":
            return "aligned" if d == "BUY" else "conflict"
        if mtf_regime == "trend_up_weak":
            return "aligned" if d == "SELL" else "conflict"
        if mtf_regime == "trend_down_weak":
            return "aligned" if d == "BUY" else "conflict"
        if mtf_regime in ("range_tight", "range_wide"):
            return "aligned"
        return "neutral"

    if fam == "BO":
        if mtf_regime == "range_wide":
            return "aligned"
        if mtf_regime in ("trend_up_weak", "trend_up_strong") and d == "BUY":
            return "aligned"
        if mtf_regime in ("trend_down_weak", "trend_down_strong") and d == "SELL":
            return "aligned"
        return "conflict"

    return "neutral"
