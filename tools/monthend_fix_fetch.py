#!/usr/bin/env python3
"""Phase 0 data fetch for the month-end WMR fix pre-reg (monthend_fix_drift / _reversion).

Fetches three series for the ~12y pre-reg window and writes a data-quality audit:
  - EUR_USD H1 (traded instrument)        -> MASSIVE API (Polygon-compatible deep FX history)
  - EUR_USD D1 (ATR(20,D1) for TP/SL)     -> MASSIVE API
  - ^GSPC  (S&P 500) daily close           -> yfinance  (signal only, NOT traded)
  - ^STOXX50E (EURO STOXX 50) daily close  -> yfinance  (signal only, NOT traded)

Indices are used solely to build the monthly-return signal (rel = ret(SX5E) - ret(SPX)),
so an external public source is acceptable; the traded leg (EUR_USD) uses the in-system
MASSIVE provider exactly like the D1 TSMOM pre-reg backfill.

Outputs to data/cache/research/monthend_fix/.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load .env (OANDA/MASSIVE keys) without extra deps.
ENV = ROOT / ".env"
if ENV.exists():
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from modules.data import fetch_ohlcv_massive  # noqa: E402

OUT = ROOT / "data" / "cache" / "research" / "monthend_fix"
OUT.mkdir(parents=True, exist_ok=True)

DAYS_12Y = 4400  # ~12.05 years


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def audit_intraday(df: pd.DataFrame, minutes: int) -> dict:
    d = _norm(df)
    deltas = d.index.to_series().diff().dropna()
    expected = pd.Timedelta(minutes=minutes)
    intra_week_gaps = int(((deltas > expected * 1.5) & (deltas < pd.Timedelta(days=3))).sum())
    trading_days = int(len(pd.bdate_range(d.index[0].normalize(), d.index[-1].normalize())))
    expected_rows = max(1, int(trading_days * (24 * 60 / minutes)))
    return {
        "rows": int(len(d)),
        "start": d.index[0].isoformat(),
        "end": d.index[-1].isoformat(),
        "intra_week_gaps": intra_week_gaps,
        "trading_days": trading_days,
        "completeness_pct": round(min(100.0, 100.0 * len(d) / expected_rows), 2),
    }


def audit_daily_index(df: pd.DataFrame, name: str) -> dict:
    d = _norm(df)
    # month-end coverage: number of distinct (year,month) with >=1 obs
    months = d.index.to_period("M").unique()
    return {
        "name": name,
        "rows": int(len(d)),
        "start": d.index[0].isoformat(),
        "end": d.index[-1].isoformat(),
        "distinct_months": int(len(months)),
        "na_close": int(d["Close"].isna().sum()) if "Close" in d else None,
    }


def fetch_index_yf(ticker: str, start: str) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(ticker, start=start, interval="1d", progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = pd.to_datetime(df.index, utc=True)
    return df.sort_index().dropna(subset=["Close"])


def main() -> None:
    audit: dict = {}

    print("[1/4] EUR_USD H1 via MASSIVE (12y) ...", flush=True)
    eur_h1 = fetch_ohlcv_massive("EUR_USD", "1h", DAYS_12Y)
    eur_h1 = _norm(eur_h1)
    eur_h1.to_parquet(OUT / "EUR_USD_1h_12y.parquet")
    audit["EUR_USD_1h"] = audit_intraday(eur_h1, 60)
    print("   ", audit["EUR_USD_1h"], flush=True)

    print("[2/4] EUR_USD D1 via MASSIVE (12y, for ATR20) ...", flush=True)
    eur_d1 = fetch_ohlcv_massive("EUR_USD", "1d", DAYS_12Y)
    eur_d1 = _norm(eur_d1)
    eur_d1.to_parquet(OUT / "EUR_USD_1d_12y.parquet")
    audit["EUR_USD_1d"] = audit_intraday(eur_d1, 1440)
    print("   ", audit["EUR_USD_1d"], flush=True)

    start = eur_h1.index[0].strftime("%Y-%m-%d")
    print(f"[3/4] ^GSPC (S&P500) daily via yfinance from {start} ...", flush=True)
    spx = fetch_index_yf("^GSPC", start)
    spx.to_parquet(OUT / "GSPC_1d.parquet")
    audit["SPX"] = audit_daily_index(spx, "^GSPC")
    print("   ", audit["SPX"], flush=True)

    print(f"[4/4] ^STOXX50E (EURO STOXX 50) daily via yfinance from {start} ...", flush=True)
    sx5e = fetch_index_yf("^STOXX50E", start)
    sx5e.to_parquet(OUT / "STOXX50E_1d.parquet")
    audit["SX5E"] = audit_daily_index(sx5e, "^STOXX50E")
    print("   ", audit["SX5E"], flush=True)

    (OUT / "phase0_audit.json").write_text(json.dumps(audit, indent=2))
    print("\nAUDIT WRITTEN ->", OUT / "phase0_audit.json", flush=True)


if __name__ == "__main__":
    main()
