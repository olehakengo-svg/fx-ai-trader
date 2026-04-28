"""Phase 8 Track C — Quantile-bucketed continuous feature scan.

Pre-registered LOCK: knowledge-base/wiki/decisions/pre-reg-phase8-track-c-2026-04-28.md

Hypothesis: 固定 threshold (Phase 7 / Track A) の bias を回避するため、
4 features を rolling 30d decile (P0..P10, P10..P20, ..., P90..P100) で bucketize し、
adaptive な edge を探索する。

Look-ahead 防止: 各 bar t の decile は、bar t を含む rolling 30d window 内での
percentile rank (backward-looking)。pandas rolling().rank(pct=True) を使用。

Stages run in this session: 1 (single-feature) + 2 (pairwise).
Stages 3 (stability) / 4 (holdout) are reserved for separate session.

Usage:
    python3 tools/phase8_track_c.py --stage 1 --output raw/phase8/track_c/
    python3 tools/phase8_track_c.py --stage 2 --input raw/phase8/track_c/stage1_decile_<ts>.json
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
    simulate_cell_trades, aggregate_trade_stats,
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

# Rolling decile window: 30 days × 96 bars/day = 2880 bars
DECILE_WINDOW_BARS = 2880
DECILE_MIN_PERIODS = 1440  # 15 days minimum
N_DECILES = 10

DECILE_FEATURES = [
    "bbpb_15m_decile",
    "rsi_15m_decile",
    "atr_pct_60d_decile",
    "recent_3bar_ret_decile",
]


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
# Data loading + decile feature pipeline
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


def _add_base_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add raw continuous features (BB%B, RSI, ATR percentile, 3-bar return)."""
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

    # ATR percentile rolling 60d (= 60 × 96 bars)
    df["atr_pct_60d"] = df["atr"].rolling(60 * 96, min_periods=2880).rank(pct=True)

    # Recent 3-bar log-return sum (momentum proxy)
    log_ret = np.log(closes / closes.shift(1))
    df["recent_3bar_ret"] = log_ret.rolling(3).sum()

    df["hour_utc"] = df.index.hour
    df["dow"] = df.index.dayofweek
    return df


def _to_decile(s: pd.Series) -> pd.Series:
    """Rolling 30d percentile rank → decile [0..9].

    Look-ahead-safe: rolling() in pandas は backward-looking。bar t の rank は
    [t - 2880 + 1, ..., t] window 内での current value の percentile。current
    value も既知 (bar t close 後) なので将来データ漏洩なし。
    """
    pct = s.rolling(DECILE_WINDOW_BARS, min_periods=DECILE_MIN_PERIODS).rank(pct=True)
    # decile = floor(pct × 10), clipped to [0, 9]
    decile = np.minimum(np.floor(pct * N_DECILES), N_DECILES - 1)
    out = pd.Series(decile, index=s.index, dtype="float64")
    return out


def _add_deciles(df: pd.DataFrame) -> pd.DataFrame:
    """Compute rolling 30d deciles for the 4 LOCK features."""
    df["bbpb_15m_decile"] = _to_decile(df["bbpb_15m"])
    df["rsi_15m_decile"] = _to_decile(df["rsi_15m"])
    df["atr_pct_60d_decile"] = _to_decile(df["atr_pct_60d"])
    df["recent_3bar_ret_decile"] = _to_decile(df["recent_3bar_ret"])
    # Cast to nullable int for clean groupby
    for c in DECILE_FEATURES:
        df[c] = df[c].astype("Int64")
    return df


def _prepare_pair(pair: str, days: int) -> pd.DataFrame | None:
    """Load + compute base features + deciles + holdout filter."""
    try:
        df = _load_pair(pair, days)
    except Exception as e:
        print(f"  load failed: {e}", flush=True)
        return None
    df = _add_atr(df)
    df = _add_base_features(df)
    df = _add_deciles(df)

    # Holdout reservation
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
    df = df[df.index < cutoff]

    # Drop rows where any decile is NA, weekday only
    df = df[df["dow"] <= 4]
    df = df.dropna(subset=["atr"] + DECILE_FEATURES)
    return df


# ─────────────────────────────────────────────────────────────
# Stage 1 — Single-feature decile scan
# ─────────────────────────────────────────────────────────────
def stage1_scan(
    days: int = TRAINING_DAYS_LOCK,
    pairs: list = None,
    forwards: list = None,
) -> dict:
    pairs = pairs or PAIRS_LOCK
    forwards = forwards or FORWARD_BARS_LOCK

    all_results = []
    boundary_log = []  # for Track A vs C comparison
    cell_counter = 0

    for pair in pairs:
        print(f"\n=== Stage 1 [decile] — {pair} ===", flush=True)
        df = _prepare_pair(pair, days)
        if df is None or len(df) < 1000:
            print(f"  insufficient bars: {0 if df is None else len(df)}", flush=True)
            continue
        print(f"  Training bars: {len(df)} (holdout reserved)", flush=True)

        # Boundary diagnostics: median P10 / P90 thresholds for each base feature
        # (compared with Track A固定 threshold)
        for fname, base_col in [
            ("bbpb_15m_decile", "bbpb_15m"),
            ("rsi_15m_decile", "rsi_15m"),
            ("atr_pct_60d_decile", "atr_pct_60d"),
            ("recent_3bar_ret_decile", "recent_3bar_ret"),
        ]:
            base = df[base_col].dropna()
            if len(base) > 0:
                boundary_log.append({
                    "pair": pair, "feature": fname, "base_col": base_col,
                    "p10_full": float(base.quantile(0.10)),
                    "p20_full": float(base.quantile(0.20)),
                    "p50_full": float(base.quantile(0.50)),
                    "p80_full": float(base.quantile(0.80)),
                    "p90_full": float(base.quantile(0.90)),
                })

        for feature in DECILE_FEATURES:
            buckets_all = sorted([b for b in df[feature].dropna().unique()])
            for bucket in buckets_all:
                bucket = int(bucket)
                mask = df[feature] == bucket
                if mask.sum() < 100:
                    continue
                bucket_idx = df.index[mask]
                signal_indices = [df.index.get_loc(t) for t in bucket_idx]

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
                        wlo = wilson_lower(stats["n_wins"], stats["n_trades"])
                        p = _binom(stats["n_wins"], stats["n_trades"], 0.5)
                        months = days / 30.0
                        per_month = stats["n_trades"] / months

                        all_results.append({
                            "stage": 1,
                            "pair": pair,
                            "feature": feature,
                            "decile": bucket,
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
    return {"results": all_results, "n_cells": cell_counter,
            "boundary_log": boundary_log}


def stage1_apply_gates(results: list, q: float = 0.10) -> list:
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
        if all(gates.values()):
            r["gates"] = gates
            survivors.append(r)
    return survivors


# ─────────────────────────────────────────────────────────────
# Stage 2 — Pairwise decile interaction
# ─────────────────────────────────────────────────────────────
def stage2_scan(
    survivors_stage1: list,
    days: int = TRAINING_DAYS_LOCK,
    pairs: list = None,
    forwards: list = None,
    top_n_features: int = 4,
) -> dict:
    pairs = pairs or PAIRS_LOCK
    forwards = forwards or FORWARD_BARS_LOCK

    feature_counts = {}
    for r in survivors_stage1:
        feature_counts[r["feature"]] = feature_counts.get(r["feature"], 0) + 1
    if feature_counts:
        top_features = sorted(feature_counts, key=lambda k: -feature_counts[k])[:top_n_features]
    else:
        # No survivors → fall back to all 4 deciles for pairwise scan (still
        # statistically valid given Bonferroni correction)
        top_features = list(DECILE_FEATURES)
    print(f"Pairwise feature pool: {top_features} (s1 counts={feature_counts})")

    if len(top_features) < 2:
        return {"results": [], "n_cells": 0, "top_features": top_features}

    from itertools import combinations
    pair_combos = list(combinations(top_features, 2))
    print(f"Pairwise combos: {pair_combos}")

    all_results = []
    cell_counter = 0
    for pair in pairs:
        print(f"\n=== Stage 2 [decile] — {pair} ===", flush=True)
        df = _prepare_pair(pair, days)
        if df is None or len(df) < 1000:
            continue

        for f1, f2 in pair_combos:
            buckets1 = sorted([int(b) for b in df[f1].dropna().unique()])
            buckets2 = sorted([int(b) for b in df[f2].dropna().unique()])
            for b1 in buckets1:
                for b2 in buckets2:
                    mask = (df[f1] == b1) & (df[f2] == b2)
                    if mask.sum() < 100:
                        continue
                    bucket_idx = df.index[mask]
                    signal_indices = [df.index.get_loc(t) for t in bucket_idx]

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
                            wlo = wilson_lower(stats["n_wins"], stats["n_trades"])
                            p = _binom(stats["n_wins"], stats["n_trades"], 0.5)
                            months = days / 30.0
                            per_month = stats["n_trades"] / months

                            all_results.append({
                                "stage": 2,
                                "pair": pair,
                                "feature1": f1, "decile1": b1,
                                "feature2": f2, "decile2": b2,
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

    return {"results": all_results, "n_cells": cell_counter,
            "top_features": top_features}


def stage2_apply_gates(results: list) -> list:
    if not results:
        return []
    n_tests = len(results)
    survivors = []
    for r in results:
        p_bonf = r["p_value"] * n_tests
        r["p_bonf"] = round(p_bonf, 5)
        gates = {
            "bonferroni": p_bonf < 0.05,
            "wilson_gt_50": r["wilson_lower"] > 0.50,
            "n_ge_100": r["n_trades"] >= 100,
            "ev_pos": r["ev_net_pip"] > 0,
            "capacity": r["trades_per_month"] >= 5,
            "sharpe_pos": (r["sharpe_per_event"] or 0) > 0.05,
        }
        if all(gates.values()):
            r["gates"] = gates
            survivors.append(r)
    return survivors


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=int, required=True, choices=[1, 2])
    p.add_argument("--days", type=int, default=TRAINING_DAYS_LOCK)
    p.add_argument("--pairs", nargs="+", default=PAIRS_LOCK)
    p.add_argument("--forwards", type=int, nargs="+", default=FORWARD_BARS_LOCK)
    p.add_argument("--output", default="raw/phase8/track_c/")
    p.add_argument("--input", default=None,
                   help="Stage 2: path to stage 1 JSON")
    p.add_argument("--bh-q", type=float, default=0.10)
    args = p.parse_args()

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    if args.stage == 1:
        print("=" * 60)
        print("  Track C Stage 1 — Decile Scan (BH-FDR primary)")
        print(f"  Pairs: {args.pairs} | Days: {args.days}")
        print(f"  Holdout reserved: last {HOLDOUT_DAYS_LOCK}d")
        print(f"  Decile window: {DECILE_WINDOW_BARS} bars (~30d)")
        print("=" * 60)
        scan = stage1_scan(days=args.days, pairs=args.pairs,
                           forwards=args.forwards)
        survivors = stage1_apply_gates(scan["results"], q=args.bh_q)
        print(f"\n=== Stage 1 [decile] Verdict ===")
        print(f"Total cells: {scan['n_cells']}")
        print(f"Survivors (BH-FDR q={args.bh_q} + all gates): {len(survivors)}")
        if survivors:
            print(f"\nTop 20 by EV_net_pip:")
            top = sorted(survivors, key=lambda x: -x["ev_net_pip"])[:20]
            for r in top:
                print(f"  {r['pair']} {r['direction']} {r['feature']}=D{r['decile']} "
                      f"fw={r['forward_bars']}: n={r['n_trades']} WR={r['wr']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} EV={r['ev_net_pip']:+.2f}p "
                      f"Sharpe_pe={r['sharpe_per_event']:.3f}")

        out = {
            "stage": 1,
            "track": "C_decile",
            "params": {
                "days": args.days, "pairs": args.pairs,
                "forwards": args.forwards, "bh_q": args.bh_q,
                "holdout_days": HOLDOUT_DAYS_LOCK,
                "sl_atr": SL_ATR_MULT_LOCK, "tp_atr": TP_ATR_MULT_LOCK,
                "decile_window_bars": DECILE_WINDOW_BARS,
                "decile_min_periods": DECILE_MIN_PERIODS,
                "n_deciles": N_DECILES,
            },
            "n_cells_total": scan["n_cells"],
            "n_survivors": len(survivors),
            "boundary_log": scan["boundary_log"],
            "all_results": scan["results"],
            "survivors": survivors,
        }
        json_path = out_dir / f"stage1_decile_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")
        return 0

    elif args.stage == 2:
        print("=" * 60)
        print("  Track C Stage 2 — Pairwise Decile (Bonferroni primary)")
        print("=" * 60)
        if not args.input:
            print("ERROR: --input <stage1.json> required", file=sys.stderr)
            return 1
        with open(args.input) as f:
            stage1 = json.load(f)
        survivors_s1 = stage1.get("survivors", [])
        scan = stage2_scan(survivors_s1, days=args.days,
                           pairs=args.pairs, forwards=args.forwards)
        survivors = stage2_apply_gates(scan["results"])
        print(f"\n=== Stage 2 [decile] Verdict ===")
        print(f"Total cells: {scan['n_cells']}")
        print(f"Survivors (Bonferroni + all gates): {len(survivors)}")
        if survivors:
            print(f"\nTop 20 by EV_net_pip:")
            top = sorted(survivors, key=lambda x: -x["ev_net_pip"])[:20]
            for r in top:
                print(f"  {r['pair']} {r['direction']} "
                      f"{r['feature1']}=D{r['decile1']} × "
                      f"{r['feature2']}=D{r['decile2']} fw={r['forward_bars']}: "
                      f"n={r['n_trades']} WR={r['wr']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} EV={r['ev_net_pip']:+.2f}p "
                      f"Sharpe_pe={r['sharpe_per_event']:.3f}")

        out = {
            "stage": 2,
            "track": "C_decile",
            "params": {"days": args.days, "pairs": args.pairs,
                       "forwards": args.forwards},
            "top_features": scan["top_features"],
            "n_cells_total": scan["n_cells"],
            "n_survivors": len(survivors),
            "all_results": scan["results"],
            "survivors": survivors,
        }
        json_path = out_dir / f"stage2_decile_pair_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
