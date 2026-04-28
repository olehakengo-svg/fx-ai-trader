"""AEO Audit — Asia Equity Open Transmission to JPY pairs.

仮説 (Andersen-Bollerslev 2002, Cai-Cheung 2001):
  Equity index intraday change → JPY pair direction lead-lag.
  ^N225 (Nikkei) 9:00 JST = 00:00 UTC open は USD_JPY Tokyo session を予測。
  ^GSPC (SPX) 14:30 UTC NY open は USD_JPY/EUR_JPY を予測。

Output: raw/aeo_audit/aeo_audit_{date}.md
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

import warnings; warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

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


def _load_equity(ticker: str, days: int) -> pd.DataFrame:
    import yfinance as yf
    period = "60d" if days >= 60 else f"{days}d"
    df = yf.download(ticker, period=period, interval="15m", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def _load_fx(pair: str, days: int) -> pd.DataFrame:
    from tools.bt_data_cache import BTDataCache
    cache = BTDataCache()
    df = cache.get(pair, "15m", days=days)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    return df[df.index >= cutoff].copy()


def aeo_event_outcome(eq: pd.DataFrame, fx: pd.DataFrame, pair: str,
                     equity_sigma: float, forward_bars: int,
                     equity_name: str = "EQUITY") -> dict:
    pip = 0.01 if "JPY" in pair else 0.0001

    # Align fx and equity by timestamp (intersection)
    eq_close = eq["Close"].rename("eq")
    fx_close = fx["Close"].rename("fx")
    df = pd.concat([eq_close, fx_close], axis=1, join="inner").dropna()
    if len(df) < 100:
        return {"insufficient": True, "n": int(len(df))}

    df["eq_ret"] = df["eq"].pct_change()
    df["fx_ret"] = df["fx"].pct_change()
    eq_std = df["eq_ret"].std()

    # Events: equity moves > N×σ
    events = df[df["eq_ret"].abs() > equity_sigma * eq_std].copy()
    if len(events) < 10:
        return {"insufficient": True, "n": int(len(events))}

    # Forward FX direction
    events["fwd_fx_ret"] = (df["fx"].shift(-forward_bars) / df["fx"] - 1
                             ).reindex(events.index)
    # Hypothesis: equity UP → JPY pair UP (risk-on, JPY weakens)
    events["signal"] = np.sign(events["eq_ret"])
    events["aligned_pip"] = events["signal"] * events["fwd_fx_ret"] * events["fx"] / pip
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
        "equity": equity_name,
        "pair": pair,
        "equity_sigma": equity_sigma,
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
    p.add_argument("--days", type=int, default=60,
                   help="yfinance intraday cap = 60d")
    p.add_argument("--sigmas", type=float, nargs="+", default=[1.0, 1.5, 2.0])
    p.add_argument("--forwards", type=int, nargs="+", default=[1, 2, 4])
    p.add_argument("--output", default="raw/aeo_audit/")
    args = p.parse_args()

    grid = []
    # Test combinations: equity × FX pair
    combos = [
        ("^GSPC", "SPX", ["USD_JPY", "EUR_JPY", "GBP_JPY"]),
        ("^N225", "Nikkei", ["USD_JPY", "EUR_JPY"]),
        ("NQ=F", "NQ_fut", ["USD_JPY"]),
    ]

    eq_data = {}
    for tk, name, _ in combos:
        try:
            print(f"Loading {name} ({tk})...", flush=True)
            eq_data[tk] = _load_equity(tk, args.days)
            print(f"  {name}: {len(eq_data[tk])} bars", flush=True)
        except Exception as e:
            print(f"  FAILED {name}: {e}", flush=True)

    for tk, name, pairs in combos:
        if tk not in eq_data:
            continue
        for pair in pairs:
            try:
                fx = _load_fx(pair, args.days)
            except Exception as e:
                print(f"  FX load failed {pair}: {e}", flush=True)
                continue
            print(f"\n=== AEO {name} → {pair} ===", flush=True)
            for sg in args.sigmas:
                for fw in args.forwards:
                    r = aeo_event_outcome(eq_data[tk], fx, pair,
                                          equity_sigma=sg, forward_bars=fw,
                                          equity_name=name)
                    if "insufficient" in r:
                        continue
                    grid.append(r)
                    print(f"  σ={sg} fw={fw}: n={r['n']} WR={r['win_rate']:.3f} "
                          f"Wilson_lo={r['wilson_lower']:.3f} avg={r['avg_pip']:+.2f}p "
                          f"Sharpe={r['sharpe']:.1f} p={r['p_value']:.4f}", flush=True)

    n_tests = len(grid)
    print(f"\nBonferroni family: {n_tests}", flush=True)
    sig = []
    for r in grid:
        r["p_bonf"] = round(r["p_value"] * n_tests, 5)
        if r["p_bonf"] < 0.05 and r["wilson_lower"] > 0.50:
            sig.append(r)
    print(f"Bonferroni-significant: {len(sig)}/{n_tests}")
    for r in sig:
        print(f"  ✅ {r['equity']} → {r['pair']} σ={r['equity_sigma']} "
              f"fw={r['forward_bars']}: n={r['n']} WR={r['win_rate']:.3f} "
              f"p_bonf={r['p_bonf']:.5f}", flush=True)
    if grid:
        best = max(grid, key=lambda x: x["sharpe"])
        print(f"\nBest Sharpe: {best['equity']}→{best['pair']} σ={best['equity_sigma']} "
              f"fw={best['forward_bars']}: WR={best['win_rate']:.3f} Sharpe={best['sharpe']:.1f}",
              flush=True)

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"aeo_audit_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump({"grid": grid, "bonferroni_n": n_tests, "significant": sig},
                  f, indent=2, default=str)
    print(f"\nJSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
