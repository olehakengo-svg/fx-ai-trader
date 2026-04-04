#!/usr/bin/env python3
"""
KSB (Keltner Squeeze Breakout) 1H Backtest
HourlyEngine + 実4H/1D HTFバイアス
"""
import os, json, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from modules.indicators import add_indicators
from strategies.context import SignalContext
from strategies.hourly import HourlyEngine

# ── データ取得 ──
def fetch_data(symbol, days=60, interval="1h"):
    import yfinance as yf
    df = yf.download(symbol, period=f"{days}d", interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return add_indicators(df)


def compute_htf_bias(df_1h, bar_idx):
    """実4H+1Dバイアスを1Hデータからリサンプリングで計算"""
    sub = df_1h.iloc[:bar_idx + 1]
    if len(sub) < 50:
        return {"agreement": "mixed"}

    # 4H足リサンプリング
    try:
        h4 = sub.resample("4h").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last"
        }).dropna()
        if len(h4) >= 21:
            h4_ema9 = h4["Close"].ewm(span=9).mean().iloc[-1]
            h4_ema21 = h4["Close"].ewm(span=21).mean().iloc[-1]
            h4_close = float(h4["Close"].iloc[-1])
            h4_bull = h4_close > h4_ema9 > h4_ema21
            h4_bear = h4_close < h4_ema9 < h4_ema21
        else:
            h4_bull = h4_bear = False
    except Exception:
        h4_bull = h4_bear = False

    # 1D足リサンプリング
    try:
        d1 = sub.resample("1D").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last"
        }).dropna()
        if len(d1) >= 9:
            d1_ema9 = d1["Close"].ewm(span=9).mean().iloc[-1]
            d1_ema21 = d1["Close"].ewm(span=21).mean().iloc[-1]
            d1_close = float(d1["Close"].iloc[-1])
            d1_bull = d1_close > d1_ema9
            d1_bear = d1_close < d1_ema9
        else:
            d1_bull = d1_bear = False
    except Exception:
        d1_bull = d1_bear = False

    _d1_ema50_falling = False
    try:
        if len(d1) >= 50:
            _d1_ema50 = d1["Close"].ewm(span=50).mean()
            _d1_ema50_falling = float(_d1_ema50.iloc[-1]) < float(_d1_ema50.iloc[-5])
    except Exception:
        pass

    if h4_bull and d1_bull:
        return {"agreement": "bull", "d1_ema50_falling": _d1_ema50_falling}
    elif h4_bear and d1_bear:
        return {"agreement": "bear", "d1_ema50_falling": _d1_ema50_falling}
    return {"agreement": "mixed", "d1_ema50_falling": _d1_ema50_falling}


def run_bt(symbol, label, days=60):
    print(f"\n{'='*60}")
    print(f"  {label} 1H KSB BT ({days}d)")
    print(f"{'='*60}")

    df = fetch_data(symbol, days=days)
    print(f"  Bars: {len(df)}")

    if len(df) < 60:
        print("  ERROR: データ不足")
        return None

    engine = HourlyEngine()

    _is_jpy = "JPY" in symbol.upper()
    _pip_mult = 100 if _is_jpy else 10000

    MAX_HOLD = 24
    COOLDOWN = 1
    BE_TRIGGER = 0.50      # TP 50%到達でBE
    TRAIL_ATR_MULT = 1.5   # トレーリング: 直近高値/安値 - ATR×1.5

    trades = []
    last_bar = -99
    htf_cache = {}
    HTF_RECALC = 24  # 24時間ごとにHTF再計算

    for i in range(50, len(df) - MAX_HOLD - 1):
        if i - last_bar < COOLDOWN:
            continue

        row = df.iloc[i]
        entry = float(row["Close"])
        open_p = float(row["Open"])
        atr = float(row.get("atr", 0.1))
        if atr <= 0:
            continue

        # Bar range filter
        bar_range = float(row["High"]) - float(row["Low"])
        _min_br = 0.030 if _is_jpy else 0.00030
        if bar_range < _min_br:
            continue

        # HTF bias (cached)
        _htf_key = i // HTF_RECALC
        if _htf_key not in htf_cache:
            htf_cache[_htf_key] = compute_htf_bias(df, i)
        htf = htf_cache[_htf_key]

        # Build SignalContext
        bar_df = df.iloc[max(0, i - 200):i + 1]
        _prev = df.iloc[i - 1] if i >= 1 else row

        ctx = SignalContext(
            entry=entry, open_price=open_p,
            atr=atr,
            atr7=float(row.get("atr7", atr)),
            ema9=float(row.get("ema9", entry)),
            ema21=float(row.get("ema21", entry)),
            ema50=float(row.get("ema50", entry)),
            ema200=float(row.get("ema200", entry)),
            rsi=float(row.get("rsi", 50)),
            rsi5=float(row.get("rsi5", 50)),
            rsi9=float(row.get("rsi9", 50)),
            stoch_k=float(row.get("stoch_k", 50)),
            stoch_d=float(row.get("stoch_d", 50)),
            adx=float(row.get("adx", 25)),
            adx_pos=float(row.get("adx_pos", 25)),
            adx_neg=float(row.get("adx_neg", 25)),
            macdh=float(row.get("macd_hist", 0)),
            macdh_prev=float(_prev.get("macd_hist", 0)),
            macdh_prev2=float(df.iloc[i-2].get("macd_hist", 0)) if i >= 2 else 0,
            bbpb=float(row.get("bb_pband", 0.5)),
            bb_upper=float(row.get("bb_upper", entry + atr)),
            bb_mid=float(row.get("bb_mid", entry)),
            bb_lower=float(row.get("bb_lower", entry - atr)),
            prev_close=float(_prev["Close"]),
            prev_open=float(_prev["Open"]),
            prev_high=float(_prev["High"]),
            prev_low=float(_prev["Low"]),
            symbol=symbol, tf="1h",
            is_jpy=_is_jpy,
            pip_mult=_pip_mult,
            df=bar_df,
            htf=htf,
            backtest_mode=True,
            bar_time=df.index[i] if hasattr(df.index[i], 'hour') else None,
            hour_utc=df.index[i].hour if hasattr(df.index[i], 'hour') else 12,
        )

        # Evaluate
        candidates = engine.evaluate_all(ctx)
        best = engine.select_best(candidates)
        if best is None:
            continue

        sig = best.signal
        sl = best.sl
        tp = best.tp
        entry_type = best.entry_type

        # Entry at next bar's Open + spread
        if i + 1 >= len(df):
            continue
        ep = float(df.iloc[i + 1]["Open"])
        _spread = 0.03 if _is_jpy else 0.00015  # 固定スプレッド
        ep = ep + _spread / 2 if sig == "BUY" else ep - _spread / 2

        # Shift SL/TP by entry price difference
        _shift = ep - entry
        sl += _shift
        tp += _shift

        sl_dist = abs(ep - sl)
        tp_dist = abs(tp - ep)
        if sl_dist <= 0 or tp_dist / sl_dist < 1.2:
            continue

        # ── Trade simulation with BE + Trailing ──
        outcome = None
        bars_held = 0
        _be_activated = False
        _current_sl = sl
        _best_progress = 0.0

        for j in range(1, MAX_HOLD + 1):
            if i + 1 + j >= len(df):
                break
            fut = df.iloc[i + 1 + j]
            hi, lo = float(fut["High"]), float(fut["Low"])
            fut_close = float(fut["Close"])

            # Progress tracking
            if sig == "BUY":
                _progress = hi - ep
                _best_progress = max(_best_progress, _progress)
            else:
                _progress = ep - lo
                _best_progress = max(_best_progress, _progress)

            # BE trigger
            if _best_progress >= tp_dist * BE_TRIGGER and not _be_activated:
                _be_activated = True
                _be_price = ep + _spread if sig == "BUY" else ep - _spread  # BE+spread
                if sig == "BUY":
                    _current_sl = max(_current_sl, _be_price)
                else:
                    _current_sl = min(_current_sl, _be_price)

            # Trailing stop
            if _be_activated:
                _trail_dist = atr * TRAIL_ATR_MULT
                if sig == "BUY":
                    # 直近3本のHighの最大値からトレーリング
                    _recent_hi = max(float(df.iloc[i+1+max(0,j-2):i+1+j+1]["High"].max()), hi)
                    _trail_sl = _recent_hi - _trail_dist
                    _current_sl = max(_current_sl, _trail_sl)
                else:
                    _recent_lo = min(float(df.iloc[i+1+max(0,j-2):i+1+j+1]["Low"].min()), lo)
                    _trail_sl = _recent_lo + _trail_dist
                    _current_sl = min(_current_sl, _trail_sl)

            # Time decay: 60% hold elapsed, tighten SL to BE if in profit
            if j >= int(MAX_HOLD * 0.6):
                if sig == "BUY" and fut_close > ep:
                    _current_sl = max(_current_sl, ep)
                elif sig == "SELL" and fut_close < ep:
                    _current_sl = min(_current_sl, ep)

            # Check TP/SL
            if sig == "BUY":
                hit_tp = hi >= tp
                hit_sl = lo <= _current_sl
            else:
                hit_tp = lo <= tp
                hit_sl = hi >= _current_sl

            if hit_tp and hit_sl:
                outcome = "WIN" if (fut_close >= ep if sig == "BUY" else fut_close <= ep) else "LOSS"
                bars_held = j
                break
            elif hit_tp:
                outcome = "WIN"
                bars_held = j
                break
            elif hit_sl:
                if _be_activated:
                    # BEまたはトレーリングで利確
                    if sig == "BUY":
                        _exit_pnl = _current_sl - ep
                    else:
                        _exit_pnl = ep - _current_sl
                    outcome = "WIN" if _exit_pnl > 0 else "LOSS"
                else:
                    outcome = "LOSS"
                bars_held = j
                break

        if outcome is None:
            # MAX_HOLD timeout — close at last bar
            _last_close = float(df.iloc[min(i + 1 + MAX_HOLD, len(df) - 1)]["Close"])
            if sig == "BUY":
                outcome = "WIN" if _last_close > ep else "LOSS"
            else:
                outcome = "WIN" if _last_close < ep else "LOSS"
            bars_held = MAX_HOLD

        _pips = 0
        if outcome == "WIN":
            _pips = tp_dist * _pip_mult
        else:
            _pips = -sl_dist * _pip_mult

        trades.append({
            "outcome": outcome,
            "bars_held": bars_held,
            "sig": sig,
            "ep": round(ep, 5 if not _is_jpy else 3),
            "sl_pip": round(sl_dist * _pip_mult, 1),
            "tp_pip": round(tp_dist * _pip_mult, 1),
            "pips": round(_pips, 1),
            "entry_type": entry_type,
            "entry_time": str(df.index[i])[:19],
            "be_hit": _be_activated,
            "rr": round(tp_dist / sl_dist, 1) if sl_dist > 0 else 0,
        })
        last_bar = i

    # ── Results ──
    n = len(trades)
    if n == 0:
        print("  0 trades")
        return {"trades": 0, "trade_log": []}

    wins = sum(1 for t in trades if t["outcome"] == "WIN")
    wr = wins / n * 100
    total_pips = sum(t["pips"] for t in trades)
    avg_pips = total_pips / n
    avg_rr = sum(t["rr"] for t in trades) / n
    avg_hold = sum(t["bars_held"] for t in trades) / n
    be_count = sum(1 for t in trades if t["be_hit"])

    print(f"  Trades: {n}")
    print(f"  WR: {wr:.1f}%")
    print(f"  Total: {total_pips:.1f}pip")
    print(f"  Avg: {avg_pips:.1f}pip/trade")
    print(f"  Avg RR: {avg_rr:.1f}")
    print(f"  Avg Hold: {avg_hold:.1f}h")
    print(f"  BE activated: {be_count}/{n}")

    print(f"\n  --- Trade Detail ---")
    for t in trades:
        _be = "BE" if t["be_hit"] else "  "
        print(f"    {t['entry_time']} {t['sig']} {t['outcome']} "
              f"ep={t['ep']} SL={t['sl_pip']}pip TP={t['tp_pip']}pip "
              f"RR={t['rr']} hold={t['bars_held']}h {_be}")

    return {
        "trades": n, "win_rate": wr, "total_pips": total_pips,
        "avg_pips": avg_pips, "avg_rr": avg_rr,
        "trade_log": trades,
    }


# ── Main ──
r_jpy = run_bt("USDJPY=X", "USD/JPY", days=120)
r_eur = run_bt("EURUSD=X", "EUR/USD", days=120)

print(f"\n{'='*60}")
print(f"  SUMMARY")
print(f"{'='*60}")
for label, r in [("JPY", r_jpy), ("EUR", r_eur)]:
    if r and r["trades"] > 0:
        print(f"  {label}: {r['trades']}t WR={r['win_rate']:.1f}% "
              f"Total={r['total_pips']:.1f}pip Avg={r['avg_pips']:.1f}pip/t")
    else:
        print(f"  {label}: 0 trades")
