#!/usr/bin/env python3
"""Sweep-Reversion Grid Scan 12y — research-only, no production code.

Spec: docs/superpowers/specs/2026-06-12-sweep-reversion-grid-scan-design.md

Scans 12y native 15m MASSIVE parquets (+1h OHLC aggregation) for
stop-hunt / liquidity-sweep reversal edge cells. Hard gate is Bonferroni
only (user choice 2026-06-12); WFO folds and yearly consistency are
reported as info columns, not gates.

Usage:
    python3 tools/research_sweep_reversion_grid_12y.py [--smoke]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache" / "massive"
OUT_JSON = ROOT / "bt-results" / "sweep-reversion-grid-scan-12y.json"
OUT_MD = ROOT / "bt-results" / "sweep-reversion-grid-scan-12y.md"

PAIRS = ["EUR_USD", "GBP_USD", "EUR_GBP", "EUR_JPY"]
SPREAD_PIP = {"EUR_USD": 0.8, "GBP_USD": 1.2, "EUR_GBP": 1.5, "EUR_JPY": 1.6}
TFS = ["15m", "1h"]
LOOKBACKS = [24, 96, 288]
DEPTHS = [0.05, 0.25, 0.5]
HORIZONS = [4, 16, 48]
SESSIONS = {"ASN": (0, 7), "LDN": (7, 13), "NY": (13, 21), "LATE": (21, 24)}
DEDUP_GAP = 12  # min bars between events per (pair,TF,L,d,dir)
MIN_N = 30      # below this, cell reported but never survives

M_TESTS = len(PAIRS) * len(TFS) * len(LOOKBACKS) * len(DEPTHS) * 2 * len(HORIZONS) * len(SESSIONS)
ALPHA = 0.05 / M_TESTS
Z_BONF = NormalDist().inv_cdf(1 - ALPHA)


def pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("JPY") else 0.0001


def load_frame(pair: str, tf: str) -> pd.DataFrame:
    df = pd.read_parquet(CACHE / f"{pair}_15m.parquet")
    cols = {c.lower(): c for c in df.columns}
    df = df.rename(columns={cols[k]: k for k in ("open", "high", "low", "close") if k in cols})
    df = df[["open", "high", "low", "close"]].astype(float)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{pair}: index is not DatetimeIndex")
    df = df.sort_index()
    if tf == "1h":
        df = df.resample("1h").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        ).dropna()
    return df


def wilder_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"],
         (df["high"] - prev_close).abs(),
         (df["low"] - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def dedup_indices(idx: np.ndarray, gap: int) -> np.ndarray:
    """Keep first event, drop any within `gap` bars of the last kept one."""
    if len(idx) == 0:
        return idx
    keep = [idx[0]]
    for i in idx[1:]:
        if i - keep[-1] >= gap:
            keep.append(i)
    return np.array(keep)


def wilson_lo(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def cell_stats(net: np.ndarray, years: np.ndarray) -> dict:
    n = len(net)
    if n == 0:
        return {"n": 0}
    mean = float(net.mean())
    std = float(net.std(ddof=1)) if n > 1 else 0.0
    t = mean / (std / math.sqrt(n)) if std > 0 and n >= 2 else 0.0
    wins = int((net > 0).sum())
    # WFO 3 equal-size folds in event order (events are time-ordered)
    folds = np.array_split(net, 3)
    fold_means = [round(float(f.mean()), 4) if len(f) else None for f in folds]
    # yearly consistency: positive-mean years / years with >=5 events
    yr_pos, yr_tot = 0, 0
    for y in np.unique(years):
        sub = net[years == y]
        if len(sub) >= 5:
            yr_tot += 1
            if sub.mean() > 0:
                yr_pos += 1
    return {
        "n": n, "wins": wins, "wr": round(wins / n, 4),
        "mean_net_pip": round(mean, 4), "std": round(std, 4),
        "t_stat": round(t, 3), "wilson_lo_95": round(wilson_lo(wins, n), 4),
        "wfo_fold_means": fold_means,
        "yearly_pos": yr_pos, "yearly_total": yr_tot,
    }


def scan() -> tuple[list[dict], list[dict]]:
    cells, survivors = [], []
    for pair in PAIRS:
        spread = SPREAD_PIP[pair]
        psize = pip_size(pair)
        for tf in TFS:
            df = load_frame(pair, tf)
            atr = wilder_atr(df)
            high, low, close = df["high"].values, df["low"].values, df["close"].values
            opn = df["open"].values
            hours = df.index.hour.values
            yrs = df.index.year.values
            nbars = len(df)
            print(f"[scan] {pair} {tf}: {nbars} bars "
                  f"{df.index.min().date()} → {df.index.max().date()}", flush=True)
            for L in LOOKBACKS:
                swing_hi = pd.Series(high).shift(1).rolling(L).max().values
                swing_lo = pd.Series(low).shift(1).rolling(L).min().values
                for d in DEPTHS:
                    thresh = d * atr.values
                    ev_hi = np.where((high > swing_hi + thresh) & (close < swing_hi))[0]
                    ev_lo = np.where((low < swing_lo - thresh) & (close > swing_lo))[0]
                    for direction, ev in (("SELL", ev_hi), ("BUY", ev_lo)):
                        ev = ev[(ev >= L) & (ev + 1 + max(HORIZONS) < nbars)]
                        ev = dedup_indices(ev, DEDUP_GAP)
                        if len(ev) == 0:
                            continue
                        entry = opn[ev + 1]
                        for H in HORIZONS:
                            exit_px = close[ev + H]
                            if direction == "SELL":
                                net = (entry - exit_px) / psize - spread
                            else:
                                net = (exit_px - entry) / psize - spread
                            ev_hours = hours[ev]
                            ev_years = yrs[ev]
                            for sess, (h0, h1) in SESSIONS.items():
                                mask = (ev_hours >= h0) & (ev_hours < h1)
                                st = cell_stats(net[mask], ev_years[mask])
                                cell = {
                                    "pair": pair, "tf": tf, "L": L, "d": d,
                                    "direction": direction, "H": H, "session": sess,
                                    **st,
                                }
                                cells.append(cell)
                                if (st.get("n", 0) >= MIN_N
                                        and st.get("mean_net_pip", 0) > 0
                                        and st.get("t_stat", 0) >= Z_BONF):
                                    survivors.append(cell)
    return cells, survivors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="EUR_USD 15m only, quick sanity run")
    args = ap.parse_args()

    global PAIRS, TFS
    if args.smoke:
        PAIRS = ["EUR_USD"]
        TFS = ["15m"]

    t0 = time.time()
    cells, survivors = scan()
    elapsed = time.time() - t0

    survivors.sort(key=lambda c: -c.get("t_stat", 0))
    result = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "spec": "docs/superpowers/specs/2026-06-12-sweep-reversion-grid-scan-design.md",
        "m_tests": M_TESTS, "alpha_bonf": ALPHA, "z_bonf": round(Z_BONF, 3),
        "hard_gate": "mean_net_pip>0 AND t_stat>=z_bonf AND n>=30 (Bonferroni only, user choice)",
        "info_columns": ["wfo_fold_means", "yearly_pos/yearly_total", "wilson_lo_95"],
        "spread_pip": SPREAD_PIP, "dedup_gap_bars": DEDUP_GAP,
        "smoke": args.smoke, "elapsed_s": round(elapsed, 1),
        "cells_evaluated": len(cells),
        "survivors_count": len(survivors),
        "survivors": survivors,
        "top50_by_tstat": sorted(
            [c for c in cells if c.get("n", 0) >= MIN_N],
            key=lambda c: -c.get("t_stat", 0))[:50],
        "cells": cells,
    }
    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=1))

    lines = [
        "# Sweep-Reversion Grid Scan 12y — Result",
        f"\nGenerated: {result['generated_at']}  elapsed {elapsed:.0f}s",
        f"\nm={M_TESTS}, alpha={ALPHA:.2e}, z_bonf={Z_BONF:.3f}, "
        f"cells evaluated={len(cells)}",
        f"\n## Survivors (Bonferroni hard gate): **{len(survivors)}**\n",
    ]
    if survivors:
        lines.append("| pair | tf | L | d | dir | H | sess | N | WR | mean_pip | t | WFO folds | yr+ |")
        lines.append("|---|---|--:|--:|---|--:|---|--:|--:|--:|--:|---|---|")
        for c in survivors:
            lines.append(
                f"| {c['pair']} | {c['tf']} | {c['L']} | {c['d']} | {c['direction']} "
                f"| {c['H']} | {c['session']} | {c['n']} | {c['wr']:.3f} "
                f"| {c['mean_net_pip']:+.3f} | {c['t_stat']:.2f} "
                f"| {c['wfo_fold_means']} | {c['yearly_pos']}/{c['yearly_total']} |")
    else:
        lines.append("**生存 cell ゼロ — sweep-reversion 機序は本 grid では Bonferroni を通らず。**")
        lines.append("機序棄却記録として保存 (TSMOM NULL と同形式)。")
    lines.append("\n## Top 10 by t-stat (gate 不問、参考)\n")
    lines.append("| pair | tf | L | d | dir | H | sess | N | WR | mean_pip | t |")
    lines.append("|---|---|--:|--:|---|--:|---|--:|--:|--:|--:|")
    for c in result["top50_by_tstat"][:10]:
        lines.append(
            f"| {c['pair']} | {c['tf']} | {c['L']} | {c['d']} | {c['direction']} "
            f"| {c['H']} | {c['session']} | {c['n']} | {c['wr']:.3f} "
            f"| {c['mean_net_pip']:+.3f} | {c['t_stat']:.2f} |")
    OUT_MD.write_text("\n".join(lines) + "\n")

    print(f"\n{'='*60}")
    print(f"cells={len(cells)} survivors={len(survivors)} "
          f"z_bonf={Z_BONF:.3f} elapsed={elapsed:.0f}s")
    print(f"saved: {OUT_JSON.name}, {OUT_MD.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
