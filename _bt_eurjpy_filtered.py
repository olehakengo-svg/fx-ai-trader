#!/usr/bin/env python3
"""
EUR/JPY UTC 12-15 限定 bb_rsi Backtest
========================================
柱1: スプレッドの壁を超える「時間帯フィルター」検証

1m (7d) + 5m (60d) の2段階検証:
  - 1m 7d: 短期精度確認 (直接比較用)
  - 5m 60d: 長期統計的有意性確認 (81日分)

EUR/JPY OANDA spread model:
  UTC 12-16 (LDN/NY): 1.5pip
  UTC 07-12:           2.0pip
  Others:              3.0-4.0pip
"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from modules.indicators import add_indicators


# ── EUR/JPY Configuration ──
IS_JPY = True
PIP_MULT = 100

# スプレッドモデル (OANDA typical for EUR/JPY)
def get_spread(hour_utc: int) -> float:
    if hour_utc < 2:    return 0.040   # 4.0pip (Tokyo early)
    elif hour_utc < 7:  return 0.025   # 2.5pip (Asia)
    elif hour_utc < 12: return 0.020   # 2.0pip (LDN)
    elif hour_utc < 16: return 0.015   # 1.5pip (LDN/NY overlap) ★最狭
    elif hour_utc < 20: return 0.025   # 2.5pip (NY)
    else:               return 0.040   # 4.0pip (Close)


def fetch_data(interval="1m", days=7):
    import yfinance as yf
    df = yf.download("EURJPY=X", period=f"{days}d", interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if len(df) < 200:
        return None
    return add_indicators(df).dropna()


def run_bt(interval: str, days: int, hour_filter: tuple = None,
           label: str = ""):
    """
    bb_rsi BT on EUR/JPY with optional hour filter.

    Args:
        interval: "1m" or "5m"
        days: lookback period
        hour_filter: (start, end) UTC hours to allow, None = all hours
        label: display label
    """
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"  EUR/JPY bb_rsi | {interval} | {days}d | "
          f"Hours: {f'UTC {hour_filter[0]}-{hour_filter[1]}' if hour_filter else 'ALL'}")
    print(f"{'='*65}")

    df = fetch_data(interval=interval, days=days)
    if df is None:
        print("  ERROR: データ不足")
        return None

    print(f"  Bars: {len(df)}")

    # Timeframe-adjusted parameters
    if interval == "1m":
        MAX_HOLD = 40      # 40 bars = 40 min
        COOLDOWN = 1       # 1 bar
    elif interval == "5m":
        MAX_HOLD = 8       # 8 bars = 40 min (same real time)
        COOLDOWN = 1
    else:
        MAX_HOLD = 40
        COOLDOWN = 1

    MIN_RR = 1.2
    MIN_BARS = 200

    trades = []
    last_exit_bar = -99
    hourly_stats = {}
    daily_pnl = {}  # YYYY-MM-DD -> total_pips

    for i in range(MIN_BARS, len(df) - MAX_HOLD - 1):
        if i - last_exit_bar < COOLDOWN:
            continue

        row = df.iloc[i]
        entry = float(row["Close"])
        atr = float(row.get("atr", 0.01))
        atr7 = float(row.get("atr7", atr))
        if atr <= 0:
            continue

        # Bar range filter
        bar_range = float(row["High"]) - float(row["Low"])
        if interval == "1m":
            _min_br = 0.008  # JPY 1m
        else:
            _min_br = 0.015  # JPY 5m (wider bars)
        if bar_range < _min_br:
            continue

        # Volume filter
        if "Volume" in df.columns:
            vol = float(row["Volume"])
            if vol > 0 and vol < 100:
                continue

        # Time
        bar_time = df.index[i]
        hour_utc = bar_time.hour if hasattr(bar_time, 'hour') else 12

        # ── Hour filter (the key innovation) ──
        if hour_filter is not None:
            if not (hour_filter[0] <= hour_utc <= hour_filter[1]):
                continue

        # ── ADX: no cap for JPY crosses (Option C approach) ──
        adx_val = float(row.get("adx", 25))

        # ── bb_rsi core conditions ──
        bbpb = float(row.get("bb_pband", 0.5))
        rsi5 = float(row.get("rsi5", 50))
        stoch_k = float(row.get("stoch_k", 50))
        stoch_d = float(row.get("stoch_d", 50))
        macdh = float(row.get("macd_hist", 0))

        _prev = df.iloc[i - 1] if i >= 1 else row
        macdh_prev = float(_prev.get("macd_hist", 0))
        macdh_prev2 = float(df.iloc[i-2].get("macd_hist", 0)) if i >= 2 else 0

        signal = None
        score = 0.0
        _min_sl = 0.030  # 3.0pip minimum SL

        # ── BUY ──
        if (bbpb <= 0.25 and rsi5 < 45
                and stoch_k < 45 and stoch_k > stoch_d):
            signal = "BUY"
            tier1 = bbpb <= 0.05 and rsi5 < 25 and stoch_k < 20
            score = (4.5 if tier1 else 3.0) + (38 - rsi5) * 0.06
            # Stoch gap bonus
            gap = stoch_k - stoch_d
            if gap > 1.5: score += 0.6
            elif gap > 0.5: score += 0.3
            # Prev bar
            if float(_prev["Close"]) <= float(_prev["Open"]): score += 0.3
            # MACD
            if macdh > 0: score += 0.5
            if macdh > macdh_prev and macdh_prev <= macdh_prev2: score += 0.6
            # ADX trend bonus (JPY cross)
            if adx_val >= 30: score += 0.6

            tp_mult = 2.0 if tier1 else 1.5
            tp = entry + atr7 * tp_mult
            bb_lower = float(row.get("bb_lower", entry - atr))
            sl_dist = max(abs(entry - bb_lower) + atr7 * 0.3, _min_sl)
            sl = entry - sl_dist

        # ── SELL ──
        if (signal is None and bbpb >= 0.75 and rsi5 > 55
                and stoch_k > 55 and stoch_k < stoch_d):
            signal = "SELL"
            tier1 = bbpb >= 0.95 and rsi5 > 75 and stoch_k > 80
            score = (4.5 if tier1 else 3.0) + (rsi5 - 58) * 0.06
            gap = stoch_d - stoch_k
            if gap > 1.5: score += 0.6
            if float(_prev["Close"]) >= float(_prev["Open"]): score += 0.3
            if macdh < 0: score += 0.5
            if macdh < macdh_prev and macdh_prev >= macdh_prev2: score += 0.6
            if adx_val >= 30: score += 0.6

            tp_mult = 2.0 if tier1 else 1.5
            tp = entry - atr7 * tp_mult
            bb_upper = float(row.get("bb_upper", entry + atr))
            sl_dist = max(abs(bb_upper - entry) + atr7 * 0.3, _min_sl)
            sl = entry + sl_dist

        if signal is None:
            continue

        # ── Entry at next bar Open + spread ──
        if i + 1 >= len(df):
            continue
        ep = float(df.iloc[i + 1]["Open"])
        spread = get_spread(hour_utc)
        ep = ep + spread / 2 if signal == "BUY" else ep - spread / 2

        # Shift SL/TP
        _shift = ep - entry
        sl += _shift
        tp += _shift

        sl_dist = abs(ep - sl)
        tp_dist = abs(tp - ep)
        if sl_dist <= 0:
            continue

        # RR check
        actual_rr = tp_dist / sl_dist
        if actual_rr < MIN_RR:
            continue

        # SL widening for low-liquidity hours
        if hour_utc in {0, 1, 18, 19, 20, 21}:
            sl_dist += atr7 * 0.2
            if signal == "BUY":
                sl = ep - sl_dist
            else:
                sl = ep + sl_dist

        # ── Trade simulation ──
        outcome = None
        bars_held = 0
        _be_activated = False
        _current_sl = sl
        _sl_genuine = atr7 * 0.3

        for j in range(1, MAX_HOLD + 1):
            if i + 1 + j >= len(df):
                break
            fut = df.iloc[i + 1 + j]
            hi, lo = float(fut["High"]), float(fut["Low"])
            fut_close = float(fut["Close"])

            # BE at 60% TP
            tp_dist_total = abs(tp - ep)
            if signal == "BUY":
                _progress = hi - ep
                if _progress >= tp_dist_total * 0.6:
                    _be_activated = True
                    _current_sl = max(_current_sl, ep)
            else:
                _progress = ep - lo
                if _progress >= tp_dist_total * 0.6:
                    _be_activated = True
                    _current_sl = min(_current_sl, ep)

            # Time-decay
            if j >= int(MAX_HOLD * 0.6):
                if signal == "BUY" and fut_close > ep:
                    _current_sl = max(_current_sl, ep)
                elif signal == "SELL" and fut_close < ep:
                    _current_sl = min(_current_sl, ep)

            # Check TP/SL
            if signal == "BUY":
                hit_tp = hi >= tp
                _wick_depth = _current_sl - lo
                hit_sl = (fut_close <= _current_sl) or (_wick_depth > _sl_genuine)
            else:
                hit_tp = lo <= tp
                _wick_depth = hi - _current_sl
                hit_sl = (fut_close >= _current_sl) or (_wick_depth > _sl_genuine)

            if hit_tp and hit_sl:
                outcome = "WIN" if (fut_close >= ep if signal == "BUY" else fut_close <= ep) else "LOSS"
                bars_held = j
                break
            elif hit_tp:
                outcome = "WIN"
                bars_held = j
                break
            elif hit_sl:
                if _be_activated:
                    outcome = "WIN" if (
                        (_current_sl >= ep if signal == "BUY" else _current_sl <= ep)
                    ) else "LOSS"
                else:
                    outcome = "LOSS"
                bars_held = j
                break

        if outcome is None:
            _last_close = float(df.iloc[min(i + 1 + MAX_HOLD, len(df) - 1)]["Close"])
            outcome = "WIN" if (
                (_last_close > ep + spread if signal == "BUY" else _last_close < ep - spread)
            ) else "LOSS"
            bars_held = MAX_HOLD

        # Exit spread
        exit_bar_idx = min(i + 1 + bars_held, len(df) - 1)
        exit_hour = df.index[exit_bar_idx].hour if hasattr(df.index[exit_bar_idx], 'hour') else 12
        exit_spread = get_spread(exit_hour)

        # Pips (net of spread)
        if outcome == "WIN":
            _pips = tp_dist * PIP_MULT - (spread + exit_spread) / 2 * PIP_MULT
        else:
            _pips = -(sl_dist * PIP_MULT + (spread + exit_spread) / 2 * PIP_MULT)

        # EXIT-based cooldown
        last_exit_bar = i + 1 + bars_held

        # Stats
        if hour_utc not in hourly_stats:
            hourly_stats[hour_utc] = {"wins": 0, "losses": 0, "pips": 0.0}
        if outcome == "WIN":
            hourly_stats[hour_utc]["wins"] += 1
        else:
            hourly_stats[hour_utc]["losses"] += 1
        hourly_stats[hour_utc]["pips"] += _pips

        # Daily PnL
        _day_key = str(bar_time.date()) if hasattr(bar_time, 'date') else "unknown"
        daily_pnl[_day_key] = daily_pnl.get(_day_key, 0.0) + _pips

        trades.append({
            "outcome": outcome,
            "bars_held": bars_held,
            "sig": signal,
            "ep": round(ep, 3),
            "sl_pip": round(sl_dist * PIP_MULT, 1),
            "tp_pip": round(tp_dist * PIP_MULT, 1),
            "pips": round(_pips, 1),
            "spread_pip": round(spread * PIP_MULT, 1),
            "rr": round(actual_rr, 1),
            "hour_utc": hour_utc,
            "adx": round(adx_val, 1),
            "score": round(score, 1),
            "entry_time": str(bar_time)[:19],
            "be_hit": _be_activated,
        })

    # ── Results ──
    n = len(trades)
    if n == 0:
        print("  0 trades")
        return {"trades": 0, "trade_log": [], "hourly_stats": {}, "daily_pnl": {}}

    wins = sum(1 for t in trades if t["outcome"] == "WIN")
    wr = wins / n * 100
    total_pips = sum(t["pips"] for t in trades)
    avg_pips = total_pips / n
    avg_rr = sum(t["rr"] for t in trades) / n
    avg_hold = sum(t["bars_held"] for t in trades) / n
    avg_spread = sum(t["spread_pip"] for t in trades) / n
    be_count = sum(1 for t in trades if t["be_hit"])

    # Gross pips
    gross_pips = 0
    for t in trades:
        if t["outcome"] == "WIN":
            gross_pips += t["tp_pip"]
        else:
            gross_pips -= t["sl_pip"]

    # Max consecutive losses
    max_consec_loss = 0
    _cl = 0
    for t in trades:
        if t["outcome"] == "LOSS":
            _cl += 1
            max_consec_loss = max(max_consec_loss, _cl)
        else:
            _cl = 0

    # Daily stats
    trading_days = len(daily_pnl)
    profitable_days = sum(1 for v in daily_pnl.values() if v > 0)
    avg_daily_pips = total_pips / max(trading_days, 1)

    # Max drawdown (pip-based)
    equity_curve = []
    _cum = 0
    for t in trades:
        _cum += t["pips"]
        equity_curve.append(_cum)
    _peak = 0
    _max_dd = 0
    for e in equity_curve:
        _peak = max(_peak, e)
        _dd = _peak - e
        _max_dd = max(_max_dd, _dd)

    print(f"  Trades: {n}")
    print(f"  WR: {wr:.1f}%")
    print(f"  Net: {total_pips:+.1f}pip | Gross: {gross_pips:+.1f}pip")
    print(f"  EV: {avg_pips:+.2f}pip/trade")
    print(f"  Avg RR: {avg_rr:.1f} | Avg Spread: {avg_spread:.1f}pip")
    if interval == "1m":
        print(f"  Avg Hold: {avg_hold:.1f}min")
    else:
        print(f"  Avg Hold: {avg_hold * 5:.1f}min ({avg_hold:.1f} bars)")
    print(f"  BE activated: {be_count}/{n}")
    print(f"  Max consec loss: {max_consec_loss}")
    print(f"  Max DD: {_max_dd:.1f}pip")
    print(f"  Days: {trading_days} | Profitable: {profitable_days} ({profitable_days/max(trading_days,1)*100:.0f}%)")
    print(f"  Avg daily: {avg_daily_pips:+.1f}pip/day")

    # Hourly breakdown
    print(f"\n  --- Hourly Breakdown ---")
    for h in sorted(hourly_stats.keys()):
        hs = hourly_stats[h]
        hn = hs["wins"] + hs["losses"]
        if hn == 0:
            continue
        hwr = hs["wins"] / hn * 100
        hev = hs["pips"] / hn
        _mark = " ★" if hev > 0 else ""
        print(f"    UTC {h:02d}: {hn:>3d}t WR={hwr:>4.0f}% "
              f"Net={hs['pips']:>+7.1f}pip EV={hev:>+5.2f}{_mark}")

    # ADX breakdown
    print(f"\n  --- ADX Breakdown ---")
    adx_bins = [(0, 20, "Low"), (20, 25, "Mid"), (25, 30, "High"), (30, 100, "VHigh")]
    for lo, hi, lbl in adx_bins:
        _at = [t for t in trades if lo <= t["adx"] < hi]
        if not _at:
            continue
        _aw = sum(1 for t in _at if t["outcome"] == "WIN")
        _awr = _aw / len(_at) * 100
        _ap = sum(t["pips"] for t in _at)
        _aev = _ap / len(_at)
        print(f"    ADX {lo}-{hi} ({lbl:>5s}): {len(_at):>3d}t WR={_awr:>4.0f}% "
              f"Net={_ap:>+7.1f}pip EV={_aev:>+5.2f}")

    # Sample trades
    print(f"\n  --- Sample Trades (first 10) ---")
    for t in trades[:10]:
        _be = "BE" if t["be_hit"] else "  "
        print(f"    {t['entry_time']} {t['sig']:4s} {t['outcome']:4s} "
              f"ep={t['ep']} SL={t['sl_pip']:.1f}p TP={t['tp_pip']:.1f}p "
              f"spd={t['spread_pip']:.1f}p ADX={t['adx']:.0f} hold={t['bars_held']} {_be}")

    return {
        "trades": n, "win_rate": wr,
        "total_pips_net": total_pips, "total_pips_gross": gross_pips,
        "ev": avg_pips, "avg_rr": avg_rr, "avg_spread": avg_spread,
        "max_dd": _max_dd, "max_consec_loss": max_consec_loss,
        "trading_days": trading_days, "profitable_days": profitable_days,
        "avg_daily_pips": avg_daily_pips,
        "trade_log": trades, "hourly_stats": hourly_stats,
        "daily_pnl": daily_pnl,
    }


# ══════════════════════════════════════════════════════════════
#  Volatility Adaptive Lot Sizing Simulation
# ══════════════════════════════════════════════════════════════
def simulate_lot_sizing(trades: list, label: str = ""):
    """
    動的ロットサイジングの効果をシミュレーション。

    2軸制御:
      Axis 1: SL距離 (既存) — 3.5pip基準で反比例
      Axis 2: ATR/spread比 (新規) — 高ボラ・低スプレッド時に加速
    """
    if not trades:
        return

    print(f"\n{'='*65}")
    print(f"  Volatility Adaptive Lot Sizing Simulation")
    print(f"  {label}")
    print(f"{'='*65}")

    BASE_SL_PIPS = 3.5     # SL基準
    BASE_LOT = 10000        # 0.1 lot

    # ATR/spread thresholds (EUR/JPY calibrated)
    VOL_BOOST_THRESHOLD = 8.0    # ATR/spread > 8 → 加速
    VOL_REDUCE_THRESHOLD = 4.0   # ATR/spread < 4 → 減速

    results_fixed = {"pips": 0, "lots_used": []}
    results_sl_only = {"pips": 0, "lots_used": []}
    results_combined = {"pips": 0, "lots_used": []}

    for t in trades:
        sl_pips = t["sl_pip"]
        spread_pips = t["spread_pip"]
        pips = t["pips"]

        # ── 固定ロット ──
        results_fixed["pips"] += pips
        results_fixed["lots_used"].append(1.0)

        # ── Axis 1: SL距離連動 (既存ロジック) ──
        sl_ratio = min(BASE_SL_PIPS / max(sl_pips, 0.5), 1.5)
        sl_ratio = max(sl_ratio, 0.5)
        results_sl_only["pips"] += pips * sl_ratio
        results_sl_only["lots_used"].append(sl_ratio)

        # ── Axis 2: ATR/spread + SL距離 (新ロジック) ──
        # ATR近似: TP_pip / 1.5 (TP = ATR7 × 1.5 from bb_rsi)
        atr_pips = t["tp_pip"] / 1.5 if t["tp_pip"] > 0 else 3.0
        vol_ratio = atr_pips / max(spread_pips, 0.1)

        if vol_ratio >= VOL_BOOST_THRESHOLD:
            vol_mult = 1.3   # boost
        elif vol_ratio <= VOL_REDUCE_THRESHOLD:
            vol_mult = 0.6   # reduce
        else:
            vol_mult = 1.0   # neutral

        combined_ratio = sl_ratio * vol_mult
        combined_ratio = max(0.3, min(combined_ratio, 2.0))  # wider range

        results_combined["pips"] += pips * combined_ratio
        results_combined["lots_used"].append(combined_ratio)

    n = len(trades)
    print(f"\n  {'Method':<30s} {'Total pip':>10s} {'EV/trade':>10s} {'Avg Lot':>10s}")
    print(f"  {'-'*60}")
    for name, res in [("Fixed (1.0x)", results_fixed),
                       ("SL-distance only", results_sl_only),
                       ("SL + ATR/spread", results_combined)]:
        avg_lot = sum(res["lots_used"]) / n
        print(f"  {name:<30s} {res['pips']:>+10.1f} "
              f"{res['pips']/n:>+10.2f} {avg_lot:>10.2f}x")

    # Lot distribution
    lots = results_combined["lots_used"]
    print(f"\n  Lot Distribution (SL + ATR/spread):")
    for lo, hi, lbl in [(0, 0.5, "0.3-0.5x"), (0.5, 0.8, "0.5-0.8x"),
                         (0.8, 1.2, "0.8-1.2x"), (1.2, 1.6, "1.2-1.6x"),
                         (1.6, 2.1, "1.6-2.0x")]:
        cnt = sum(1 for l in lots if lo <= l < hi)
        if cnt > 0:
            pct = cnt / n * 100
            print(f"    {lbl:>8s}: {cnt:>3d} ({pct:>4.0f}%)")


# ══════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":

    # ── Test 1: 1m 7d — ALL hours (baseline) ──
    r1_all = run_bt("1m", 7, hour_filter=None,
                    label="Test 1: 1m 7d ALL hours (baseline)")

    # ── Test 2: 1m 7d — UTC 12-15 only ──
    r1_filt = run_bt("1m", 7, hour_filter=(12, 15),
                     label="Test 2: 1m 7d UTC 12-15 only")

    # ── Test 3: 5m 60d — ALL hours (long baseline) ──
    r5_all = run_bt("5m", 60, hour_filter=None,
                    label="Test 3: 5m 60d ALL hours")

    # ── Test 4: 5m 60d — UTC 12-15 only (KEY TEST) ──
    r5_filt = run_bt("5m", 60, hour_filter=(12, 15),
                     label="Test 4: 5m 60d UTC 12-15 only ★★★")

    # ── Test 5: 5m 60d — UTC 12-16 (wider window) ──
    r5_wide = run_bt("5m", 60, hour_filter=(12, 16),
                     label="Test 5: 5m 60d UTC 12-16 (wider)")

    # ── Test 6: 5m 60d — UTC 07-10 (London open) ──
    r5_ldn = run_bt("5m", 60, hour_filter=(7, 10),
                    label="Test 6: 5m 60d UTC 07-10 (London open)")

    # ── Lot Sizing Simulation ──
    if r5_filt and r5_filt["trades"] > 0:
        simulate_lot_sizing(r5_filt["trade_log"],
                           label="EUR/JPY UTC 12-15 (5m 60d)")

    if r5_all and r5_all["trades"] > 0:
        simulate_lot_sizing(r5_all["trade_log"],
                           label="EUR/JPY ALL hours (5m 60d)")

    # ── Final Summary ──
    print(f"\n{'='*75}")
    print(f"  EUR/JPY bb_rsi COMPREHENSIVE SUMMARY")
    print(f"{'='*75}")
    print(f"  {'Test':<40s} {'Trades':>6s} {'WR':>6s} {'Net':>8s} "
          f"{'EV/t':>7s} {'DD':>6s} {'Days':>5s} {'$/d':>7s}")
    print(f"  {'-'*84}")

    tests = [
        ("1m 7d ALL hours", r1_all),
        ("1m 7d UTC 12-15", r1_filt),
        ("5m 60d ALL hours", r5_all),
        ("5m 60d UTC 12-15 ★", r5_filt),
        ("5m 60d UTC 12-16", r5_wide),
        ("5m 60d UTC 07-10 (LDN)", r5_ldn),
    ]

    for name, r in tests:
        if r is None or r["trades"] == 0:
            print(f"  {name:<40s} {'0':>6s}")
            continue
        verdict = "✅" if r["ev"] > 0 else "❌"
        print(f"  {name:<40s} {r['trades']:>6d} {r['win_rate']:>5.1f}% "
              f"{r['total_pips_net']:>+8.1f} {r['ev']:>+7.2f} "
              f"{r['max_dd']:>5.1f} {r['trading_days']:>5d} "
              f"{r['avg_daily_pips']:>+7.1f} {verdict}")
