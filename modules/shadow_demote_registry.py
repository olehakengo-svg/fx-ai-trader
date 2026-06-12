"""Per-cell Shadow demotion registry for R2 critical cells."""
from __future__ import annotations


# Strategy-level permanent retirement: blocks Shadow emission on ALL
# instruments, including pairs added by future modes (the per-cell entries
# below stopped EUR/GBP/JPY on 2026-05-08, but the daytrade_1h_usdchf
# Phase B-1 slot kept leaking ema_trend_scalp x USD_CHF afterwards).
SHADOW_RETIRED_STRATEGIES = frozenset({
    # 2026-06-12 (rule:R2): edge-factor audit clean N=1,117 — all 8
    # pair x dir cells PF 0.03-0.77, loser MAFE favorable median 0.5p
    # (entry has no predictive power; inverse also fails: gross EV ~ 0),
    # monthly WR 20.8% -> 16.1% -> 6.5%. No salvageable cell, no SIZE
    # lever target. Ref: wiki/learning/edge-factor-audit-2026-06-12-ema-trend-scalp.md
    "ema_trend_scalp",
})


SHADOW_DEMOTED_CELLS = frozenset({
    ("bb_rsi_reversion", "EUR_USD"),
    ("bb_rsi_reversion", "GBP_USD"),
    ("bb_rsi_reversion", "USD_JPY"),
    ("ema_trend_scalp", "EUR_USD"),
    ("ema_trend_scalp", "GBP_USD"),
    ("ema_trend_scalp", "USD_JPY"),
    ("engulfing_bb", "USD_JPY"),
    ("sr_channel_reversal", "EUR_USD"),
    ("sr_channel_reversal", "USD_JPY"),
    ("sr_fib_confluence", "EUR_JPY"),
    ("sr_fib_confluence", "GBP_JPY"),
    ("sr_fib_confluence", "USD_JPY"),
})


def is_shadow_demoted(strategy: str, instrument: str) -> bool:
    """Return True when a strategy x instrument cell must not emit Shadow rows."""
    strategy_key = str(strategy or "")
    if strategy_key in SHADOW_RETIRED_STRATEGIES:
        return True
    return (strategy_key, str(instrument or "").upper()) in SHADOW_DEMOTED_CELLS
