"""
FX AI Trader  —  USD/JPY Day Trading Signal Dashboard
======================================================
v3: 全精度改善モジュール搭載
  ① マルチタイムフレーム コンフルエンス
  ② ローソク足パターン認識 (8種)
  ③ ダウ理論 高値・安値構造
  ④ 出来高 / OBV 分析
  ⑤ RSI / MACD ダイバージェンス検出
  ⑥ S/R スナップ SL/TP
  ⑦ セッション時間帯フィルター
  ⑧ 閾値厳格化 (0.28)
"""

from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import os
import warnings
warnings.filterwarnings("ignore")

from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

app = Flask(__name__)

# ═══════════════════════════════════════════════════════
#  Timeframe config
# ═══════════════════════════════════════════════════════
TF_CFG = {
    "1m":  dict(interval="1m",  period="5d",   resample=None,  sr_w=10, sr_tol=0.0020, ch_lb=200),
    "5m":  dict(interval="5m",  period="25d",  resample=None,  sr_w=10, sr_tol=0.0020, ch_lb=150),
    "15m": dict(interval="15m", period="55d",  resample=None,  sr_w=8,  sr_tol=0.0025, ch_lb=120),
    "30m": dict(interval="30m", period="55d",  resample=None,  sr_w=6,  sr_tol=0.0030, ch_lb=100),
    "1h":  dict(interval="1h",  period="55d",  resample=None,  sr_w=5,  sr_tol=0.0030, ch_lb=80),
    "4h":  dict(interval="1h",  period="90d",  resample="4h",  sr_w=4,  sr_tol=0.0050, ch_lb=60),
    "1d":  dict(interval="1d",  period="2y",   resample=None,  sr_w=5,  sr_tol=0.0060, ch_lb=50),
    "1w":  dict(interval="1wk", period="10y",  resample=None,  sr_w=3,  sr_tol=0.0100, ch_lb=30),
    "1M":  dict(interval="1mo", period="max",  resample=None,  sr_w=2,  sr_tol=0.0150, ch_lb=20),
}

# ① MTF: higher timeframes to check per current TF
MTF_HIGHER = {
    "1m":  ["5m", "15m", "1h"],
    "5m":  ["15m", "1h", "4h"],
    "15m": ["1h", "4h", "1d"],
    "30m": ["1h", "4h", "1d"],
    "1h":  ["4h", "1d"],
    "4h":  ["1d", "1w"],
    "1d":  ["1w"],
    "1w":  ["1M"],
    "1M":  [],
}

# Caches
_data_cache:  dict = {}  # (symbol,interval,period) -> (df, timestamp)
_bt_cache:    dict = {}  # backtest result cache
_news_cache:  dict = {}  # news sentiment cache
CACHE_TTL    = 300       # 5 min data cache
BT_CACHE_TTL = 21600     # 6 hour backtest cache
NEWS_TTL     = 1800      # 30 min news cache

# Swing-mode ATR multipliers per timeframe
TF_SL_MULT = {
    "1m": 1.5, "5m": 1.5, "15m": 1.5, "30m": 1.8,
    "1h": 2.2, "4h": 2.5, "1d": 3.0, "1w": 3.5, "1M": 4.0,
}
TF_TP_MULT = {
    "1m": 2.5, "5m": 2.5, "15m": 2.5, "30m": 3.0,
    "1h": 3.3, "4h": 3.8, "1d": 5.0, "1w": 6.0, "1M": 7.0,
}
TF_MIN_RR = {
    "1m": 1.2, "5m": 1.2, "15m": 1.3, "30m": 1.4,
    "1h": 1.5, "4h": 1.6, "1d": 1.8, "1w": 1.8, "1M": 2.0,
}


# ═══════════════════════════════════════════════════════
#  Data fetching
# ═══════════════════════════════════════════════════════
def _fetch_raw(symbol: str, period: str, interval: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC")
    return df.dropna()


def fetch_ohlcv(symbol="USDJPY=X", period="5d", interval="1m") -> pd.DataFrame:
    key = (symbol, interval, period)
    now = datetime.now()
    if key in _data_cache:
        cached_df, ts = _data_cache[key]
        if (now - ts).total_seconds() < CACHE_TTL:
            return cached_df.copy()
    df = _fetch_raw(symbol, period, interval)
    _data_cache[key] = (df, now)
    return df.copy()


def resample_df(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return df.resample(rule).agg(
        Open=("Open","first"), High=("High","max"),
        Low=("Low","min"),    Close=("Close","last"),
        Volume=("Volume","sum")
    ).dropna()


# ═══════════════════════════════════════════════════════
#  Indicators
# ═══════════════════════════════════════════════════════
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c, h, l = df["Close"], df["High"], df["Low"]
    df["ema9"]      = EMAIndicator(c, window=9).ema_indicator()
    df["ema21"]     = EMAIndicator(c, window=21).ema_indicator()
    df["ema50"]     = EMAIndicator(c, window=50).ema_indicator()
    df["rsi"]       = RSIIndicator(c, window=14).rsi()
    m = MACD(c, window_slow=26, window_fast=12, window_sign=9)
    df["macd"]      = m.macd()
    df["macd_sig"]  = m.macd_signal()
    df["macd_hist"] = m.macd_diff()
    bb = BollingerBands(c, window=20, window_dev=2)
    df["bb_upper"]  = bb.bollinger_hband()
    df["bb_mid"]    = bb.bollinger_mavg()
    df["bb_lower"]  = bb.bollinger_lband()
    df["bb_pband"]  = bb.bollinger_pband()
    df["atr"]       = AverageTrueRange(h, l, c, window=14).average_true_range()
    return df.dropna()


# ═══════════════════════════════════════════════════════
#  ② ローソク足パターン認識
# ═══════════════════════════════════════════════════════
def detect_candle_patterns(df: pd.DataFrame):
    """Detect 8 major reversal/continuation candlestick patterns."""
    if len(df) < 3:
        return 0.0, []

    c0, c1, c2 = df.iloc[-1], df.iloc[-2], df.iloc[-3]
    score   = 0.0
    patterns = []

    body0   = abs(c0["Close"] - c0["Open"])
    body1   = abs(c1["Close"] - c1["Open"])
    rng0    = c0["High"] - c0["Low"]
    up_shd0 = c0["High"] - max(c0["Open"], c0["Close"])
    dn_shd0 = min(c0["Open"], c0["Close"]) - c0["Low"]

    # 1. ハンマー（強気反転）
    if (rng0 > 0 and dn_shd0 >= body0 * 2 and up_shd0 <= body0 * 0.4
            and c1["Close"] < c1["Open"]):
        score += 1.5
        patterns.append("🔨 ハンマー（強気反転）")

    # 2. 射撃線 / 首吊り（弱気）
    if (rng0 > 0 and up_shd0 >= body0 * 2 and dn_shd0 <= body0 * 0.4
            and c1["Close"] > c1["Open"]):
        score -= 1.5
        patterns.append("⭐ 射撃線（弱気反転）")

    # 3. 強気エンガルフィング
    if (c1["Close"] < c1["Open"] and c0["Close"] > c0["Open"]
            and c0["Open"] <= c1["Close"] and c0["Close"] >= c1["Open"]
            and body0 > body1):
        score += 2.0
        patterns.append("📈 強気エンガルフィング")

    # 4. 弱気エンガルフィング
    if (c1["Close"] > c1["Open"] and c0["Close"] < c0["Open"]
            and c0["Open"] >= c1["Close"] and c0["Close"] <= c1["Open"]
            and body0 > body1):
        score -= 2.0
        patterns.append("📉 弱気エンガルフィング")

    # 5. 強気ピンバー（長い下ヒゲ）
    if (rng0 > 0 and dn_shd0 >= rng0 * 0.60 and body0 <= rng0 * 0.25
            and not patterns):
        score += 1.2
        patterns.append("📌 強気ピンバー（長い下ヒゲ）")

    # 6. 弱気ピンバー（長い上ヒゲ）
    if (rng0 > 0 and up_shd0 >= rng0 * 0.60 and body0 <= rng0 * 0.25
            and not any("ピンバー" in p for p in patterns)):
        score -= 1.2
        patterns.append("📌 弱気ピンバー（長い上ヒゲ）")

    # 7. 明けの明星（3本線 強気反転）
    if (c2["Close"] < c2["Open"]
            and abs(c1["Close"] - c1["Open"]) <= (c2["High"] - c2["Low"]) * 0.35
            and c0["Close"] > c0["Open"]
            and c0["Close"] > (c2["Open"] + c2["Close"]) / 2):
        score += 2.0
        patterns.append("🌅 明けの明星（強気3本線）")

    # 8. 宵の明星（3本線 弱気反転）
    if (c2["Close"] > c2["Open"]
            and abs(c1["Close"] - c1["Open"]) <= (c2["High"] - c2["Low"]) * 0.35
            and c0["Close"] < c0["Open"]
            and c0["Close"] < (c2["Open"] + c2["Close"]) / 2):
        score -= 2.0
        patterns.append("🌇 宵の明星（弱気3本線）")

    # ドージ（十字線）= 迷い、単体では中立
    if rng0 > 0 and body0 <= rng0 * 0.10:
        patterns.append("➖ ドージ（十字線・迷い）")

    return score, patterns


# ═══════════════════════════════════════════════════════
#  ③ ダウ理論 高値・安値構造
# ═══════════════════════════════════════════════════════
def dow_theory_analysis(df: pd.DataFrame, window: int = 5):
    """Determine trend by Dow Theory HH/HL or LH/LL structure."""
    if len(df) < window * 6:
        return 0.0, "↔ データ不足（ダウ理論判定不能）"

    H = df["High"].values
    L = df["Low"].values
    n = len(df)

    swing_highs, swing_lows = [], []
    for i in range(window, n - window):
        if H[i] == H[i - window: i + window + 1].max():
            swing_highs.append(H[i])
        if L[i] == L[i - window: i + window + 1].min():
            swing_lows.append(L[i])

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return 0.0, "↔ スウィング不足（ダウ理論判定不能）"

    hh = swing_highs[-1] > swing_highs[-2]  # Higher High
    hl = swing_lows[-1]  > swing_lows[-2]   # Higher Low
    lh = swing_highs[-1] < swing_highs[-2]  # Lower High
    ll = swing_lows[-1]  < swing_lows[-2]   # Lower Low

    if hh and hl:
        return  2.5, "✅ ダウ理論：HH+HL（上昇トレンド確認）"
    elif lh and ll:
        return -2.5, "🔻 ダウ理論：LH+LL（下降トレンド確認）"
    elif hh:
        return  1.0, "↗ ダウ理論：高値更新中（上昇継続の可能性）"
    elif ll:
        return -1.0, "↘ ダウ理論：安値更新中（下降継続の可能性）"
    else:
        return  0.0, "↔ ダウ理論：レンジ相場（明確なトレンドなし）"


# ═══════════════════════════════════════════════════════
#  ④ 出来高 / OBV 分析
# ═══════════════════════════════════════════════════════
def volume_obv_analysis(df: pd.DataFrame):
    """Analyze volume spikes and OBV trend."""
    score, reasons = 0.0, []

    vol = df["Volume"]
    if vol.sum() == 0 or vol.iloc[-1] == 0:
        return 0.0, []  # FX pair with no volume data

    obv = [0.0]
    for i in range(1, len(df)):
        if df["Close"].iloc[i] > df["Close"].iloc[i - 1]:
            obv.append(obv[-1] + vol.iloc[i])
        elif df["Close"].iloc[i] < df["Close"].iloc[i - 1]:
            obv.append(obv[-1] - vol.iloc[i])
        else:
            obv.append(obv[-1])
    obv_s = pd.Series(obv, index=df.index)
    obv_ema = obv_s.ewm(span=14).mean()

    avg_vol  = vol.rolling(20).mean().iloc[-1]
    cur_vol  = vol.iloc[-1]
    ratio    = cur_vol / avg_vol if avg_vol > 0 else 1.0
    price_up = df["Close"].iloc[-1] > df["Close"].iloc[-2]

    if ratio >= 2.0:
        if price_up:
            score += 1.2; reasons.append(f"✅ 出来高急増（{ratio:.1f}x）+ 上昇 → ブレイクアウト確認")
        else:
            score -= 1.2; reasons.append(f"🔻 出来高急増（{ratio:.1f}x）+ 下落 → 売り圧力強")
    elif ratio >= 1.5:
        if price_up:
            score += 0.7; reasons.append(f"↗ 出来高増加（{ratio:.1f}x）+ 上昇")
        else:
            score -= 0.7; reasons.append(f"↘ 出来高増加（{ratio:.1f}x）+ 下落")

    # OBV trend
    if len(obv_s) >= 5:
        if obv_s.iloc[-1] > obv_ema.iloc[-1] and obv_s.iloc[-1] > obv_s.iloc[-5]:
            score += 0.8; reasons.append("✅ OBV上昇（買い資金流入）")
        elif obv_s.iloc[-1] < obv_ema.iloc[-1] and obv_s.iloc[-1] < obv_s.iloc[-5]:
            score -= 0.8; reasons.append("🔻 OBV下降（資金流出）")

        # Price-OBV divergence
        if price_up and obv_s.iloc[-1] < obv_s.iloc[-3]:
            score -= 0.6; reasons.append("⚠️ 価格↑ OBV↓ 弱気ダイバージェンス（注意）")
        elif not price_up and obv_s.iloc[-1] > obv_s.iloc[-3]:
            score += 0.6; reasons.append("⚠️ 価格↓ OBV↑ 強気ダイバージェンス（注目）")

    return score, reasons


# ═══════════════════════════════════════════════════════
#  ⑤ RSI / MACD ダイバージェンス
# ═══════════════════════════════════════════════════════
def detect_divergence(df: pd.DataFrame, lookback: int = 30):
    """Detect bullish/bearish divergence between price and RSI/MACD."""
    score, reasons = 0.0, []
    if len(df) < lookback:
        return score, reasons

    sub = df.tail(lookback)
    H   = sub["High"].values
    L   = sub["Low"].values
    rsi = sub["rsi"].values
    mh  = sub["macd_hist"].values
    n   = len(sub)
    mid = n // 2

    # ── Price swing points in the recent half ──────
    ph_idx = int(np.argmax(H[mid:])) + mid
    pl_idx = int(np.argmin(L[mid:])) + mid

    # Prev swing points in the older half
    ph_prev = int(np.argmax(H[:mid]))
    pl_prev = int(np.argmin(L[:mid]))

    # Bearish RSI divergence: price HH but RSI LH
    if H[ph_idx] > H[ph_prev] and rsi[ph_idx] < rsi[ph_prev]:
        score -= 1.5
        reasons.append("⚠️ RSI 弱気ダイバージェンス（価格↑ RSI↓）→ 反落注意")

    # Bullish RSI divergence: price LL but RSI HL
    if L[pl_idx] < L[pl_prev] and rsi[pl_idx] > rsi[pl_prev]:
        score += 1.5
        reasons.append("✅ RSI 強気ダイバージェンス（価格↓ RSI↑）→ 反発期待")

    # Bearish MACD divergence
    mh_high_recent = np.max(mh[mid:])
    mh_high_prev   = np.max(mh[:mid])
    if H[ph_idx] > H[ph_prev] and mh_high_recent < mh_high_prev:
        score -= 1.0
        reasons.append("⚠️ MACD 弱気ダイバージェンス（モメンタム低下）")

    # Bullish MACD divergence
    mh_low_recent = np.min(mh[mid:])
    mh_low_prev   = np.min(mh[:mid])
    if L[pl_idx] < L[pl_prev] and mh_low_recent > mh_low_prev:
        score += 1.0
        reasons.append("✅ MACD 強気ダイバージェンス（底打ちモメンタム）")

    return score, reasons


# ═══════════════════════════════════════════════════════
#  ⑦ セッション時間帯フィルター
# ═══════════════════════════════════════════════════════
def get_session_info():
    """Return current FX session name, confidence multiplier, and label."""
    h = datetime.now(timezone.utc).hour
    # Session windows (UTC)
    tokyo  = 0  <= h <  9
    london = 8  <= h < 17
    ny     = 13 <= h < 22
    overlap_lnny = 13 <= h < 17   # London + NY  ← highest liquidity
    overlap_tkln = 7  <= h <  9   # Tokyo + London

    if overlap_lnny:
        return {"name": "NY × London", "mult": 1.20, "color": "green",
                "label": "🟢 NY×ロンドン（最高流動性）"}
    if ny:
        return {"name": "New York",    "mult": 1.05, "color": "green",
                "label": "🟢 NYセッション"}
    if overlap_tkln:
        return {"name": "東京 × London","mult": 1.00, "color": "yellow",
                "label": "🟡 東京×ロンドン移行"}
    if london:
        return {"name": "London",       "mult": 1.05, "color": "green",
                "label": "🟢 ロンドンセッション"}
    if tokyo:
        return {"name": "Tokyo",        "mult": 0.90, "color": "yellow",
                "label": "🟡 東京セッション"}
    return     {"name": "Off-hours",   "mult": 0.65, "color": "red",
                "label": "🔴 閑散時間帯（信頼度低）"}


# ═══════════════════════════════════════════════════════
#  ① マルチタイムフレーム コンフルエンス
# ═══════════════════════════════════════════════════════
def mtf_confluence(symbol: str, current_tf: str):
    """Check 2 higher timeframes for trend alignment."""
    higher = MTF_HIGHER.get(current_tf, [])[:2]
    total_score = 0.0
    details = []

    for tf in higher:
        cfg = TF_CFG.get(tf)
        if not cfg:
            continue
        try:
            df = fetch_ohlcv(symbol, period=cfg["period"], interval=cfg["interval"])
            if cfg["resample"]:
                df = resample_df(df, cfg["resample"])
            df  = add_indicators(df)
            row = df.iloc[-1]
            rsi = float(row["rsi"])

            if row["Close"] > row["ema9"] > row["ema21"]:
                tf_sc = 1.5
                trend = "↗ 上昇"
                tcolor = "green"
            elif row["Close"] < row["ema9"] < row["ema21"]:
                tf_sc = -1.5
                trend = "↘ 下降"
                tcolor = "red"
            else:
                tf_sc = 0.0
                trend = "↔ 中立"
                tcolor = "neutral"

            # Dampen if RSI is extreme in opposite direction
            if tf_sc > 0 and rsi > 72: tf_sc *= 0.6
            if tf_sc < 0 and rsi < 28: tf_sc *= 0.6

            total_score += tf_sc
            details.append({
                "tf": tf, "trend": trend, "color": tcolor,
                "rsi": round(rsi, 1), "score": round(tf_sc, 2)
            })
        except Exception:
            pass

    return total_score, details


# ═══════════════════════════════════════════════════════
#  S/R levels  (same as v2)
# ═══════════════════════════════════════════════════════
def find_sr_levels(df, window=5, tolerance_pct=0.003, min_touches=2, max_levels=10):
    H, L, n = df["High"].values, df["Low"].values, len(df)
    pts = []
    for i in range(window, n - window):
        if H[i] == H[i-window:i+window+1].max(): pts.append(float(H[i]))
        if L[i] == L[i-window:i+window+1].min(): pts.append(float(L[i]))
    if not pts:
        return []
    pts.sort()
    clusters, cl = [], [pts[0]]
    for p in pts[1:]:
        if (p - cl[0]) / cl[0] <= tolerance_pct: cl.append(p)
        else: clusters.append(cl); cl = [p]
    clusters.append(cl)
    lvls = [{"price": round(float(np.median(c)),3), "touches": len(c)}
            for c in clusters if len(c) >= min_touches]
    lvls.sort(key=lambda x: -x["touches"])
    return [l["price"] for l in lvls[:max_levels]]


# ═══════════════════════════════════════════════════════
#  Parallel channel  (same as v2)
# ═══════════════════════════════════════════════════════
def find_parallel_channel(df, window=5, lookback=100):
    if len(df) < window * 4: return None
    fd = df.tail(lookback)
    H, L, n = fd["High"].values, fd["Low"].values, len(fd)
    sh, sl = [], []
    for i in range(window, n - window):
        if H[i] == H[i-window:i+window+1].max(): sh.append(i)
        if L[i] == L[i-window:i+window+1].min(): sl.append(i)
    if len(sh) < 2 or len(sl) < 2: return None
    hm, hb = np.polyfit(sh, H[sh], 1)
    lm, lb = np.polyfit(sl, L[sl], 1)
    offset = len(df) - len(fd)
    ts_arr = [int(t.timestamp()) for t in df.index]
    upper, lower, middle = [], [], []
    for j, ts in enumerate(ts_arr):
        i = j - offset
        hv = round(float(hm*i+hb), 3)
        lv = round(float(lm*i+lb), 3)
        upper .append({"time": ts, "value": hv})
        lower .append({"time": ts, "value": lv})
        middle.append({"time": ts, "value": round((hv+lv)/2, 3)})
    return {"upper": upper, "lower": lower, "middle": middle,
            "trend": "up" if (hm+lm)/2 > 0 else "down"}


# ═══════════════════════════════════════════════════════
#  ⑥ S/R スナップ SL/TP
# ═══════════════════════════════════════════════════════
def calc_sl_tp_v3(entry: float, signal: str, atr: float, sr_levels: list,
                  tf: str = "1m"):
    """
    SL/TP calculation snapped to nearest S/R level.
    ATR multipliers scale with timeframe (larger = swing-style).
    """
    sl_mult  = TF_SL_MULT.get(tf, 1.5)
    tp_mult  = TF_TP_MULT.get(tf, 2.5)
    min_rr   = TF_MIN_RR.get(tf, 1.2)

    if signal == "BUY":
        raw_sl = entry - atr * sl_mult
        raw_tp = entry + atr * tp_mult
        sl_candidates = [l for l in sr_levels if l < entry - atr * 0.3]
        tp_candidates = [l for l in sr_levels if l > entry + atr * 0.5]
        sl = max(sl_candidates) - atr * 0.15 if sl_candidates else raw_sl
        tp = min(tp_candidates) - atr * 0.10 if tp_candidates else raw_tp
    else:  # SELL
        raw_sl = entry + atr * sl_mult
        raw_tp = entry - atr * tp_mult
        sl_candidates = [l for l in sr_levels if l > entry + atr * 0.3]
        tp_candidates = [l for l in sr_levels if l < entry - atr * 0.5]
        sl = min(sl_candidates) + atr * 0.15 if sl_candidates else raw_sl
        tp = max(tp_candidates) + atr * 0.10 if tp_candidates else raw_tp

    # Ensure minimum RR
    if abs(tp - entry) < abs(sl - entry) * min_rr:
        tp = (entry + abs(sl - entry) * (min_rr + 0.3)
              if signal == "BUY"
              else entry - abs(sl - entry) * (min_rr + 0.3))

    return round(sl, 3), round(tp, 3)


# ═══════════════════════════════════════════════════════
#  Momentum score  (lightweight replacement for ML)
# ═══════════════════════════════════════════════════════
def momentum_score(df: pd.DataFrame) -> float:
    """Returns a score in [-1, +1] based on price/indicator momentum."""
    try:
        n   = min(10, len(df))
        rec = df.iloc[-n:]

        # 1) Price momentum: avg return over last n candles
        ret = rec["Close"].pct_change().dropna()
        price_mom = float(np.tanh(ret.mean() / max(ret.std(), 1e-8)))

        # 2) RSI momentum: direction of RSI over last 5 bars
        rsi_chg = float(df["rsi"].iloc[-1] - df["rsi"].iloc[-6]) if len(df) >= 7 else 0.0
        rsi_mom = max(-1.0, min(1.0, rsi_chg / 20.0))

        # 3) EMA alignment strength
        row    = df.iloc[-1]
        spread = float(row["ema9"] - row["ema50"])
        atr    = float(row["atr"]) if float(row["atr"]) > 0 else 1e-4
        ema_mom = max(-1.0, min(1.0, spread / (atr * 3.0)))

        return round((price_mom * 0.4 + rsi_mom * 0.3 + ema_mom * 0.3), 4)
    except Exception:
        return 0.0


# ═══════════════════════════════════════════════════════
#  ⑨ Institutional Flow  (Volume Spike + Force Index + VIX)
# ═══════════════════════════════════════════════════════
def _vol_force(df, vol_window: int = 20):
    """
    出来高×価格方向でForce Indexを計算。
    Returns (force_score[-1,+1], vol_ratio, is_spike)
    force > 0 = 買い圧力, < 0 = 売り圧力
    """
    try:
        vol   = df["Volume"].fillna(0).astype(float)
        close = df["Close"].astype(float)
        if vol.sum() == 0:
            return 0.0, 0.0, False
        avg_vol = vol.iloc[-vol_window:].mean()
        cur_vol = float(vol.iloc[-1])
        ratio   = cur_vol / max(avg_vol, 1.0)
        # 直近3本の価格方向
        if len(close) >= 4:
            price_dir = 1.0 if float(close.iloc[-1]) > float(close.iloc[-4]) else -1.0
        else:
            price_dir = 0.0
        # Force Index = 方向 × 正規化出来高（最大4倍でクリップ）
        force    = price_dir * min(ratio, 4.0) / 4.0
        is_spike = ratio >= 2.0
        return round(force, 4), round(ratio, 2), is_spike
    except Exception:
        return 0.0, 0.0, False


def institutional_flow_score():
    """
    大口ファンド参入を3つの視点で検知:
      ① JPY先物 (6J=F) 出来高×方向 Force Index  → 平均比2倍以上で大口参入シグナル
      ② DXY  (DX-Y.NYB) 出来高×方向 Force Index → USD機関フローの実際の売買量
      ③ VIX  (^VIX)                             → 上昇=リスクオフ=円高圧力
    Returns: (score [-1,+1], detail dict)
    """
    score      = 0.0
    weight_sum = 0.0
    detail     = {}

    # ── ① JPY先物 出来高スパイク + Force Index ──────────────────
    try:
        jpy = fetch_ohlcv("6J=F", period="40d", interval="1d")
        jpy = add_indicators(jpy)
        jpy_force, jpy_ratio, jpy_spike = _vol_force(jpy)
        # JPY先物は逆相関（先物上昇=円高=USD/JPY下落）
        jpy_s = -jpy_force

        score      += jpy_s * 0.40
        weight_sum += 0.40
        detail["jpy_vol_ratio"] = f"{jpy_ratio:.1f}x"
        detail["jpy_spike"]     = jpy_spike

        if jpy_ratio >= 1.5:
            if jpy_s > 0.25:
                detail["jpy_direction"] = "🟢 大口USD買い（USD/JPY↑）"
            elif jpy_s < -0.25:
                detail["jpy_direction"] = "🔴 大口円買い（USD/JPY↓）"
            else:
                detail["jpy_direction"] = "⚪ 大口方向不明"
        else:
            detail["jpy_direction"] = "⚫ 通常出来高（様子見）"
        if jpy_spike:
            detail["jpy_direction"] += " 🔥"
    except Exception as e:
        print(f"[INST/JPY] {e}")

    # ── ② DXY 出来高スパイク + Force Index ──────────────────────
    try:
        dxy = fetch_ohlcv("DX-Y.NYB", period="40d", interval="1d")
        dxy = add_indicators(dxy)
        dxy_force, dxy_ratio, dxy_spike = _vol_force(dxy)

        score      += dxy_force * 0.35
        weight_sum += 0.35
        detail["dxy"]           = round(float(dxy["Close"].iloc[-1]), 2)
        detail["dxy_vol_ratio"] = f"{dxy_ratio:.1f}x"
        detail["dxy_spike"]     = dxy_spike

        if dxy_ratio >= 1.5:
            if dxy_force > 0.25:
                detail["dxy_flow"] = "🟢 大口USD買い"
            elif dxy_force < -0.25:
                detail["dxy_flow"] = "🔴 大口USD売り"
            else:
                detail["dxy_flow"] = "⚪ 方向不明"
        else:
            detail["dxy_flow"] = "⚫ 通常出来高"
        if dxy_spike:
            detail["dxy_flow"] += " 🔥"
    except Exception as e:
        print(f"[INST/DXY] {e}")

    # ── ③ VIX（リスクオフ指標）───────────────────────────────────
    try:
        vix_df  = fetch_ohlcv("^VIX", period="20d", interval="1d")
        vix_cur = float(vix_df["Close"].iloc[-1])
        vix_avg = float(vix_df["Close"].mean())
        vix_chg = float(vix_df["Close"].iloc[-1] - vix_df["Close"].iloc[-2])

        # VIX高い/上昇 = リスクオフ = 円高圧力 = USD/JPY↓
        vix_level = max(-1.0, min(1.0, -(vix_cur - 20.0) / 10.0))  # 20=中立
        vix_trend = -1.0 if vix_chg > 0 else 1.0
        vix_s     = vix_level * 0.5 + vix_trend * 0.5

        score      += vix_s * 0.25
        weight_sum += 0.25
        detail["vix"] = round(vix_cur, 1)
        if vix_cur > 25:
            detail["vix_signal"] = "🔴 高VIX リスクオフ（円高圧力）"
        elif vix_cur < 15:
            detail["vix_signal"] = "🟢 低VIX リスクオン（円安圧力）"
        else:
            detail["vix_signal"] = "⚪ VIX中立"
    except Exception as e:
        print(f"[INST/VIX] {e}")

    if weight_sum == 0:
        return 0.0, {}
    normalized = score / weight_sum
    return round(max(-1.0, min(1.0, normalized)), 4), detail


# ═══════════════════════════════════════════════════════
#  ⑩ Fundamental Score  (米日金利差 + 米10年債)
# ═══════════════════════════════════════════════════════
_jp10y_cache: dict = {}
JP10Y_TTL = 86400  # 24時間キャッシュ（日次データのため）

def fetch_jp10y() -> float:
    """
    日本10年国債利回りをFRED（OECD経由）から取得。
    取得失敗時は直近キャッシュ値 or 1.5%にフォールバック。
    """
    global _jp10y_cache
    now = datetime.now()
    if _jp10y_cache.get("ts") and (now - _jp10y_cache["ts"]).total_seconds() < JP10Y_TTL:
        return _jp10y_cache["value"]
    try:
        import urllib.request, csv, io
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IRLTLT01JPM156N"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = list(csv.reader(io.TextIOWrapper(r)))
        # 最終行（最新値）を取得
        for row in reversed(rows):
            if len(row) == 2 and row[1] not in ("", "."):
                value = float(row[1])
                _jp10y_cache = {"value": value, "ts": now}
                return value
    except Exception as e:
        print(f"[JP10Y] FRED取得失敗: {e}")
    # フォールバック: 前回キャッシュ or 1.5%（BOJ利上げ後の近似値）
    return _jp10y_cache.get("value", 1.5)


def fundamental_score():
    """
    米日ファンダメンタル:
      - ^TNX : 米10年債利回り（上昇=USD強）
      - 米日金利差（US10Y - JP10Y）: 拡大=USD強
      - JP10Y: FREDからリアルタイム取得
    Returns: (score [-1,+1], detail dict)
    """
    try:
        tnx = fetch_ohlcv("^TNX", period="30d", interval="1d")
        us10y      = float(tnx["Close"].iloc[-1])
        us10y_prev = float(tnx["Close"].iloc[-6]) if len(tnx) >= 7 else us10y

        # 金利水準スコア: 3%=中立, 1-6%の範囲で正規化
        yield_level = max(-1.0, min(1.0, (us10y - 3.0) / 2.0))

        # 5日間の金利変化方向
        chg = (us10y - us10y_prev) / max(us10y_prev, 1e-4)
        yield_trend = max(-1.0, min(1.0, chg * 20.0))

        # 日本10年利回りをリアルタイム取得
        jp10y    = fetch_jp10y()
        spread   = us10y - jp10y
        # 中立水準を動的に設定: 金利差2%=中立（BOJ利上げ後）
        spread_n = max(-1.0, min(1.0, (spread - 2.0) / 2.0))

        score = (yield_level * 0.30 +
                 yield_trend * 0.40 +
                 spread_n   * 0.30)

        detail = {
            "us10y":      round(us10y, 2),
            "jp10y":      round(jp10y, 2),
            "spread":     round(spread, 2),
            "rate_trend": "上昇（USD強）" if yield_trend > 0 else "低下（USD弱）",
        }
        return round(max(-1.0, min(1.0, score)), 4), detail
    except Exception as e:
        print(f"[FUND] {e}")
        return 0.0, {}


# ═══════════════════════════════════════════════════════
#  Rule-based signal (original 4 indicators)
# ═══════════════════════════════════════════════════════
def rule_signal(row: pd.Series):
    score, reasons = 0.0, []

    if   row["Close"] > row["ema9"] > row["ema21"] > row["ema50"]:
        score += 2.0; reasons.append("✅ 強気トレンド：EMA9>EMA21>EMA50")
    elif row["Close"] < row["ema9"] < row["ema21"] < row["ema50"]:
        score -= 2.0; reasons.append("🔻 弱気トレンド：EMA9<EMA21<EMA50")
    elif row["Close"] > row["ema21"]: score += 0.8; reasons.append("↗ 中期上昇（EMA21上）")
    elif row["Close"] < row["ema21"]: score -= 0.8; reasons.append("↘ 中期下落（EMA21下）")

    rsi = row["rsi"]
    if   rsi < 25: score += 2.5; reasons.append(f"✅ RSI 極度売られ過ぎ ({rsi:.0f})")
    elif rsi < 35: score += 1.5; reasons.append(f"✅ RSI 売られ過ぎ ({rsi:.0f})")
    elif rsi > 75: score -= 2.5; reasons.append(f"🔻 RSI 極度買われ過ぎ ({rsi:.0f})")
    elif rsi > 65: score -= 1.5; reasons.append(f"🔻 RSI 買われ過ぎ ({rsi:.0f})")

    if   row["macd_hist"]>0 and row["macd"]>row["macd_sig"]:
        score += 1.5; reasons.append("✅ MACDゴールデンクロス")
    elif row["macd_hist"]<0 and row["macd"]<row["macd_sig"]:
        score -= 1.5; reasons.append("🔻 MACDデッドクロス")
    elif row["macd_hist"]>0: score += 0.5; reasons.append("↗ MACDヒスト正")
    elif row["macd_hist"]<0: score -= 0.5; reasons.append("↘ MACDヒスト負")

    bp = row["bb_pband"]
    if   bp < 0.05: score += 2.0; reasons.append("✅ ボリンジャー下限タッチ")
    elif bp < 0.15: score += 1.0; reasons.append("↗ ボリンジャー下限近辺")
    elif bp > 0.95: score -= 2.0; reasons.append("🔻 ボリンジャー上限タッチ")
    elif bp > 0.85: score -= 1.0; reasons.append("↘ ボリンジャー上限近辺")

    return score, reasons


# ═══════════════════════════════════════════════════════
#  1H / 4H 上位足バイアス（ハードフィルター用）
# ═══════════════════════════════════════════════════════
_htf_cache: dict = {}
HTF_TTL = 300  # 5分キャッシュ

def get_htf_bias(symbol: str) -> dict:
    """
    1H足と4H足のEMAトレンド構造から上位足バイアスを取得。
    - 両足一致強気  → BUYのみ許可
    - 両足一致弱気  → SELLのみ許可
    - 不一致        → シグナル抑制
    Returns: {score, h1, h4, agreement, label}
    """
    global _htf_cache
    now = datetime.now()
    key = symbol
    if _htf_cache.get(key) and (now - _htf_cache[key]["ts"]).total_seconds() < HTF_TTL:
        return _htf_cache[key]["data"]

    results = {}
    for tf_key, cfg in [("1h", TF_CFG["1h"]), ("4h", TF_CFG["4h"])]:
        try:
            df_h = fetch_ohlcv(symbol, period=cfg["period"], interval=cfg["interval"])
            if cfg.get("resample"):
                df_h = resample_df(df_h, cfg["resample"])
            df_h = add_indicators(df_h)
            row  = df_h.iloc[-1]
            c    = float(row["Close"])
            e9   = float(row["ema9"])
            e21  = float(row["ema21"])
            e50  = float(row["ema50"])
            rsi  = float(row["rsi"])

            if   c > e9 > e21 > e50:  sc = 1.0;  lbl = "↗↗ 強気（全EMA上昇列）"
            elif c > e21 and e9 > e21: sc = 0.6;  lbl = "↗ 強気（EMA21超）"
            elif c > e21:              sc = 0.3;  lbl = "↗ 弱強気（EMA21超）"
            elif c < e9 < e21 < e50:  sc = -1.0; lbl = "↘↘ 弱気（全EMA下降列）"
            elif c < e21 and e9 < e21: sc = -0.6; lbl = "↘ 弱気（EMA21下）"
            elif c < e21:              sc = -0.3; lbl = "↘ 弱弱気（EMA21下）"
            else:                      sc = 0.0;  lbl = "↔ 中立"

            results[tf_key] = {
                "score": sc, "label": lbl,
                "rsi": round(rsi, 1),
                "ema9": round(e9, 3), "ema21": round(e21, 3), "ema50": round(e50, 3),
                "close": round(c, 3),
            }
        except Exception as e:
            print(f"[HTF/{tf_key}] {e}")
            results[tf_key] = {"score": 0.0, "label": "取得失敗", "rsi": 50.0}

    h1_sc = results.get("1h", {}).get("score", 0.0)
    h4_sc = results.get("4h", {}).get("score", 0.0)

    # 4H優先の加重平均（4H=60%, 1H=40%）
    avg = round(h1_sc * 0.40 + h4_sc * 0.60, 3)

    if   h1_sc > 0.2 and h4_sc > 0.2:  agreement = "bull"; label = "📈 1H+4H 上昇一致 → BUYのみ有効"
    elif h1_sc < -0.2 and h4_sc < -0.2: agreement = "bear"; label = "📉 1H+4H 下降一致 → SELLのみ有効"
    else:                                agreement = "mixed"; label = "⚖️ 1H+4H 不一致 → シグナル抑制中"

    data = {
        "score": avg, "agreement": agreement, "label": label,
        "h1": results.get("1h", {}), "h4": results.get("4h", {}),
    }
    _htf_cache[key] = {"data": data, "ts": now}
    return data


# ═══════════════════════════════════════════════════════
#  Master signal aggregator
# ═══════════════════════════════════════════════════════
def compute_signal(df: pd.DataFrame, tf: str, sr_levels: list, symbol="USDJPY=X"):
    row   = df.iloc[-1]
    entry = float(row["Close"])
    atr   = float(row["atr"])

    # ── Component scores ───────────────────────────
    rule_sc,    rule_rsns   = rule_signal(row)
    candle_sc,  candle_rsns = detect_candle_patterns(df)
    dow_sc,     dow_rsn     = dow_theory_analysis(df)
    vol_sc,     vol_rsns    = volume_obv_analysis(df)
    div_sc,     div_rsns    = detect_divergence(df)
    mtf_sc,     mtf_details = mtf_confluence(symbol, tf)
    session                 = get_session_info()
    mom_sc                  = momentum_score(df)
    inst_sc, inst_detail    = institutional_flow_score()        # ⑨ 大口フロー
    fund_sc, fund_detail    = fundamental_score()               # ⑩ ファンダメンタル
    news_data               = get_news_sentiment()              # ⑪ ニュース
    dw_data                 = get_daily_weekly_direction(symbol) # ⑫ 大局観

    # ── Normalize each component to [-1, +1] ───────
    rule_n   = max(-1.0, min(1.0, rule_sc   / 8.0))
    candle_n = max(-1.0, min(1.0, candle_sc / 4.0))
    dow_n    = max(-1.0, min(1.0, dow_sc    / 2.5))
    vol_n    = max(-1.0, min(1.0, vol_sc    / 2.0))
    div_n    = max(-1.0, min(1.0, div_sc    / 2.5))
    mtf_n    = max(-1.0, min(1.0, mtf_sc    / 3.0))
    mom_n    = max(-1.0, min(1.0, mom_sc))
    inst_n   = max(-1.0, min(1.0, inst_sc))
    fund_n   = max(-1.0, min(1.0, fund_sc))
    news_n   = max(-1.0, min(1.0, float(news_data.get("score", 0.0))))
    dw_n     = max(-1.0, min(1.0, float(dw_data.get("overall_score", 0.0))))

    # ── Weighted combination ────────────────────────
    #  rule 18%, candle 9%, dow 11%, vol 5%, div 5%,
    #  mtf 14%, momentum 9%, institutional 11%, fundamental 8%,
    #  news 5%, daily/weekly 5%
    combined = (
        rule_n   * 0.18 +
        candle_n * 0.09 +
        dow_n    * 0.11 +
        vol_n    * 0.05 +
        div_n    * 0.05 +
        mtf_n    * 0.14 +
        mom_n    * 0.09 +
        inst_n   * 0.11 +
        fund_n   * 0.08 +
        news_n   * 0.05 +
        dw_n     * 0.05
    )

    # ⑦ Session multiplier
    combined *= session["mult"]

    # ── 日足・週足 逆方向フィルター（スイング時）──────────────
    if tf in ("1h", "4h", "1d"):
        dw_overall = float(dw_data.get("overall_score", 0.0))
        if (combined > 0 and dw_overall < -0.5) or (combined < 0 and dw_overall > 0.5):
            combined *= 0.6

    # ── 1H / 4H ハードフィルター（最重要）────────────────────
    # 1H+4H のトレンドと逆方向のシグナルを完全カット
    htf = get_htf_bias(symbol)
    htf_agreement = htf["agreement"]

    if htf_agreement == "bull":
        # 両足強気 → BUYのみ有効、SELLは0に
        if combined < 0:
            combined = 0.0
        else:
            combined = min(1.0, combined * 1.2)  # BUY方向を強化
    elif htf_agreement == "bear":
        # 両足弱気 → SELLのみ有効、BUYは0に
        if combined > 0:
            combined = 0.0
        else:
            combined = max(-1.0, combined * 1.2)  # SELL方向を強化
    else:
        # 不一致 → 全体的に抑制（閾値を実質的に引き上げ）
        combined *= 0.60

    # ⑧ Strict threshold
    THRESHOLD = 0.28

    if   combined >  THRESHOLD: signal, conf = "BUY",  int(min(95, 50 + combined * 55))
    elif combined < -THRESHOLD: signal, conf = "SELL", int(min(95, 50 + abs(combined) * 55))
    else:                       signal, conf = "WAIT", int(max(25, 50 - abs(combined) * 40))

    # ⑥ S/R-snapped SL/TP（TF対応スイングモード）
    # WAIT時はcombinedの符号で方向を決定（0の場合はBUY）
    if signal == "WAIT":
        act_signal = "BUY" if combined >= 0 else "SELL"
    else:
        act_signal = signal
    sl, tp = calc_sl_tp_v3(entry, act_signal, atr, sr_levels, tf=tf)
    rr     = round(abs(tp - entry) / max(abs(sl - entry), 1e-6), 2)

    # ── Institutional / Fundamental / News reasons ───
    inst_rsns = []
    if inst_detail.get("jpy_direction"):
        inst_rsns.append(f"🏦 JPY先物: {inst_detail['jpy_direction']}")
    if inst_detail.get("dxy_flow"):
        inst_rsns.append(f"🏦 DXY({inst_detail.get('dxy','?')}): {inst_detail['dxy_flow']}")
    if inst_detail.get("vix_signal"):
        inst_rsns.append(f"😨 VIX({inst_detail.get('vix','?')}): {inst_detail['vix_signal']}")
    fund_rsns = []
    if fund_detail.get("rate_trend"):
        fund_rsns.append(f"📊 米10年債: {fund_detail['rate_trend']}" +
                         (f" ({fund_detail['us10y']}%)" if "us10y" in fund_detail else ""))
    if fund_detail.get("spread") is not None:
        fund_rsns.append(f"📊 米日金利差: {fund_detail['spread']}%")
    news_rsns = []
    if news_data.get("sentiment"):
        news_rsns.append(f"📰 ニュース: {news_data['sentiment']}")
    dw_rsns = []
    if dw_data.get("bias"):
        dw_rsns.append(f"🔭 {dw_data['bias']}")

    # Assemble reasons
    all_reasons = (
        rule_rsns +
        ([dow_rsn] if dow_rsn and "不足" not in dow_rsn else []) +
        candle_rsns +
        vol_rsns +
        div_rsns +
        inst_rsns +
        fund_rsns +
        news_rsns +
        dw_rsns +
        ([session["label"]] if session["mult"] < 0.85 or session["mult"] >= 1.2 else [])
    )

    ts_str = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name,"strftime") else str(row.name)

    return {
        "timestamp":  ts_str,
        "symbol":     "USD/JPY",
        "tf":         tf,
        "entry":      round(entry, 3),
        "signal":     signal,
        "confidence": conf,
        "sl":         sl,
        "tp":         tp,
        "rr_ratio":   rr,
        "atr":        round(atr, 3),
        "session":       session,
        "mtf":           mtf_details,
        "dow_trend":     dow_rsn,
        "institutional": inst_detail,
        "fundamental":   fund_detail,
        "news":          news_data,
        "daily_weekly":  dw_data,
        "swing_mode":    tf in ("1h", "4h", "1d", "1w"),
        "htf_bias":      htf,
        "indicators": {
            "ema9":     round(float(row["ema9"]),  3),
            "ema21":    round(float(row["ema21"]), 3),
            "ema50":    round(float(row["ema50"]), 3),
            "rsi":      round(float(row["rsi"]),   1),
            "macd":     round(float(row["macd"]),      5),
            "macd_sig": round(float(row["macd_sig"]),  5),
            "macd_hist":round(float(row["macd_hist"]), 5),
            "bb_upper": round(float(row["bb_upper"]), 3),
            "bb_mid":   round(float(row["bb_mid"]),   3),
            "bb_lower": round(float(row["bb_lower"]), 3),
            "bb_pband": round(float(row["bb_pband"]), 3),
        },
        "reasons":  all_reasons,
        "score_detail": {
            "rule":          round(rule_n,   3),
            "candle":        round(candle_n, 3),
            "dow":           round(dow_n,    3),
            "volume":        round(vol_n,    3),
            "divergence":    round(div_n,    3),
            "mtf":           round(mtf_n,    3),
            "momentum":      round(mom_n,    3),
            "institutional": round(inst_n,   3),
            "fundamental":   round(fund_n,   3),
            "news":          round(news_n,   3),
            "daily_weekly":  round(dw_n,     3),
            "combined":      round(combined, 3),
        },
    }


# ═══════════════════════════════════════════════════════
#  日足・週足 大局方向確認（スイング用）
# ═══════════════════════════════════════════════════════
def get_daily_weekly_direction(symbol: str = "USDJPY=X") -> dict:
    """
    日足・週足のトレンド方向を返す。
    スイングトレードの大局観フィルターとして使用。
    """
    result = {}
    try:
        # 日足 (EMA50 + EMA21 + RSI)
        d = fetch_ohlcv(symbol, period="1y",  interval="1d")
        d = add_indicators(d)
        dr = d.iloc[-1]
        daily_dir = 1.0 if float(dr["Close"]) > float(dr["ema50"]) else -1.0
        daily_rsi = round(float(dr["rsi"]), 1)
        daily_macd = "強気" if float(dr["macd_hist"]) > 0 else "弱気"
        result["daily"] = {
            "trend":    "上昇" if daily_dir > 0 else "下落",
            "score":    daily_dir,
            "rsi":      daily_rsi,
            "macd":     daily_macd,
            "ema50":    round(float(dr["ema50"]), 3),
        }
    except Exception as e:
        print(f"[DW/daily] {e}")

    try:
        # 週足 (EMA21)
        w = fetch_ohlcv(symbol, period="5y",  interval="1wk")
        w = add_indicators(w)
        wr = w.iloc[-1]
        weekly_dir = 1.0 if float(wr["Close"]) > float(wr["ema21"]) else -1.0
        weekly_rsi = round(float(wr["rsi"]), 1)
        result["weekly"] = {
            "trend":  "上昇" if weekly_dir > 0 else "下落",
            "score":  weekly_dir,
            "rsi":    weekly_rsi,
            "ema21":  round(float(wr["ema21"]), 3),
        }
    except Exception as e:
        print(f"[DW/weekly] {e}")

    # 大局スコア（日60% 週40%）
    d_s = result.get("daily",  {}).get("score", 0.0)
    w_s = result.get("weekly", {}).get("score", 0.0)
    overall = round(d_s * 0.6 + w_s * 0.4, 2)
    if overall > 0.2:
        bias = "📈 大局：買い優位（日足・週足上昇）"
    elif overall < -0.2:
        bias = "📉 大局：売り優位（日足・週足下落）"
    else:
        bias = "⚖️ 大局：中立（混在）"
    result["overall_score"] = overall
    result["bias"] = bias
    return result


# ═══════════════════════════════════════════════════════
#  ニュースセンチメント（yfinance news + Yahoo RSS）
# ═══════════════════════════════════════════════════════
def get_news_sentiment() -> dict:
    """
    USD/JPY関連ニュースを取得しキーワードベースでセンチメント判定。
    30分キャッシュ。
    """
    global _news_cache
    now = datetime.now()
    if _news_cache.get("ts") and (now - _news_cache["ts"]).total_seconds() < NEWS_TTL:
        return _news_cache["result"]

    headlines = []
    try:
        for sym in ["USDJPY=X", "JPY=X", "DX-Y.NYB"]:
            try:
                items = yf.Ticker(sym).news or []
                for it in items[:6]:
                    t = (it.get("title") or
                         (it.get("content") or {}).get("title") or "")
                    if t and t not in headlines:
                        headlines.append(t)
            except Exception:
                pass
    except Exception:
        pass

    # Yahoo Finance RSS フォールバック
    if len(headlines) < 3:
        try:
            import urllib.request, xml.etree.ElementTree as ET
            url = ("https://feeds.finance.yahoo.com/rss/2.0/headline"
                   "?s=USDJPY%3DX&region=US&lang=en-US")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                root = ET.parse(r).getroot()
                for item in root.iter("item"):
                    el = item.find("title")
                    if el is not None and el.text and el.text not in headlines:
                        headlines.append(el.text)
        except Exception:
            pass

    headlines = list(dict.fromkeys(headlines))[:10]

    # キーワードスコアリング
    BULL = ["hawkish", "rate hike", "strong dollar", "dollar gains", "usd rises",
            "fed hike", "yields rise", "risk on", "円安", "ドル高", "利上げ",
            "buy usd", "usd strength", "dollar rally", "positive"]
    BEAR = ["dovish", "rate cut", "weak dollar", "dollar drops", "usd falls",
            "fed cut", "yields fall", "risk off", "recession", "slowdown",
            "円高", "ドル安", "利下げ", "safe haven", "sell usd", "usd weakness"]
    score = 0.0
    for h in headlines:
        hl = h.lower()
        for kw in BULL:
            if kw in hl: score += 1.0
        for kw in BEAR:
            if kw in hl: score -= 1.0

    n = max(len(headlines), 1)
    score = max(-1.0, min(1.0, score / n))

    if   score >  0.15: sentiment = "📈 USD強気（円安方向）"
    elif score < -0.15: sentiment = "📉 USD弱気（円高方向）"
    else:               sentiment = "⚖️ 中立"

    result = {
        "score":     round(score, 3),
        "sentiment": sentiment,
        "headlines": headlines[:5],
        "count":     len(headlines),
    }
    _news_cache["result"] = result
    _news_cache["ts"]     = now
    return result


# ═══════════════════════════════════════════════════════
#  バックテスト（1H / 90日・勝率・期待値算出）
# ═══════════════════════════════════════════════════════
def run_backtest(symbol: str = "USDJPY=X",
                 lookback_days: int = 90) -> dict:
    """
    1H足を使ったバックテスト（実シグナルに近いロジック）。
    - rule_signal + candle_pattern + dow_theory の複合スコアでエントリー判定
    - EMA21トレンドフィルター（逆張り排除）
    - スプレッド3pip考慮
    - SL: 2.2×ATR, TP: 3.3×ATR（1H スイング設定）
    - 最大保有: 48時間
    6時間キャッシュ。
    """
    global _bt_cache
    now = datetime.now()
    if _bt_cache.get("ts") and (now - _bt_cache["ts"]).total_seconds() < BT_CACHE_TTL:
        return _bt_cache["result"]

    try:
        df = fetch_ohlcv(symbol, period=f"{lookback_days}d", interval="1h")
        df = add_indicators(df)
        df = df.dropna()
        if len(df) < 100:
            return {"error": "データ不足"}

        SPREAD   = 0.030   # 3 pips
        SL_MULT  = TF_SL_MULT["1h"]  # 2.2
        TP_MULT  = TF_TP_MULT["1h"]  # 3.3
        MAX_HOLD = 48      # bars (hours)
        # 正規化後の複合スコア閾値（compute_signalのTHRESHOLD=0.28に相当）
        MIN_COMBINED = 0.28

        trades = []
        for i in range(50, len(df) - MAX_HOLD - 1):
            row    = df.iloc[i]
            sub_df = df.iloc[:i + 1]

            # rule_signal（正規化: /8.0）
            rule_sc, _ = rule_signal(row)
            rule_n     = max(-1.0, min(1.0, rule_sc / 8.0))

            # ローソク足パターン（正規化: /4.0）
            candle_sc, _ = detect_candle_patterns(sub_df)
            candle_n     = max(-1.0, min(1.0, candle_sc / 4.0))

            # ダウ理論（正規化: /2.5）
            dow_sc, _  = dow_theory_analysis(sub_df)
            dow_n      = max(-1.0, min(1.0, dow_sc / 2.5))

            # EMA21トレンドフィルター（方向の一致確認）
            ema21_prev = float(df["ema21"].iloc[i - 5])
            ema21_cur  = float(row["ema21"])
            ema_trend  = 1.0 if ema21_cur > ema21_prev else -1.0

            # 複合スコア（実シグナルのウェイトに準じた簡易版）
            combined = rule_n * 0.50 + candle_n * 0.20 + dow_n * 0.30

            # EMAトレンドと逆方向はスキップ
            if (combined > 0 and ema_trend < 0) or (combined < 0 and ema_trend > 0):
                continue

            if abs(combined) < MIN_COMBINED:
                continue

            signal = "BUY" if combined > 0 else "SELL"
            entry  = float(row["Close"])
            atr    = float(row["atr"])
            if atr <= 0:
                continue

            # Apply spread
            if signal == "BUY":
                ep = entry + SPREAD / 2
                sl = ep - atr * SL_MULT
                tp = ep + atr * TP_MULT
            else:
                ep = entry - SPREAD / 2
                sl = ep + atr * SL_MULT
                tp = ep - atr * TP_MULT

            # Forward test
            outcome   = None
            bars_held = 0
            for j in range(1, MAX_HOLD + 1):
                fut = df.iloc[i + j]
                hi  = float(fut["High"])
                lo  = float(fut["Low"])
                if signal == "BUY":
                    if hi >= tp: outcome = "WIN";  bars_held = j; break
                    if lo <= sl: outcome = "LOSS"; bars_held = j; break
                else:
                    if lo <= tp: outcome = "WIN";  bars_held = j; break
                    if hi >= sl: outcome = "LOSS"; bars_held = j; break

            if outcome:
                trades.append({
                    "outcome":   outcome,
                    "bars_held": bars_held,
                    "rr_actual": round(TP_MULT / SL_MULT, 2),
                })

        def _calc_stats(trade_list):
            if len(trade_list) < 5:
                return None
            w = sum(1 for t in trade_list if t["outcome"] == "WIN")
            n = len(trade_list)
            wr = round(w / n * 100, 1)
            ev = round((wr / 100 * TP_MULT) - ((1 - wr / 100) * SL_MULT), 3)
            return {"trades": n, "win_rate": wr, "expected_value": ev}

        if len(trades) < 10:
            result = {"error": "サンプル数不足 (最低10トレード必要)",
                      "trades": len(trades)}
        else:
            wins  = sum(1 for t in trades if t["outcome"] == "WIN")
            total = len(trades)
            wr    = round(wins / total * 100, 1)
            avg_h = round(sum(t["bars_held"] for t in trades) / total, 1)
            rr    = round(TP_MULT / SL_MULT, 2)
            ev    = round((wr / 100 * TP_MULT) - ((1 - wr / 100) * SL_MULT), 3)

            if   ev > 0.3: verdict = "✅ 期待値プラス（推奨）"
            elif ev > 0:   verdict = "🟡 期待値わずかプラス（要注意）"
            else:          verdict = "❌ 期待値マイナス（不推奨）"

            # ── Walk-forward: 90日を3窓(各30日)に分割 ──────────────
            total_bars   = len(df)
            window_bars  = total_bars // 3
            wf_windows   = []
            for w_idx in range(3):
                w_start = 50 + w_idx * window_bars
                w_end   = w_start + window_bars
                label   = f"{lookback_days - (w_idx+1)*30}〜{lookback_days - w_idx*30}日前"
                w_trades = []
                for i in range(w_start, min(w_end, len(df) - MAX_HOLD - 1)):
                    row    = df.iloc[i]
                    sub_df = df.iloc[:i + 1]
                    rule_sc, _   = rule_signal(row)
                    rule_n       = max(-1.0, min(1.0, rule_sc / 8.0))
                    candle_sc, _ = detect_candle_patterns(sub_df)
                    candle_n     = max(-1.0, min(1.0, candle_sc / 4.0))
                    dow_sc, _    = dow_theory_analysis(sub_df)
                    dow_n        = max(-1.0, min(1.0, dow_sc / 2.5))
                    ema21_prev   = float(df["ema21"].iloc[i - 5])
                    ema21_cur    = float(row["ema21"])
                    ema_trend    = 1.0 if ema21_cur > ema21_prev else -1.0
                    combined     = rule_n * 0.50 + candle_n * 0.20 + dow_n * 0.30
                    if (combined > 0 and ema_trend < 0) or (combined < 0 and ema_trend > 0):
                        continue
                    if abs(combined) < MIN_COMBINED:
                        continue
                    sig   = "BUY" if combined > 0 else "SELL"
                    ep    = float(row["Close"])
                    atr_v = float(row["atr"])
                    if atr_v <= 0:
                        continue
                    ep    = ep + SPREAD/2 if sig == "BUY" else ep - SPREAD/2
                    sl_v  = ep - atr_v * SL_MULT if sig == "BUY" else ep + atr_v * SL_MULT
                    tp_v  = ep + atr_v * TP_MULT if sig == "BUY" else ep - atr_v * TP_MULT
                    for j in range(1, MAX_HOLD + 1):
                        if i + j >= len(df):
                            break
                        fut = df.iloc[i + j]
                        hi, lo = float(fut["High"]), float(fut["Low"])
                        if sig == "BUY":
                            if hi >= tp_v: w_trades.append({"outcome":"WIN","bars_held":j,"rr_actual":rr}); break
                            if lo <= sl_v: w_trades.append({"outcome":"LOSS","bars_held":j,"rr_actual":rr}); break
                        else:
                            if lo <= tp_v: w_trades.append({"outcome":"WIN","bars_held":j,"rr_actual":rr}); break
                            if hi >= sl_v: w_trades.append({"outcome":"LOSS","bars_held":j,"rr_actual":rr}); break
                stats = _calc_stats(w_trades)
                if stats:
                    wf_windows.append({"label": label, **stats})

            profitable_windows = sum(1 for w in wf_windows if w.get("expected_value", -1) > 0)
            consistency = f"{profitable_windows}/{len(wf_windows)} 窓でプラス期待値"

            result = {
                "win_rate":        wr,
                "trades":          total,
                "wins":            wins,
                "losses":          total - wins,
                "rr":              rr,
                "avg_hold_hours":  avg_h,
                "expected_value":  ev,
                "verdict":         verdict,
                "period":          f"過去{lookback_days}日",
                "sl_mult":         SL_MULT,
                "tp_mult":         TP_MULT,
                "walk_forward":    wf_windows,
                "consistency":     consistency,
            }

        _bt_cache["result"] = result
        _bt_cache["ts"]     = now
        return result
    except Exception as e:
        import traceback
        print(f"[BACKTEST] {traceback.format_exc()}")
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════
#  大口参入マーカー生成（チャート描画用）
# ═══════════════════════════════════════════════════════
def detect_large_player_markers(df: pd.DataFrame, vol_window: int = 20,
                                spike_thresh: float = 2.0) -> list:
    """
    USD/JPYチャート上に大口参入バブルマーカーを生成する。
    出来高が直近vol_window本平均のspike_thresh倍以上 → 大口参入と判定。
    Returns list of {time, position, color, shape, text}
    """
    markers = []
    vol = df["Volume"].fillna(0).astype(float)
    if vol.sum() == 0:
        # 出来高データなし → 価格変動でVOL代用（ATRスパイク）
        atr_mean = df["atr"].rolling(vol_window).mean()
        proxy    = df["atr"] / atr_mean.replace(0, np.nan)
        vol      = proxy.fillna(1.0)
        spike_thresh = 1.8  # ATR代用の場合閾値を下げる

    avg_vol = vol.rolling(vol_window).mean()

    for i in range(vol_window, len(df)):
        row    = df.iloc[i]
        cur_v  = float(vol.iloc[i])
        avg_v  = float(avg_vol.iloc[i])
        if avg_v <= 0:
            continue
        ratio = cur_v / avg_v
        if ratio < spike_thresh:
            continue

        ts = df.index[i]
        t  = int(ts.timestamp()) if hasattr(ts, "timestamp") else int(ts)

        # 方向判定（直前3本との比較）
        prev_close = float(df["Close"].iloc[i - 3]) if i >= 3 else float(df["Close"].iloc[0])
        cur_close  = float(row["Close"])
        is_buy     = cur_close > prev_close

        label = f"🏦 {ratio:.1f}x"
        markers.append({
            "time":     t,
            "position": "belowBar" if is_buy  else "aboveBar",
            "color":    "#3fb950"  if is_buy  else "#f85149",
            "shape":    "arrowUp"  if is_buy  else "arrowDown",
            "text":     label,
        })

    # 直近50本の中で強いスパイクのみ（過去100本を表示上限）
    return markers[-100:]


# ═══════════════════════════════════════════════════════
#  Flask routes
# ═══════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/signal")
def api_signal():
    tf  = request.args.get("tf", "1m")
    cfg = TF_CFG.get(tf, TF_CFG["1m"])
    try:
        df = fetch_ohlcv("USDJPY=X", period=cfg["period"], interval=cfg["interval"])
        if cfg["resample"]: df = resample_df(df, cfg["resample"])
        df = add_indicators(df)
        sr = find_sr_levels(df, window=cfg["sr_w"], tolerance_pct=cfg["sr_tol"])
        return jsonify(compute_signal(df, tf, sr))
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/chart")
def api_chart():
    tf  = request.args.get("tf", "1m")
    cfg = TF_CFG.get(tf, TF_CFG["1m"])
    try:
        df = fetch_ohlcv("USDJPY=X", period=cfg["period"], interval=cfg["interval"])
        if cfg["resample"]: df = resample_df(df, cfg["resample"])
        df       = add_indicators(df)
        df_chart = df.tail(400)
        sr       = find_sr_levels(df, window=cfg["sr_w"], tolerance_pct=cfg["sr_tol"])
        ch       = find_parallel_channel(df_chart, window=cfg["sr_w"], lookback=cfg["ch_lb"])

        candles = []
        for ts, row in df_chart.iterrows():
            t = int(ts.timestamp()) if hasattr(ts, "timestamp") else int(ts)
            candles.append({
                "time": t,
                "open":  round(float(row["Open"]),  3),
                "high":  round(float(row["High"]),  3),
                "low":   round(float(row["Low"]),   3),
                "close": round(float(row["Close"]), 3),
                "ema9":  round(float(row["ema9"]),  3),
                "ema21": round(float(row["ema21"]), 3),
                "ema50": round(float(row["ema50"]), 3),
                "bb_upper": round(float(row["bb_upper"]),3),
                "bb_mid":   round(float(row["bb_mid"]),  3),
                "bb_lower": round(float(row["bb_lower"]),3),
                "rsi":       round(float(row["rsi"]),        1),
                "macd":      round(float(row["macd"]),       5),
                "macd_sig":  round(float(row["macd_sig"]),   5),
                "macd_hist": round(float(row["macd_hist"]),  5),
            })
        markers = detect_large_player_markers(df_chart)
        return jsonify({"candles": candles, "sr_levels": sr, "channel": ch,
                        "lp_markers": markers})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/backtest")
def api_backtest():
    """バックテスト結果（6時間キャッシュ）"""
    try:
        result = run_backtest("USDJPY=X", lookback_days=90)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/news")
def api_news():
    """最新ニュース・センチメント（30分キャッシュ）"""
    try:
        result = get_news_sentiment()
        dw     = get_daily_weekly_direction("USDJPY=X")
        return jsonify({"news": result, "daily_weekly": dw})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── TwelveData リアルタイム価格キャッシュ ──────────────────────
_price_cache: dict = {}
PRICE_TTL = 8  # 8秒キャッシュ（Basic枠: 8req/min）

@app.route("/api/price")
def api_price():
    """
    TwelveDataからUSD/JPYリアルタイム価格を取得。
    TWELVEDATA_API_KEY 環境変数が未設定の場合はyfinanceにフォールバック。
    """
    global _price_cache
    now = datetime.now()
    if _price_cache.get("ts") and (now - _price_cache["ts"]).total_seconds() < PRICE_TTL:
        return jsonify(_price_cache["data"])

    api_key = os.environ.get("TWELVEDATA_API_KEY", "")

    if api_key:
        try:
            import urllib.request, json as _json
            url = (f"https://api.twelvedata.com/quote"
                   f"?symbol=USD/JPY&apikey={api_key}&dp=3")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                q = _json.load(r)
            if q.get("status") == "error":
                raise ValueError(q.get("message", "TwelveData error"))
            data = {
                "price":       float(q["close"]),
                "open":        float(q["open"]),
                "high":        float(q["high"]),
                "low":         float(q["low"]),
                "prev_close":  float(q["previous_close"]),
                "change":      round(float(q["close"]) - float(q["previous_close"]), 3),
                "change_pct":  round((float(q["close"]) - float(q["previous_close"]))
                                     / float(q["previous_close"]) * 100, 4),
                "datetime":    q.get("datetime", ""),
                "source":      "twelvedata",
            }
            _price_cache = {"data": data, "ts": now}
            return jsonify(data)
        except Exception as e:
            print(f"[PRICE/TwelveData] {e}")

    # フォールバック: yfinance最新足
    try:
        df = fetch_ohlcv("USDJPY=X", period="1d", interval="1m")
        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(last["Close"])
        prev_price = float(prev["Close"])
        data = {
            "price":      round(price, 3),
            "open":       round(float(last["Open"]), 3),
            "high":       round(float(last["High"]), 3),
            "low":        round(float(last["Low"]),  3),
            "prev_close": round(prev_price, 3),
            "change":     round(price - prev_price, 3),
            "change_pct": round((price - prev_price) / prev_price * 100, 4),
            "datetime":   str(last.name),
            "source":     "yfinance",
        }
        _price_cache = {"data": data, "ts": now}
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 55)
    print("  FX AI Trader v5  —  USD/JPY Swing Day Trade")
    print(f"  http://localhost:{port}")
    print("=" * 55)
    app.run(debug=False, port=port, host="0.0.0.0")
