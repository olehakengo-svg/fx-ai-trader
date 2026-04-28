"""Phase 8 Track B — Micro-Sequence Pattern Discovery.

Pre-registered LOCK: knowledge-base/wiki/decisions/pre-reg-phase8-track-b-2026-04-28.md

5 sequence-encoded pattern families (3-5 bar OHLC):
  P1 dir_seq_3      27 patterns  (close-open sign triplet)
  P2 engulf_seq      8 patterns  (engulf indicators × dir(t))
  P3 wick_dom_seq   27 patterns  (dominant wick state triplet)
  P4 mom_exhaust_5   2 patterns  (5 consecutive same-dir bars)
  P5 in_out_3        9 patterns  (inside/outside bar 2-state)

Stages:
  1: Training scan 275d (BH-FDR + N≥50 + Wilson_lo>0.50 + EV>0)
  2: Holdout OOS 90d (WR>0.50, EV>0)

Usage:
    python3 tools/phase8_track_b.py --stage 1
    python3 tools/phase8_track_b.py --stage 2 --input raw/phase8/track_b/stage1_<tag>.json
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

from tools.lib.trade_sim import simulate_cell_trades, aggregate_trade_stats


# ─────────────────────────────────────────────────────────────
# Pre-registered LOCK
# ─────────────────────────────────────────────────────────────
PAIRS_LOCK = ["USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY"]
DIRECTIONS_LOCK = ["BUY", "SELL"]
FORWARD_BARS_LOCK = [4, 8, 12]
HOLDOUT_DAYS_LOCK = 90
TRAINING_DAYS_LOCK = 275
SL_ATR_MULT_LOCK = 1.0
TP_ATR_MULT_LOCK = 1.5
N_MIN_LOCK = 50
WILSON_LOWER_MIN = 0.50
BH_FDR_Q_LOCK = 0.10

PATTERN_KINDS = ["dir_seq_3", "engulf_seq", "wick_dom_seq",
                 "mom_exhaust_5", "in_out_3"]


# ─────────────────────────────────────────────────────────────
# Statistics helpers (inlined for minimal coupling)
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
# Data loading + ATR
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


# ─────────────────────────────────────────────────────────────
# Pattern encoders — return Series of pattern label, aligned to bar(t)
# Look-ahead-safe: only use bar(t-k..t) close-confirmed values; entry is bar(t+1).Open via simulate_cell_trades
# ─────────────────────────────────────────────────────────────
def encode_dir_seq_3(df: pd.DataFrame, eps: float = 0.05) -> pd.Series:
    """27-state triplet of close-open sign (with eps × ATR dead zone)."""
    body = df["Close"].astype(float) - df["Open"].astype(float)
    atr = df["atr"].astype(float)
    threshold = eps * atr
    sign = pd.Series(0, index=df.index, dtype="int8")
    sign[body > threshold] = 1
    sign[body < -threshold] = -1
    s2 = sign.shift(2)
    s1 = sign.shift(1)
    s0 = sign
    label = s2.astype("Int64").astype(str) + "|" + \
            s1.astype("Int64").astype(str) + "|" + s0.astype("Int64").astype(str)
    label[s2.isna() | s1.isna()] = pd.NA
    return label


def encode_engulf_seq(df: pd.DataFrame) -> pd.Series:
    """8-state: (engulf(t-1, t-2), engulf(t, t-1), dir(t))."""
    o = df["Open"].astype(float)
    c = df["Close"].astype(float)
    atr = df["atr"].astype(float)
    body_top = np.maximum(o, c)
    body_bot = np.minimum(o, c)
    real_body = (c - o).abs() > 0.1 * atr

    eng_curr = ((body_top >= body_top.shift(1)) &
                (body_bot <= body_bot.shift(1)) & real_body).astype("Int64")
    eng_prev = ((body_top.shift(1) >= body_top.shift(2)) &
                (body_bot.shift(1) <= body_bot.shift(2)) &
                real_body.shift(1)).astype("Int64")
    dir_t = (c >= o).astype("Int64")  # +1 (bullish) / 0 (bearish)
    label = eng_prev.astype(str) + "|" + eng_curr.astype(str) + "|" + dir_t.astype(str)
    label[eng_prev.isna() | eng_curr.isna()] = pd.NA
    return label


def encode_wick_dom_seq(df: pd.DataFrame) -> pd.Series:
    """27-state: dominant wick state triplet (U/L/N)."""
    o = df["Open"].astype(float)
    c = df["Close"].astype(float)
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    atr = df["atr"].astype(float)
    body_top = np.maximum(o, c)
    body_bot = np.minimum(o, c)
    upper = h - body_top
    lower = body_bot - l
    denom = np.maximum((c - o).abs(), 0.1 * atr)
    ratio = (upper - lower) / denom

    state = pd.Series("N", index=df.index, dtype=object)
    state[ratio > 0.5] = "U"
    state[ratio < -0.5] = "L"
    s2 = state.shift(2)
    s1 = state.shift(1)
    label = s2.astype(str) + "|" + s1.astype(str) + "|" + state.astype(str)
    # NaN propagation: when shifts hit NaN, str will be 'nan'
    label[(s2.isna()) | (s1.isna())] = pd.NA
    # Also drop the first 2 rows explicitly
    label.iloc[:2] = pd.NA
    return label


def encode_mom_exhaust_5(df: pd.DataFrame) -> pd.Series:
    """2-state: 5 consecutive same-direction bars (UP5 / DN5)."""
    body = df["Close"].astype(float) - df["Open"].astype(float)
    up = (body > 0).astype(int)
    dn = (body < 0).astype(int)
    up5 = up.rolling(5).sum() == 5
    dn5 = dn.rolling(5).sum() == 5
    label = pd.Series(pd.NA, index=df.index, dtype=object)
    label[up5] = "UP5"
    label[dn5] = "DN5"
    return label


def encode_in_out_3(df: pd.DataFrame) -> pd.Series:
    """9-state: (state(t-1), state(t)) with state in {IN, OUT, NORM}."""
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    inside = (h <= h.shift(1)) & (l >= l.shift(1))
    outside = (h >= h.shift(1)) & (l <= l.shift(1))
    state = pd.Series("NORM", index=df.index, dtype=object)
    state[inside] = "IN"
    state[outside] = "OUT"
    label = state.shift(1).astype(str) + "|" + state.astype(str)
    # First row has NaN shift
    label.iloc[0] = pd.NA
    return label


PATTERN_ENCODERS = {
    "dir_seq_3": encode_dir_seq_3,
    "engulf_seq": encode_engulf_seq,
    "wick_dom_seq": encode_wick_dom_seq,
    "mom_exhaust_5": encode_mom_exhaust_5,
    "in_out_3": encode_in_out_3,
}


def add_all_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all 5 pattern columns. Caller ensures _add_atr was called."""
    for name, fn in PATTERN_ENCODERS.items():
        df[f"pat_{name}"] = fn(df)
    return df


# ─────────────────────────────────────────────────────────────
# Stage 1 — Training scan
# ─────────────────────────────────────────────────────────────
def stage1_pattern_scan(
    days: int = TRAINING_DAYS_LOCK,
    pairs: list = None,
    forwards: list = None,
) -> dict:
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

        cutoff_holdout = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
        df = df[df.index < cutoff_holdout].copy()
        df = _add_atr(df).dropna(subset=["atr"])
        if len(df) < 1000:
            print(f"  insufficient bars after holdout: {len(df)}", flush=True)
            continue
        df = add_all_patterns(df)
        print(f"  Training bars: {len(df)} (holdout reserved)", flush=True)

        for kind in PATTERN_KINDS:
            col = f"pat_{kind}"
            ser = df[col].dropna()
            buckets = ser.unique()
            for bucket in buckets:
                bucket_idx = ser[ser == bucket].index
                if len(bucket_idx) < N_MIN_LOCK:
                    continue
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
                        if stats["n_trades"] < N_MIN_LOCK:
                            continue
                        wlo = wilson_lower(stats["n_wins"], stats["n_trades"])
                        p = _binom(stats["n_wins"], stats["n_trades"], 0.5)
                        months = days / 30.0
                        per_month = stats["n_trades"] / months

                        all_results.append({
                            "stage": 1,
                            "pair": pair,
                            "pattern_kind": kind,
                            "pattern": str(bucket),
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


def stage1_apply_gates(results: list, q: float = BH_FDR_Q_LOCK) -> list:
    if not results:
        return []
    p_values = [r["p_value"] for r in results]
    bh_sig = benjamini_hochberg(p_values, q=q)
    survivors = []
    for r, sig in zip(results, bh_sig):
        gates = {
            "bh_fdr": sig,
            "wilson_gt_50": r["wilson_lower"] > WILSON_LOWER_MIN,
            "n_ge_50": r["n_trades"] >= N_MIN_LOCK,
            "ev_pos": r["ev_net_pip"] > 0,
        }
        if all(gates.values()):
            r["gates"] = gates
            survivors.append(r)
    return survivors


# ─────────────────────────────────────────────────────────────
# Stage 2 — Holdout OOS
# ─────────────────────────────────────────────────────────────
def run_stage2(args, out_dir: Path, date_tag: str) -> int:
    print("=" * 60)
    print("  Stage 2 — Holdout OOS Validation (last 90d)")
    print("=" * 60)
    if not args.input:
        print("ERROR: --input <stage1.json> required", file=sys.stderr)
        return 1
    with open(args.input) as f:
        stage1 = json.load(f)
    survivors_s1 = stage1.get("survivors", [])
    if not survivors_s1:
        print("Stage 1 had no survivors — Stage 2 skipped")
        out = {
            "stage": 2, "params": {"days": args.days, "holdout_days": HOLDOUT_DAYS_LOCK},
            "n_tested": 0, "n_survivors": 0, "survivors": [], "all_results": [],
        }
        json_path = out_dir / f"stage2_holdout_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")
        return 0

    print(f"Stage 1 survivors to test on holdout: {len(survivors_s1)}")
    pair_dfs = {}
    survivors_s2 = []
    all_holdout = []
    for r in survivors_s1:
        pair = r["pair"]
        if pair not in pair_dfs:
            try:
                df = _load_pair(pair, args.days + HOLDOUT_DAYS_LOCK)
                df = _add_atr(df).dropna(subset=["atr"])
                df = add_all_patterns(df)
                pair_dfs[pair] = df
            except Exception as e:
                print(f"  load failed {pair}: {e}", flush=True)
                continue
        df = pair_dfs[pair]
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=HOLDOUT_DAYS_LOCK)
        df_hold = df[df.index >= cutoff]

        col = f"pat_{r['pattern_kind']}"
        mask = (df_hold[col] == r["pattern"])
        bucket_idx = df_hold[mask].index
        sig_idx_hold = [df.index.get_loc(t) for t in bucket_idx]
        if len(sig_idx_hold) < 5:
            r2 = dict(r)
            r2["stage2_holdout"] = {"n": len(sig_idx_hold), "skip": "n<5"}
            r2["stage2_pass"] = False
            all_holdout.append(r2)
            continue

        trades = simulate_cell_trades(
            df, sig_idx_hold, r["direction"], df["atr"],
            sl_atr_mult=SL_ATR_MULT_LOCK, tp_atr_mult=TP_ATR_MULT_LOCK,
            max_hold_bars=r["forward_bars"], pair=pair, dedup=True,
        )
        s = aggregate_trade_stats(trades)
        wlo = wilson_lower(s["n_wins"], s["n_trades"]) if s["n_trades"] > 0 else 0
        r2 = dict(r)
        r2["stage2_holdout"] = {
            "n": s["n_trades"], "wr": s["wr"],
            "wilson_lower": round(wlo, 4),
            "ev_net_pip": s["ev_net_pip"],
        }
        passed = (s["n_trades"] >= 10) and (s["wr"] > 0.50) and (s["ev_net_pip"] > 0)
        r2["stage2_pass"] = passed
        all_holdout.append(r2)
        if passed:
            survivors_s2.append(r2)
            print(f"  ✅ {pair} {r['pattern_kind']}={r['pattern']} {r['direction']} fw={r['forward_bars']}: "
                  f"holdout n={s['n_trades']} WR={s['wr']:.3f} EV={s['ev_net_pip']:+.2f}p")

    print(f"\n=== Stage 2 Verdict ===")
    print(f"Tested: {len(survivors_s1)} | Final survivors: {len(survivors_s2)}")

    out = {
        "stage": 2,
        "params": {"days": args.days, "holdout_days": HOLDOUT_DAYS_LOCK},
        "n_tested": len(survivors_s1),
        "n_survivors": len(survivors_s2),
        "survivors": survivors_s2,
        "all_results": all_holdout,
    }
    json_path = out_dir / f"stage2_holdout_{date_tag}.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nJSON: {json_path}")
    return 0


# ─────────────────────────────────────────────────────────────
# Main CLI
# ─────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", type=int, required=True, choices=[1, 2])
    p.add_argument("--days", type=int, default=TRAINING_DAYS_LOCK)
    p.add_argument("--pairs", nargs="+", default=PAIRS_LOCK)
    p.add_argument("--forwards", type=int, nargs="+", default=FORWARD_BARS_LOCK)
    p.add_argument("--output", default="raw/phase8/track_b/")
    p.add_argument("--input", default=None,
                   help="JSON path (Stage 2 で前 stage 出力を読み込み)")
    p.add_argument("--bh-q", type=float, default=BH_FDR_Q_LOCK)
    args = p.parse_args()

    out_dir = Path(_PROJECT_ROOT) / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

    if args.stage == 1:
        print("=" * 60)
        print("  Phase 8 Track B — Stage 1: Sequence Pattern Scan")
        print(f"  Pairs: {args.pairs} | Days: {args.days}")
        print(f"  Holdout reserved: last {HOLDOUT_DAYS_LOCK} days")
        print(f"  Pattern kinds: {PATTERN_KINDS}")
        print("=" * 60)
        scan = stage1_pattern_scan(
            days=args.days, pairs=args.pairs, forwards=args.forwards,
        )
        survivors = stage1_apply_gates(scan["results"], q=args.bh_q)
        print(f"\n=== Stage 1 Verdict ===")
        print(f"Total cells: {scan['n_cells']}")
        print(f"Survivors: {len(survivors)}")
        if survivors:
            print(f"\nTop 30 by EV_net_pip:")
            top = sorted(survivors, key=lambda x: -x["ev_net_pip"])[:30]
            for r in top:
                print(f"  {r['pair']} {r['direction']} {r['pattern_kind']}={r['pattern']} "
                      f"fw={r['forward_bars']}: n={r['n_trades']} WR={r['wr']:.3f} "
                      f"Wilson_lo={r['wilson_lower']:.3f} EV={r['ev_net_pip']:+.2f}p "
                      f"Sharpe_pe={r['sharpe_per_event']:.3f}")

        out = {
            "stage": 1,
            "params": {
                "days": args.days, "pairs": args.pairs,
                "forwards": args.forwards, "bh_q": args.bh_q,
                "holdout_days": HOLDOUT_DAYS_LOCK,
                "n_min": N_MIN_LOCK,
                "sl_atr": SL_ATR_MULT_LOCK, "tp_atr": TP_ATR_MULT_LOCK,
                "pattern_kinds": PATTERN_KINDS,
            },
            "n_cells_total": scan["n_cells"],
            "n_survivors": len(survivors),
            "all_results": scan["results"],
            "survivors": survivors,
        }
        json_path = out_dir / f"stage1_seqscan_{date_tag}.json"
        with open(json_path, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"\nJSON: {json_path}")
        return 0

    elif args.stage == 2:
        return run_stage2(args, out_dir, date_tag)


if __name__ == "__main__":
    sys.exit(main())
