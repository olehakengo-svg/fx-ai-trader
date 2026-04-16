#!/usr/bin/env python3
"""365d BT Runner — 全ペアのELITE_LIVE戦略パフォーマンスを取得

Usage:
    BT_MODE=1 python3 tools/bt_365d_runner.py [symbol]

Outputs results to knowledge-base/raw/bt-results/
"""
import os
import sys
import time
import json
from datetime import datetime

os.environ["BT_MODE"] = "1"
os.environ["NO_AUTOSTART"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PAIRS = [
    "USDJPY=X",
    "EURUSD=X",
    "GBPUSD=X",
]

# Allow single pair override
if len(sys.argv) > 1:
    arg = sys.argv[1].upper()
    PAIRS = [p for p in PAIRS if arg in p]
    if not PAIRS:
        PAIRS = [sys.argv[1]]

LOOKBACK = 365
INTERVAL = "15m"

print("=" * 60)
print(f"  365d BT Runner — {INTERVAL} DT Mode")
print(f"  Pairs: {', '.join(PAIRS)}")
print("=" * 60)

t0 = time.time()
print(f"\nImporting app.py...")
import app
print(f"Import OK ({time.time()-t0:.1f}s)")

# ELITE_LIVE strategies to track
ELITE_LIVE = {
    "session_time_bias", "trendline_sweep", "gbp_deep_pullback",
}

results = {}

for symbol in PAIRS:
    print(f"\n{'─'*60}")
    print(f"  Running: {symbol} × {LOOKBACK}d {INTERVAL}")
    print(f"{'─'*60}")

    # Clear cache before each run
    app._dt_bt_cache.clear()

    t1 = time.time()
    try:
        result = app.run_daytrade_backtest(symbol, lookback_days=LOOKBACK, interval=INTERVAL)
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback; traceback.print_exc()
        results[symbol] = {"error": str(e)}
        continue

    elapsed = time.time() - t1
    n_trades = result.get("trades", 0)

    if result.get("error"):
        print(f"  ⚠️ {result['error']} (trades={n_trades})")
        results[symbol] = result
        continue

    print(f"  ✅ {n_trades} trades in {elapsed:.0f}s")
    print(f"  Aggregate: WR={result.get('win_rate')}% EV={result.get('expected_value')} "
          f"Sharpe={result.get('sharpe')} MDD={result.get('max_drawdown')}")

    # Entry breakdown
    breakdown = result.get("entry_breakdown", {})
    print(f"\n  {'Strategy':35s} {'N':>4s} {'WR':>6s} {'EV':>7s} {'PnL':>8s} {'PF':>5s}")
    print(f"  {'─'*65}")

    sorted_entries = sorted(breakdown.items(), key=lambda x: -x[1].get("total", 0))
    for et, stats in sorted_entries:
        n = stats["total"]
        wr = stats["win_rate"]
        ev = stats["ev"]
        pnl = stats["pnl"]
        wins = stats["wins"]
        losses = n - wins
        # Calculate PF
        trades_list = [t for t in result.get("trade_log", []) if t.get("entry_type") == et]
        total_wins_pnl = sum(t.get("tp_m", 0) for t in trades_list if t["outcome"] == "WIN")
        total_loss_pnl = sum(t.get("sl_m", 0) for t in trades_list if t["outcome"] == "LOSS")
        pf = round(total_wins_pnl / max(total_loss_pnl, 0.001), 2)

        elite = " ★" if et in ELITE_LIVE else ""
        print(f"  {et:35s} {n:4d} {wr:5.1f}% {ev:+7.3f} {pnl:+8.1f} {pf:5.2f}{elite}")

    # Walk-forward
    wf = result.get("walk_forward", [])
    if wf:
        print(f"\n  Walk-Forward: ", end="")
        for w in wf:
            print(f"{w['label']}(N={w['trades']} WR={w['win_rate']}% EV={w['expected_value']:+.3f}) ", end="")
        print()

    # Monte Carlo
    mc = result.get("monte_carlo", {})
    if mc:
        print(f"  MC 95%CI: [{mc.get('ci_lower', '?')}, {mc.get('ci_upper', '?')}]")

    results[symbol] = {
        "trades": n_trades,
        "win_rate": result.get("win_rate"),
        "expected_value": result.get("expected_value"),
        "sharpe": result.get("sharpe"),
        "max_drawdown": result.get("max_drawdown"),
        "profit_factor": result.get("profit_factor"),
        "entry_breakdown": {et: {"N": s["total"], "WR": s["win_rate"], "EV": s["ev"]}
                           for et, s in breakdown.items()},
        "walk_forward": wf,
        "monte_carlo": mc,
        "elapsed_s": round(elapsed, 1),
    }

# Save results
total_time = time.time() - t0
print(f"\n{'='*60}")
print(f"  COMPLETE — Total: {total_time:.0f}s")
print(f"{'='*60}")

outfile = f"/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/bt-results/bt-365d-{datetime.now().strftime('%Y-%m-%d')}.json"
with open(outfile, "w") as f:
    json.dump({"date": datetime.now().isoformat(), "lookback": LOOKBACK,
               "interval": INTERVAL, "results": results}, f, indent=2, default=str)
print(f"\nResults saved: {outfile}")
