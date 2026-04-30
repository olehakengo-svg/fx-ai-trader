"""DT v2.3-style cascade prototype: 4H regime → 1D macro → 15m bounce.

Empirical BT only — no strategy module yet.
"""
import os, sys, math
os.environ.setdefault("BT_MODE", "1"); os.environ.setdefault("NO_AUTOSTART", "1")
sys.path.insert(0, '.')
import pandas as pd, numpy as np
from collections import Counter
from modules.regime_classifier import classify_15m, REGIME_MODERATE_TREND, hurst_rs
from modules.indicators import add_indicators

PAIRS = ["USD_JPY", "EUR_USD"]
DAYS = 365  # try max range

def session_of(h):
    if 0 <= h < 6: return "Tokyo"
    if 6 <= h < 12: return "London"
    if 12 <= h < 21: return "NY"
    return "Sydney"

def wilson_lo(wins, n, z=1.96):
    if n == 0: return 0
    p = wins / n
    centre = (p + z*z/(2*n))/(1 + z*z/n)
    margin = z*math.sqrt((p*(1-p) + z*z/(4*n))/n)/(1 + z*z/n)
    return max(0, centre - margin) * 100

def run_pair(symbol):
    df_15 = pd.read_parquet(f'data/cache/massive/{symbol}_15m.parquet')
    df_1h = pd.read_parquet(f'data/cache/massive/{symbol}_1h.parquet')
    end = df_15.index.max(); start = end - pd.Timedelta(days=DAYS)
    df_15 = df_15[df_15.index >= start].copy()
    df_1h = df_1h[df_1h.index >= start].copy()
    
    # Resample 1h → 4h, 1h → 1d
    df_4h = df_1h.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
    df_1d = df_1h.resample('1D').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
    
    df_15 = add_indicators(df_15).dropna()
    df_4h = add_indicators(df_4h).dropna()
    df_1d = add_indicators(df_1d).dropna()
    
    # Pre-compute 4H regime features
    h4_feat = {}
    for i in range(64, len(df_4h)):
        bar = df_4h.iloc[i]; prev = df_4h.iloc[i-1]
        slope = float(bar.get("ema21", 0)) - float(prev.get("ema21", 0))
        h = hurst_rs(df_4h["Close"].iloc[i-64:i].tolist())
        h4_feat[df_4h.index[i]] = {
            "adx": float(bar.get("adx", 0)),
            "ema_slope": slope,
            "atr15": float(bar.get("atr", 0)),
            "range_20": float(df_4h["High"].iloc[i-20:i].max() - df_4h["Low"].iloc[i-20:i].min()),
            "hurst_64": h,
            "ema21": float(bar.get("ema21", 0)),
        }
    h4_idx = pd.DatetimeIndex(list(h4_feat.keys()))
    
    # Pre-compute 1D macro
    d1_feat = {}
    for i in range(50, len(df_1d)):
        bar = df_1d.iloc[i]
        d1_feat[df_1d.index[i]] = {
            "ema21": float(bar.get("ema21", 0)),
            "ema50": float(bar.get("ema50", 0)),
        }
    d1_idx = pd.DatetimeIndex(list(d1_feat.keys()))
    
    pip_mult = 100 if "JPY" in symbol else 10000
    pip_size = 1.0 / pip_mult
    MIN_SL_PIPS = 10  # DT scale: larger SL than scalp
    RR_FLOOR = 1.5
    MAX_HOLD = 16  # 16 × 15m = 4 hours
    COOLDOWN = 4   # 4 × 15m = 1 hour
    
    trades = []
    last_fire = -1000
    
    for i in range(50, len(df_15) - MAX_HOLD - 1):
        if i - last_fire < COOLDOWN: continue
        bar = df_15.iloc[i]; prev = df_15.iloc[i-1]; ts = df_15.index[i]
        
        # L1: 4H regime
        h4_pos = h4_idx.searchsorted(ts, side="right") - 1
        if h4_pos < 0: continue
        h4 = h4_feat[h4_idx[h4_pos]]
        if classify_15m(h4) != REGIME_MODERATE_TREND: continue
        
        # Macro: 1D EMA21 vs EMA50
        d1_pos = d1_idx.searchsorted(ts, side="right") - 1
        if d1_pos < 0: continue
        d1 = d1_feat[d1_idx[d1_pos]]
        if d1["ema21"] <= 0 or d1["ema50"] <= 0: continue
        d1_bull = d1["ema21"] > d1["ema50"]
        d1_bear = d1["ema21"] < d1["ema50"]
        
        # 4H slope direction
        h4_slope = h4["ema_slope"]
        if h4_slope > 0 and d1_bull:
            sd = +1
        elif h4_slope < 0 and d1_bear:
            sd = -1
        else:
            continue
        
        # L3: 15m candle direction + min_bounce
        atr = float(bar.get("atr", 0))
        atr14 = float(bar.get("atr14", atr))  # may not exist
        if atr <= 0: continue
        ema21 = float(bar.get("ema21", 0))
        if ema21 <= 0: continue
        entry = float(bar.Close); op = float(bar.Open)
        p_close = float(prev.Close)
        min_bounce = atr * 0.3
        
        if sd > 0:
            if (entry - ema21) < min_bounce: continue
            if not (entry > p_close and entry > op): continue
            sig = "BUY"
            sl_raw = ema21 - atr * 0.5
            sl_dist = max(entry - sl_raw, MIN_SL_PIPS * pip_size)
            sl = entry - sl_dist
            tp = entry + sl_dist * RR_FLOOR
        else:
            if (ema21 - entry) < min_bounce: continue
            if not (entry < p_close and entry < op): continue
            sig = "SELL"
            sl_raw = ema21 + atr * 0.5
            sl_dist = max(sl_raw - entry, MIN_SL_PIPS * pip_size)
            sl = entry + sl_dist
            tp = entry - sl_dist * RR_FLOOR
        
        # Simulate forward
        win = None
        for j in range(i+1, min(i+MAX_HOLD+1, len(df_15))):
            h = df_15.iloc[j].High; l = df_15.iloc[j].Low
            if sig == "BUY":
                if l <= sl: win = False; break
                if h >= tp: win = True; break
            else:
                if h >= sl: win = False; break
                if l <= tp: win = True; break
        if win is None: continue
        pip_w = abs(tp - entry) * pip_mult
        pip_l = abs(entry - sl) * pip_mult
        trades.append({"win": win, "pips": pip_w if win else -pip_l, "sig": sig, "ts": ts, "session": session_of(ts.hour)})
        last_fire = i
    return trades

# Run + analyze
print(f"DT Regime Cascade Prototype — 4H regime + 1D macro + 15m bounce ({DAYS}d)")
print("=" * 80)
all_cells = {}
for sym in PAIRS:
    trades = run_pair(sym)
    by_sess = Counter(t["session"] for t in trades)
    print(f"\n{sym}: total N={len(trades)}, sessions={dict(by_sess)}")
    if not trades: continue
    n = len(trades); wins = sum(1 for t in trades if t["win"])
    avg_w = np.mean([t["pips"] for t in trades if t["win"]]) if wins else 0
    avg_l = np.mean([abs(t["pips"]) for t in trades if not t["win"]]) if (n-wins) else 0
    pf = (wins*avg_w)/((n-wins)*avg_l) if (n-wins) and avg_l else float("inf")
    ev = np.mean([t["pips"] for t in trades])
    wlo = wilson_lo(wins, n)
    bev = 100.0/(1+pf) if pf > 0 else 0
    if avg_l:
        b = avg_w/avg_l; p = wins/n
        kelly = ((b*p - (1-p))/b)*100
    else:
        kelly = float("inf")
    print(f"  N={n} W={wins} L={n-wins} WR={100*wins/n:.1f}% (Wlo={wlo:.1f}% BEV={bev:.1f}%)")
    print(f"  PF={pf:.2f} EV={ev:+.2f}p Kelly={kelly:+.1f}%  avg_win={avg_w:.2f} avg_loss={avg_l:.2f}")
    all_cells[(sym, "ALL")] = trades

# Cell-level: Bonferroni cell = strategy(1) × pair(2) × session(3) = 6
print(f"\n=== Bonferroni cell-level (cell=6, α={0.05/6:.5f}) ===")
print(f"{'cell':30s} {'N':>5s} {'WR%':>6s} {'PF':>6s} {'EV(p)':>7s} {'Kelly%':>7s} Rule1")
for sym in PAIRS:
    trades = run_pair(sym) if (sym, "ALL") not in all_cells else all_cells[(sym, "ALL")]
    by_sess = {}
    for t in trades:
        by_sess.setdefault(t["session"], []).append(t)
    for sess, ts in sorted(by_sess.items()):
        n = len(ts)
        if n == 0: continue
        wins = sum(1 for t in ts if t["win"])
        avg_w = np.mean([t["pips"] for t in ts if t["win"]]) if wins else 0
        avg_l = np.mean([abs(t["pips"]) for t in ts if not t["win"]]) if (n-wins) else 0
        pf = (wins*avg_w)/((n-wins)*avg_l) if (n-wins) and avg_l else float("inf")
        ev = np.mean([t["pips"] for t in ts])
        bev = 100.0/(1+pf) if pf>0 else 0
        if avg_l:
            b = avg_w/avg_l; p = wins/n
            kelly = ((b*p - (1-p))/b)*100
        else:
            kelly = 0
        passed = n >= 30 and pf >= 1.20 and ev > 0 and kelly > 0 and 100*wins/n > bev
        flag = "✅" if passed else "❌"
        print(f"{sym} × {sess:20s} {n:5d} {100*wins/n:5.1f}% {pf:5.2f} {ev:+6.2f}p {kelly:+6.1f}% {flag}")
