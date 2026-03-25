"""
FX AI Trader — Technical indicators module
=============================================
Core indicator calculations, candlestick patterns, Dow theory,
volume/OBV analysis, divergence detection, S/R levels,
Fibonacci retracements, and order block detection.
"""

import pandas as pd
import numpy as np

from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange


# ═══════════════════════════════════════════════════════
#  Core Indicators
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
    df["rsi9"]      = RSIIndicator(c, window=9).rsi()   # 5m最適バランス (Axiory研究)
    df["atr7"]      = AverageTrueRange(h, l, c, window=7).average_true_range()
    stoch = StochasticOscillator(h, l, c, window=5, smooth_window=3)
    df["stoch_k"]   = stoch.stoch()
    df["stoch_d"]   = stoch.stoch_signal()
    # BBバンド幅（スクイーズ検出用）
    df["bb_width"]  = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"].replace(0, np.nan)
    # デイトレード / スイング用追加指標
    df["ema100"]    = EMAIndicator(c, window=100).ema_indicator()
    df["ema200"]    = EMAIndicator(c, window=200).ema_indicator()
    adx_ind = ADXIndicator(h, l, c, window=14)
    df["adx"]       = adx_ind.adx()
    df["adx_pos"]   = adx_ind.adx_pos()   # +DI
    df["adx_neg"]   = adx_ind.adx_neg()   # -DI
    # ドンチアンチャネル20本 (Brock, Lakonishok, LeBaron 1992 JoF)
    df["don_high20"] = df["High"].rolling(20).max()
    df["don_low20"]  = df["Low"].rolling(20).min()
    df["don_mid20"]  = (df["don_high20"] + df["don_low20"]) / 2
    # ドンチアン位置 (0=下限付近, 1=上限付近)
    don_range = (df["don_high20"] - df["don_low20"]).replace(0, np.nan)
    df["don_pct"]    = (c - df["don_low20"]) / don_range
    return df.dropna()


# ═══════════════════════════════════════════════════════
#  Candlestick pattern detection (8 patterns)
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
#  Dow Theory analysis
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
#  Volume / OBV analysis
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
#  RSI / MACD divergence detection
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

    # -- Price swing points in the recent half --
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
#  S/R levels
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


def find_sr_levels_weighted(df, window=5, tolerance_pct=0.003, min_touches=2,
                            max_levels=10, bars_per_day=288):
    """
    SR水平線の強度スコアリング版。
    Returns list of dicts:
    {
        "price": float,        # SR価格
        "touches": int,        # タッチ回数
        "days_span": float,    # 最初のタッチから最後のタッチまでの日数
        "strength": float,     # 0-1 正規化スコア
        "is_strong": bool,     # strength >= 0.6
        "type": str,           # "support" | "resistance" | "both"
    }

    Strength scoring:
    - touches weight: 40%  (normalized: touches / max_touches)
    - days_span weight: 35% (normalized: span / max_span)
    - recency weight: 25%  (normalized: recency_score)
    """
    H, L, n = df["High"].values, df["Low"].values, len(df)
    # Collect pivot points with bar indices and source (high/low)
    pts = []  # (price, bar_index, source)  source: "H" or "L"
    for i in range(window, n - window):
        if H[i] == H[i - window:i + window + 1].max():
            pts.append((float(H[i]), i, "H"))
        if L[i] == L[i - window:i + window + 1].min():
            pts.append((float(L[i]), i, "L"))
    if not pts:
        return []

    # Sort by price for clustering
    pts.sort(key=lambda x: x[0])
    clusters = [[pts[0]]]
    for p in pts[1:]:
        if (p[0] - clusters[-1][0][0]) / clusters[-1][0][0] <= tolerance_pct:
            clusters[-1].append(p)
        else:
            clusters.append([p])

    # Build rich SR objects
    results = []
    # Collect all stats first for normalization
    raw_levels = []
    for cl in clusters:
        if len(cl) < min_touches:
            continue
        prices = [x[0] for x in cl]
        indices = [x[1] for x in cl]
        sources = [x[2] for x in cl]
        price = round(float(np.median(prices)), 3)
        touches = len(cl)
        first_idx, last_idx = min(indices), max(indices)
        days_span = (last_idx - first_idx) / max(bars_per_day, 1)
        # Recency: distance of most recent touch from end of data
        recency_bars = n - 1 - last_idx
        # Source type classification
        h_count = sum(1 for s in sources if s == "H")
        l_count = sum(1 for s in sources if s == "L")
        if h_count > l_count * 2:
            sr_type = "resistance"
        elif l_count > h_count * 2:
            sr_type = "support"
        else:
            sr_type = "both"
        raw_levels.append({
            "price": price,
            "touches": touches,
            "days_span": round(days_span, 2),
            "recency_bars": recency_bars,
            "type": sr_type,
        })

    if not raw_levels:
        return []

    # Normalize components 0-1
    max_touches = max(r["touches"] for r in raw_levels)
    max_span = max(r["days_span"] for r in raw_levels) or 1.0
    max_recency = max(r["recency_bars"] for r in raw_levels) or 1.0

    for r in raw_levels:
        t_score = r["touches"] / max_touches if max_touches > 0 else 0
        s_score = r["days_span"] / max_span if max_span > 0 else 0
        # Recency: closer to end = higher score (invert)
        rec_score = 1.0 - (r["recency_bars"] / max_recency) if max_recency > 0 else 0.5
        strength = round(0.40 * t_score + 0.35 * s_score + 0.25 * rec_score, 3)
        results.append({
            "price": r["price"],
            "touches": r["touches"],
            "days_span": r["days_span"],
            "strength": strength,
            "is_strong": strength >= 0.6,
            "type": r["type"],
        })

    # Sort by strength descending, limit to max_levels
    results.sort(key=lambda x: -x["strength"])
    return results[:max_levels]


# ═══════════════════════════════════════════════════════
#  Fibonacci retracement levels
# ═══════════════════════════════════════════════════════
def _calc_fibonacci_levels(df: pd.DataFrame, lookback: int = 60) -> dict:
    """
    直近スイング高値・安値からフィボナッチリトレースメントレベルを算出。
    Returns: {swing_high, swing_low, r236, r382, r500, r618, r786, trend}
    """
    try:
        sub = df.tail(lookback)
        H, L = sub["High"].values, sub["Low"].values
        swing_high = float(np.max(H))
        swing_low  = float(np.min(L))
        rng = swing_high - swing_low
        if rng < 1e-6:
            return {}
        # 直近の方向を判定（後半50本の移動で判断）
        mid = len(sub) // 2
        trend = "up" if float(sub["Close"].iloc[-1]) > float(sub["Close"].iloc[mid]) else "down"
        if trend == "up":
            # 上昇中: 押し目=swing_highからの下落%
            return {
                "swing_high": round(swing_high, 3),
                "swing_low":  round(swing_low,  3),
                "r236": round(swing_high - rng * 0.236, 3),
                "r382": round(swing_high - rng * 0.382, 3),
                "r500": round(swing_high - rng * 0.500, 3),
                "r618": round(swing_high - rng * 0.618, 3),
                "r786": round(swing_high - rng * 0.786, 3),
                "trend": "up",
            }
        else:
            # 下降中: 戻り=swing_lowからの上昇%
            return {
                "swing_high": round(swing_high, 3),
                "swing_low":  round(swing_low,  3),
                "r236": round(swing_low + rng * 0.236, 3),
                "r382": round(swing_low + rng * 0.382, 3),
                "r500": round(swing_low + rng * 0.500, 3),
                "r618": round(swing_low + rng * 0.618, 3),
                "r786": round(swing_low + rng * 0.786, 3),
                "trend": "down",
            }
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════
#  SMC Order Block detection
# ═══════════════════════════════════════════════════════
def detect_order_blocks(df: pd.DataFrame, atr_mult: float = 1.5,
                        lookback: int = 80) -> tuple:
    """
    SMC Order Block:
    - Bull OB: 強気インパルス直前の最後の陰線 -> サポートゾーン
    - Bear OB: 弱気インパルス直前の最後の陽線 -> レジスタンスゾーン
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
            if closes[i] < opens[i]:         # 直前陰線 -> Bull OB
                ob_zones.append({"type": "bull",
                    "high": round(float(highs[i]), 3),
                    "low":  round(float(lows[i]),  3),
                    "time": t, "label": "🟩 Bull OB"})
        elif closes[imp_i] < opens[imp_i]:  # 弱気インパルス
            if closes[i] > opens[i]:         # 直前陽線 -> Bear OB
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
