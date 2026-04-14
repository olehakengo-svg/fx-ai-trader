"""
Scalp BT Lab — スキャルプ戦略の問題点を一つずつ潰すための実験環境

既存のrun_scalp_backtest()のtrade_logを後処理で分析:
  Fix 1: London/NY時間帯フィルター (UTC 7-17のみ → Asia除外)
  Fix 2: 即死率分析 (MFE=0トレードの特性把握)
  Fix 3: SL幅別のWR/EV再計算シミュレーション

Usage:
  python3 tools/bt_scalp_lab.py
  python3 tools/bt_scalp_lab.py --pairs EURUSD=X
"""

import os
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
except ImportError:
    pass

import json
import argparse
import numpy as np


def analyze_scalp_trades(symbol: str, days: int = 60):
    """既存BT実行 → trade_log後処理分析"""
    from app import run_scalp_backtest

    print(f"  Running BT for {symbol} ({days}d)...", flush=True)
    r = run_scalp_backtest(symbol, days)

    if "error" in r:
        return {"error": r["error"], "symbol": symbol}

    trade_log = r.get("trade_log", [])
    entry_breakdown = r.get("entry_breakdown", {})

    if not trade_log:
        return {"error": "No trades in trade_log", "symbol": symbol,
                "entry_breakdown": entry_breakdown}

    # PnL calculation — scalp BT trade_log uses different keys
    # Keys: sig, outcome, bars, type, entry_time, sl_m, tp_m, actual_sl_m, exit_reason
    def _pnl(t):
        ef = t.get("exit_friction_m") or 0
        if t.get("outcome") == "WIN":
            return (t.get("tp_m") or 0) - ef
        _sl = t.get("actual_sl_m") or t.get("sl_m") or 0
        return -(_sl + ef)

    # === Analysis 1: Baseline (全時間帯) ===
    baseline = _compute_stats(trade_log, _pnl, "BASELINE")

    # === Analysis 2: London/NY filter (UTC 7-17) ===
    london_trades = []
    asia_trades = []
    for t in trade_log:
        h = _get_hour(t.get("entry_time", ""))
        if h is not None and 7 <= h < 17:
            london_trades.append(t)
        else:
            asia_trades.append(t)

    london_stats = _compute_stats(london_trades, _pnl, "LONDON/NY (UTC 7-17)")
    asia_stats = _compute_stats(asia_trades, _pnl, "ASIA/OFF (UTC 0-7, 17-24)")

    # === Analysis 3: Per-strategy breakdown (baseline vs london) ===
    strat_analysis = {}
    for t in trade_log:
        et = t.get("type", t.get("entry_type", "unknown"))
        h = _get_hour(t.get("entry_time", ""))
        is_london = h is not None and 7 <= h < 17

        if et not in strat_analysis:
            strat_analysis[et] = {
                "all": [], "london": [], "asia": [],
                "sl_hit": [], "tp_hit": [], "max_hold": [], "sr": [],
            }
        strat_analysis[et]["all"].append(t)
        if is_london:
            strat_analysis[et]["london"].append(t)
        else:
            strat_analysis[et]["asia"].append(t)

        # Exit reason classification
        reason = t.get("exit_reason", "")
        if "sl" in reason.lower():
            strat_analysis[et]["sl_hit"].append(t)
        elif "tp" in reason.lower():
            strat_analysis[et]["tp_hit"].append(t)
        elif "max_hold" in reason.lower():
            strat_analysis[et]["max_hold"].append(t)
        elif "signal_reverse" in reason.lower() or "reverse" in reason.lower():
            strat_analysis[et]["sr"].append(t)

    # Build strategy comparison table
    strat_table = {}
    for et, data in strat_analysis.items():
        n_all = len(data["all"])
        if n_all < 3:
            continue

        all_stats = _mini_stats(data["all"], _pnl)
        ldn_stats = _mini_stats(data["london"], _pnl) if len(data["london"]) >= 2 else None
        asia_stats_s = _mini_stats(data["asia"], _pnl) if len(data["asia"]) >= 2 else None

        # Instant death analysis
        instant_death = sum(1 for t in data["all"]
                          if t.get("bars", t.get("bars_held", 99)) <= 2 and t["outcome"] == "LOSS")
        instant_death_pct = round(instant_death / max(n_all, 1) * 100, 1)

        # Exit reason breakdown
        exit_breakdown = {
            "sl_hit": len(data["sl_hit"]),
            "tp_hit": len(data["tp_hit"]),
            "max_hold": len(data["max_hold"]),
            "signal_reverse": len(data["sr"]),
        }

        strat_table[et] = {
            "all": all_stats,
            "london": ldn_stats,
            "asia": asia_stats_s,
            "instant_death_pct": instant_death_pct,
            "exit_breakdown": exit_breakdown,
            "london_improvement": None,
        }

        # Calculate London improvement
        if ldn_stats and all_stats:
            strat_table[et]["london_improvement"] = {
                "wr_delta": round(ldn_stats["wr"] - all_stats["wr"], 1),
                "ev_delta": round(ldn_stats["ev"] - all_stats["ev"], 3),
            }

    return {
        "symbol": symbol, "days": days,
        "baseline": baseline,
        "london": london_stats,
        "asia": asia_stats,
        "strategies": dict(sorted(strat_table.items(),
                                   key=lambda x: (x[1].get("london") or x[1]["all"])["ev"],
                                   reverse=True)),
    }


def _get_hour(time_str):
    """Extract UTC hour from time string"""
    try:
        from datetime import datetime
        if hasattr(time_str, 'hour'):
            return time_str.hour
        for fmt in ["%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S+00:00",
                    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
            try:
                return datetime.strptime(str(time_str)[:25], fmt).hour
            except ValueError:
                continue
        # Fallback: extract hour from string
        parts = str(time_str).split(" ")
        if len(parts) >= 2:
            return int(parts[1].split(":")[0])
    except Exception:
        pass
    return None


def _compute_stats(trades, pnl_fn, label=""):
    """Compute aggregate stats from trade list"""
    if not trades:
        return {"label": label, "n": 0, "wr": 0, "ev": 0, "pf": 0, "pnl": 0}
    n = len(trades)
    wins = sum(1 for t in trades if t["outcome"] == "WIN")
    wr = round(wins / n * 100, 1)
    pnls = [pnl_fn(t) for t in trades]
    ev = round(sum(pnls) / n, 3)
    wpnl = sum(p for p in pnls if p > 0)
    lpnl = abs(sum(p for p in pnls if p < 0))
    pf = round(wpnl / max(lpnl, 1e-6), 2)
    return {"label": label, "n": n, "wr": wr, "ev": ev, "pf": pf, "pnl": round(sum(pnls), 1)}


def _mini_stats(trades, pnl_fn):
    if not trades:
        return None
    n = len(trades)
    wins = sum(1 for t in trades if t["outcome"] == "WIN")
    wr = round(wins / n * 100, 1)
    pnls = [pnl_fn(t) for t in trades]
    ev = round(sum(pnls) / n, 3)
    wpnl = sum(p for p in pnls if p > 0)
    lpnl = abs(sum(p for p in pnls if p < 0))
    pf = round(wpnl / max(lpnl, 1e-6), 2)
    return {"n": n, "wr": wr, "ev": ev, "pf": pf, "pnl": round(sum(pnls), 1)}


def main():
    parser = argparse.ArgumentParser(description="Scalp BT Lab")
    parser.add_argument("--pairs", default="EURUSD=X,USDJPY=X")
    parser.add_argument("--days", type=int, default=60)
    args = parser.parse_args()

    pairs = args.pairs.split(",")
    all_results = {}

    for pair in pairs:
        print(f"\n{'='*90}")
        print(f"  {pair}")
        print(f"{'='*90}")

        r = analyze_scalp_trades(pair, args.days)
        all_results[pair] = r

        if "error" in r:
            print(f"  ERROR: {r['error']}")
            continue

        # Print baseline vs london
        bl = r["baseline"]
        ld = r["london"]
        asia = r["asia"]
        print(f"\n  {'Condition':30s} {'N':>5s} {'WR':>6s} {'EV':>7s} {'PF':>6s} {'PnL':>8s}")
        print(f"  {'-'*65}")
        for s in [bl, ld, asia]:
            print(f"  {s['label']:30s} {s['n']:>5d} {s['wr']:>5.1f}% {s['ev']:>+6.3f} {s['pf']:>5.2f} {s['pnl']:>+7.1f}p")

        # Print per-strategy
        print(f"\n  === Per-Strategy (sorted by London EV) ===")
        print(f"  {'Strategy':22s} | {'ALL':>22s} | {'LONDON':>22s} | {'ASIA':>22s} | {'死':>4s} | Improvement")
        print(f"  {'':22s} | {'N  WR    EV    PF':>22s} | {'N  WR    EV    PF':>22s} | {'N  WR    EV    PF':>22s} |")
        print(f"  {'-'*120}")

        for et, data in r["strategies"].items():
            a = data["all"]
            l = data.get("london")
            asi = data.get("asia")
            imp = data.get("london_improvement")

            a_str = f"{a['n']:>3d} {a['wr']:>5.1f}% {a['ev']:>+5.3f} {a['pf']:>4.2f}"
            l_str = f"{l['n']:>3d} {l['wr']:>5.1f}% {l['ev']:>+5.3f} {l['pf']:>4.2f}" if l else "  —"
            asi_str = f"{asi['n']:>3d} {asi['wr']:>5.1f}% {asi['ev']:>+5.3f} {asi['pf']:>4.2f}" if asi else "  —"
            death = f"{data['instant_death_pct']:>4.0f}%"
            imp_str = ""
            if imp:
                wr_d = imp["wr_delta"]
                ev_d = imp["ev_delta"]
                imp_str = f"WR{wr_d:>+5.1f}pp EV{ev_d:>+6.3f}"

            tier = "★" if l and l["ev"] > 0.3 and l["pf"] > 1.2 and l["n"] >= 8 else \
                   "●" if l and l["ev"] > 0 and l["pf"] > 1.0 and l["n"] >= 5 else \
                   "○" if l and l["ev"] > 0 else "✗"

            print(f"  {et:22s} | {a_str} | {l_str} | {asi_str} | {death} | {imp_str} {tier}")

    # Save
    out_path = os.path.join(_PROJECT_ROOT, "data", "cache", "scalp_lab_results.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n✅ Results saved to {out_path}")


if __name__ == "__main__":
    main()
