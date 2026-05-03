#!/usr/bin/env python3
"""
W3 Data Prep — fetch FX M5 12-year history from Massive Market Data API and
write parquet for Codex offline BT consumption.

Originally W3-3 Phase 0 (USDJPY only). Generalised 2026-05-03 to support any
Polygon-compatible ticker via --ticker / --pair (W3-4 GBPJPY unblock task).

Idempotent: skips fetch if output parquet already covers the requested window.

Defaults: USDJPY (preserves W3-3 reproducibility).
Run from Claude (司令塔) host — Codex sandbox cannot reach DNS.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

ALLOWED_HOST = "api.massive.com"


def _safe_get(url: str, headers: dict, timeout: int = 60) -> dict:
    """urllib GET with strict scheme/host whitelist (prevents file:// and SSRF
    from a poisoned next_url). Massive's pagination only ever returns URLs on
    api.massive.com over https; anything else is a protocol violation."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise RuntimeError(f"refusing non-https URL: {parsed.scheme}://{parsed.netloc}")
    if parsed.hostname != ALLOWED_HOST:
        raise RuntimeError(f"refusing non-allowlisted host: {parsed.hostname}")
    req = urllib.request.Request(url, headers=headers)  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosemgrep
        return json.load(resp)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "cache" / "massive"
DEFAULT_PAIR = "USD_JPY"
DEFAULT_TICKER = "C:USDJPY"
DEFAULT_OUTPUT = DEFAULT_OUTPUT_DIR / "USD_JPY_5m_2014_2026.parquet"
ENV_PATH = REPO_ROOT / ".env"

MULT, TIMESPAN = 5, "minute"
DEFAULT_FROM = "2014-01-01"
DEFAULT_TO = "2026-04-30"
LIMIT = 50000
MAX_PAGES_PER_YEAR = 30


def load_api_key() -> str:
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if key:
        return key
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("MASSIVE_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    raise SystemExit("MASSIVE_API_KEY not found in environment or .env")


def fetch_year(api_key: str, ticker: str, year_from: str, year_to: str) -> list[dict]:
    base = f"https://api.massive.com/v2/aggs/ticker/{ticker}/range/{MULT}/{TIMESPAN}/{year_from}/{year_to}"
    url = f"{base}?adjusted=true&sort=asc&limit={LIMIT}"
    headers = {"User-Agent": "fx-ai-trader/phase0", "Authorization": f"Bearer {api_key}"}
    rows: list[dict] = []
    for page in range(MAX_PAGES_PER_YEAR):
        try:
            payload = _safe_get(url, headers)
        except Exception as exc:
            if page == 0:
                raise RuntimeError(f"first-page fetch failed for {year_from}..{year_to}: {exc}") from exc
            print(f"  [warn] page {page}: {exc}", file=sys.stderr)
            break
        results = payload.get("results", []) or []
        rows.extend(results)
        next_url = payload.get("next_url")
        if not next_url or not results:
            break
        url = next_url
        time.sleep(0.1)
    return rows


def coverage_ok(parquet_path: Path, want_from: str, want_to: str) -> bool:
    if not parquet_path.exists():
        return False
    try:
        df = pd.read_parquet(parquet_path)
    except Exception:
        return False
    if df.empty:
        return False
    idx = pd.to_datetime(df.index, utc=True)
    have_from = idx.min().strftime("%Y-%m-%d")
    have_to = idx.max().strftime("%Y-%m-%d")
    return have_from <= want_from and have_to >= want_to


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default=DEFAULT_PAIR, help="Pair label for output naming, e.g. USD_JPY / GBP_JPY")
    ap.add_argument("--ticker", default=None, help="Massive/Polygon ticker (default derived from --pair as C:<pair without underscore>)")
    ap.add_argument("--from", dest="date_from", default=DEFAULT_FROM)
    ap.add_argument("--to", dest="date_to", default=DEFAULT_TO)
    ap.add_argument("--output", default=None, help="Output parquet path (default data/cache/massive/<pair>_5m_<years>.parquet)")
    ap.add_argument("--force", action="store_true", help="refetch even if cache covers range")
    args = ap.parse_args()

    pair = args.pair
    ticker = args.ticker or f"C:{pair.replace('_', '')}"
    if args.output:
        output = Path(args.output)
    else:
        years_tag = f"{args.date_from[:4]}_{args.date_to[:4]}"
        output = DEFAULT_OUTPUT_DIR / f"{pair}_5m_{years_tag}.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)

    if not args.force and coverage_ok(output, args.date_from, args.date_to):
        df = pd.read_parquet(output)
        print(f"[skip] cache already covers {args.date_from}..{args.date_to}: {output} ({len(df):,} rows)")
        return 0

    api_key = load_api_key()
    print(f"[fetch] {ticker} ({pair}) {MULT}{TIMESPAN[:1]} {args.date_from}..{args.date_to}")
    print(f"[output] {output}")

    start_year = int(args.date_from[:4])
    end_year = int(args.date_to[:4])
    all_rows: list[dict] = []
    t0 = time.time()
    for year in range(start_year, end_year + 1):
        y_from = max(args.date_from, f"{year}-01-01")
        y_to = min(args.date_to, f"{year}-12-31")
        ts0 = time.time()
        rows = fetch_year(api_key, ticker, y_from, y_to)
        ts1 = time.time()
        all_rows.extend(rows)
        print(f"  {year}: {len(rows):>7,} bars ({ts1 - ts0:5.1f}s)")
    t_fetch = time.time() - t0

    if not all_rows:
        raise SystemExit("Massive API returned no data")

    df = pd.DataFrame(
        {
            "open": [float(r["o"]) for r in all_rows],
            "high": [float(r["h"]) for r in all_rows],
            "low": [float(r["l"]) for r in all_rows],
            "close": [float(r["c"]) for r in all_rows],
            "volume": [float(r.get("v", 0)) for r in all_rows],
            "vwap": [float(r.get("vw", r["c"])) for r in all_rows],
            "n_transactions": [int(r.get("n", 0)) for r in all_rows],
        },
        index=pd.DatetimeIndex(pd.to_datetime([r["t"] for r in all_rows], unit="ms", utc=True), name="timestamp_utc"),
    )
    df = df[~df.index.duplicated(keep="last")].sort_index()

    df.to_parquet(output, compression="snappy")
    size_mb = output.stat().st_size / 1024 / 1024
    print(
        f"[done] {len(df):,} bars, {df.index.min()} .. {df.index.max()}, "
        f"{size_mb:.1f} MB, fetch={t_fetch:.1f}s"
    )

    audit = {
        "phase": "W3 Data Prep",
        "pair": pair,
        "ticker": ticker,
        "interval": f"{MULT}{TIMESPAN}",
        "requested_from": args.date_from,
        "requested_to": args.date_to,
        "actual_from": str(df.index.min()),
        "actual_to": str(df.index.max()),
        "rows": int(len(df)),
        "size_mb": round(size_mb, 2),
        "fetch_seconds": round(t_fetch, 1),
        "output": str(output),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "Massive Market Data API (Polygon-compatible)",
    }
    audit_path = output.with_suffix(".audit.json")
    audit_path.write_text(json.dumps(audit, indent=2))
    print(f"[audit] {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
