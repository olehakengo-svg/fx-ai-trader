#!/usr/bin/env python3
"""Save a dated tier-master.json snapshot for /strategies diffs.

Usage:
  python3 scripts/save_tier_master_snapshot.py
  python3 scripts/save_tier_master_snapshot.py --date 2026-05-11
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TIER_MASTER_PATH = REPO_ROOT / "knowledge-base" / "wiki" / "tier-master.json"
SNAPSHOT_DIR = REPO_ROOT / "knowledge-base" / "wiki" / "snapshots"


def save_snapshot(snapshot_date: str | None = None) -> Path:
    taken_at = datetime.now(timezone.utc)
    date_str = snapshot_date or taken_at.date().isoformat()
    source = json.loads(TIER_MASTER_PATH.read_text(encoding="utf-8"))
    source["_snapshot_taken_at"] = taken_at.isoformat(timespec="seconds")

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SNAPSHOT_DIR / f"tier-master-{date_str}.json"
    out_path.write_text(
        json.dumps(source, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save tier-master daily snapshot")
    parser.add_argument("--date", help="Snapshot date override, YYYY-MM-DD")
    args = parser.parse_args(argv)
    out_path = save_snapshot(snapshot_date=args.date)
    print(f"[tier-master-snapshot] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
