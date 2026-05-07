#!/usr/bin/env python3
"""OANDA Labs sentiment cron — append-only history store.

Polls https://labs-api.oanda.com/graphql for retail sentiment
(short_pct) on the 6 BT pairs and appends new rows to
data/sentiment/oanda_labs_h4_history.parquet (deduplicated on
(pair, time_utc)).

Why this exists:
  Phase 1b (OANDA retail-contrarian BT) showed the right qualitative
  shape but is N-bound at high thresholds (>=75). The OANDA Labs API
  only exposes the rolling 90 days, so we must poll and accumulate
  if we ever want enough N at extreme thresholds for Bonferroni.

Schedule:
  Designed to run every 1 hour. Each run fetches the full 90d window
  (cheap, ~500 points per pair) and merges. Beyond 90 days from
  first run the cumulative parquet grows beyond the API window.

Usage:
  python3 scripts/oanda_sentiment_cron.py
  python3 scripts/oanda_sentiment_cron.py --pair EUR_USD  (debug single pair)
  python3 scripts/oanda_sentiment_cron.py --quiet         (suppress non-error stdout)

Output:
  data/sentiment/oanda_labs_h4_history.parquet
    columns: pair (str), time_utc (datetime64 UTC), short_pct (float),
             long_pct (float), fetched_at (datetime64 UTC)

Constraints (verified 2026-05-07):
  - Endpoint requires header `Origin: https://www.oanda.jp`
  - Only valid combo here: granularity=H4, timeSpan=NINETY_DAYS
  - Public API, no auth
"""
from __future__ import annotations

import argparse
import sys
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

PAIRS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CAD", "USD_CHF", "NZD_USD",
    "EUR_JPY", "GBP_JPY", "AUD_JPY", "EUR_AUD", "EUR_GBP", "EUR_CHF", "GBP_CHF",
]
ENDPOINT = "https://labs-api.oanda.com/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://www.oanda.jp",
    "Referer": "https://www.oanda.jp/lab-education/oanda_lab/oanda_rab/orderbook_history/",
    "User-Agent": "Mozilla/5.0",
}
QUERY = (
    "query GetSentiments($instrument: String!, $granularity: Granularity!, $timeSpan: TimeSpan!) "
    "{ sentiments(instrument: $instrument, granularity: $granularity, timeSpan: $timeSpan) "
    "{ sentiments { sentiment { shortPercent } time } } }"
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = REPO_ROOT / "data" / "sentiment" / "oanda_labs_h4_history.parquet"


def fetch_pair(pair: str, timeout: float = 30.0) -> list[dict[str, Any]]:
    payload = {
        "operationName": "GetSentiments",
        "variables": {"instrument": pair, "granularity": "H4", "timeSpan": "NINETY_DAYS"},
        "query": QUERY,
    }
    resp = requests.post(ENDPOINT, json=payload, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    parsed = resp.json()
    if parsed.get("errors"):
        raise RuntimeError(f"GraphQL errors for {pair}: {parsed['errors']}")
    items = (parsed.get("data") or {}).get("sentiments", {}).get("sentiments") or []
    return items


def to_frame(pair: str, items: list[dict[str, Any]], fetched_at: datetime) -> pd.DataFrame:
    rows = []
    for it in items:
        sent = it.get("sentiment") or {}
        short_pct = sent.get("shortPercent")
        time_iso = it.get("time")
        if short_pct is None or time_iso is None:
            continue
        rows.append(
            {
                "pair": pair,
                "time_utc": pd.Timestamp(time_iso).tz_convert("UTC"),
                "short_pct": float(short_pct),
                "long_pct": 100.0 - float(short_pct),
                "fetched_at": fetched_at,
            }
        )
    return pd.DataFrame(rows)


def append_history(new_df: pd.DataFrame) -> tuple[int, int]:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if HISTORY_PATH.exists():
        old_df = pd.read_parquet(HISTORY_PATH)
        before = len(old_df)
        merged = pd.concat([old_df, new_df], ignore_index=True)
    else:
        before = 0
        merged = new_df
    merged = merged.drop_duplicates(subset=["pair", "time_utc"], keep="last").sort_values(
        ["pair", "time_utc"]
    )
    merged.to_parquet(HISTORY_PATH, index=False)
    return before, len(merged)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OANDA Labs sentiment cron")
    parser.add_argument("--pair", help="Limit to one pair (debug)")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-error stdout")
    args = parser.parse_args(argv)

    fetched_at = datetime.now(timezone.utc)
    pairs = [args.pair] if args.pair else PAIRS

    if not args.quiet:
        print(f"[oanda-cron] fetching at {fetched_at.isoformat(timespec='seconds')}")

    frames: list[pd.DataFrame] = []
    for pair in pairs:
        try:
            items = fetch_pair(pair)
        except (requests.exceptions.RequestException, RuntimeError) as exc:
            print(f"[oanda-cron] WARN {pair}: {exc}", file=sys.stderr)
            continue
        frames.append(to_frame(pair, items, fetched_at))
        if not args.quiet:
            print(f"[oanda-cron] {pair}: {len(items)} rows fetched")
        _time.sleep(1.0)

    if not frames:
        print("[oanda-cron] ERROR: no data fetched", file=sys.stderr)
        return 1

    new_df = pd.concat(frames, ignore_index=True)
    before, after = append_history(new_df)
    delta = after - before
    if not args.quiet:
        print(f"[oanda-cron] history: {before} -> {after} rows (+{delta} new)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
