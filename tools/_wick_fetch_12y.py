#!/usr/bin/env python3
"""One-off fetch: GBP_USD H1 + D1 12y from MASSIVE for wick-imb continuation BT.

Writes to dedicated files (does NOT clobber the production caches):
  data/cache/massive/GBP_USD_1h_12y_massive.parquet
  data/cache/massive/GBP_USD_1d_12y_massive.parquet
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# load .env
for line in open(ROOT / ".env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        import os
        os.environ.setdefault(k, v)

import pandas as pd  # noqa: E402
from modules.data import fetch_ohlcv_massive  # noqa: E402

DAYS = 4600  # ~12.6y back from 2026-06 -> ~2013-11

def go(tf: str, out_name: str):
    print(f"[fetch] GBP_USD {tf} days={DAYS} ...", flush=True)
    df = fetch_ohlcv_massive("GBP_USD", tf, DAYS)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    elif df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df = df.sort_index()
    out = ROOT / "data" / "cache" / "massive" / out_name
    df.to_parquet(out)
    info = {
        "tf": tf, "rows": int(len(df)),
        "start": df.index[0].isoformat(), "end": df.index[-1].isoformat(),
        "out": str(out),
    }
    print("[done] " + json.dumps(info), flush=True)
    return info

if __name__ == "__main__":
    r1 = go("1h", "GBP_USD_1h_12y_massive.parquet")
    r2 = go("1d", "GBP_USD_1d_12y_massive.parquet")
    print("ALL_DONE " + json.dumps([r1, r2]), flush=True)
