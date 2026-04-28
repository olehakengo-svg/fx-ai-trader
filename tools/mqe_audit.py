"""MQE Audit — Month/Quarter-End Fixing Flow.

仮説 (Melvin-Prins 2015 拡張):
  Month-end last 2-3 営業日 + London 4pm fix (15:30-16:00 UTC) は
  institutional rebalancing で predictable pressure。GBP_USD/EUR_USD
  で fix 周辺の reversion or continuation pattern を audit。
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import calendar
import numpy as np
import pandas as pd

try:
    from scipy.stats import binomtest as _bt
    def _binom(k, n, p):
        return _bt(k=k, n=n, p=p, alternative="greater").pvalue
except ImportError:
    from scipy.stats import binom_test as _bt
    def _binom(k, n, p):
        return _bt(k, n, p, alternative="greater")


def _wilson(wins, n):
    if n == 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _load(pair, days):
    from tools.bt_data_cache import BTDataCache
    cache = BTDataCache()
    df = cache.get(pair, "15m", days=days)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    return df[df.index >= cutoff].copy()


def is_month_end_window(ts, days_before: int = 2) -> bool:
    """Last `days_before` business days of the month."""
    last_day = calendar.monthrange(ts.year, ts.month)[1]
    end = pd.Timestamp(ts.year, ts.month, last_day, tz=ts.tz)
    # walk back to find business days
    threshold_date = end
    count = 0
    while count < days_before:
        if threshold_date.weekday() < 5:
            count += 1
            if count >= days_before:
                break
        threshold_date = threshold_date - pd.Timedelta(days=1)
    return ts.date() >= threshold_date.date()


def is_fix_window(ts, hour_start: int = 15, hour_end: int = 16) -> bool:
    """London 4pm fix window: 15:30-16:00 UTC default."""
    return hour_start <= ts.hour < hour_end


def mqe_event_outcome(df: pd.DataFrame, pair: str,
                     forward_bars: int,
                     direction: str = "reversal",
                     fix_window: tuple = (15, 16)) -> dict:
    pip = 0.01 if "JPY" in pair else 0.0001
    df = df.copy()
    df["dow"] = df.index.dayofweek

    # Mark month-end fix events
    df["is_month_end"] = df.index.map(lambda t: is_month_end_window(t, days_before=2))
    df["is_fix"] = df.index.map(lambda t: is_fix_window(t, *fix_window))
    df["event"] = df["is_month_end"] & df["is_fix"]

    events = df[df["event"]].copy()
    if len(events) < 10:
        return {"insufficient": True, "n": int(len(events))}

    # Forward direction
    events["fwd_close"] = df["Close"].shift(-forward_bars).reindex(events.index)
    # Direction = continuation/reversal of recent move
    events["recent_move"] = events["Close"] - df["Close"].shift(4).reindex(events.index)
    if direction == "reversal":
        events["signal"] = -np.sign(events["recent_move"])
    else:
        events["signal"] = np.sign(events["recent_move"])
    events["fwd_pip"] = (events["fwd_close"] - events["Close"]) / pip
    events["aligned_pip"] = events["signal"] * events["fwd_pip"]
    events = events.dropna(subset=["aligned_pip"])
    if len(events) < 10:
        return {"insufficient": True, "n": int(len(events))}

    rets = events["aligned_pip"].values
    n = len(rets)
    n_wins = int((rets > 0).sum())
    wr = n_wins / n
    wlo, whi = _wilson(n_wins, n)
    p = _binom(n_wins, n, p=0.5)
    avg = float(rets.mean())
    sharpe = avg / (rets.std() + 1e-9) * math.sqrt(252)  # daily-ish event freq
    return {
        "pair": pair,
        "direction": direction,
        "forward_bars": forward_bars,
        "fix_window": f"{fix_window[0]}-{fix_window[1]}UTC",
        "n": n,
        "win_rate": round(wr, 4),
        "wilson_lower": round(wlo, 4),
        "wilson_upper": round(whi, 4),
        "p_value": round(p, 6),
        "avg_pip": round(avg, 3),
        "sharpe": round(float(sharpe), 2),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", nargs="+",
                   default=["GBP_USD", "EUR_USD", "USD_JPY"])
    p.add_argument("--days", type=int, default=730,
                   help="MQE needs longer history for sufficient month-ends")
    p.add_argument("--forwards", type=int, nargs="+", default=[2, 4, 6, 8])
    p.add_argument("--output", default="raw/mqe_audit/")
    args = p.parse_args()

    grid = []
    for pair in args.pairs:
        print(f"=== MQE {pair} ===", flush=True)
        try:
            df = _load(pair, args.days)
            print(f"  Loaded {len(df)} bars", flush=True)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            continue
        for fw in args.forwards:
            for direction in ("reversal", "continuation"):
                r = mqe_event_outcome(df, pair, fw, direction)
                if "insufficient" in r:
                    continue
                grid.append(r)
                print(f"  {direction[:3]} fw={fw}: n={r['n']} WR={r['win_rate']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} avg={r['avg_pip']:+.2f}p "
                      f"Sharpe={r['sharpe']:.2f} p={r['p_value']:.4f}",
                      flush=True)

    n_tests = len(grid)
    print(f"\nBonferroni family: {n_tests}", flush=True)
    sig = []
    for r in grid:
        r["p_bonf"] = round(r["p_value"] * n_tests, 5)
        if r["p_bonf"] < 0.05 and r["wilson_lower"] > 0.50:
            sig.append(r)
    print(f"Bonferroni-significant: {len(sig)}/{n_tests}")
    for r in sig:
        print(f"  ✅ {r['pair']} {r['direction']} fw={r['forward_bars']}: "
              f"n={r['n']} WR={r['win_rate']:.3f} p_bonf={r['p_bonf']:.5f}",
              flush=True)
    if grid:
        best = max(grid, key=lambda x: x["sharpe"])
        print(f"\nBest Sharpe: {best['pair']} {best['direction']} fw={best['forward_bars']} "
              f"WR={best['win_rate']:.3f} Sharpe={best['sharpe']:.2f}",
              flush=True)

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"mqe_audit_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump({"grid": grid, "bonferroni_n": n_tests, "significant": sig},
                  f, indent=2, default=str)
    print(f"\nJSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
