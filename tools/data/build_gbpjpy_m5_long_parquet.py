"""Convert dukascopy-node CSV output to BT-loader-compatible parquet.

Source: /tmp/dukascopy_full/download/gbpjpy-m5-bid-<from>-<to>.csv (any pattern)
Output: data/cache/extended/GBP_JPY_5m_long.parquet

CSV schema: timestamp(ms),open,high,low,close[,volume]
Parquet schema: DatetimeIndex (UTC) with columns Open/High/Low/Close/Volume
(Volume defaults to 0 if absent in source CSV.)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = Path("/tmp/dukascopy_full/download")
DEFAULT_OUTPUT = REPO_ROOT / "data" / "cache" / "extended" / "GBP_JPY_5m_long.parquet"
DEFAULT_AUDIT = REPO_ROOT / "data" / "cache" / "extended" / "GBP_JPY_5m_long.audit.json"


def load_csv(input_dirs: list[Path]) -> pd.DataFrame:
    files: list[Path] = []
    for d in input_dirs:
        files.extend(sorted(d.glob("gbpjpy-m5-bid-*.csv")))
    if not files:
        raise FileNotFoundError(f"no csv under {input_dirs}")
    frames = []
    for f in files:
        df = pd.read_csv(f)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df["timestamp"].max() > 1e12:
        idx = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    else:
        idx = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    volume = df["volume"].astype("float64").to_numpy() if "volume" in df.columns else 0.0
    out = pd.DataFrame(
        {
            "Open": df["open"].astype("float64").to_numpy(),
            "High": df["high"].astype("float64").to_numpy(),
            "Low": df["low"].astype("float64").to_numpy(),
            "Close": df["close"].astype("float64").to_numpy(),
            "Volume": volume,
        },
        index=pd.DatetimeIndex(idx, name="timestamp"),
    )
    out = out[~out.index.duplicated(keep="first")]
    out = out.sort_index()
    return out


def coverage_audit(df: pd.DataFrame, start: str, end: str) -> dict:
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    weekday_mask = df.index.dayofweek < 5
    df_wd = df[weekday_mask & (df.index >= start_ts) & (df.index < end_ts)]
    expected_days = pd.bdate_range(start=start_ts, end=end_ts, freq="C").size
    expected_bars = expected_days * 24 * 12
    actual_bars = len(df_wd)
    coverage = actual_bars / expected_bars if expected_bars else 0.0
    return {
        "start_utc": str(start_ts),
        "end_utc": str(end_ts),
        "expected_business_days": int(expected_days),
        "expected_bars_naive": int(expected_bars),
        "actual_bars_weekday_window": int(actual_bars),
        "actual_bars_total_post_dedup": int(len(df)),
        "coverage_ratio_naive": round(coverage, 4),
        "min_index_utc": str(df.index.min()),
        "max_index_utc": str(df.index.max()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", action="append", default=None,
                    help="CSV input directory; can be passed multiple times")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--audit", default=str(DEFAULT_AUDIT))
    ap.add_argument("--start", default="2014-01-01")
    ap.add_argument("--end", default="2026-04-30")
    ap.add_argument("--data-source", default="dukascopy")
    args = ap.parse_args()

    input_dirs = [Path(p) for p in (args.input_dir or [str(DEFAULT_INPUT)])]
    output = Path(args.output)
    audit_path = Path(args.audit)

    print(f"[load] reading CSV from {input_dirs}")
    raw = load_csv(input_dirs)
    print(f"[load] raw rows: {len(raw)}")

    df = normalize(raw)
    print(f"[normalize] post-dedup rows: {len(df)}")
    print(f"[normalize] range: {df.index.min()} → {df.index.max()}")

    audit = coverage_audit(df, args.start, args.end)
    print(f"[audit] coverage_ratio_naive={audit['coverage_ratio_naive']}")
    print(f"[audit] actual_bars_weekday_window={audit['actual_bars_weekday_window']}")

    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, engine="pyarrow", compression="snappy")
    sha = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"[write] parquet={output} sha256={sha}")

    audit.update(
        {
            "data_source": args.data_source,
            "live_separation": "bt_only",
            "output_parquet": str(output),
            "parquet_sha256": sha,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "row_count": int(len(df)),
        }
    )
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True))
    print(f"[write] audit={audit_path}")

    if audit["coverage_ratio_naive"] < 0.85:
        print(f"[WARN] coverage {audit['coverage_ratio_naive']:.3f} < 0.85 — investigate before BT", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
