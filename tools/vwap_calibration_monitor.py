#!/usr/bin/env python3
"""
VWAP Calibration Monitor

目的:
  2026-04-23 VWAP conf_adj 中立化 (commit b37ee8b) の効果測定。
  Shadow post-cutoff データを confidence bucket × strategy category で集計し、
  monotonicity と aligned/conflict WR gap を定点観測する。

使い方:
  python3 tools/vwap_calibration_monitor.py          # 標準レポート
  python3 tools/vwap_calibration_monitor.py --json   # 機械可読出力
  python3 tools/vwap_calibration_monitor.py --since 2026-04-24  # 期間指定

推奨運用:
  週次 cron で実行し、KB `wiki/analyses/vwap-calibration-timeseries.md` に追記。

判定基準 (Phase 2 GO/NOGO):
  - Delta WR (High - Low) が -3pp -> +3pp に反転 -> VWAP修正効果あり、
    戦略カテゴリ別 conf_adj (TF +2 / MR -2) へ進む
  - 反転せず flat なら、confidence gate 全体の Platt/Isotonic 再校正が必要
"""
import argparse
import json
import subprocess
import sys
from collections import defaultdict
from statistics import mean

DEFAULT_SINCE = "2026-04-08"  # fidelity cutoff
BT_COST = 1.0

# Categorization aligned with strategies/daytrade/* and shadow routing
MR_TYPES = {
    "bb_rsi_reversion", "sr_channel_reversal", "engulfing_bb", "fib_reversal",
    "stoch_trend_pullback", "dt_bb_rsi_mr", "sr_fib_confluence",
    "engulfing_bb_lvn_london_ny", "bb_rsi_mr", "sr_touch",
}
TF_TYPES = {
    "ema_pullback", "ema200_trend_reversal", "trend_rebound", "ema_trend_scalp",
    "ema_pullback_v2", "trend_break", "london_breakout",
}

BUCKETS = ["<30", "30-39", "40-49", "50-54", "55-59", "60-64", "65-69", "70-79", "80-89", "90+"]


def bucket_for(conf):
    if conf is None:
        return None
    c = int(conf)
    if c < 30: return "<30"
    if c < 40: return "30-39"
    if c < 50: return "40-49"
    if c < 55: return "50-54"
    if c < 60: return "55-59"
    if c < 65: return "60-64"
    if c < 70: return "65-69"
    if c < 80: return "70-79"
    if c < 90: return "80-89"
    return "90+"


def categorize(entry_type):
    if entry_type in MR_TYPES:
        return "MR"
    if entry_type in TF_TYPES:
        return "TF"
    return "OTHER"


def fetch_closed_since(since):
    trades = []
    offset = 0
    limit = 500
    while True:
        url = (
            "https://fx-ai-trader.onrender.com/api/demo/trades"
            f"?status=closed&date_from={since}&limit={limit}&offset={offset}"
        )
        try:
            out = subprocess.check_output(["curl", "-sS", url], timeout=60)
            d = json.loads(out)
        except Exception as e:
            print(f"[warn] fetch offset={offset}: {e}", file=sys.stderr)
            break
        batch = d.get("trades", [])
        trades.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
        if offset > 50000:
            break
    return trades


def compute(trades):
    by_cell = defaultdict(list)
    by_bucket = defaultdict(list)
    by_cat = defaultdict(list)

    n_shadow = 0
    for t in trades:
        if t.get("is_shadow") != 1:
            continue
        if "XAU" in (t.get("instrument") or ""):
            continue
        if t.get("pnl_pips") is None:
            continue
        n_shadow += 1
        b = bucket_for(t.get("confidence"))
        c = categorize(t.get("entry_type"))
        p = float(t["pnl_pips"])
        if b is None:
            continue
        by_cell[(b, c)].append(p)
        by_bucket[b].append(p)
        by_cat[c].append(p)

    def wr(vals):
        return 100.0 * sum(1 for v in vals if v > 0) / len(vals) if vals else 0.0

    def evc(vals):
        return mean(vals) - BT_COST if vals else 0.0

    def summarize(vals):
        return {"n": len(vals), "wr": round(wr(vals), 2), "ev_cost": round(evc(vals), 2)}

    result = {
        "n_shadow": n_shadow,
        "by_bucket": {b: summarize(by_bucket[b]) for b in BUCKETS if by_bucket[b]},
        "by_category": {c: summarize(by_cat[c]) for c in ("TF", "MR", "OTHER") if by_cat[c]},
        "by_cell": {
            f"{b}|{c}": summarize(by_cell[(b, c)])
            for b in BUCKETS for c in ("TF", "MR", "OTHER") if by_cell.get((b, c))
        },
    }

    # Monotonicity
    low_buckets = ("30-39", "40-49", "50-54")
    high_buckets = ("65-69", "70-79", "80-89", "90+")
    low_pool = [v for b in low_buckets for v in by_bucket.get(b, [])]
    high_pool = [v for b in high_buckets for v in by_bucket.get(b, [])]
    if low_pool and high_pool:
        delta = wr(high_pool) - wr(low_pool)
        result["monotonicity"] = {
            "low_n": len(low_pool), "low_wr": round(wr(low_pool), 2),
            "high_n": len(high_pool), "high_wr": round(wr(high_pool), 2),
            "delta_wr": round(delta, 2),
            "verdict": "monotonic" if delta > 3 else ("inverse" if delta < -3 else "flat"),
        }

    for cat in ("TF", "MR"):
        low_c = [v for b in low_buckets for v in by_cell.get((b, cat), [])]
        high_c = [v for b in high_buckets for v in by_cell.get((b, cat), [])]
        if len(low_c) >= 10 and len(high_c) >= 10:
            result.setdefault("category_monotonicity", {})[cat] = {
                "low_n": len(low_c), "low_wr": round(wr(low_c), 2),
                "high_n": len(high_c), "high_wr": round(wr(high_c), 2),
                "delta_wr": round(wr(high_c) - wr(low_c), 2),
            }

    return result


def render_text(r):
    print(f"Shadow post-cutoff closed N = {r['n_shadow']}")
    print()
    cats = ("TF", "MR", "OTHER")
    header = f"{'bucket':<8} |" + "|".join(f"{c+' N':>5} {c+' WR':>7} {c+' EV':>8}" for c in cats)
    print(header)
    print("-" * len(header))
    for b in BUCKETS:
        row = [f"{b:<8}"]
        for c in cats:
            key = f"{b}|{c}"
            if key in r["by_cell"]:
                d = r["by_cell"][key]
                row.append(f"{d['n']:>5} {d['wr']:>6.1f}% {d['ev_cost']:>+7.2f}p")
            else:
                row.append(f"{'.':>5} {'-':>7} {'-':>8}")
        print("|".join(row))
    print()
    if "monotonicity" in r:
        m = r["monotonicity"]
        print(f"Pooled monotonicity: Low N={m['low_n']} WR={m['low_wr']}% vs "
              f"High N={m['high_n']} WR={m['high_wr']}% "
              f"(Delta={m['delta_wr']:+.1f}pp) -> {m['verdict']}")
    if "category_monotonicity" in r:
        for cat, m in r["category_monotonicity"].items():
            print(f"  {cat}: low N={m['low_n']} WR={m['low_wr']}% -> "
                  f"high N={m['high_n']} WR={m['high_wr']}% "
                  f"(Delta={m['delta_wr']:+.1f}pp)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=DEFAULT_SINCE,
                    help=f"date_from (YYYY-MM-DD), default={DEFAULT_SINCE}")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    trades = fetch_closed_since(args.since)
    if not trades:
        print("No trades fetched.", file=sys.stderr)
        sys.exit(1)
    r = compute(trades)
    r["since"] = args.since
    r["source"] = "https://fx-ai-trader.onrender.com/api/demo/trades"

    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        render_text(r)


if __name__ == "__main__":
    main()
