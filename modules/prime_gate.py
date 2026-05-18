"""PRIME gate — condition-based LIVE promotion layer (v9.4, 2026-04-21).

Path A implementation: this module is a pure classifier. It does NOT modify any
signal function or indicator. It inspects the entry context (entry_type,
instrument, sig dict, entry UTC datetime) and, if the context matches one of
the 6 pre-registered PRIME fire conditions, returns the PRIME strategy name,
Evidence Tier (A/B/C) and initial lot multiplier.

The binding pre-registration governs this module:
  knowledge-base/wiki/sessions/prereg-6-prime-strategies-2026-04-21.md
All thresholds, edges, lot multipliers and Tier classifications were
re-evaluated 2026-05-18; see
knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md.

Integration: demo_trader.py calls ``classify_prime(entry_type, instrument,
sig, entry_dt_utc)`` during the OANDA gate decision. If the return is not
None and tier is "A" or "B", the PRIME trade is promoted to LIVE with the
specified ``lot_multiplier`` applied. Tier "C" never promotes (Shadow-only
continuation).

Post-re-eval 2026-05-18 verdict: 5/6 entries failed keep thresholds and
were demoted to Tier C (lot=0.0). engulfing_bb_TOKYO_EARLY remains Tier C
as before. Awaiting v2 candidates from `20260518-XXXX-prime-v2-shadow-audit`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════
# ── Binding quartile edges ──
# ══════════════════════════════════════════════════════════════
# Source: research/prime_gate_v2_proposal.py
# Filter: Render API 2026-04-02 -> 2026-05-18, shadow WIN/LOSS non-XAU rows.
EDGES: Dict[str, List[float]] = {
    "confidence":         [54.0, 64.0, 71.0],
    "rj_adx":             [18.525844, 24.084449, 31.282508],
    "rj_atr_ratio":       [0.926959, 0.983332, 1.091413],
    "rj_close_vs_ema200": [-0.281692, -0.00188, 0.009222],
}


def _quartile(value: Optional[float], edges: List[float]) -> Optional[str]:
    """Map ``value`` to one of Q1..Q4 using the supplied quartile edges.

    Rule: v <= edges[0] -> Q1, <= edges[1] -> Q2, <= edges[2] -> Q3, else Q4.
    Returns None if ``value`` is missing or not numeric.
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v <= edges[0]:
        return "Q1"
    if v <= edges[1]:
        return "Q2"
    if v <= edges[2]:
        return "Q3"
    return "Q4"


def _session_of(hour_utc: int) -> str:
    """Map UTC hour to session band: tokyo 0-8, london 8-13, ny 13-22, offhours else."""
    if 0 <= hour_utc < 8:
        return "tokyo"
    if 8 <= hour_utc < 13:
        return "london"
    if 13 <= hour_utc < 22:
        return "ny"
    return "offhours"


def _parse_regime(sig: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the regime dict from ``sig``.

    ``sig["regime"]`` may already be a dict, or (when round-tripped via DB)
    a JSON string. Returns an empty dict on any parse error.
    """
    rj = sig.get("regime")
    if isinstance(rj, dict):
        return rj
    if isinstance(rj, str) and rj.startswith("{"):
        try:
            return json.loads(rj)
        except (ValueError, TypeError):
            return {}
    return {}


def _feature_bundle(
    instrument: str,
    sig: Dict[str, Any],
    entry_dt_utc: Optional[datetime],
) -> Dict[str, Any]:
    """Assemble the minimal feature bundle the PRIME rules match against.

    All keys are optional; a missing feature simply causes the rule that
    depends on it to be treated as non-matching.
    """
    regime = _parse_regime(sig)

    # Hour / session from entry_dt_utc (falls back to 'now' only when caller
    # omits it — production caller always supplies datetime.now(utc)).
    if entry_dt_utc is None:
        entry_dt_utc = datetime.now(timezone.utc)
    elif entry_dt_utc.tzinfo is None:
        entry_dt_utc = entry_dt_utc.replace(tzinfo=timezone.utc)

    hour = int(entry_dt_utc.hour)
    session = _session_of(hour)

    # direction comes from the signal itself
    direction = str(sig.get("signal") or "").upper()

    # Features with quartile binning (binding edges)
    confidence = sig.get("confidence")
    rj_adx = regime.get("adx")
    rj_atr = regime.get("atr_ratio")
    rj_cvema = regime.get("close_vs_ema200")

    return {
        "instrument": instrument,
        "direction": direction,
        "hour": hour,
        "session": session,
        "confidence": confidence,
        "rj_adx": rj_adx,
        "rj_atr_ratio": rj_atr,
        "rj_close_vs_ema200": rj_cvema,
        "_conf_q":  _quartile(confidence, EDGES["confidence"]),
        "_adx_q":   _quartile(rj_adx, EDGES["rj_adx"]),
        "_atr_q":   _quartile(rj_atr, EDGES["rj_atr_ratio"]),
        "_cvema_q": _quartile(rj_cvema, EDGES["rj_close_vs_ema200"]),
    }


# ══════════════════════════════════════════════════════════════
# ── Binding PRIME specifications ──
# ══════════════════════════════════════════════════════════════
# Format: (prime_name, base_entry_type, tier, lot_multiplier, predicate)
# predicate: callable(features_bundle) -> bool (all-AND fire condition).
#
# Tier A: Bonferroni-6 significant (p < 0.05/6 = 0.0083), WF reproducible,
#         EV+ and PF>1 → lot 0.3x small-lot LIVE trial
# Tier B: raw p<0.05, WF reproducible, EV+ and PF>1, Bonferroni-6 non-sig
#         → lot 0.1x Sentinel
# Tier C: N<10 or raw p>0.10 → stays Shadow, never promotes
#
# Source: prereg-6-prime-strategies-2026-04-21.md sections 2 & 3.
#
# ## 2026-05-18 Re-evaluation outcome
#
# - stoch_trend_pullback_PRIME: DEMOTE from Tier A to Tier C
# - stoch_trend_pullback_LONDON_LOWVOL: DEMOTE from Tier B to Tier C
# - fib_reversal_PRIME: DEMOTE from Tier A to Tier C
# - bb_rsi_reversion_NY_ATRQ2: DEMOTE from Tier B to Tier C
# - engulfing_bb_TOKYO_EARLY: KEEP at Tier C
# - sr_fib_confluence_GBP_ADXQ2: DEMOTE from Tier B to Tier C
_PRIMES: List[Tuple[str, str, str, float, Any]] = [
    # Pre-reg LOCK 2026-05-18: N=22 WR=31.8% Wlo=16.4% Bonf_p=1.00e+00
    # Verdict: DEMOTE from current Tier A
    (
        'stoch_trend_pullback_PRIME',
        'stoch_trend_pullback',
        'C', 0.0,
        lambda f: (f["_atr_q"] == "Q1" and f["direction"] == "BUY"),
    ),
    # Pre-reg LOCK 2026-05-18: N=18 WR=27.8% Wlo=12.5% Bonf_p=1.00e+00
    # Verdict: DEMOTE from current Tier B
    (
        'stoch_trend_pullback_LONDON_LOWVOL',
        'stoch_trend_pullback',
        'C', 0.0,
        lambda f: (f["_atr_q"] == "Q1" and f["session"] == "london"),
    ),
    # Pre-reg LOCK 2026-05-18: N=28 WR=42.9% Wlo=26.5% Bonf_p=2.83e-01
    # Verdict: DEMOTE from current Tier A
    (
        'fib_reversal_PRIME',
        'fib_reversal',
        'C', 0.0,
        lambda f: (f["_conf_q"] == "Q3" and f["_cvema_q"] == "Q3"),
    ),
    # Pre-reg LOCK 2026-05-18: N=48 WR=33.3% Wlo=21.7% Bonf_p=1.00e+00
    # Verdict: DEMOTE from current Tier B
    (
        'bb_rsi_reversion_NY_ATRQ2',
        'bb_rsi_reversion',
        'C', 0.0,
        lambda f: (f["hour"] in (12, 13, 14, 15) and f["_atr_q"] == "Q2"),
    ),
    # Pre-reg LOCK 2026-05-18: N=23 WR=30.4% Wlo=15.6% Bonf_p=1.00e+00
    # Verdict: KEEP from current Tier C
    (
        'engulfing_bb_TOKYO_EARLY',
        'engulfing_bb',
        'C', 0.0,
        lambda f: (f["session"] == "tokyo" and f["hour"] in (0, 1, 2, 3)),
    ),
    # Pre-reg LOCK 2026-05-18: N=19 WR=42.1% Wlo=23.1% Bonf_p=6.42e-01
    # Verdict: DEMOTE from current Tier B
    (
        'sr_fib_confluence_GBP_ADXQ2',
        'sr_fib_confluence',
        'C', 0.0,
        lambda f: (f["instrument"] == "GBP_USD" and f["_adx_q"] == "Q2"),
    ),
]


# Map base entry_type -> list of PRIME rules, for O(1) lookup.
_BY_BASE: Dict[str, List[Tuple[str, str, str, float, Any]]] = {}
for _row in _PRIMES:
    _BY_BASE.setdefault(_row[1], []).append(_row)


def classify_prime(
    entry_type: str,
    instrument: str,
    sig: Dict[str, Any],
    entry_dt_utc: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Return the PRIME classification for this entry, or None.

    Parameters
    ----------
    entry_type : str
        The base strategy entry_type (as produced by the signal function).
    instrument : str
        OANDA instrument code, e.g. "USD_JPY".
    sig : dict
        The signal dict (from the signal function). Must contain "signal"
        (BUY/SELL), "confidence", and a "regime" entry (dict or JSON str).
    entry_dt_utc : datetime, optional
        UTC timestamp for the entry. Defaults to ``datetime.now(timezone.utc)``
        if omitted.

    Returns
    -------
    dict or None
        ``{"name": str, "tier": "A"|"B"|"C", "lot_multiplier": float,
          "base": str, "features": dict}`` if matched, else None.

    Notes
    -----
    This function is pure: it has no side effects, does no I/O, never
    raises on malformed input (returns None instead).
    """
    if not entry_type:
        return None
    candidates = _BY_BASE.get(entry_type)
    if not candidates:
        return None

    try:
        feats = _feature_bundle(instrument, sig or {}, entry_dt_utc)
    except Exception:
        # Fail-closed: any unexpected error → no PRIME promotion.
        return None

    for name, base, tier, lot_mult, predicate in candidates:
        try:
            if predicate(feats):
                return {
                    "name": name,
                    "base": base,
                    "tier": tier,
                    "lot_multiplier": float(lot_mult),
                    "features": feats,
                }
        except Exception:
            # Fail-closed on predicate error (missing feature key, type mismatch).
            continue
    return None


def prime_fingerprint(match: Dict[str, Any]) -> str:
    """Short human-readable fingerprint for logs.

    Example: ``"PRIME[A:stoch_trend_pullback_PRIME lot=0.30 atrQ1/BUY]"``.
    """
    if not match:
        return ""
    name = match.get("name", "?")
    tier = match.get("tier", "?")
    lot = float(match.get("lot_multiplier", 0.0))
    feats = match.get("features", {})
    bits: List[str] = []
    for k in ("direction", "session", "hour",
              "_conf_q", "_adx_q", "_atr_q", "_cvema_q"):
        v = feats.get(k)
        if v is not None and v != "":
            bits.append(f"{k}={v}")
    return f"PRIME[{tier}:{name} lot={lot:.2f} {' '.join(bits)}]"


__all__ = [
    "EDGES",
    "classify_prime",
    "prime_fingerprint",
]
