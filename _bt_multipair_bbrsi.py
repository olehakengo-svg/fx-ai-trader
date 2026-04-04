#!/usr/bin/env python3
"""
Multi-Pair bb_rsi Backtest — スプレッド負けせずEVプラスの通貨ペア探索
======================================================================
BBRsiReversion (Option C) を GBP/JPY, EUR/JPY, GBP/USD, AUD/USD,
USD/CHF, CAD/JPY に適用し、OANDAリアルスプレッド環境でのEVを測定。

各ペアのスプレッドモデル:
  - GBP/JPY: ~3.0pip (高ボラ・高スプレッド)
  - EUR/JPY: ~2.0pip
  - GBP/USD: ~1.5pip
  - AUD/USD: ~1.5pip
  - USD/CHF: ~1.5pip
  - CAD/JPY: ~3.0pip
  比較: USD/JPY ~0.4pip, EUR/USD ~0.4pip

各ペアのDeath Valley / Gold Hours は流動性プロファイルに基づき調整。
"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from modules.indicators import add_indicators
from strategies.context import SignalContext
from strategies.scalp.bb_rsi import BBRsiReversion


# ── ペア別設定 ──
PAIR_CONFIG = {
    "GBPJPY=X": {
        "label": "GBP/JPY",
        "is_jpy": True, "pip_mult": 100,
        # OANDA typical spread: 2.5-4.0pip
        "spread_model": {
            "tokyo_early": 0.050,   # 5.0pip (UTC 0-2)
            "asia":        0.030,   # 3.0pip (UTC 2-7)
            "ldn_ny":      0.025,   # 2.5pip (UTC 7-16)
            "ny_late":     0.035,   # 3.5pip (UTC 16-20)
            "close":       0.050,   # 5.0pip (UTC 20-24)
        },
        # GBP/JPY: 高ボラ通貨。London/NY重複が活発。
        # Death Valley: アジア早朝(00-02), NY終盤(20-23) — スプレッド拡大+低流動性
        "death_valley": frozenset({0, 1, 2, 20, 21, 22, 23}),
        # Gold Hours: London open(7-10), NY重複(13-16) — 高ボラ+タイトスプレッド
        "gold_hours": frozenset({7, 8, 9, 10, 13, 14, 15, 16}),
        "adx_max": 999,  # ADX制限なし（JPYクロスはトレンドフォロー環境多い）
        "adx_trend_bonus_threshold": 30,
    },
    "EURJPY=X": {
        "label": "EUR/JPY",
        "is_jpy": True, "pip_mult": 100,
        "spread_model": {
            "tokyo_early": 0.040,   # 4.0pip
            "asia":        0.020,   # 2.0pip
            "ldn_ny":      0.015,   # 1.5pip
            "ny_late":     0.025,   # 2.5pip
            "close":       0.040,   # 4.0pip
        },
        "death_valley": frozenset({0, 1, 21, 22, 23}),
        "gold_hours": frozenset({7, 8, 9, 10, 14, 15, 16}),
        "adx_max": 999,
        "adx_trend_bonus_threshold": 30,
    },
    "GBPUSD=X": {
        "label": "GBP/USD",
        "is_jpy": False, "pip_mult": 10000,
        "spread_model": {
            "tokyo_early": 0.00025, # 2.5pip
            "asia":        0.00015, # 1.5pip
            "ldn_ny":      0.00010, # 1.0pip
            "ny_late":     0.00015, # 1.5pip
            "close":       0.00025, # 2.5pip
        },
        # GBP/USD: EUR/USD同様にレンジ環境でのBB反発がメイン
        "death_valley": frozenset({0, 1, 2, 21, 22, 23}),
        "gold_hours": frozenset({7, 8, 9, 10, 13, 14, 15}),
        "adx_max": 25,  # EUR/USD同様レンジ限定
        "adx_trend_bonus_threshold": 999,  # トレンドボーナスなし
    },
    "AUDUSD=X": {
        "label": "AUD/USD",
        "is_jpy": False, "pip_mult": 10000,
        "spread_model": {
            "tokyo_early": 0.00025, # 2.5pip
            "asia":        0.00015, # 1.5pip
            "ldn_ny":      0.00012, # 1.2pip
            "ny_late":     0.00018, # 1.8pip
            "close":       0.00030, # 3.0pip
        },
        # AUD/USD: Sydney/Tokyo活発。NY終盤は死。
        "death_valley": frozenset({20, 21, 22, 23, 0}),
        "gold_hours": frozenset({0, 1, 2, 3, 4, 5, 7, 8}),  # Sydney/Tokyo + LDN open
        "adx_max": 25,
        "adx_trend_bonus_threshold": 999,
    },
    "USDCHF=X": {
        "label": "USD/CHF",
        "is_jpy": False, "pip_mult": 10000,
        "spread_model": {
            "tokyo_early": 0.00025, # 2.5pip
            "asia":        0.00018, # 1.8pip
            "ldn_ny":      0.00012, # 1.2pip
            "ny_late":     0.00018, # 1.8pip
            "close":       0.00025, # 2.5pip
        },
        "death_valley": frozenset({0, 1, 2, 21, 22, 23}),
        "gold_hours": frozenset({7, 8, 9, 10, 13, 14, 15}),
        "adx_max": 25,
        "adx_trend_bonus_threshold": 999,
    },
    "CADJPY=X": {
        "label": "CAD/JPY",
        "is_jpy": True, "pip_mult": 100,
        "spread_model": {
            "tokyo_early": 0.060,   # 6.0pip
            "asia":        0.035,   # 3.5pip
            "ldn_ny":      0.025,   # 2.5pip
            "ny_late":     0.040,   # 4.0pip
            "close":       0.060,   # 6.0pip
        },
        "death_valley": frozenset({0, 1, 2, 20, 21, 22, 23}),
        "gold_hours": frozenset({7, 8, 9, 13, 14, 15}),
        "adx_max": 999,
        "adx_trend_bonus_threshold": 30,
    },
}

# 比較用: 既存ペア
BASELINE_CONFIG = {
    "USDJPY=X": {
        "label": "USD/JPY (base)",
        "is_jpy": True, "pip_mult": 100,
        "spread_model": {
            "tokyo_early": 0.008, "asia": 0.004,
            "ldn_ny": 0.002, "ny_late": 0.003, "close": 0.008,
        },
        "death_valley": frozenset({0, 1, 9, 12, 13, 14, 15, 16}),
        "gold_hours": frozenset({5, 6, 7, 8, 19, 20, 21, 22, 23}),
        "adx_max": 999,
        "adx_trend_bonus_threshold": 30,
    },
    "EURUSD=X": {
        "label": "EUR/USD (base)",
        "is_jpy": False, "pip_mult": 10000,
        "spread_model": {
            "tokyo_early": 0.00008, "asia": 0.00004,
            "ldn_ny": 0.00002, "ny_late": 0.00003, "close": 0.00008,
        },
        "death_valley": frozenset(),  # EUR/USDはDeath Valleyなし（ADX<25で制御）
        "gold_hours": frozenset(),
        "adx_max": 25,
        "adx_trend_bonus_threshold": 999,
    },
}


def get_spread(hour_utc: int, cfg: dict) -> float:
    """時間帯変動スプレッドモデル"""
    sm = cfg["spread_model"]
    if hour_utc < 2:    return sm["tokyo_early"]
    elif hour_utc < 7:  return sm["asia"]
    elif hour_utc < 16: return sm["ldn_ny"]
    elif hour_utc < 20: return sm["ny_late"]
    else:               return sm["close"]


def fetch_data(symbol, days=7, interval="1m"):
    import yfinance as yf
    df = yf.download(symbol, period=f"{days}d", interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if len(df) < 100:
        return None
    return add_indicators(df).dropna()


def run_pair_bt(symbol: str, cfg: dict, days: int = 7):
    """1ペアのbb_rsi BT実行"""
    label = cfg["label"]
    is_jpy = cfg["is_jpy"]
    pip_mult = cfg["pip_mult"]

    print(f"\n{'='*60}")
    print(f"  {label} bb_rsi BT ({days}d, 1m)")
    print(f"{'='*60}")

    df = fetch_data(symbol, days=days)
    if df is None or len(df) < 200:
        print(f"  ERROR: データ不足 ({0 if df is None else len(df)} bars)")
        return None

    print(f"  Bars: {len(df)}")

    # ── ペア別BBRsiReversion (カスタムパラメータ) ──
    strat = BBRsiReversion()

    MAX_HOLD = 40
    COOLDOWN = 1
    MIN_RR = 1.2

    trades = []
    last_exit_bar = -99  # EXIT-based cooldown
    hourly_stats = {}  # 時間帯別統計

    for i in range(200, len(df) - MAX_HOLD - 1):
        if i - last_exit_bar < COOLDOWN:
            continue

        row = df.iloc[i]
        entry = float(row["Close"])
        atr = float(row.get("atr", 0.001))
        atr7 = float(row.get("atr7", atr))
        if atr <= 0:
            continue

        # Bar range filter
        bar_range = float(row["High"]) - float(row["Low"])
        _min_br = 0.008 if is_jpy else 0.00008
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

        # ── ペア別フィルター適用 (カスタム evaluate) ──
        # Death Valley
        if hour_utc in cfg.get("death_valley", frozenset()):
            continue

        # ADX filter
        adx_val = float(row.get("adx", 25))
        if adx_val >= cfg.get("adx_max", 999):
            continue

        # Build SignalContext
        bar_df = df.iloc[max(0, i - 500):i + 1]
        _prev = df.iloc[i - 1] if i >= 1 else row

        ctx = SignalContext(
            entry=entry,
            open_price=float(row["Open"]),
            atr=atr,
            atr7=atr7,
            ema9=float(row.get("ema9", entry)),
            ema21=float(row.get("ema21", entry)),
            ema50=float(row.get("ema50", entry)),
            ema200=float(row.get("ema200", entry)),
            rsi=float(row.get("rsi", 50)),
            rsi5=float(row.get("rsi5", 50)),
            rsi9=float(row.get("rsi9", 50)),
            stoch_k=float(row.get("stoch_k", 50)),
            stoch_d=float(row.get("stoch_d", 50)),
            adx=adx_val,
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
            symbol=symbol, tf="1m",
            is_jpy=is_jpy,
            pip_mult=pip_mult,
            df=bar_df,
            backtest_mode=True,
            bar_time=bar_time,
            hour_utc=hour_utc,
        )

        # ── Evaluate (戦略内のis_jpyフィルターをバイパスし、ペア別設定を使用) ──
        # 直接条件チェック（BBRsiReversionのevaluateはis_jpyしか見ないため）
        signal = None
        score = 0.0
        reasons = []
        sl = 0.0
        tp = 0.0
        _min_sl = 0.030 if is_jpy else 0.00030

        bbpb = ctx.bbpb
        rsi5 = ctx.rsi5
        stoch_k = ctx.stoch_k
        stoch_d = ctx.stoch_d

        # ── BUY ──
        if (bbpb <= 0.25 and rsi5 < 45
                and stoch_k < 45 and stoch_k > stoch_d):
            signal = "BUY"
            tier1 = bbpb <= 0.05 and rsi5 < 25 and stoch_k < 20
            score = (4.5 if tier1 else 3.0) + (38 - rsi5) * 0.06
            reasons.append(f"BB%B={bbpb:.2f}<=0.25")
            # Stoch gap bonus
            gap = stoch_k - stoch_d
            if gap > 1.5: score += 0.6
            elif gap > 0.5: score += 0.3
            # Prev bar
            if ctx.prev_close <= ctx.prev_open: score += 0.3
            # MACD
            if ctx.macdh > 0: score += 0.5
            if ctx.macdh > ctx.macdh_prev and ctx.macdh_prev <= ctx.macdh_prev2:
                score += 0.6
            tp_mult = 2.0 if tier1 else 1.5
            tp = entry + atr7 * tp_mult
            sl_dist = max(abs(entry - ctx.bb_lower) + atr7 * 0.3, _min_sl)
            sl = entry - sl_dist

        # ── SELL ──
        if (signal is None and bbpb >= 0.75 and rsi5 > 55
                and stoch_k > 55 and stoch_k < stoch_d):
            signal = "SELL"
            tier1 = bbpb >= 0.95 and rsi5 > 75 and stoch_k > 80
            score = (4.5 if tier1 else 3.0) + (rsi5 - 58) * 0.06
            reasons.append(f"BB%B={bbpb:.2f}>=0.75")
            gap = stoch_d - stoch_k
            if gap > 1.5: score += 0.6
            if ctx.prev_close >= ctx.prev_open: score += 0.3
            if ctx.macdh < 0: score += 0.5
            if ctx.macdh < ctx.macdh_prev and ctx.macdh_prev >= ctx.macdh_prev2:
                score += 0.6
            tp_mult = 2.0 if tier1 else 1.5
            tp = entry - atr7 * tp_mult
            sl_dist = max(abs(ctx.bb_upper - entry) + atr7 * 0.3, _min_sl)
            sl = entry + sl_dist

        if signal is None:
            continue

        # ── Gold Hours bonus ──
        if hour_utc in cfg.get("gold_hours", frozenset()):
            score += 0.5
        # ADX trend bonus
        if adx_val >= cfg.get("adx_trend_bonus_threshold", 999):
            score += 0.6

        # ── Entry at next bar's Open + spread ──
        if i + 1 >= len(df):
            continue
        ep = float(df.iloc[i + 1]["Open"])
        spread = get_spread(hour_utc, cfg)
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

        # ── SL widening: low-liquidity hours ──
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
                    if signal == "BUY":
                        outcome = "WIN" if _current_sl >= ep else "LOSS"
                    else:
                        outcome = "WIN" if _current_sl <= ep else "LOSS"
                else:
                    outcome = "LOSS"
                bars_held = j
                break

        if outcome is None:
            # MAX_HOLD timeout
            _last_close = float(df.iloc[min(i + 1 + MAX_HOLD, len(df) - 1)]["Close"])
            if signal == "BUY":
                outcome = "WIN" if _last_close > ep + spread else "LOSS"
            else:
                outcome = "WIN" if _last_close < ep - spread else "LOSS"
            bars_held = MAX_HOLD

        # Pips calculation (exit spread deduction)
        exit_spread = get_spread(
            df.index[min(i + 1 + bars_held, len(df) - 1)].hour
            if hasattr(df.index[min(i + 1 + bars_held, len(df) - 1)], 'hour') else 12,
            cfg
        )
        if outcome == "WIN":
            _pips = tp_dist * pip_mult - (spread + exit_spread) / 2 * pip_mult
        else:
            _pips = -(sl_dist * pip_mult + (spread + exit_spread) / 2 * pip_mult)

        # EXIT-based cooldown
        last_exit_bar = i + 1 + bars_held

        # Hourly stats
        if hour_utc not in hourly_stats:
            hourly_stats[hour_utc] = {"wins": 0, "losses": 0, "pips": 0.0}
        if outcome == "WIN":
            hourly_stats[hour_utc]["wins"] += 1
        else:
            hourly_stats[hour_utc]["losses"] += 1
        hourly_stats[hour_utc]["pips"] += _pips

        trades.append({
            "outcome": outcome,
            "bars_held": bars_held,
            "sig": signal,
            "ep": round(ep, 3 if is_jpy else 5),
            "sl_pip": round(sl_dist * pip_mult, 1),
            "tp_pip": round(tp_dist * pip_mult, 1),
            "pips": round(_pips, 1),
            "spread_pip": round(spread * pip_mult, 1),
            "rr": round(actual_rr, 1),
            "hour_utc": hour_utc,
            "entry_time": str(bar_time)[:19],
            "be_hit": _be_activated,
        })

    # ── Results ──
    n = len(trades)
    if n == 0:
        print("  0 trades")
        return {"label": label, "trades": 0, "trade_log": [], "hourly_stats": {}}

    wins = sum(1 for t in trades if t["outcome"] == "WIN")
    wr = wins / n * 100
    total_pips = sum(t["pips"] for t in trades)
    avg_pips = total_pips / n
    avg_rr = sum(t["rr"] for t in trades) / n
    avg_hold = sum(t["bars_held"] for t in trades) / n
    avg_spread = sum(t["spread_pip"] for t in trades) / n
    be_count = sum(1 for t in trades if t["be_hit"])
    ev = avg_pips  # EV = average pips per trade

    # Gross pips (spread前)
    gross_pips = 0
    for t in trades:
        if t["outcome"] == "WIN":
            gross_pips += t["tp_pip"]
        else:
            gross_pips -= t["sl_pip"]

    print(f"  Trades: {n}")
    print(f"  WR: {wr:.1f}%")
    print(f"  Total (net): {total_pips:.1f}pip")
    print(f"  Total (gross): {gross_pips:.1f}pip")
    print(f"  Avg: {avg_pips:.1f}pip/trade")
    print(f"  Avg RR: {avg_rr:.1f}")
    print(f"  Avg Hold: {avg_hold:.1f}min")
    print(f"  Avg Spread: {avg_spread:.1f}pip")
    print(f"  BE activated: {be_count}/{n}")
    print(f"  EV: {ev:.2f}pip/trade")

    # Hourly breakdown (top hours)
    print(f"\n  --- Hourly Breakdown ---")
    for h in sorted(hourly_stats.keys()):
        hs = hourly_stats[h]
        hn = hs["wins"] + hs["losses"]
        if hn == 0:
            continue
        hwr = hs["wins"] / hn * 100
        print(f"    UTC {h:02d}: {hn}t WR={hwr:.0f}% {hs['pips']:.1f}pip")

    # Sample trades
    print(f"\n  --- Sample Trades (first 15) ---")
    for t in trades[:15]:
        _be = "BE" if t["be_hit"] else "  "
        print(f"    {t['entry_time']} {t['sig']:4s} {t['outcome']:4s} "
              f"ep={t['ep']} SL={t['sl_pip']:.1f}p TP={t['tp_pip']:.1f}p "
              f"spread={t['spread_pip']:.1f}p hold={t['bars_held']}m {_be}")

    return {
        "label": label, "trades": n, "win_rate": wr,
        "total_pips_net": total_pips, "total_pips_gross": gross_pips,
        "avg_pips": avg_pips, "avg_rr": avg_rr, "avg_spread": avg_spread,
        "ev": ev, "trade_log": trades, "hourly_stats": hourly_stats,
    }


# ── Main ──
if __name__ == "__main__":
    results = {}

    # 新ペア
    for sym, cfg in PAIR_CONFIG.items():
        r = run_pair_bt(sym, cfg, days=7)
        results[sym] = r

    # ベースライン比較
    for sym, cfg in BASELINE_CONFIG.items():
        r = run_pair_bt(sym, cfg, days=7)
        results[sym] = r

    # ── Summary ──
    print(f"\n{'='*75}")
    print(f"  MULTI-PAIR bb_rsi SUMMARY")
    print(f"{'='*75}")
    print(f"  {'Pair':<18s} {'Trades':>6s} {'WR':>6s} {'Net pip':>8s} "
          f"{'Gross':>8s} {'EV/t':>7s} {'AvgSpd':>7s} {'Verdict':>10s}")
    print(f"  {'-'*68}")

    for sym in list(PAIR_CONFIG.keys()) + list(BASELINE_CONFIG.keys()):
        r = results.get(sym)
        if r is None or r["trades"] == 0:
            print(f"  {PAIR_CONFIG.get(sym, BASELINE_CONFIG.get(sym, {})).get('label', sym):<18s} {'0':>6s} {'—':>6s} {'—':>8s} {'—':>8s} {'—':>7s} {'—':>7s} {'NO DATA':>10s}")
            continue
        verdict = "✅ GO" if r["ev"] > 0 else "❌ NO"
        print(f"  {r['label']:<18s} {r['trades']:>6d} {r['win_rate']:>5.1f}% "
              f"{r['total_pips_net']:>+8.1f} {r['total_pips_gross']:>+8.1f} "
              f"{r['ev']:>+7.2f} {r['avg_spread']:>6.1f}p {verdict:>10s}")

    print(f"\n  Key: Net=after spread, Gross=before spread, EV=avg pip/trade")
    print(f"  Spread model: OANDA typical (time-varying by session)")
