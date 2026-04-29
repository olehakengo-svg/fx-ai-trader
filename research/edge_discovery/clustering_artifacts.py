"""Trade clustering / repeat-firing artifact detection.

Phase 9 walk-forward 3-fold scanner catches *time-regime* fragility (a cell
that wins in one fold and loses in another). It does NOT catch the
within-fold artifact where a single setup fires many times in a few minutes
at near-identical entry/SL prices, inflating sample size without independent
information.

Concrete case (2026-04-28 audit): fib_reversal × USD_JPY × Tokyo prime
showed 24 wins/3 losses in shadow data — but 17 of 21 wins came from a
single 17-minute window on 2026-04-08 at 158.49–158.53. Each "trade" was
the same signal repeating, not 21 independent setups.

This module is **complementary** to walk_forward_scanner: walk-forward
checks regime stability across folds; this checks within-cell independence
of trade samples. Both should be applied before LOCK.

Public API
----------
``detect_repeat_firing(rows, pair=None)``
  Inspect a list of trade dicts (or sqlite3.Row objects) and return a
  verdict dict with single-day / burst-firing / price-cluster diagnostics
  plus a ``verdict ∈ {clean, weak_clustering, artifactual}`` label.

``downgrade_verdict(base_verdict, clustering_verdict)``
  Combine an external robustness verdict with the clustering verdict.
  ``artifactual`` always wins; ``weak_clustering`` downgrades by one step.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping, Sequence


# Triggering thresholds (calibrated from 2026-04-28 fib_reversal artifact)
SINGLE_DAY_DOMINANT: float = 0.70  # ≥70% trades on a single UTC date
SINGLE_DAY_CONCENTRATION: float = 0.50  # ≥50% triggers weak flag
BURST_DOMINANT: float = 0.50  # ≥50% in any 30-min window
BURST_MODERATE: float = 0.30
PRICE_TIGHT_PIPS: float = 1.0  # entry/SL stdev <1 pip → same-setup cluster
PRICE_LOOSE_PIPS: float = 5.0  # <5 pips still suspicious for single setup
BURST_WINDOW: timedelta = timedelta(minutes=30)


def _pip_size(pair: str | None) -> float:
    """Price units per pip for an FX/metal pair."""
    p = (pair or "USD_JPY").upper()
    if "JPY" in p or "XAU" in p:
        return 0.01
    return 0.0001


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return (
            datetime.fromisoformat(s.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
        )
    except Exception:
        return None


def _row_get(row, key, default=None):
    """Uniform getter for sqlite3.Row OR dict OR mapping."""
    if isinstance(row, Mapping):
        return row.get(key, default)
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def _stddev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def detect_repeat_firing(
    rows: Iterable,
    pair: str | None = None,
    *,
    burst_window: timedelta = BURST_WINDOW,
) -> dict:
    """Inspect trades for within-cell repeat-firing artifacts.

    Parameters
    ----------
    rows
        Iterable of trade records (sqlite3.Row, dict, or other mapping).
        Required keys: entry_time, entry_price, sl, instrument.
    pair
        Override pair for pip-size lookup. If None, taken from row's
        ``instrument`` (first row).
    burst_window
        Sliding window for burst-firing detection (default 30 min).

    Returns
    -------
    dict with keys:
        single_day_share / single_day_top
        burst_share / burst_window_iso (start ISO if any burst)
        entry_price_sigma_pips / sl_price_sigma_pips
        flags: list[str]
        verdict: 'clean' | 'weak_clustering' | 'artifactual'
    """
    rows = list(rows)
    if not rows:
        return {
            "verdict": "clean", "flags": [],
            "single_day_share": 0.0, "single_day_top": None,
            "burst_share": 0.0, "burst_window_iso": None,
            "entry_price_sigma_pips": 0.0, "sl_price_sigma_pips": 0.0,
            "n": 0,
        }

    n = len(rows)
    pair_resolved = pair or _row_get(rows[0], "instrument") or "USD_JPY"
    pip = _pip_size(pair_resolved)

    # 1) Single-day concentration
    by_day: dict[str, int] = defaultdict(int)
    for r in rows:
        ts = _parse_iso(_row_get(r, "entry_time"))
        if ts is not None:
            by_day[ts.date().isoformat()] += 1
    if by_day:
        single_day_top, single_day_count = max(by_day.items(), key=lambda x: x[1])
        single_day_share = single_day_count / n
    else:
        single_day_top, single_day_share = None, 0.0

    # 2) Burst-firing: max trades within any rolling burst_window
    timestamps = sorted(
        t for t in (_parse_iso(_row_get(r, "entry_time")) for r in rows)
        if t is not None
    )
    burst_share = 0.0
    burst_start_iso: str | None = None
    if len(timestamps) >= 2:
        max_in_window = 1
        max_start = timestamps[0]
        for i, t0 in enumerate(timestamps):
            j = i
            while j < len(timestamps) and (timestamps[j] - t0) <= burst_window:
                j += 1
            count = j - i
            if count > max_in_window:
                max_in_window = count
                max_start = t0
        burst_share = max_in_window / n
        if max_in_window > 1:
            burst_start_iso = max_start.isoformat()

    # 3) Entry / SL price tightness in pip units
    entry_prices = [
        float(_row_get(r, "entry_price") or 0.0) for r in rows
        if _row_get(r, "entry_price") is not None
    ]
    sls = [
        float(_row_get(r, "sl") or 0.0) for r in rows
        if _row_get(r, "sl") is not None
    ]
    entry_sigma_pips = _stddev(entry_prices) / pip if pip > 0 else 0.0
    sl_sigma_pips = _stddev(sls) / pip if pip > 0 else 0.0

    flags: list[str] = []
    if single_day_share >= SINGLE_DAY_DOMINANT:
        flags.append("single_day_dominance")
    elif single_day_share >= SINGLE_DAY_CONCENTRATION:
        flags.append("single_day_concentration")
    if burst_share >= BURST_DOMINANT:
        flags.append("burst_firing")
    elif burst_share >= BURST_MODERATE:
        flags.append("burst_clustering")
    if entry_sigma_pips < PRICE_TIGHT_PIPS and n >= 5:
        flags.append("same_entry_price_cluster")
    elif entry_sigma_pips < PRICE_LOOSE_PIPS and n >= 5:
        flags.append("tight_entry_price_cluster")
    if sl_sigma_pips < PRICE_TIGHT_PIPS and n >= 5:
        flags.append("same_sl_cluster")

    if (
        single_day_share >= SINGLE_DAY_DOMINANT
        or (burst_share >= BURST_DOMINANT and entry_sigma_pips < PRICE_LOOSE_PIPS)
    ):
        verdict = "artifactual"
    elif (
        single_day_share >= SINGLE_DAY_CONCENTRATION
        or burst_share >= BURST_MODERATE
        or entry_sigma_pips < PRICE_TIGHT_PIPS
    ):
        verdict = "weak_clustering"
    else:
        verdict = "clean"

    return {
        "n": n,
        "single_day_share": round(single_day_share, 3),
        "single_day_top": single_day_top,
        "burst_share": round(burst_share, 3),
        "burst_window_iso": burst_start_iso,
        "entry_price_sigma_pips": round(entry_sigma_pips, 3),
        "sl_price_sigma_pips": round(sl_sigma_pips, 3),
        "flags": flags,
        "verdict": verdict,
    }


def downgrade_verdict(base: str, clustering: str) -> str:
    """Combine a base robustness verdict with a clustering verdict.

    Rules:
    - clustering=='artifactual' → returns 'artifactual' (overrides base)
    - clustering=='weak_clustering' → downgrades base one step
        robust → partial → fragile → fragile
    - clustering=='clean' → base unchanged
    """
    if clustering == "artifactual":
        return "artifactual"
    if clustering == "weak_clustering":
        ladder = {"robust": "partial", "partial": "fragile",
                  "fragile": "fragile", "insufficient": "fragile"}
        return ladder.get(base, base)
    return base
