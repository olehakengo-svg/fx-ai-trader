"""VDR Audit — VWAP Deviation Reversion (institutional benchmark anchor).

仮説 (Madhavan-Smidt 1991, Almgren-Chriss 2001):
  機関投資家は VWAP benchmark で執行 evaluation。Daily VWAP からの
  ±2.0σ 乖離は機関的 mean-reversion 圧力で収束する典型。

監査構成:
  1. Daily session VWAP からの z-score 計算 (per pair)
  2. |z| > {1.5, 2.0, 2.5} で event 化、forward {2,4,6,8} bar の VWAP 復帰測定
  3. Bonferroni 補正 (3 σ × 4 forward × 5 pair = 60 tests)
  4. Quarterly stability check
  5. Trade-outcome simulation (SL/TP + 1.5 pip friction)

Output: raw/vdr_audit/vdr_audit_{date}.md
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


def _wilson(wins: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, c - h), min(1.0, c + h))


PAIRS = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]
FRICTION_PIP = 1.5


def _load(pair: str, days: int) -> pd.DataFrame:
    from tools.bt_data_cache import BTDataCache
    cache = BTDataCache()
    df = cache.get(pair, "15m", days=days)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    df = df[df.index >= cutoff].copy()

    # Compute ATR
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    c = df["Close"].astype(float)
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()],
                   axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()

    # Daily session VWAP if not present (rebuild per UTC day)
    if "vwap" not in df.columns:
        df["date"] = df.index.date
        df["tpv"] = ((df["High"] + df["Low"] + df["Close"]) / 3) * df["Volume"]
        df["vwap"] = (df.groupby("date")["tpv"].cumsum()
                      / df.groupby("date")["Volume"].cumsum())
        df = df.drop(columns=["tpv"])
    else:
        # Existing vwap may be cumulative — recompute daily for consistency
        pass

    return df.dropna(subset=["atr", "vwap"])


def vdr_event_outcome(df: pd.DataFrame, pair: str, sigma: float,
                       forward_bars: int) -> dict:
    """Detect |z(close - vwap)/atr| > sigma events; forward VWAP convergence."""
    pip = 0.01 if "JPY" in pair else 0.0001
    df = df.copy()
    df["dev"] = (df["Close"] - df["vwap"])
    df["dev_atr"] = df["dev"] / df["atr"]

    events = df[df["dev_atr"].abs() > sigma].copy()
    if len(events) < 10:
        return {"n": int(len(events)), "insufficient": True}

    # Forward outcome: did price move TOWARD VWAP within forward_bars?
    # Signed return: -sign(dev) × forward_close_change (positive = moved toward VWAP)
    events["fwd_close"] = df["Close"].shift(-forward_bars).reindex(events.index)
    events["signed_fwd_pip"] = (
        -np.sign(events["dev"]) * (events["fwd_close"] - events["Close"]) / pip
    )
    events = events.dropna(subset=["signed_fwd_pip"])
    if len(events) < 10:
        return {"n": int(len(events)), "insufficient": True}

    rets = events["signed_fwd_pip"].values
    n = len(events)
    n_wins = int((rets > 0).sum())
    win_rate = n_wins / n
    wlo, whi = _wilson(n_wins, n)
    p_value = _binom(n_wins, n, p=0.5)
    avg_pip = float(np.mean(rets))
    sharpe = avg_pip / (np.std(rets) + 1e-9) * math.sqrt(96 * 252)
    return {
        "pair": pair,
        "sigma": sigma,
        "forward_bars": forward_bars,
        "n": n,
        "win_rate": round(win_rate, 4),
        "wilson_lower": round(wlo, 4),
        "wilson_upper": round(whi, 4),
        "p_value": round(p_value, 6),
        "avg_pip": round(avg_pip, 3),
        "sharpe": round(float(sharpe), 2),
    }


def trade_sim(df: pd.DataFrame, pair: str, sigma: float,
               forward_bars: int) -> dict:
    """Hypothetical trade: SL = 1 ATR, TP = VWAP, friction 1.5 pip."""
    pip = 0.01 if "JPY" in pair else 0.0001
    df = df.copy()
    df["dev"] = df["Close"] - df["vwap"]
    df["dev_atr"] = df["dev"] / df["atr"]
    events = df[df["dev_atr"].abs() > sigma].copy()
    if len(events) < 10:
        return {}

    pnls = []
    for idx, row in events.iterrows():
        loc = df.index.get_loc(idx)
        if loc + forward_bars >= len(df):
            continue
        entry = float(row["Close"])
        atr = float(row["atr"])
        signal = -np.sign(row["dev"])  # toward VWAP
        if signal == 0:
            continue
        sl = entry - signal * atr
        tp = float(row["vwap"])
        if (signal > 0 and tp <= entry) or (signal < 0 and tp >= entry):
            continue
        outcome = "TIMEOUT"
        exit_price = None
        for j in range(loc + 1, min(loc + 1 + forward_bars, len(df))):
            bar = df.iloc[j]
            bh = float(bar["High"])
            bl = float(bar["Low"])
            if signal > 0:
                if bl <= sl:
                    outcome, exit_price = "SL", sl; break
                if bh >= tp:
                    outcome, exit_price = "TP", tp; break
            else:
                if bh >= sl:
                    outcome, exit_price = "SL", sl; break
                if bl <= tp:
                    outcome, exit_price = "TP", tp; break
        if exit_price is None:
            exit_price = float(df.iloc[min(loc + forward_bars,
                                            len(df) - 1)]["Close"])
        pnl_gross = signal * (exit_price - entry) / pip
        pnl_net = pnl_gross - FRICTION_PIP
        pnls.append(pnl_net)

    if not pnls:
        return {}
    arr = np.array(pnls)
    n = len(arr)
    wins = arr[arr > 0]
    losses = arr[arr < 0]
    pf = (sum(wins) / abs(sum(losses))) if len(losses) > 0 else float("inf")
    if len(wins) and len(losses):
        b = np.mean(wins) / abs(np.mean(losses))
        p = len(wins) / n
        kelly = (p * b - (1 - p)) / b if b > 0 else 0
    else:
        kelly = None
    return {
        "n_trades": n,
        "trade_wr": round(float((arr > 0).mean()), 4),
        "ev_pip_net": round(float(arr.mean()), 3),
        "pf": round(pf, 3) if pf != float("inf") else None,
        "kelly": round(kelly, 4) if kelly is not None else None,
    }


def quarterly(df: pd.DataFrame, pair: str, sigma: float,
              forward_bars: int) -> dict:
    n = len(df)
    qs = [df.iloc[i * n // 4: (i + 1) * n // 4] for i in range(4)]
    wrs = []
    for q in qs:
        if len(q) < 200:
            continue
        r = vdr_event_outcome(q, pair, sigma, forward_bars)
        if "win_rate" in r:
            wrs.append(r["win_rate"])
    return {
        "wrs": [round(w, 3) for w in wrs],
        "wr_std": round(float(np.std(wrs)), 4) if len(wrs) >= 2 else None,
        "all_above_bev": all(w > 0.5 for w in wrs) if wrs else False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pairs", nargs="+", default=PAIRS)
    p.add_argument("--days", type=int, default=365)
    p.add_argument("--sigmas", type=float, nargs="+",
                   default=[1.5, 2.0, 2.5])
    p.add_argument("--forwards", type=int, nargs="+", default=[2, 4, 6, 8])
    p.add_argument("--output", default="raw/vdr_audit/")
    args = p.parse_args()

    grid = []
    for pair in args.pairs:
        print(f"=== VDR {pair} ===", flush=True)
        try:
            df = _load(pair, args.days)
            print(f"  Loaded {len(df)} bars", flush=True)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            continue
        for sg in args.sigmas:
            for fw in args.forwards:
                r = vdr_event_outcome(df, pair, sg, fw)
                if "insufficient" in r:
                    continue
                grid.append(r)
                print(f"  σ={sg} fw={fw}: n={r['n']} WR={r['win_rate']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} avg_pip={r['avg_pip']:+.2f} "
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
            print(f"  ✅ {r['pair']} σ={r['sigma']} fw={r['forward_bars']} "
                  f"p_bonf={r['p_bonf']:.5f}", flush=True)

    if sig:
        best = max(sig, key=lambda x: x["sharpe"])
        print(f"\n--- Best (Bonferroni-passing) ---", flush=True)
        print(f"  {best['pair']} σ={best['sigma']} fw={best['forward_bars']}: "
              f"WR={best['win_rate']:.3f} Sharpe={best['sharpe']:.1f}",
              flush=True)
    elif grid:
        best = max(grid, key=lambda x: x["sharpe"])
        print(f"\n--- Best (no Bonferroni-significant; Sharpe leader) ---", flush=True)
        print(f"  {best['pair']} σ={best['sigma']} fw={best['forward_bars']}: "
              f"WR={best['win_rate']:.3f} Sharpe={best['sharpe']:.1f}",
              flush=True)
    else:
        print("No valid combinations.")
        return 1

    # Trade sim + quarterly for best
    df_best = _load(best["pair"], args.days)
    trade = trade_sim(df_best, best["pair"], best["sigma"],
                       best["forward_bars"])
    if trade:
        print(f"\n  Trade sim: n={trade['n_trades']} WR={trade['trade_wr']:.3f} "
              f"EV={trade['ev_pip_net']:+.2f}p PF={trade['pf']} Kelly={trade['kelly']}",
              flush=True)
    qs = quarterly(df_best, best["pair"], best["sigma"], best["forward_bars"])
    if qs:
        print(f"  Quarterly WRs: {qs.get('wrs')} std={qs.get('wr_std')} "
              f"all_above_BEV={qs.get('all_above_bev')}", flush=True)

    # Save
    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    json_path = out_dir / f"vdr_audit_{date_tag}.json"
    md_path = out_dir / f"vdr_audit_{date_tag}.md"

    with open(json_path, "w") as f:
        json.dump({
            "grid": grid, "bonferroni_n": n_tests,
            "best": best, "trade_sim": trade, "quarterly": qs,
        }, f, indent=2, default=str)

    md = ["# VDR Audit (VWAP Deviation Reversion)", ""]
    md.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"Days: {args.days}, Bonferroni N={n_tests}")
    md.append("")
    md.append("## Event grid")
    md.append("| pair | σ | fw | n | WR | Wilson_lo | avg_pip | Sharpe | p_raw | p_bonf |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in grid:
        md.append(f"| {r['pair']} | {r['sigma']} | {r['forward_bars']} | "
                  f"{r['n']} | {r['win_rate']:.3f} | {r['wilson_lower']:.3f} | "
                  f"{r['avg_pip']:+.2f} | {r['sharpe']:.1f} | "
                  f"{r['p_value']:.5f} | {r['p_bonf']:.5f} |")
    md.append("")
    md.append("## Best")
    md.append(f"- {best['pair']} σ={best['sigma']} fw={best['forward_bars']}")
    md.append(f"- n={best['n']} WR={best['win_rate']:.3f} Sharpe={best['sharpe']:.1f}")
    if trade:
        md.append(f"- Trade: WR={trade['trade_wr']:.3f} EV={trade['ev_pip_net']:+.2f}p "
                  f"PF={trade['pf']} Kelly={trade['kelly']}")
    if qs:
        md.append(f"- Quarterly WRs: {qs.get('wrs')} std={qs.get('wr_std')}")

    with open(md_path, "w") as f:
        f.write("\n".join(md))
    print(f"\nJSON: {json_path}\nMD: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
