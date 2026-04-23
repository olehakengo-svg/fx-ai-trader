"""
Shadow variant routing — derive filter-specialized entry_type names from runtime conditions.

Active variants (2026-04-23, post Bootstrap EV CI validation):
- engulfing_bb_lvn_london_ny: LVN zone × London(UTC7-12)/NY(UTC16-21) session
    Base subset N=25 (London 13 WR=53.8% EV+0.68p, NY 12 WR=41.7% EV+2.40p)
    Shadow で変種固有 Bootstrap EV_lo>0 を確認後 Kelly Half Live 昇格判断。

Retracted variants (2026-04-23, failed promotion gate at base-subset validation):
- stoch_trend_pullback_tokyo: 実コスト 5.28p, Top1-drop EV=-6.10p, tail-driven のため撤回
- ema_trend_scalp_ny: 実コスト 8.65p, Top1-drop EV=-6.61p, tail-driven のため撤回
  Lever-B で「上位セル」に見えた EV は Top1 単独依存、実コストで完全に負 EV。

New entry_type names are NOT listed in _FORCE_DEMOTED, so signals automatically
accumulate as PHASE0_SHADOW for independent N tracking.
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
    # Overlap 12-16 と Tokyo 0-7 は EV drag のため除外
    if et == "engulfing_bb":
        in_lvn = ("LVN内" in rtext) or ("低出来高ノード" in rtext)
        in_london_ny = (7 <= h < 12) or (16 <= h < 21)
        if in_lvn and in_london_ny:
            return "engulfing_bb_lvn_london_ny"
        return None

    return None
