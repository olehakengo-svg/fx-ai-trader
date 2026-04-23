"""
Shadow variant routing — derive filter-specialized entry_type names from runtime conditions.

Phase 1 variants (derived from quant analysis 2026-04-23):
- engulfing_bb_lvn: LVN zone filter (baseline N=158 WR=27.2% EV=-3.43 → N=51 WR=39.2% EV=+0.22, lift +3.65p)
- stoch_trend_pullback_tokyo: Tokyo session only
- ema_trend_scalp_ny: NY session only

New entry_type names are NOT listed in _FORCE_DEMOTED, so signals automatically
accumulate as PHASE0_SHADOW for independent N tracking. Kelly Half Live promotion
gate evaluated after N≥30 per variant.
"""
from datetime import datetime, timezone


def _hour_utc() -> int:
    return datetime.now(timezone.utc).hour


def _reasons_text(sig) -> str:
    reasons = sig.get("reasons") or []
    if isinstance(reasons, str):
        return reasons
    try:
        return " ".join(str(r) for r in reasons)
    except Exception:
        return str(reasons)


def derive_variant_entry_type(sig, df=None, symbol=None):
    """Return a new entry_type if the signal matches a Phase 1 variant filter, else None.

    Call site: immediately after MassiveSignalEnhancer.enhance() so LVN/VWAP reasons
    are populated. Caller preserves base entry_type in sig['_base_entry_type'].
    """
    if not sig or sig.get("signal") in (None, "WAIT"):
        return None

    et = sig.get("entry_type")
    if not et:
        return None

    rtext = _reasons_text(sig)
    h = _hour_utc()

    # engulfing_bb + LVN zone (MassiveSignalEnhancer tags "LVN内" or "低出来高ノード")
    if et == "engulfing_bb":
        if "LVN内" in rtext or "低出来高ノード" in rtext:
            return "engulfing_bb_lvn"
        return None

    # stoch_trend_pullback in Tokyo session (UTC 0-7)
    if et == "stoch_trend_pullback":
        if 0 <= h < 7:
            return "stoch_trend_pullback_tokyo"
        return None

    # ema_trend_scalp in NY session (UTC 16-21)
    if et == "ema_trend_scalp":
        if 16 <= h < 21:
            return "ema_trend_scalp_ny"
        return None

    return None
