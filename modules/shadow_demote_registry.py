"""Per-cell Shadow demotion registry for R2 critical cells."""
from __future__ import annotations


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
    return (str(strategy or ""), str(instrument or "").upper()) in SHADOW_DEMOTED_CELLS
