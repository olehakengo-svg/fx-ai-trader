"""
FX AI Trader - USD/JPY Day Trading Signal Dashboard
====================================================
Flask backend: data fetching, technical indicators, AI signal generation
"""

from flask import Flask, render_template, jsonify
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

# Technical Analysis
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands, AverageTrueRange

# Machine Learning
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

app = Flask(__name__)

# ─────────────────────────────────────────────────
# Global model cache (retrain every hour)
# ─────────────────────────────────────────────────
_model_cache = {
    "model": None,
    "scaler": None,
    "trained_at": None,
}


# ─────────────────────────────────────────────────
# Data fetching
# ─────────────────────────────────────────────────
def fetch_ohlcv(symbol: str = "USDJPY=X", period: str = "5d", interval: str = "1m") -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    if df.index.tz is not None:
        df.index = df.index.tz_convert("UTC")
    return df.dropna()


# ─────────────────────────────────────────────────
# Indicator calculation
# ─────────────────────────────────────────────────
def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]

    # EMA
    df["ema9"]  = EMAIndicator(close, window=9).ema_indicator()
    df["ema21"] = EMAIndicator(close, window=21).ema_indicator()
    df["ema50"] = EMAIndicator(close, window=50).ema_indicator()

    # RSI
    df["rsi"] = RSIIndicator(close, window=14).rsi()

    # MACD
    macd_obj       = MACD(close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"]     = macd_obj.macd()
    df["macd_sig"] = macd_obj.macd_signal()
    df["macd_hist"]= macd_obj.macd_diff()

    # Bollinger Bands
    bb_obj        = BollingerBands(close, window=20, window_dev=2)
    df["bb_upper"]= bb_obj.bollinger_hband()
    df["bb_mid"]  = bb_obj.bollinger_mavg()
    df["bb_lower"]= bb_obj.bollinger_lband()
    df["bb_pband"]= bb_obj.bollinger_pband()   # %B: 0=lower, 1=upper

    # ATR
    df["atr"] = AverageTrueRange(high, low, close, window=14).average_true_range()

    return df.dropna()


# ─────────────────────────────────────────────────
# Feature engineering for ML
# ─────────────────────────────────────────────────
FEATURE_COLS = [
    "ema9_ratio", "ema21_ratio", "ema50_ratio",
    "ema9_21_cross", "ema21_50_cross",
    "rsi_norm", "rsi_ob", "rsi_os",
    "macd_hist_norm", "bb_pband",
    "ret1", "ret5", "ret10",
]

def make_features(df: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame(index=df.index)
    f["ema9_ratio"]    = df["Close"] / df["ema9"]  - 1
    f["ema21_ratio"]   = df["Close"] / df["ema21"] - 1
    f["ema50_ratio"]   = df["Close"] / df["ema50"] - 1
    f["ema9_21_cross"] = df["ema9"]  / df["ema21"] - 1
    f["ema21_50_cross"]= df["ema21"] / df["ema50"] - 1
    f["rsi_norm"]      = df["rsi"] / 100
    f["rsi_ob"]        = (df["rsi"] > 70).astype(float)
    f["rsi_os"]        = (df["rsi"] < 30).astype(float)
    f["macd_hist_norm"]= df["macd_hist"] / df["atr"].replace(0, np.nan)
    f["bb_pband"]      = df["bb_pband"]
    f["ret1"]          = df["Close"].pct_change(1)
    f["ret5"]          = df["Close"].pct_change(5)
    f["ret10"]         = df["Close"].pct_change(10)
    return f.dropna()


# ─────────────────────────────────────────────────
# ML: train Random Forest on hourly data
# ─────────────────────────────────────────────────
def train_model_if_needed():
    now = datetime.now()
    trained_at = _model_cache["trained_at"]
    if trained_at and (now - trained_at).total_seconds() < 3600:
        return  # still fresh

    try:
        df_h = yf.Ticker("USDJPY=X").history(period="60d", interval="1h", auto_adjust=True)
        df_h = add_indicators(df_h)
        feats  = make_features(df_h)
        labels = (df_h["Close"].shift(-1) > df_h["Close"]).astype(int)

        idx = feats.index.intersection(labels.dropna().index)
        X, y = feats.loc[idx], labels.loc[idx]
        if len(X) < 100:
            return

        sc = StandardScaler()
        Xs = sc.fit_transform(X)

        clf = RandomForestClassifier(
            n_estimators=200, max_depth=6,
            min_samples_leaf=5, random_state=42, n_jobs=-1
        )
        clf.fit(Xs, y)

        _model_cache["model"]      = clf
        _model_cache["scaler"]     = sc
        _model_cache["trained_at"] = now
        print(f"[ML] Model retrained at {now.strftime('%H:%M:%S')} with {len(X)} samples")

    except Exception as e:
        print(f"[ML] Training error: {e}")


# ─────────────────────────────────────────────────
# Rule-based signal scoring
# ─────────────────────────────────────────────────
def rule_signal(row: pd.Series):
    score   = 0.0
    reasons = []

    # ── EMA trend alignment ──────────────────────
    if row["Close"] > row["ema9"] > row["ema21"] > row["ema50"]:
        score += 2.0
        reasons.append("✅ 強気トレンド：EMA9 > EMA21 > EMA50")
    elif row["Close"] < row["ema9"] < row["ema21"] < row["ema50"]:
        score -= 2.0
        reasons.append("🔻 弱気トレンド：EMA9 < EMA21 < EMA50")
    elif row["Close"] > row["ema21"]:
        score += 0.8
        reasons.append("↗ 中期上昇（EMA21上）")
    elif row["Close"] < row["ema21"]:
        score -= 0.8
        reasons.append("↘ 中期下落（EMA21下）")

    # ── RSI ─────────────────────────────────────
    rsi = row["rsi"]
    if rsi < 25:
        score += 2.5
        reasons.append(f"✅ RSI 極度売られ過ぎ ({rsi:.0f})")
    elif rsi < 35:
        score += 1.5
        reasons.append(f"✅ RSI 売られ過ぎ ({rsi:.0f})")
    elif rsi > 75:
        score -= 2.5
        reasons.append(f"🔻 RSI 極度買われ過ぎ ({rsi:.0f})")
    elif rsi > 65:
        score -= 1.5
        reasons.append(f"🔻 RSI 買われ過ぎ ({rsi:.0f})")

    # ── MACD ────────────────────────────────────
    if row["macd_hist"] > 0 and row["macd"] > row["macd_sig"]:
        score += 1.5
        reasons.append("✅ MACDゴールデンクロス（上昇モメンタム）")
    elif row["macd_hist"] < 0 and row["macd"] < row["macd_sig"]:
        score -= 1.5
        reasons.append("🔻 MACDデッドクロス（下降モメンタム）")
    elif row["macd_hist"] > 0:
        score += 0.5
        reasons.append("↗ MACDヒストグラム正（弱い上昇圧力）")
    elif row["macd_hist"] < 0:
        score -= 0.5
        reasons.append("↘ MACDヒストグラム負（弱い下降圧力）")

    # ── Bollinger Bands ──────────────────────────
    bp = row["bb_pband"]
    if bp < 0.05:
        score += 2.0
        reasons.append("✅ ボリンジャー下限バンドタッチ（反発期待）")
    elif bp < 0.15:
        score += 1.0
        reasons.append("↗ ボリンジャー下限バンド近辺")
    elif bp > 0.95:
        score -= 2.0
        reasons.append("🔻 ボリンジャー上限バンドタッチ（反落期待）")
    elif bp > 0.85:
        score -= 1.0
        reasons.append("↘ ボリンジャー上限バンド近辺")

    return score, reasons


# ─────────────────────────────────────────────────
# SL / TP calculation based on ATR
# ─────────────────────────────────────────────────
def calc_sl_tp(entry: float, signal: str, atr: float):
    sl_mult = 1.5
    tp_mult = 2.5
    if signal == "BUY":
        return round(entry - atr * sl_mult, 3), round(entry + atr * tp_mult, 3)
    else:  # SELL
        return round(entry + atr * sl_mult, 3), round(entry - atr * tp_mult, 3)


# ─────────────────────────────────────────────────
# Flask routes
# ─────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/signal")
def api_signal():
    try:
        train_model_if_needed()

        df = fetch_ohlcv("USDJPY=X", period="5d", interval="1m")
        df = add_indicators(df)

        row   = df.iloc[-1]
        entry = float(row["Close"])
        atr   = float(row["atr"])

        # Rule-based score
        rule_score, reasons = rule_signal(row)

        # ML probability (BUY direction)
        ml_prob = 0.5
        if _model_cache["model"] is not None:
            try:
                feats = make_features(df)
                if len(feats) > 0:
                    x  = feats.iloc[-1:].values
                    xs = _model_cache["scaler"].transform(x)
                    ml_prob = float(_model_cache["model"].predict_proba(xs)[0][1])
            except Exception:
                pass

        # Combine: 65% rule, 35% ML
        rule_norm = max(-1.0, min(1.0, rule_score / 8.0))
        combined  = rule_norm * 0.65 + (ml_prob - 0.5) * 2 * 0.35

        THRESHOLD = 0.18
        if combined > THRESHOLD:
            signal = "BUY"
            conf   = int(min(95, 50 + combined * 56))
        elif combined < -THRESHOLD:
            signal = "SELL"
            conf   = int(min(95, 50 + abs(combined) * 56))
        else:
            signal = "WAIT"
            conf   = int(max(30, 50 - abs(combined) * 30))

        sl, tp = calc_sl_tp(entry, signal if signal != "WAIT" else "BUY", atr)
        rr     = round(abs(tp - entry) / max(abs(sl - entry), 1e-6), 2)

        ts_str = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)

        return jsonify({
            "timestamp": ts_str,
            "symbol":    "USD/JPY",
            "entry":     round(entry, 3),
            "signal":    signal,
            "confidence":conf,
            "sl":        sl,
            "tp":        tp,
            "rr_ratio":  rr,
            "atr":       round(atr, 3),
            "indicators": {
                "ema9":       round(float(row["ema9"]),  3),
                "ema21":      round(float(row["ema21"]), 3),
                "ema50":      round(float(row["ema50"]), 3),
                "rsi":        round(float(row["rsi"]),   1),
                "macd":       round(float(row["macd"]),  5),
                "macd_sig":   round(float(row["macd_sig"]),  5),
                "macd_hist":  round(float(row["macd_hist"]), 5),
                "bb_upper":   round(float(row["bb_upper"]), 3),
                "bb_mid":     round(float(row["bb_mid"]),   3),
                "bb_lower":   round(float(row["bb_lower"]), 3),
                "bb_pband":   round(float(row["bb_pband"]), 3),
            },
            "reasons":   reasons,
            "ml_prob":   round(ml_prob * 100, 1),
            "rule_score":round(rule_score, 2),
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/chart")
def api_chart():
    try:
        df = fetch_ohlcv("USDJPY=X", period="5d", interval="1m")
        df = add_indicators(df)
        df = df.tail(400)

        candles = []
        for ts, row in df.iterrows():
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
                "rsi":       round(float(row["rsi"]), 1),
                "macd":      round(float(row["macd"]),      5),
                "macd_sig":  round(float(row["macd_sig"]),  5),
                "macd_hist": round(float(row["macd_hist"]), 5),
            })

        return jsonify(candles)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("  FX AI Trader - USD/JPY Day Trading Dashboard")
    print(f"  http://localhost:{port}")
    print("=" * 50)
    app.run(debug=False, port=port, host="0.0.0.0")
