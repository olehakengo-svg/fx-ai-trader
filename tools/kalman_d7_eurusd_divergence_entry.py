#!/usr/bin/env python3
"""EUR_USD M15 — bullish divergence entry detector.

Concept (user observation):
  red → gray → green is the natural transition. Before the green starts,
  RSI and MACD show bullish divergence: price makes lower lows while
  RSI/MACD make higher lows.

Detection (during gray period after recent perfect_dn):
  - Track pivot lows in: price, RSI, MACD histogram
  - Bullish divergence: latest price_pivot_low < previous price_pivot_low
                       AND latest rsi_pivot_low > previous rsi_pivot_low
                       AND latest macd_pivot_low > previous macd_pivot_low (optional MACD)
  - Entry: bar where divergence is confirmed (with piv_right lag)

Constraints:
  - Must be in gray (neutral) regime, not perfect_up or perfect_dn
  - Must have had recent perfect_dn (pdn_in_50 >= 25)
"""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from kalman_d7_eurusd_filter_grid import prepare


def pivot_low(s: pd.Series, left: int, right: int) -> pd.Series:
    n = len(s); out = np.full(n, np.nan); arr = s.values
    for i in range(left, n - right):
        win = arr[i - left:i + right + 1]
        if arr[i] == win.min() and (win == arr[i]).sum() == 1:
            out[i + right] = arr[i]
    return pd.Series(out, index=s.index)


def main():
    df = prepare(start="2025-05-21", end="2026-05-21")

    # Add MACD line + histogram (12, 26, 9)
    ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd_line"] = ema_12 - ema_26
    df["macd_sig"] = df["macd_line"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd_line"] - df["macd_sig"]
    df["neutral"] = ~df["perfect_up"] & ~df["perfect_dn"]
    df["pdn_in_50"] = df["perfect_dn"].rolling(50).sum()

    # Pivot lows
    piv_l = 3; piv_r = 2
    df["pl_price"] = pivot_low(df["Low"], piv_l, piv_r)
    df["pl_rsi"] = pivot_low(df["rsi"], piv_l, piv_r)
    df["pl_macd"] = pivot_low(df["macd_hist"], piv_l, piv_r)

    cl = df["Close"].values; lo = df["Low"].values
    r = df["rsi"].values; mh = df["macd_hist"].values
    pl_p = df["pl_price"].values; pl_r = df["pl_rsi"].values; pl_m = df["pl_macd"].values
    pe_strict = df["pup_end"].values
    neutral = df["neutral"].values
    pdn50 = df["pdn_in_50"].values
    perfect_up = df["perfect_up"].values
    n = len(df)

    # Detect bullish divergence: at each pivot low bar, compare with previous pivot low
    div_signals = []  # list of (idx, kind)
    last_pp_idx = -1
    last_rp_idx = -1
    last_mp_idx = -1
    for i in range(n):
        if not np.isnan(pl_p[i]):
            # price pivot low detected
            if last_pp_idx >= 0:
                # compare current vs previous pp
                if pl_p[i] < pl_p[last_pp_idx]:  # lower price low
                    # check RSI: any RSI pivot between last_pp and current pp?
                    # Simpler: compare RSI value at current pp vs at last_pp
                    rsi_now = r[i]; rsi_last = r[last_pp_idx]
                    macd_now = mh[i]; macd_last = mh[last_pp_idx]
                    rsi_div = rsi_now > rsi_last  # higher rsi at lower price = bullish div
                    macd_div = macd_now > macd_last  # higher macd hist
                    if rsi_div and macd_div:
                        # require this happened during gray period AND recent perfect_dn
                        if neutral[i] and (not np.isnan(pdn50[i])) and pdn50[i] >= 25:
                            div_signals.append((i, "RSI+MACD"))
                        elif neutral[i] and (not np.isnan(pdn50[i])) and pdn50[i] >= 15:
                            div_signals.append((i, "RSI+MACD weaker"))
                    elif rsi_div and neutral[i] and (not np.isnan(pdn50[i])) and pdn50[i] >= 25:
                        div_signals.append((i, "RSI only"))
            last_pp_idx = i

    print(f"=== EUR_USD M15 bullish divergence detection (12mo) ===")
    print(f"  Total divergence signals: {len(div_signals)}")
    from collections import Counter
    print(f"  By type: {Counter([k for _, k in div_signals])}")

    # Simulate trades from divergence entries (no overlap with primary)
    # Entry: divergence signal
    # Exit: pup_end (when persistent_up next ends) or perfect_dn re-onset
    df["persistent_up"] = df["persistent_up"] if "persistent_up" in df.columns else (df["perfect_up"] | (df["neutral"] & (df["pup_end"] == False)))
    pers_up = df["persistent_up"].values

    trades = []
    in_pos = False; ent_i = -1; ent_px = 0.0; ent_kind = ""
    div_set = {idx: kind for idx, kind in div_signals}
    for i in range(n):
        if not in_pos:
            if i in div_set:
                in_pos = True; ent_i = i; ent_px = cl[i]; ent_kind = div_set[i]
        else:
            # exit when persistent_up turns false (after we've been in for at least a few bars)
            # Or when perfect_dn fires
            if (i - ent_i >= 3) and (df["perfect_dn"].iloc[i] or pe_strict[i]):
                p = (cl[i] - ent_px) / 0.0001
                peak_p = (df["High"].iloc[ent_i:i+1].max() - ent_px) / 0.0001
                trades.append({
                    "ent_ts_jst": df.index[ent_i] + pd.Timedelta(hours=9),
                    "kind": ent_kind,
                    "pnl": p,
                    "peak": peak_p,
                    "bars_held": i - ent_i,
                })
                in_pos = False
    t = pd.DataFrame(trades)
    print(f"\n  Simulated trades (entry=divergence, exit=pup_end or perfect_dn): {len(t)}")
    if len(t) > 0:
        for kind in t["kind"].unique():
            sub = t[t["kind"] == kind]
            wins = sub[sub["pnl"] > 0]["pnl"].sum()
            loss = -sub[sub["pnl"] <= 0]["pnl"].sum()
            pf = wins / loss if loss > 0 else float("inf")
            wr = (sub["pnl"] > 0).mean() * 100
            print(f"    {kind:<20} N={len(sub):>3} sum={sub['pnl'].sum():+.0f}p mean={sub['pnl'].mean():+.2f}p WR={wr:.1f}% PF={pf:.2f} peak_mean={sub['peak'].mean():+.1f}p")

        print(f"\n  All trades:")
        for _, row in t.iterrows():
            print(f"    {row['ent_ts_jst']!s:<26} JST  kind={row['kind']:<20}  pnl={row['pnl']:+6.1f}p  peak={row['peak']:+6.1f}p  held={row['bars_held']:>3}b")


if __name__ == "__main__":
    main()
