#!/usr/bin/env python3
"""
Backfill mtf_regime / mtf_d1_label / mtf_h4_label / mtf_vol_state
═════════════════════════════════════════════════════════════════

v9.3 Phase D (2026-04-17) で demo_trades に MTF regime 列を追加したが,
shadow_monitor が書き込むのは 2026-04-20 以降の新規 trade のみ.
過去 trade (N ≈ 1969) には空文字が入ったまま.

本スクリプトは OANDA D1/H4/H1 ローソクを独立 source として retrospective に
ラベルし, **as-of backward merge (look-ahead なし)** で各 trade の entry_time
に該当する regime を復元する. Live labeler (demo_trader._get_mtf_regime) との
同等性は 2026-04-21 の self-reconciliation check (N=193, 100% 一致) で確認済.

Usage:
    # dry-run (デフォルト): 件数集計のみ, SQL 書き込みなし
    python3 scripts/backfill_mtf_regime.py --trades-json /tmp/trades_all.json

    # SQL UPDATE file を生成 (本番 DB 書き込みは Render Shell で別途適用)
    python3 scripts/backfill_mtf_regime.py --trades-json /tmp/trades_all.json \\
        --write sql --output /tmp/backfill_mtf_regime.sql

Design:
    - idempotent: 既に mtf_regime が populated な行は skip
    - look-ahead なし: mtf_regime_engine.label_mtf() の shift(1) + backward merge_asof
    - XAU exclude: feedback_exclude_xau に従い XAU_USD は対象外
    - 事前宣言: knowledge-base/wiki/analyses/regime-strategy-2d-2026-04-20.md §12

Output schema (SQL mode):
    BEGIN TRANSACTION;
    UPDATE demo_trades SET mtf_regime='range_tight', mtf_d1_label=0,
                           mtf_h4_label=-1, mtf_vol_state='squeeze'
        WHERE id = 123 AND (mtf_regime IS NULL OR mtf_regime = '');
    ...
    COMMIT;

Validation (本番適用後):
    - tests/test_strategy_family_map.py
    - tools/tier_integrity_check.py
    - tools/strategies_drift_check.py
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def load_trades(trades_json: str) -> List[dict]:
    """Load /api/demo/trades snapshot. Excludes XAU (feedback_exclude_xau)."""
    with open(trades_json) as f:
        data = json.load(f)
    trades = data["trades"] if isinstance(data, dict) and "trades" in data else data
    return [
        t for t in trades
        if "XAU" not in (t.get("instrument") or "")
    ]


def label_all(trades: List[dict]) -> Tuple[List[dict], Dict[str, int]]:
    """Run label_mtf() per instrument and as-of merge to each trade's entry_time.

    Returns:
        (labeled_trades, counts)
            labeled_trades: rows with new keys {new_regime, new_d1, new_h4, new_vol}
            counts: {input, skipped_already_labeled, labeled, errors}
    """
    import pandas as pd
    from research.edge_discovery.mtf_regime_engine import (
        MTFConfig, label_mtf, fetch_mtf_data,
    )
    from modules.oanda_client import OandaClient

    counts = {"input": len(trades), "skipped": 0, "labeled": 0, "errors": 0}
    df = pd.DataFrame(trades)
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True).astype("datetime64[ns, UTC]")
    df["already_labeled"] = (
        df["mtf_regime"].notna() & (df["mtf_regime"].astype(str) != "")
    )
    pending = df[~df["already_labeled"]].copy()
    counts["skipped"] = int(df["already_labeled"].sum())
    if pending.empty:
        return [], counts

    client = OandaClient()
    cfg = MTFConfig()
    out_pieces: List[pd.DataFrame] = []

    for inst in sorted(pending["instrument"].unique()):
        print(f"[{inst}] fetching OANDA candles...", flush=True)
        try:
            mtf = fetch_mtf_data(
                instrument=inst, base_granularity="H1",
                base_chunks=3, h4_chunks=3, d1_chunks=2,
                count_per_chunk=500, client=client,
            )
        except Exception as e:
            print(f"  FAIL fetch {inst}: {e}")
            counts["errors"] += int((pending["instrument"] == inst).sum())
            continue
        if mtf["base"].empty or mtf["d1"].empty or mtf["h4"].empty:
            print(f"  empty data for {inst}")
            counts["errors"] += int((pending["instrument"] == inst).sum())
            continue

        lab = label_mtf(mtf["base"], mtf["d1"], mtf["h4"], cfg)
        lab = lab[["time", "regime_mtf", "d1_label", "h4_label",
                   "vol_state"]].copy()
        lab["time"] = pd.to_datetime(lab["time"], utc=True).astype("datetime64[ns, UTC]")
        lab = lab.sort_values("time").reset_index(drop=True)

        earliest_label = lab["time"].min()
        sub = pending[pending["instrument"] == inst].copy().sort_values("entry_time")
        # Drop trades whose entry_time predates the fetched candle window
        before_window = sub[sub["entry_time"] < earliest_label]
        if len(before_window):
            print(f"  {len(before_window)} trades predate candle window "
                  f"(earliest {earliest_label}) — recorded as errors")
            counts["errors"] += len(before_window)
            sub = sub[sub["entry_time"] >= earliest_label]

        merged = pd.merge_asof(
            sub,
            lab.rename(columns={
                "time": "_regime_ts",
                "regime_mtf": "new_regime",
                "d1_label": "new_d1",
                "h4_label": "new_h4",
                "vol_state": "new_vol",
            }),
            left_on="entry_time", right_on="_regime_ts", direction="backward",
        )
        # Drop rows where merge failed (should be rare given predate check)
        missing = merged["new_regime"].isna()
        if missing.any():
            counts["errors"] += int(missing.sum())
            merged = merged[~missing]
        n_ok = len(merged)
        counts["labeled"] += n_ok
        print(f"  {inst}: labeled {n_ok} / skipped {int((df['instrument']==inst).sum()) - n_ok}")
        out_pieces.append(merged)

    if not out_pieces:
        return [], counts
    import pandas as pd  # noqa
    out = pd.concat(out_pieces, ignore_index=True)
    out["new_d1"] = out["new_d1"].astype(int)
    out["new_h4"] = out["new_h4"].astype(int)
    return out.to_dict(orient="records"), counts


def emit_sql(rows: List[dict], output_path: str) -> None:
    """Emit idempotent SQL UPDATE script.

    Each UPDATE has a WHERE clause enforcing empty-only write, so re-running
    against a DB that has already been backfilled is a no-op.
    """
    def _esc(s: str) -> str:
        return str(s).replace("'", "''")

    with open(output_path, "w") as f:
        f.write("-- Backfill mtf_regime columns. Generated by scripts/backfill_mtf_regime.py\n")
        f.write("-- Apply via: sqlite3 /var/data/demo_trades.db < backfill_mtf_regime.sql\n")
        f.write("-- Idempotent: WHERE clause skips rows already labeled.\n\n")
        f.write("BEGIN TRANSACTION;\n")
        for r in rows:
            tid = int(r["id"])
            reg = _esc(r["new_regime"])
            d1 = int(r["new_d1"])
            h4 = int(r["new_h4"])
            vol = _esc(r["new_vol"])
            f.write(
                f"UPDATE demo_trades SET mtf_regime='{reg}', "
                f"mtf_d1_label={d1}, mtf_h4_label={h4}, "
                f"mtf_vol_state='{vol}' "
                f"WHERE id={tid} AND "
                f"(mtf_regime IS NULL OR mtf_regime='');\n"
            )
        f.write("COMMIT;\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades-json", required=True,
                    help="Path to /api/demo/trades JSON snapshot")
    ap.add_argument("--write", choices=["sql"], default=None,
                    help="Emit SQL UPDATE script (default: dry-run)")
    ap.add_argument("--output", default="/tmp/backfill_mtf_regime.sql",
                    help="SQL output path (used with --write sql)")
    args = ap.parse_args()

    trades = load_trades(args.trades_json)
    print(f"Loaded {len(trades)} non-XAU trades")

    rows, counts = label_all(trades)

    # Summary
    print("\n=== Backfill summary ===")
    print(f"  input (non-XAU):        {counts['input']:5d}")
    print(f"  already labeled (skip): {counts['skipped']:5d}")
    print(f"  newly labeled:          {counts['labeled']:5d}")
    print(f"  errors:                 {counts['errors']:5d}")

    if rows:
        from collections import Counter
        reg_dist = Counter(r["new_regime"] for r in rows)
        print("\n=== New label distribution ===")
        for reg, n in sorted(reg_dist.items(), key=lambda x: -x[1]):
            print(f"  {reg:20s}: {n:5d} ({100*n/len(rows):5.1f}%)")

    if args.write == "sql":
        emit_sql(rows, args.output)
        print(f"\nWrote SQL to: {args.output}")
        print("Apply via Render Shell:")
        print(f"  sqlite3 /var/data/demo_trades.db < {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
