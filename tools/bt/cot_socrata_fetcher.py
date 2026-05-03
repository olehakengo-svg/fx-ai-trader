#!/usr/bin/env python3
"""Prepare COT and yfinance JSON caches for S3 pair-pool BT."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.bt.s3_pair_pool_fdr import MARKETS, PAIR_POOL, YFINANCE_TICKERS, parse_pairs


COT_API = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fetch_cot_pair(pair: str, since: str, until: str) -> list[dict[str, Any]]:
    market = MARKETS[pair]
    params = urllib.parse.urlencode(
        {
            "$select": "report_date_as_yyyy_mm_dd,contract_market_name,dealer_positions_long_all,dealer_positions_short_all,change_in_dealer_long_all,change_in_dealer_short_all",
            "$where": (
                f"contract_market_name='{market}' "
                f"AND report_date_as_yyyy_mm_dd >= '{since}T00:00:00' "
                f"AND report_date_as_yyyy_mm_dd <= '{until}T00:00:00'"
            ),
            "$order": "report_date_as_yyyy_mm_dd ASC",
            "$limit": "50000",
        }
    )
    url = f"{COT_API}?{params}"
    with urllib.request.urlopen(url, timeout=30) as response:
        raw_rows = json.loads(response.read().decode("utf-8"))
    rows = []
    for row in raw_rows:
        rows.append(
            {
                "report_date": str(row.get("report_date_as_yyyy_mm_dd", ""))[:10],
                "contract_market_name": row.get("contract_market_name", market),
                "dealer_positions_long_all": _num(row.get("dealer_positions_long_all")),
                "dealer_positions_short_all": _num(row.get("dealer_positions_short_all")),
                "change_in_dealer_long_all": _num(row.get("change_in_dealer_long_all")),
                "change_in_dealer_short_all": _num(row.get("change_in_dealer_short_all")),
                "source_url": url,
            }
        )
    return rows


def fetch_yfinance_pair(pair: str, since: str, until: str) -> list[dict[str, Any]]:
    import yfinance as yf

    df = yf.download(YFINANCE_TICKERS[pair], start=since, end=until, progress=False, auto_adjust=False)
    if df.empty:
        return []
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    close_col = "Close" if "Close" in df.columns else "Adj Close"
    rows = []
    for idx, row in df.reset_index().iterrows():
        rows.append({"date": pd.Timestamp(row["Date"]).strftime("%Y-%m-%d"), "close": float(row[close_col])})
    return rows


def write_pair_cache(out_dir: Path, pair: str, rows: list[dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{pair}.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", default=",".join(PAIR_POOL))
    parser.add_argument("--since", required=True)
    parser.add_argument("--until", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--download-yfinance", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out)
    for pair in parse_pairs(args.pairs):
        rows = (
            fetch_yfinance_pair(pair, args.since, args.until)
            if args.download_yfinance
            else fetch_cot_pair(pair, args.since, args.until)
        )
        write_pair_cache(out_dir, pair, rows)
        print(f"{pair}: wrote {len(rows)} rows to {out_dir / f'{pair}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
