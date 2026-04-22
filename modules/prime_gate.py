"""PRIME gate — condition-based LIVE promotion layer (v9.4, 2026-04-21).

Path A implementation: this module is a pure classifier. It does NOT modify any
signal function or indicator. It inspects the entry context (entry_type,
instrument, sig dict, entry UTC datetime) and, if the context matches one of
the 6 pre-registered PRIME fire conditions, returns the PRIME strategy name,
Evidence Tier (A/B/C) and initial lot multiplier.

The binding pre-registration governs this module:
  knowledge-base/wiki/sessions/prereg-6-prime-strategies-2026-04-21.md
All thresholds, edges, lot multipliers and Tier classifications are frozen
until the 2026-05-15 re-evaluation checkpoint. Do NOT edit any constant in
this file before that date except for bug fixes.

Integration: demo_trader.py calls ``classify_prime(entry_type, instrument,
sig, entry_dt_utc)`` during the OANDA gate decision. If the return is not
None and tier is "A" or "B", the PRIME trade is promoted to LIVE with the
specified ``lot_multiplier`` applied. Tier "C" never promotes (Shadow-only
continuation until 2026-05-15 re-evaluation).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════
# ── Binding quartile edges (DO NOT EDIT before 2026-05-15) ──
# ══════════════════════════════════════════════════════════════
# Source: knowledge-base/wiki/sessions/task1-win-dna-2026-04-21.py
# Filter: is_shadow=1 AND outcome IN (WIN,LOSS) AND instrument != XAU_USD
# N=1711 (WIN=474, LOSS=1237), Cutoff=2026-04-16
EDGES: Dict[str, List[float]] = {
    "confidence":        [53.0, 61.0, 69.0],     # Q1/Q2/Q3/Q4 boundaries
    "rj_adx":            [20.3, 25.3, 31.7],
    "rj_atr_ratio":      [0.95, 1.01, 1.09],
    "rj_close_vs_ema200": [-0.019, 0.001, 0.034],
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
_PRIMES: List[Tuple[str, str, str, float, Any]] = [
    # (1) stoch_trend_pullback_PRIME — Tier A
    # Shadow: N=24 WR=58.3% PF=2.10 EV=+1.51p, Fisher p=0.0010 (Bonf ✓)
    (
        "stoch_trend_pullback_PRIME",
        "stoch_trend_pullback",
        "A", 0.3,
        lambda f: (f["_atr_q"] == "Q1" and f["direction"] == "BUY"),
    ),
    # (2) stoch_trend_pullback_LONDON_LOWVOL — Tier B
    # Shadow: N=11 WR=63.6% PF=2.43 EV=+2.06p, Fisher p=0.0138
    (
        "stoch_trend_pullback_LONDON_LOWVOL",
        "stoch_trend_pullback",
        "B", 0.1,
        lambda f: (f["_atr_q"] == "Q1" and f["session"] == "london"),
    ),
    # (3) fib_reversal_PRIME — Tier A
    # Shadow: N=12 WR=75.0% PF=4.99 EV=+2.96p, Fisher p=0.0046 (Bonf ✓)
    (
        "fib_reversal_PRIME",
        "fib_reversal",
        "A", 0.3,
        lambda f: (f["_conf_q"] == "Q3" and f["_cvema_q"] == "Q3"),
    ),
    # (4) bb_rsi_reversion_NY_ATRQ2 — Tier B
    # Shadow: N=18 WR=55.6% PF=1.30 EV=+0.82p, Fisher p=0.0113
    (
        "bb_rsi_reversion_NY_ATRQ2",
        "bb_rsi_reversion",
        "B", 0.1,
        lambda f: (f["hour"] in (12, 13, 14, 15) and f["_atr_q"] == "Q2"),
    ),
    # (5) engulfing_bb_TOKYO_EARLY — Tier C (shadow-only, not promoted)
    # Shadow: N=9 WR=55.6% PF=2.73 EV=+2.18p, Fisher p=0.1374 (no sig)
    (
        "engulfing_bb_TOKYO_EARLY",
        "engulfing_bb",
        "C", 0.0,  # 0.0 => never promoted
        lambda f: (f["session"] == "tokyo" and f["hour"] in (0, 1, 2, 3)),
    ),
    # (6) sr_fib_confluence_GBP_ADXQ2 — Tier B
    # Shadow: N=13 WR=53.8% PF=1.46 EV=+1.75p, Fisher p=0.0148
    (
        "sr_fib_confluence_GBP_ADXQ2",
        "sr_fib_confluence",
        "B", 0.1,
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
