"""
FX AI Trader  —  USD/JPY Day Trading Signal Dashboard
======================================================
v2: Multi-timeframe · S/R horizontal lines · Parallel channel
"""

from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import warnings
warnings.filterwarnings("ignore")

# Technical Analysis
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

# Machine Learning
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

# ML cache keyed by timeframe
_model_cache: dict = {}


# ═══════════════════════════════════════════════════════
#  Data fetching & resampling
# ═══════════════════════════════════════════════════════
def fetch_ohlcv(symbol: str = "USDJPY=X",
                period: str = "5d",
                interval: str = "1m") -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC")
    return df.dropna()


def resample_df(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return df.resample(rule).agg(
        Open=("Open", "first"), High=("High", "max"),
        Low=("Low", "min"),   Close=("Close", "last"),
        Volume=("Volume", "sum")
    ).dropna()


# ═══════════════════════════════════════════════════════
#  Technical indicators
# ═══════════════════════════════════════════════════════
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c, h, l = df["Close"], df["High"], df["Low"]

    df["ema9"]      = EMAIndicator(c, window=9).ema_indicator()
    df["ema21"]     = EMAIndicator(c, window=21).ema_indicator()
    df["ema50"]     = EMAIndicator(c, window=50).ema_indicator()
    df["rsi"]       = RSIIndicator(c, window=14).rsi()

    m               = MACD(c, window_slow=26, window_fast=12, window_sign=9)
    df["macd"]      = m.macd()
    df["macd_sig"]  = m.macd_signal()
    df["macd_hist"] = m.macd_diff()

    bb              = BollingerBands(c, window=20, window_dev=2)
    df["bb_upper"]  = bb.bollinger_hband()
    df["bb_mid"]    = bb.bollinger_mavg()
    df["bb_lower"]  = bb.bollinger_lband()
    df["bb_pband"]  = bb.bollinger_pband()

    df["atr"]       = AverageTrueRange(h, l, c, window=14).average_true_range()
    return df.dropna()


# ═══════════════════════════════════════════════════════
#  Support / Resistance horizontal lines
# ═══════════════════════════════════════════════════════
def find_sr_levels(df: pd.DataFrame,
                   window: int = 5,
                   tolerance_pct: float = 0.003,
                   min_touches: int = 2,
                   max_levels: int = 10) -> list:
    """
    Detect horizontal S/R levels by clustering swing highs & lows.
    Returns a list of price levels sorted by touch-count (strongest first).
    """
    H = df["High"].values
    L = df["Low"].values
    n = len(df)

    swing_pts = []
    for i in range(window, n - window):
        if H[i] == H[i - window: i + window + 1].max():
            swing_pts.append(float(H[i]))
        if L[i] == L[i - window: i + window + 1].min():
            swing_pts.append(float(L[i]))

    if not swing_pts:
        return []

    swing_pts.sort()
    clusters, cluster = [], [swing_pts[0]]

    for p in swing_pts[1:]:
        if (p - cluster[0]) / cluster[0] <= tolerance_pct:
            cluster.append(p)
        else:
            clusters.append(cluster)
            cluster = [p]
    clusters.append(cluster)

    levels = [
        {"price": round(float(np.median(cl)), 3), "touches": len(cl)}
        for cl in clusters if len(cl) >= min_touches
    ]
    levels.sort(key=lambda x: -x["touches"])
    return [lv["price"] for lv in levels[:max_levels]]


# ═══════════════════════════════════════════════════════
#  Parallel channel (linear-regression)
# ═══════════════════════════════════════════════════════
def find_parallel_channel(df: pd.DataFrame,
                           window: int = 5,
                           lookback: int = 100) -> dict | None:
    """
    Fit a linear-regression parallel channel to recent swing highs / lows.
    Returns {upper, lower, middle} as LightweightCharts line-data arrays
    plus 'trend' ('up' | 'down').
    """
    if len(df) < window * 4:
        return None

    fit_df = df.tail(lookback)
    H, L   = fit_df["High"].values, fit_df["Low"].values
    n      = len(fit_df)

    sh_idx, sl_idx = [], []
    for i in range(window, n - window):
        if H[i] == H[i - window: i + window + 1].max():
            sh_idx.append(i)
        if L[i] == L[i - window: i + window + 1].min():
            sl_idx.append(i)

    if len(sh_idx) < 2 or len(sl_idx) < 2:
        return None

    h_m, h_b = np.polyfit(sh_idx, H[sh_idx], 1)
    l_m, l_b = np.polyfit(sl_idx, L[sl_idx], 1)

    offset     = len(df) - len(fit_df)
    timestamps = [int(ts.timestamp()) for ts in df.index]

    upper, lower, middle = [], [], []
    for j, ts in enumerate(timestamps):
        i     = j - offset
        h_val = round(float(h_m * i + h_b), 3)
        l_val = round(float(l_m * i + l_b), 3)
        m_val = round((h_val + l_val) / 2, 3)
        upper .append({"time": ts, "value": h_val})
        lower .append({"time": ts, "value": l_val})
        middle.append({"time": ts, "value": m_val})

    avg_slope = (h_m + l_m) / 2
    return {
        "upper":  upper,
        "lower":  lower,
        "middle": middle,
        "trend":  "up" if avg_slope > 0 else "down",
    }


# ═══════════════════════════════════════════════════════
#  ML feature engineering
# ═══════════════════════════════════════════════════════
def make_features(df: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=df.index)
    f["ema9_ratio"]     = df["Close"] / df["ema9"]  - 1
    f["ema21_ratio"]    = df["Close"] / df["ema21"] - 1
    f["ema50_ratio"]    = df["Close"] / df["ema50"] - 1
    f["ema9_21_cross"]  = df["ema9"]  / df["ema21"] - 1
    f["ema21_50_cross"] = df["ema21"] / df["ema50"] - 1
    f["rsi_norm"]       = df["rsi"] / 100
    f["rsi_ob"]         = (df["rsi"] > 70).astype(float)
    f["rsi_os"]         = (df["rsi"] < 30).astype(float)
    f["macd_hist_norm"] = df["macd_hist"] / df["atr"].replace(0, np.nan)
    f["bb_pband"]       = df["bb_pband"]
    f["ret1"]           = df["Close"].pct_change(1)
    f["ret5"]           = df["Close"].pct_change(5)
    f["ret10"]          = df["Close"].pct_change(10)
    return f.dropna()


# ═══════════════════════════════════════════════════════
#  ML model training (one model per timeframe, hourly data)
# ═══════════════════════════════════════════════════════
def get_cache(tf: str) -> dict:
    if tf not in _model_cache:
        _model_cache[tf] = {"model": None, "scaler": None, "trained_at": None}
    return _model_cache[tf]


def train_model_if_needed(tf: str = "1m"):
    cache = get_cache(tf)
    now   = datetime.now()
    if cache["trained_at"] and (now - cache["trained_at"]).total_seconds() < 3600:
        return
    try:
        df_t = fetch_ohlcv("USDJPY=X", period="60d", interval="1h")
        df_t = add_indicators(df_t)
        feats  = make_features(df_t)
        labels = (df_t["Close"].shift(-1) > df_t["Close"]).astype(int)
        idx    = feats.index.intersection(labels.dropna().index)
        X, y   = feats.loc[idx], labels.loc[idx]
        if len(X) < 100:
            return
        sc  = StandardScaler()
        Xs  = sc.fit_transform(X)
        clf = RandomForestClassifier(
            n_estimators=200, max_depth=6,
            min_samples_leaf=5, random_state=42, n_jobs=-1
        )
        clf.fit(Xs, y)
        cache["model"], cache["scaler"], cache["trained_at"] = clf, sc, now
        print(f"[ML] {tf} trained — {len(X)} samples")
    except Exception as e:
        print(f"[ML] Training error: {e}")


# ═══════════════════════════════════════════════════════
#  Rule-based signal
# ═══════════════════════════════════════════════════════
def rule_signal(row: pd.Series):
    score, reasons = 0.0, []

    # ── EMA trend ──────────────────────────────────
    if row["Close"] > row["ema9"] > row["ema21"] > row["ema50"]:
        score += 2.0; reasons.append("✅ 強気トレンド：EMA9 > EMA21 > EMA50")
    elif row["Close"] < row["ema9"] < row["ema21"] < row["ema50"]:
        score -= 2.0; reasons.append("🔻 弱気トレンド：EMA9 < EMA21 < EMA50")
    elif row["Close"] > row["ema21"]:
        score += 0.8; reasons.append("↗ 中期上昇（EMA21上）")
    elif row["Close"] < row["ema21"]:
        score -= 0.8; reasons.append("↘ 中期下落（EMA21下）")

    # ── RSI ────────────────────────────────────────
    rsi = row["rsi"]
    if   rsi < 25: score += 2.5; reasons.append(f"✅ RSI 極度売られ過ぎ ({rsi:.0f})")
    elif rsi < 35: score += 1.5; reasons.append(f"✅ RSI 売られ過ぎ ({rsi:.0f})")
    elif rsi > 75: score -= 2.5; reasons.append(f"🔻 RSI 極度買われ過ぎ ({rsi:.0f})")
    elif rsi > 65: score -= 1.5; reasons.append(f"🔻 RSI 買われ過ぎ ({rsi:.0f})")

    # ── MACD ───────────────────────────────────────
    if   row["macd_hist"] > 0 and row["macd"] > row["macd_sig"]:
        score += 1.5; reasons.append("✅ MACDゴールデンクロス（上昇）")
    elif row["macd_hist"] < 0 and row["macd"] < row["macd_sig"]:
        score -= 1.5; reasons.append("🔻 MACDデッドクロス（下降）")
    elif row["macd_hist"] > 0:
        score += 0.5; reasons.append("↗ MACDヒストグラム正（弱い上昇圧力）")
    elif row["macd_hist"] < 0:
        score -= 0.5; reasons.append("↘ MACDヒストグラム負（弱い下降圧力）")

    # ── Bollinger Bands ────────────────────────────
    bp = row["bb_pband"]
    if   bp < 0.05: score += 2.0; reasons.append("✅ ボリンジャー下限タッチ（反発期待）")
    elif bp < 0.15: score += 1.0; reasons.append("↗ ボリンジャー下限近辺")
    elif bp > 0.95: score -= 2.0; reasons.append("🔻 ボリンジャー上限タッチ（反落期待）")
    elif bp > 0.85: score -= 1.0; reasons.append("↘ ボリンジャー上限近辺")

    return score, reasons


def calc_sl_tp(entry: float, signal: str, atr: float):
    if signal == "BUY":
        return round(entry - atr * 1.5, 3), round(entry + atr * 2.5, 3)
    return round(entry + atr * 1.5, 3), round(entry - atr * 2.5, 3)


# ═══════════════════════════════════════════════════════
#  Flask routes
# ═══════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chart")
def api_chart():
    tf  = request.args.get("tf", "1m")
    cfg = TF_CFG.get(tf, TF_CFG["1m"])
    try:
        df = fetch_ohlcv("USDJPY=X", period=cfg["period"], interval=cfg["interval"])
        if cfg["resample"]:
            df = resample_df(df, cfg["resample"])
        df       = add_indicators(df)
        df_chart = df.tail(400)

        sr_levels = find_sr_levels(
            df, window=cfg["sr_w"], tolerance_pct=cfg["sr_tol"]
        )
        channel = find_parallel_channel(
            df_chart, window=cfg["sr_w"], lookback=cfg["ch_lb"]
        )

        candles = []
        for ts, row in df_chart.iterrows():
            t = int(ts.timestamp()) if hasattr(ts, "timestamp") else int(ts)
            candles.append({
                "time":      t,
                "open":      round(float(row["Open"]),  3),
                "high":      round(float(row["High"]),  3),
                "low":       round(float(row["Low"]),   3),
                "close":     round(float(row["Close"]), 3),
                "ema9":      round(float(row["ema9"]),  3),
                "ema21":     round(float(row["ema21"]), 3),
                "ema50":     round(float(row["ema50"]), 3),
                "bb_upper":  round(float(row["bb_upper"]), 3),
                "bb_mid":    round(float(row["bb_mid"]),   3),
                "bb_lower":  round(float(row["bb_lower"]), 3),
                "rsi":       round(float(row["rsi"]),       1),
                "macd":      round(float(row["macd"]),      5),
                "macd_sig":  round(float(row["macd_sig"]),  5),
                "macd_hist": round(float(row["macd_hist"]), 5),
            })

        return jsonify({"candles": candles, "sr_levels": sr_levels, "channel": channel})

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/signal")
def api_signal():
    tf  = request.args.get("tf", "1m")
    cfg = TF_CFG.get(tf, TF_CFG["1m"])
    try:
        train_model_if_needed(tf)
        df = fetch_ohlcv("USDJPY=X", period=cfg["period"], interval=cfg["interval"])
        if cfg["resample"]:
            df = resample_df(df, cfg["resample"])
        df    = add_indicators(df)
        row   = df.iloc[-1]
        entry = float(row["Close"])
        atr   = float(row["atr"])

        rule_score, reasons = rule_signal(row)

        ml_prob = 0.5
        cache   = get_cache(tf)
        if cache["model"] is not None:
            try:
                feats = make_features(df)
                if len(feats) > 0:
                    x  = feats.iloc[-1:].values
                    xs = cache["scaler"].transform(x)
                    ml_prob = float(cache["model"].predict_proba(xs)[0][1])
            except Exception:
                pass

        rule_norm = max(-1.0, min(1.0, rule_score / 8.0))
        combined  = rule_norm * 0.65 + (ml_prob - 0.5) * 2 * 0.35
        THRESHOLD = 0.18

        if   combined >  THRESHOLD: signal, conf = "BUY",  int(min(95, 50 + combined * 56))
        elif combined < -THRESHOLD: signal, conf = "SELL", int(min(95, 50 + abs(combined) * 56))
        else:                       signal, conf = "WAIT", int(max(30, 50 - abs(combined) * 30))

        sl, tp = calc_sl_tp(entry, signal if signal != "WAIT" else "BUY", atr)
        rr     = round(abs(tp - entry) / max(abs(sl - entry), 1e-6), 2)
        ts_str = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)

        return jsonify({
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
            "indicators": {
                "ema9":      round(float(row["ema9"]),  3),
                "ema21":     round(float(row["ema21"]), 3),
                "ema50":     round(float(row["ema50"]), 3),
                "rsi":       round(float(row["rsi"]),   1),
                "macd":      round(float(row["macd"]),      5),
                "macd_sig":  round(float(row["macd_sig"]),  5),
                "macd_hist": round(float(row["macd_hist"]), 5),
                "bb_upper":  round(float(row["bb_upper"]), 3),
                "bb_mid":    round(float(row["bb_mid"]),   3),
                "bb_lower":  round(float(row["bb_lower"]), 3),
                "bb_pband":  round(float(row["bb_pband"]), 3),
            },
            "reasons":    reasons,
            "ml_prob":    round(ml_prob * 100, 1),
            "rule_score": round(rule_score, 2),
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("  FX AI Trader  —  USD/JPY Multi-TF Dashboard")
    print(f"  http://localhost:{port}")
    print("=" * 50)
    app.run(debug=False, port=port, host="0.0.0.0")
