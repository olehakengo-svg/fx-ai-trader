"""Pattern Discovery Engine — Phase 7 bottom-up empirical edge mining.

Pre-registered LOCK: knowledge-base/wiki/decisions/pre-reg-pattern-discovery-2026-04-28.md

Stages:
  0: Pre-registration (separate doc, already committed)
  1: Single-feature scan (BH-FDR primary)
  2: Pairwise interaction (Bonferroni primary)
  3: Stability + Chow + WF
  4: True OOS (holdout 90d + live shadow)
  5: Strategy generation (manual review post Stage 4)

Usage:
    python3 tools/pattern_discovery.py --stage 1 --days 275 --output raw/pattern_discovery/
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

try:
    from scipy.stats import binomtest as _bt
    def _binom(k, n, p):
        return _bt(k=k, n=n, p=p, alternative="two-sided").pvalue
except ImportError:
    from scipy.stats import binom_test as _bt
    def _binom(k, n, p):
        return _bt(k, n, p, alternative="two-sided")

from tools.lib.trade_sim import (
    simulate_cell_trades, aggregate_trade_stats, pip_size,
    session_for_utc_hour,
)


# ─────────────────────────────────────────────────────────────
# Pre-registered LOCK (must match pre-reg doc)
# ─────────────────────────────────────────────────────────────
PAIRS_LOCK = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]
DIRECTIONS_LOCK = ["BUY", "SELL"]
FORWARD_BARS_LOCK = [4, 8, 12]
HOLDOUT_DAYS_LOCK = 90
TRAINING_DAYS_LOCK = 275
SL_ATR_MULT_LOCK = 1.0
TP_ATR_MULT_LOCK = 1.5

FEATURE_AXES_LOCK = {
    "hour_utc":    list(range(24)),
    "dow":         [0, 1, 2, 3, 4],
    "bbpb_15m":    [0, 1, 2, 3, 4],
    "rsi_15m":     [0, 1, 2, 3],
    "bbpb_1h":     [0, 1, 2, 3, 4],
    "atr_pct_60d": [0, 1, 2],
    "recent_3bar": [-1, 0, 1],
}


# ─────────────────────────────────────────────────────────────
# Statistics helpers
# ─────────────────────────────────────────────────────────────
def wilson_lower(wins: int, n: int, alpha: float = 0.05) -> float:
    if n == 0:
        return 0.0
    z = 1.959963984540054
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return max(0.0, c - h)


def benjamini_hochberg(p_values: list, q: float = 0.10) -> list:
    """Return list of bool (True = significant after BH correction)."""
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    rejected = [False] * n
    for rank_i, (orig_i, p) in enumerate(indexed, start=1):
        threshold = (rank_i / n) * q
        if p <= threshold:
            for k in range(rank_i):
                rejected[indexed[k][0]] = True
    return rejected


# ─────────────────────────────────────────────────────────────
# Data loading + indicator pipeline
# ─────────────────────────────────────────────────────────────
def _load_pair(pair: str, days: int) -> pd.DataFrame:
    from tools.bt_data_cache import BTDataCache
    cache = BTDataCache()
    df = cache.get(pair, "15m", days=days)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    return df[df.index >= cutoff].copy()


def _add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    h, l, c = df["High"].astype(float), df["Low"].astype(float), df["Close"].astype(float)
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()],
                   axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / period, adjust=False).mean()
    return df


def _add_bbpb_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """Add 15m BB%B and RSI."""
    closes = df["Close"].astype(float)
    sma = closes.rolling(20).mean()
    sd = closes.rolling(20).std()
    upper = sma + 2 * sd
    lower = sma - 2 * sd
    df["bbpb_15m"] = (closes - lower) / (upper - lower).replace(0, np.nan)

    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-12)
    df["rsi_15m"] = 100 - 100 / (1 + rs)
    return df


def _add_1h_aggregated(df: pd.DataFrame) -> pd.DataFrame:
    """Add 1h aggregated BB%B (and align to 15m index, look-ahead-safe)."""
    n_full = (len(df) // 4) * 4
    df_h = df.iloc[-n_full:].copy()
    df_h["bucket"] = np.arange(len(df_h)) // 4
    h1 = df_h.groupby("bucket").agg({"Close": "last"})
    h1_sma = h1["Close"].rolling(20).mean()
    h1_sd = h1["Close"].rolling(20).std()
    h1_upper = h1_sma + 2 * h1_sd
    h1_lower = h1_sma - 2 * h1_sd
    h1["bbpb_1h"] = (h1["Close"] - h1_lower) / (h1_upper - h1_lower).replace(0, np.nan)

    bbpb_1h_full = np.full(len(df), np.nan)
    offset = len(df) - n_full
    # Look-ahead 防止: bucket b の bbpb_1h は bucket b+1 開始以降に使用可
    for b in range(len(h1) - 1):
        s = offset + (b + 1) * 4   # next bucket start
        e = offset + (b + 2) * 4
        if s >= len(df):
            break
        if e > len(df):
            e = len(df)
        bbpb_1h_full[s:e] = h1["bbpb_1h"].iloc[b]
    df["bbpb_1h"] = bbpb_1h_full
    return df


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all feature transformations + bucketization (LOCK 準拠)."""
    df = _add_atr(df)
    df = _add_bbpb_rsi(df)
    df = _add_1h_aggregated(df)

    # ATR percentile (60d rolling)
    df["atr_pct_60d"] = df["atr"].rolling(60 * 96).rank(pct=True)  # 60d × 96 bars/day

    # Recent 3-bar direction
    closes = df["Close"]
    delta = closes.diff()
    df["recent_3bar_raw"] = np.sign(delta).rolling(3).sum()

    # Time features
    df["hour_utc"] = df.index.hour
    df["dow"] = df.index.dayofweek

    # Bucketize
    df["bbpb_15m_b"] = pd.cut(
        df["bbpb_15m"], bins=[-np.inf, 0.2, 0.4, 0.6, 0.8, np.inf],
        labels=[0, 1, 2, 3, 4],
    ).astype("Int64")
    df["rsi_15m_b"] = pd.cut(
        df["rsi_15m"], bins=[-np.inf, 30, 50, 70, np.inf],
        labels=[0, 1, 2, 3],
    ).astype("Int64")
    df["bbpb_1h_b"] = pd.cut(
        df["bbpb_1h"], bins=[-np.inf, 0.2, 0.4, 0.6, 0.8, np.inf],
        labels=[0, 1, 2, 3, 4],
    ).astype("Int64")
    df["atr_pct_60d_b"] = pd.cut(
        df["atr_pct_60d"], bins=[-np.inf, 1/3, 2/3, np.inf],
        labels=[0, 1, 2],
    ).astype("Int64")
    df["recent_3bar_b"] = df["recent_3bar_raw"].apply(
        lambda x: -1 if x is np.nan or x is None or pd.isna(x) else
                  (-1 if x < -1 else (1 if x > 1 else 0))
    )

    # Filter weekday only (dow 0-4)
    df = df[df["dow"] <= 4]
    return df


# ─────────────────────────────────────────────────────────────
# Stage 1 — Single-feature scan
# ─────────────────────────────────────────────────────────────
SINGLE_FEATURE_AXES = ["hour_utc", "dow", "bbpb_15m_b", "rsi_15m_b",
                       "bbpb_1h_b", "atr_pct_60d_b", "recent_3bar_b"]


def stage1_single_feature_scan(
    days: int = TRAINING_DAYS_LOCK,
    pairs: list = None,
    forwards: list = None,
) -> dict:
    """Stage 1: each (pair, feature, direction, forward, bucket) cell の audit。"""
    pairs = pairs or PAIRS_LOCK
    forwards = forwards or FORWARD_BARS_LOCK

    all_results = []
    cell_counter = 0
    for pair in pairs:
        print(f"\n=== Stage 1 — {pair} ===", flush=True)
        try:
            df = _load_pair(pair, days)
        except Exception as e:
            print(f"  load failed: {e}", flush=True)
            continue

        # Holdout reservation (do NOT touch most recent HOLDOUT_DAYS_LOCK)
        cutoff_holdout = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
        df = df[df.index < cutoff_holdout]

        df = _add_features(df).dropna(subset=["atr", "bbpb_15m", "rsi_15m"])
        if len(df) < 1000:
            print(f"  insufficient bars after holdout: {len(df)}", flush=True)
            continue
        print(f"  Training bars: {len(df)} (holdout reserved)", flush=True)

        for feature in SINGLE_FEATURE_AXES:
            if feature not in df.columns:
                continue
            # Drop NA in this feature column for comparisons
            feature_series = df[feature].dropna()
            buckets = feature_series.unique()
            for bucket in buckets:
                # Use index match to avoid NA issues
                bucket_idx = feature_series[feature_series == bucket].index
                signal_indices = [df.index.get_loc(t) for t in bucket_idx]
                if len(signal_indices) < 100:
                    continue   # capacity gate

                for direction in DIRECTIONS_LOCK:
                    for fw in forwards:
                        trades = simulate_cell_trades(
                            df, signal_indices, direction,
                            atr_series=df["atr"],
                            sl_atr_mult=SL_ATR_MULT_LOCK,
                            tp_atr_mult=TP_ATR_MULT_LOCK,
                            max_hold_bars=fw, pair=pair, dedup=True,
                        )
                        stats = aggregate_trade_stats(trades)
                        if stats["n_trades"] < 100:
                            continue
                        # Per-bar p-value
                        wlo = wilson_lower(stats["n_wins"], stats["n_trades"])
                        p = _binom(stats["n_wins"], stats["n_trades"], 0.5)

                        # Capacity: trades per month (training period)
                        months = days / 30.0
                        per_month = stats["n_trades"] / months

                        all_results.append({
                            "stage": 1,
                            "pair": pair,
                            "feature": feature,
                            "bucket": int(bucket) if bucket is not pd.NA else -99,
                            "direction": direction,
                            "forward_bars": fw,
                            "n_trades": stats["n_trades"],
                            "wr": stats["wr"],
                            "wilson_lower": round(wlo, 4),
                            "ev_net_pip": stats["ev_net_pip"],
                            "pf": stats["pf"],
                            "kelly": stats["kelly"],
                            "sharpe_per_event": stats["sharpe_per_event"],
                            "trades_per_month": round(per_month, 1),
                            "p_value": round(float(p), 6),
                        })
                        cell_counter += 1

    print(f"\nTotal cells generated: {cell_counter}")
    return {"results": all_results, "n_cells": cell_counter}


# ─────────────────────────────────────────────────────────────
# Stage 1 gate filter
# ─────────────────────────────────────────────────────────────
def stage1_apply_gates(results: list, q: float = 0.10) -> list:
    """Apply BH-FDR + capacity + EV gates."""
    if not results:
        return []
    p_values = [r["p_value"] for r in results]
    bh_sig = benjamini_hochberg(p_values, q=q)
    survivors = []
    for r, sig in zip(results, bh_sig):
        gates = {
            "bh_fdr": sig,
            "wilson_gt_50": r["wilson_lower"] > 0.50,
            "n_ge_100": r["n_trades"] >= 100,
            "ev_pos": r["ev_net_pip"] > 0,
            "capacity": r["trades_per_month"] >= 5,
            "sharpe_pos": (r["sharpe_per_event"] or 0) > 0.05,
        }
        all_pass = all(gates.values())
        if all_pass:
            r["gates"] = gates
            survivors.append(r)
    return survivors


# ─────────────────────────────────────────────────────────────
# Main CLI
# ─────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=int, required=True, choices=[1, 2, 3, 4])
    p.add_argument("--days", type=int, default=TRAINING_DAYS_LOCK)
    p.add_argument("--pairs", nargs="+", default=PAIRS_LOCK)
    p.add_argument("--forwards", type=int, nargs="+", default=FORWARD_BARS_LOCK)
    p.add_argument("--output", default="raw/pattern_discovery/")
    p.add_argument("--input", default=None,
                   help="JSON path (Stage 2-4 で前 stage 出力を読み込み)")
    p.add_argument("--bh-q", type=float, default=0.10)
    args = p.parse_args()

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    if args.stage == 1:
        print("=" * 60)
        print("  Stage 1 — Single-Feature Scan (BH-FDR primary)")
        print(f"  Pairs: {args.pairs} | Days: {args.days} (training only)")
        print(f"  Holdout reserved: last {HOLDOUT_DAYS_LOCK} days")
        print("=" * 60)
        scan = stage1_single_feature_scan(
            days=args.days, pairs=args.pairs, forwards=args.forwards,
        )
        survivors = stage1_apply_gates(scan["results"], q=args.bh_q)
        print(f"\n=== Stage 1 Verdict ===")
        print(f"Total cells: {scan['n_cells']}")
        print(f"Survivors (all gates pass + BH-FDR q={args.bh_q}): {len(survivors)}")
        if survivors:
            print(f"\nTop 20 by EV_net_pip:")
            top = sorted(survivors, key=lambda x: -x["ev_net_pip"])[:20]
            for r in top:
                print(f"  {r['pair']} {r['direction']} {r['feature']}={r['bucket']} "
                      f"fw={r['forward_bars']}: n={r['n_trades']} WR={r['wr']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} EV={r['ev_net_pip']:+.2f}p "
                      f"Sharpe_pe={r['sharpe_per_event']:.3f}")

        out = {
            "stage": 1,
            "params": {
                "days": args.days, "pairs": args.pairs,
                "forwards": args.forwards, "bh_q": args.bh_q,
                "holdout_days": HOLDOUT_DAYS_LOCK,
                "sl_atr": SL_ATR_MULT_LOCK, "tp_atr": TP_ATR_MULT_LOCK,
            },
            "n_cells_total": scan["n_cells"],
            "n_survivors": len(survivors),
            "all_results": scan["results"],
            "survivors": survivors,
        }
        json_path = out_dir / f"stage1_single_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")
        return 0

    elif args.stage == 2:
        print("Stage 2 not yet implemented in this script — TODO")
        return 1
    elif args.stage == 3:
        print("Stage 3 not yet implemented — TODO")
        return 1
    elif args.stage == 4:
        print("Stage 4 not yet implemented — TODO")
        return 1


if __name__ == "__main__":
    sys.exit(main())
