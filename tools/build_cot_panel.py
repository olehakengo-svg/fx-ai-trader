#!/usr/bin/env python3
"""W1-F2: Build weekly CFTC COT FX panel (legacy format, futures only).

Downloads CFTC Commitments of Traders legacy 'futures only' annual files
(deacot{YYYY}.zip -> annual.txt) for 2010-2026, extracts the six major CME FX
futures (EUR, JPY, GBP, AUD, CAD, CHF), and writes a weekly panel parquet:

    data/external/cot_fx_panel.parquet
    columns: report_date, currency, noncomm_long, noncomm_short,
             noncomm_net, open_interest, net_pct_oi

Fetch + panel build ONLY. No edge analysis / IC computation (queued for
pre-registered analysis).

Usage:
    python3 tools/build_cot_panel.py [--start-year 2010] [--end-year 2026]
                                     [--force-download]
"""

import argparse
import io
import subprocess
import sys
import zipfile
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "external" / "cot_raw"
OUT_PARQUET = REPO_ROOT / "data" / "external" / "cot_fx_panel.parquet"

CFTC_URL_TMPL = "https://www.cftc.gov/files/dea/history/deacot{year}.zip"

# CFTC Contract Market Codes are stable across years (market *names* are not,
# e.g. "BRITISH POUND STERLING" -> "BRITISH POUND").
CONTRACT_CODE_TO_CCY = {
    "099741": "EUR",  # EURO FX - CME
    "097741": "JPY",  # JAPANESE YEN - CME
    "096742": "GBP",  # BRITISH POUND (STERLING) - CME
    "232741": "AUD",  # AUSTRALIAN DOLLAR - CME
    "090741": "CAD",  # CANADIAN DOLLAR - CME
    "092741": "CHF",  # SWISS FRANC - CME
}

# Sanity substrings the market name must contain for each currency.
CCY_NAME_SUBSTR = {
    "EUR": "EURO FX",
    "JPY": "JAPANESE YEN",
    "GBP": "BRITISH POUND",
    "AUD": "AUSTRALIAN DOLLAR",
    "CAD": "CANADIAN DOLLAR",
    "CHF": "SWISS FRANC",
}

COL_MARKET = "Market and Exchange Names"
COL_DATE = "As of Date in Form YYYY-MM-DD"
COL_CODE = "CFTC Contract Market Code"
COL_OI = "Open Interest (All)"
COL_NC_LONG = "Noncommercial Positions-Long (All)"
COL_NC_SHORT = "Noncommercial Positions-Short (All)"
# Commercial side (wave-3 W3-1 carve-out family; exact legacy names asserted).
COL_C_LONG = "Commercial Positions-Long (All)"
COL_C_SHORT = "Commercial Positions-Short (All)"


def download_year(year: int, force: bool = False) -> Path:
    """Download one annual zip via curl. Returns local path. Raises on failure."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest = RAW_DIR / f"deacot{year}.zip"
    if dest.exists() and dest.stat().st_size > 10_000 and not force:
        print(f"  [skip] {dest.name} already present ({dest.stat().st_size:,} bytes)")
        return dest
    url = CFTC_URL_TMPL.format(year=year)
    print(f"  [get ] {url}")
    result = subprocess.run(
        ["curl", "-sS", "-L", "--fail", "--max-time", "180",
         "-o", str(dest), url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"curl failed for {url} (rc={result.returncode}): {result.stderr.strip()}"
        )
    if not dest.exists() or dest.stat().st_size < 10_000:
        raise RuntimeError(f"download of {url} produced missing/tiny file: {dest}")
    return dest


def parse_year_zip(zip_path: Path) -> pd.DataFrame:
    """Parse one deacot zip -> filtered FX rows (raw legacy columns subset)."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        txt_names = [n for n in names if n.lower().endswith(".txt")]
        if len(txt_names) != 1:
            raise RuntimeError(f"{zip_path.name}: expected 1 .txt member, got {names}")
        raw = zf.read(txt_names[0])

    df = pd.read_csv(
        io.BytesIO(raw),
        dtype={COL_CODE: str},
        low_memory=False,
        skipinitialspace=True,
    )
    df.columns = [c.strip() for c in df.columns]

    required = [COL_MARKET, COL_DATE, COL_CODE, COL_OI, COL_NC_LONG, COL_NC_SHORT,
                COL_C_LONG, COL_C_SHORT]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"{zip_path.name}: missing columns {missing}")

    df[COL_CODE] = df[COL_CODE].astype(str).str.strip()
    fx = df[df[COL_CODE].isin(CONTRACT_CODE_TO_CCY)].copy()
    if fx.empty:
        raise RuntimeError(f"{zip_path.name}: 0 FX rows matched contract codes "
                           f"{sorted(CONTRACT_CODE_TO_CCY)} — format change?")

    fx["currency"] = fx[COL_CODE].map(CONTRACT_CODE_TO_CCY)

    # Name sanity check: contract code must map to expected market name.
    for ccy, substr in CCY_NAME_SUBSTR.items():
        sub = fx[fx["currency"] == ccy]
        if sub.empty:
            continue
        bad = sub[~sub[COL_MARKET].str.upper().str.contains(substr, regex=False)]
        if not bad.empty:
            raise RuntimeError(
                f"{zip_path.name}: contract code for {ccy} matched unexpected "
                f"market name(s): {bad[COL_MARKET].unique()[:3]}"
            )

    out = pd.DataFrame({
        "report_date": pd.to_datetime(fx[COL_DATE], format="%Y-%m-%d"),
        "currency": fx["currency"],
        "noncomm_long": pd.to_numeric(fx[COL_NC_LONG]).astype("int64"),
        "noncomm_short": pd.to_numeric(fx[COL_NC_SHORT]).astype("int64"),
        "comm_long": pd.to_numeric(fx[COL_C_LONG]).astype("int64"),
        "comm_short": pd.to_numeric(fx[COL_C_SHORT]).astype("int64"),
        "open_interest": pd.to_numeric(fx[COL_OI]).astype("int64"),
    })
    return out


def build_panel(start_year: int, end_year: int, force_download: bool) -> pd.DataFrame:
    frames = []
    failed_years = []
    for year in range(start_year, end_year + 1):
        try:
            zip_path = download_year(year, force=force_download)
            part = parse_year_zip(zip_path)
            print(f"  [ok  ] {year}: {len(part)} FX rows, "
                  f"{part['report_date'].min().date()} .. {part['report_date'].max().date()}")
            frames.append(part)
        except Exception as exc:
            # Current year may not exist yet early in Jan; count explicitly.
            print(f"  [FAIL] {year}: {exc}", file=sys.stderr)
            failed_years.append(year)

    if not frames:
        raise RuntimeError("no years parsed successfully — aborting")
    # Only the (possibly not-yet-published) end year is allowed to fail.
    hard_fail = [y for y in failed_years if y < end_year]
    if hard_fail:
        raise RuntimeError(f"required years failed: {hard_fail}")

    panel = pd.concat(frames, ignore_index=True)

    dup_n = panel.duplicated(subset=["report_date", "currency"]).sum()
    if dup_n:
        print(f"  [warn] {dup_n} duplicate (report_date, currency) rows dropped")
        panel = panel.drop_duplicates(subset=["report_date", "currency"], keep="last")

    panel["noncomm_net"] = panel["noncomm_long"] - panel["noncomm_short"]
    panel["comm_net"] = panel["comm_long"] - panel["comm_short"]
    zero_oi = int((panel["open_interest"] <= 0).sum())
    if zero_oi:
        print(f"  [warn] {zero_oi} rows with open_interest <= 0 (net_pct_oi -> NaN)")
    oi = panel["open_interest"].where(panel["open_interest"] > 0)
    panel["net_pct_oi"] = 100.0 * panel["noncomm_net"] / oi
    panel["comm_net_pct_oi"] = 100.0 * panel["comm_net"] / oi

    panel = panel[[
        "report_date", "currency", "noncomm_long", "noncomm_short",
        "noncomm_net", "comm_long", "comm_short", "comm_net",
        "open_interest", "net_pct_oi", "comm_net_pct_oi",
    ]].sort_values(["currency", "report_date"]).reset_index(drop=True)
    return panel


def validate(panel: pd.DataFrame) -> None:
    print("\n=== VALIDATION ===")
    print(f"rows total          : {len(panel)}")
    print(f"date span           : {panel['report_date'].min().date()} .. "
          f"{panel['report_date'].max().date()}")
    print("\nweeks per currency:")
    per_ccy = panel.groupby("currency").agg(
        n_weeks=("report_date", "nunique"),
        first=("report_date", "min"),
        last=("report_date", "max"),
        net_min=("noncomm_net", "min"),
        net_max=("noncomm_net", "max"),
    )
    print(per_ccy.to_string())

    nan_pct = int(panel["net_pct_oi"].isna().sum())
    print(f"\nnet_pct_oi NaN rows : {nan_pct}")

    # Spot-check: JPY record net short area (2024-04). Expect strongly negative
    # noncomm_net (~ -170k contracts) and strongly negative net_pct_oi.
    jpy_apr24 = panel[
        (panel["currency"] == "JPY")
        & (panel["report_date"] >= "2024-04-01")
        & (panel["report_date"] <= "2024-05-01")
    ]
    print("\nspot-check JPY 2024-04 (expect strongly negative net / net_pct_oi):")
    if jpy_apr24.empty:
        raise RuntimeError("spot-check FAILED: no JPY rows in 2024-04 window")
    print(jpy_apr24.to_string(index=False))
    worst = jpy_apr24["net_pct_oi"].min()
    if worst > -30.0:
        raise RuntimeError(
            f"spot-check FAILED: JPY 2024-04 min net_pct_oi = {worst:.1f} "
            "(expected strongly negative, < -30)"
        )
    print(f"spot-check PASS: JPY 2024-04 min net_pct_oi = {worst:.1f}%, "
          f"min noncomm_net = {jpy_apr24['noncomm_net'].min():,}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--force-download", action="store_true",
                        help="re-download zips even if cached locally")
    args = parser.parse_args()

    print(f"Building COT FX panel {args.start_year}-{args.end_year}")
    print(f"raw dir : {RAW_DIR}")
    print(f"output  : {OUT_PARQUET}")

    panel = build_panel(args.start_year, args.end_year, args.force_download)
    validate(panel)

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT_PARQUET, index=False)
    print(f"\nwrote {OUT_PARQUET} ({OUT_PARQUET.stat().st_size:,} bytes, "
          f"{len(panel)} rows)")


if __name__ == "__main__":
    main()
