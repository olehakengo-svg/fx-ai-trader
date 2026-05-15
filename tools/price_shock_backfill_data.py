#!/usr/bin/env python3
"""Backfill MASSIVE parquet caches for the price-shock reproduction grid."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAIRS = [
    "USD_JPY",
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "NZD_USD",
    "USD_CAD",
    "USD_CHF",
    "EUR_JPY",
    "GBP_JPY",
    "AUD_JPY",
    "NZD_JPY",
    "EUR_GBP",
    "EUR_AUD",
]
TFS = ["4h", "1h"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1600)
    parser.add_argument("--cache-dir", default=str(ROOT / "data" / "cache" / "massive"))
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--sleep", type=float, default=15.0)
    return parser.parse_args()


def run_fetch(pair: str, tf: str, days: int, cache_dir: Path, retries: int, sleep_s: float) -> dict:
    out = cache_dir / f"{pair}_{tf}.parquet"
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "fetch_massive_data.py"),
        "--pair",
        pair,
        "--tf",
        tf,
        "--days",
        str(days),
        "--out",
        str(out),
    ]
    last_error = ""
    for attempt in range(1, retries + 2):
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout.strip().splitlines()[-1])
            except (IndexError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"{pair} {tf} fetch produced invalid audit JSON: {exc}") from exc
        last_error = (proc.stderr or proc.stdout).strip()
        if attempt <= retries:
            time.sleep(sleep_s * attempt)
    raise RuntimeError(f"{pair} {tf} fetch failed after {retries + 1} attempts: {last_error}")


def main() -> int:
    args = parse_args()
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    audits: list[dict] = []
    failures: list[str] = []
    for pair in PAIRS:
        for tf in TFS:
            try:
                audit = run_fetch(pair, tf, args.days, cache_dir, args.retries, args.sleep)
                audits.append(audit)
                print(json.dumps(audit, sort_keys=True), flush=True)
            except Exception as exc:
                failures.append(f"{pair} {tf}: {exc}")
                print(f"FAIL {pair} {tf}: {exc}", file=sys.stderr, flush=True)
    summary = {
        "requested": len(PAIRS) * len(TFS),
        "succeeded": len(audits),
        "failed": len(failures),
        "failures": failures,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
