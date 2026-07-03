#!/usr/bin/env python3
"""EUR_USD M15 Kalman D7 + Perfect Order initial-move diagnostic.

Replicates TV Pine v15e/v15f logic in Python on MASSIVE cache parquet.
Outputs:
  - global N raw PO_UP starts, captured (entries), missed (bridged)
  - per-cell breakdown (SESS / DIST_q / GAP_q / RSI_q) for cap vs mis
  - forward N-bar P&L (pip) per raw PO_UP start, segmented by cap vs mis
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "data/cache/massive"


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    d = series.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1 / length, adjust=False).mean() / dn.ewm(alpha=1 / length, adjust=False).mean()
    return 100 - 100 / (1 + rs)


def run(symbol: str = "EUR_USD", start: str = "2025-07-01", end: str = "2026-05-05", max_gap: int = 10, fwd_bars: int = 20) -> None:
    p = CACHE / f"{symbol}_15m.parquet"
    df = pd.read_parquet(p)
    df = df.loc[start:end].copy()
    print(f"=== {symbol} M15 diagnostic ({start} → {end}, max_gap={max_gap}, fwd={fwd_bars} bars) ===")
    print(f"bars: {len(df):,}")

    c = df["Close"]
    df["ema_fast"] = ema(c, 25)
    df["ema_mid"] = ema(c, 75)
    df["ema_slow"] = ema(c, 200)
    df["atr"] = atr(df, 14)
    df["rsi"] = rsi(c, 14)
    df["perfect_up"] = (df["ema_fast"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_slow"]) & (c > df["ema_fast"])
    df["perfect_dn"] = (df["ema_slow"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_fast"])
    df["neutral"] = ~df["perfect_up"] & ~df["perfect_dn"]

    bars_since_pu = np.empty(len(df), dtype=np.int64)
    cur = 9999
    pu_arr = df["perfect_up"].values
    pd_arr = df["perfect_dn"].values
    for i in range(len(df)):
        if pu_arr[i]:
            cur = 0
        elif pd_arr[i]:
            cur = 9999
        else:
            cur += 1
        bars_since_pu[i] = cur
    df["bars_since_pu"] = bars_since_pu

    df["persistent_up"] = df["perfect_up"] | (df["neutral"] & (df["bars_since_pu"] <= max_gap))
    df["raw_pu_start"] = df["perfect_up"] & ~df["perfect_up"].shift(1, fill_value=False)
    df["was_captured"] = df["raw_pu_start"] & ~df["persistent_up"].shift(1, fill_value=False)
    df["was_missed"] = df["raw_pu_start"] & df["persistent_up"].shift(1, fill_value=False)
    df["pup_start"] = df["persistent_up"] & ~df["persistent_up"].shift(1, fill_value=False)
    df["pup_end"] = ~df["persistent_up"]

    df["dist_atr"] = (c - df["ema_slow"]) / df["atr"]
    df["gap_atr"] = (df["ema_fast"] - df["ema_slow"]) / df["atr"]
    df["hour_utc"] = df.index.hour
    df["sess_idx"] = np.where(df["hour_utc"] < 7, 0, np.where(df["hour_utc"] < 12, 1, np.where(df["hour_utc"] < 16, 2, np.where(df["hour_utc"] < 21, 3, 4))))

    def dist_q(v):
        if v < 1.5: return 0
        if v < 3.0: return 1
        if v < 4.5: return 2
        return 3
    df["dist_q"] = df["dist_atr"].apply(dist_q)
    df["gap_q"] = df["gap_atr"].apply(dist_q)
    df["rsi_q"] = np.where(df["rsi"] < 50, 0, np.where(df["rsi"] < 70, 1, 2))

    n_raw = int(df["raw_pu_start"].sum())
    n_cap = int(df["was_captured"].sum())
    n_mis = int(df["was_missed"].sum())
    print(f"\nRAW PO_UP starts: {n_raw}")
    print(f"  Captured (entries): {n_cap}  ({100*n_cap/n_raw:.1f}%)")
    print(f"  Missed (bridged):   {n_mis}  ({100*n_mis/n_raw:.1f}%)")

    starts = df[df["raw_pu_start"]].copy()
    fwd_pips = np.full(len(starts), np.nan)
    pip = 0.0001
    idx_to_pos = {ts: i for i, ts in enumerate(df.index)}
    for j, (ts, row) in enumerate(starts.iterrows()):
        i = idx_to_pos[ts]
        if i + fwd_bars >= len(df):
            continue
        entry = df["Close"].iloc[i]
        exit_ = df["Close"].iloc[i + fwd_bars]
        fwd_pips[j] = (exit_ - entry) / pip
    starts["fwd_pips"] = fwd_pips

    cap = starts[starts["was_captured"]].copy()
    mis = starts[starts["was_missed"]].copy()

    def stat(s: pd.Series) -> dict:
        s = s.dropna()
        if len(s) == 0:
            return {"N": 0, "mean": np.nan, "wr": np.nan, "sum": np.nan}
        return {"N": len(s), "mean": float(s.mean()), "wr": float((s > 0).mean() * 100), "sum": float(s.sum())}

    print(f"\n=== Forward {fwd_bars}-bar (~{fwd_bars*15/60:.0f}h) P&L (pip) ===")
    print(f"  Captured: N={stat(cap['fwd_pips'])['N']} mean={stat(cap['fwd_pips'])['mean']:+.2f}p WR={stat(cap['fwd_pips'])['wr']:.1f}% sum={stat(cap['fwd_pips'])['sum']:+.0f}p")
    print(f"  Missed:   N={stat(mis['fwd_pips'])['N']} mean={stat(mis['fwd_pips'])['mean']:+.2f}p WR={stat(mis['fwd_pips'])['wr']:.1f}% sum={stat(mis['fwd_pips'])['sum']:+.0f}p")

    def breakdown(starts_subset, col, names):
        rows = []
        for k, name in enumerate(names):
            sub = starts_subset[starts_subset[col] == k]["fwd_pips"]
            st = stat(sub)
            rows.append((name, st["N"], st["mean"], st["wr"], st["sum"]))
        return rows

    sess_names = ["ASN", "LDN", "OVL", "NY", "DEAD"]
    dist_names = ["<1.5", "1.5-3", "3-4.5", ">=4.5"]
    rsi_names = ["<50", "50-70", ">=70"]

    print(f"\n=== Per-SESSION (Captured) ===")
    for n, N, m, wr, s in breakdown(cap, "sess_idx", sess_names):
        print(f"  {n:5s} N={N:3d}  mean={m:+6.2f}p  WR={wr:5.1f}%  sum={s:+7.0f}p")
    print(f"=== Per-SESSION (Missed) ===")
    for n, N, m, wr, s in breakdown(mis, "sess_idx", sess_names):
        print(f"  {n:5s} N={N:3d}  mean={m:+6.2f}p  WR={wr:5.1f}%  sum={s:+7.0f}p")

    print(f"\n=== Per-DIST_q (Captured) ===")
    for n, N, m, wr, s in breakdown(cap, "dist_q", dist_names):
        print(f"  DIST_{n:6s} N={N:3d}  mean={m:+6.2f}p  WR={wr:5.1f}%  sum={s:+7.0f}p")
    print(f"=== Per-DIST_q (Missed) ===")
    for n, N, m, wr, s in breakdown(mis, "dist_q", dist_names):
        print(f"  DIST_{n:6s} N={N:3d}  mean={m:+6.2f}p  WR={wr:5.1f}%  sum={s:+7.0f}p")

    print(f"\n=== Per-GAP_q (Captured) ===")
    for n, N, m, wr, s in breakdown(cap, "gap_q", dist_names):
        print(f"  GAP_{n:6s} N={N:3d}  mean={m:+6.2f}p  WR={wr:5.1f}%  sum={s:+7.0f}p")
    print(f"=== Per-GAP_q (Missed) ===")
    for n, N, m, wr, s in breakdown(mis, "gap_q", dist_names):
        print(f"  GAP_{n:6s} N={N:3d}  mean={m:+6.2f}p  WR={wr:5.1f}%  sum={s:+7.0f}p")

    print(f"\n=== Per-RSI_q (Captured) ===")
    for n, N, m, wr, s in breakdown(cap, "rsi_q", rsi_names):
        print(f"  RSI_{n:6s} N={N:3d}  mean={m:+6.2f}p  WR={wr:5.1f}%  sum={s:+7.0f}p")
    print(f"=== Per-RSI_q (Missed) ===")
    for n, N, m, wr, s in breakdown(mis, "rsi_q", rsi_names):
        print(f"  RSI_{n:6s} N={N:3d}  mean={m:+6.2f}p  WR={wr:5.1f}%  sum={s:+7.0f}p")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="EUR_USD")
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end", default="2026-05-05")
    ap.add_argument("--max-gap", type=int, default=10)
    ap.add_argument("--fwd", type=int, default=20)
    args = ap.parse_args()
    run(symbol=args.symbol, start=args.start, end=args.end, max_gap=args.max_gap, fwd_bars=args.fwd)
