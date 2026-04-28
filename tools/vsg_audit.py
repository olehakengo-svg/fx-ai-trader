"""VSG Audit — Vol Surprise (EWMA-forecast vs Realized) edge detection.

代替: arch ライブラリなしで RiskMetrics EWMA (λ=0.94) を IGARCH proxy として使用
(Engle-Patton 2001 では full GARCH(1,1) が議論されるが EWMA は IGARCH(1,1)
の特殊解で実用上 90%以上の説明力を確保できる)

仮説: |Realized - Forecast| / Forecast > θ で「vol surprise」発生 →
方向 = sign(realized return)、forward N-bar で **momentum 継続** か MR か検定
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


def ewma_volatility(returns: pd.Series, lambda_: float = 0.94) -> pd.Series:
    """RiskMetrics EWMA volatility forecast: σ²_t = (1-λ) r²_{t-1} + λ σ²_{t-1}."""
    sq_ret = returns.fillna(0) ** 2
    var = sq_ret.ewm(alpha=1 - lambda_, adjust=False).mean()
    return np.sqrt(var)


def vsg_event_outcome(df: pd.DataFrame, pair: str,
                      surprise_threshold: float, forward_bars: int,
                      direction: str = "momentum") -> dict:
    """Vol surprise event study.

    direction: "momentum" → forward direction = realized direction
               "reversal" → forward direction = -realized direction
    """
    pip = 0.01 if "JPY" in pair else 0.0001
    df = df.copy()
    df["ret"] = df["Close"].pct_change()
    df["ewma_vol"] = ewma_volatility(df["ret"])
    # Forecast (next-bar): use t-1 EWMA as prediction for bar t realized
    df["forecast"] = df["ewma_vol"].shift(1)
    df["realized"] = df["ret"].abs()
    df["surprise"] = (df["realized"] - df["forecast"]) / df["forecast"].replace(0, np.nan)
    df = df.dropna(subset=["surprise"])

    events = df[df["surprise"] > surprise_threshold].copy()
    if len(events) < 10:
        return {"n": int(len(events)), "insufficient": True}

    # Forward outcome
    events["fwd_close"] = df["Close"].shift(-forward_bars).reindex(events.index)
    events["fwd_pip_raw"] = (events["fwd_close"] - events["Close"]) / pip
    if direction == "momentum":
        events["signal"] = np.sign(events["ret"])
    else:
        events["signal"] = -np.sign(events["ret"])
    events["aligned_pip"] = events["signal"] * events["fwd_pip_raw"]
    events = events.dropna(subset=["aligned_pip"])
    if len(events) < 10:
        return {"n": int(len(events)), "insufficient": True}

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
        "surprise_threshold": surprise_threshold,
        "forward_bars": forward_bars,
        "direction": direction,
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
    p.add_argument("--thresholds", type=float, nargs="+",
                   default=[0.5, 1.0, 1.5, 2.0])
    p.add_argument("--forwards", type=int, nargs="+", default=[2, 4, 6, 8])
    p.add_argument("--output", default="raw/vsg_audit/")
    args = p.parse_args()

    grid = []
    for pair in args.pairs:
        print(f"=== VSG {pair} ===", flush=True)
        try:
            df = _load(pair, args.days)
            print(f"  Loaded {len(df)} bars", flush=True)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            continue
        for th in args.thresholds:
            for fw in args.forwards:
                for direction in ("momentum", "reversal"):
                    r = vsg_event_outcome(df, pair, th, fw, direction)
                    if "insufficient" in r:
                        continue
                    grid.append(r)
                    print(f"  {direction[:3]} th={th} fw={fw}: "
                          f"n={r['n']} WR={r['win_rate']:.3f} "
                          f"Wilson_lo={r['wilson_lower']:.3f} avg={r['avg_pip']:+.2f}p "
                          f"Sharpe={r['sharpe']:.1f} p={r['p_value']:.4f}",
                          flush=True)

    n_tests = len(grid)
    print(f"\nBonferroni family: {n_tests}", flush=True)
    sig = []
    for r in grid:
        r["p_bonf"] = round(r["p_value"] * n_tests, 5)
        if r["p_bonf"] < 0.05 and r["wilson_lower"] > 0.50:
            sig.append(r)

    print(f"Bonferroni-significant: {len(sig)}")
    for r in sig:
        print(f"  ✅ {r['pair']} {r['direction']} th={r['surprise_threshold']} "
              f"fw={r['forward_bars']} n={r['n']} WR={r['win_rate']:.3f} "
              f"p_bonf={r['p_bonf']:.5f}", flush=True)

    if grid:
        best = max(grid, key=lambda x: x["sharpe"])
        print(f"\nBest Sharpe: {best['pair']} {best['direction']} "
              f"th={best['surprise_threshold']} fw={best['forward_bars']} "
              f"WR={best['win_rate']:.3f} Sharpe={best['sharpe']:.1f}",
              flush=True)

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"vsg_audit_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump({"grid": grid, "bonferroni_n": n_tests}, f,
                  indent=2, default=str)
    print(f"\nJSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
