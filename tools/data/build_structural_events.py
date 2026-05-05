#!/usr/bin/env python3
"""Build structural calendar events for SFT-1 research BTs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

try:
    import jpholiday
except ImportError:  # pragma: no cover - production path uses dependency.
    jpholiday = None


def is_jp_holiday(day: pd.Timestamp) -> bool:
    if jpholiday is None:
        return False
    return bool(jpholiday.is_holiday(day.date()))


def build_structural_events(start: str, end: str) -> pd.DataFrame:
    dates = pd.date_range(start=start, end=end, freq="D", tz="UTC")
    us_holidays = {
        pd.Timestamp(d).date()
        for d in USFederalHolidayCalendar().holidays(start=start, end=end)
    }
    rows = []
    for ts in dates:
        date = ts.date()
        weekday = ts.weekday()
        jp_holiday = is_jp_holiday(ts)
        rows.append(
            {
                "date_utc": ts.normalize(),
                "jp_business_day": weekday < 5 and not jp_holiday,
                "us_business_day": weekday < 5 and date not in us_holidays,
                "jp_holiday": jp_holiday,
                "tokyo_fix_utc": ts.normalize() + pd.Timedelta(minutes=55),
                "london_fix_utc": ts.normalize() + pd.Timedelta(hours=16),
            }
        )
    df = pd.DataFrame(rows)
    df["month_end_jp"] = False
    df["month_end_us"] = False
    for col, out_col in (("jp_business_day", "month_end_jp"), ("us_business_day", "month_end_us")):
        bd = df[df[col]].copy()
        month_key = df.loc[bd.index, "date_utc"].dt.strftime("%Y-%m")
        idx = bd.groupby(month_key)["date_utc"].idxmax()
        df.loc[idx, out_col] = True
    df["quarter_end_jp"] = df["month_end_jp"] & df["date_utc"].dt.month.isin([3, 9])
    return df[
        [
            "date_utc",
            "jp_business_day",
            "us_business_day",
            "month_end_jp",
            "month_end_us",
            "quarter_end_jp",
            "tokyo_fix_utc",
            "london_fix_utc",
            "jp_holiday",
        ]
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = build_structural_events(args.start, args.end)
    df.to_parquet(out, index=False)
    print(f"wrote {out} rows={len(df)} start={df['date_utc'].min()} end={df['date_utc'].max()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
