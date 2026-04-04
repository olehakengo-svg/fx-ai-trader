#!/usr/bin/env python3
"""
London Close Reversal (LCR) — Phase 2 Backtest
================================================
1H data × 400日 でペア別 Extension Ratio フィルター + Engulfing確認付きBT。

ペア別パラメータ:
  GBP/JPY: Extension 0.5-1.2 ATR, spread 3.0pip
  EUR/JPY: Extension 1.0-1.6 ATR, spread 2.0pip
  GBP/USD: Extension 1.0-1.5 ATR, spread 1.5pip

エントリー: UTC 15bar close (= 16:00) での反転トレード
エグジット: ATR-based TP/SL or UTC 20:00 time exit
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from collections import defaultdict


PAIRS = {
    "GBPJPY=X": {
        "label": "GBP/JPY",
        "pip_mult": 100,
        "ext_min": 0.5, "ext_max": 1.2,
        "spread_pips": 3.0,
    },
    "EURJPY=X": {
        "label": "EUR/JPY",
        "pip_mult": 100,
        "ext_min": 1.0, "ext_max": 1.6,
        "spread_pips": 2.0,
    },
    "GBPUSD=X": {
        "label": "GBP/USD",
        "pip_mult": 10000,
        "ext_min": 1.0, "ext_max": 1.5,
        "spread_pips": 1.5,
    },
}

# TP/SL ATR multiples to test
TP_SL_CONFIGS = [
    {"tp": 0.6, "sl": 0.8, "label": "TP0.6/SL0.8"},
    {"tp": 0.8, "sl": 1.0, "label": "TP0.8/SL1.0"},
    {"tp": 1.0, "sl": 1.0, "label": "TP1.0/SL1.0"},
    {"tp": 1.0, "sl": 0.8, "label": "TP1.0/SL0.8"},
    {"tp": 1.2, "sl": 1.0, "label": "TP1.2/SL1.0"},
]


def fetch_1h(symbol: str, days: int = 400) -> pd.DataFrame:
    """yfinance 1H data fetch"""
    import yfinance as yf
    df = yf.download(symbol, period=f"{days}d", interval="1h", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _simulate_trades(day_data: list, tp_atr: float, sl_atr: float,
                     spread_pips: float, pip_mult: float) -> list:
    """共通トレードシミュレーション: TP/SL比率テスト用"""
    trades = []
    for d in day_data:
        atr = d["atr"]
        entry_price = d["entry_price"]
        direction = d["direction"]
        post_bars = d["post_bars"]

        tp_dist = atr * tp_atr
        sl_dist = atr * sl_atr

        if direction == "BUY":
            tp_price = entry_price + tp_dist
            sl_price = entry_price - sl_dist
        else:
            tp_price = entry_price - tp_dist
            sl_price = entry_price + sl_dist

        outcome = "TIME_EXIT"
        exit_price = entry_price

        for bh, bl, bc, bhr in post_bars:
            if direction == "BUY":
                # SL first (pessimistic)
                if bl <= sl_price:
                    outcome, exit_price = "SL", sl_price
                    break
                if bh >= tp_price:
                    outcome, exit_price = "TP", tp_price
                    break
            else:
                if bh >= sl_price:
                    outcome, exit_price = "SL", sl_price
                    break
                if bl <= tp_price:
                    outcome, exit_price = "TP", tp_price
                    break
            exit_price = bc

        if direction == "BUY":
            pnl_pips = (exit_price - entry_price) * pip_mult
        else:
            pnl_pips = (entry_price - exit_price) * pip_mult

        pnl_pips -= spread_pips

        trades.append({
            "date": d["date"],
            "direction": direction,
            "ext_ratio": d["ext_ratio"],
            "pnl_pips": round(pnl_pips, 1),
            "outcome": outcome,
            "is_engulfing": d["is_engulfing"],
            "atr_pips": round(atr * pip_mult, 1),
        })
    return trades


def run_bt(symbol: str, cfg: dict, days: int = 400):
    label = cfg["label"]
    pip_mult = cfg["pip_mult"]
    ext_min, ext_max = cfg["ext_min"], cfg["ext_max"]
    spread_pips = cfg["spread_pips"]

    print(f"\n{'='*70}")
    print(f"  {label} — LCR Phase 2 Backtest ({days}d, 1H)")
    print(f"  Extension: {ext_min}-{ext_max} ATR | Spread: {spread_pips}pip")
    print(f"{'='*70}")

    df = fetch_1h(symbol, days=days)
    if df is None or len(df) < 200:
        print("  ERROR: Insufficient data")
        return None

    df["atr"] = compute_atr(df)
    df = df.dropna(subset=["atr"])
    print(f"  Bars: {len(df)}")

    df["date"] = df.index.date
    dates = sorted(df["date"].unique())

    # ── Phase 1: 全日のエントリー候補データ収集 ──
    day_data = []

    for date in dates:
        day_df = df[df["date"] == date]
        if len(day_df) < 8:
            continue
        if day_df.index[0].weekday() >= 5:
            continue

        # London session bars: UTC 07-14
        ldn_bars = day_df[[7 <= h.hour <= 14 for h in day_df.index]]
        if len(ldn_bars) < 4:
            continue

        ldn_open = float(ldn_bars.iloc[0]["Open"])
        ldn_close = float(ldn_bars.iloc[-1]["Close"])
        ldn_direction = ldn_close - ldn_open
        is_bull = ldn_direction > 0

        atr = float(ldn_bars.iloc[-1]["atr"])
        if atr <= 0:
            continue

        ext_ratio = abs(ldn_direction) / atr

        # Extension ratio filter
        if ext_ratio < ext_min or ext_ratio > ext_max:
            continue

        # Reversal confirmation bar (UTC 15)
        rev_bars = day_df[[h.hour == 15 for h in day_df.index]]
        if len(rev_bars) == 0:
            continue
        rev_bar = rev_bars.iloc[0]
        rev_open = float(rev_bar["Open"])
        rev_close = float(rev_bar["Close"])
        rev_body = rev_close - rev_open

        # Reversal direction check
        if is_bull and rev_body >= 0:
            continue
        if not is_bull and rev_body <= 0:
            continue

        # Engulfing check (1h proxy): reversal bar body > 70% of previous bar body
        prev_body = abs(float(ldn_bars.iloc[-1]["Close"]) - float(ldn_bars.iloc[-1]["Open"]))
        is_engulfing = abs(rev_body) > prev_body * 0.7

        direction = "SELL" if is_bull else "BUY"

        # Post-entry bars (UTC 16-20)
        post_bars_df = day_df[[16 <= h.hour <= 20 for h in day_df.index]]
        post_bars = [(float(r["High"]), float(r["Low"]), float(r["Close"]), r.name.hour)
                     for _, r in post_bars_df.iterrows()]

        day_data.append({
            "date": str(date),
            "direction": direction,
            "ext_ratio": round(ext_ratio, 2),
            "entry_price": rev_close,
            "atr": atr,
            "is_engulfing": is_engulfing,
            "post_bars": post_bars,
        })

    trading_days = len(day_data)
    print(f"  Qualifying days: {trading_days} / {len(dates)} trading days")

    if trading_days == 0:
        print("  NO TRADES generated")
        return None

    # ── Phase 2: TP/SL 感度分析 ──
    print(f"\n  ── TP/SL Sensitivity (spread={spread_pips}pip) ──")
    print(f"  {'Config':<16} {'Trades':>6} {'WR':>6} {'EV':>9} {'Total':>9} {'Mo.pips':>9}")
    print(f"  {'-'*16} {'-'*6} {'-'*6} {'-'*9} {'-'*9} {'-'*9}")

    best_cfg = None
    best_ev = -9999

    for tsc in TP_SL_CONFIGS:
        trades = _simulate_trades(day_data, tsc["tp"], tsc["sl"], spread_pips, pip_mult)
        n = len(trades)
        wins = sum(1 for t in trades if t["pnl_pips"] > 0)
        total = sum(t["pnl_pips"] for t in trades)
        wr = wins / n * 100
        ev = total / n
        d_span = (pd.Timestamp(trades[-1]["date"]) - pd.Timestamp(trades[0]["date"])).days + 1
        mo_pips = total / (d_span / 30) if d_span > 0 else 0
        print(f"  {tsc['label']:<16} {n:>6} {wr:>5.1f}% {ev:>+8.1f} {total:>+8.1f} {mo_pips:>+8.1f}")
        if ev > best_ev:
            best_ev = ev
            best_cfg = tsc

    # ── Phase 3: ベスト構成で詳細分析 ──
    print(f"\n  ★ Best config: {best_cfg['label']}")
    trades = _simulate_trades(day_data, best_cfg["tp"], best_cfg["sl"], spread_pips, pip_mult)
    n = len(trades)
    wins = sum(1 for t in trades if t["pnl_pips"] > 0)
    total = sum(t["pnl_pips"] for t in trades)
    wr = wins / n * 100
    ev = total / n

    first_d, last_d = trades[0]["date"], trades[-1]["date"]
    d_span = (pd.Timestamp(last_d) - pd.Timestamp(first_d)).days + 1
    months = d_span / 30
    mo_pips = total / months if months > 0 else 0

    print(f"\n  ── Best Results (spread={spread_pips}pip deducted) ──")
    print(f"  Period: {first_d} → {last_d} ({d_span}d, {months:.1f}mo)")
    print(f"  Trades: {n} | WR: {wr:.1f}% | EV: {ev:+.1f}pip/trade")
    print(f"  Total: {total:+.1f}pip | Monthly: {mo_pips:+.1f}pip/mo")

    tp_c = sum(1 for t in trades if t["outcome"] == "TP")
    sl_c = sum(1 for t in trades if t["outcome"] == "SL")
    te_c = sum(1 for t in trades if t["outcome"] == "TIME_EXIT")
    print(f"  TP: {tp_c} | SL: {sl_c} | TimeExit: {te_c}")

    # Engulfing filter
    eng = [t for t in trades if t["is_engulfing"]]
    non_eng = [t for t in trades if not t["is_engulfing"]]
    print(f"\n  ── Engulfing Filter Impact ──")
    if eng:
        e_n = len(eng)
        e_wr = sum(1 for t in eng if t["pnl_pips"] > 0) / e_n * 100
        e_ev = sum(t["pnl_pips"] for t in eng) / e_n
        e_tot = sum(t["pnl_pips"] for t in eng)
        print(f"  Engulfing:     {e_n}t WR={e_wr:.1f}% EV={e_ev:+.1f} Total={e_tot:+.1f}pip")
    if non_eng:
        ne_n = len(non_eng)
        ne_wr = sum(1 for t in non_eng if t["pnl_pips"] > 0) / ne_n * 100
        ne_ev = sum(t["pnl_pips"] for t in non_eng) / ne_n
        print(f"  Non-engulfing: {ne_n}t WR={ne_wr:.1f}% EV={ne_ev:+.1f}")

    # Direction breakdown
    buys = [t for t in trades if t["direction"] == "BUY"]
    sells = [t for t in trades if t["direction"] == "SELL"]
    print(f"\n  ── Direction ──")
    if buys:
        b_wr = sum(1 for t in buys if t["pnl_pips"] > 0) / len(buys) * 100
        b_ev = sum(t["pnl_pips"] for t in buys) / len(buys)
        print(f"  BUY:  {len(buys):>3}t WR={b_wr:.1f}% EV={b_ev:+.1f}pip")
    if sells:
        s_wr = sum(1 for t in sells if t["pnl_pips"] > 0) / len(sells) * 100
        s_ev = sum(t["pnl_pips"] for t in sells) / len(sells)
        print(f"  SELL: {len(sells):>3}t WR={s_wr:.1f}% EV={s_ev:+.1f}pip")

    # Spread sensitivity
    print(f"\n  ── Spread Sensitivity ──")
    for sp in [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]:
        adj = sum(t["pnl_pips"] + spread_pips - sp for t in trades)
        print(f"  Spread={sp:.1f}pip: Total={adj:+.1f}pip EV={adj/n:+.1f}pip")

    # Monthly breakdown
    print(f"\n  ── Monthly Breakdown ──")
    monthly = defaultdict(list)
    for t in trades:
        monthly[t["date"][:7]].append(t["pnl_pips"])
    for ym in sorted(monthly.keys()):
        m = monthly[ym]
        m_t = sum(m)
        m_wr = sum(1 for p in m if p > 0) / len(m) * 100
        print(f"  {ym}: {len(m):>3}t WR={m_wr:.0f}% {m_t:+.1f}pip")

    return {
        "label": label,
        "trades": n,
        "wr": round(wr, 1),
        "ev": round(ev, 1),
        "total_pips": round(total, 1),
        "monthly_pips": round(mo_pips, 1),
        "spread_pips": spread_pips,
        "best_config": best_cfg["label"],
        "eng_n": len(eng) if eng else 0,
        "eng_wr": round(e_wr, 1) if eng else 0,
        "eng_ev": round(e_ev, 1) if eng else 0,
    }


# ── Extension Ratio 感度分析 ──
def run_ext_sensitivity(symbol: str, cfg: dict, days: int = 400):
    """Extension Ratioレンジの最適化グリッドサーチ"""
    label = cfg["label"]
    pip_mult = cfg["pip_mult"]
    spread_pips = cfg["spread_pips"]

    df = fetch_1h(symbol, days=days)
    if df is None or len(df) < 200:
        return
    df["atr"] = compute_atr(df)
    df = df.dropna(subset=["atr"])
    df["date"] = df.index.date
    dates = sorted(df["date"].unique())

    # 全日データ収集 (フィルターなし)
    all_days = []
    for date in dates:
        day_df = df[df["date"] == date]
        if len(day_df) < 8 or day_df.index[0].weekday() >= 5:
            continue
        ldn_bars = day_df[[7 <= h.hour <= 14 for h in day_df.index]]
        if len(ldn_bars) < 4:
            continue
        ldn_open = float(ldn_bars.iloc[0]["Open"])
        ldn_close = float(ldn_bars.iloc[-1]["Close"])
        ldn_dir = ldn_close - ldn_open
        is_bull = ldn_dir > 0
        atr = float(ldn_bars.iloc[-1]["atr"])
        if atr <= 0:
            continue
        ext_ratio = abs(ldn_dir) / atr

        rev_bars = day_df[[h.hour == 15 for h in day_df.index]]
        if len(rev_bars) == 0:
            continue
        rev_close = float(rev_bars.iloc[0]["Close"])
        rev_open = float(rev_bars.iloc[0]["Open"])
        rev_body = rev_close - rev_open
        if is_bull and rev_body >= 0:
            continue
        if not is_bull and rev_body <= 0:
            continue

        prev_body = abs(float(ldn_bars.iloc[-1]["Close"]) - float(ldn_bars.iloc[-1]["Open"]))
        is_eng = abs(rev_body) > prev_body * 0.7
        direction = "SELL" if is_bull else "BUY"
        post_df = day_df[[16 <= h.hour <= 20 for h in day_df.index]]
        post_bars = [(float(r["High"]), float(r["Low"]), float(r["Close"]), r.name.hour)
                     for _, r in post_df.iterrows()]

        all_days.append({
            "date": str(date), "direction": direction,
            "ext_ratio": ext_ratio, "entry_price": rev_close,
            "atr": atr, "is_engulfing": is_eng, "post_bars": post_bars,
        })

    print(f"\n  ── {label} Extension Ratio Grid Search ──")
    print(f"  Total qualifying days (no ext filter): {len(all_days)}")
    print(f"  {'Range':<14} {'N':>4} {'WR':>6} {'EV':>8} {'Total':>9}")
    print(f"  {'-'*14} {'-'*4} {'-'*6} {'-'*8} {'-'*9}")

    for lo in [0.3, 0.5, 0.7, 1.0]:
        for hi in [0.8, 1.0, 1.2, 1.5, 2.0]:
            if lo >= hi:
                continue
            subset = [d for d in all_days if lo <= d["ext_ratio"] <= hi]
            if len(subset) < 10:
                continue
            trades = _simulate_trades(subset, 0.8, 1.0, spread_pips, pip_mult)
            n = len(trades)
            wins = sum(1 for t in trades if t["pnl_pips"] > 0)
            total = sum(t["pnl_pips"] for t in trades)
            wr = wins / n * 100
            ev = total / n
            marker = " ★" if ev > 2.0 else ""
            print(f"  {lo:.1f}-{hi:.1f} ATR   {n:>4} {wr:>5.1f}% {ev:>+7.1f} {total:>+8.1f}{marker}")


if __name__ == "__main__":
    print("=" * 70)
    print("  LCR Phase 2 Backtest")
    print("  Pair-specific Extension Ratio + Engulfing + TP/SL Sensitivity")
    print("  Data: yfinance 1H × 400d | Entry: UTC 16:00 | Exit: TP/SL/UTC20")
    print("=" * 70)

    results = {}
    for sym, cfg in PAIRS.items():
        r = run_bt(sym, cfg, days=400)
        if r:
            results[sym] = r

    # Extension Ratio sensitivity (after main BT)
    print(f"\n\n{'='*70}")
    print("  Extension Ratio Sensitivity Analysis")
    print(f"{'='*70}")
    for sym, cfg in PAIRS.items():
        run_ext_sensitivity(sym, cfg, days=400)

    # ── Final Summary ──
    print(f"\n\n{'='*70}")
    print("  FINAL SUMMARY — LCR Phase 2 Backtest")
    print(f"{'='*70}")
    print(f"  {'Pair':<10} {'N':>5} {'WR':>6} {'EV':>9} {'Total':>9} {'Mo':>9} {'Spread':>7} {'Best TP/SL':<16}")
    print(f"  {'-'*10} {'-'*5} {'-'*6} {'-'*9} {'-'*9} {'-'*9} {'-'*7} {'-'*16}")
    for sym, r in results.items():
        print(f"  {r['label']:<10} {r['trades']:>5} {r['wr']:>5.1f}% {r['ev']:>+8.1f} "
              f"{r['total_pips']:>+8.1f} {r['monthly_pips']:>+8.1f} {r['spread_pips']:>6.1f} {r['best_config']}")

    print(f"\n  ── Viability Verdict ──")
    for sym, r in results.items():
        viable = r["ev"] > 0 and r["trades"] >= 50
        verdict = "VIABLE" if viable else "MARGINAL" if r["ev"] > -2 else "NOT VIABLE"
        print(f"  {r['label']}: EV={r['ev']:+.1f}pip (spread={r['spread_pips']}pip込) "
              f"N={r['trades']} → {verdict}")

    print(f"\n  ── Engulfing Filter Verdict ──")
    for sym, r in results.items():
        if r["eng_n"] > 0:
            delta = r["eng_ev"] - r["ev"]
            better = "BETTER" if delta > 1 else "SIMILAR" if abs(delta) <= 1 else "WORSE"
            print(f"  {r['label']}: Engulfing EV={r['eng_ev']:+.1f} vs All EV={r['ev']:+.1f} "
                  f"(delta={delta:+.1f}) → {better}")
