#!/usr/bin/env python3
"""
Round Number Barrier (RNB) — Phase 1 Backtest
==============================================
クロス円 (USD/JPY, EUR/JPY, GBP/JPY) のキリ番（.00/.50）で
オプションバリア防衛・ストップ狩り反発を狙うスキャルプ〜DT戦略。

コアエッジ:
  機関投資家のオプション防衛フローが .00/.50 に集中。
  急接近 (momentum) + 反発確認 (rejection wick / engulfing) で
  ダマシを排除し、バリア防衛リバウンドを捕捉。

データ: yfinance 15m × 60d (+ 5m × 60d 比較)
対象: USD/JPY, EUR/JPY, GBP/JPY
"""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from collections import defaultdict


PAIRS = {
    "USDJPY=X": {
        "label": "USD/JPY", "pip_mult": 100,
        "spread": 0.4,   # OANDA実測
        "round_step": 0.50,  # .00 and .50
    },
    "EURJPY=X": {
        "label": "EUR/JPY", "pip_mult": 100,
        "spread": 1.5,   # UTC 12-15 typical
        "round_step": 0.50,
    },
    "GBPJPY=X": {
        "label": "GBP/JPY", "pip_mult": 100,
        "spread": 3.0,
        "round_step": 0.50,
    },
}

# ── パラメータグリッド ──
PARAM_GRID = {
    # Momentum: 直近 lookback 本で round number ±zone に急接近
    "lookback_bars": [3, 5, 8],          # 15m: 45min / 75min / 2h
    "momentum_atr_mult": [0.3, 0.5, 0.8],  # ATR倍率 (最低限の急接近)
    # Zone: round number ±zone_pips に入ったら監視開始
    "zone_pips": [8, 10, 15],
    # Rejection: wick ratio (ヒゲ/全体レンジ)
    "wick_ratio_min": [0.50, 0.60],
    # TP/SL
    "tp_pips": [12, 18, 25],
    "sl_pips": [10, 12, 15],
    # Overshoot: round numberを超えてOKな幅 (pips)
    "overshoot_max_pips": [3, 5],
}

# 探索量を抑えるためベスト候補のみ
CONFIGS = [
    # Tight scalp
    {"lb": 3, "mom": 0.5, "zone": 10, "wick": 0.50, "tp": 12, "sl": 10, "os": 5, "label": "Tight-12/10"},
    {"lb": 3, "mom": 0.5, "zone": 10, "wick": 0.60, "tp": 12, "sl": 10, "os": 5, "label": "Tight-wick60"},
    # Standard
    {"lb": 5, "mom": 0.5, "zone": 10, "wick": 0.50, "tp": 18, "sl": 12, "os": 5, "label": "Std-18/12"},
    {"lb": 5, "mom": 0.3, "zone": 10, "wick": 0.50, "tp": 18, "sl": 12, "os": 5, "label": "Std-mom30"},
    {"lb": 5, "mom": 0.5, "zone": 15, "wick": 0.50, "tp": 18, "sl": 12, "os": 5, "label": "Std-zone15"},
    # Wide DT
    {"lb": 8, "mom": 0.5, "zone": 15, "wick": 0.50, "tp": 25, "sl": 15, "os": 5, "label": "Wide-25/15"},
    {"lb": 5, "mom": 0.5, "zone": 10, "wick": 0.50, "tp": 25, "sl": 12, "os": 5, "label": "Wide-25/12"},
    # Aggressive momentum
    {"lb": 3, "mom": 0.8, "zone": 8, "wick": 0.50, "tp": 15, "sl": 10, "os": 3, "label": "Aggro-15/10"},
    # Conservative engulfing
    {"lb": 5, "mom": 0.5, "zone": 10, "wick": 0.50, "tp": 20, "sl": 15, "os": 5, "label": "Cons-20/15"},
]


def fetch_data(symbol: str, interval: str = "15m", days: int = 60) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(symbol, period=f"{days}d", interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, pc = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def nearest_round(price: float, step: float = 0.50) -> float:
    """最寄りのキリ番を返す"""
    return round(price / step) * step


def run_bt_config(df: pd.DataFrame, cfg: dict, pair_cfg: dict) -> list:
    """1構成でのBT実行"""
    pip_mult = pair_cfg["pip_mult"]
    spread = pair_cfg["spread"]
    step = pair_cfg["round_step"]

    lb = cfg["lb"]
    mom_mult = cfg["mom"]
    zone = cfg["zone"] / pip_mult     # pips → price
    wick_min = cfg["wick"]
    tp_pips = cfg["tp"]
    sl_pips = cfg["sl"]
    os_max = cfg["os"] / pip_mult     # pips → price

    tp_dist = tp_pips / pip_mult
    sl_dist = sl_pips / pip_mult

    df = df.copy()
    df["atr"] = compute_atr(df)
    df = df.dropna(subset=["atr"])
    if len(df) < lb + 20:
        return []

    trades = []
    cooldown_until = 0  # bar index cooldown

    for i in range(lb + 14, len(df)):
        if i <= cooldown_until:
            continue

        bar = df.iloc[i]
        h = float(bar["High"])
        l = float(bar["Low"])
        o = float(bar["Open"])
        c = float(bar["Close"])
        atr = float(bar["atr"])
        bar_range = h - l
        if bar_range <= 0 or atr <= 0:
            continue

        # UTC filter: London+NY (7-20) のみ
        if hasattr(bar.name, 'hour'):
            hr = bar.name.hour
            if hr < 7 or hr > 20:
                continue

        # ── 最寄りキリ番 ──
        mid = (h + l) / 2
        rn = nearest_round(mid, step)

        # ── Zone check: bar が round number ± zone に入っているか ──
        dist_high = abs(h - rn)
        dist_low = abs(l - rn)
        if min(dist_high, dist_low) > zone:
            continue  # zone外

        # ── Approaching direction 判定 ──
        # 下から接近 (resistance) or 上から接近 (support)
        close_prev = float(df.iloc[i - 1]["Close"])

        approaching_from_below = (h >= rn - os_max) and (close_prev < rn)
        approaching_from_above = (l <= rn + os_max) and (close_prev > rn)

        if not approaching_from_below and not approaching_from_above:
            continue

        # ── Momentum check: 直前 lb 本で急接近 ──
        close_lb_ago = float(df.iloc[i - lb]["Close"])
        momentum = abs(c - close_lb_ago)
        mom_threshold = atr * mom_mult

        if momentum < mom_threshold:
            continue

        # Direction check: momentum の方向が round に向かっているか
        if approaching_from_below and (c - close_lb_ago) <= 0:
            continue  # 上昇モメンタムが必要
        if approaching_from_above and (close_lb_ago - c) <= 0:
            continue  # 下降モメンタムが必要

        # ── Overshoot check ──
        if approaching_from_below:
            overshoot = h - rn
            if overshoot > os_max:
                continue  # ブレイクスルー（バリア崩壊）
        else:
            overshoot = rn - l
            if overshoot > os_max:
                continue

        # ── Rejection (wick) check ──
        if approaching_from_below:
            # 上ヒゲが長い = resistance rejection
            upper_wick = h - max(o, c)
            wick_ratio = upper_wick / bar_range
            if wick_ratio < wick_min:
                # Engulfing fallback: 次の足で包み足確認
                if i + 1 < len(df):
                    next_bar = df.iloc[i + 1]
                    nb_o, nb_c = float(next_bar["Open"]), float(next_bar["Close"])
                    # 次の足が陰線で、前足の実体を包む
                    if not (nb_c < nb_o and nb_c < min(o, c) and nb_o > max(o, c)):
                        continue
                    # Engulfing confirmed: entry at next bar close
                    entry_price = nb_c
                    entry_idx = i + 1
                else:
                    continue
            else:
                entry_price = c
                entry_idx = i
            direction = "SELL"  # barrier resistance → sell
        else:
            # 下ヒゲが長い = support rejection
            lower_wick = min(o, c) - l
            wick_ratio = lower_wick / bar_range
            if wick_ratio < wick_min:
                # Engulfing fallback
                if i + 1 < len(df):
                    next_bar = df.iloc[i + 1]
                    nb_o, nb_c = float(next_bar["Open"]), float(next_bar["Close"])
                    if not (nb_c > nb_o and nb_c > max(o, c) and nb_o < min(o, c)):
                        continue
                    entry_price = nb_c
                    entry_idx = i + 1
                else:
                    continue
            else:
                entry_price = c
                entry_idx = i
            direction = "BUY"  # barrier support → buy

        # ── TP/SL 設定 ──
        if direction == "BUY":
            tp_price = entry_price + tp_dist
            sl_price = entry_price - sl_dist
        else:
            tp_price = entry_price - tp_dist
            sl_price = entry_price + sl_dist

        # ── Trade tracking (最大8本 = 2h for 15m) ──
        outcome = "TIME_EXIT"
        exit_price = entry_price
        max_bars = 8
        exit_idx = min(entry_idx + max_bars, len(df) - 1)

        for j in range(entry_idx + 1, exit_idx + 1):
            bj = df.iloc[j]
            bh, bl, bc = float(bj["High"]), float(bj["Low"]), float(bj["Close"])

            if direction == "BUY":
                if bl <= sl_price:
                    outcome, exit_price = "SL", sl_price
                    exit_idx = j
                    break
                if bh >= tp_price:
                    outcome, exit_price = "TP", tp_price
                    exit_idx = j
                    break
            else:
                if bh >= sl_price:
                    outcome, exit_price = "SL", sl_price
                    exit_idx = j
                    break
                if bl <= tp_price:
                    outcome, exit_price = "TP", tp_price
                    exit_idx = j
                    break
            exit_price = bc

        # PnL
        if direction == "BUY":
            pnl_pips = (exit_price - entry_price) * pip_mult
        else:
            pnl_pips = (entry_price - exit_price) * pip_mult
        pnl_pips -= spread

        trades.append({
            "date": str(bar.name.date()) if hasattr(bar.name, 'date') else str(bar.name),
            "time": str(bar.name),
            "direction": direction,
            "round_number": round(rn, 2),
            "is_double_zero": abs(rn % 1.0) < 0.01 or abs(rn % 1.0 - 1.0) < 0.01,
            "entry_price": round(entry_price, 3),
            "exit_price": round(exit_price, 3),
            "pnl_pips": round(pnl_pips, 1),
            "outcome": outcome,
            "momentum_pips": round(momentum * pip_mult, 1),
            "atr_pips": round(atr * pip_mult, 1),
            "overshoot_pips": round(overshoot * pip_mult, 1),
        })

        # Cooldown: 3 bars after exit
        cooldown_until = exit_idx + 2

    return trades


def analyze_trades(trades: list, label: str, spread: float):
    """トレード結果の詳細分析"""
    n = len(trades)
    if n == 0:
        print(f"  {label}: NO TRADES")
        return None

    wins = sum(1 for t in trades if t["pnl_pips"] > 0)
    total = sum(t["pnl_pips"] for t in trades)
    wr = wins / n * 100
    ev = total / n

    # Period
    dates = [t["date"] for t in trades]
    d_span = (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[0])).days + 1
    months = d_span / 30
    mo_pips = total / months if months > 0 else 0

    # Outcome breakdown
    tp_c = sum(1 for t in trades if t["outcome"] == "TP")
    sl_c = sum(1 for t in trades if t["outcome"] == "SL")
    te_c = sum(1 for t in trades if t["outcome"] == "TIME_EXIT")

    # .00 vs .50
    dz = [t for t in trades if t["is_double_zero"]]
    hz = [t for t in trades if not t["is_double_zero"]]

    print(f"  {label}: {n}t WR={wr:.1f}% EV={ev:+.1f}pip Total={total:+.1f} Mo={mo_pips:+.1f}pip/mo")
    print(f"    TP:{tp_c} SL:{sl_c} Time:{te_c}")

    if dz:
        dz_wr = sum(1 for t in dz if t["pnl_pips"] > 0) / len(dz) * 100
        dz_ev = sum(t["pnl_pips"] for t in dz) / len(dz)
        print(f"    .00 level: {len(dz)}t WR={dz_wr:.1f}% EV={dz_ev:+.1f}")
    if hz:
        hz_wr = sum(1 for t in hz if t["pnl_pips"] > 0) / len(hz) * 100
        hz_ev = sum(t["pnl_pips"] for t in hz) / len(hz)
        print(f"    .50 level: {len(hz)}t WR={hz_wr:.1f}% EV={hz_ev:+.1f}")

    # Direction
    buys = [t for t in trades if t["direction"] == "BUY"]
    sells = [t for t in trades if t["direction"] == "SELL"]
    if buys:
        b_wr = sum(1 for t in buys if t["pnl_pips"] > 0) / len(buys) * 100
        b_ev = sum(t["pnl_pips"] for t in buys) / len(buys)
        print(f"    BUY: {len(buys)}t WR={b_wr:.1f}% EV={b_ev:+.1f}")
    if sells:
        s_wr = sum(1 for t in sells if t["pnl_pips"] > 0) / len(sells) * 100
        s_ev = sum(t["pnl_pips"] for t in sells) / len(sells)
        print(f"    SELL: {len(sells)}t WR={s_wr:.1f}% EV={s_ev:+.1f}")

    # Spread sensitivity
    print(f"    Spread sensitivity:")
    for sp in [0.0, 0.5, 1.0, 2.0, 3.0, 4.0]:
        adj = sum(t["pnl_pips"] + spread - sp for t in trades)
        adj_ev = adj / n
        marker = " ←current" if abs(sp - spread) < 0.01 else ""
        print(f"      {sp:.1f}pip: EV={adj_ev:+.1f} Total={adj:+.1f}{marker}")

    return {
        "n": n, "wr": round(wr, 1), "ev": round(ev, 1),
        "total": round(total, 1), "mo_pips": round(mo_pips, 1),
    }


def run_pair(symbol: str, pair_cfg: dict, interval: str = "15m", days: int = 60):
    """1ペアの全構成テスト"""
    label = pair_cfg["label"]
    spread = pair_cfg["spread"]

    print(f"\n{'='*70}")
    print(f"  {label} — RNB Phase 1 ({interval}, {days}d)")
    print(f"  Spread: {spread}pip | Round step: {pair_cfg['round_step']}")
    print(f"{'='*70}")

    df = fetch_data(symbol, interval=interval, days=days)
    if df is None or len(df) < 100:
        print("  ERROR: Insufficient data")
        return None

    print(f"  Bars: {len(df)} | Period: {df.index[0]} → {df.index[-1]}")

    best_result = None
    best_ev = -999
    best_label = ""

    print(f"\n  ── Config Scan ──")
    for cfg in CONFIGS:
        trades = run_bt_config(df, cfg, pair_cfg)
        n = len(trades)
        if n < 5:
            print(f"  {cfg['label']:<16} {n:>3}t (skip, N<5)")
            continue

        wins = sum(1 for t in trades if t["pnl_pips"] > 0)
        total = sum(t["pnl_pips"] for t in trades)
        wr = wins / n * 100
        ev = total / n
        marker = " ★" if ev > 1.0 else ""
        print(f"  {cfg['label']:<16} {n:>3}t WR={wr:>5.1f}% EV={ev:>+7.1f} Total={total:>+8.1f}{marker}")

        if ev > best_ev:
            best_ev = ev
            best_label = cfg["label"]
            best_result = trades

    if best_result is None:
        print("  No valid configurations found")
        return None

    # ── Best config 詳細分析 ──
    print(f"\n  ★ Best: {best_label}")
    result = analyze_trades(best_result, f"{label} ({best_label})", spread)

    # Monthly breakdown
    if best_result:
        print(f"\n    Monthly breakdown:")
        monthly = defaultdict(list)
        for t in best_result:
            monthly[t["date"][:7]].append(t["pnl_pips"])
        for ym in sorted(monthly.keys()):
            m = monthly[ym]
            m_t = sum(m)
            m_wr = sum(1 for p in m if p > 0) / len(m) * 100
            print(f"    {ym}: {len(m):>3}t WR={m_wr:.0f}% {m_t:+.1f}pip")

    if result:
        result["best_config"] = best_label
        result["label"] = label
        result["spread"] = spread
    return result


if __name__ == "__main__":
    print("=" * 70)
    print("  Round Number Barrier (RNB) — Phase 1 Backtest")
    print("  クロス円キリ番(.00/.50)急接近+反発 スキャルプ〜DT")
    print("  Data: yfinance 15m × 60d | Entry: Wick/Engulfing rejection")
    print("=" * 70)

    # ── 15m BT ──
    results_15m = {}
    for sym, cfg in PAIRS.items():
        r = run_pair(sym, cfg, interval="15m", days=60)
        if r:
            results_15m[sym] = r

    # ── 5m BT (比較) ──
    print(f"\n\n{'='*70}")
    print("  5m Comparison (same 60d period)")
    print(f"{'='*70}")

    results_5m = {}
    for sym, cfg in PAIRS.items():
        r = run_pair(sym, cfg, interval="5m", days=60)
        if r:
            results_5m[sym] = r

    # ── Final Summary ──
    print(f"\n\n{'='*70}")
    print("  FINAL SUMMARY — RNB Phase 1")
    print(f"{'='*70}")

    print(f"\n  15m Results:")
    print(f"  {'Pair':<10} {'N':>5} {'WR':>6} {'EV':>9} {'Total':>9} {'Mo':>9} {'Sprd':>5} {'Config'}")
    print(f"  {'-'*10} {'-'*5} {'-'*6} {'-'*9} {'-'*9} {'-'*9} {'-'*5} {'-'*16}")
    for sym, r in results_15m.items():
        print(f"  {r['label']:<10} {r['n']:>5} {r['wr']:>5.1f}% {r['ev']:>+8.1f} "
              f"{r['total']:>+8.1f} {r['mo_pips']:>+8.1f} {r['spread']:>4.1f} {r['best_config']}")

    print(f"\n  5m Results:")
    print(f"  {'Pair':<10} {'N':>5} {'WR':>6} {'EV':>9} {'Total':>9} {'Mo':>9} {'Sprd':>5} {'Config'}")
    print(f"  {'-'*10} {'-'*5} {'-'*6} {'-'*9} {'-'*9} {'-'*9} {'-'*5} {'-'*16}")
    for sym, r in results_5m.items():
        print(f"  {r['label']:<10} {r['n']:>5} {r['wr']:>5.1f}% {r['ev']:>+8.1f} "
              f"{r['total']:>+8.1f} {r['mo_pips']:>+8.1f} {r['spread']:>4.1f} {r['best_config']}")

    # TF recommendation
    print(f"\n  ── Timeframe Recommendation ──")
    for sym in PAIRS:
        l = PAIRS[sym]["label"]
        r15 = results_15m.get(sym)
        r5 = results_5m.get(sym)
        if r15 and r5:
            better = "15m" if r15["ev"] > r5["ev"] else "5m"
            b_r = r15 if better == "15m" else r5
            print(f"  {l}: {better} recommended (EV={b_r['ev']:+.1f}, N={b_r['n']})")
        elif r15:
            print(f"  {l}: 15m only (EV={r15['ev']:+.1f})")
        elif r5:
            print(f"  {l}: 5m only (EV={r5['ev']:+.1f})")
        else:
            print(f"  {l}: No valid results")

    # Viability
    print(f"\n  ── Viability Verdict ──")
    for sym in PAIRS:
        l = PAIRS[sym]["label"]
        sp = PAIRS[sym]["spread"]
        best_r = None
        for res in [results_15m.get(sym), results_5m.get(sym)]:
            if res and (best_r is None or res["ev"] > best_r["ev"]):
                best_r = res
        if best_r:
            viable = best_r["ev"] > 0 and best_r["n"] >= 15
            verdict = ("VIABLE" if viable else
                       "MARGINAL" if best_r["ev"] > -2 else "NOT VIABLE")
            print(f"  {l}: EV={best_r['ev']:+.1f}pip (spread={sp}pip込) "
                  f"N={best_r['n']} → {verdict}")
        else:
            print(f"  {l}: NO DATA")
