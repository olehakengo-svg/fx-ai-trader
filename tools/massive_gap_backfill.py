#!/usr/bin/env python3
"""Backfill MASSIVE parquet caches over vendor-side historical gaps via OANDA v20.

Background (2026-07-29, rule:R3 data-pipeline repair):
  The MASSIVE aggregates source itself is missing FX bars in two windows —
  2019-09-14..2019-10-05 and 2020-10-13..2020-11-14 — with pair-dependent
  severity (USD_JPY: 100% of both windows; USD_CAD/USD_CHF: 100% of the 2020
  window; EUR*/GBP*/NZD*: partial). Local caches mirror the vendor exactly
  (probe-verified day-by-day), so a MASSIVE refetch cannot fill these holes.
  This tool fills only the missing in-window bars from OANDA v20 mid candles
  fetched with dailyAlignment=0 / alignmentTimezone=UTC so H4/D bar
  boundaries match MASSIVE's UTC-aligned aggregates.

Guarantees:
  - Only timestamps inside the two windows are ever added.
  - Pre-existing rows are never modified (asserted before write).
  - Added bars must match the file's own (weekday, hour, minute) coverage
    pattern, so session-boundary conventions (Sunday open etc.) are kept.
  - Every modified parquet gets a .bak-pre-gapfill-2026-07-29 backup and a
    refreshed .audit.json carrying an explicit "backfill" provenance record.

Usage:
  python3 tools/massive_gap_backfill.py --dry-run
  python3 tools/massive_gap_backfill.py [--cache-dir PATH]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BACKFILL_DATE = "2026-07-29"
BACKUP_SUFFIX = f".bak-pre-gapfill-{BACKFILL_DATE}"

# (label, start, end) — end exclusive, UTC.
WINDOWS = [
    ("2019-09-14..2019-10-05", "2019-09-14", "2019-10-06"),
    ("2020-10-13..2020-11-14", "2020-10-13", "2020-11-15"),
]

TF_MINUTES = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
TF_TO_OANDA = {"5m": "M5", "15m": "M15", "1h": "H1", "4h": "H4", "1d": "D"}
# Session conventions (Sunday-open bars etc.) drift over the years, so the
# (weekday, hour, minute) guard is built from bars near each window, not from
# the whole file. Peer-file row counts are NOT used as a completeness
# reference: when every file of a TF shares the vendor hole (5m × 2020), the
# peer maximum is itself a gap value.
ERA_DAYS = 90

_FNAME_RE = re.compile(r"^([A-Z]{3}_[A-Z]{3})_(5m|15m|1h|4h|1d)(?:_|\.)")
# Plain {PAIR}_15m.parquet files are pinned by the E15/E7 pre-reg data ledger
# (tools/event_modality_oos_verdict.py load_and_verify_bars asserts
# rows_at_ledger_last == frozen ledger rows; any pre-snapshot insertion breaks
# phase-1 verification, verdict 2026-08-28). Their deep history has no other
# consumer — BTDataCache.get() slices to <=365d — so they are excluded here.
_EXCLUDE_RE = re.compile(r"^[A-Z]{3}_[A-Z]{3}_15m\.parquet$")


def _norm_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.DatetimeIndex(pd.to_datetime(idx, utc=True))
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")


def audit_frame(df: pd.DataFrame, tf: str) -> dict:
    """Same semantics as tools/fetch_massive_data.audit_frame, plus 15m."""
    idx = _norm_index(df).sort_values()
    minutes = TF_MINUTES.get(tf)
    if len(idx) == 0 or minutes is None:
        return {"rows": int(len(idx)), "start": None, "end": None,
                "gap_count": 0, "completeness_pct": 0.0,
                "completeness_pct_naive": 0.0, "trading_days": 0}
    deltas = idx.to_series().diff().dropna()
    expected = pd.Timedelta(minutes=minutes)
    intra_week_gaps = int(((deltas > expected * 1.5) & (deltas < pd.Timedelta(days=3))).sum())
    span_minutes = (idx[-1] - idx[0]).total_seconds() / 60
    expected_rows_naive = max(1, int(span_minutes / minutes) + 1)
    trading_days = int(len(pd.bdate_range(idx[0].normalize(), idx[-1].normalize())))
    expected_rows_tw = max(1, int(trading_days * (24 * 60 / minutes)))
    return {
        "rows": int(len(idx)),
        "start": idx[0].isoformat(),
        "end": idx[-1].isoformat(),
        "gap_count": intra_week_gaps,
        "completeness_pct": round(min(100.0, 100.0 * len(idx) / expected_rows_tw), 4),
        "completeness_pct_naive": round(min(100.0, 100.0 * len(idx) / expected_rows_naive), 4),
        "trading_days": trading_days,
    }


def fetch_oanda_window(client, pair: str, tf: str,
                       ws: pd.Timestamp, we: pd.Timestamp) -> pd.DataFrame:
    """Fetch complete OANDA mid candles for [ws, we) with UTC bar alignment."""
    gran = TF_TO_OANDA[tf]
    # Slice so each request stays under OANDA's 5000-candle cap.
    slice_days = {"5m": 15, "15m": 45, "1h": 180, "4h": 500, "1d": 500}[tf]
    out_rows, out_idx = [], []
    cursor = ws
    while cursor < we:
        sl_end = min(cursor + pd.Timedelta(days=slice_days), we)
        path = (
            f"/v3/instruments/{pair}/candles?granularity={gran}&price=M"
            f"&from={cursor.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            f"&to={sl_end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            f"&dailyAlignment=0&alignmentTimezone=UTC"
        )
        ok, resp = False, {}
        for attempt in range(5):
            ok, resp = client._request("GET", path, timeout=30)
            if ok:
                break
            time.sleep(6)  # covers the client's 5s 429 backoff
        if not ok:
            raise RuntimeError(f"OANDA candles failed for {pair} {gran}: {resp}")
        for c in resp.get("candles", []):
            if not c.get("complete"):
                continue
            mid = c["mid"]
            out_idx.append(pd.Timestamp(c["time"], tz="UTC"))
            out_rows.append({
                "o": float(mid["o"]), "h": float(mid["h"]),
                "l": float(mid["l"]), "c": float(mid["c"]),
                "volume": float(c.get("volume", 0)),
            })
        cursor = sl_end
        time.sleep(0.3)
    if not out_rows:
        return pd.DataFrame(columns=["o", "h", "l", "c", "volume"])
    df = pd.DataFrame(out_rows, index=pd.DatetimeIndex(out_idx))
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df[(df.index >= ws) & (df.index < we)]


def adapt_schema(src: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    """Map OANDA o/h/l/c/volume rows onto the target parquet's column schema."""
    cap = {"Open": src["o"], "High": src["h"], "Low": src["l"],
           "Close": src["c"], "Volume": src["volume"], "vwap": src["c"]}
    low = {"open": src["o"], "high": src["h"], "low": src["l"],
           "close": src["c"], "volume": src["volume"], "vwap": src["c"],
           "n_transactions": src["volume"]}
    known = {**cap, **low}
    missing = [c for c in target.columns if c not in known]
    if missing:
        raise RuntimeError(f"Unknown target columns {missing}; refusing to guess")
    out = pd.DataFrame({c: known[c] for c in target.columns}, index=src.index)
    # Match target dtypes so concat doesn't upcast pre-existing columns
    # (e.g. int64 n_transactions), which would break the no-modify assert.
    return out.astype(target.dtypes.to_dict())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=str(ROOT / "data" / "cache" / "massive"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        if not os.environ.get("OANDA_TOKEN"):
            # Worktrees have no .env; fall back to the .env of the repo that
            # owns --cache-dir (<repo>/data/cache/massive → <repo>/.env).
            load_dotenv(Path(args.cache_dir).resolve().parents[2] / ".env")
    except ImportError:
        pass
    from modules.oanda_client import OandaClient
    client = OandaClient()

    files = []
    for p in sorted(glob.glob(os.path.join(args.cache_dir, "*.parquet"))):
        name = os.path.basename(p)
        if ".bak" in name or ".partial" in name or _EXCLUDE_RE.match(name):
            continue
        m = _FNAME_RE.match(name)
        if not m:
            continue
        files.append((p, name, m.group(1), m.group(2)))

    oanda_cache: dict = {}
    report, touched = [], 0
    for p, name, pair, tf in files:
        df_old = pd.read_parquet(p)
        idx_old = _norm_index(df_old)
        df_old = df_old.set_axis(idx_old).sort_index()
        idx_old = df_old.index

        spanned = []
        for label, ws, we in WINDOWS:
            ws_t, we_t = pd.Timestamp(ws, tz="UTC"), pd.Timestamp(we, tz="UTC")
            if len(idx_old) and idx_old.min() <= ws_t and idx_old.max() >= we_t:
                spanned.append((label, ws_t, we_t))
        if not spanned:
            continue

        added_frames, per_window_added = [], {}
        for label, ws_t, we_t in spanned:
            n_had = int(((idx_old >= ws_t) & (idx_old < we_t)).sum())
            era = idx_old[((idx_old >= ws_t - pd.Timedelta(days=ERA_DAYS)) & (idx_old < ws_t))
                          | ((idx_old >= we_t) & (idx_old < we_t + pd.Timedelta(days=ERA_DAYS)))]
            pattern = set(zip(era.dayofweek, era.hour, era.minute))
            if len(era) < 50:
                raise RuntimeError(f"{name}: era sample too small ({len(era)}) for {label}")
            key = (pair, tf, label)
            if key not in oanda_cache:
                oanda_cache[key] = fetch_oanda_window(client, pair, tf, ws_t, we_t)
            src = oanda_cache[key]
            src = src[~src.index.isin(idx_old)]
            keep = [ts for ts in src.index
                    if (ts.dayofweek, ts.hour, ts.minute) in pattern]
            src = src.loc[keep]
            if len(src):
                added_frames.append(adapt_schema(src, df_old))
            per_window_added[label] = int(len(src))
            report.append((name, label, n_had, int(len(src))))

        total_added = sum(per_window_added.values())
        if total_added == 0 or args.dry_run:
            continue

        df_new = pd.concat([df_old] + added_frames).sort_index()
        assert not df_new.index.duplicated().any(), name
        assert len(df_new) == len(df_old) + total_added, name
        # Pre-existing rows must be byte-identical after the merge.
        assert df_new.loc[idx_old].equals(df_old), name
        df_new.index.name = df_old.index.name

        backup = p + BACKUP_SUFFIX
        if not os.path.exists(backup):
            shutil.copy2(p, backup)
        df_new.to_parquet(p)
        touched += 1

        audit_path = Path(p).with_suffix(".audit.json")
        audit = json.loads(audit_path.read_text()) if audit_path.exists() else {
            "pair": pair, "tf": tf, "source": "MASSIVE"}
        audit.update(audit_frame(df_new, tf))
        audit.setdefault("backfill", []).append({
            "date": BACKFILL_DATE,
            "source": "OANDA_v20_mid (dailyAlignment=0, alignmentTimezone=UTC)",
            "windows": per_window_added,
            "rows_added_total": total_added,
            "reason": ("MASSIVE vendor-side historical gap (probe-confirmed; "
                       "refetch cannot fill). See knowledge-base/wiki/analyses/"
                       "massive-vendor-gap-backfill-2026-07-29.md"),
        })
        audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")

    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"[{mode}] {len(report)} file-windows examined, {touched} files rewritten")
    print("%-42s %-24s %8s %8s" % ("file", "window", "had", "added"))
    for name, label, n, a in report:
        print("%-42s %-24s %8d %8d" % (name, label, n, a))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
