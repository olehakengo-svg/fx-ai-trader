"""RSK Audit — Realized Skewness Reversion (Barndorff-Nielsen 2005, Amaya 2015).

仮説: rolling N-bar realized skewness が深く負 (downside skew) → 売り疲弊 →
forward N-bar で BUY direction edge。逆: 深く正 → 買い疲弊 → SELL edge。

実装: realized_skew = E[(r - r_mean)³] / σ³
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


def realized_skewness(returns: pd.Series, window: int = 30) -> pd.Series:
    """Rolling realized skewness — vectorized using moments."""
    r = returns.fillna(0)
    m1 = r.rolling(window).mean()
    centered = r - m1
    m3 = (centered ** 3).rolling(window).mean()
    var = (centered ** 2).rolling(window).mean()
    std = var.pow(0.5)
    return m3 / (std ** 3 + 1e-12)


def rsk_event_outcome(df: pd.DataFrame, pair: str,
                     skew_window: int, skew_threshold: float,
                     forward_bars: int) -> dict:
    """Detect skewness extremes; measure forward reversion."""
    pip = 0.01 if "JPY" in pair else 0.0001
    df = df.copy()
    df["ret"] = df["Close"].pct_change()
    df["skew"] = realized_skewness(df["ret"], skew_window)

    # Normalize skew (z-score over rolling window)
    df["skew_z"] = (
        (df["skew"] - df["skew"].rolling(96).mean())
        / (df["skew"].rolling(96).std() + 1e-12)
    )
    df = df.dropna(subset=["skew_z"])

    # Negative skew → BUY (downside exhaustion)
    # Positive skew → SELL (upside exhaustion)
    events = df[df["skew_z"].abs() > skew_threshold].copy()
    if len(events) < 10:
        return {"insufficient": True, "n": int(len(events))}

    events["fwd_close"] = df["Close"].shift(-forward_bars).reindex(events.index)
    events["signal"] = -np.sign(events["skew_z"])  # negative skew → BUY (+1)
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
    sharpe = avg / (rets.std() + 1e-9) * math.sqrt(96 * 252)
    return {
        "pair": pair,
        "skew_window": skew_window,
        "skew_threshold": skew_threshold,
        "forward_bars": forward_bars,
        "n": n,
        "win_rate": round(wr, 4),
        "wilson_lower": round(wlo, 4),
        "wilson_upper": round(whi, 4),
        "p_value": round(p, 6),
        "avg_pip": round(avg, 3),
        "sharpe": round(sharpe, 2),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", nargs="+",
                   default=["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"])
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--skew-windows", type=int, nargs="+", default=[20, 30, 50])
    p.add_argument("--thresholds", type=float, nargs="+", default=[1.0, 1.5, 2.0])
    p.add_argument("--forwards", type=int, nargs="+", default=[2, 4, 6])
    p.add_argument("--output", default="raw/rsk_audit/")
    args = p.parse_args()

    grid = []
    for pair in args.pairs:
        print(f"=== RSK {pair} ===", flush=True)
        try:
            df = _load(pair, args.days)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            continue
        for sw in args.skew_windows:
            for th in args.thresholds:
                for fw in args.forwards:
                    r = rsk_event_outcome(df, pair, sw, th, fw)
                    if "insufficient" in r:
                        continue
                    grid.append(r)
                    print(f"  sw={sw} th={th} fw={fw}: n={r['n']} "
                          f"WR={r['win_rate']:.3f} Wilson_lo={r['wilson_lower']:.3f} "
                          f"avg={r['avg_pip']:+.2f}p Sharpe={r['sharpe']:.1f} "
                          f"p={r['p_value']:.4f}", flush=True)

    n_tests = len(grid)
    print(f"\nBonferroni family: {n_tests}", flush=True)
    sig = []
    for r in grid:
        r["p_bonf"] = round(r["p_value"] * n_tests, 5)
        if r["p_bonf"] < 0.05 and r["wilson_lower"] > 0.50:
            sig.append(r)
    print(f"Bonferroni-significant: {len(sig)}/{n_tests}")
    for r in sig[:20]:
        print(f"  ✅ {r['pair']} sw={r['skew_window']} th={r['skew_threshold']} "
              f"fw={r['forward_bars']}: n={r['n']} WR={r['win_rate']:.3f} "
              f"Wilson_lo={r['wilson_lower']:.3f} Sharpe={r['sharpe']:.1f} "
              f"p_bonf={r['p_bonf']:.5f}", flush=True)
    if grid:
        best = max(grid, key=lambda x: x["sharpe"])
        print(f"\nBest Sharpe: {best['pair']} sw={best['skew_window']} "
              f"th={best['skew_threshold']} fw={best['forward_bars']}: "
              f"WR={best['win_rate']:.3f} Sharpe={best['sharpe']:.1f}", flush=True)

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"rsk_audit_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump({"grid": grid, "bonferroni_n": n_tests, "significant": sig},
                  f, indent=2, default=str)
    print(f"\nJSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
