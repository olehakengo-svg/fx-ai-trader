#!/usr/bin/env python3
"""Auto-recovery of FORCE_DEMOTED strategies that re-establish a Bonferroni-significant
Shadow edge (daily cron, 2026-04-27).

Background (obs 255 / 267):
  `force_demoted` in `knowledge-base/wiki/tier-master.json` is a manual override that
  short-circuits `_evaluate_promotions`. There is currently no automatic path back —
  if a Shadow strategy genuinely re-acquires edge after the manual block, OANDA-side
  trading stays disabled indefinitely.

Recovery gate (matches `tools/cell_edge_audit.py` v2 promotion gate, with stricter N):
  N >= 30
  AND Wilson_BF lower bound > 0.50   (Z = 3.29, ≈ 99.9% one-sided, Bonferroni-safe)
  AND Bonferroni p < 0.05            (raw two-sided binomial p × N_force_demoted)

Side effects:
  - Atomic rewrite of tier-master.json (timestamped .bak written first).
  - One row per recovery in `algo_change_log` via `DemoDB.save_algo_change`,
    change_type = "auto_recovery_from_force_demoted".

Usage:
  python3 tools/auto_force_demoted_recovery.py [--db demo_trades.db] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Project root on sys.path
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from modules.demo_db import DemoDB  # noqa: E402
from tools.cell_edge_audit import (  # noqa: E402
    binomial_two_sided_pvalue,
    wilson_lower,
)


# ─── Configuration ──────────────────────────────────────────────────────
MIN_N: int = 30
WILSON_BF_Z: float = 3.29  # Bonferroni-corrected one-sided ~99.9%
WILSON_BF_LOWER_THRESHOLD: float = 0.50
BONFERRONI_ALPHA: float = 0.05

DEFAULT_TIER_MASTER = (
    _HERE.parent / "knowledge-base" / "wiki" / "tier-master.json"
)
DEFAULT_DB_PATH = _HERE.parent / "demo_trades.db"


# ─── Shadow aggregation (Sentinel-only, XAU + seed excluded) ────────────
def fetch_shadow_aggregate(db: DemoDB, entry_type: str) -> dict:
    """Aggregate Shadow (`is_shadow=1`) closed trades for one entry_type.

    Filter parity with `DemoDB.get_shadow_trades_for_evaluation` (XAU exclusion +
    seed exclusion). We re-issue the SQL ourselves to obtain an exact `wins` count
    for the Wilson / binomial calculation; the helper rounds WR to one decimal,
    which can flip outcomes at recovery-gate boundaries.
    """
    from modules.demo_db import _SEED_EXCLUSION_SQL  # noqa: E402

    query = (
        "SELECT outcome, pnl_pips FROM demo_trades "
        "WHERE status='CLOSED' AND is_shadow = 1 "
        "AND (instrument IS NULL OR instrument NOT LIKE '%XAU%') "
        f"AND {_SEED_EXCLUSION_SQL} "
        "AND entry_type = ?"
    )
    with db._safe_conn() as conn:
        rows = conn.execute(query, (entry_type,)).fetchall()
    n = len(rows)
    wins = sum(1 for r in rows if r["outcome"] == "WIN")
    pnl_sum = sum((r["pnl_pips"] or 0.0) for r in rows)
    ev = (pnl_sum / n) if n else 0.0
    return {"n": n, "wins": wins, "ev_pip": ev}


def evaluate_recovery(
    n: int, wins: int, n_tests: int
) -> dict:
    """Apply the recovery gate and return the full stats record."""
    wr = (wins / n) if n else 0.0
    wl_bf = wilson_lower(wins, n, z=WILSON_BF_Z) if n else 0.0
    p_raw = binomial_two_sided_pvalue(wins, n, p0=0.5) if n else 1.0
    p_bonf = min(1.0, p_raw * max(1, n_tests))
    qualifies = (
        n >= MIN_N
        and wl_bf > WILSON_BF_LOWER_THRESHOLD
        and p_bonf < BONFERRONI_ALPHA
    )
    return {
        "n": n,
        "wins": wins,
        "wr": round(wr, 4),
        "wilson_bf_lower": round(wl_bf, 4),
        "p_value_raw": round(p_raw, 5),
        "p_value_bonferroni": round(p_bonf, 5),
        "qualifies": qualifies,
    }


# ─── tier-master.json I/O ───────────────────────────────────────────────
def load_tier_master(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_tier_master(path: Path, data: dict) -> Path:
    """Write `data` to `path` atomically, after dropping a timestamped backup.

    Returns the backup path. Atomicity uses tempfile + os.replace within the same
    directory so the rename is on the same filesystem.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_suffix(path.suffix + f".bak.{ts}")
    shutil.copy2(path, backup)

    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return backup


# ─── Orchestration ──────────────────────────────────────────────────────
def run_recovery(
    db: DemoDB,
    tier_master_path: Path,
    dry_run: bool = False,
) -> dict:
    """Compute the recovery decision and (unless dry_run) persist it.

    Returns a dict suitable for printing / JSON dumping.
    """
    tm = load_tier_master(tier_master_path)
    force_demoted = list(tm.get("force_demoted", []))
    n_tests = len(force_demoted)

    evaluations: list[dict] = []
    recovered: list[str] = []
    for strat in force_demoted:
        agg = fetch_shadow_aggregate(db, strat)
        stat = evaluate_recovery(agg["n"], agg["wins"], n_tests)
        rec = {
            "strategy": strat,
            "ev_pip": round(agg["ev_pip"], 3),
            **stat,
        }
        evaluations.append(rec)
        if stat["qualifies"]:
            recovered.append(strat)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier_master_path": str(tier_master_path),
        "n_force_demoted_in": len(force_demoted),
        "n_tests_for_bonferroni": n_tests,
        "min_n": MIN_N,
        "wilson_bf_z": WILSON_BF_Z,
        "wilson_bf_lower_threshold": WILSON_BF_LOWER_THRESHOLD,
        "bonferroni_alpha": BONFERRONI_ALPHA,
        "evaluations": evaluations,
        "recovered": recovered,
        "dry_run": dry_run,
    }

    if not recovered or dry_run:
        summary["wrote_tier_master"] = False
        summary["backup"] = None
        return summary

    new_force_demoted = [s for s in force_demoted if s not in set(recovered)]
    new_tm = dict(tm)
    new_tm["force_demoted"] = new_force_demoted
    new_tm["generated_at"] = summary["generated_at"]

    backup = atomic_write_tier_master(tier_master_path, new_tm)
    summary["wrote_tier_master"] = True
    summary["backup"] = str(backup)

    db.save_algo_change(
        change_type="auto_recovery_from_force_demoted",
        description=(
            f"Auto-recovered {len(recovered)} strateg"
            f"{'y' if len(recovered) == 1 else 'ies'} from force_demoted "
            f"(N>={MIN_N}, Wilson_BF lower>{WILSON_BF_LOWER_THRESHOLD}, "
            f"Bonferroni p<{BONFERRONI_ALPHA}): "
            + ", ".join(recovered)
        ),
        params_before={"force_demoted": force_demoted},
        params_after={
            "force_demoted": new_force_demoted,
            "recovered": recovered,
            "evaluations": [
                e for e in evaluations if e["strategy"] in set(recovered)
            ],
        },
        triggered_by="auto_force_demoted_recovery_cron",
    )
    return summary


# ─── CLI ────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-recover FORCE_DEMOTED strategies with Bonferroni-significant Shadow edge."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument(
        "--tier-master",
        default=str(DEFAULT_TIER_MASTER),
        help="Path to tier-master.json",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute and print, but do not write tier-master.json or algo_change_log.")
    parser.add_argument("--json", action="store_true",
                        help="Emit the summary as JSON to stdout.")
    args = parser.parse_args()

    db = DemoDB(db_path=args.db)
    summary = run_recovery(
        db=db,
        tier_master_path=Path(args.tier_master),
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        recovered = summary["recovered"]
        print(
            f"[auto_force_demoted_recovery] checked {summary['n_force_demoted_in']} "
            f"force_demoted strateg{'y' if summary['n_force_demoted_in'] == 1 else 'ies'} "
            f"(N≥{MIN_N}, Z_BF={WILSON_BF_Z}, α_BF={BONFERRONI_ALPHA})"
        )
        for r in summary["evaluations"]:
            mark = "✓" if r["qualifies"] else "·"
            print(
                f"  {mark} {r['strategy']:<28} "
                f"N={r['n']:>4} W={r['wins']:>3} WR={r['wr']:.1%} "
                f"Wilson_BF≥{r['wilson_bf_lower']:.3f} "
                f"p_bonf={r['p_value_bonferroni']:.4f} "
                f"EV={r['ev_pip']:+.2f}p"
            )
        if recovered:
            tag = "DRY-RUN — would recover" if args.dry_run else "Recovered"
            print(f"[auto_force_demoted_recovery] {tag}: {', '.join(recovered)}")
            if summary.get("backup"):
                print(f"[auto_force_demoted_recovery] backup: {summary['backup']}")
        else:
            print("[auto_force_demoted_recovery] No strategies met the recovery gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
