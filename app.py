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
from ta.momentum import RSIIndicator, StochasticOscillator
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


# TF別キャッシュTTL
_TF_CACHE_TTL = {
    "1m": 10, "5m": 15, "15m": 45, "30m": 90,
    "1h": 180, "4h": 300, "1d": 600, "1wk": 1800, "1mo": 3600,
}

# TwelveData対応: interval変換マップ (yfinance → TwelveData)
_TD_INTERVAL_MAP = {
    "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1h", "1d": "1day", "1wk": "1week", "1mo": "1month",
}
# TwelveData対応: symbol変換マップ (yfinance → TwelveData)
_TD_SYMBOL_MAP = {
    "USDJPY=X": "USD/JPY",
    "JPY=X":    "USD/JPY",
}
# TwelveDataを優先使用するinterval (USD/JPYのみ)
_TD_INTERVALS = {"1m", "5m", "15m", "30m", "1h"}
# TwelveDataでリクエストするバー数
_TD_OUTPUTSIZE = {
    "1m": 500, "5m": 600, "15m": 600, "30m": 400, "1h": 500,
}

# データソース記録 (最後に使ったソース)
_last_data_source: dict = {}


def fetch_ohlcv_twelvedata(symbol: str, interval: str) -> pd.DataFrame:
    """
    TwelveData time_series APIからOHLCVデータを取得しDataFrameで返す。
    TWELVEDATA_API_KEY 環境変数が必要。
    """
    import urllib.request as _ur, json as _js
    api_key = os.environ.get("TWELVEDATA_API_KEY", "")
    if not api_key:
        raise ValueError("TWELVEDATA_API_KEY not set")

    td_sym   = _TD_SYMBOL_MAP.get(symbol)
    if not td_sym:
        raise ValueError(f"Symbol {symbol} not in TwelveData map")

    td_iv    = _TD_INTERVAL_MAP.get(interval)
    if not td_iv:
        raise ValueError(f"Interval {interval} not in TwelveData map")

    size     = _TD_OUTPUTSIZE.get(interval, 500)
    url      = (f"https://api.twelvedata.com/time_series"
                f"?symbol={td_sym}&interval={td_iv}"
                f"&outputsize={size}&apikey={api_key}&dp=5&timezone=UTC&format=JSON")

    req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with _ur.urlopen(req, timeout=10) as r:
        data = _js.load(r)

    if data.get("status") == "error":
        raise ValueError(f"TwelveData: {data.get('message','unknown error')}")

    values = data.get("values", [])
    if not values:
        raise ValueError("TwelveData: empty values")

    # values はnewest-first → reverse で古い順に並べ直す
    values = list(reversed(values))
    rows = [{
        "Open":   float(v["open"]),
        "High":   float(v["high"]),
        "Low":    float(v["low"]),
        "Close":  float(v["close"]),
        "Volume": float(v.get("volume", 0)),
    } for v in values]
    idx = pd.DatetimeIndex(
        [pd.Timestamp(v["datetime"], tz="UTC") for v in values]
    )
    return pd.DataFrame(rows, index=idx).dropna()


def _rt_patch(df: pd.DataFrame, symbol: str, interval: str) -> pd.DataFrame:
    """
    価格キャッシュ(_price_cache)が新鮮なら、最終足のClose/High/Lowをリアルタイム更新。
    OHLCVを再取得せずに現在足を常に最新化するため、足型ズレを大幅に削減する。
    USD/JPY の 1m/5m のみ対象。
    """
    if interval not in ("1m", "5m") or symbol not in _TD_SYMBOL_MAP:
        return df
    pc = _price_cache  # グローバル参照（モジュール初期化後は常に存在）
    if not pc.get("ts"):
        return df
    age = (datetime.now() - pc["ts"]).total_seconds()
    if age > 10:
        return df
    price = float(pc["data"]["price"])
    last  = df.index[-1]
    df.at[last, "Close"] = price
    df.at[last, "High"]  = max(float(df.at[last, "High"]), price)
    df.at[last, "Low"]   = min(float(df.at[last, "Low"]),  price)
    return df


def fetch_ohlcv(symbol="USDJPY=X", period="5d", interval="1m") -> pd.DataFrame:
    key = (symbol, interval, period)
    now = datetime.now()
    ttl = _TF_CACHE_TTL.get(interval, CACHE_TTL)
    if key in _data_cache:
        cached_df, ts = _data_cache[key]
        if (now - ts).total_seconds() < ttl:
            return _rt_patch(cached_df.copy(), symbol, interval)

    df = None
    # ── TwelveData優先: USD/JPY の短期TFのみ ──
    if (os.environ.get("TWELVEDATA_API_KEY") and
            symbol in _TD_SYMBOL_MAP and
            interval in _TD_INTERVALS):
        try:
            df = fetch_ohlcv_twelvedata(symbol, interval)
            _last_data_source[interval] = "twelvedata"
            print(f"[TD/{interval}] {len(df)}本取得")
        except Exception as e:
            print(f"[TD/{interval}] {e} → yfinanceにフォールバック")
            df = None

    # ── フォールバック: yfinance ──
    if df is None:
        df = _fetch_raw(symbol, period, interval)
        _last_data_source[interval] = "yfinance"

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
    # スキャルプ用高速指標
    df["rsi5"]      = RSIIndicator(c, window=5).rsi()
    df["atr7"]      = AverageTrueRange(h, l, c, window=7).average_true_range()
    stoch = StochasticOscillator(h, l, c, window=5, smooth_window=3)
    df["stoch_k"]   = stoch.stoch()
    df["stoch_d"]   = stoch.stoch_signal()
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
        is_spike = bool(ratio >= 2.0)
        return float(round(force, 4)), float(round(ratio, 2)), is_spike
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
        jpy = fetch_ohlcv("6J=F", period="120d", interval="1d")
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
        dxy = fetch_ohlcv("DX-Y.NYB", period="120d", interval="1d")
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
    日本10年国債利回りを複数ソースから取得。
    ①FRED CSV → ②stooq.com → ③前回キャッシュ or 1.5%
    """
    global _jp10y_cache
    now = datetime.now()
    if _jp10y_cache.get("ts"):
        ttl = 3600 if _jp10y_cache.get("is_fallback") else JP10Y_TTL
        if (now - _jp10y_cache["ts"]).total_seconds() < ttl:
            return _jp10y_cache["value"]

    import urllib.request as _ur, csv, io

    # ── ① FRED ──────────────────────────────────────────────────
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IRLTLT01JPM156N"
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=5) as r:
            rows = list(csv.reader(io.TextIOWrapper(r)))
        for row in reversed(rows):
            if len(row) == 2 and row[1] not in ("", "."):
                value = float(row[1])
                _jp10y_cache = {"value": value, "ts": now}
                print(f"[JP10Y] FRED: {value}%")
                return value
    except Exception as e:
        print(f"[JP10Y] FRED失敗: {e}")

    # ── ② stooq.com（日次データ）────────────────────────────────
    try:
        url = "https://stooq.com/q/d/l/?s=10yjpy.b&i=d"
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=5) as r:
            rows = list(csv.reader(io.TextIOWrapper(r)))
        # フォーマット: Date,Open,High,Low,Close,Volume
        for row in reversed(rows[1:]):
            if len(row) >= 5 and row[4] not in ("", "null", "N/D"):
                value = float(row[4])
                _jp10y_cache = {"value": value, "ts": now}
                print(f"[JP10Y] stooq: {value}%")
                return value
    except Exception as e:
        print(f"[JP10Y] stooq失敗: {e}")

    # ── ③ フォールバック: 前回キャッシュ or 1.5%（1時間キャッシュして再試行を抑制）
    fallback = _jp10y_cache.get("value", 1.5)
    _jp10y_cache = {"value": fallback, "ts": now, "is_fallback": True}
    print(f"[JP10Y] フォールバック: {fallback}%（1h後に再試行）")
    return fallback


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
#  A: COT Report — CFTC JPY先物ポジション
# ═══════════════════════════════════════════════════════
_cot_cache: dict = {}
COT_TTL = 86400 * 7  # 1週間キャッシュ（COTは週次データ）


def _cot_make_result(nc_long, nc_short, cm_long, cm_short, report_date, source):
    """COT数値からスコアとdetailを生成するヘルパー。"""
    nc_net  = nc_long - nc_short   # 正=円買い
    cm_net  = cm_long - cm_short
    nc_norm = max(-1.0, min(1.0,  nc_net / 80000.0))
    cm_norm = max(-1.0, min(1.0, -cm_net / 80000.0))
    score   = -(nc_norm * 0.6 + cm_norm * 0.4)
    detail  = {
        "report_date": report_date,
        "nc_long": nc_long, "nc_short": nc_short, "nc_net": nc_net,
        "cm_long": cm_long, "cm_short": cm_short, "cm_net": cm_net,
        "source": source,
    }
    if   nc_net >  30000: detail["signal"] = "🔴 投機筋 大口円買い（USD/JPY 下落圧力）"
    elif nc_net < -30000: detail["signal"] = "🟢 投機筋 大口円売り（USD/JPY 上昇圧力）"
    elif nc_net >  10000: detail["signal"] = "🟠 投機筋 円買い優位"
    elif nc_net < -10000: detail["signal"] = "🟡 投機筋 円売り優位"
    else:                 detail["signal"] = "⚪ 投機筋 ポジション中立"
    return round(max(-1.0, min(1.0, score)), 4), detail


def fetch_cot_data() -> tuple:
    """
    CFTC COT（Commitments of Traders）レポートから JPY先物ポジション取得。
    方法①: CFTC OData API  (新API、不安定なことあり)
    方法②: CFTC deafut.txt (レガシーテキストファイル、より安定)
    Non-commercial（投機筋）ネットポジションでUSD/JPY方向を判断。
    Returns: (score [-1,+1], detail dict)
    """
    global _cot_cache
    now = datetime.now()
    if _cot_cache.get("ts") and (now - _cot_cache["ts"]).total_seconds() < COT_TTL:
        return _cot_cache.get("score", 0.0), _cot_cache.get("detail", {})

    import urllib.request as _ur, json as _js, urllib.parse as _up, csv, io

    mkt = "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"

    # ── 方法①: CFTC OData API ──────────────────────────────────
    endpoints = [
        "https://publicreporting.cftc.gov/api/odata/v1/CorrectionsCommitmentsOfTraders",
        "https://publicreporting.cftc.gov/api/odata/v1/CommitmentsOfTraders",
    ]
    sel = ("Report_Date_as_YYYY_MM_DD,Noncomm_Positions_Long_All,"
           "Noncomm_Positions_Short_All,Comm_Positions_Long_All,"
           "Comm_Positions_Short_All")
    for endpoint in endpoints:
        try:
            filter_str = f"Market_and_Exchange_Names eq '{mkt}'"
            url = (f"{endpoint}?$filter={_up.quote(filter_str)}"
                   f"&$orderby=Report_Date_as_YYYY_MM_DD%20desc"
                   f"&$top=5&$select={sel}")
            req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                             "Accept": "application/json"})
            with _ur.urlopen(req, timeout=10) as r:
                data = _js.load(r)
            records = data.get("value", [])
            if not records:
                continue
            rec      = records[0]
            nc_long  = int(rec.get("Noncomm_Positions_Long_All",  0) or 0)
            nc_short = int(rec.get("Noncomm_Positions_Short_All", 0) or 0)
            cm_long  = int(rec.get("Comm_Positions_Long_All",     0) or 0)
            cm_short = int(rec.get("Comm_Positions_Short_All",    0) or 0)
            score, detail = _cot_make_result(
                nc_long, nc_short, cm_long, cm_short,
                rec.get("Report_Date_as_YYYY_MM_DD", ""), "CFTC OData")
            _cot_cache = {"score": score, "detail": detail, "ts": now}
            print(f"[COT/OData] nc_net={nc_long-nc_short:+d} score={score}")
            return score, detail
        except Exception as e:
            print(f"[COT/{endpoint.split('/')[-1]}] {e}")
            continue

    # ── 方法②: CFTC Legacy Text File (deafut.txt) ──────────────
    # CFTCが毎週金曜に公開するレガシーテキスト形式（カンマ区切り・引用符付き）
    try:
        url = "https://www.cftc.gov/dea/newcot/deafut.txt"
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=15) as r:
            content = r.read().decode("utf-8", errors="replace")

        reader    = csv.reader(io.StringIO(content))
        header    = [c.strip().strip('"').lower() for c in next(reader)]

        # CFTC Legacy Futures Only 固定カラム位置（0-based）
        # col0=Market_and_Exchange_Names, col1=As_of_Date_In_Form_YYMMDD,
        # col7=Open_Interest_All, col8=NonComm_Positions_Long_All,
        # col9=NonComm_Positions_Short_All, col10=NonComm_Postions_Spread_All,
        # col11=Comm_Positions_Long_All, col12=Comm_Positions_Short_All
        nc_long_i, nc_short_i = 8, 9
        cm_long_i, cm_short_i = 11, 12
        date_i = 1

        def _int(row, idx):
            if idx is None or idx >= len(row):
                return 0
            return int(row[idx].replace(",", "").strip() or "0")

        for row in reader:
            if not row:
                continue
            name = row[0].strip().strip('"')
            if "JAPANESE YEN" not in name.upper():
                continue
            nc_long  = _int(row, nc_long_i)
            nc_short = _int(row, nc_short_i)
            cm_long  = _int(row, cm_long_i)
            cm_short = _int(row, cm_short_i)
            rdate    = row[date_i].strip().strip('"') if date_i else ""
            score, detail = _cot_make_result(
                nc_long, nc_short, cm_long, cm_short, rdate, "CFTC deafut.txt")
            _cot_cache = {"score": score, "detail": detail, "ts": now}
            print(f"[COT/deafut] {rdate} nc_net={nc_long-nc_short:+d} score={score}")
            return score, detail

        print("[COT/deafut] JAPANESE YEN not found in file")
    except Exception as e:
        print(f"[COT/deafut] {e}")

    detail = {"error": "COT取得失敗", "signal": "⚪ COTデータ取得不可（中立）"}
    return 0.0, detail


# ═══════════════════════════════════════════════════════
#  B: Order Block Detection  (SMC オーダーブロック)
# ═══════════════════════════════════════════════════════
def detect_order_blocks(df: pd.DataFrame, atr_mult: float = 1.5,
                        lookback: int = 80) -> tuple:
    """
    SMC Order Block:
    - Bull OB: 強気インパルス直前の最後の陰線 → サポートゾーン
    - Bear OB: 弱気インパルス直前の最後の陽線 → レジスタンスゾーン
    Returns: (score [-1,+1], list of OB zone dicts)
    """
    if len(df) < 20:
        return 0.0, []

    sub      = df.tail(lookback)
    atr_mean = float(sub["atr"].mean()) if float(sub["atr"].mean()) > 0 else 1e-4
    closes   = sub["Close"].values
    opens    = sub["Open"].values
    highs    = sub["High"].values
    lows     = sub["Low"].values
    atrs     = sub["atr"].values
    tidx     = sub.index
    n        = len(sub)
    ob_zones = []

    for i in range(1, n - 2):
        imp_i    = i + 1
        imp_body = abs(closes[imp_i] - opens[imp_i])
        imp_atr  = atrs[imp_i] if atrs[imp_i] > 0 else atr_mean
        if imp_body < atr_mult * imp_atr:
            continue  # インパルスキャンドル条件を満たさない

        ts = tidx[i]
        t  = int(ts.timestamp()) if hasattr(ts, "timestamp") else int(ts)

        if closes[imp_i] > opens[imp_i]:    # 強気インパルス
            if closes[i] < opens[i]:         # 直前陰線 → Bull OB
                ob_zones.append({"type": "bull",
                    "high": round(float(highs[i]), 3),
                    "low":  round(float(lows[i]),  3),
                    "time": t, "label": "🟩 Bull OB"})
        elif closes[imp_i] < opens[imp_i]:  # 弱気インパルス
            if closes[i] > opens[i]:         # 直前陽線 → Bear OB
                ob_zones.append({"type": "bear",
                    "high": round(float(highs[i]), 3),
                    "low":  round(float(lows[i]),  3),
                    "time": t, "label": "🟥 Bear OB"})

    ob_zones = ob_zones[-10:]   # 最新10件
    if not ob_zones:
        return 0.0, []

    current_price = float(df["Close"].iloc[-1])
    current_atr   = float(df["atr"].iloc[-1])
    score = 0.0
    for ob in ob_zones[-5:]:
        tol = current_atr * 0.5
        if ob["type"] == "bull" and ob["low"] - tol <= current_price <= ob["high"] + tol:
            score += 1.5
        elif ob["type"] == "bear" and ob["low"] - tol <= current_price <= ob["high"] + tol:
            score -= 1.5

    return round(max(-1.0, min(1.0, score / 3.0)), 4), ob_zones


# ═══════════════════════════════════════════════════════
#  C: Fake Breakout / Stop Hunt Filter
# ═══════════════════════════════════════════════════════
def detect_fake_breakout(df: pd.DataFrame, sr_levels: list,
                         lookback_candles: int = 8) -> tuple:
    """
    フェイクブレイクアウト（逆指値狩り）を検出。
    ウィックがS/Rを超えたが実体が戻る → 逆方向への期待。
    Returns: (score [-1,+1], list of signal strings)
    """
    if len(df) < 5 or not sr_levels:
        return 0.0, []

    recent  = df.tail(lookback_candles)
    atr_val = float(df["atr"].iloc[-1])
    score   = 0.0
    signals = []
    seen    = set()

    for idx_i in range(len(recent)):
        row = recent.iloc[idx_i]
        h, l = float(row["High"]), float(row["Low"])
        o, c = float(row["Open"]), float(row["Close"])
        body_high = max(o, c)
        body_low  = min(o, c)
        weight = 1.5 if idx_i == len(recent) - 1 else 0.6

        for level in sr_levels:
            tol   = atr_val * 0.4
            key_b = (round(level, 2), "bull")
            key_r = (round(level, 2), "bear")

            # Bull Fake Break: ウィックが level 以下まで伸び、実体は level 上で引け
            if (l < level - tol and body_low > level - tol * 3
                    and c > level and key_b not in seen):
                seen.add(key_b)
                score += weight
                signals.append(f"🎣 強気フェイクブレイク (S:{level:.3f}) 逆指値狩り→反発期待")

            # Bear Fake Break: ウィックが level 以上まで伸び、実体は level 下で引け
            elif (h > level + tol and body_high < level + tol * 3
                    and c < level and key_r not in seen):
                seen.add(key_r)
                score -= weight
                signals.append(f"🎣 弱気フェイクブレイク (R:{level:.3f}) 逆指値狩り→下落期待")

    return round(max(-1.0, min(1.0, score / 3.0)), 4), signals[:4]


# ═══════════════════════════════════════════════════════
#  D: Liquidity Map — Equal Highs / Equal Lows
# ═══════════════════════════════════════════════════════
def detect_liquidity_zones(df: pd.DataFrame, window: int = 5,
                           tolerance_pct: float = 0.0012,
                           lookback: int = 120) -> list:
    """
    均等高値（EQH）・均等安値（EQL）を検出してリクイディティゾーンを生成。
    大口はこれらの逆指値集中帯を刈り取ってから反転する傾向。
    Returns: list of {type, price, strength, time, label}
    """
    if len(df) < window * 4:
        return []

    sub  = df.tail(lookback)
    H    = sub["High"].values
    L    = sub["Low"].values
    n    = len(sub)
    tidx = sub.index

    swing_highs: list = []
    swing_lows:  list = []
    for i in range(window, n - window):
        if H[i] == H[max(0, i - window): i + window + 1].max():
            swing_highs.append((i, float(H[i])))
        if L[i] == L[max(0, i - window): i + window + 1].min():
            swing_lows.append((i, float(L[i])))

    def cluster_pts(pts):
        if len(pts) < 2:
            return []
        sorted_p = sorted(pts, key=lambda x: x[1])
        clusters, cur = [], [sorted_p[0]]
        for pt in sorted_p[1:]:
            ref = cur[0][1]
            if ref > 0 and abs(pt[1] - ref) / ref <= tolerance_pct:
                cur.append(pt)
            else:
                if len(cur) >= 2:
                    clusters.append(cur)
                cur = [pt]
        if len(cur) >= 2:
            clusters.append(cur)
        return clusters

    zones = []
    for cl in cluster_pts(swing_highs)[-4:]:
        avg_p = sum(p for _, p in cl) / len(cl)
        max_i = max(i for i, _ in cl)
        ts    = tidx[max_i]
        t     = int(ts.timestamp()) if hasattr(ts, "timestamp") else int(ts)
        zones.append({"type": "equal_high", "price": round(float(avg_p), 3),
                      "strength": len(cl), "time": t,
                      "label": f"EQH ×{len(cl)} 買い逆指値集中"})
    for cl in cluster_pts(swing_lows)[-4:]:
        avg_p = sum(p for _, p in cl) / len(cl)
        max_i = max(i for i, _ in cl)
        ts    = tidx[max_i]
        t     = int(ts.timestamp()) if hasattr(ts, "timestamp") else int(ts)
        zones.append({"type": "equal_low", "price": round(float(avg_p), 3),
                      "strength": len(cl), "time": t,
                      "label": f"EQL ×{len(cl)} 売り逆指値集中"})
    return zones


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
    cot_sc,  cot_detail     = fetch_cot_data()                  # A: COT大口ポジ
    ob_sc,   ob_zones       = detect_order_blocks(df)            # B: OBゾーン
    fb_sc,   fb_rsns        = detect_fake_breakout(df, sr_levels) # C: フェイクブレイク
    liq_zones               = detect_liquidity_zones(df)         # D: 流動性ゾーン

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
    cot_n    = max(-1.0, min(1.0, cot_sc))
    ob_n     = max(-1.0, min(1.0, ob_sc))
    fb_n     = max(-1.0, min(1.0, fb_sc))

    # ── Weighted combination ────────────────────────
    #  rule 15%, candle 8%, dow 10%, vol 4%, div 4%,
    #  mtf 11%, momentum 8%, institutional 10%, fundamental 7%,
    #  news 4%, daily/weekly 4%, COT 5%, OB 5%, FakeBreak 5%
    combined = (
        rule_n   * 0.15 +
        candle_n * 0.08 +
        dow_n    * 0.10 +
        vol_n    * 0.04 +
        div_n    * 0.04 +
        mtf_n    * 0.11 +
        mom_n    * 0.08 +
        inst_n   * 0.10 +
        fund_n   * 0.07 +
        news_n   * 0.04 +
        dw_n     * 0.04 +
        cot_n    * 0.05 +
        ob_n     * 0.05 +
        fb_n     * 0.05
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
    cot_rsns = []
    if cot_detail.get("signal") and "中立" not in cot_detail.get("signal", ""):
        cot_rsns.append(f"📋 COT: {cot_detail['signal']}")

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
        cot_rsns +
        fb_rsns +
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
        "cot":       cot_detail,
        "ob_zones":  ob_zones,
        "liq_zones": liq_zones,
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
            "cot":           round(cot_n,    3),
            "order_block":   round(ob_n,     3),
            "fake_breakout": round(fb_n,     3),
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
    kw_score = 0.0
    for h in headlines:
        hl = h.lower()
        for kw in BULL:
            if kw in hl: kw_score += 1.0
        for kw in BEAR:
            if kw in hl: kw_score -= 1.0

    n = max(len(headlines), 1)
    kw_score = max(-1.0, min(1.0, kw_score / n))

    # AI分析（Claude Haiku）で60%ブレンド
    ai_result = analyze_news_ai(headlines)
    ai_score  = ai_result.get("score", 0.0)
    use_ai    = ai_result.get("source") == "claude_ai"

    if use_ai:
        score = ai_score * 0.6 + kw_score * 0.4
    else:
        score = kw_score
    score = max(-1.0, min(1.0, score))

    if   score >  0.15: sentiment = "📈 USD強気（円安方向）"
    elif score < -0.15: sentiment = "📉 USD弱気（円高方向）"
    else:               sentiment = "⚖️ 中立"

    result = {
        "score":       round(score, 3),
        "sentiment":   sentiment,
        "headlines":   headlines[:5],
        "count":       len(headlines),
        "ai_analysis": ai_result if use_ai else None,
        "kw_score":    round(kw_score, 3),
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

        SPREAD       = 0.030   # 3 pips
        SL_MULT      = TF_SL_MULT["1h"]   # 2.2
        TP_MULT      = TF_TP_MULT["1h"]   # 3.3
        MAX_HOLD     = 48                  # bars (hours)
        MIN_COMBINED = 0.33                # 0.38→0.33 過剰フィルター緩和
        EMA_LB       = 15                  # ↑ 5→15 トレンド判定安定化
        ATR_MED      = float(df["atr"].median())

        def _signal_ok(i):
            """標準モード エントリー条件（重複排除）"""
            row    = df.iloc[i]
            sub_df = df.iloc[:i + 1]
            rule_sc, _   = rule_signal(row)
            rule_n       = max(-1.0, min(1.0, rule_sc / 8.0))
            candle_sc, _ = detect_candle_patterns(sub_df)
            candle_n     = max(-1.0, min(1.0, candle_sc / 4.0))
            dow_sc, _    = dow_theory_analysis(sub_df)
            dow_n        = max(-1.0, min(1.0, dow_sc / 2.5))
            combined     = rule_n * 0.50 + candle_n * 0.20 + dow_n * 0.30
            if abs(combined) < MIN_COMBINED:
                return None, None
            # EMA15本トレンドフィルター
            ema21_prev = float(df["ema21"].iloc[i - EMA_LB])
            ema21_cur  = float(row["ema21"])
            ema50_cur  = float(row["ema50"])
            ema_trend  = 1.0 if ema21_cur > ema21_prev else -1.0
            if (combined > 0 and ema_trend < 0) or (combined < 0 and ema_trend > 0):
                return None, None
            # RSI確認フィルター（過熱ゾーンのみ除外）
            rsi = float(row["rsi"])
            if combined > 0 and rsi > 72:   return None, None  # 買われ過ぎゾーンはBUYしない
            if combined < 0 and rsi < 28:   return None, None  # 売られ過ぎゾーンはSELLしない
            # 低ボラティリティフィルター
            atr = float(row["atr"])
            if atr < ATR_MED * 0.5:
                return None, None
            # セッションフィルター: London + NY のみ (8〜20 UTC)
            try:
                h = row.name.hour
                if not (8 <= h < 20):
                    return None, None
            except Exception:
                pass
            sig = "BUY" if combined > 0 else "SELL"
            return sig, atr

        trades = []
        last_trade_bar = -99
        for i in range(max(50, EMA_LB + 1), len(df) - MAX_HOLD - 1):
            if i - last_trade_bar < 3:   # 3本クールダウン
                continue
            sig, atr = _signal_ok(i)
            if sig is None:
                continue
            # エントリーは次の足のOpen（ルックアヘッドバイアス排除）
            if i + 1 >= len(df):
                continue
            ep = float(df.iloc[i + 1]["Open"])
            ep = ep + SPREAD / 2 if sig == "BUY" else ep - SPREAD / 2
            sl = ep - atr * SL_MULT if sig == "BUY" else ep + atr * SL_MULT
            tp = ep + atr * TP_MULT if sig == "BUY" else ep - atr * TP_MULT

            outcome = None; bars_held = 0
            for j in range(1, MAX_HOLD + 1):
                if i + 1 + j >= len(df): break
                fut = df.iloc[i + 1 + j]
                hi, lo = float(fut["High"]), float(fut["Low"])
                if sig == "BUY":
                    if hi >= tp: outcome = "WIN";  bars_held = j; break
                    if lo <= sl: outcome = "LOSS"; bars_held = j; break
                else:
                    if lo <= tp: outcome = "WIN";  bars_held = j; break
                    if hi >= sl: outcome = "LOSS"; bars_held = j; break

            if outcome:
                last_trade_bar = i
                trades.append({"outcome": outcome, "bars_held": bars_held,
                                "sig": sig, "ep": round(ep, 3),
                                "sl": round(sl, 3), "tp": round(tp, 3),
                                "bar_idx": i})

        def _calc_stats(trade_list):
            if len(trade_list) < 5:
                return None
            w  = sum(1 for t in trade_list if t["outcome"] == "WIN")
            n  = len(trade_list)
            wr = round(w / n * 100, 1)
            ev = round((wr / 100 * TP_MULT) - ((1 - wr / 100) * SL_MULT), 3)
            return {"trades": n, "win_rate": wr, "expected_value": ev}

        def _max_dd(trade_list):
            """最大ドローダウン（RR単位）"""
            eq, peak, dd = 0.0, 0.0, 0.0
            for t in trade_list:
                eq += TP_MULT if t["outcome"] == "WIN" else -SL_MULT
                if eq > peak: peak = eq
                if peak - eq > dd: dd = peak - eq
            return round(dd, 3)

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
            mdd   = _max_dd(trades)
            # 簡易シャープ比（RR単位の期待値 / 標準偏差）
            pnls  = [TP_MULT if t["outcome"] == "WIN" else -SL_MULT for t in trades]
            pnl_std = float(np.std(pnls)) if len(pnls) > 1 else 1.0
            sharpe  = round(float(np.mean(pnls)) / max(pnl_std, 1e-6), 3)

            if   ev > 0.3: verdict = "✅ 期待値プラス（推奨）"
            elif ev > 0:   verdict = "🟡 期待値わずかプラス（要注意）"
            else:          verdict = "❌ 期待値マイナス（不推奨）"

            # ── Walk-forward: 3窓 (各30日) ───────────────────────────
            wf_windows = []
            for w_idx in range(3):
                d_from = lookback_days - (w_idx + 1) * 30
                d_to   = lookback_days - w_idx * 30
                label  = f"{d_from}〜{d_to}日前"
                # bar_idxで時間帯を近似（均等3分割）
                b_from = len(df) * w_idx // 3
                b_to   = len(df) * (w_idx + 1) // 3
                w_trades = [t for t in trades if b_from <= t["bar_idx"] < b_to]
                stats = _calc_stats(w_trades)
                if stats:
                    wf_windows.append({"label": label, **stats})

            profitable_windows = sum(1 for w in wf_windows if w.get("expected_value", -1) > 0)
            consistency = f"{profitable_windows}/{len(wf_windows)} 窓でプラス期待値"

            # 直近10トレードログ
            trade_log = [{"sig": t["sig"], "outcome": t["outcome"],
                          "bars": t["bars_held"]} for t in trades[-10:]]

            result = {
                "win_rate":        wr,
                "trades":          total,
                "wins":            wins,
                "losses":          total - wins,
                "rr":              rr,
                "avg_hold_hours":  avg_h,
                "expected_value":  ev,
                "max_drawdown":    mdd,
                "sharpe":          sharpe,
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
#  スキャルピング専用バックテスト（5m/15m足）
# ═══════════════════════════════════════════════════════
_scalp_bt_cache: dict = {}
SCALP_BT_TTL = 3600  # 1時間キャッシュ

def run_scalp_backtest(symbol: str = "USDJPY=X",
                       lookback_days: int = 30,
                       interval: str = "5m") -> dict:
    """
    スキャルピング専用バックテスト。
    実際のcompute_scalp_signalと同じロジック（EMA9PB必須/RSI5/Stoch/MACD/BB）で検証。
    ② TP: S/Rレベルを考慮した動的調整（最大ATR7×2.0）
    ③ EMA9プルバック必須 + THRESHOLD=0.55（厳格化後と同条件）
    SL: ATR7×0.8 / MAX_HOLD: 20bars / 1時間キャッシュ。
    """
    global _scalp_bt_cache
    cache_key = f"{interval}_{lookback_days}"
    now = datetime.now()
    cached = _scalp_bt_cache.get(cache_key)
    if cached and (now - cached["ts"]).total_seconds() < SCALP_BT_TTL:
        return cached["result"]

    try:
        df = fetch_ohlcv(symbol, period=f"{lookback_days}d", interval=interval)
        df = add_indicators(df)
        df = df.dropna()
        if len(df) < 200:
            return {"error": "データ不足（最低200本必要）", "trades": 0, "mode": "scalp"}

        SPREAD       = 0.005   # 0.5 pip
        SL_MULT      = 0.8
        TP_MULT      = 1.3
        TP_MAX       = 2.0
        MAX_HOLD     = 20      # bars
        COOLDOWN     = 3       # bars between signals (5→3 過剰フィルター緩和)
        bars_per_min = 5 if interval == "5m" else 15

        trades = []
        last_trade_bar = -99

        for i in range(60, len(df) - MAX_HOLD - 1):
            if i - last_trade_bar < COOLDOWN:
                continue

            row     = df.iloc[i]
            entry   = float(row["Close"])
            atr7    = float(row["atr7"]) if "atr7" in row.index else float(row["atr"])
            rsi5    = float(row.get("rsi5", row["rsi"]))
            stoch_k = float(row.get("stoch_k", 50.0))
            stoch_d = float(row.get("stoch_d", 50.0))
            macdh   = float(row["macd_hist"])
            bbpb    = float(row["bb_pband"])
            ema9    = float(row["ema9"])
            ema21   = float(row["ema21"])
            ema50   = float(row["ema50"])
            if atr7 <= 0:
                continue

            # セッションフィルター: London + NY (8〜18 UTC)
            try:
                h = row.name.hour
                if not (8 <= h < 18):
                    continue
            except Exception:
                pass

            # EMAトレンド判定（15本前との比較）
            ema21_prev = float(df["ema21"].iloc[i - 15])
            if   ema21 > ema21_prev and ema21 > ema50: d_mult =  1.0
            elif ema21 < ema21_prev and ema21 < ema50: d_mult = -1.0
            else: continue

            score = 0.0
            has_pullback  = False
            has_rsi_reset = False  # ← 新規必須条件

            if d_mult == 1.0:
                if ema9 > ema21 > ema50:
                    if entry <= ema9 * 1.001:   score += 2.0; has_pullback = True
                    elif entry <= ema9 * 1.003: score += 0.8
                    else:                       score += 0.3
                elif ema9 > ema21: score += 0.4
                if rsi5 < 25:   score += 1.8; has_rsi_reset = True
                elif rsi5 < 52: score += 1.2; has_rsi_reset = True  # 45→52 緩和
                elif rsi5 < 60: score += 0.5
                if macdh > 0:   score += 0.6
                if bbpb < 0.25: score += 0.6
                if stoch_k < 20 and stoch_k > stoch_d:  score += 1.0
                elif stoch_k < 40 and stoch_k > stoch_d: score += 0.5
            else:
                if ema9 < ema21 < ema50:
                    if entry >= ema9 * 0.999:   score -= 2.0; has_pullback = True
                    elif entry >= ema9 * 0.997: score -= 0.8
                    else:                       score -= 0.3
                elif ema9 < ema21: score -= 0.4
                if rsi5 > 75:   score -= 1.8; has_rsi_reset = True
                elif rsi5 > 48: score -= 1.2; has_rsi_reset = True  # 55→48 緩和
                elif rsi5 > 40: score -= 0.5
                if macdh < 0:   score -= 0.6
                if bbpb > 0.75: score -= 0.6
                if stoch_k > 80 and stoch_k < stoch_d:  score -= 1.0
                elif stoch_k > 60 and stoch_k < stoch_d: score -= 0.5

            # 必須条件: EMA9プルバック AND RSI5リセット
            if not has_pullback or not has_rsi_reset:
                continue
            if abs(score) < 2.5:   # 絶対スコア閾値（3.0→2.5 緩和）
                continue

            sig = "BUY" if score > 0 else "SELL"
            # エントリーは次の足のOpen
            if i + 1 >= len(df):
                continue
            ep  = float(df.iloc[i + 1]["Open"])
            ep  = ep + SPREAD / 2 if sig == "BUY" else ep - SPREAD / 2
            sl  = ep - atr7 * SL_MULT if sig == "BUY" else ep + atr7 * SL_MULT

            # TP: S/Rスナップ
            sub_sr = find_sr_levels(df.iloc[max(0, i - 100):i + 1],
                                    window=5, tolerance_pct=0.002)
            if sig == "BUY":
                tp_cands = [l for l in sub_sr if ep + atr7 * 0.3 < l < ep + atr7 * TP_MAX]
                tp = round(min(tp_cands) - atr7 * 0.05, 3) if tp_cands else round(ep + atr7 * TP_MULT, 3)
            else:
                tp_cands = [l for l in sub_sr if ep - atr7 * TP_MAX < l < ep - atr7 * 0.3]
                tp = round(max(tp_cands) + atr7 * 0.05, 3) if tp_cands else round(ep - atr7 * TP_MULT, 3)
            sl_dist = abs(ep - sl)
            if abs(tp - ep) < sl_dist:
                tp = round(ep + sl_dist * 1.2, 3) if sig == "BUY" else round(ep - sl_dist * 1.2, 3)

            actual_rr = round(abs(tp - ep) / max(sl_dist, 1e-6), 2)
            outcome = None; bars_held = 0
            for j in range(1, MAX_HOLD + 1):
                if i + 1 + j >= len(df): break
                fut = df.iloc[i + 1 + j]
                hi, lo = float(fut["High"]), float(fut["Low"])
                if sig == "BUY":
                    if hi >= tp: outcome = "WIN";  bars_held = j; break
                    if lo <= sl: outcome = "LOSS"; bars_held = j; break
                else:
                    if lo <= tp: outcome = "WIN";  bars_held = j; break
                    if hi >= sl: outcome = "LOSS"; bars_held = j; break

            if outcome:
                last_trade_bar = i
                trades.append({"outcome": outcome, "bars_held": bars_held,
                                "sig": sig, "ep": round(ep, 3),
                                "actual_rr": actual_rr, "bar_idx": i})

        def _max_dd_scalp(trade_list):
            eq, peak, dd = 0.0, 0.0, 0.0
            for t in trade_list:
                eq += TP_MULT if t["outcome"] == "WIN" else -SL_MULT
                if eq > peak: peak = eq
                if peak - eq > dd: dd = peak - eq
            return round(dd, 3)

        if len(trades) < 10:
            result = {
                "error":  f"サンプル数不足（{len(trades)}トレード）",
                "trades": len(trades),
                "mode":   "scalp",
            }
        else:
            wins  = sum(1 for t in trades if t["outcome"] == "WIN")
            total = len(trades)
            wr    = round(wins / total * 100, 1)
            rr    = round(TP_MULT / SL_MULT, 2)
            ev    = round((wr / 100 * TP_MULT) - ((1 - wr / 100) * SL_MULT), 3)
            avg_h = round(sum(t["bars_held"] for t in trades) / total, 1)
            mdd   = _max_dd_scalp(trades)
            pnls  = [TP_MULT if t["outcome"] == "WIN" else -SL_MULT for t in trades]
            sharpe = round(float(np.mean(pnls)) / max(float(np.std(pnls)), 1e-6), 3)
            per_day = round(total / lookback_days, 1)

            if   ev > 0.3: verdict = "✅ 期待値プラス（スキャル推奨）"
            elif ev > 0:   verdict = "🟡 期待値わずかプラス（要注意）"
            else:          verdict = "❌ 期待値マイナス（スキャル不推奨）"

            # Walk-forward: 3窓
            wlen = max(1, len(trades) // 3)
            wf_windows = []
            for w in range(3):
                wt = trades[w * wlen:(w + 1) * wlen]
                if len(wt) < 5: continue
                ww  = sum(1 for t in wt if t["outcome"] == "WIN")
                wwr = round(ww / len(wt) * 100, 1)
                wev = round((wwr / 100 * TP_MULT) - ((1 - wwr / 100) * SL_MULT), 3)
                wf_windows.append({"label": f"窓{w + 1}", "trades": len(wt),
                                   "win_rate": wwr, "expected_value": wev})

            profitable = sum(1 for w in wf_windows if w.get("expected_value", -1) > 0)
            trade_log  = [{"sig": t["sig"], "outcome": t["outcome"],
                           "bars": t["bars_held"]} for t in trades[-10:]]
            result = {
                "win_rate":       wr,
                "trades":         total,
                "wins":           wins,
                "losses":         total - wins,
                "rr":             rr,
                "avg_hold_bars":  avg_h,
                "avg_hold_min":   round(avg_h * bars_per_min, 1),
                "trades_per_day": per_day,
                "expected_value": ev,
                "max_drawdown":   mdd,
                "sharpe":         sharpe,
                "verdict":        verdict,
                "period":         f"過去{lookback_days}日 ({interval}足)",
                "sl_mult":        SL_MULT,
                "tp_mult":        TP_MULT,
                "walk_forward":   wf_windows,
                "consistency":    f"{profitable}/{len(wf_windows)} 窓でプラス期待値",
                "trade_log":      trade_log,
                "mode":           "scalp",
            }

        _scalp_bt_cache[cache_key] = {"result": result, "ts": now}
        return result
    except Exception as e:
        import traceback
        print(f"[SCALP_BT] {traceback.format_exc()}")
        return {"error": str(e), "mode": "scalp"}


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
#  Mode: Day Flow — NY引け後の1日トレードプラン
# ═══════════════════════════════════════════════════════
_dayplan_cache: dict = {}
DAYPLAN_TTL = 3600  # 1時間キャッシュ


def get_session_range(symbol: str, session: str = "tokyo") -> dict:
    """指定セッション(UTC)の高値・安値・中値を取得。"""
    try:
        df_1h = fetch_ohlcv(symbol, period="5d", interval="1h")
        if df_1h.index.tz is None:
            df_1h.index = df_1h.index.tz_localize("UTC")

        now_utc     = datetime.now(timezone.utc)
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

        hours_map = {"tokyo": (0, 9), "london": (8, 17), "ny": (13, 22)}
        s_start, s_end = hours_map.get(session, (0, 9))

        bars = df_1h[
            (df_1h.index >= today_start) &
            (df_1h.index.hour >= s_start) & (df_1h.index.hour < s_end)
        ]
        if len(bars) == 0:
            yesterday = today_start - pd.Timedelta(days=1)
            bars = df_1h[
                (df_1h.index >= yesterday) & (df_1h.index < today_start) &
                (df_1h.index.hour >= s_start) & (df_1h.index.hour < s_end)
            ]
        if len(bars) == 0:
            return {}

        high = float(bars["High"].max())
        low  = float(bars["Low"].min())
        return {"high": round(high, 3), "low": round(low, 3),
                "mid": round((high + low) / 2, 3), "bars": len(bars)}
    except Exception as e:
        print(f"[SESSION_RANGE/{session}] {e}")
        return {}


def compute_dayflow_plan(symbol: str = "USDJPY=X") -> dict:
    """
    NY引け後に翌日のトレードプランを算出。
    標準ピボットポイント + 前日高安 + セッション別エントリーゾーンを返す。
    """
    global _dayplan_cache
    now = datetime.now()
    if (_dayplan_cache.get("ts") and
            (now - _dayplan_cache["ts"]).total_seconds() < DAYPLAN_TTL):
        return _dayplan_cache["result"]

    try:
        df_d = fetch_ohlcv(symbol, period="30d", interval="1d")
        if len(df_d) < 3:
            return {"error": "データ不足"}

        prev  = df_d.iloc[-2]
        today = df_d.iloc[-1]
        ph, pl, pc = float(prev["High"]), float(prev["Low"]), float(prev["Close"])
        tc         = float(today["Close"])

        # 標準ピボットポイント
        pivot = (ph + pl + pc) / 3
        r1 = 2 * pivot - pl;   s1 = 2 * pivot - ph
        r2 = pivot + ph - pl;  s2 = pivot - ph + pl
        r3 = r1 + ph - pl;     s3 = s1 - ph + pl

        # 週足オープン
        df_w = fetch_ohlcv(symbol, period="10d", interval="1wk")
        wo   = round(float(df_w["Open"].iloc[-1]), 3) if len(df_w) > 0 else round(pivot, 3)

        # 日足ATR
        df_di = add_indicators(df_d.tail(20).copy())
        datr  = round(float(df_di["atr"].iloc[-1]), 3) if len(df_di) > 0 else 0.3

        # 方向バイアス
        if tc > pivot and tc > wo:
            bias_lbl = "📈 強気（ピボット＆週足オープン上）→ BUY優先"
        elif tc < pivot and tc < wo:
            bias_lbl = "📉 弱気（ピボット＆週足オープン下）→ SELL優先"
        elif tc > pivot:
            bias_lbl = "🟡 やや強気（ピボット上）→ BUY方向"
        else:
            bias_lbl = "🟡 やや弱気（ピボット下）→ SELL方向"

        tokyo  = get_session_range(symbol, "tokyo")
        london = get_session_range(symbol, "london")

        result = {
            "date":      str(today.name.date()) if hasattr(today.name, "date") else str(today.name),
            "bias":      bias_lbl,
            "bias_dir":  "bull" if tc > pivot else "bear",
            "current":   round(tc, 3),
            "daily_atr": datr,
            "levels": {
                "r3": round(r3, 3), "r2": round(r2, 3), "r1": round(r1, 3),
                "pivot": round(pivot, 3),
                "s1": round(s1, 3), "s2": round(s2, 3), "s3": round(s3, 3),
            },
            "prev_day":     {"high": round(ph, 3), "low": round(pl, 3), "close": round(pc, 3)},
            "weekly_open":  wo,
            "buy_plan": {
                "entry": round(s1, 3),
                "sl":    round(s2 - datr * 0.2, 3),
                "tp1":   round(pivot, 3),
                "tp2":   round(r1, 3),
                "note":  "S1でロング → TP1:ピボット / TP2:R1",
            },
            "sell_plan": {
                "entry": round(r1, 3),
                "sl":    round(r2 + datr * 0.2, 3),
                "tp1":   round(pivot, 3),
                "tp2":   round(s1, 3),
                "note":  "R1でショート → TP1:ピボット / TP2:S1",
            },
            "tokyo_range":  tokyo,
            "london_range": london,
            "session_strategy": [
                "🌅 東京: レンジ高値付近SELL / 安値付近BUY（レンジトレード）",
                "🇬🇧 ロンドン: 東京レンジブレイク方向に追随",
                "🗽 NY: ロンドントレンド継続 or ピボット反転監視",
            ],
        }
        _dayplan_cache["result"] = result
        _dayplan_cache["ts"]     = now
        return result
    except Exception as e:
        import traceback; print(f"[DAYPLAN] {traceback.format_exc()}")
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════
#  Mode: Session Strategy — セッション別トレード
# ═══════════════════════════════════════════════════════
def compute_session_signal(df: pd.DataFrame, tf: str, sr_levels: list,
                           symbol: str = "USDJPY=X") -> dict:
    """
    セッション別戦略:
    - 東京: アジアレンジのレンジトレード（高値SELL / 安値BUY）
    - ロンドン: 東京レンジブレイク方向追随
    - NY: 1H+4H継続 or ピボット反転
    ベースシグナル70% + セッションバイアス30% で合成。
    """
    session = get_session_info()
    sname   = session["name"]
    row     = df.iloc[-1]
    entry   = float(row["Close"])
    atr     = float(row["atr"])

    base          = compute_signal(df, tf, sr_levels, symbol)
    base_combined = base["score_detail"]["combined"]

    tokyo  = get_session_range(symbol, "tokyo")
    t_high = tokyo.get("high")
    t_low  = tokyo.get("low")
    t_mid  = tokyo.get("mid")

    ses_bias  = 0.0
    ses_notes = []
    s_type    = "off"

    if "Tokyo" in sname or "東京" in sname:
        s_type = "range"
        if t_high and t_low and t_high != t_low:
            r_pct = (entry - t_low) / (t_high - t_low)
            if r_pct >= 0.80:
                ses_bias = -0.65; ses_notes.append(f"🌅 東京レンジ上限({t_high:.3f})接近 → SELL")
            elif r_pct <= 0.20:
                ses_bias =  0.65; ses_notes.append(f"🌅 東京レンジ下限({t_low:.3f})接近 → BUY")
            elif r_pct >= 0.60:
                ses_bias = -0.20; ses_notes.append("🌅 レンジ上半部 → やや慎重")
            elif r_pct <= 0.40:
                ses_bias =  0.20; ses_notes.append("🌅 レンジ下半部 → やや強気")
            else:
                ses_notes.append(f"🌅 東京レンジ中央({t_mid:.3f}) → WAIT")
        else:
            ses_notes.append("🌅 東京レンジ形成中 → WAIT")

    elif "London" in sname or "ロンドン" in sname:
        s_type = "breakout"
        if t_high and t_low:
            if entry > t_high + atr * 0.3:
                ses_bias =  0.70; ses_notes.append(f"🇬🇧 東京高値({t_high:.3f})ブレイク → BUY")
            elif entry < t_low - atr * 0.3:
                ses_bias = -0.70; ses_notes.append(f"🇬🇧 東京安値({t_low:.3f})ブレイク → SELL")
            elif entry > t_high:
                ses_bias =  0.35; ses_notes.append("🇬🇧 東京高値上 → BUY方向")
            elif entry < t_low:
                ses_bias = -0.35; ses_notes.append("🇬🇧 東京安値下 → SELL方向")
            else:
                ses_notes.append(f"🇬🇧 東京レンジ内 ({t_low:.3f}–{t_high:.3f}) → ブレイク待ち")
        else:
            ses_notes.append("🇬🇧 ロンドン開幕 → 東京レンジ確認中")

    elif "New York" in sname or "NY" in sname:
        s_type = "continuation"
        htf = get_htf_bias(symbol)
        dp  = compute_dayflow_plan(symbol)
        pivot = dp.get("levels", {}).get("pivot")
        if htf["agreement"] == "bull":
            ses_bias = 0.50; ses_notes.append("🗽 NY: 1H+4H強気 → BUY継続")
            if pivot and entry > pivot:
                ses_notes.append(f"✅ ピボット({pivot:.3f})上 → BUY確度高")
        elif htf["agreement"] == "bear":
            ses_bias = -0.50; ses_notes.append("🗽 NY: 1H+4H弱気 → SELL継続")
            if pivot and entry < pivot:
                ses_notes.append(f"✅ ピボット({pivot:.3f})下 → SELL確度高")
        else:
            ses_notes.append("🗽 NY: 不明確 → 様子見")
            if pivot and abs(entry - pivot) < atr * 0.5:
                ses_notes.append(f"⚠️ ピボット({pivot:.3f})近辺 → 反転注意")
    else:
        ses_notes.append("🌙 閑散時間帯 → トレード非推奨")

    final = base_combined * 0.70 + ses_bias * 0.30
    THRESHOLD = 0.25
    if   final >  THRESHOLD: signal, conf = "BUY",  int(min(90, 50 + final * 50))
    elif final < -THRESHOLD: signal, conf = "SELL", int(min(90, 50 + abs(final) * 50))
    else:                    signal, conf = "WAIT", int(max(25, 50 - abs(final) * 35))

    act = signal if signal != "WAIT" else ("BUY" if final >= 0 else "SELL")
    sl, tp = calc_sl_tp_v3(entry, act, atr, sr_levels, tf=tf)
    rr = round(abs(tp - entry) / max(abs(sl - entry), 1e-6), 2)

    # セッション別戦略のキー (フロントエンド用) — 重複セッションはNY優先
    if "New York" in sname or "NY" in sname:
        ses_key = "ny"
    elif "Tokyo" in sname or "東京" in sname:
        ses_key = "tokyo"
    elif "London" in sname or "ロンドン" in sname:
        ses_key = "london"
    else:
        ses_key = "off"
    return {
        **base,
        "signal": signal, "confidence": conf,
        "sl": sl, "tp": tp, "rr_ratio": rr,
        "mode": "session", "session_bias": round(ses_bias, 3),
        "session_strategy": {
            "type":       s_type, "session":    sname,
            "bias":       round(ses_bias, 3), "notes": ses_notes,
            "tokyo_high": round(t_high, 3) if t_high else None,
            "tokyo_low":  round(t_low,  3) if t_low  else None,
            "tokyo_mid":  round(t_mid,  3) if t_mid  else None,
        },
        "session_info": {
            "session":       ses_key,
            "strategy_note": ses_notes[0] if ses_notes else "—",
            "tokyo_range": {
                "high": round(t_high, 3) if t_high else None,
                "low":  round(t_low,  3) if t_low  else None,
            },
        },
        "reasons": ses_notes + base.get("reasons", []),
    }


# ═══════════════════════════════════════════════════════
#  Mode: Scalping — 1H足ベーススキャルピング（1m/5m/15m）
# ═══════════════════════════════════════════════════════
def compute_scalp_signal(df: pd.DataFrame, tf: str, sr_levels: list,
                         symbol: str = "USDJPY=X") -> dict:
    """
    スキャルピングモード (推奨: 1m/5m/15m)。
    1H+4H トレンドをハードフィルターとして使用。
    EMA9プルバック + RSIリセット + MACD/BB確認 でエントリー判断。
    SL=ATR×0.8 / TP=ATR×1.2 固定（スピード重視）。
    """
    htf    = get_htf_bias(symbol)
    row    = df.iloc[-1]
    entry  = float(row["Close"])
    atr    = float(row["atr"])
    rsi    = float(row["rsi"])
    ema9   = float(row["ema9"])
    ema21  = float(row["ema21"])
    ema50  = float(row["ema50"])
    macdh  = float(row["macd_hist"])
    bbpb   = float(row["bb_pband"])
    atr7   = float(row["atr7"]) if "atr7" in row.index else atr  # 短期ATR(7)
    session = get_session_info()

    h1_sc  = htf.get("h1", {}).get("score", 0.0)
    h4_sc  = htf.get("h4", {}).get("score", 0.0)

    score   = 0.0
    reasons = []

    # ── 1H+4H ハードフィルター ──
    if htf["agreement"] == "bull":
        d_mult = 1.0;  reasons.append("📈 1H+4H 強気 → BUYのみ有効")
    elif htf["agreement"] == "bear":
        d_mult = -1.0; reasons.append("📉 1H+4H 弱気 → SELLのみ有効")
    else:
        d_mult = 0.5;  reasons.append("⚖️ 1H+4H 不一致 → シグナル抑制中")

    # ── EMA9 プルバック ──
    # mixed(0.5)のときは方向が不明瞭なのでスキップ
    if d_mult == 1.0:
        if ema9 > ema21 > ema50:
            if entry <= ema9 * 1.001:   # EMA9の0.1%以内まで引いたときのみ
                score += 2.0; reasons.append(f"✅ EMA9プルバック({ema9:.3f}) BUYゾーン")
            elif entry <= ema9 * 1.003:
                score += 0.8; reasons.append("↗ EMA9>EMA21>EMA50 上昇列")
            else:
                score += 0.3; reasons.append("↗ EMA上昇配列（プルバック待ち）")
        elif ema9 > ema21:
            score += 0.4; reasons.append("↗ EMA9>EMA21")
    elif d_mult == -1.0:
        if ema9 < ema21 < ema50:
            if entry >= ema9 * 0.999:   # EMA9の0.1%以内まで戻したときのみ
                score -= 2.0; reasons.append(f"✅ EMA9プルバック({ema9:.3f}) SELLゾーン")
            elif entry >= ema9 * 0.997:
                score -= 0.8; reasons.append("↘ EMA9<EMA21<EMA50 下降列")
            else:
                score -= 0.3; reasons.append("↘ EMA下降配列（戻り待ち）")
        elif ema9 < ema21:
            score -= 0.4; reasons.append("↘ EMA9<EMA21")
    else:
        reasons.append("⚖️ EMA方向不明瞭 → スキップ")

    # ── RSI(5) 高速版 + RSI(14) 補助 ──
    rsi5  = float(row.get("rsi5", rsi))  # 高速RSI(5)
    if d_mult == 1.0:
        if rsi5 < 25:   score += 1.8; reasons.append(f"✅ RSI5 売られ過ぎ({rsi5:.0f}) 強BUYシグナル")
        elif rsi5 < 45: score += 1.2; reasons.append(f"✅ RSI5({rsi5:.0f}) リセット完了")
        elif rsi5 < 55: score += 0.5; reasons.append(f"↗ RSI5({rsi5:.0f}) 中立圏")
        if rsi < 40:    score += 0.4  # RSI14補助
    elif d_mult == -1.0:
        if rsi5 > 75:   score -= 1.8; reasons.append(f"✅ RSI5 買われ過ぎ({rsi5:.0f}) 強SELLシグナル")
        elif rsi5 > 55: score -= 1.2; reasons.append(f"✅ RSI5({rsi5:.0f}) リセット完了")
        elif rsi5 > 45: score -= 0.5; reasons.append(f"↘ RSI5({rsi5:.0f}) 中立圏")
        if rsi > 60:    score -= 0.4  # RSI14補助

    # ── MACD ──
    if d_mult == 1.0 and macdh > 0:   score += 0.6; reasons.append("✅ MACDヒスト正")
    elif d_mult == 1.0 and macdh < 0:  score -= 0.3
    elif d_mult == -1.0 and macdh < 0: score -= 0.6; reasons.append("✅ MACDヒスト負")
    elif d_mult == -1.0 and macdh > 0: score += 0.3

    # ── ボリンジャーバンド ──
    if d_mult == 1.0 and bbpb < 0.25:
        score += 0.6; reasons.append(f"✅ BB下限付近({bbpb:.2f}) スキャルBUYゾーン")
    elif d_mult == -1.0 and bbpb > 0.75:
        score -= 0.6; reasons.append(f"✅ BB上限付近({bbpb:.2f}) スキャルSELLゾーン")

    # ── Stochastic(5,3,3) — クロス確認 ──
    stoch_k = float(row.get("stoch_k", 50.0))
    stoch_d = float(row.get("stoch_d", 50.0))
    if d_mult == 1.0:
        if stoch_k < 20 and stoch_k > stoch_d:
            score += 1.0; reasons.append(f"✅ Stoch ゴールデンクロス({stoch_k:.0f}) 売られ過ぎ圏")
        elif stoch_k < 40 and stoch_k > stoch_d:
            score += 0.5; reasons.append(f"↗ Stoch({stoch_k:.0f}) 上向き")
    elif d_mult == -1.0:
        if stoch_k > 80 and stoch_k < stoch_d:
            score -= 1.0; reasons.append(f"✅ Stoch デッドクロス({stoch_k:.0f}) 買われ過ぎ圏")
        elif stoch_k > 60 and stoch_k < stoch_d:
            score -= 0.5; reasons.append(f"↘ Stoch({stoch_k:.0f}) 下向き")

    # ── 方向フィルター & セッション補正 ──
    # ※ scoreはすでに方向性あり（正=BUY,負=SELL）→ d_multの符号は使わず倍率のみ適用
    score *= (1.0 if abs(d_mult) == 1.0 else 0.55)
    if session["name"] in ("NY × London", "New York", "London"):
        score *= 1.10; reasons.append(f"🟢 {session['name']}（流動性高）")
    elif session["name"] == "Off-hours":
        score *= 0.50; reasons.append("⚠️ 閑散時間帯（スキャル非推奨）")

    # TF警告
    if tf not in ("1m", "5m", "15m"):
        reasons.append(f"⚠️ {tf}足 — スキャルは1m/5m/15m推奨")

    # ── SL / TP ──
    SCALP_SL, SCALP_TP = 0.8, 1.3
    # 必須条件チェック（バックテストと同条件）
    has_pb        = any("EMA9プルバック" in r and ("BUYゾーン" in r or "SELLゾーン" in r) for r in reasons)
    has_rsi_reset = any("RSI5" in r and ("売られ過ぎ" in r or "リセット完了" in r or "買われ過ぎ" in r) for r in reasons)
    if not has_pb:
        reasons.append("⛔ EMA9プルバック未確認 → WAIT（押し目/戻り待機）")
        signal, conf = "WAIT", int(max(15, 50 - abs(score) * 10))
    elif not has_rsi_reset:
        reasons.append("⛔ RSI5未リセット → WAIT（RSI5<45 or >55 を待機）")
        signal, conf = "WAIT", int(max(15, 50 - abs(score) * 10))
    elif abs(score) < 3.0:
        reasons.append(f"⛔ スコア不足({score:.1f}<3.0) → WAIT")
        signal, conf = "WAIT", int(max(15, 50 - abs(score) * 10))
    elif score >  0: signal, conf = "BUY",  int(min(90, 50 + score * 8))
    elif score <  0: signal, conf = "SELL", int(min(90, 50 + abs(score) * 8))
    else:            signal, conf = "WAIT", 20

    act = signal if signal != "WAIT" else ("BUY" if score >= 0 else "SELL")
    atr_scalp = atr7 if atr7 > 0 else atr

    # SL: ATR7ベース（タイト固定）
    sl = round(entry - atr_scalp * SCALP_SL, 3) if act == "BUY" else round(entry + atr_scalp * SCALP_SL, 3)

    # ② TP: S/Rレベルを考慮した動的調整（最大ATR7×2.0）
    SCALP_TP_MAX = 2.0
    if act == "BUY":
        tp_cands = [l for l in sr_levels if entry + atr_scalp * 0.3 < l < entry + atr_scalp * SCALP_TP_MAX]
        if tp_cands:
            tp = round(min(tp_cands) - atr_scalp * 0.05, 3)
            reasons.append(f"🎯 TP → S/R {min(tp_cands):.3f} に調整")
        else:
            tp = round(entry + atr_scalp * SCALP_TP, 3)
        # ③ 直近S/Rが近すぎる場合は警告
        near_sr = [l for l in sr_levels if entry < l < entry + atr_scalp * 0.5]
        if near_sr:
            reasons.append(f"⚠️ 直近S/R({min(near_sr):.3f})近接 → TP到達前に反発リスク")
    else:
        tp_cands = [l for l in sr_levels if entry - atr_scalp * SCALP_TP_MAX < l < entry - atr_scalp * 0.3]
        if tp_cands:
            tp = round(max(tp_cands) + atr_scalp * 0.05, 3)
            reasons.append(f"🎯 TP → S/R {max(tp_cands):.3f} に調整")
        else:
            tp = round(entry - atr_scalp * SCALP_TP, 3)
        near_sr = [l for l in sr_levels if entry - atr_scalp * 0.5 < l < entry]
        if near_sr:
            reasons.append(f"⚠️ 直近S/R({max(near_sr):.3f})近接 → TP到達前に反発リスク")

    # 最小RR保証（1.0以上）
    sl_dist = abs(entry - sl)
    if abs(tp - entry) < sl_dist:
        tp = round(entry + sl_dist * 1.2, 3) if act == "BUY" else round(entry - sl_dist * 1.2, 3)
        reasons.append("⚠️ RR不足 → TP最小RR1.2に拡張")

    rr  = round(abs(tp - entry) / max(abs(sl - entry), 1e-6), 2)

    ts_str = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)
    return {
        "timestamp": ts_str, "symbol": "USD/JPY", "tf": tf,
        "entry": round(entry, 3), "signal": signal, "confidence": conf,
        "sl": sl, "tp": tp, "rr_ratio": rr, "atr": round(atr, 3),
        "session": session, "htf_bias": htf, "swing_mode": False,
        "reasons": reasons, "mode": "scalp",
        "scalp_score": round(score, 3),
        "indicators": {
            "ema9":      round(ema9,  3), "ema21": round(ema21, 3),
            "ema50":     round(ema50, 3), "rsi":   round(rsi,   1),
            "macd":      round(float(row["macd"]), 5),
            "macd_sig":  round(float(row["macd_sig"]), 5),
            "macd_hist": round(macdh, 5),
            "bb_upper":  round(float(row["bb_upper"]), 3),
            "bb_mid":    round(float(row["bb_mid"]),   3),
            "bb_lower":  round(float(row["bb_lower"]), 3),
            "bb_pband":  round(bbpb,  3),
        },
        "score_detail": {
            "h1_score":  round(h1_sc, 3), "h4_score": round(h4_sc, 3),
            "combined":  round(score, 3),
            # スキャルプで使うコンポーネントをスコアバーに反映
            "mtf":       round(max(-1.0, min(1.0, (h1_sc + h4_sc) / 2)), 3),
            "rule":      round(max(-1.0, min(1.0, score / max(abs(score), 1e-6) * 0.5)), 3) if score != 0 else 0.0,
        },
        "scalp_info": {
            "htf_label":     htf.get("label", "—"),
            "htf_direction": 1 if htf["agreement"] == "bull" else (-1 if htf["agreement"] == "bear" else 0),
            "scalp_score":   round(score, 3),
            "sl_pips":       round(atr_scalp * SCALP_SL * 100, 1),
            "tp_pips":       round(atr_scalp * SCALP_TP * 100, 1),
            "atr7":          round(atr7, 3),
            "rsi5":          round(float(row.get("rsi5", 50)), 1),
            "stoch_k":       round(float(row.get("stoch_k", 50)), 1),
        },
    }


# ═══════════════════════════════════════════════════════
#  News AI — Claude APIでニュースをファンダメンタル分析
# ═══════════════════════════════════════════════════════
_news_ai_cache: dict = {}
NEWS_AI_TTL = 1800  # 30分キャッシュ


def analyze_news_ai(headlines: list) -> dict:
    """
    Claude claude-haiku-4-5-20251001でニュースヘッドラインをUSD/JPYファンダメンタル分析。
    ANTHROPIC_API_KEY 未設定時はキーワード分析にフォールバック。
    """
    global _news_ai_cache
    now = datetime.now()

    cache_key = str(sorted(set(headlines[:10])))
    if (_news_ai_cache.get("key") == cache_key and _news_ai_cache.get("ts") and
            (now - _news_ai_cache["ts"]).total_seconds() < NEWS_AI_TTL):
        return _news_ai_cache["result"]

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or not headlines:
        return {"score": 0.0, "sentiment": "⚖️ 中立", "key_factor": "—",
                "risk": "—", "source": "keyword"}

    try:
        import anthropic as _ant, json as _js
        client = _ant.Anthropic(api_key=api_key)
        hl_text = "\n".join(f"- {h}" for h in headlines[:10])
        prompt = (
            "あなたはFXアナリストです。以下のUSD/JPY関連ニュースヘッドラインを読み、"
            "USD/JPYの方向性をJSON形式のみで回答してください（説明不要）。\n\n"
            f"【ニュース】\n{hl_text}\n\n"
            '{"score": -1.0から1.0の数値（正=USD強気/円安, 負=USD弱気/円高, 0=中立）,'
            '"sentiment": "📈 USD強気（円安方向）" または "📉 USD弱気（円高方向）" または "⚖️ 中立",'
            '"key_factor": "最重要ファクター40字以内",'
            '"risk": "主なリスク40字以内"}'
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        text = msg.content[0].text.strip()
        s, e = text.find("{"), text.rfind("}") + 1
        result = _js.loads(text[s:e])
        result["source"] = "claude_ai"
        result["score"]  = max(-1.0, min(1.0, float(result.get("score", 0.0))))
        _news_ai_cache = {"key": cache_key, "result": result, "ts": now}
        return result
    except Exception as ex:
        print(f"[NEWS_AI] {ex}")
        return {"score": 0.0, "sentiment": "⚖️ 中立（AI分析失敗）",
                "key_factor": "取得失敗", "risk": "—", "source": "error"}


# ═══════════════════════════════════════════════════════
#  Flask routes
# ═══════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/signal")
def api_signal():
    tf   = request.args.get("tf", "1m")
    mode = request.args.get("mode", "standard")
    cfg  = TF_CFG.get(tf, TF_CFG["1m"])
    try:
        df = fetch_ohlcv("USDJPY=X", period=cfg["period"], interval=cfg["interval"])
        if cfg["resample"]: df = resample_df(df, cfg["resample"])
        df = add_indicators(df)
        sr = find_sr_levels(df, window=cfg["sr_w"], tolerance_pct=cfg["sr_tol"])
        if mode == "scalp":
            result = compute_scalp_signal(df, tf, sr, "USDJPY=X")
        elif mode == "session":
            result = compute_session_signal(df, tf, sr, "USDJPY=X")
        elif mode == "dayflow":
            result = compute_signal(df, tf, sr)
            plan   = compute_dayflow_plan("USDJPY=X")
            result["day_plan"] = plan
            result["mode"]     = "dayflow"
        else:
            result = compute_signal(df, tf, sr)
        # データソース情報を付加
        result["ohlcv_source"] = _last_data_source.get(cfg["interval"], "yfinance")
        result["bar_count"]    = len(df)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/day_plan")
def api_day_plan():
    """Day Flow用ピボットプランを返す（1時間キャッシュ）"""
    try:
        plan = compute_dayflow_plan("USDJPY=X")
        return jsonify(plan)
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
                "rsi5":      round(float(row.get("rsi5", row["rsi"])), 1),
                "stoch_k":   round(float(row.get("stoch_k", 50)), 1),
                "stoch_d":   round(float(row.get("stoch_d", 50)), 1),
                "macd":      round(float(row["macd"]),       5),
                "macd_sig":  round(float(row["macd_sig"]),   5),
                "macd_hist": round(float(row["macd_hist"]),  5),
            })
        markers   = detect_large_player_markers(df_chart)
        _, ob_zns = detect_order_blocks(df_chart)
        liq_zns   = detect_liquidity_zones(df_chart)
        src       = _last_data_source.get(cfg["interval"], "yfinance")
        return jsonify({"candles": candles, "sr_levels": sr, "channel": ch,
                        "lp_markers": markers, "ob_zones": ob_zns,
                        "liq_zones": liq_zns,
                        "ohlcv_source": src, "bar_count": len(df_chart)})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/backtest")
def api_backtest():
    """バックテスト結果（標準: 6h キャッシュ、スキャル: 1h キャッシュ）
    ?mode=scalp&tf=5m でスキャル専用バックテストを返す。
    """
    try:
        mode = request.args.get("mode", "standard")
        if mode == "scalp":
            tf       = request.args.get("tf", "5m")
            interval = "15m" if tf == "15m" else "5m"
            result   = run_scalp_backtest("USDJPY=X", lookback_days=30, interval=interval)
        else:
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
