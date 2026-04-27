#!/usr/bin/env python3
"""Net-edge WR audit — strategy WR vs market-beta benchmark.

戦略 WR は単独で見ると市場ベータ便乗 (例: GBP/USD 単一ラリーに乗っただけ) と
真のエッジを区別できない。本ツールは指定戦略のトレード時刻範囲を抽出し、
**同期間 × 同 instrument × 同 direction の他戦略 Shadow** を benchmark として
WR/EV を比較する。

intraday_seasonality 検証 (2026-04-27):
  strat_WR=66.7% (4/6 GBP_USD BUY)
  cluster window benchmark = ema_trend_scalp 100% (1/1)
  → net_edge ≈ 0 (戦略固有エッジではなく市場ベータ)

詳細: reports/deployment-wave-analysis-2026-04-27.md §4
使い方:
    python tools/net_edge_audit.py --strategy intraday_seasonality
    python tools/net_edge_audit.py --strategy vol_spike_mr --window 4h
    python tools/net_edge_audit.py --all  # 全 entry_type を走査
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# project root on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.demo_db import DemoDB  # noqa: E402


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    """One-sided lower Wilson confidence bound (95%) for win rate."""
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return max(0.0, (center - margin) / denom)


def audit_strategy(db: DemoDB, entry_type: str, window_h: int = 0) -> dict:
    """Compute strategy vs benchmark WR for a single entry_type.

    window_h=0 means use the union of trade-hour windows; otherwise expand
    each trade entry by ±window_h hours.
    """
    # 1. Strategy trades
    with db._safe_conn() as conn:
        rows = conn.execute(
            "SELECT id, entry_time, instrument, direction, pnl_pips "
            "FROM demo_trades WHERE status='CLOSED' AND entry_type=? "
            "AND (instrument IS NULL OR instrument NOT LIKE '%XAU%') "
            "AND (strftime('%s', exit_time) - strftime('%s', entry_time)) >= 5 "
            "ORDER BY entry_time",
            (entry_type,),
        ).fetchall()
    strat_trades = [dict(r) for r in rows]
    if not strat_trades:
        return {"entry_type": entry_type, "n_strat": 0, "note": "no real trades"}

    strat_n = len(strat_trades)
    strat_wins = sum(1 for t in strat_trades if (t["pnl_pips"] or 0) > 0)
    strat_wr = strat_wins / strat_n
    strat_avg_pip = sum((t["pnl_pips"] or 0) for t in strat_trades) / strat_n

    # 2. Benchmark: same (instrument, direction) for each strategy trade window
    bench_n = 0
    bench_wins = 0
    bench_pip_sum = 0.0
    seen_ids: set[int] = set()
    for t in strat_trades:
        if window_h > 0:
            from datetime import datetime, timedelta, timezone
            try:
                t0 = datetime.fromisoformat(t["entry_time"])
            except Exception:
                continue
            if t0.tzinfo is None:
                t0 = t0.replace(tzinfo=timezone.utc)
            t_lo = (t0 - timedelta(hours=window_h)).isoformat()
            t_hi = (t0 + timedelta(hours=window_h)).isoformat()
        else:
            # 4h bucket centered on the trade
            from datetime import datetime, timedelta, timezone
            try:
                t0 = datetime.fromisoformat(t["entry_time"])
            except Exception:
                continue
            if t0.tzinfo is None:
                t0 = t0.replace(tzinfo=timezone.utc)
            t_lo = (t0 - timedelta(hours=2)).isoformat()
            t_hi = (t0 + timedelta(hours=2)).isoformat()

        with db._safe_conn() as conn:
            brows = conn.execute(
                "SELECT id, pnl_pips FROM demo_trades "
                "WHERE status='CLOSED' AND is_shadow=1 "
                "AND instrument=? AND direction=? AND entry_type != ? "
                "AND entry_time >= ? AND entry_time < ? "
                "AND (strftime('%s', exit_time) - strftime('%s', entry_time)) >= 5",
                (t["instrument"], t["direction"], entry_type, t_lo, t_hi),
            ).fetchall()
        for br in brows:
            if br["id"] in seen_ids:
                continue
            seen_ids.add(br["id"])
            bench_n += 1
            pnl = br["pnl_pips"] or 0
            bench_pip_sum += pnl
            if pnl > 0:
                bench_wins += 1

    bench_wr = bench_wins / bench_n if bench_n else 0.0
    bench_avg_pip = bench_pip_sum / bench_n if bench_n else 0.0

    return {
        "entry_type": entry_type,
        "n_strat": strat_n,
        "strat_wr": round(strat_wr, 3),
        "strat_avg_pip": round(strat_avg_pip, 2),
        "strat_wilson_lower": round(_wilson_lower(strat_wins, strat_n), 3),
        "n_bench": bench_n,
        "bench_wr": round(bench_wr, 3),
        "bench_avg_pip": round(bench_avg_pip, 2),
        "net_edge_wr_pt": round((strat_wr - bench_wr) * 100, 1),
        "net_edge_pip": round(strat_avg_pip - bench_avg_pip, 2),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--strategy", help="single entry_type to audit")
    p.add_argument("--all", action="store_true", help="audit every entry_type")
    p.add_argument("--window", type=int, default=0,
                   help="±hours around each trade for benchmark; 0 uses ±2h bucket")
    p.add_argument("--db", default="demo.db", help="path to sqlite DB")
    args = p.parse_args()

    db = DemoDB(db_path=args.db)

    if args.all:
        with db._safe_conn() as conn:
            ets = [r[0] for r in conn.execute(
                "SELECT DISTINCT entry_type FROM demo_trades "
                "WHERE entry_type IS NOT NULL AND entry_type != '' "
                "AND (instrument IS NULL OR instrument NOT LIKE '%XAU%')"
            ).fetchall()]
        results = []
        for et in sorted(ets):
            r = audit_strategy(db, et, window_h=args.window)
            results.append(r)
        # sort by net_edge_wr_pt desc, n_strat>=5 first
        results.sort(key=lambda r: (-(r.get("n_strat", 0) >= 5),
                                    -r.get("net_edge_wr_pt", -999)))
        print(f"{'entry_type':35s} {'N':>4s} {'strat_WR':>8s} {'WilsonL':>8s} "
              f"{'bench_WR':>8s} {'net_pt':>7s} {'net_pip':>8s}")
        print("-" * 90)
        for r in results:
            n = r.get("n_strat", 0)
            if n == 0:
                continue
            print(
                f"{r['entry_type']:35s} {n:>4d} "
                f"{r.get('strat_wr', 0)*100:>7.1f}% "
                f"{r.get('strat_wilson_lower', 0)*100:>7.1f}% "
                f"{r.get('bench_wr', 0)*100:>7.1f}% "
                f"{r.get('net_edge_wr_pt', 0):>+6.1f} "
                f"{r.get('net_edge_pip', 0):>+7.2f}"
            )
        return 0
    elif args.strategy:
        r = audit_strategy(db, args.strategy, window_h=args.window)
        for k, v in r.items():
            print(f"  {k}: {v}")
        return 0
    else:
        p.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
