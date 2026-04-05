#!/usr/bin/env python3
"""
Round Number Barrier (RNB) — Phase 2 Backtest
==============================================
USD/JPY BUY-only, 15m + 1H dual-timeframe, 365日長期検証。

Phase 1 確定パラメータ (Cons-20/15):
  TF: 15m, TP=20pip, SL=15pip (RR=1.33)
  Lookback=5bars(75min), Momentum>0.5*ATR
  Zone=±10pip, WickMin=50%, Overshoot<=5pip
  Direction: BUY-only (support barrier bounce)
  Active: UTC 7-20

Phase 2 検証:
  1H × 365d → サンプル拡大 (N=400+目標)
  15m × 60d → Phase1再現性確認 (BUY-only)
  月次安定性 / MaxDD / Win/Loss streak
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from collections import defaultdict


def fetch(symbol: str, interval: str, days: int) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(symbol, period=f"{days}d", interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def compute_atr(df, period=14):
    h, l, pc = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def nearest_round(price, step=0.50):
    return round(price / step) * step


# ── Phase 1 確定パラメータ ──
CFG = {
    "lb": 5, "mom": 0.5, "zone_pips": 10, "wick": 0.50,
    "tp_pips": 20, "sl_pips": 15, "os_pips": 5,
    "spread_pips": 0.4, "pip_mult": 100, "step": 0.50,
    "max_hold_bars": 8,  # 15m=2h, 1h=8h
}


def run_bt(df: pd.DataFrame, cfg: dict, label: str, buy_only: bool = True):
    pm = cfg["pip_mult"]
    sp = cfg["spread_pips"]
    lb = cfg["lb"]
    mom_mult = cfg["mom"]
    zone = cfg["zone_pips"] / pm
    wick_min = cfg["wick"]
    tp_dist = cfg["tp_pips"] / pm
    sl_dist = cfg["sl_pips"] / pm
    os_max = cfg["os_pips"] / pm
    step = cfg["step"]
    max_hold = cfg["max_hold_bars"]

    df = df.copy()
    df["atr"] = compute_atr(df)
    df = df.dropna(subset=["atr"])

    trades = []
    cooldown_until = 0

    for i in range(lb + 14, len(df)):
        if i <= cooldown_until:
            continue

        bar = df.iloc[i]
        h, l, o, c = float(bar["High"]), float(bar["Low"]), float(bar["Open"]), float(bar["Close"])
        atr = float(bar["atr"])
        br = h - l
        if br <= 0 or atr <= 0:
            continue

        # UTC filter
        if hasattr(bar.name, 'hour'):
            hr = bar.name.hour
            if hr < 7 or hr > 20:
                continue

        mid = (h + l) / 2
        rn = nearest_round(mid, step)

        # Zone check
        if min(abs(h - rn), abs(l - rn)) > zone:
            continue

        # Approaching from above → support bounce → BUY
        close_prev = float(df.iloc[i - 1]["Close"])
        approaching_from_above = (l <= rn + os_max) and (close_prev > rn)

        if not approaching_from_above:
            if buy_only:
                continue
            # Check approaching from below for SELL (disabled in BUY-only)
            approaching_from_below = (h >= rn - os_max) and (close_prev < rn)
            if not approaching_from_below:
                continue

        # Momentum
        close_lb = float(df.iloc[i - lb]["Close"])
        momentum = abs(c - close_lb)
        if momentum < atr * mom_mult:
            continue

        if approaching_from_above:
            # Need downward momentum toward round number
            if (close_lb - c) <= 0:
                continue
            # Overshoot check
            overshoot = rn - l
            if overshoot > os_max or overshoot < 0:
                # negative overshoot means didn't reach round number (check differently)
                if l > rn + zone * 0.5:
                    continue
                overshoot = max(0, rn - l)
            # Rejection: lower wick
            lower_wick = min(o, c) - l
            wick_ratio = lower_wick / br
            if wick_ratio < wick_min:
                # Engulfing fallback
                if i + 1 < len(df):
                    nb = df.iloc[i + 1]
                    nb_o, nb_c = float(nb["Open"]), float(nb["Close"])
                    if not (nb_c > nb_o and nb_c > max(o, c) and nb_o < min(o, c)):
                        continue
                    entry_price = nb_c
                    entry_idx = i + 1
                else:
                    continue
            else:
                entry_price = c
                entry_idx = i
            direction = "BUY"
        else:
            # SELL path (only if buy_only=False)
            if (c - close_lb) <= 0:
                continue
            overshoot = h - rn
            if overshoot > os_max:
                continue
            upper_wick = h - max(o, c)
            wick_ratio = upper_wick / br
            if wick_ratio < wick_min:
                if i + 1 < len(df):
                    nb = df.iloc[i + 1]
                    nb_o, nb_c = float(nb["Open"]), float(nb["Close"])
                    if not (nb_c < nb_o and nb_c < min(o, c) and nb_o > max(o, c)):
                        continue
                    entry_price = nb_c
                    entry_idx = i + 1
                else:
                    continue
            else:
                entry_price = c
                entry_idx = i
            direction = "SELL"

        # TP/SL
        if direction == "BUY":
            tp_price = entry_price + tp_dist
            sl_price = entry_price - sl_dist
        else:
            tp_price = entry_price - tp_dist
            sl_price = entry_price + sl_dist

        # Track
        outcome = "TIME_EXIT"
        exit_price = entry_price
        exit_idx = min(entry_idx + max_hold, len(df) - 1)

        for j in range(entry_idx + 1, exit_idx + 1):
            bj = df.iloc[j]
            bh, bl, bc = float(bj["High"]), float(bj["Low"]), float(bj["Close"])
            if direction == "BUY":
                if bl <= sl_price:
                    outcome, exit_price, exit_idx = "SL", sl_price, j
                    break
                if bh >= tp_price:
                    outcome, exit_price, exit_idx = "TP", tp_price, j
                    break
            else:
                if bh >= sl_price:
                    outcome, exit_price, exit_idx = "SL", sl_price, j
                    break
                if bl <= tp_price:
                    outcome, exit_price, exit_idx = "TP", tp_price, j
                    break
            exit_price = bc

        pnl = (exit_price - entry_price) * pm if direction == "BUY" else (entry_price - exit_price) * pm
        pnl -= sp

        dt = bar.name
        trades.append({
            "date": str(dt.date()) if hasattr(dt, 'date') else str(dt)[:10],
            "time": str(dt),
            "direction": direction,
            "rn": round(rn, 2),
            "is_00": abs(rn % 1.0) < 0.01 or abs(rn % 1.0 - 1.0) < 0.01,
            "entry": round(entry_price, 3),
            "exit": round(exit_price, 3),
            "pnl": round(pnl, 1),
            "outcome": outcome,
            "mom_pips": round(momentum * pm, 1),
            "atr_pips": round(atr * pm, 1),
            "hour": hr if hasattr(bar.name, 'hour') else 0,
        })
        cooldown_until = exit_idx + 2

    # ── 分析 ──
    n = len(trades)
    if n == 0:
        print(f"  {label}: NO TRADES")
        return None

    wins = sum(1 for t in trades if t["pnl"] > 0)
    total = sum(t["pnl"] for t in trades)
    wr = wins / n * 100
    ev = total / n

    dates = [t["date"] for t in trades]
    d_span = (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[0])).days + 1
    months = d_span / 30
    mo_pips = total / months if months > 0 else 0

    tp_c = sum(1 for t in trades if t["outcome"] == "TP")
    sl_c = sum(1 for t in trades if t["outcome"] == "SL")
    te_c = sum(1 for t in trades if t["outcome"] == "TIME_EXIT")

    # Max DD (cumulative)
    cum = 0
    peak = 0
    max_dd = 0
    for t in trades:
        cum += t["pnl"]
        peak = max(peak, cum)
        dd = peak - cum
        max_dd = max(max_dd, dd)

    # Win/Loss streaks
    max_win_streak = max_loss_streak = 0
    cur_w = cur_l = 0
    for t in trades:
        if t["pnl"] > 0:
            cur_w += 1
            cur_l = 0
        else:
            cur_l += 1
            cur_w = 0
        max_win_streak = max(max_win_streak, cur_w)
        max_loss_streak = max(max_loss_streak, cur_l)

    # Profit factor
    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    print(f"  Period: {dates[0]} → {dates[-1]} ({d_span}d, {months:.1f}mo)")
    print(f"  Trades: {n} | WR: {wr:.1f}% | EV: {ev:+.1f}pip/trade")
    print(f"  Total: {total:+.1f}pip | Monthly: {mo_pips:+.1f}pip/mo")
    print(f"  TP: {tp_c} | SL: {sl_c} | TimeExit: {te_c}")
    print(f"  MaxDD: {max_dd:.1f}pip | PF: {pf:.2f}")
    print(f"  Win streak: {max_win_streak} | Loss streak: {max_loss_streak}")
    print(f"  Gross profit: {gross_profit:+.1f} | Gross loss: {gross_loss:.1f}")

    # .00 vs .50
    dz = [t for t in trades if t["is_00"]]
    hz = [t for t in trades if not t["is_00"]]
    if dz:
        dz_wr = sum(1 for t in dz if t["pnl"] > 0) / len(dz) * 100
        dz_ev = sum(t["pnl"] for t in dz) / len(dz)
        print(f"  .00 level: {len(dz)}t WR={dz_wr:.1f}% EV={dz_ev:+.1f}")
    if hz:
        hz_wr = sum(1 for t in hz if t["pnl"] > 0) / len(hz) * 100
        hz_ev = sum(t["pnl"] for t in hz) / len(hz)
        print(f"  .50 level: {len(hz)}t WR={hz_wr:.1f}% EV={hz_ev:+.1f}")

    # Hour analysis
    print(f"\n  ── Hourly Distribution ──")
    hour_grp = defaultdict(list)
    for t in trades:
        hour_grp[t["hour"]].append(t["pnl"])
    for hr in sorted(hour_grp.keys()):
        hh = hour_grp[hr]
        h_wr = sum(1 for p in hh if p > 0) / len(hh) * 100
        h_ev = sum(hh) / len(hh)
        marker = " ★" if h_ev > 3 else ""
        print(f"    UTC {hr:02d}: {len(hh):>3}t WR={h_wr:.0f}% EV={h_ev:+.1f}{marker}")

    # Spread sensitivity
    print(f"\n  ── Spread Sensitivity ──")
    for sp_test in [0.0, 0.2, 0.4, 0.8, 1.0, 2.0, 3.0]:
        adj = sum(t["pnl"] + sp - sp_test for t in trades)
        marker = " ←current" if abs(sp_test - sp) < 0.01 else ""
        print(f"    {sp_test:.1f}pip: EV={adj/n:+.1f} Total={adj:+.1f}{marker}")

    # Monthly breakdown
    print(f"\n  ── Monthly Breakdown ──")
    monthly = defaultdict(list)
    for t in trades:
        monthly[t["date"][:7]].append(t["pnl"])

    positive_months = 0
    total_months = 0
    for ym in sorted(monthly.keys()):
        m = monthly[ym]
        m_t = sum(m)
        m_wr = sum(1 for p in m if p > 0) / len(m) * 100
        total_months += 1
        if m_t > 0:
            positive_months += 1
        print(f"    {ym}: {len(m):>3}t WR={m_wr:.0f}% {m_t:+.1f}pip")

    print(f"  Positive months: {positive_months}/{total_months} ({positive_months/total_months*100:.0f}%)")

    # Equity curve (cumulative pips)
    print(f"\n  ── Equity Curve (cumulative, every 20 trades) ──")
    cum_eq = 0
    for idx, t in enumerate(trades):
        cum_eq += t["pnl"]
        if (idx + 1) % 20 == 0 or idx == n - 1:
            bar_len = max(0, int(cum_eq / 10))
            print(f"    #{idx+1:>4}: {cum_eq:>+8.1f}pip {'█' * min(bar_len, 40)}")

    return {
        "n": n, "wr": round(wr, 1), "ev": round(ev, 1),
        "total": round(total, 1), "mo_pips": round(mo_pips, 1),
        "max_dd": round(max_dd, 1), "pf": round(pf, 2),
        "max_win_streak": max_win_streak, "max_loss_streak": max_loss_streak,
        "positive_months": positive_months, "total_months": total_months,
        "label": label,
    }


if __name__ == "__main__":
    print("=" * 70)
    print("  RNB Phase 2 — USD/JPY BUY-only 長期検証")
    print("  Config: Cons-20/15 (TP=20/SL=15, LB=5, Mom=0.5ATR)")
    print("  Spread: 0.4pip (OANDA)")
    print("=" * 70)

    sym = "USDJPY=X"

    # ── 1H × 365d (BUY-only) ──
    print("\n\n[1] Fetching 1H × 400d data...")
    df_1h = fetch(sym, "1h", 400)
    print(f"    Bars: {len(df_1h)}")

    cfg_1h = CFG.copy()
    cfg_1h["max_hold_bars"] = 4   # 1h: 4bars = 4h
    r_1h_buy = run_bt(df_1h, cfg_1h, "USD/JPY 1H × 400d BUY-only", buy_only=True)

    # 1H both-direction for comparison
    r_1h_both = run_bt(df_1h, cfg_1h, "USD/JPY 1H × 400d BOTH (reference)", buy_only=False)

    # ── 15m × 60d (BUY-only) — Phase 1 再現確認 ──
    print("\n\n[2] Fetching 15m × 60d data...")
    df_15m = fetch(sym, "15m", 60)
    print(f"    Bars: {len(df_15m)}")

    cfg_15m = CFG.copy()
    cfg_15m["max_hold_bars"] = 8   # 15m: 8bars = 2h
    r_15m_buy = run_bt(df_15m, cfg_15m, "USD/JPY 15m × 60d BUY-only", buy_only=True)

    # 15m both for comparison
    r_15m_both = run_bt(df_15m, cfg_15m, "USD/JPY 15m × 60d BOTH (reference)", buy_only=False)

    # ── Final Summary ──
    print(f"\n\n{'='*70}")
    print("  FINAL SUMMARY — RNB Phase 2")
    print(f"{'='*70}")
    print(f"\n  {'Config':<35} {'N':>5} {'WR':>6} {'EV':>8} {'Total':>9} {'Mo':>9} {'MaxDD':>7} {'PF':>5}")
    print(f"  {'-'*35} {'-'*5} {'-'*6} {'-'*8} {'-'*9} {'-'*9} {'-'*7} {'-'*5}")
    for r in [r_1h_buy, r_1h_both, r_15m_buy, r_15m_both]:
        if r:
            print(f"  {r['label']:<35} {r['n']:>5} {r['wr']:>5.1f}% {r['ev']:>+7.1f} "
                  f"{r['total']:>+8.1f} {r['mo_pips']:>+8.1f} {r['max_dd']:>6.1f} {r['pf']:>4.2f}")

    # BUY-only improvement
    if r_1h_buy and r_1h_both:
        delta = r_1h_buy["ev"] - r_1h_both["ev"]
        print(f"\n  BUY-only filter impact (1H): EV delta = {delta:+.1f}pip/trade")
    if r_15m_buy and r_15m_both:
        delta = r_15m_buy["ev"] - r_15m_both["ev"]
        print(f"  BUY-only filter impact (15m): EV delta = {delta:+.1f}pip/trade")

    # Final verdict
    print(f"\n  ── VERDICT ──")
    if r_1h_buy:
        pm = r_1h_buy["positive_months"]
        tm = r_1h_buy["total_months"]
        viable = r_1h_buy["ev"] > 0 and r_1h_buy["n"] >= 100 and pm / tm >= 0.6
        print(f"  1H BUY-only: EV={r_1h_buy['ev']:+.1f} N={r_1h_buy['n']} "
              f"Months+={pm}/{tm} MaxDD={r_1h_buy['max_dd']} PF={r_1h_buy['pf']:.2f}")
        print(f"  → {'PRODUCTION READY' if viable else 'NEEDS REVIEW'}")
