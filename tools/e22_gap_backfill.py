#!/usr/bin/env python3
"""E22 VRP: OANDA v20 backfill of the MASSIVE vendor gap on EUR_USD 15m.

Per the E22 adversarial verification (2026-08-17) blocking condition 1: the
explore window contains an unrepaired vendor hole 2020-10-23..2020-11-16
(16 trading days incl. the 2020-11-03 US election week). This is the known
2020-10 MASSIVE vendor window (MEMORY project_massive_vendor_gap_backfill_2026_07_29)
surfacing on the EUR_USD 15m cache.

Inherits all guarantees from tools/massive_gap_backfill.py: pre-existing rows
never modified (asserted), (weekday,hour,minute) era pattern guard, .bak backup,
audit.json provenance record. The E22 data-freeze manifest is generated AFTER
this backfill (verification condition 1).

Usage:
  python3 tools/e22_gap_backfill.py [--cache-dir PATH] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.massive_gap_backfill import (  # noqa: E402
    ERA_DAYS, adapt_schema, audit_frame, fetch_oanda_window, _norm_index,
)

BACKFILL_DATE = "2026-08-17"
BACKUP_SUFFIX = f".bak-pre-gapfill-{BACKFILL_DATE}"
PAIR = "EUR_USD"
TF = "15m"
# end exclusive, UTC — measured hole census (E22 adversarial verification cond. 1)
WINDOWS = [
    ("2020-10-23..2020-11-16", "2020-10-23", "2020-11-17"),
]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=str(ROOT / "data" / "cache" / "massive"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        if not os.environ.get("OANDA_TOKEN"):
            # worktree fallback: main checkout .env
            load_dotenv(Path("/Users/jg-n-012/test/fx-ai-trader/.env"))
    except ImportError:
        pass
    from modules.oanda_client import OandaClient
    client = OandaClient()

    report, touched = [], 0
    p = os.path.join(args.cache_dir, f"{PAIR}_{TF}.parquet")
    df_old = pd.read_parquet(p)
    df_old = df_old.set_axis(_norm_index(df_old)).sort_index()
    idx_old = df_old.index

    added_frames, per_window_added = [], {}
    for label, ws, we in WINDOWS:
        ws_t, we_t = pd.Timestamp(ws, tz="UTC"), pd.Timestamp(we, tz="UTC")
        assert idx_old.min() <= ws_t and idx_old.max() >= we_t, (PAIR, label)
        n_had = int(((idx_old >= ws_t) & (idx_old < we_t)).sum())
        era = idx_old[((idx_old >= ws_t - pd.Timedelta(days=ERA_DAYS)) & (idx_old < ws_t))
                      | ((idx_old >= we_t) & (idx_old < we_t + pd.Timedelta(days=ERA_DAYS)))]
        if len(era) < 50:
            raise RuntimeError(f"{PAIR}: era sample too small ({len(era)}) for {label}")
        pattern = set(zip(era.dayofweek, era.hour, era.minute))
        src = fetch_oanda_window(client, PAIR, TF, ws_t, we_t)
        src = src[~src.index.isin(idx_old)]
        keep = [ts for ts in src.index
                if (ts.dayofweek, ts.hour, ts.minute) in pattern]
        src = src.loc[keep]
        if len(src):
            added_frames.append(adapt_schema(src, df_old))
        per_window_added[label] = int(len(src))
        report.append((PAIR, label, n_had, int(len(src))))

    total_added = sum(per_window_added.values())
    if total_added and not args.dry_run:
        df_new = pd.concat([df_old] + added_frames).sort_index()
        assert not df_new.index.duplicated().any(), PAIR
        assert len(df_new) == len(df_old) + total_added, PAIR
        assert df_new.loc[idx_old].equals(df_old), PAIR
        df_new.index.name = df_old.index.name

        backup = p + BACKUP_SUFFIX
        if not os.path.exists(backup):
            shutil.copy2(p, backup)
        df_new.to_parquet(p)
        touched = 1

        audit_path = Path(p).with_suffix(".audit.json")
        audit = json.loads(audit_path.read_text()) if audit_path.exists() else {
            "pair": PAIR, "tf": TF, "source": "MASSIVE"}
        audit.update(audit_frame(df_new, TF))
        audit.setdefault("backfill", []).append({
            "date": BACKFILL_DATE,
            "source": "OANDA_v20_mid (dailyAlignment=0, alignmentTimezone=UTC)",
            "windows": per_window_added,
            "rows_added_total": total_added,
            "reason": ("MASSIVE vendor-side 2020-10 gap on EUR_USD 15m "
                       "(E22 adversarial verification 2026-08-17 condition 1; "
                       "explore-window hole incl. 2020-11-03 US election week)"),
        })
        audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")

    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"[{mode}] {touched} files rewritten")
    print("%-10s %-24s %8s %8s" % ("pair", "window", "had", "added"))
    for pair, label, n, a in report:
        print("%-10s %-24s %8d %8d" % (pair, label, n, a))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
