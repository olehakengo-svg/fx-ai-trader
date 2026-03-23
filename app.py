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
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

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
_model_cache: dict = {}
_data_cache:  dict = {}  # (symbol,interval,period) -> (df, timestamp)
CACHE_TTL = 300          # 5 min data cache


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
def calc_sl_tp_v3(entry: float, signal: str, atr: float, sr_levels: list):
    """SL/TP calculation snapped to nearest S/R level."""
    if signal == "BUY":
        raw_sl = entry - atr * 1.5
        raw_tp = entry + atr * 2.5
        sl_candidates = [l for l in sr_levels if l < entry - atr * 0.3]
        tp_candidates = [l for l in sr_levels if l > entry + atr * 0.5]
        sl = max(sl_candidates) - atr * 0.15 if sl_candidates else raw_sl
        tp = min(tp_candidates) - atr * 0.10 if tp_candidates else raw_tp
    else:  # SELL
        raw_sl = entry + atr * 1.5
        raw_tp = entry - atr * 2.5
        sl_candidates = [l for l in sr_levels if l > entry + atr * 0.3]
        tp_candidates = [l for l in sr_levels if l < entry - atr * 0.5]
        sl = min(sl_candidates) + atr * 0.15 if sl_candidates else raw_sl
        tp = max(tp_candidates) + atr * 0.10 if tp_candidates else raw_tp

    # Ensure minimum RR of 1.2
    if abs(tp - entry) < abs(sl - entry) * 1.2:
        if signal == "BUY":
            tp = entry + abs(sl - entry) * 1.5
        else:
            tp = entry - abs(sl - entry) * 1.5

    return round(sl, 3), round(tp, 3)


# ═══════════════════════════════════════════════════════
#  ML  (same training approach, cached per TF)
# ═══════════════════════════════════════════════════════
def make_features(df):
    f = pd.DataFrame(index=df.index)
    f["ema9_r"]   = df["Close"]/df["ema9"]  - 1
    f["ema21_r"]  = df["Close"]/df["ema21"] - 1
    f["ema50_r"]  = df["Close"]/df["ema50"] - 1
    f["e9_21"]    = df["ema9"] /df["ema21"] - 1
    f["e21_50"]   = df["ema21"]/df["ema50"] - 1
    f["rsi_n"]    = df["rsi"] / 100
    f["rsi_ob"]   = (df["rsi"] > 70).astype(float)
    f["rsi_os"]   = (df["rsi"] < 30).astype(float)
    f["macd_n"]   = df["macd_hist"] / df["atr"].replace(0, np.nan)
    f["bb_pb"]    = df["bb_pband"]
    f["ret1"]     = df["Close"].pct_change(1)
    f["ret5"]     = df["Close"].pct_change(5)
    f["ret10"]    = df["Close"].pct_change(10)
    return f.dropna()


def get_cache(tf):
    if tf not in _model_cache:
        _model_cache[tf] = {"model": None, "scaler": None, "trained_at": None}
    return _model_cache[tf]


def train_model_if_needed(tf="1m"):
    cache = get_cache(tf)
    now   = datetime.now()
    if cache["trained_at"] and (now - cache["trained_at"]).total_seconds() < 3600:
        return
    try:
        df_t   = fetch_ohlcv("USDJPY=X", period="60d", interval="1h")
        df_t   = add_indicators(df_t)
        feats  = make_features(df_t)
        labels = (df_t["Close"].shift(-1) > df_t["Close"]).astype(int)
        idx    = feats.index.intersection(labels.dropna().index)
        X, y   = feats.loc[idx], labels.loc[idx]
        if len(X) < 100: return
        sc  = StandardScaler()
        Xs  = sc.fit_transform(X)
        clf = RandomForestClassifier(
            n_estimators=200, max_depth=6,
            min_samples_leaf=5, random_state=42, n_jobs=-1)
        clf.fit(Xs, y)
        cache["model"], cache["scaler"], cache["trained_at"] = clf, sc, now
        print(f"[ML] {tf} trained — {len(X)} samples")
    except Exception as e:
        print(f"[ML] Training error: {e}")


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

    # ── ML ─────────────────────────────────────────
    ml_prob = 0.5
    train_model_if_needed(tf)
    cache = get_cache(tf)
    if cache["model"] is not None:
        try:
            feats = make_features(df)
            if len(feats):
                xs = cache["scaler"].transform(feats.iloc[-1:].values)
                ml_prob = float(cache["model"].predict_proba(xs)[0][1])
        except Exception:
            pass

    # ── Normalize each component to [-1, +1] ───────
    rule_n   = max(-1.0, min(1.0, rule_sc   / 8.0))
    candle_n = max(-1.0, min(1.0, candle_sc / 4.0))
    dow_n    = max(-1.0, min(1.0, dow_sc    / 2.5))
    vol_n    = max(-1.0, min(1.0, vol_sc    / 2.0))
    div_n    = max(-1.0, min(1.0, div_sc    / 2.5))
    mtf_n    = max(-1.0, min(1.0, mtf_sc    / 3.0))
    ml_adj   = (ml_prob - 0.5) * 2.0

    # ── Weighted combination ────────────────────────
    #  weight: rules 25%, candle 12%, dow 15%, vol 8%,
    #          div 8%, mtf 17%, ml 15%
    combined = (
        rule_n   * 0.25 +
        candle_n * 0.12 +
        dow_n    * 0.15 +
        vol_n    * 0.08 +
        div_n    * 0.08 +
        mtf_n    * 0.17 +
        ml_adj   * 0.15
    )

    # ⑦ Session multiplier
    combined *= session["mult"]

    # ⑧ Strict threshold
    THRESHOLD = 0.28

    if   combined >  THRESHOLD: signal, conf = "BUY",  int(min(95, 50 + combined * 55))
    elif combined < -THRESHOLD: signal, conf = "SELL", int(min(95, 50 + abs(combined) * 55))
    else:                       signal, conf = "WAIT", int(max(25, 50 - abs(combined) * 40))

    # ⑥ S/R-snapped SL/TP
    act_signal = signal if signal != "WAIT" else "BUY"
    sl, tp = calc_sl_tp_v3(entry, act_signal, atr, sr_levels)
    rr     = round(abs(tp - entry) / max(abs(sl - entry), 1e-6), 2)

    # Assemble reasons
    all_reasons = (
        rule_rsns +
        ([dow_rsn] if dow_rsn and "不足" not in dow_rsn else []) +
        candle_rsns +
        vol_rsns +
        div_rsns +
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
        "session":    session,
        "mtf":        mtf_details,
        "dow_trend":  dow_rsn,
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
        "ml_prob":  round(ml_prob * 100, 1),
        "score_detail": {
            "rule":      round(rule_n,   3),
            "candle":    round(candle_n, 3),
            "dow":       round(dow_n,    3),
            "volume":    round(vol_n,    3),
            "divergence":round(div_n,    3),
            "mtf":       round(mtf_n,    3),
            "ml":        round(ml_adj/2, 3),
            "combined":  round(combined, 3),
        },
    }


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
        return jsonify({"candles": candles, "sr_levels": sr, "channel": ch})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 55)
    print("  FX AI Trader v3  —  USD/JPY Multi-TF Dashboard")
    print(f"  http://localhost:{port}")
    print("=" * 55)
    app.run(debug=False, port=port, host="0.0.0.0")
