"""CSMR Audit — Currency Strength Mean Reversion at Extremes.

仮説: basket strength が rolling 96-bar (24h) percentile で ≥95%ile or ≤5%ile
の extreme に達した時、強い通貨は弱まる/弱い通貨は戻る (Lustig-Verdelhan 2007).

xs_momentum (per-pair momentum follow) との orthogonality を必須確認。
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

from modules.currency_strength import (
    basket_strength, basket_strength_percentile, PAIR_MAP,
)


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


def csmr_audit(days: int = 365,
               pct_extreme: float = 0.05,
               percentile_window: int = 96,
               forward_bars_grid: list = (4, 8, 12)) -> list:
    """Detect basket extremes, measure forward reversion."""
    pairs = list(PAIR_MAP.keys())
    pair_dfs = {}
    for pair in pairs:
        try:
            df = _load(pair, days)
            pair_dfs[pair] = df
        except Exception as e:
            print(f"  load failed {pair}: {e}")
            continue

    if len(pair_dfs) < 4:
        return []

    # Common index (intersection of all pair indices)
    common_idx = None
    for df in pair_dfs.values():
        if common_idx is None:
            common_idx = df.index
        else:
            common_idx = common_idx.intersection(df.index)
    if len(common_idx) < 200:
        return []

    pair_returns = {p: df.loc[common_idx, "Close"].pct_change()
                    for p, df in pair_dfs.items()}
    strength = basket_strength(pair_returns)
    pct = {ccy: basket_strength_percentile(s, window=percentile_window)
           for ccy, s in strength.items()}

    results = []
    pip_map = {"USD_JPY": 0.01, "EUR_USD": 0.0001, "GBP_USD": 0.0001,
               "EUR_JPY": 0.01, "GBP_JPY": 0.01}

    for ccy, p_pct in pct.items():
        # When ccy is at top extreme → expect ccy weaken → SELL pairs where ccy is "pos"
        # When ccy at bottom extreme → expect ccy strengthen → BUY pairs where ccy is "pos"
        # We measure on ALL pairs touching this currency
        for pair in pairs:
            pos, neg = PAIR_MAP[pair]
            if ccy not in (pos, neg):
                continue
            df = pair_dfs[pair].loc[common_idx]
            pip = pip_map[pair]
            # Direction: when ccy at top, ccy weakens
            # Pair direction: pos↑ if ccy=neg gets weaker, pos↓ if ccy=pos gets weaker

            for fw in forward_bars_grid:
                events_top = p_pct[p_pct >= 1 - pct_extreme].index
                events_bot = p_pct[p_pct <= pct_extreme].index

                # Compute forward returns
                close = df["Close"]
                fwd = close.shift(-fw) / close - 1
                pip_ret = fwd / pip

                # Top extreme: ccy strong → ccy weakens
                # If ccy=pos (e.g. USD in USDJPY), pair direction = -1 (SELL)
                # If ccy=neg (e.g. JPY in USDJPY), pair direction = +1 (BUY, jpy weakens means usdjpy up)
                top_records = []
                for ev_ts in events_top:
                    if ev_ts not in pip_ret.index:
                        continue
                    r = pip_ret.loc[ev_ts]
                    if not np.isfinite(r):
                        continue
                    sign = -1 if pos == ccy else +1
                    top_records.append(sign * r)

                bot_records = []
                for ev_ts in events_bot:
                    if ev_ts not in pip_ret.index:
                        continue
                    r = pip_ret.loc[ev_ts]
                    if not np.isfinite(r):
                        continue
                    sign = +1 if pos == ccy else -1
                    bot_records.append(sign * r)

                all_records = top_records + bot_records
                if len(all_records) < 30:
                    continue

                arr = np.array(all_records)
                n = len(arr)
                wins = int((arr > 0).sum())
                wr = wins / n
                wlo, whi = _wilson(wins, n)
                p = _binom(wins, n, p=0.5)
                avg = float(arr.mean())
                sharpe = avg / (arr.std() + 1e-9) * math.sqrt(96 * 252)
                results.append({
                    "currency": ccy,
                    "pair": pair,
                    "forward_bars": fw,
                    "pct_extreme": pct_extreme,
                    "n": n,
                    "win_rate": round(wr, 4),
                    "wilson_lower": round(wlo, 4),
                    "wilson_upper": round(whi, 4),
                    "p_value": round(p, 6),
                    "avg_pip": round(avg, 3),
                    "sharpe": round(float(sharpe), 2),
                })
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--pct-extreme", type=float, default=0.05)
    p.add_argument("--forwards", type=int, nargs="+", default=[4, 8, 12])
    p.add_argument("--output", default="raw/csmr_audit/")
    args = p.parse_args()

    results = csmr_audit(days=args.days, pct_extreme=args.pct_extreme,
                         forward_bars_grid=args.forwards)
    if not results:
        print("Insufficient data for CS-MR audit.")
        return 1

    print(f"Total grid: {len(results)}", flush=True)
    n_tests = len(results)
    sig = []
    for r in results:
        r["p_bonf"] = round(r["p_value"] * n_tests, 5)
        if r["p_bonf"] < 0.05 and r["wilson_lower"] > 0.50:
            sig.append(r)
            print(f"  ✅ {r['currency']} on {r['pair']} fw={r['forward_bars']}: "
                  f"n={r['n']} WR={r['win_rate']:.3f} Wilson_lo={r['wilson_lower']:.3f} "
                  f"avg={r['avg_pip']:+.2f}p Sharpe={r['sharpe']:.1f} "
                  f"p_bonf={r['p_bonf']:.5f}", flush=True)

    print(f"Bonferroni-significant: {len(sig)}/{n_tests}")
    best = max(results, key=lambda x: x["sharpe"])
    print(f"Best Sharpe: {best['currency']} on {best['pair']} fw={best['forward_bars']} "
          f"WR={best['win_rate']:.3f} Sharpe={best['sharpe']:.1f}", flush=True)

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"csmr_audit_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump({"grid": results, "bonferroni_n": n_tests, "significant": sig},
                  f, indent=2, default=str)
    print(f"\nJSON: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
