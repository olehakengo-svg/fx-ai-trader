#!/usr/bin/env python3
"""Target BT Runner — 指定戦略×ペアの365d BTを実行

Usage:
    BT_MODE=1 python3 tools/bt_target_runner.py

BT未実施のPAIR_PROMOTED戦略を対象に365d BTを実行し結果を出力
"""
import os
import sys
import time
import json
from datetime import datetime

os.environ["BT_MODE"] = "1"
os.environ["NO_AUTOSTART"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── BT対象: Alpha探索戦略 ──
TARGETS = [
    # (mode, strategy, yf_symbol, oanda_pair, interval, lookback_days)
    # Wave 3: Alpha探索 — 3戦略 × 3ペア
    ("daytrade", "intraday_seasonality",       "USDJPY=X", "USD_JPY", "15m", 365),
    ("daytrade", "intraday_seasonality",       "EURUSD=X", "EUR_USD", "15m", 365),
    ("daytrade", "intraday_seasonality",       "GBPUSD=X", "GBP_USD", "15m", 365),
    ("daytrade", "wick_imbalance_reversion",   "USDJPY=X", "USD_JPY", "15m", 365),
    ("daytrade", "wick_imbalance_reversion",   "EURUSD=X", "EUR_USD", "15m", 365),
    ("daytrade", "wick_imbalance_reversion",   "GBPUSD=X", "GBP_USD", "15m", 365),
    ("daytrade", "atr_regime_break",           "USDJPY=X", "USD_JPY", "15m", 365),
    ("daytrade", "atr_regime_break",           "EURUSD=X", "EUR_USD", "15m", 365),
    ("daytrade", "atr_regime_break",           "GBPUSD=X", "GBP_USD", "15m", 365),
]

print("=" * 70)
print(f"  Target BT Runner — BT未実施PAIR_PROMOTED戦略")
print(f"  Targets: {len(TARGETS)}")
print("=" * 70)

t0 = time.time()
print(f"\nImporting app.py...")
import app
print(f"Import OK ({time.time()-t0:.1f}s)")

results = {}

for mode, strategy, symbol, pair, interval, lookback in TARGETS:
    print(f"\n{'─'*70}")
    print(f"  {strategy} × {pair} ({mode} {interval} {lookback}d)")
    print(f"{'─'*70}")

    # Clear caches
    if hasattr(app, '_dt_bt_cache'):
        app._dt_bt_cache.clear()
    if hasattr(app, '_scalp_bt_cache'):
        try:
            app._scalp_bt_cache.clear()
        except Exception:
            pass

    t1 = time.time()
    try:
        if mode == "scalp":
            result = app.run_scalp_backtest(symbol, lookback_days=lookback, interval=interval)
        else:
            result = app.run_daytrade_backtest(symbol, lookback_days=lookback, interval=interval)
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback; traceback.print_exc()
        results[f"{strategy}×{pair}"] = {"error": str(e)}
        continue

    elapsed = time.time() - t1
    n_trades = result.get("trades", 0) or result.get("total_trades", 0)

    if result.get("error"):
        print(f"  ⚠️ {result['error']} (trades={n_trades})")

    # Extract target strategy from breakdown
    breakdown = result.get("entry_breakdown", {})
    target_stats = breakdown.get(strategy, {})
    target_n = target_stats.get("total", 0)
    target_wr = target_stats.get("win_rate", 0)
    target_ev = target_stats.get("ev", 0)
    target_pnl = target_stats.get("pnl", 0)

    # Calculate PF for target strategy
    trade_log = result.get("trade_log", [])
    target_trades = [t for t in trade_log if t.get("entry_type") == strategy]
    total_win_pnl = sum(t.get("tp_m", 0) for t in target_trades if t.get("outcome") == "WIN")
    total_loss_pnl = sum(abs(t.get("sl_m", 0)) for t in target_trades if t.get("outcome") == "LOSS")
    pf = round(total_win_pnl / max(total_loss_pnl, 0.001), 2) if total_loss_pnl > 0 else 999.0

    print(f"  Total trades (all strategies): {n_trades} in {elapsed:.0f}s")
    print(f"")
    print(f"  ★ {strategy} × {pair}:")
    print(f"    N={target_n}  WR={target_wr:.1f}%  EV={target_ev:+.3f}  PnL={target_pnl:+.1f}  PF={pf:.2f}")
    print(f"")

    # Show all strategies for context
    if breakdown:
        print(f"  {'Strategy':35s} {'N':>4s} {'WR':>6s} {'EV':>7s} {'PnL':>8s}")
        print(f"  {'─'*60}")
        for et, stats in sorted(breakdown.items(), key=lambda x: -x[1].get("total", 0)):
            n = stats.get("total", 0)
            wr = stats.get("win_rate", 0)
            ev = stats.get("ev", 0)
            pnl = stats.get("pnl", 0)
            marker = " ★★★" if et == strategy else ""
            print(f"  {et:35s} {n:4d} {wr:5.1f}% {ev:+7.3f} {pnl:+8.1f}{marker}")

    # Walk-forward
    wf = result.get("walk_forward", [])
    if wf:
        print(f"\n  Walk-Forward: ", end="")
        for w in wf:
            print(f"{w['label']}(N={w['trades']} WR={w['win_rate']}% EV={w['expected_value']:+.3f}) ", end="")
        print()

    results[f"{strategy}×{pair}"] = {
        "strategy": strategy,
        "pair": pair,
        "mode": mode,
        "interval": interval,
        "lookback_days": lookback,
        "N": target_n,
        "WR": round(target_wr, 1),
        "EV": round(target_ev, 3),
        "PnL": round(target_pnl, 1),
        "PF": pf,
        "total_trades_all": n_trades,
        "elapsed_s": round(elapsed, 1),
    }

# ── Summary ──
total_time = time.time() - t0
print(f"\n{'='*70}")
print(f"  SUMMARY — Total: {total_time:.0f}s")
print(f"{'='*70}")
print(f"")
print(f"  {'Strategy×Pair':45s} {'N':>4s} {'WR':>6s} {'EV':>7s} {'PF':>5s} {'Verdict'}")
print(f"  {'─'*80}")

for key, r in results.items():
    if "error" in r:
        print(f"  {key:45s} ERROR: {r['error']}")
        continue
    n = r["N"]
    wr = r["WR"]
    ev = r["EV"]
    pf = r["PF"]

    # Verdict
    if n < 10:
        verdict = "❌ N不足 — 統計的に無意味"
    elif ev < 0:
        verdict = "❌ 負EV — PAIR_PROMOTED解除検討"
    elif ev < 0.1 and n >= 30:
        verdict = "⚠️ 微小EV — 要監視"
    elif n >= 30 and ev > 0.2:
        verdict = "✅ STRONG"
    elif n >= 20 and ev > 0.1:
        verdict = "✅ GOOD"
    else:
        verdict = "⚠️ 蓄積中"

    print(f"  {key:45s} {n:4d} {wr:5.1f}% {ev:+7.3f} {pf:5.2f} {verdict}")

# Save JSON
outfile = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "knowledge-base", "raw", "bt-results",
    f"bt-target-{datetime.now().strftime('%Y-%m-%d')}.json"
)
with open(outfile, "w") as f:
    json.dump({
        "date": datetime.now().isoformat(),
        "targets": results,
    }, f, indent=2, default=str)
print(f"\nResults saved: {outfile}")
