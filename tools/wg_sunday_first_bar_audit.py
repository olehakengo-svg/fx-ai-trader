#!/usr/bin/env python3
"""weekend_gap_fade — Sunday first-bar / Friday last-bar timestamp audit (price-free).

rule:R3 (2026-10-22, registry `wg-dst-cutoff-basis-r3`, DRAFT
weekend-gap-execution-modality-r1-redraft-DRAFT-2026-09-22 §5 items 1-2).

Question answered: when US DST ends (Sunday open moves 21:00 -> 22:00 UTC),
does the MASSIVE 15m bar index that feeds `detect_weekend_gap_signal`
(`first_bar_ts` = first bar with ts >= Sunday 21:00 UTC, <=24h guard) resolve
to a **22:00-stamped** bar (deadline = 22:15 > real open ~22:04, fine) or to a
**21:00-stamped** bar (deadline 21:15 < real open => deterministic
ABANDONED_HALT every winter weekend = structural bug)?

Reads ONLY the parquet index (timestamps). No OHLC column is loaded, no
outcome / trade table is touched. Pure functions are unit-tested in
tests/test_wg_sunday_first_bar_audit.py.

Usage:
  python3 tools/wg_sunday_first_bar_audit.py \
      --start 2025-10-01 --end 2026-10-22 \
      --out knowledge-base/raw/bt-results/wg-winter-first-bar-audit-2026-10-22.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from strategies.daytrade.weekend_gap_fade import (  # noqa: E402
    SUN_OPEN_GUARD_H,
    WEEKEND_GAP_FADE_PAIRS,
    WEEKEND_GAP_HALT_ABANDON_MIN,
    _last_friday_cut,
)

DEFAULT_CACHE_DIR = os.path.join(_ROOT, "data", "cache", "massive")
WEEKEND_GAP_MIN_H = 40.0   # a Fri->Sun gap is >=47h; holidays (<=24h) are excluded


def load_index(path: str) -> pd.DatetimeIndex:
    """Load ONLY the DatetimeIndex of a 15m parquet (no price columns)."""
    df = pd.read_parquet(path, columns=[])
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.DatetimeIndex(pd.to_datetime(idx))
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    return idx.sort_values()


def weekend_boundaries(idx: pd.DatetimeIndex, min_gap_h: float = WEEKEND_GAP_MIN_H
                       ) -> List[dict]:
    """Return one record per weekend gap in `idx` (gaps >= min_gap_h).

    Each record: last_bar (Fri side), first_bar (Sun side), gap_h.
    Holiday gaps (e.g. Dec-25 ~23h) are excluded by `min_gap_h`.
    """
    if len(idx) < 2:
        return []
    s = pd.Series(idx, index=idx)
    diffs = s.diff()
    mask = diffs >= pd.Timedelta(hours=min_gap_h)
    out: List[dict] = []
    for ts in s[mask]:
        pos = idx.get_loc(ts)
        prev = idx[pos - 1]
        out.append({
            "last_bar": prev,
            "first_bar": ts,
            "gap_h": round((ts - prev).total_seconds() / 3600.0, 2),
        })
    return out


def resolve_as_detector(idx: pd.DatetimeIndex, first_bar: pd.Timestamp) -> dict:
    """Replicate `detect_weekend_gap_signal`'s timestamp resolution for the
    weekend containing `first_bar` (no price access):

      fri_cut  = _last_friday_cut(first_bar)   (Friday 21:00 UTC, DST-blind)
      sun_cut  = fri_cut + 48h                  (Sunday 21:00 UTC, DST-blind)
      fri_close_bar = last bar strictly < fri_cut
      first_bar_ts  = first bar >= sun_cut (guard <= SUN_OPEN_GUARD_H)
      halt_deadline = first_bar_ts + WEEKEND_GAP_HALT_ABANDON_MIN
    """
    fri_cut = _last_friday_cut(first_bar.to_pydatetime())
    sun_cut = fri_cut + timedelta(hours=48)
    i_fri = idx.searchsorted(fri_cut) - 1
    i_sun = idx.searchsorted(sun_cut)
    fri_close_bar = idx[i_fri] if i_fri >= 0 else None
    first_bar_ts = idx[i_sun] if i_sun < len(idx) else None
    within_guard = bool(
        first_bar_ts is not None
        and (first_bar_ts - sun_cut) <= timedelta(hours=SUN_OPEN_GUARD_H)
    )
    deadline = (first_bar_ts + timedelta(minutes=WEEKEND_GAP_HALT_ABANDON_MIN)
                if first_bar_ts is not None else None)
    return {
        "fri_cut": fri_cut,
        "sun_cut": sun_cut,
        "fri_close_bar": fri_close_bar,
        "first_bar_ts": first_bar_ts,
        "first_bar_within_guard": within_guard,
        "halt_deadline": deadline,
        "first_bar_hour_utc": int(first_bar_ts.hour) if first_bar_ts is not None else None,
    }


def _nth_sunday(year: int, month: int, n: int) -> datetime:
    d = datetime(year, month, 1, tzinfo=timezone.utc)
    first_sun = d + timedelta(days=(6 - d.weekday()) % 7)
    return first_sun + timedelta(days=7 * (n - 1))


def expected_sunday_open_hour_utc(sunday) -> int:
    """Expected OANDA Sunday open hour (UTC) from the US DST calendar ONLY —
    independent of any observed bar (positive control for the audit).

    OANDA opens Sunday 17:00 New York. US DST ends on the first Sunday of
    November (-> EST, 22:00 UTC) and starts on the second Sunday of March
    (-> EDT, 21:00 UTC). Both switch Sundays already open at the new hour
    (measured 2025-11-02 -> 22:00, 2026-03-08 -> 21:00).
    """
    ts = pd.Timestamp(sunday)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    y = ts.year
    dst_end = _nth_sunday(y, 11, 1).date()
    dst_start = _nth_sunday(y, 3, 2).date()
    d = ts.date()
    return 22 if (d >= dst_end or d < dst_start) else 21


def classify_open(first_bar: Optional[pd.Timestamp]) -> str:
    """'sun21' (summer stamp) / 'sun22' (winter stamp) / 'other'."""
    if first_bar is None or first_bar.weekday() != 6:
        return "other"
    if first_bar.hour == 21 and first_bar.minute == 0:
        return "sun21"
    if first_bar.hour == 22 and first_bar.minute == 0:
        return "sun22"
    return "other"


def _iso(ts) -> Optional[str]:
    return None if ts is None else pd.Timestamp(ts).isoformat()


def audit_pair(instrument: str, idx: pd.DatetimeIndex,
               start: pd.Timestamp, end: pd.Timestamp) -> dict:
    rows = []
    counts = {"sun21": 0, "sun22": 0, "other": 0}
    deterministic_halt = 0
    for rec in weekend_boundaries(idx):
        fb = rec["first_bar"]
        if fb < start or fb > end:
            continue
        res = resolve_as_detector(idx, fb)
        cls = classify_open(res["first_bar_ts"])
        counts[cls] += 1
        # Expected open hour comes from the US DST calendar, NOT from the
        # observed index (otherwise a vendor 21:00 bar on a winter Sunday
        # would define its own expectation and hide the bug).
        exp_hour = expected_sunday_open_hour_utc(res["sun_cut"])
        resolved_hour = res["first_bar_hour_utc"]
        # structural-bug signature: calendar says winter (22:00 real open) but
        # the detector resolves to a 21:00-stamped bar -> deadline 21:15 < open
        if exp_hour == 22 and resolved_hour == 21:
            deterministic_halt += 1
        rows.append({
            "weekend": res["sun_cut"].date().isoformat(),
            "last_bar": _iso(rec["last_bar"]),
            "first_bar": _iso(fb),
            "gap_h": rec["gap_h"],
            "expected_open_hour_utc": exp_hour,
            "detector_first_bar_ts": _iso(res["first_bar_ts"]),
            "detector_hour_matches_expected": bool(resolved_hour == exp_hour),
            "detector_matches_index_first_bar": bool(res["first_bar_ts"] == fb),
            "detector_fri_close_bar": _iso(res["fri_close_bar"]),
            "halt_deadline": _iso(res["halt_deadline"]),
            "first_bar_within_guard": res["first_bar_within_guard"],
            "class": cls,
        })
    return {
        "instrument": instrument,
        "n_weekends": len(rows),
        "counts": counts,
        "deterministic_halt_signature": deterministic_halt,
        "weekends": rows,
    }


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pairs", nargs="*", default=sorted(WEEKEND_GAP_FADE_PAIRS))
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR)
    ap.add_argument("--start", default="2025-10-01")
    ap.add_argument("--end", default=datetime.now(timezone.utc).date().isoformat())
    ap.add_argument("--out", default=None, help="JSON output path (optional)")
    args = ap.parse_args(list(argv) if argv is not None else None)

    start = pd.Timestamp(args.start, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC") + pd.Timedelta(hours=23, minutes=59)
    report = {
        "tool": "tools/wg_sunday_first_bar_audit.py",
        "rule": "R3",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cache_dir": os.path.relpath(args.cache_dir, _ROOT),
        "window": [args.start, args.end],
        "price_columns_read": 0,
        "pairs": [],
    }
    for inst in args.pairs:
        path = os.path.join(args.cache_dir, f"{inst}_15m.parquet")
        if not os.path.exists(path):
            report["pairs"].append({"instrument": inst, "error": f"missing {path}"})
            continue
        idx = load_index(path)
        rep = audit_pair(inst, idx, start, end)
        rep["index_range"] = [_iso(idx.min()), _iso(idx.max())]
        report["pairs"].append(rep)

    for rep in report["pairs"]:
        if "error" in rep:
            print(f"{rep['instrument']}: {rep['error']}")
            continue
        print(f"=== {rep['instrument']} weekends={rep['n_weekends']} "
              f"counts={rep['counts']} "
              f"deterministic_halt_signature={rep['deterministic_halt_signature']}")
        for r in rep["weekends"]:
            flag = "" if r["detector_hour_matches_expected"] else "  <-- MISMATCH vs DST calendar"
            print(f"  {r['weekend']} last={r['last_bar'][11:16]} "
                  f"first={r['first_bar'][11:16]} expect={r['expected_open_hour_utc']:02d}:00 "
                  f"class={r['class']} deadline={r['halt_deadline'][11:16]}{flag}")
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
