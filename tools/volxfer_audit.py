"""VolXfer Audit — Cross-Pair Volatility Transmission lead-lag.

仮説 (Engle-Sheppard 2001 DCC, Diebold-Yilmaz 2009 spillover):
  pair_A の |return| > 2σ vol spike → pair_B の N bar 後 direction predict。
  特に JPY pairs trio (USD_JPY/EUR_JPY/GBP_JPY) で機関 unwind cascade 構造。

監査: leader pair の vol spike 発生時、follower pair の forward direction が
spike direction と整合する確率を測定。
"""
from __future__ import annotations
import argparse, json, math, os, sys
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


def volxfer_audit(leader: str, follower: str, days: int,
                  sigma_threshold: float = 2.0,
                  forward_bars: int = 2,
                  direction: str = "follow") -> dict:
    """leader vol spike → follower forward direction。

    direction:
      "follow"   = follower moves SAME direction as leader spike
      "fade"     = follower moves OPPOSITE direction
    """
    pip_f = 0.01 if "JPY" in follower else 0.0001
    a = _load(leader, days)
    b = _load(follower, days)

    df = pd.concat([a["Close"].rename("a"), b["Close"].rename("b")],
                   axis=1, join="inner").dropna()
    df["a_ret"] = df["a"].pct_change()
    df["b_ret"] = df["b"].pct_change()
    df["a_std"] = df["a_ret"].rolling(60).std()

    # leader vol spike events
    events = df[df["a_ret"].abs() > sigma_threshold * df["a_std"]].copy()
    if len(events) < 20:
        return {"insufficient": True, "n": int(len(events))}

    events["fwd_b"] = df["b"].shift(-forward_bars).reindex(events.index)
    events["fwd_pip"] = (events["fwd_b"] - events["b"]) / pip_f

    if direction == "follow":
        events["signal"] = np.sign(events["a_ret"])
    else:
        events["signal"] = -np.sign(events["a_ret"])
    events["aligned_pip"] = events["signal"] * events["fwd_pip"]
    events = events.dropna(subset=["aligned_pip"])
    if len(events) < 20:
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
        "leader": leader, "follower": follower,
        "sigma": sigma_threshold, "forward_bars": forward_bars,
        "direction": direction,
        "n": n, "win_rate": round(wr, 4),
        "wilson_lower": round(wlo, 4), "wilson_upper": round(whi, 4),
        "p_value": round(p, 6), "avg_pip": round(avg, 3),
        "sharpe": round(sharpe, 2),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--sigmas", type=float, nargs="+", default=[1.5, 2.0, 2.5])
    p.add_argument("--forwards", type=int, nargs="+", default=[1, 2, 3])
    p.add_argument("--output", default="raw/volxfer_audit/")
    args = p.parse_args()

    # JPY trio + EUR/GBP_USD pair
    pairs = [
        ("USD_JPY", "EUR_JPY"), ("USD_JPY", "GBP_JPY"),
        ("EUR_JPY", "USD_JPY"), ("EUR_JPY", "GBP_JPY"),
        ("GBP_JPY", "USD_JPY"), ("GBP_JPY", "EUR_JPY"),
        ("EUR_USD", "GBP_USD"), ("GBP_USD", "EUR_USD"),
    ]
    grid = []
    for leader, follower in pairs:
        for sg in args.sigmas:
            for fw in args.forwards:
                for dir_ in ("follow", "fade"):
                    r = volxfer_audit(leader, follower, args.days,
                                      sg, fw, dir_)
                    if "insufficient" in r:
                        continue
                    grid.append(r)
                    if r.get("p_value", 1) < 0.05:
                        print(f"  {leader}->{follower} {dir_[:4]} σ={sg} fw={fw}: "
                              f"n={r['n']} WR={r['win_rate']:.3f} Sharpe={r['sharpe']:.1f} "
                              f"p={r['p_value']:.4f}", flush=True)

    n_tests = len(grid)
    print(f"\nTotal grid: {n_tests}", flush=True)
    sig = []
    for r in grid:
        r["p_bonf"] = round(r["p_value"] * n_tests, 5)
        if r["p_bonf"] < 0.05 and r["wilson_lower"] > 0.50:
            sig.append(r)
    print(f"Bonferroni-significant: {len(sig)}/{n_tests}")
    for r in sig[:20]:
        print(f"  ✅ {r['leader']}->{r['follower']} {r['direction']} "
              f"σ={r['sigma']} fw={r['forward_bars']}: "
              f"n={r['n']} WR={r['win_rate']:.3f} p_bonf={r['p_bonf']:.5f}",
              flush=True)
    if grid:
        best = max(grid, key=lambda x: x["sharpe"])
        print(f"\nBest Sharpe: {best['leader']}->{best['follower']} "
              f"{best['direction']} σ={best['sigma']} fw={best['forward_bars']}: "
              f"WR={best['win_rate']:.3f} Sharpe={best['sharpe']:.1f}",
              flush=True)

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"volxfer_audit_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump({"grid": grid, "bonferroni_n": n_tests, "significant": sig},
                  f, indent=2, default=str)
    print(f"\nJSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
