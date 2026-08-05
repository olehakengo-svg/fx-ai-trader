#!/usr/bin/env python3
"""#21 cc-mr: OANDA v20 backfill of MASSIVE vendor gaps on the 3 commodity crosses (1h).

Extends the 2026-07-29 repair (tools/massive_gap_backfill.py) per the wave-6 #21
adversarial verification (2026-08-05) §6.2-1 / condition 2: the known 2020 vendor
window must run through 2021-01-03 to cover the measured holes
(AUD_NZD 1225h 2020-11-13..2021-01-03 / NZD_CAD 1730h 2020-10-23..2021-01-03 and
286h 2019-09-24..2019-10-06). Scope is deliberately limited to the three cross
1h parquets — other caches keep their 07-29 state (E15/E7 frozen ledgers etc.).

Inherits all guarantees from massive_gap_backfill: pre-existing rows never
modified (asserted), (weekday,hour,minute) era pattern guard, .bak backup,
audit.json provenance record.

Usage:
  python3 tools/cc_mr_gap_backfill.py [--cache-dir PATH] [--dry-run]
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

BACKFILL_DATE = "2026-08-05"
BACKUP_SUFFIX = f".bak-pre-gapfill-{BACKFILL_DATE}"
PAIRS = ("AUD_NZD", "AUD_CAD", "NZD_CAD")
TF = "1h"
# (label, start, end) — end exclusive, UTC. Window 2 extended vs 07-29 per
# measured hole census (adversarial verification §1.2-4).
WINDOWS = [
    ("2019-09-14..2019-10-06", "2019-09-14", "2019-10-07"),
    ("2020-10-13..2021-01-03", "2020-10-13", "2021-01-04"),
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
            load_dotenv(Path(args.cache_dir).resolve().parents[2] / ".env")
    except ImportError:
        pass
    from modules.oanda_client import OandaClient
    client = OandaClient()

    report, touched = [], 0
    for pair in PAIRS:
        p = os.path.join(args.cache_dir, f"{pair}_{TF}.parquet")
        df_old = pd.read_parquet(p)
        df_old = df_old.set_axis(_norm_index(df_old)).sort_index()
        idx_old = df_old.index

        added_frames, per_window_added = [], {}
        for label, ws, we in WINDOWS:
            ws_t, we_t = pd.Timestamp(ws, tz="UTC"), pd.Timestamp(we, tz="UTC")
            assert idx_old.min() <= ws_t and idx_old.max() >= we_t, (pair, label)
            n_had = int(((idx_old >= ws_t) & (idx_old < we_t)).sum())
            era = idx_old[((idx_old >= ws_t - pd.Timedelta(days=ERA_DAYS)) & (idx_old < ws_t))
                          | ((idx_old >= we_t) & (idx_old < we_t + pd.Timedelta(days=ERA_DAYS)))]
            if len(era) < 50:
                raise RuntimeError(f"{pair}: era sample too small ({len(era)}) for {label}")
            pattern = set(zip(era.dayofweek, era.hour, era.minute))
            src = fetch_oanda_window(client, pair, TF, ws_t, we_t)
            src = src[~src.index.isin(idx_old)]
            keep = [ts for ts in src.index
                    if (ts.dayofweek, ts.hour, ts.minute) in pattern]
            src = src.loc[keep]
            if len(src):
                added_frames.append(adapt_schema(src, df_old))
            per_window_added[label] = int(len(src))
            report.append((pair, label, n_had, int(len(src))))

        total_added = sum(per_window_added.values())
        if total_added == 0 or args.dry_run:
            continue

        df_new = pd.concat([df_old] + added_frames).sort_index()
        assert not df_new.index.duplicated().any(), pair
        assert len(df_new) == len(df_old) + total_added, pair
        assert df_new.loc[idx_old].equals(df_old), pair
        df_new.index.name = df_old.index.name

        backup = p + BACKUP_SUFFIX
        if not os.path.exists(backup):
            shutil.copy2(p, backup)
        df_new.to_parquet(p)
        touched += 1

        audit_path = Path(p).with_suffix(".audit.json")
        audit = json.loads(audit_path.read_text()) if audit_path.exists() else {
            "pair": pair, "tf": TF, "source": "MASSIVE"}
        audit.update(audit_frame(df_new, TF))
        audit.setdefault("backfill", []).append({
            "date": BACKFILL_DATE,
            "source": "OANDA_v20_mid (dailyAlignment=0, alignmentTimezone=UTC)",
            "windows": per_window_added,
            "rows_added_total": total_added,
            "reason": ("MASSIVE vendor-side historical gap on commodity crosses "
                       "(measured census, wave-6 #21 adversarial verification "
                       "2026-08-05 §1.2-4); extends the 2026-07-29 repair windows."),
        })
        audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")

    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"[{mode}] {len(report)} pair-windows examined, {touched} files rewritten")
    print("%-10s %-24s %8s %8s" % ("pair", "window", "had", "added"))
    for pair, label, n, a in report:
        print("%-10s %-24s %8d %8d" % (pair, label, n, a))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
