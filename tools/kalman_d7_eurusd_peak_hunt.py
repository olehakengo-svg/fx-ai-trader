#!/usr/bin/env python3
"""EUR_USD M15 — peak detection hunt.

Goal: find an exit condition that approaches the per-trade peak high
without firing too early (selection bias) or too late (give-back).

Strategy:
  (A) For every pup_start trade (rsi>=65 filter), identify peak_bar (max High)
      and characterize it vs non-peak bars in the same trade.
  (B) Grid-search peak exit candidates:
      - Chandelier trail: exit when close < highest_since_entry - K*ATR_entry
      - Lower-high RSI: exit when RSI declines >= D from its rolling-max
      - Bearish reversal candle: close < open AND (high - close) > 1.5*(close-low)
      - dev_ef percentile rollover: dev_ef declines from N-bar rolling max
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kalman_d7_eurusd_filter_grid import prepare


def sim_with_exit_rule(df, rsi_min: float, exit_fn, sl_mul: float | None = 1.5) -> dict:
    cl = df["Close"].values
    op = df["Open"].values
    hi = df["High"].values
    lo = df["Low"].values
    ef = df["ema_fast"].values
    a = df["atr"].values
    r = df["rsi"].values
    ps = df["pup_start"].values
    pe = df["pup_end"].values
    n = len(df)
    pnl, durs, reasons, peak_caps = [], [], [], []
    in_pos = False; ent_i = -1; ent_px = 0.0; ent_atr = 0.0
    for i in range(n):
        if not in_pos:
            if ps[i] and r[i] >= rsi_min:
                in_pos = True; ent_i = i; ent_px = cl[i]; ent_atr = a[i]
        else:
            close_now = False; reason = ""; exit_px = cl[i]
            if sl_mul is not None and lo[i] <= ent_px - sl_mul * ent_atr:
                close_now = True; reason = "SL"; exit_px = ent_px - sl_mul * ent_atr
            else:
                rc = exit_fn(df, i, ent_i, ent_px, ent_atr)
                if rc is not None:
                    close_now = True; reason = rc[0]; exit_px = rc[1]
                elif pe[i]:
                    close_now = True; reason = "pup_end"; exit_px = cl[i]
            if close_now:
                p = (exit_px - ent_px) / 0.0001
                peak_actual = (hi[ent_i:i + 1].max() - ent_px) / 0.0001
                cap_pct = (100 * p / peak_actual) if peak_actual > 0 else 0.0
                pnl.append(p); durs.append(i - ent_i); reasons.append(reason); peak_caps.append(cap_pct)
                in_pos = False
    arr = np.array(pnl)
    if len(arr) == 0:
        return {"N": 0}
    cum = arr.cumsum()
    dd = cum - np.maximum.accumulate(cum)
    wins = arr[arr > 0].sum(); losses = -arr[arr < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")
    wr = (arr > 0).mean()
    return {"N": len(arr), "sum": arr.sum(), "mean": arr.mean(), "wr": wr * 100, "pf": pf,
            "meanDur": float(np.mean(durs)), "maxDD": float(dd.min()),
            "avg_cap_pct": float(np.mean(peak_caps)),
            "reasons": pd.Series(reasons).value_counts().to_dict()}


def main():
    df = prepare(start="2025-05-21", end="2026-05-21")
    df["rsi_d3"] = df["rsi"] - df["rsi"].shift(3)
    cl = df["Close"].values
    op = df["Open"].values
    hi = df["High"].values
    lo = df["Low"].values
    ef = df["ema_fast"].values
    a = df["atr"].values
    r = df["rsi"].values

    # --- (A) Peak bar characterization ---
    print(f"=== EUR_USD M15 peak-hunting (12mo) ===")
    ps = df["pup_start"].values; pe = df["pup_end"].values
    in_pos = False; ent_i = -1; trade_peaks = []
    for i in range(len(df)):
        if not in_pos:
            if ps[i] and r[i] >= 65:
                in_pos = True; ent_i = i
        else:
            if pe[i]:
                # peak bar
                peak_pos = ent_i + int(hi[ent_i:i + 1].argmax())
                if peak_pos > ent_i and peak_pos < i:
                    # peak features
                    trade_peaks.append({
                        "rsi_peak": r[peak_pos],
                        "rsi_after_1": r[peak_pos + 1] if peak_pos + 1 < len(df) else np.nan,
                        "rsi_after_2": r[peak_pos + 2] if peak_pos + 2 < len(df) else np.nan,
                        "rsi_after_3": r[peak_pos + 3] if peak_pos + 3 < len(df) else np.nan,
                        "dev_ef_peak": (cl[peak_pos] - ef[peak_pos]) / a[peak_pos],
                        "dev_ef_after_1": (cl[peak_pos + 1] - ef[peak_pos + 1]) / a[peak_pos + 1] if peak_pos + 1 < len(df) else np.nan,
                        "close_open_peak": cl[peak_pos] - op[peak_pos],
                        "uwick_peak": hi[peak_pos] - max(op[peak_pos], cl[peak_pos]),
                        "lwick_peak": min(op[peak_pos], cl[peak_pos]) - lo[peak_pos],
                        "atr_peak": a[peak_pos],
                        "bars_to_peak": peak_pos - ent_i,
                    })
                in_pos = False
    pdf = pd.DataFrame(trade_peaks)
    print(f"  Trades with mid-trade peak: {len(pdf)}")
    print(f"  peak features (median):")
    for k in ["rsi_peak", "rsi_after_1", "rsi_after_2", "dev_ef_peak", "dev_ef_after_1", "uwick_peak", "lwick_peak", "bars_to_peak"]:
        print(f"    {k:20s} median={pdf[k].median():.3f}  mean={pdf[k].mean():.3f}")
    print(f"  RSI drop 1-bar after peak: median={pdf['rsi_peak'].median() - pdf['rsi_after_1'].median():.2f}")

    # --- (B) Exit rule grid ---
    print(f"\n=== Exit rule grid (entry=pup_start AND rsi>=65, SL=1.5xATR) ===")

    # Chandelier trail K
    def make_chand(K):
        def fn(df_, i, ent_i, ent_px, ent_atr):
            hh = df_["High"].iloc[ent_i:i + 1].max()
            if df_["Close"].iloc[i] < hh - K * ent_atr and i > ent_i:
                return ("chand_" + str(K), df_["Close"].iloc[i])
            return None
        return fn

    # RSI rollover X pts from peak
    def make_rsi_rollover(X, N=8):
        def fn(df_, i, ent_i, ent_px, ent_atr):
            if i - ent_i < 1: return None
            rmax = df_["rsi"].iloc[max(ent_i, i - N):i + 1].max()
            if rmax >= 60 and df_["rsi"].iloc[i] <= rmax - X:
                return ("rsi_drop_" + str(X), df_["Close"].iloc[i])
            return None
        return fn

    # Bearish reversal candle (after recent HH within trade)
    def make_bear_rev():
        def fn(df_, i, ent_i, ent_px, ent_atr):
            if i - ent_i < 2: return None
            # close < open and large upper wick
            cl_ = df_["Close"].iloc[i]; op_ = df_["Open"].iloc[i]
            hi_ = df_["High"].iloc[i]; lo_ = df_["Low"].iloc[i]
            uwick = hi_ - max(op_, cl_)
            body = abs(cl_ - op_)
            # bearish reversal: red candle with large upper wick (>=1.5x body)
            if cl_ < op_ and uwick > 0 and body > 0 and uwick / body >= 1.5:
                return ("bear_rev", cl_)
            return None
        return fn

    # dev_ef rollover (peak dev_ef in last N bars then drop)
    def make_dev_rollover(N=5):
        def fn(df_, i, ent_i, ent_px, ent_atr):
            if i - ent_i < N: return None
            cl_ = df_["Close"].values; ef_ = df_["ema_fast"].values; a_ = df_["atr"].values
            devs = (cl_[max(ent_i, i - N):i + 1] - ef_[max(ent_i, i - N):i + 1]) / a_[max(ent_i, i - N):i + 1]
            if len(devs) >= 2 and devs.max() >= 1.5 and devs[-1] < devs.max() - 0.3:
                return ("dev_rollover", cl_[i])
            return None
        return fn

    # Composite: chandelier OR bear_rev (peak-aware)
    def make_composite(K):
        chand = make_chand(K); rev = make_bear_rev()
        def fn(df_, i, ent_i, ent_px, ent_atr):
            r1 = chand(df_, i, ent_i, ent_px, ent_atr)
            if r1: return r1
            r2 = rev(df_, i, ent_i, ent_px, ent_atr)
            if r2: return r2
            return None
        return fn

    candidates = [
        ("chand K=0.3", make_chand(0.3)),
        ("chand K=0.5", make_chand(0.5)),
        ("chand K=0.75", make_chand(0.75)),
        ("chand K=1.0", make_chand(1.0)),
        ("chand K=1.5", make_chand(1.5)),
        ("chand K=2.0", make_chand(2.0)),
        ("rsi_drop 3 pts", make_rsi_rollover(3)),
        ("rsi_drop 5 pts", make_rsi_rollover(5)),
        ("rsi_drop 8 pts", make_rsi_rollover(8)),
        ("bear_rev only", make_bear_rev()),
        ("dev_rollover", make_dev_rollover(5)),
        ("chand K=0.5 + bear_rev", make_composite(0.5)),
        ("chand K=1.0 + bear_rev", make_composite(1.0)),
        ("chand K=1.5 + bear_rev", make_composite(1.5)),
    ]

    print(f"\n{'Rule':<28} {'N':>4} {'sum':>7} {'mean':>7} {'WR%':>5} {'PF':>5} {'cap%':>5} {'dur':>4}  reasons")
    print("-" * 120)
    for name, fn in candidates:
        r = sim_with_exit_rule(df, 65, fn, sl_mul=1.5)
        if r.get("N", 0) == 0:
            print(f"{name:<28} 0")
            continue
        print(f"{name:<28} {r['N']:>4} {r['sum']:>+7.0f} {r['mean']:>+7.2f} {r['wr']:>5.1f} {r['pf']:>5.2f} {r['avg_cap_pct']:>5.1f} {r['meanDur']:>4.0f}  {r['reasons']}")


if __name__ == "__main__":
    main()
