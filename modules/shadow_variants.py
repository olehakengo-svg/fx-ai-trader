"""
Shadow variant routing — derive filter-specialized entry_type names from runtime conditions.

Phase 1 variants (derived from quant analysis 2026-04-23):
- engulfing_bb_lvn_london_ny: LVN zone × London(UTC7-12)/NY(UTC16-21) session
    * 元 engulfing_bb_lvn (全セッション) は Bootstrap EV_lo<0 で昇格ゲート不通過
    * セル分解で Overlap/Tokyo が drag、London N=13 WR=53.8% EV=+0.68p, NY N=12 WR=41.7% EV=+2.40p
    * 精密化により真のエッジ源 (LVN × London/NY) のみ shadow 対象化
- stoch_trend_pullback_tokyo: Tokyo session only (UTC 0-7)
- ema_trend_scalp_ny: NY session only (UTC 16-21)

New entry_type names are NOT listed in _FORCE_DEMOTED, so signals automatically
accumulate as PHASE0_SHADOW for independent N tracking. Kelly Half Live promotion
gate evaluated after variant-specific Bootstrap EV_cost_lo > 0 確認.
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

    # engulfing_bb + LVN zone + London(7-12) or NY(16-21) session
    # (Overlap 12-16 と Tokyo 0-7 は EV drag のため除外)
    if et == "engulfing_bb":
        in_lvn = ("LVN内" in rtext) or ("低出来高ノード" in rtext)
        in_london_ny = (7 <= h < 12) or (16 <= h < 21)
        if in_lvn and in_london_ny:
            return "engulfing_bb_lvn_london_ny"
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
