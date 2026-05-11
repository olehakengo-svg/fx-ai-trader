#!/usr/bin/env python3
"""Fetch one MASSIVE FX parquet cache and write a data-quality audit JSON."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.data import fetch_ohlcv_massive  # noqa: E402


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def audit_frame(df: pd.DataFrame, tf: str) -> dict:
    data = _normalize_index(df)
    minutes = {"5m": 5, "1h": 60}.get(tf)
    if data.empty or minutes is None:
        return {
            "rows": int(len(data)),
            "start": None,
            "end": None,
            "gap_count": 0,
            "completeness_pct": 0.0,
        }
    deltas = data.index.to_series().diff().dropna()
    expected = pd.Timedelta(minutes=minutes)
    gap_count = int((deltas > expected * 1.5).sum())
    span_minutes = (data.index[-1] - data.index[0]).total_seconds() / 60
    expected_rows = max(1, int(span_minutes / minutes) + 1)
    completeness = min(100.0, 100.0 * len(data) / expected_rows)
    return {
        "rows": int(len(data)),
        "start": data.index[0].isoformat(),
        "end": data.index[-1].isoformat(),
        "gap_count": gap_count,
        "completeness_pct": round(completeness, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True)
    parser.add_argument("--tf", required=True, choices=["5m", "1h"])
    parser.add_argument("--days", type=int, default=395)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    df = fetch_ohlcv_massive(args.pair, args.tf, args.days)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out)
    audit = {
        "pair": args.pair,
        "tf": args.tf,
        "days_requested": args.days,
        "source": "MASSIVE",
        **audit_frame(df, args.tf),
    }
    audit_path = out.with_suffix(".audit.json")
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

