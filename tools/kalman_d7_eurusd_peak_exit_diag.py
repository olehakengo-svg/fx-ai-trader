#!/usr/bin/env python3
"""EUR_USD M15 peak-exit timing diagnostic.

Compares 3 exit logics for the pup_start entry:
  1. pup_end (current v15d default)
  2. peak_rollover: RSI rolling-over after recent overbought
  3. bear_div: bearish divergence (lower-high RSI swing with higher-high price swing, prior RSI > 70)
  combo: peak_rollover OR bear_div, fallback to pup_end

Reports per-trade P&L breakdown.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "data/cache/massive"


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1 / n, adjust=False).mean() / dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + rs)


def pivot_high(s: pd.Series, left: int, right: int) -> pd.Series:
    n = len(s)
    out = np.full(n, np.nan)
    arr = s.values
    for i in range(left, n - right):
        win = arr[i - left:i + right + 1]
        if arr[i] == win.max() and (win == arr[i]).sum() == 1:
            out[i + right] = arr[i]  # pine: pivot reported at +right bars (delay)
    return pd.Series(out, index=s.index)


def run(start: str, end: str, max_gap: int = 10, ob: float = 70.0, ob_lb: int = 10, rsi_drop: float = 2.0, piv_l: int = 5, piv_r: int = 3) -> None:
    df = pd.read_parquet(CACHE / "EUR_USD_15m.parquet").loc[start:end].copy()
    print(f"=== EUR_USD M15 peak-exit diag ({start}→{end}, max_gap={max_gap}, OB={ob}/{ob_lb}, drop={rsi_drop}, piv={piv_l}/{piv_r}) ===")
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

    bspu = np.empty(len(df), dtype=np.int64)
    cur = 9999
    pu = df["perfect_up"].values
    pdn = df["perfect_dn"].values
    for i in range(len(df)):
        if pu[i]:
            cur = 0
        elif pdn[i]:
            cur = 9999
        else:
            cur += 1
        bspu[i] = cur
    df["bspu"] = bspu

    df["persistent_up"] = df["perfect_up"] | (df["neutral"] & (df["bspu"] <= max_gap))
    df["pup_start"] = df["persistent_up"] & ~df["persistent_up"].shift(1, fill_value=False)
    df["pup_end"] = ~df["persistent_up"]

    # peak_rollover: rsi[-1] was within 0.5 of recent OB max, rsi dropped >= rsi_drop from rsi[-1]
    df["rsi_rolling_max"] = df["rsi"].rolling(ob_lb).max()
    df["rsi_was_ob"] = df["rsi_rolling_max"] >= ob
    df["peak_rollover"] = df["rsi_was_ob"] & (df["rsi"].shift(1) >= df["rsi_rolling_max"] - 0.5) & (df["rsi"] < df["rsi"].shift(1) - rsi_drop)

    # bearish divergence
    df["ph_price"] = pivot_high(df["High"], piv_l, piv_r)
    df["ph_rsi"] = pivot_high(df["rsi"], piv_l, piv_r)
    last_pp = np.nan
    last_pr = np.nan
    bear = np.zeros(len(df), dtype=bool)
    pp_arr = df["ph_price"].values
    pr_arr = df["ph_rsi"].values
    for i in range(len(df)):
        if not (np.isnan(pp_arr[i]) or np.isnan(pr_arr[i])):
            if not np.isnan(last_pp) and not np.isnan(last_pr):
                if pp_arr[i] > last_pp and pr_arr[i] < last_pr and last_pr >= ob:
                    bear[i] = True
            last_pp = pp_arr[i]
            last_pr = pr_arr[i]
    df["bear_div"] = bear

    df["peak_any"] = df["peak_rollover"] | df["bear_div"]

    # Simulate trades for 3 exit logics
    def simulate(exit_signal: pd.Series, name: str, fallback_pup_end: bool = False) -> dict:
        pnl_pips = []
        durations = []
        exit_reasons = []
        in_pos = False
        entry_px = 0.0
        entry_i = -1
        n_rows = len(df)
        ps = df["pup_start"].values
        pe = df["pup_end"].values
        ex = exit_signal.values
        cl = df["Close"].values
        for i in range(n_rows):
            if not in_pos:
                if ps[i]:
                    in_pos = True
                    entry_px = cl[i]
                    entry_i = i
            else:
                close_now = False
                reason = ""
                if ex[i]:
                    close_now = True
                    reason = name
                elif fallback_pup_end and pe[i]:
                    close_now = True
                    reason = "pup_end"
                if close_now:
                    p = (cl[i] - entry_px) / 0.0001
                    pnl_pips.append(p)
                    durations.append(i - entry_i)
                    exit_reasons.append(reason)
                    in_pos = False
        return {"N": len(pnl_pips), "pnl": np.array(pnl_pips), "dur": np.array(durations), "reasons": exit_reasons}

    res = {}
    res["pup_end"] = simulate(df["pup_end"], "pup_end", fallback_pup_end=False)
    res["peak_only"] = simulate(df["peak_any"], "peak_any", fallback_pup_end=False)
    res["peak_+_pup_end"] = simulate(df["peak_any"], "peak_any", fallback_pup_end=True)

    print("\n=== Exit logic comparison ===")
    print(f"{'Logic':<20} {'N':>4} {'sumP':>8} {'mean':>8} {'WR%':>6} {'meanDur':>8} {'PF':>6}")
    for k, r in res.items():
        p = r["pnl"]
        if len(p) == 0:
            print(f"{k:<20} 0")
            continue
        wins = p[p > 0].sum()
        losses = -p[p < 0].sum()
        pf = wins / losses if losses > 0 else float("inf")
        wr = (p > 0).mean() * 100
        print(f"{k:<20} {len(p):>4} {p.sum():>+8.0f} {p.mean():>+8.2f} {wr:>6.1f} {r['dur'].mean():>8.1f} {pf:>6.3f}")

    # peak signal trigger counts
    pr_total = int(df["peak_rollover"].sum())
    bd_total = int(df["bear_div"].sum())
    pa_total = int(df["peak_any"].sum())
    print(f"\nPeak signal triggers in window: rollover={pr_total}, bear_div={bd_total}, any_peak={pa_total}")

    # detailed: for combo (peak + pup_end fallback), reason breakdown
    combo = res["peak_+_pup_end"]
    reasons = pd.Series(combo["reasons"])
    print(f"\nCombo exit-reason breakdown:")
    print(reasons.value_counts())

    p_combo = combo["pnl"]
    for r_name in reasons.unique():
        idx = [i for i, x in enumerate(combo["reasons"]) if x == r_name]
        sub = p_combo[idx]
        wr = (sub > 0).mean() * 100 if len(sub) else float("nan")
        print(f"  {r_name:<15} N={len(sub):3d} sum={sub.sum():+.0f}p mean={sub.mean():+.2f}p WR={wr:.1f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end", default="2026-05-05")
    ap.add_argument("--max-gap", type=int, default=10)
    ap.add_argument("--ob", type=float, default=70.0)
    ap.add_argument("--ob-lb", type=int, default=10)
    ap.add_argument("--rsi-drop", type=float, default=2.0)
    ap.add_argument("--piv-l", type=int, default=5)
    ap.add_argument("--piv-r", type=int, default=3)
    args = ap.parse_args()
    run(start=args.start, end=args.end, max_gap=args.max_gap, ob=args.ob, ob_lb=args.ob_lb, rsi_drop=args.rsi_drop, piv_l=args.piv_l, piv_r=args.piv_r)
