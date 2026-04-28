"""VPIN Audit — toxic flow event reversal detection.

仮説: VPIN > P90 → toxic order flow (informed trader 集中) →
其後 N bar 内に price reversal が発生確率高 (Easley-de Prado 2012).
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

from modules.vpin import bvc_split, equal_volume_buckets, vpin_series


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


def vpin_event_study(df: pd.DataFrame, pair: str,
                     vpin_pct_threshold: float = 0.90,
                     forward_bars_grid: list = (4, 8, 12),
                     bucket_per_day: int = 50,
                     vpin_window: int = 50) -> list:
    """For each forward_bars: compute VPIN events and forward reversal stats."""
    pip = 0.01 if "JPY" in pair else 0.0001

    # Compute VPIN
    df_bvc = bvc_split(df, sigma_window=30)
    buckets = equal_volume_buckets(df_bvc, buckets_per_day=bucket_per_day)
    if len(buckets) < vpin_window + 20:
        return [{"insufficient": True, "n_buckets": len(buckets)}]

    vpin = vpin_series(buckets, window=vpin_window)
    vpin = vpin.dropna()
    if len(vpin) < 50:
        return [{"insufficient": True, "n_vpin": len(vpin)}]

    threshold = vpin.quantile(vpin_pct_threshold)
    events_ts = vpin[vpin > threshold].index

    results = []
    for fw in forward_bars_grid:
        # For each event timestamp, find the closest df bar and compute forward
        records = []
        for ev_ts in events_ts:
            # Find nearest df index >= ev_ts
            try:
                loc = df.index.searchsorted(ev_ts)
                if loc + fw >= len(df) or loc >= len(df):
                    continue
                c0 = float(df.iloc[loc]["Close"])
                c_fw = float(df.iloc[loc + fw]["Close"])
                # Direction at event: use last bar's price change as proxy
                if loc < 1:
                    continue
                last_change = c0 - float(df.iloc[loc - 1]["Close"])
                # Reversal hypothesis: forward direction = -sign(last_change)
                signal = -np.sign(last_change)
                if signal == 0:
                    continue
                fwd_pip = signal * (c_fw - c0) / pip
                records.append({
                    "ts": ev_ts, "vpin": float(vpin.loc[ev_ts]),
                    "signal": int(signal),
                    "fwd_pip": fwd_pip,
                })
            except Exception:
                continue
        if len(records) < 10:
            results.append({"forward_bars": fw, "n": len(records),
                            "insufficient": True})
            continue

        rets = np.array([r["fwd_pip"] for r in records])
        n = len(rets)
        n_wins = int((rets > 0).sum())
        wr = n_wins / n
        wlo, whi = _wilson(n_wins, n)
        p = _binom(n_wins, n, p=0.5)
        avg = float(rets.mean())
        std = float(rets.std() + 1e-9)
        sharpe = avg / std * math.sqrt(96 * 252)

        results.append({
            "pair": pair,
            "forward_bars": fw,
            "vpin_pct": vpin_pct_threshold,
            "n": n,
            "win_rate": round(wr, 4),
            "wilson_lower": round(wlo, 4),
            "wilson_upper": round(whi, 4),
            "p_value": round(p, 6),
            "avg_pip": round(avg, 3),
            "sharpe": round(sharpe, 2),
            "vpin_threshold": round(float(threshold), 4),
        })
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", nargs="+",
                   default=["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"])
    p.add_argument("--days", type=int, default=60,
                   help="lookback days (intraday data limit)")
    p.add_argument("--vpin-pcts", type=float, nargs="+", default=[0.85, 0.90, 0.95])
    p.add_argument("--forwards", type=int, nargs="+", default=[4, 8, 12])
    p.add_argument("--output", default="raw/vpin_audit/")
    args = p.parse_args()

    grid = []
    for pair in args.pairs:
        print(f"=== VPIN {pair} ===", flush=True)
        try:
            df = _load(pair, args.days)
            print(f"  Loaded {len(df)} bars", flush=True)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            continue
        for vp in args.vpin_pcts:
            results = vpin_event_study(df, pair, vpin_pct_threshold=vp,
                                       forward_bars_grid=args.forwards)
            for r in results:
                if "insufficient" in r:
                    continue
                r["vpin_pct"] = vp
                grid.append(r)
                print(f"  vpin>P{int(vp*100)} fw={r['forward_bars']}: "
                      f"n={r['n']} WR={r['win_rate']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} avg={r['avg_pip']:+.2f}p "
                      f"Sharpe={r['sharpe']:.1f} p={r['p_value']:.4f}",
                      flush=True)

    n_tests = len(grid)
    print(f"\nBonferroni family: {n_tests}, α/n = {0.05/max(1,n_tests):.5f}",
          flush=True)
    sig = []
    for r in grid:
        r["p_bonf"] = round(r["p_value"] * n_tests, 5)
        if r["p_bonf"] < 0.05 and r["wilson_lower"] > 0.50:
            sig.append(r)
            print(f"  ✅ {r['pair']} vp={r['vpin_pct']} fw={r['forward_bars']} "
                  f"p_bonf={r['p_bonf']:.5f}", flush=True)

    if grid:
        best = max(grid, key=lambda x: x["sharpe"])
        print(f"\nBest Sharpe: {best['pair']} vp={best['vpin_pct']} fw={best['forward_bars']} "
              f"Sharpe={best['sharpe']:.1f} WR={best['win_rate']:.3f}", flush=True)

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"vpin_audit_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump({"grid": grid, "bonferroni_n": n_tests}, f,
                  indent=2, default=str)
    print(f"\nJSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
