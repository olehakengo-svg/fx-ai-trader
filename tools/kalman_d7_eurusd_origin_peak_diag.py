#!/usr/bin/env python3
"""EUR_USD M15 — pup_start origin state + per-trade peak metrics.

Two diagnostics:
  A) pup_start prior-bar state (perfect_dn / neutral / perfect_up_continuation):
     - how many entries came from each state
     - outcome breakdown (mean P&L, WR)
     - also surface "green-regime entries we missed" (perfect_up bars where no entry fired because persistent_up was bridged)

  B) Per-trade peak analysis:
     - find bar of max unrealized gain (max High between entry and exit)
     - measure at-peak: (close-ema_fast)/atr, (close-ema_slow)/atr, (close-ema_fast)/close*100, rsi
     - compare to entry-time values
     - look for a threshold where peak ≈ exit signal candidate
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parent.parent / "data/cache/massive"


def ema(s, n): return s.ewm(span=n, adjust=False).mean()


def atr_calc(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi_calc(s, n=14):
    d = s.diff()
    up = d.clip(lower=0); dn = -d.clip(upper=0)
    rs = up.ewm(alpha=1 / n, adjust=False).mean() / dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + rs)


def prepare(start="2025-07-01", end="2026-05-05", max_gap=10):
    df = pd.read_parquet(CACHE / "EUR_USD_15m.parquet").loc[start:end].copy()
    c = df["Close"]
    df["ema_fast"] = ema(c, 25); df["ema_mid"] = ema(c, 75); df["ema_slow"] = ema(c, 200)
    df["atr"] = atr_calc(df, 14); df["rsi"] = rsi_calc(c, 14)
    df["perfect_up"] = (df["ema_fast"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_slow"]) & (c > df["ema_fast"])
    df["perfect_dn"] = (df["ema_slow"] > df["ema_mid"]) & (df["ema_mid"] > df["ema_fast"])
    df["neutral"] = ~df["perfect_up"] & ~df["perfect_dn"]
    pu = df["perfect_up"].values; pdn = df["perfect_dn"].values
    bspu = np.empty(len(df), dtype=np.int64); cur = 9999
    for i in range(len(df)):
        if pu[i]: cur = 0
        elif pdn[i]: cur = 9999
        else: cur += 1
        bspu[i] = cur
    df["bspu"] = bspu
    df["persistent_up"] = df["perfect_up"] | (df["neutral"] & (df["bspu"] <= max_gap))
    df["pup_start"] = df["persistent_up"] & ~df["persistent_up"].shift(1, fill_value=False)
    df["pup_end"] = ~df["persistent_up"]
    return df


def main():
    df = prepare()
    print(f"=== EUR_USD M15 origin + peak diagnostic ===")
    print(f"bars: {len(df):,}  pup_start: {int(df['pup_start'].sum())}  raw perfect_up bars: {int(df['perfect_up'].sum())}")

    # --- (A) pup_start prior-bar state ---
    print(f"\n=== (A) pup_start origin state (prior bar) ===")
    prev_pu = df["perfect_up"].shift(1, fill_value=False).values
    prev_pdn = df["perfect_dn"].shift(1, fill_value=False).values
    prev_neutral = (~df["perfect_up"].shift(1, fill_value=False) & ~df["perfect_dn"].shift(1, fill_value=False)).values
    ps_idx = np.where(df["pup_start"].values)[0]
    state_labels = []
    for i in ps_idx:
        if prev_pdn[i]:
            state_labels.append("from_red")
        elif prev_neutral[i]:
            state_labels.append("from_gray")
        else:
            state_labels.append("from_green")  # shouldn't happen (since persistent_up[1] would be true), but safety
    print(f"  Origin counts: {pd.Series(state_labels).value_counts().to_dict()}")

    # --- Simulate trades (entry=pup_start, exit=pup_end) with origin tag ---
    cl = df["Close"].values
    hi = df["High"].values
    lo = df["Low"].values
    ef = df["ema_fast"].values
    em = df["ema_mid"].values
    es = df["ema_slow"].values
    a = df["atr"].values
    r = df["rsi"].values
    ps = df["pup_start"].values
    pe = df["pup_end"].values
    rsiv = df["rsi"].values
    n = len(df)

    trades = []
    in_pos = False; ent_i = -1; ent_px = 0.0; ent_state = ""
    for i in range(n):
        if not in_pos:
            if ps[i]:
                in_pos = True; ent_i = i; ent_px = cl[i]
                if prev_pdn[i]: ent_state = "from_red"
                elif prev_neutral[i]: ent_state = "from_gray"
                else: ent_state = "from_green"
        else:
            if pe[i]:
                # find peak high during the trade
                seg_hi = hi[ent_i:i + 1]
                peak_pos = ent_i + int(seg_hi.argmax())
                peak_px = hi[peak_pos]
                # at-peak metrics
                pk_ef = ef[peak_pos]; pk_es = es[peak_pos]; pk_em = em[peak_pos]; pk_atr = a[peak_pos]; pk_rsi = rsiv[peak_pos]
                dev_ef_atr = (cl[peak_pos] - pk_ef) / pk_atr  # close vs ema_fast in ATR
                dev_es_atr = (cl[peak_pos] - pk_es) / pk_atr
                dev_ef_pct = (cl[peak_pos] - pk_ef) / cl[peak_pos] * 100
                # at-entry metrics
                en_ef = ef[ent_i]; en_es = es[ent_i]; en_atr = a[ent_i]
                dev_ef_atr_e = (cl[ent_i] - en_ef) / en_atr
                # also: bars from entry to peak, bars from peak to exit (lag)
                trades.append({
                    "origin": ent_state,
                    "pnl_pips": (cl[i] - ent_px) / 0.0001,
                    "max_pips": (peak_px - ent_px) / 0.0001,
                    "give_back_pips": (peak_px - cl[i]) / 0.0001,
                    "bars_to_peak": peak_pos - ent_i,
                    "bars_peak_to_exit": i - peak_pos,
                    "rsi_at_entry": r[ent_i],
                    "rsi_at_peak": pk_rsi,
                    "dev_ef_atr_entry": dev_ef_atr_e,
                    "dev_ef_atr_peak": dev_ef_atr,
                    "dev_es_atr_peak": dev_es_atr,
                    "dev_ef_pct_peak": dev_ef_pct,
                })
                in_pos = False
    t = pd.DataFrame(trades)

    # outcome per origin
    print(f"\n=== Outcome per origin (entry=pup_start, exit=pup_end) ===")
    for orig in ["from_red", "from_gray"]:
        sub = t[t["origin"] == orig]
        if len(sub) == 0: continue
        wins_p = sub[sub["pnl_pips"] > 0]["pnl_pips"].sum()
        loss_p = -sub[sub["pnl_pips"] <= 0]["pnl_pips"].sum()
        pf = wins_p / loss_p if loss_p > 0 else float("inf")
        wr = (sub["pnl_pips"] > 0).mean() * 100
        print(f"  {orig:<10} N={len(sub):3d}  sum={sub['pnl_pips'].sum():+.0f}p  mean={sub['pnl_pips'].mean():+.2f}p  WR={wr:.1f}%  PF={pf:.3f}")
        print(f"    avg max_pips: {sub['max_pips'].mean():+.2f}  avg give_back: {sub['give_back_pips'].mean():+.2f}  bars_to_peak: {sub['bars_to_peak'].mean():.1f}  bars_peak_to_exit: {sub['bars_peak_to_exit'].mean():.1f}")

    # missed green entries: perfect_up bars where the trade was already in a bridged persistent_up
    raw_pu_start = df["perfect_up"] & ~df["perfect_up"].shift(1, fill_value=False)
    n_raw = int(raw_pu_start.sum())
    captured = raw_pu_start & ~df["persistent_up"].shift(1, fill_value=False)
    missed = raw_pu_start & df["persistent_up"].shift(1, fill_value=False)
    print(f"\n=== Raw perfect_up starts vs captured (pup_start fires) ===")
    print(f"  Raw PO_UP starts:           {n_raw}")
    print(f"  Captured (= pup_start):     {int(captured.sum())}")
    print(f"  Missed (bridged-merged):    {int(missed.sum())}")

    # --- (B) Peak metrics analysis ---
    print(f"\n=== (B) Per-trade peak metrics (all 137 trades) ===")
    print(f"  avg max_pips: {t['max_pips'].mean():+.2f}p  median {t['max_pips'].median():+.2f}p")
    print(f"  avg give_back at exit: {t['give_back_pips'].mean():+.2f}p  median {t['give_back_pips'].median():+.2f}p")
    print(f"  avg bars_to_peak: {t['bars_to_peak'].mean():.1f}  avg bars_peak_to_exit: {t['bars_peak_to_exit'].mean():.1f}")
    print(f"  avg dev_ef_atr at peak: {t['dev_ef_atr_peak'].mean():.2f}  median {t['dev_ef_atr_peak'].median():.2f}")
    print(f"  avg dev_es_atr at peak: {t['dev_es_atr_peak'].mean():.2f}  median {t['dev_es_atr_peak'].median():.2f}")
    print(f"  avg dev_ef_pct at peak: {t['dev_ef_pct_peak'].mean():.4f}%  median {t['dev_ef_pct_peak'].median():.4f}%")
    print(f"  avg rsi at peak: {t['rsi_at_peak'].mean():.1f}  median {t['rsi_at_peak'].median():.1f}")

    # win vs loss peak comparison
    wins = t[t["pnl_pips"] > 0]
    losses = t[t["pnl_pips"] <= 0]
    print(f"\n  WINS  N={len(wins):3d}: peak rsi mean={wins['rsi_at_peak'].mean():.1f}, dev_ef_atr={wins['dev_ef_atr_peak'].mean():.2f}, dev_es_atr={wins['dev_es_atr_peak'].mean():.2f}, max_pips={wins['max_pips'].mean():+.1f}, give_back={wins['give_back_pips'].mean():+.1f}")
    print(f"  LOSSES N={len(losses):3d}: peak rsi mean={losses['rsi_at_peak'].mean():.1f}, dev_ef_atr={losses['dev_ef_atr_peak'].mean():.2f}, dev_es_atr={losses['dev_es_atr_peak'].mean():.2f}, max_pips={losses['max_pips'].mean():+.1f}, give_back={losses['give_back_pips'].mean():+.1f}")

    # if we exit when dev_ef_atr crosses some threshold, peak %?
    print(f"\n=== dev_ef_atr threshold scan — if exit when dev_ef_atr >= X, what % of peak captured ===")
    print(f"{'threshold X':>12} {'N_trades_hit':>13} {'avg_pips_at_X':>14} {'avg_max_pips':>14} {'capture_%':>10}")
    for X in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        n_hit = 0; pips_at = []; pips_max = []
        # we need the bar where dev first crosses X
        in_pos = False; ent_i = -1; ent_px = 0.0
        for i in range(n):
            if not in_pos:
                if ps[i]: in_pos = True; ent_i = i; ent_px = cl[i]
            else:
                # check dev at this bar
                dev_now = (cl[i] - ef[i]) / a[i]
                if pe[i]:
                    in_pos = False
                    continue
                if dev_now >= X:
                    p_at = (cl[i] - ent_px) / 0.0001
                    # also peak so far
                    seg_hi = hi[ent_i:i + 1]
                    p_max = (seg_hi.max() - ent_px) / 0.0001
                    pips_at.append(p_at); pips_max.append(p_max)
                    n_hit += 1
                    in_pos = False
        if n_hit > 0:
            avg_at = np.mean(pips_at); avg_max = np.mean(pips_max)
            cap = 100 * avg_at / avg_max if avg_max > 0 else float("nan")
            print(f"{X:>12.1f} {n_hit:>13} {avg_at:>+14.2f} {avg_max:>+14.2f} {cap:>10.1f}")
        else:
            print(f"{X:>12.1f} {n_hit:>13} {'-':>14} {'-':>14} {'-':>10}")


if __name__ == "__main__":
    main()
