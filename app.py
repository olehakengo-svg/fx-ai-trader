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

from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

# ML imports
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit
    import pickle
    _ML_AVAILABLE = True
except ImportError:
    _ML_AVAILABLE = False

app = Flask(__name__)

# ═══════════════════════════════════════════════════════
#  Module imports (refactored)
# ═══════════════════════════════════════════════════════
from modules.config import (
    TF_CFG, STRATEGY_MODE, STRATEGY_PROFILES, HOUR_DIRECTION_BIAS,
    AGENT_MISSION, MTF_HIGHER, TF_SL_MULT, TF_TP_MULT, TF_MIN_RR,
    CACHE_TTL, BT_CACHE_TTL, NEWS_TTL, CALENDAR_TTL, MASTER_BIAS_TTL,
    SCALP_BT_TTL, DT_BT_TTL,
)
from modules.data import (
    fetch_ohlcv, resample_df, _fetch_raw,
    fetch_ohlcv_twelvedata, fetch_ohlcv_massive, _rt_patch,
    _data_cache, _last_data_source, _price_cache,
    _TD_SYMBOL_MAP, _TD_INTERVALS, _TF_CACHE_TTL,
)
from modules.indicators import (
    add_indicators, find_sr_levels, find_sr_levels_weighted,
    detect_order_blocks,
    _calc_fibonacci_levels, detect_candle_patterns,
    dow_theory_analysis, volume_obv_analysis, detect_divergence,
)




_bt_cache:    dict = {}  # backtest result cache
_news_cache:  dict = {}  # news sentiment cache


# Layer 0/1 キャッシュ
_calendar_cache:    dict = {}
_master_bias_cache: dict = {}

# ═══════════════════════════════════════════════════════
#  Performance Monitor — KPI追跡 & フィードバックループ
# ═══════════════════════════════════════════════════════
import json as _json
_PERF_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perf_data.json")
_perf_records: list = []   # in-memory store
_PERF_MAX_RECORDS = 1000   # keep last 1000 trades

def _load_perf_data() -> list:
    """ファイルからパフォーマンスデータを読み込む"""
    global _perf_records
    try:
        if os.path.exists(_PERF_FILE):
            with open(_PERF_FILE, "r") as f:
                _perf_records = _json.load(f)
    except Exception:
        _perf_records = []
    return _perf_records

def _save_perf_data():
    """パフォーマンスデータをファイルに保存"""
    try:
        with open(_PERF_FILE, "w") as f:
            _json.dump(_perf_records[-_PERF_MAX_RECORDS:], f)
    except Exception:
        pass

def record_trade_result(
    signal:     str,     # "BUY" | "SELL"
    mode:       str,     # "scalp" | "daytrade"
    tf:         str,     # "5m" | "15m" | "1h" etc.
    outcome:    str,     # "WIN" | "LOSS" | "BREAKEVEN"
    rr_ratio:   float,   # risk-reward ratio (e.g. 1.5)
    entry:      float,
    exit_price: float,
    sl:         float,
    tp:         float,
    confidence: int,     # 0-100
    layer1_dir: str = "neutral",  # "bull" | "bear" | "neutral"
    regime:     str = "UNKNOWN",
) -> dict:
    """
    1トレードの結果を記録する。
    outcome="WIN" → R倍 = rr_ratio
    outcome="LOSS" → R倍 = -1.0
    outcome="BREAKEVEN" → R倍 = 0.0
    """
    global _perf_records
    r_multiple = rr_ratio if outcome == "WIN" else (-1.0 if outcome == "LOSS" else 0.0)
    record = {
        "ts":         datetime.now(timezone.utc).isoformat(),
        "signal":     signal,
        "mode":       mode,
        "tf":         tf,
        "outcome":    outcome,
        "r_multiple": round(r_multiple, 3),
        "rr_ratio":   round(rr_ratio, 3),
        "entry":      round(entry, 3),
        "exit_price": round(exit_price, 3),
        "sl":         round(sl, 3),
        "tp":         round(tp, 3),
        "confidence": confidence,
        "layer1_dir": layer1_dir,
        "regime":     regime,
    }
    _perf_records.append(record)
    if len(_perf_records) > _PERF_MAX_RECORDS:
        _perf_records = _perf_records[-_PERF_MAX_RECORDS:]
    _save_perf_data()
    return record

def compute_kpi(records: list) -> dict:
    """
    KPIを計算する。
    勝率, 期待値, Sharpe比, 最大ドローダウン, 日次取引回数
    """
    if not records:
        return {
            "total_trades": 0, "win_rate": 0.0, "ev_per_trade": 0.0,
            "sharpe": 0.0, "max_dd_pct": 0.0,
            "avg_rr": 0.0, "daily_trade_rate": 0.0,
            "kpi_pass": {"win_rate": False, "ev": False, "sharpe": False, "max_dd": False},
        }

    r_list = [r["r_multiple"] for r in records]
    outcomes = [r["outcome"] for r in records]
    n = len(records)

    wins  = outcomes.count("WIN")
    win_rate = wins / n * 100
    ev   = sum(r_list) / n

    # Sharpe (annualized, assume daily trades → 252 periods)
    if n >= 2:
        std_r = float(np.std(r_list))
        sharpe = (ev / std_r * np.sqrt(252)) if std_r > 0 else 0.0
    else:
        sharpe = 0.0

    # Max drawdown in R
    equity = 0.0
    peak   = 0.0
    max_dd = 0.0
    for r in r_list:
        equity += r
        if equity > peak: peak = equity
        dd = peak - equity
        if dd > max_dd: max_dd = dd
    # Express as % of peak (or as R if peak=0)
    max_dd_pct = (max_dd / max(abs(peak), 1.0)) * 100 if peak > 0 else max_dd * 10

    # Daily trade rate
    if n >= 2:
        try:
            first_ts = datetime.fromisoformat(records[0]["ts"])
            last_ts  = datetime.fromisoformat(records[-1]["ts"])
            days_elapsed = max(1, (last_ts - first_ts).total_seconds() / 86400)
            daily_rate = n / days_elapsed
        except Exception:
            daily_rate = 0.0
    else:
        daily_rate = 0.0

    # KPI pass/fail vs active strategy profile targets
    profile = STRATEGY_PROFILES.get(STRATEGY_MODE, STRATEGY_PROFILES["A"])
    kpi_pass = {
        "win_rate": win_rate >= profile["kpi_wr"] * 100,
        "ev":       ev       >= profile["kpi_ev"],
        "sharpe":   sharpe   >= profile["kpi_sharpe"],
        "max_dd":   max_dd_pct <= profile["kpi_maxdd"] * 100,
    }

    return {
        "total_trades":   n,
        "win_rate":       round(win_rate, 1),
        "ev_per_trade":   round(ev, 4),
        "sharpe":         round(sharpe, 2),
        "max_dd_pct":     round(max_dd_pct, 1),
        "avg_rr":         round(sum(r["rr_ratio"] for r in records) / n, 2),
        "daily_trade_rate": round(daily_rate, 1),
        "kpi_pass":       kpi_pass,
        "all_pass":       all(kpi_pass.values()),
    }

# 起動時にデータ読み込み
_load_perf_data()




# ═══════════════════════════════════════════════════════
#  Layer 0: 取引禁止条件チェック
# ═══════════════════════════════════════════════════════
def get_economic_calendar() -> list:
    """
    ForexFactory カレンダーから今週の高インパクト USD/JPY 指標を取得。
    1時間キャッシュ。失敗時は空リストを返す（取引は停止しない）。
    """
    global _calendar_cache
    now = datetime.now()
    if _calendar_cache.get("ts") and (now - _calendar_cache["ts"]).total_seconds() < CALENDAR_TTL:
        return _calendar_cache.get("events", [])

    import urllib.request as _ur, json as _js
    events = []
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with _ur.urlopen(req, timeout=8) as r:
            data = _js.load(r)
        for ev in data:
            if ev.get("impact") == "High" and ev.get("currency") in ("USD", "JPY"):
                events.append({
                    "title":    ev.get("title", ""),
                    "currency": ev.get("currency", ""),
                    "date":     ev.get("date", ""),
                    "impact":   "High",
                })
        print(f"[Calendar] {len(events)}件の高インパクト指標取得")
    except Exception as e:
        print(f"[Calendar] {e}")

    _calendar_cache = {"events": events, "ts": now}
    return events


def is_trade_prohibited(df=None, bar_time=None) -> dict:
    """
    Layer 0: 取引禁止条件チェック

    禁止条件:
      ① 低流動性セッション (22:00-07:00 UTC)
      ② 重要経済指標の前後30分 (USD/JPY 高インパクト)
      ③ 異常ボラティリティ (現在ATR > 20期間平均の2.5倍)

    Args:
      bar_time: BT用 — バーのタイムスタンプ（Noneなら現在時刻）
    Returns:
      {"prohibited": bool, "reason": str, "layer": 0, ...}
    """
    now_utc  = bar_time if bar_time else datetime.now(timezone.utc)
    if hasattr(now_utc, 'tzinfo') and now_utc.tzinfo is None:
        from datetime import timezone as _tz
        now_utc = now_utc.replace(tzinfo=_tz.utc)
    hour_utc = now_utc.hour

    # ① 低流動性セッション
    # 22:00-23:59 UTC: 深夜 — 出来高不足で取引禁止
    # 00:00-06:59 UTC: 東京セッション — 平均回帰戦略で稼働
    if hour_utc >= 22:
        return {
            "prohibited": True,
            "reason":     f"🌙 深夜セッション ({hour_utc:02d}:00 UTC) — 出来高不足",
            "layer": 0, "check": "session",
        }
    if hour_utc < 7:
        # 東京セッション: 取引は許可、専用戦略で稼働
        # (経済指標・異常ボラチェックは引き続き下で実施)
        tokyo_result = {
            "prohibited": False,
            "tokyo_mode": True,
            "reason": "🏯 東京セッション — 平均回帰戦略で稼働中",
            "layer": 0, "check": "session",
        }

    # ② 経済指標チェック (±30分) — BT時はスキップ
    if bar_time is None:
        try:
            events = get_economic_calendar()
            for ev in events:
                try:
                    ev_dt = datetime.fromisoformat(
                        ev["date"].replace("Z", "+00:00")
                    ).astimezone(timezone.utc)
                    diff_min = (ev_dt - now_utc).total_seconds() / 60
                    if -30 <= diff_min <= 30:
                        sign = "前" if diff_min > 0 else "後"
                        return {
                            "prohibited": True,
                            "reason":     f"⚠️ 重要指標{sign}{abs(diff_min):.0f}分: {ev['currency']} {ev['title']}",
                            "layer": 0, "check": "event", "event": ev,
                        }
                except Exception:
                    continue
        except Exception as e:
            print(f"[Layer0/Calendar] {e}")

    # ③ 異常ボラティリティ
    if df is not None and "atr" in df.columns and len(df) >= 20:
        try:
            atr_cur = float(df["atr"].iloc[-1])
            atr_avg = float(df["atr"].tail(20).mean())
            if atr_avg > 0 and atr_cur > atr_avg * 2.5:
                ratio = round(atr_cur / atr_avg, 1)
                return {
                    "prohibited": True,
                    "reason":     f"🌪️ 異常ボラティリティ (ATR = 平均の{ratio}倍) — 正常化まで待機",
                    "layer": 0, "check": "volatility", "atr_ratio": ratio,
                }
        except Exception:
            pass

    # 東京セッション中なら tokyo_mode フラグ付きで返す
    if hour_utc < 7:
        return tokyo_result

    return {"prohibited": False, "reason": "", "layer": 0, "check": "ok"}


# ═══════════════════════════════════════════════════════
#  Layer 1: 大口バイアス判定 — MASTER FILTER
# ═══════════════════════════════════════════════════════
def get_master_bias(symbol: str) -> dict:
    """
    Layer 1: 大口（機関投資家）フロー方向をマスターフィルターとして判定。

    3つの大口指標の多数決 (2/3以上一致で方向確定):
      ① 機関フロースコア (JPY先物 + DXY + VIX)
      ② COT大口投機筋ネットポジション (CFTC)
      ③ DXY短期EMAトレンド (ドルインデックス方向)

    direction: "bull" → USD買い優位 (USD/JPY↑)
               "bear" → USD売り優位 (USD/JPY↓)
               "neutral" → 大口方向不一致 → シグナル品質低下

    Returns: {direction, confidence, label, components, votes}
    """
    global _master_bias_cache
    now = datetime.now()
    key = symbol
    cached = _master_bias_cache.get(key)
    if cached and (now - cached["ts"]).total_seconds() < MASTER_BIAS_TTL:
        return cached["data"]

    votes      = []   # +1=bull, -1=bear, 0=neutral
    components = {}

    # ① 機関フロースコア (JPY先物 + DXY + VIX)
    try:
        inst_sc, inst_detail = institutional_flow_score()
        if   inst_sc >  0.2: votes.append(1);  comp_dir = "bull"
        elif inst_sc < -0.2: votes.append(-1); comp_dir = "bear"
        else:                 votes.append(0);  comp_dir = "neutral"
        components["inst"] = {"direction": comp_dir, "score": round(inst_sc, 3),
                              "detail": inst_detail}
    except Exception as e:
        print(f"[MasterBias/inst] {e}")
        votes.append(0)  # データ取得失敗→中立票
        components["inst"] = {"direction": "neutral", "score": 0.0}

    # ② COT大口投機筋ネットポジション
    try:
        cot_sc, cot_detail = fetch_cot_data()
        if   cot_sc >  0.2: votes.append(1);  comp_dir = "bull"
        elif cot_sc < -0.2: votes.append(-1); comp_dir = "bear"
        else:                votes.append(0);  comp_dir = "neutral"
        components["cot"] = {"direction": comp_dir, "score": round(cot_sc, 3),
                             "detail": cot_detail}
    except Exception as e:
        print(f"[MasterBias/cot] {e}")
        votes.append(0)  # データ取得失敗→中立票
        components["cot"] = {"direction": "neutral", "score": 0.0}

    # ③ DXY短期EMAトレンド
    try:
        dxy_df  = fetch_ohlcv("DX-Y.NYB", period="90d", interval="1d")
        if dxy_df is None or len(dxy_df) < 30:
            raise ValueError(f"DXY data insufficient: {len(dxy_df) if dxy_df is not None else 0} rows")
        dxy_df  = add_indicators(dxy_df)
        dxy_row = dxy_df.iloc[-1]
        dxy_c   = float(dxy_row["Close"])
        dxy_e9  = float(dxy_row["ema9"])
        dxy_e21 = float(dxy_row["ema21"])
        if   dxy_c > dxy_e9 > dxy_e21: votes.append(1);  comp_dir = "bull"
        elif dxy_c < dxy_e9 < dxy_e21: votes.append(-1); comp_dir = "bear"
        else:                            votes.append(0);  comp_dir = "neutral"
        components["dxy"] = {"direction": comp_dir, "value": round(dxy_c, 2),
                             "ema9": round(dxy_e9, 2), "ema21": round(dxy_e21, 2)}
    except Exception as e:
        print(f"[MasterBias/dxy] {e}")
        votes.append(0)  # データ取得失敗→中立票
        components["dxy"] = {"direction": "neutral", "value": 0.0}

    # 多数決
    bull_v  = votes.count(1)
    bear_v  = votes.count(-1)
    neut_v  = votes.count(0)
    total   = max(len(votes), 1)

    if bull_v >= 2:
        direction  = "bull"
        confidence = round(bull_v / total, 2)
        label = f"📈 大口バイアス: USD買い優位 ({bull_v}/{total}一致) — BUYシグナル優先"
    elif bear_v >= 2:
        direction  = "bear"
        confidence = round(bear_v / total, 2)
        label = f"📉 大口バイアス: USD売り優位 ({bear_v}/{total}一致) — SELLシグナル優先"
    else:
        direction  = "neutral"
        confidence = 0.0
        label = f"⚖️ 大口バイアス: 方向不一致 ({bull_v}↑/{bear_v}↓/{neut_v}→) — シグナル品質低下"

    data = {
        "direction":  direction,
        "confidence": confidence,
        "label":      label,
        "components": components,
        "votes": {"bull": bull_v, "bear": bear_v, "neutral": neut_v},
    }
    _master_bias_cache[key] = {"data": data, "ts": now}
    return data


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
#  学術根拠S/R: ラウンドナンバー + VPOC + 回帰チャネル
# ═══════════════════════════════════════════════════════

def detect_round_number_sr(price: float, window_pips: float = 200.0) -> list:
    """
    Osler (2000) FRBNY: ラウンドナンバー(XX.00 / XX.50)はUSD/JPYで
    統計的に有意なS/Rとして証明済み。
    理由: 機関投資家の指値/逆指値がXX.00に集中 → 自己実現的S/R
    USD/JPY: 1pip = 0.01円, window_pips=200 → ±2円以内のラウンド
    """
    levels = []
    base = int(price)
    for offset in range(-3, 5):
        for half in [0.00, 0.50]:
            lvl = round((base + offset) + half, 2)
            if abs(lvl - price) <= window_pips * 0.01:  # pips→円変換
                levels.append(lvl)
    return sorted(levels)


def get_volume_poc(df: pd.DataFrame, lookback: int = 200) -> "float | None":
    """
    Volume Point of Control (VPOC) — 機関投資家が最も取引した価格帯。
    学術根拠: Gärtner & Kübler (2016), Czyżewski et al. (2020)
    → VPOCはS/Rとして機能し、価格が近づくと反発/突破で方向性が決まる。
    Price bucketごとの出来高を集計し最大ボリュームの価格を返す。
    """
    if "Volume" not in df.columns:
        return None
    recent = df.tail(lookback).copy()
    if recent["Volume"].sum() == 0:
        return None
    # USD/JPY: 0.05円刻みでバケット化
    recent["bucket"] = (recent["Close"] / 0.05).round() * 0.05
    vol_by_price = recent.groupby("bucket")["Volume"].sum()
    if vol_by_price.empty:
        return None
    return round(float(vol_by_price.idxmax()), 3)


def get_regression_channel(df: pd.DataFrame, lookback: int = 50) -> dict:
    """
    線形回帰チャネル (±2σ) — 統計的チャネル境界。
    学術根拠:
      - Lo, Mamaysky, Wang (2000) JoF: 回帰ベースのチャネルは
        ランダムウォーク仮説に反する有意な予測力を持つ
      - Brock et al. (1992) JoF: チャネル上下限での反転は
        リスク調整後でもプラスのリターン
    ±2σ = 統計的に価格の95%が収まる範囲 → 逸脱は高確率で回帰
    Returns: {score, upper, lower, mid, slope, std}
      score: +1.0=上限(SELL圧力), -1.0=下限(BUY圧力)
    """
    if len(df) < lookback:
        return {"score": 0.0, "upper": None, "lower": None, "mid": None, "slope": 0.0}
    closes = df["Close"].tail(lookback).values.astype(float)
    x      = np.arange(len(closes))
    coeffs = np.polyfit(x, closes, 1)
    mid    = np.polyval(coeffs, x)
    resid  = closes - mid
    std    = float(np.std(resid))
    if std < 1e-8:
        return {"score": 0.0, "upper": None, "lower": None, "mid": None, "slope": 0.0}
    cur_dev = float(resid[-1])
    score   = float(np.clip(cur_dev / (2.0 * std), -1.0, 1.0))
    upper   = round(float(mid[-1]) + 2.0 * std, 3)
    lower   = round(float(mid[-1]) - 2.0 * std, 3)
    return {
        "score":  round(score, 3),
        "upper":  upper,
        "lower":  lower,
        "mid":    round(float(mid[-1]), 3),
        "slope":  round(float(coeffs[0]), 5),   # >0=上昇チャネル, <0=下降チャネル
        "std":    round(std, 4),
        "channel_width_pips": round(4.0 * std / 0.01, 1),  # チャネル幅(pips)
    }




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

    # Ensure minimum SL distance (SRスナップでSLが狭くなりすぎるのを防止)
    _min_sl_dist = atr * sl_mult * 0.6  # SL_MULT の60%を最低保証
    if abs(sl - entry) < _min_sl_dist:
        sl = entry - _min_sl_dist if signal == "BUY" else entry + _min_sl_dist

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
    米日ファンダメンタル総合:
      - ^TNX : 米10年債利回り（上昇=USD強）
      - 米日金利差（US10Y - JP10Y）: 拡大=USD強
      - DXYトレンド: ドル指数の方向（上昇=USD強）
      - VIXリスクセンチメント: 高VIX=円高圧力
      - 経済カレンダー: 今後24h以内の高インパクト指標
    Returns: (score [-1,+1], detail dict)
    """
    detail = {}
    sub_scores = {}

    # ── 1. 米10年債 + 金利差 ──
    try:
        tnx = fetch_ohlcv("^TNX", period="30d", interval="1d")
        us10y      = float(tnx["Close"].iloc[-1])
        us10y_prev = float(tnx["Close"].iloc[-6]) if len(tnx) >= 7 else us10y

        yield_level = max(-1.0, min(1.0, (us10y - 3.0) / 2.0))
        chg = (us10y - us10y_prev) / max(us10y_prev, 1e-4)
        yield_trend = max(-1.0, min(1.0, chg * 20.0))

        jp10y    = fetch_jp10y()
        spread   = us10y - jp10y
        spread_n = max(-1.0, min(1.0, (spread - 2.0) / 2.0))

        rate_sc = yield_level * 0.30 + yield_trend * 0.40 + spread_n * 0.30
        sub_scores["rate"] = round(max(-1.0, min(1.0, rate_sc)), 3)

        detail["us10y"]      = round(us10y, 2)
        detail["jp10y"]      = round(jp10y, 2)
        detail["spread"]     = round(spread, 2)
        # 金利差方向: US10Yの変化方向で近似（JP10Yの変動は相対的に小さい）
        detail["spread_chg"] = "拡大中" if yield_trend > 0.05 else ("縮小中" if yield_trend < -0.05 else "横ばい")
        detail["rate_trend"] = "上昇（USD強）" if yield_trend > 0 else "低下（USD弱）"
    except Exception as e:
        print(f"[FUND/rate] {e}")
        sub_scores["rate"] = 0.0

    # ── 2. DXYトレンド ──
    try:
        dxy = fetch_ohlcv("DX-Y.NYB", period="30d", interval="1d")
        dxy_c    = float(dxy["Close"].iloc[-1])
        dxy_prev = float(dxy["Close"].iloc[-6]) if len(dxy) >= 7 else dxy_c
        dxy_chg  = (dxy_c - dxy_prev) / max(dxy_prev, 1e-4)
        dxy_sc   = max(-1.0, min(1.0, dxy_chg * 15.0))
        sub_scores["dxy"] = round(dxy_sc, 3)
        detail["dxy"]       = round(dxy_c, 2)
        detail["dxy_trend"] = "上昇（USD強）" if dxy_sc > 0.1 else ("下落（USD弱）" if dxy_sc < -0.1 else "横ばい")
    except Exception as e:
        print(f"[FUND/dxy] {e}")
        sub_scores["dxy"] = 0.0

    # ── 3. VIXリスクセンチメント ──
    try:
        vix_df  = fetch_ohlcv("^VIX", period="20d", interval="1d")
        vix_cur = float(vix_df["Close"].iloc[-1])
        vix_sc  = max(-1.0, min(1.0, -(vix_cur - 20.0) / 10.0))
        sub_scores["vix"] = round(vix_sc, 3)
        detail["vix"]        = round(vix_cur, 1)
        detail["vix_regime"] = "リスクオフ（円高圧力）" if vix_cur > 25 else ("リスクオン（円安圧力）" if vix_cur < 15 else "中立")
    except Exception as e:
        print(f"[FUND/vix] {e}")
        sub_scores["vix"] = 0.0

    # ── 4. 経済カレンダー（今後24h） ──
    upcoming_events = []
    try:
        events = get_economic_calendar()
        now_utc = datetime.now(timezone.utc)
        for ev in events:
            try:
                ev_dt = datetime.fromisoformat(
                    ev["date"].replace("Z", "+00:00")
                ).astimezone(timezone.utc)
                diff_h = (ev_dt - now_utc).total_seconds() / 3600
                if -1 <= diff_h <= 24:
                    upcoming_events.append({
                        "title":    ev["title"],
                        "currency": ev["currency"],
                        "time":     ev_dt.strftime("%m/%d %H:%M UTC"),
                        "hours_until": round(diff_h, 1),
                        "status":   "発表済み" if diff_h < 0 else ("間もなく" if diff_h < 1 else "待機中"),
                    })
            except Exception:
                pass
    except Exception:
        pass
    detail["upcoming_events"] = upcoming_events[:5]

    # ── 総合スコア: 金利40% + DXY30% + VIX30% ──
    score = (sub_scores.get("rate", 0) * 0.40 +
             sub_scores.get("dxy", 0)  * 0.30 +
             sub_scores.get("vix", 0)  * 0.30)
    score = round(max(-1.0, min(1.0, score)), 4)

    # 総合バイアスサマリー
    if score > 0.25:
        detail["bias"]       = "USD強気（円安方向）"
        detail["bias_level"] = "strong_bull" if score > 0.5 else "bull"
    elif score < -0.25:
        detail["bias"]       = "USD弱気（円高方向）"
        detail["bias_level"] = "strong_bear" if score < -0.5 else "bear"
    else:
        detail["bias"]       = "中立（方向感なし）"
        detail["bias_level"] = "neutral"

    detail["sub_scores"]  = sub_scores
    detail["total_score"] = score

    return score, detail


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
    # 【修正】RSI を平均回帰でなくトレンド整合フィルタとして使用。
    # 旧: RSI>65 → -1.5 (上昇トレンド中の正常な RSI 68 を SELL 圧力扱い → バグ)
    # 新: 真の過熱・枯渇域 (< 22 / > 78) のみシグナル、中間帯は中立
    if   rsi < 22: score += 2.0; reasons.append(f"✅ RSI 極度売られ過ぎ ({rsi:.0f}) — 反転圏")
    elif rsi < 30: score += 1.0; reasons.append(f"↗ RSI 売られ過ぎ ({rsi:.0f})")
    elif rsi > 78: score -= 2.0; reasons.append(f"🔻 RSI 極度買われ過ぎ ({rsi:.0f}) — 反転圏")
    elif rsi > 70: score -= 1.0; reasons.append(f"↘ RSI 買われ過ぎ ({rsi:.0f})")
    # RSI 30–70: トレンドモメンタムの正常域 — ペナルティなし

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

# ─── デイトレード用 4H+1D 上位足キャッシュ ────────────────────────
_htf_dt_cache: dict = {}
HTF_DT_TTL = 900  # 15分キャッシュ（4H足は変化が遅い）

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


def get_htf_bias_daytrade(symbol: str) -> dict:
    """
    デイトレード用: 4H足と1D足のEMAトレンド構造からマスタートレンドバイアスを取得。
    スキャルプの1H+4Hより一段上のタイムフレームを使用。
    - 両足一致強気  → BUYのみ許可 (4H+1D上昇)
    - 両足一致弱気  → SELLのみ許可 (4H+1D下降)
    - 不一致        → シグナル抑制
    Returns: {score, h4, d1, agreement, label}
    """
    global _htf_dt_cache
    now = datetime.now()
    key = symbol
    if _htf_dt_cache.get(key) and (now - _htf_dt_cache[key]["ts"]).total_seconds() < HTF_DT_TTL:
        return _htf_dt_cache[key]["data"]

    results = {}
    for tf_key, cfg in [("h4", TF_CFG["4h"]), ("d1", TF_CFG["1d"])]:
        try:
            df_h = fetch_ohlcv(symbol, period=cfg["period"], interval=cfg["interval"])
            if cfg.get("resample"):
                df_h = resample_df(df_h, cfg["resample"])
            df_h = add_indicators(df_h)
            row    = df_h.iloc[-1]
            c      = float(row["Close"])
            e9     = float(row["ema9"])
            e21    = float(row["ema21"])
            e50    = float(row["ema50"])
            ema200 = float(row.get("ema200", row["ema50"]))
            rsi    = float(row["rsi"])

            # EMAアライメントスコア
            if   c > e9 > e21 > e50:  sc = 1.0;  lbl = "↗↗ 強気（全EMA上昇列）"
            elif c > e21 and e9 > e21: sc = 0.6;  lbl = "↗ 強気（EMA21超）"
            elif c > e21:              sc = 0.3;  lbl = "↗ 弱強気（EMA21超）"
            elif c < e9 < e21 < e50:  sc = -1.0; lbl = "↘↘ 弱気（全EMA下降列）"
            elif c < e21 and e9 < e21: sc = -0.6; lbl = "↘ 弱気（EMA21下）"
            elif c < e21:              sc = -0.3; lbl = "↘ 弱弱気（EMA21下）"
            else:                      sc = 0.0;  lbl = "↔ 中立"

            # EMA200によるボーナス補正（Neely & Weller 2011）
            if c > ema200: sc = min(1.0, sc + 0.1)
            else:          sc = max(-1.0, sc - 0.1)

            results[tf_key] = {
                "score":  sc, "label": lbl,
                "rsi":    round(rsi, 1),
                "ema9":   round(e9, 3), "ema21": round(e21, 3),
                "ema50":  round(e50, 3), "ema200": round(ema200, 3),
                "close":  round(c, 3),
            }
        except Exception as e:
            print(f"[HTF_DT/{tf_key}] {e}")
            results[tf_key] = {"score": 0.0, "label": "取得失敗", "rsi": 50.0}

    h4_sc = results.get("h4", {}).get("score", 0.0)
    d1_sc = results.get("d1", {}).get("score", 0.0)

    # 1D優先の加重平均（マスタートレンド=1D 60%, 中期=4H 40%）
    avg = round(h4_sc * 0.40 + d1_sc * 0.60, 3)

    if   h4_sc > 0.2  and d1_sc > 0.2:  agreement = "bull"; label = "📈 4H+1D 上昇一致 → BUYのみ有効"
    elif h4_sc < -0.2 and d1_sc < -0.2: agreement = "bear"; label = "📉 4H+1D 下降一致 → SELLのみ有効"
    else:                                agreement = "mixed"; label = "⚖️ 4H+1D 不一致 → シグナル抑制中"

    data = {
        "score": avg, "agreement": agreement, "label": label,
        "h4": results.get("h4", {}), "d1": results.get("d1", {}),
    }
    _htf_dt_cache[key] = {"data": data, "ts": now}
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

    # ── HTFバイアスフィルター（最重要）────────────────────────
    # 【修正】表示は常に 1H+4H (UIカード維持), フィルタ論理のみ TF 依存:
    #   tf=1h: 4H+1D でフィルタ (1H が自身の HTF に入る循環参照を回避)
    #   その他: 1H+4H でフィルタ (上位足確認)
    if backtest_mode and htf_cache and "htf" in htf_cache:
        htf = htf_cache["htf"]
    else:
        htf = get_htf_bias(symbol)  # UI表示用 (常に 1H+4H)
    if tf == "1h":
        if backtest_mode and htf_cache and "htf_dt" in htf_cache:
            htf_filter = htf_cache["htf_dt"]
        else:
            htf_filter = get_htf_bias_daytrade(symbol)  # 4H+1D フィルタ (循環参照回避)
    else:
        htf_filter = htf  # 1H+4H フィルタ
    htf_agreement = htf_filter.get("agreement", "mixed")

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

    # 金曜フィルター: 週末前の薄商い＋ポジション解消で方向性低下
    _is_friday_dt = False
    try:
        _dt_bar = bar_time if bar_time else datetime.now(timezone.utc)
        _dt_dow = _dt_bar.weekday() if hasattr(_dt_bar, 'weekday') else df.index[-1].weekday()
        if _dt_dow == 4:  # 金曜日
            _is_friday_dt = True
            _fri_hour = _dt_bar.hour if hasattr(_dt_bar, 'hour') else 12
            if _fri_hour >= 10:
                # 金曜UTC10時以降: 完全ブロック（NY前～クローズは損失集中）
                combined = 0.0
                reasons.append("🚫 金曜UTC10時以降: DT完全ブロック")
            elif _fri_hour < 7:
                # 金曜東京セッション(UTC0-6): 完全ブロック（低流動性+週末=高損失率）
                combined = 0.0
                reasons.append("🚫 金曜東京セッション: DT完全ブロック")
            else:
                # 金曜London(UTC7-9): 85%減衰で超高確信のみ通す
                combined *= 0.15
                reasons.append("⚠️ 金曜London: 週末リスク → スコア85%減衰")
    except Exception:
        pass

    _dt_threshold = 0.45 if _is_friday_dt else THRESHOLD  # 金曜は閾値も大幅引き上げ
    if   combined >  _dt_threshold: signal, conf = "BUY",  int(min(95, 50 + combined * 55))
    elif combined < -_dt_threshold: signal, conf = "SELL", int(min(95, 50 + abs(combined) * 55))
    else:                           signal, conf = "WAIT", int(max(25, 50 - abs(combined) * 40))

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
    if fund_detail.get("bias"):
        fund_rsns.append(f"📊 ファンダ総合: {fund_detail['bias']}")
    if fund_detail.get("rate_trend"):
        fund_rsns.append(f"📊 米10年債: {fund_detail['rate_trend']}" +
                         (f" ({fund_detail['us10y']}%)" if "us10y" in fund_detail else ""))
    if fund_detail.get("spread") is not None:
        fund_rsns.append(f"📊 金利差: {fund_detail['spread']}% ({fund_detail.get('spread_chg','—')})")
    if fund_detail.get("dxy_trend"):
        fund_rsns.append(f"📊 DXY: {fund_detail['dxy_trend']}")
    if fund_detail.get("vix_regime") and "中立" not in fund_detail.get("vix_regime", ""):
        fund_rsns.append(f"😨 {fund_detail['vix_regime']}")
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
#  デイトレードシグナル（30m/1h）
#  学術根拠:
#   - EMA200フィルター: +8-10%勝率改善 (QuantifiedStrategies, Neely & Weller 2011)
#   - ADX>25: チョッピー相場排除 (Wilder 1978, 広範な実証)
#   - フィボナッチ38.2-61.8%: 高確率プルバックゾーン
#   - セッション13-17UTC: London/NY重複、最高流動性 (Krohn et al. 2024 JoF)
#   - ボリューム確認: Sharpe+37-78% (IJSAT 2025)
# ═══════════════════════════════════════════════════════
def compute_daytrade_signal(df: pd.DataFrame, tf: str, sr_levels: list,
                            symbol: str = "USDJPY=X",
                            backtest_mode: bool = False,
                            bar_time=None,
                            htf_cache: dict = None) -> dict:
    # ── Layer 0: 取引禁止チェック ──────────────────────────────
    layer0 = is_trade_prohibited(df, bar_time=bar_time)

    # ── Layer 1: 大口バイアス（マスターフィルター）──────────────
    if backtest_mode and htf_cache and "layer1" in htf_cache:
        layer1 = htf_cache["layer1"]
    else:
        layer1 = get_master_bias(symbol)

    # ── Layer 2/3 + レジーム判定 ──────────────────────────────
    regime = detect_market_regime(df)
    layer2 = compute_layer2_score(df, tf)
    layer3 = compute_layer3_score(df, tf, sr_levels)

    row   = df.iloc[-1]
    entry = float(row["Close"])
    atr   = float(row["atr"])

    # ── 指標取得 ─────────────────────────────────────
    ema9   = float(row["ema9"])
    ema21  = float(row["ema21"])
    ema50  = float(row["ema50"])
    ema200 = float(row.get("ema200", row["ema50"]))
    adx    = float(row.get("adx", 25.0))
    adx_p  = float(row.get("adx_pos", 25.0))
    adx_n  = float(row.get("adx_neg", 25.0))
    rsi    = float(row["rsi"])
    macdh  = float(row["macd_hist"])
    macdh_prev = float(df["macd_hist"].iloc[-2]) if len(df) > 1 else 0.0
    bbpb   = float(row["bb_pband"])

    score   = 0.0
    reasons = []

    # ── HIGH_VOL レジームミュート ─────────────────────────
    if regime.get("regime") == "HIGH_VOL":
        session = get_session_info()
        ts_str = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)
        if backtest_mode:
            _hv_fund_detail, _hv_inst_detail = {}, {}
        else:
            _hv_fund_sc, _hv_fund_detail = fundamental_score()
            _hv_inst_sc, _hv_inst_detail = institutional_flow_score()
        return {
            "timestamp": ts_str, "symbol": "USD/JPY", "tf": tf,
            "entry": round(entry, 3), "signal": "WAIT", "confidence": 0,
            "sl": round(entry - atr * 0.7, 3), "tp": round(entry + atr * 1.5, 3),
            "rr_ratio": 2.14, "atr": round(atr, 3),
            "session": session,
            "reasons": [f"⚠️ 高ボラレジーム（ATR比{regime.get('atr_ratio',0):.1f}×） — 全シグナルミュート"],
            "mode": "daytrade", "regime": regime,
            "htf_bias": htf_cache["htf"] if backtest_mode and htf_cache else get_htf_bias(symbol),
            "dual_scenarios": [], "sr_entry_map": {},
            "entry_type": "wait", "score": 0.0,
            "layer_status": {"layer0": layer0, "layer1": layer1,
                             "master_bias": layer1.get("label","—"), "trade_ok": False},
            "indicators": {"ema9": round(ema9,3), "ema21": round(ema21,3),
                           "ema50": round(ema50,3), "ema200": round(ema200,3),
                           "rsi": round(rsi,1), "adx": round(adx,1),
                           "macd": 0.0, "macd_sig": 0.0,
                           "macd_hist": round(macdh,4),
                           "bb_upper": 0.0, "bb_mid": 0.0, "bb_lower": 0.0,
                           "bb_pband": round(bbpb,3)},
            "fundamental": _hv_fund_detail,
            "institutional": _hv_inst_detail,
            "score_detail": {"combined": 0.0, "rule": 0.0},
        }

    # ⓪ 4H+1D マスタートレンドフィルター（デイトレード専用上位足バイアス）
    if backtest_mode and htf_cache and "htf" in htf_cache:
        htf_dt = htf_cache["htf"]
    else:
        htf_dt       = get_htf_bias_daytrade(symbol)
    htf_agreement = htf_dt.get("agreement", "mixed")
    if htf_agreement == "bull":
        reasons.append(f"📈 {htf_dt.get('label','4H+1D 上昇一致')} → BUYバイアス")
    elif htf_agreement == "bear":
        reasons.append(f"📉 {htf_dt.get('label','4H+1D 下降一致')} → SELLバイアス")
    else:
        reasons.append(f"⚖️ {htf_dt.get('label','4H+1D 不一致')} → シグナル抑制")

    # ① ADX レジームフィルター (Wilder 1978) ── 緩和版: 取引頻度重視
    if adx >= 25:
        adx_mult = 1.1; reasons.append(f"✅ ADX{adx:.0f}≥25: 強トレンド確認（Wilder 1978）")
    elif adx >= 18:
        adx_mult = 0.85; reasons.append(f"⚠️ ADX{adx:.0f}: 中程度トレンド")
    elif adx >= 12:
        adx_mult = 0.65; reasons.append(f"⚠️ ADX{adx:.0f}: 弱トレンド（頻度重視で許容）")
    else:
        adx_mult = 0.45; reasons.append(f"⛔ ADX{adx:.0f}<12: レンジ相場（シグナル減衰）")

    # ② EMA200方向フィルター + スロープ分析（Neely & Weller 2011）
    bull200 = entry > ema200
    _dt_ema200_slope = (ema200 - float(df["ema200"].iloc[-min(20, len(df)-1)])) if "ema200" in df.columns and len(df) >= 2 else 0
    _dt_ema200_rising = _dt_ema200_slope > 0
    if bull200 and _dt_ema200_rising:
        score += 0.5
        reasons.append(f"✅ EMA200({ema200:.3f})上位+上昇中: 強い上昇バイアス")
    elif bull200:
        reasons.append(f"✅ EMA200({ema200:.3f})上位: 上昇バイアス(slope弱)")
    elif not bull200 and not _dt_ema200_rising:
        score -= 0.5
        reasons.append(f"🔻 EMA200({ema200:.3f})下位+下降中: 強い下降バイアス")
    else:
        reasons.append(f"🔻 EMA200({ema200:.3f})下位: 下降バイアス(slope弱)")

    # ③ EMAアライメント + +DI/-DI方向
    if ema9 > ema21 > ema50 and adx_p > adx_n:
        score += 2.5; reasons.append("✅ 強気EMAアライメント(9>21>50) + +DI優位")
        act = "BUY"
    elif ema9 < ema21 < ema50 and adx_n > adx_p:
        score -= 2.5; reasons.append("🔻 弱気EMAアライメント(9<21<50) + -DI優位")
        act = "SELL"
    elif ema9 > ema21 and ema21 > ema50 * 0.998:
        score += 1.2; reasons.append("↗ 中期強気EMA")
        act = "BUY"
    elif ema9 < ema21 and ema21 < ema50 * 1.002:
        score -= 1.2; reasons.append("↘ 中期弱気EMA")
        act = "SELL"
    elif entry > ema21:
        score += 0.5; act = "BUY"
    else:
        score -= 0.5; act = "SELL"

    # EMA200逆方向のシグナルを減衰（スロープ考慮版・15m短期向け緩和）
    if (act == "BUY" and not bull200) or (act == "SELL" and bull200):
        # スロープも逆行 → ペナルティ（ただし15m短期なので過度に抑制しない）
        if (act == "BUY" and not _dt_ema200_rising) or (act == "SELL" and _dt_ema200_rising):
            score *= 0.60
            reasons.append("⚠️ EMA200+スロープ逆行 → 減衰")
        else:
            score *= 0.75
            reasons.append("⚠️ EMA200と逆方向 → 軽度減衰")

    # 4H+1D マスタートレンドとの整合性チェック（ハードフィルター: scalp同様に逆行ブロック）
    # 本番実績: HTF bullish時のSELL 12連敗(-101pip) → スコアペナルティでは不十分、完全ブロック必須
    if htf_agreement == "bull":
        if act == "SELL":
            ema_score = 0.0  # SELL完全ブロック
            score = 0.0
            reasons.append("🚫 4H+1D 上昇一致 → SELL ブロック")
        else:
            score *= 1.2  # BUY方向を強化
    elif htf_agreement == "bear":
        if act == "BUY":
            ema_score = 0.0  # BUY完全ブロック
            score = 0.0
            reasons.append("🚫 4H+1D 下降一致 → BUY ブロック")
        else:
            score *= 1.2  # SELL方向を強化
    else:
        # mixed: 全体的に抑制
        score *= 0.70
        reasons.append("⚠️ 4H+1D 不一致 → シグナル抑制")

    # ④ フィボナッチプルバックゾーン（38.2-61.8%が最高確率）
    fib = _calc_fibonacci_levels(df, lookback=80)
    if fib:
        r382, r500, r618 = fib.get("r382"), fib.get("r500"), fib.get("r618")
        if r618 and r382:
            lo, hi = min(r618, r382), max(r618, r382)
            if lo <= entry <= hi:
                score += 1.5 if act == "BUY" else -1.5
                reasons.append(f"✅ フィボ38.2-61.8%ゾーン({lo:.3f}-{hi:.3f}): 高確率プルバック")
            elif r500 and abs(entry - r500) < atr * 0.5:
                score += 0.8 if act == "BUY" else -0.8
                reasons.append(f"↗ フィボ50%近辺({r500:.3f})")

    # ⑤ RSI14確認（過熱外のみ: Menkhoff 2012のフィルター概念）
    if act == "BUY":
        if 40 <= rsi <= 65:
            score += 1.0; reasons.append(f"✅ RSI{rsi:.0f}: モメンタムゾーン(40-65)")
        elif rsi < 40:
            score += 0.5; reasons.append(f"↗ RSI{rsi:.0f}: 売られ過ぎ回復")
        elif rsi > 72:
            score -= 1.5; reasons.append(f"⚠️ RSI{rsi:.0f}: 過買い → 慎重エントリー")
    else:
        if 35 <= rsi <= 60:
            score -= 1.0; reasons.append(f"🔻 RSI{rsi:.0f}: モメンタムゾーン(35-60)")
        elif rsi > 60:
            score -= 0.5; reasons.append(f"↘ RSI{rsi:.0f}: 買われ過ぎ回落")
        elif rsi < 28:
            score += 1.5; reasons.append(f"⚠️ RSI{rsi:.0f}: 過売り → 慎重エントリー")

    # ⑥ MACDヒスト転換点（方向変化のみ使用: EMAとの重複回避）
    if (macdh > 0 and macdh > macdh_prev and act == "BUY"):
        score += 0.8; reasons.append("✅ MACDヒスト上昇転換: 買いモメンタム強化")
    elif (macdh < 0 and macdh < macdh_prev and act == "SELL"):
        score -= 0.8; reasons.append("🔻 MACDヒスト下落転換: 売りモメンタム強化")

    # ⑦ ボリューム確認（IJSAT 2025: Sharpe+37-78%）
    if "Volume" in df.columns:
        vol = float(df["Volume"].tail(1).values[0])
        vol_avg = float(df["Volume"].tail(20).mean())
        if vol_avg > 0 and vol > vol_avg * 1.3:
            score += 0.6 if act == "BUY" else -0.6
            reasons.append(f"✅ 出来高{vol/vol_avg:.1f}x: 機関参入シグナル")

    # ⑧ BBパンド（中央ゾーン = 良好エントリー）
    if 0.25 <= bbpb <= 0.75:
        reasons.append(f"✅ BB中央ゾーン({bbpb:.2f}): エントリー適正")
    elif (act == "BUY" and bbpb > 0.88) or (act == "SELL" and bbpb < 0.12):
        score *= 0.7; reasons.append(f"⚠️ BB極端({bbpb:.2f}): リスク注意")

    # ADXマルチプライヤー適用
    score *= adx_mult

    # ── Layer 1: 大口バイアス適用（緩和版: 取引頻度確保）────────
    bias_dir = layer1["direction"]
    if bias_dir == "bull":
        if score < 0:  score *= 0.55   # 逆方向でも半分は残す
        else:          score *= 1.15
    elif bias_dir == "bear":
        if score > 0:  score *= 0.55
        else:          score *= 1.15
    else:
        score *= 0.80  # 大口方向不明 → 軽度減衰

    # ── Layer 0: 取引禁止時の早期リターン（東京モードはスキップ）──
    if layer0["prohibited"] and not layer0.get("tokyo_mode", False):
        session = get_session_info()
        ts_str  = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)
        return {
            "timestamp": ts_str, "symbol": "USD/JPY", "tf": tf,
            "entry": round(entry, 3), "signal": "WAIT", "confidence": 0,
            "sl": round(entry - atr * 0.8, 3), "tp": round(entry + atr * 2.0, 3),
            "rr_ratio": 2.5, "atr": round(atr, 3),
            "session": session,
            "htf_bias": htf_cache["htf"] if backtest_mode and htf_cache else get_htf_bias(symbol),
            "swing_mode": tf in ("1h","4h","1d"),
            "reasons": [f"🚫 {layer0['reason']}"],
            "mode": "daytrade", "score": 0.0,
            "indicators": {"ema9": round(ema9,3), "ema21": round(ema21,3),
                          "ema50": round(ema50,3), "ema200": round(ema200,3),
                          "adx": round(adx,1), "rsi": round(rsi,1),
                          "macd": 0.0, "macd_sig": 0.0, "macd_hist": round(macdh,5),
                          "bb_upper": 0.0, "bb_mid": 0.0, "bb_lower": 0.0, "bb_pband": round(bbpb,3)},
            "daytrade_info": {"adx": round(adx,1), "adx_pos": round(adx_p,1),
                             "adx_neg": round(adx_n,1), "ema200": round(ema200,3),
                             "fib": {}, "score": 0.0},
            "htf_bias_daytrade": htf_dt,
            "layer_status": {"layer0": layer0, "layer1": layer1,
                            "master_bias": layer1.get("label","—"), "trade_ok": False},
            "score_detail": {"combined": 0.0, "rule": 0.0},
        }

    # セッションフィルター: London/NY重複 = ボーナス（オフセッションも許容）
    try:
        h = df.index[-1].hour
        if 13 <= h < 17:
            score *= 1.15; reasons.append(f"✅ London/NY重複({h}UTC): 最高流動性")
        elif 7 <= h < 20:
            pass  # 通常時間
        else:
            score *= 0.70; reasons.append(f"⚠️ オフセッション({h}UTC): 軽度減衰")
    except Exception:
        pass

    # 上位足バイアス (既存関数再利用)
    if backtest_mode and htf_cache and "htf" in htf_cache:
        htf = htf_cache["htf"]
    else:
        htf = get_htf_bias(symbol)

    # ── Layer 2: トレンド構造整合性ブースト ─────────────────────
    l2_sc = layer2["score"]
    if (score > 0 and l2_sc > 0) or (score < 0 and l2_sc < 0):
        score += l2_sc * 0.25   # up to +0.25 boost when aligned
    elif (score > 0 and l2_sc < 0) or (score < 0 and l2_sc > 0):
        score *= 0.70           # 30% reduction when conflicting

    # ── Layer 3: 精密エントリーボーナス ─────────────────────────
    l3_sc = layer3["score"]
    score += l3_sc * 0.15       # up to +0.15 precision bonus
    score = max(-3.0, min(3.0, score))  # clamp before normalization

    # ── ハイブリッドシグナル決定: SR構造主導 + EMAスコア確度補正 ──
    # EMAスコア（既存の score 変数）を確度ブースターとして使用
    ema_score = score  # 保存（SR構造判定後に確度補正に使用）

    # SR構造による方向・シグナル決定
    _dt_sr_weighted = []
    _dt_nearest_scenario = None
    try:
        _dt_sr_weighted = find_sr_levels_weighted(
            df, window=5, tolerance_pct=0.003, min_touches=2,
            max_levels=8, bars_per_day=96 if "15m" in tf or "30m" in tf else 24)
    except Exception:
        pass

    _dt_above = [s for s in _dt_sr_weighted if s["price"] > entry + atr * 0.1
                 and s["strength"] >= 0.4 and s["touches"] >= 2]
    _dt_below = [s for s in _dt_sr_weighted if s["price"] < entry - atr * 0.1
                 and s["strength"] >= 0.4 and s["touches"] >= 2]
    _dt_above.sort(key=lambda x: x["price"])
    _dt_below.sort(key=lambda x: -x["price"])

    signal = "WAIT"
    conf = 30
    _dt_entry_type = "unknown"
    SL_MULT, TP_MULT = 0.4, 1.5

    # SR構造ベースのシグナル判定（BT dual_sr_bounce/breakout と整合）
    _sr_signal_found = False

    # ── ADXハードブロック: レンジ相場ではSR bounceを禁止 ──
    # 本番で0/9全敗（-101.5pip）の根本原因: レンジでBUY/SELL交互発火
    _dt_adx_ok = adx >= 15  # ADX15未満はレンジ → SR bounce禁止

    # A: 下のSRバウンス → BUY（EMA方向整合必須 + ADX≥15）
    if _dt_adx_ok and _dt_below:
        _sup = _dt_below[0]
        _sup_tol = atr * 0.6  # 旧0.4 → 0.6（SR近接判定を緩和）
        if abs(float(row["Low"]) - _sup["price"]) < _sup_tol and entry > _sup["price"]:
            if entry > float(row["Open"]) and rsi < 60 and ema9 > ema21:
                signal = "BUY"
                _dt_entry_type = "dual_sr_bounce"
                _sr_signal_found = True
                _dt_nearest_scenario = {"type": "bounce", "sr": _sup}

    # B: 上のSRバウンス → SELL（EMA方向整合必須 + ADX≥15）
    if not _sr_signal_found and _dt_adx_ok and _dt_above:
        _res = _dt_above[0]
        _res_tol = atr * 0.6  # 旧0.4 → 0.6
        if abs(float(row["High"]) - _res["price"]) < _res_tol and entry < _res["price"]:
            if entry < float(row["Open"]) and rsi > 40 and ema9 < ema21:
                signal = "SELL"
                _dt_entry_type = "dual_sr_bounce"
                _sr_signal_found = True
                _dt_nearest_scenario = {"type": "bounce", "sr": _res}

    # C: 下のSR下抜けブレイク → SELL
    if not _sr_signal_found and _dt_below:
        _sup = _dt_below[0]
        if (_sup["touches"] >= 2
                and entry < _sup["price"] - atr * 0.1
                and entry < float(row["Open"]) and adx >= 12):
            signal = "SELL"
            _dt_entry_type = "dual_sr_breakout"
            _sr_signal_found = True
            _dt_nearest_scenario = {"type": "breakout", "sr": _sup}

    # D: 上のSR上抜けブレイク → BUY
    if not _sr_signal_found and _dt_above:
        _res = _dt_above[0]
        if (_res["touches"] >= 2
                and entry > _res["price"] + atr * 0.1
                and entry > float(row["Open"]) and adx >= 12):
            signal = "BUY"
            _dt_entry_type = "dual_sr_breakout"
            _sr_signal_found = True
            _dt_nearest_scenario = {"type": "breakout", "sr": _res}

    # ── E: 三尊天井 / 逆三尊（15m足: ノイズ少なく有効）──
    # Bulkowski (2005): H&S patterns on 15m+ have 65-70% follow-through
    if not _sr_signal_found and len(df) >= 30:
        _dt_hs_window = 3  # 15m足: 前後3本（前後45分の極値）
        _dt_lookback = min(40, len(df) - 1)
        _dt_hs_df = df.iloc[-_dt_lookback:]
        _dt_h_arr = _dt_hs_df["High"].values.flatten()
        _dt_l_arr = _dt_hs_df["Low"].values.flatten()

        _dt_swing_highs = []
        _dt_swing_lows = []
        for _si in range(_dt_hs_window, len(_dt_hs_df) - _dt_hs_window):
            _loc_h = _dt_h_arr[max(0, _si - _dt_hs_window):_si + _dt_hs_window + 1]
            _loc_l = _dt_l_arr[max(0, _si - _dt_hs_window):_si + _dt_hs_window + 1]
            if _dt_h_arr[_si] == _loc_h.max() and _dt_h_arr[_si] > _dt_h_arr[_si - 1]:
                _dt_swing_highs.append((_si, float(_dt_h_arr[_si])))
            if _dt_l_arr[_si] == _loc_l.min() and _dt_l_arr[_si] < _dt_l_arr[_si - 1]:
                _dt_swing_lows.append((_si, float(_dt_l_arr[_si])))

        # 三尊天井 → SELL
        for _hi in range(len(_dt_swing_highs) - 2):
            _s1i, _s1p = _dt_swing_highs[_hi]
            _s2i, _s2p = _dt_swing_highs[_hi + 1]
            _s3i, _s3p = _dt_swing_highs[_hi + 2]
            if not (_s2p > _s1p and _s2p > _s3p):
                continue
            if _s3i - _s1i > 30 or _s3i - _s1i < 6:
                continue
            _hp = min(_s2p - _s1p, _s2p - _s3p) * 100
            _sd = abs(_s1p - _s3p) * 100
            if _hp < 5.0 or _sd > _hp * 0.6:  # 15m: 5pip以上の prominence
                continue
            _neck_lows = [(_li, _lp) for _li, _lp in _dt_swing_lows if _s1i < _li < _s3i]
            if not _neck_lows:
                continue
            _neckline = min(_neck_lows, key=lambda x: x[1])[1]
            if _s3i < len(_dt_hs_df) - 2:
                _nd = (entry - _neckline) * 100
                if -3.0 <= _nd <= 2.0 and entry < float(row["Open"]) and ema9 < ema21:
                    signal = "SELL"
                    _dt_entry_type = "hs_neckbreak"
                    _sr_signal_found = True
                    reasons.append(f"✅ 三尊天井: L={_s1p:.3f} H={_s2p:.3f} R={_s3p:.3f} [Bulkowski 2005]")
                    reasons.append(f"✅ ネックライン{_neckline:.3f}({_nd:+.1f}pip), prominence={_hp:.1f}pip")
                    break

        # 逆三尊 → BUY
        if not _sr_signal_found:
            for _li in range(len(_dt_swing_lows) - 2):
                _s1i, _s1p = _dt_swing_lows[_li]
                _s2i, _s2p = _dt_swing_lows[_li + 1]
                _s3i, _s3p = _dt_swing_lows[_li + 2]
                if not (_s2p < _s1p and _s2p < _s3p):
                    continue
                if _s3i - _s1i > 30 or _s3i - _s1i < 6:
                    continue
                _hp = min(_s1p - _s2p, _s3p - _s2p) * 100
                _sd = abs(_s1p - _s3p) * 100
                if _hp < 5.0 or _sd > _hp * 0.6:
                    continue
                _neck_highs = [(_hi2, _hp2) for _hi2, _hp2 in _dt_swing_highs if _s1i < _hi2 < _s3i]
                if not _neck_highs:
                    continue
                _neckline = max(_neck_highs, key=lambda x: x[1])[1]
                if _s3i < len(_dt_hs_df) - 2:
                    _nd = (_neckline - entry) * 100
                    if -3.0 <= _nd <= 2.0 and entry > float(row["Open"]) and ema9 > ema21:
                        signal = "BUY"
                        _dt_entry_type = "ihs_neckbreak"
                        _sr_signal_found = True
                        reasons.append(f"✅ 逆三尊: L={_s1p:.3f} H={_s2p:.3f} R={_s3p:.3f} [Bulkowski 2005]")
                        reasons.append(f"✅ ネックライン{_neckline:.3f}({_nd:+.1f}pip), prominence={_hp:.1f}pip")
                        break

    # SR+Fib / OB Retest フォールバック（強いスコア + EMAトレンド整合 + ADX必須）
    # 本番0/6全敗(-40.2pip): 0.20閾値が甘すぎ + レンジ相場でエントリー
    if not _sr_signal_found and adx >= 15:
        _has_sr_fib = any("Fib" in r or "フィボ" in r for r in reasons)
        _has_ob     = any("OB" in r or "オーダーブロック" in r for r in reasons)
        THRESHOLD = 0.35   # 0.20→0.35: 弱シグナル排除（本番0%WR対策）
        if ema_score > THRESHOLD and ema9 > ema21:
            signal = "BUY"
            _dt_entry_type = "sr_fib_confluence" if _has_sr_fib else ("ob_retest" if _has_ob else "ema_cross")
        elif ema_score < -THRESHOLD and ema9 < ema21:
            signal = "SELL"
            _dt_entry_type = "sr_fib_confluence" if _has_sr_fib else ("ob_retest" if _has_ob else "ema_cross")

    # ════════════════════════════════════════════════════════
    #  DT新戦略A: Fibonacci Reversal（15m足フィボリトレースメント反発）
    #  根拠: フィボ38.2%/50%/61.8%はスイング反転の高確率ゾーン
    # ════════════════════════════════════════════════════════
    if not _sr_signal_found and signal == "WAIT" and len(df) >= 80:
        _dt_fib = _calc_fibonacci_levels(df, lookback=80)
        if _dt_fib and _dt_fib.get("trend"):
            _dt_fib_levels = {
                "38.2%": _dt_fib.get("r382", 0),
                "50.0%": _dt_fib.get("r500", 0),
                "61.8%": _dt_fib.get("r618", 0),
            }
            _dt_fib_touch = None
            for _fn, _fv in _dt_fib_levels.items():
                if _fv and abs(entry - _fv) < atr * 0.3:
                    _dt_fib_touch = (_fn, _fv)
                    break

            if _dt_fib_touch:
                _fn, _fv = _dt_fib_touch
                # 上昇トレンド押し目買い
                if _dt_fib["trend"] == "up" and rsi < 45 and macdh > macdh_prev:
                    signal = "BUY"
                    _dt_entry_type = "dt_fib_reversal"
                    _sr_signal_found = True
                    score += 1.5
                    reasons.append(f"✅ DT Fib {_fn}サポート反発({_fv:.3f})")
                    if _fn == "61.8%":
                        score += 0.8
                        reasons.append("✅ Fib61.8%: 最高確率ゾーン")
                    if ema9 > ema21:
                        score += 0.5
                        reasons.append("✅ EMA順列確認")
                # 下降トレンド戻り売り
                elif _dt_fib["trend"] == "down" and rsi > 55 and macdh < macdh_prev:
                    signal = "SELL"
                    _dt_entry_type = "dt_fib_reversal"
                    _sr_signal_found = True
                    score -= 1.5
                    reasons.append(f"✅ DT Fib {_fn}レジスタンス反発({_fv:.3f})")
                    if _fn == "61.8%":
                        score -= 0.8
                        reasons.append("✅ Fib61.8%: 最高確率ゾーン")
                    if ema9 < ema21:
                        score -= 0.5
                        reasons.append("✅ EMA逆順列確認")

    # ════════════════════════════════════════════════════════
    #  DT新戦略B: SR Channel Reversal（15m足SR/チャネルバウンス）
    #  根拠: 水平線・並行チャネル境界での反発
    # ════════════════════════════════════════════════════════
    if not _sr_signal_found and signal == "WAIT" and sr_levels and len(df) >= 20:
        _dt_ch = find_parallel_channel(df, window=5, lookback=min(100, len(df) - 1))
        _dt_ch_upper = float(_dt_ch["upper"][-1]["value"]) if _dt_ch else None
        _dt_ch_lower = float(_dt_ch["lower"][-1]["value"]) if _dt_ch else None

        _dt_sr_buy = [l for l in sr_levels if 0 < entry - l < atr * 0.4]
        _dt_sr_sell = [l for l in sr_levels if 0 < l - entry < atr * 0.4]
        _dt_at_ch_lower = _dt_ch_lower and abs(entry - _dt_ch_lower) < atr * 0.4
        _dt_at_ch_upper = _dt_ch_upper and abs(entry - _dt_ch_upper) < atr * 0.4

        # BUY: SRサポート or チャネル下限 + RSI反転 + MACD反転
        if (_dt_sr_buy or _dt_at_ch_lower) and rsi < 45 and macdh > macdh_prev:
            signal = "BUY"
            _dt_entry_type = "dt_sr_channel_reversal"
            _sr_signal_found = True
            score += 1.2
            if _dt_sr_buy:
                reasons.append(f"✅ DT SRサポート反発({max(_dt_sr_buy):.3f})")
            if _dt_at_ch_lower:
                score += 0.5
                reasons.append(f"✅ DT チャネル下限反発({_dt_ch_lower:.3f})")
            if ema9 > ema21:
                score += 0.5
                reasons.append("✅ EMA順列確認")

        # SELL: SRレジスタンス or チャネル上限 + RSI反転 + MACD反転
        elif (_dt_sr_sell or _dt_at_ch_upper) and rsi > 55 and macdh < macdh_prev:
            signal = "SELL"
            _dt_entry_type = "dt_sr_channel_reversal"
            _sr_signal_found = True
            score -= 1.2
            if _dt_sr_sell:
                reasons.append(f"✅ DT SRレジスタンス反発({min(_dt_sr_sell):.3f})")
            if _dt_at_ch_upper:
                score -= 0.5
                reasons.append(f"✅ DT チャネル上限反発({_dt_ch_upper:.3f})")
            if ema9 < ema21:
                score -= 0.5
                reasons.append("✅ EMA逆順列確認")

    # ════════════════════════════════════════════════════════
    #  DT新戦略C: EMA200 Trend Reversal（トレンド転換検出）
    #  根拠: EMA200ブレイク後のリテスト・反発
    # ════════════════════════════════════════════════════════
    if not _sr_signal_found and signal == "WAIT" and len(df) >= 20:
        _ema200_dist_dt = (entry - ema200) / atr if atr > 0 else 0
        # 直近20バーでEMA200をクロスしたか
        _ema200_crosses = 0
        for _ci in range(max(1, len(df) - 20), len(df)):
            _prev_c = float(df["Close"].iloc[_ci - 1])
            _curr_c = float(df["Close"].iloc[_ci])
            _prev_e200 = float(df["ema200"].iloc[_ci - 1]) if "ema200" in df.columns else ema200
            _curr_e200 = float(df["ema200"].iloc[_ci]) if "ema200" in df.columns else ema200
            if (_prev_c < _prev_e200 and _curr_c > _curr_e200) or \
               (_prev_c > _prev_e200 and _curr_c < _curr_e200):
                _ema200_crosses += 1

        # EMA200をクロス後、リテストして反発
        if _ema200_crosses >= 1 and abs(_ema200_dist_dt) < 0.5:
            # 上抜け後のリテスト → BUY（EMA200がサポート化）
            if bull200 and _ema200_dist_dt < 0.5 and _ema200_dist_dt > 0 and macdh > macdh_prev and rsi < 55:
                signal = "BUY"
                _dt_entry_type = "ema200_trend_reversal"
                _sr_signal_found = True
                score += 1.5
                reasons.append(f"✅ EMA200上抜けリテスト({ema200:.3f}, dist={_ema200_dist_dt:.2f}ATR)")
                if _dt_ema200_rising:
                    score += 0.5
                    reasons.append("✅ EMA200上昇中: トレンド転換確認")
            # 下抜け後のリテスト → SELL（EMA200がレジスタンス化）
            elif not bull200 and _ema200_dist_dt > -0.5 and _ema200_dist_dt < 0 and macdh < macdh_prev and rsi > 45:
                signal = "SELL"
                _dt_entry_type = "ema200_trend_reversal"
                _sr_signal_found = True
                score -= 1.5
                reasons.append(f"✅ EMA200下抜けリテスト({ema200:.3f}, dist={_ema200_dist_dt:.2f}ATR)")
                if not _dt_ema200_rising:
                    score -= 0.5
                    reasons.append("✅ EMA200下降中: トレンド転換確認")

    # ── EMAスコアによる確度補正 ──
    # SR構造が方向を決め、EMAスコアが確度を上下させる
    if signal != "WAIT":
        base_conf = 50
        # SR構造ボーナス
        if _dt_nearest_scenario:
            sr_s = _dt_nearest_scenario["sr"]["strength"]
            base_conf += int(sr_s * 15)  # 強度95% → +14pt
            if _dt_nearest_scenario["sr"]["touches"] >= 5:
                base_conf += 5  # 多タッチボーナス
        # EMAスコアブースト（同方向なら+、逆方向なら-）
        if signal == "BUY":
            ema_boost = int(np.clip(ema_score * 8, -15, 15))
        else:
            ema_boost = int(np.clip(-ema_score * 8, -15, 15))
        # EMAトレンド整合ボーナス
        if signal == "BUY" and ema9 > ema21 > ema50:
            ema_boost += 5
            reasons.append("✅ EMA順列 (9>21>50): SR BUY確度UP")
        elif signal == "SELL" and ema9 < ema21 < ema50:
            ema_boost += 5
            reasons.append("✅ EMA逆順列 (9<21<50): SR SELL確度UP")
        elif signal == "BUY" and ema9 < ema21:
            ema_boost -= 5
            reasons.append("⚠️ EMA逆行 (9<21): SR BUYだが確度DOWN")
        elif signal == "SELL" and ema9 > ema21:
            ema_boost -= 5
            reasons.append("⚠️ EMA逆行 (9>21): SR SELLだが確度DOWN")
        # MACD整合
        if signal == "BUY" and macdh > 0 and macdh > macdh_prev:
            ema_boost += 3
        elif signal == "SELL" and macdh < 0 and macdh < macdh_prev:
            ema_boost += 3

        conf = int(np.clip(base_conf + ema_boost, 25, 92))
    else:
        conf = int(max(20, 50 - abs(ema_score) * 15))

    # SL/TP ── SR構造ベース
    act_s = signal if signal != "WAIT" else ("BUY" if ema_score >= 0 else "SELL")
    dir_s = 1.0 if act_s == "BUY" else -1.0

    if _dt_entry_type == "dual_sr_bounce":
        SL_MULT, TP_MULT = 0.4, 1.5
        # TP: 対面SRまでの距離
        if act_s == "BUY" and _dt_above:
            _tp_dist = abs(_dt_above[0]["price"] - entry) / max(atr, 1e-6)
            TP_MULT = min(_tp_dist * 0.95, 2.5)
        elif act_s == "SELL" and _dt_below:
            _tp_dist = abs(entry - _dt_below[0]["price"]) / max(atr, 1e-6)
            TP_MULT = min(_tp_dist * 0.95, 2.5)
    elif _dt_entry_type == "dual_sr_breakout":
        SL_MULT, TP_MULT = 0.4, 2.0
    else:
        SL_MULT, TP_MULT = 0.5, 1.5

    sl   = round(entry - atr * SL_MULT * dir_s, 3)
    tp   = round(entry + atr * TP_MULT * dir_s, 3)

    # 最低SL距離保証: 5.0pips（DT用 — スプレッド+ノイズ余裕）
    DT_MIN_SL_PIPS = 0.050  # 5.0 pips for JPY pairs
    _dt_sl_dist = abs(entry - sl)
    if _dt_sl_dist < DT_MIN_SL_PIPS:
        sl = round(entry - DT_MIN_SL_PIPS * dir_s, 3)

    # SR-aware TP snap
    if act_s == "BUY":
        tp_cands = [l for l in sr_levels if entry + atr*0.3 < l < entry + atr*TP_MULT*1.5]
        if tp_cands:
            tp = round(min(tp_cands) - 0.005, 3)
    else:
        tp_cands = [l for l in sr_levels if entry - atr*TP_MULT*1.5 < l < entry - atr*0.3]
        if tp_cands:
            tp = round(max(tp_cands) + 0.005, 3)

    sl_d = abs(entry - sl)
    if abs(tp - entry) < sl_d * 1.3:
        tp = round(entry + sl_d * 1.8 * dir_s, 3)
    rr = round(abs(tp - entry) / max(sl_d, 1e-6), 2)

    session = get_session_info()
    ts_str  = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)

    # ── ファンダメンタル + 大口フロー取得（デュアルシナリオ・マクロ表示用）──
    if backtest_mode:
        fund_sc, fund_detail = 0.0, {}
        inst_sc, inst_detail = 0.0, {}
    else:
        fund_sc, fund_detail = fundamental_score()
        inst_sc, inst_detail = institutional_flow_score()

    # ── デュアルシナリオ生成（SR構造 × EMA整合ハイブリッド）──────
    # 上下の強いSRを特定し、バウンス/ブレイクの2シナリオを準備
    # マスター方向（EMA/ADX）との整合度を各シナリオに付与
    dual_scenarios = []

    # マスター方向判定（EMAスコアベース）
    _master_dir = "BUY" if ema_score >= 0 else "SELL"
    _master_str = abs(ema_score)  # 0-3のEMA確度スコア
    # ファンダバイアス（デュアルシナリオ確度補正用）
    _fund_bias = htf_dt.get("agreement", "mixed")  # bull/bear/mixed
    _fund_total = fund_detail.get("total_score", 0.0) if fund_detail else 0.0

    def _ema_alignment(sc_dir):
        """シナリオ方向とマスターEMA+ファンダ方向の整合スコア (0-100)"""
        aligned = (sc_dir == _master_dir)
        base = 60 if aligned else 25
        # EMAスコアが強いほど整合/非整合の影響が大きい
        boost = int(min(_master_str * 12, 30)) if aligned else -int(min(_master_str * 8, 20))
        # EMAアライメント追加
        if sc_dir == "BUY" and ema9 > ema21 > ema50:
            boost += 10
        elif sc_dir == "SELL" and ema9 < ema21 < ema50:
            boost += 10
        elif sc_dir == "BUY" and ema9 < ema21:
            boost -= 8
        elif sc_dir == "SELL" and ema9 > ema21:
            boost -= 8
        # MACD整合
        if sc_dir == "BUY" and macdh > 0:
            boost += 5
        elif sc_dir == "SELL" and macdh < 0:
            boost += 5
        # RSI整合
        if sc_dir == "BUY" and 35 <= rsi <= 65:
            boost += 3
        elif sc_dir == "SELL" and 35 <= rsi <= 65:
            boost += 3
        # ── ファンダメンタル整合 ──
        # 金利差・DXY・VIXの総合バイアスがシナリオ方向と一致するか
        if sc_dir == "BUY" and _fund_total > 0.15:
            boost += int(min(_fund_total * 10, 8))  # USD強=BUY支援
        elif sc_dir == "SELL" and _fund_total < -0.15:
            boost += int(min(abs(_fund_total) * 10, 8))  # USD弱=SELL支援
        elif sc_dir == "BUY" and _fund_total < -0.25:
            boost -= 5  # USD弱なのにBUY=ペナルティ
        elif sc_dir == "SELL" and _fund_total > 0.25:
            boost -= 5  # USD強なのにSELL=ペナルティ
        # 4H+1Dマスタートレンドとの整合
        if _fund_bias == "bull" and sc_dir == "BUY":
            boost += 5
        elif _fund_bias == "bear" and sc_dir == "SELL":
            boost += 5
        elif _fund_bias == "bull" and sc_dir == "SELL":
            boost -= 6
        elif _fund_bias == "bear" and sc_dir == "BUY":
            boost -= 6
        return int(np.clip(base + boost, 10, 95))

    try:
        sr_weighted = find_sr_levels_weighted(df, window=5, tolerance_pct=0.003,
                                              min_touches=2, max_levels=8,
                                              bars_per_day=96 if "15m" in tf or "30m" in tf else 24)
        _above = [s for s in sr_weighted if s["price"] > entry + atr * 0.15
                  and s["strength"] >= 0.4 and s["touches"] >= 2]
        _below = [s for s in sr_weighted if s["price"] < entry - atr * 0.15
                  and s["strength"] >= 0.4 and s["touches"] >= 2]
        _above.sort(key=lambda x: x["price"])
        _below.sort(key=lambda x: -x["price"])

        # シナリオA: 下のSRでバウンス → BUY
        if _below:
            sup = _below[0]
            _tp_a = _above[0]["price"] if _above else round(sup["price"] + atr * 2.0, 3)
            _ea = _ema_alignment("BUY")
            dual_scenarios.append({
                "id": "A", "label": "サポート反発 → BUY",
                "direction": "BUY",
                "trigger_price": round(sup["price"], 3),
                "trigger_type": "bounce",
                "entry": round(sup["price"] + atr * 0.1, 3),
                "sl": round(sup["price"] - atr * 0.4, 3),
                "tp": round(_tp_a - atr * 0.05, 3),
                "sr_strength": sup["strength"],
                "sr_touches": sup["touches"],
                "rr": round(abs(_tp_a - sup["price"]) / max(atr * 0.4, 1e-6), 2),
                "condition": f"SR {sup['price']:.3f} (強度{sup['strength']:.0%}, {sup['touches']}回タッチ)で陽線反転",
                "master_aligned": _master_dir == "BUY",
                "ema_confidence": _ea,
                "combined_score": round(sup["strength"] * 0.5 + _ea / 100 * 0.5, 3),
            })

        # シナリオB: 上のSRでバウンス → SELL
        if _above:
            res = _above[0]
            _tp_b = _below[0]["price"] if _below else round(res["price"] - atr * 2.0, 3)
            _eb = _ema_alignment("SELL")
            dual_scenarios.append({
                "id": "B", "label": "レジスタンス反発 → SELL",
                "direction": "SELL",
                "trigger_price": round(res["price"], 3),
                "trigger_type": "bounce",
                "entry": round(res["price"] - atr * 0.1, 3),
                "sl": round(res["price"] + atr * 0.4, 3),
                "tp": round(_tp_b + atr * 0.05, 3),
                "sr_strength": res["strength"],
                "sr_touches": res["touches"],
                "rr": round(abs(res["price"] - _tp_b) / max(atr * 0.4, 1e-6), 2),
                "condition": f"SR {res['price']:.3f} (強度{res['strength']:.0%}, {res['touches']}回タッチ)で陰線反転",
                "master_aligned": _master_dir == "SELL",
                "ema_confidence": _eb,
                "combined_score": round(res["strength"] * 0.5 + _eb / 100 * 0.5, 3),
            })

        # シナリオC: 下のSRブレイク → SELL（Strong SRのみ）
        if _below and _below[0]["is_strong"] and _below[0]["touches"] >= 3:
            sup = _below[0]
            _next_sup = _below[1]["price"] if len(_below) > 1 else round(sup["price"] - atr * 2.0, 3)
            _ec = _ema_alignment("SELL")
            dual_scenarios.append({
                "id": "C", "label": "サポート下抜け → SELL",
                "direction": "SELL",
                "trigger_price": round(sup["price"], 3),
                "trigger_type": "breakout",
                "entry": round(sup["price"] - atr * 0.1, 3),
                "sl": round(sup["price"] + atr * 0.3, 3),
                "tp": round(_next_sup + atr * 0.05, 3),
                "sr_strength": sup["strength"],
                "sr_touches": sup["touches"],
                "rr": round(abs(sup["price"] - _next_sup) / max(atr * 0.3, 1e-6), 2),
                "condition": f"SR {sup['price']:.3f} (強度{sup['strength']:.0%})を終値で下抜け＋出来高増",
                "master_aligned": _master_dir == "SELL",
                "ema_confidence": _ec,
                "combined_score": round(sup["strength"] * 0.5 + _ec / 100 * 0.5, 3),
            })

        # シナリオD: 上のSRブレイク → BUY（Strong SRのみ）
        if _above and _above[0]["is_strong"] and _above[0]["touches"] >= 3:
            res = _above[0]
            _next_res = _above[1]["price"] if len(_above) > 1 else round(res["price"] + atr * 2.0, 3)
            _ed = _ema_alignment("BUY")
            dual_scenarios.append({
                "id": "D", "label": "レジスタンス上抜け → BUY",
                "direction": "BUY",
                "trigger_price": round(res["price"], 3),
                "trigger_type": "breakout",
                "entry": round(res["price"] + atr * 0.1, 3),
                "sl": round(res["price"] - atr * 0.3, 3),
                "tp": round(_next_res - atr * 0.05, 3),
                "sr_strength": res["strength"],
                "sr_touches": res["touches"],
                "rr": round(abs(_next_res - res["price"]) / max(atr * 0.3, 1e-6), 2),
                "condition": f"SR {res['price']:.3f} (強度{res['strength']:.0%})を終値で上抜け＋出来高増",
                "master_aligned": _master_dir == "BUY",
                "ema_confidence": _ed,
                "combined_score": round(res["strength"] * 0.5 + _ed / 100 * 0.5, 3),
            })

        # combined_score降順でソート → 最初がベストシナリオ
        dual_scenarios.sort(key=lambda x: x["combined_score"], reverse=True)
        # ベストシナリオにフラグ付与
        if dual_scenarios:
            dual_scenarios[0]["recommended"] = True
            for sc in dual_scenarios[1:]:
                sc["recommended"] = False
    except Exception as e:
        print(f"[DualScenario] {e}")

    # ── SR Entry Map: 現在価格から見た上下SR＋推奨エントリー根拠 ──
    sr_entry_map = {"nearest_support": None, "nearest_resistance": None,
                    "current_zone": "neutral", "recommended": None}
    try:
        _sr_all = find_sr_levels_weighted(
            df, window=5, tolerance_pct=0.003, min_touches=2,
            max_levels=10, bars_per_day=96 if "15m" in tf or "30m" in tf else 24)
        _sr_sup = sorted([s for s in _sr_all if s["price"] < entry - atr * 0.05],
                         key=lambda x: -x["price"])
        _sr_res = sorted([s for s in _sr_all if s["price"] > entry + atr * 0.05],
                         key=lambda x: x["price"])
        if _sr_sup:
            s0 = _sr_sup[0]
            dist_pips = round((entry - s0["price"]) * 100, 1)
            sr_entry_map["nearest_support"] = {
                "price": round(s0["price"], 3), "strength": s0["strength"],
                "touches": s0["touches"], "is_strong": s0["is_strong"],
                "type": s0.get("type", "support"),
                "distance_pips": dist_pips,
                "action": "BUY反発" if dist_pips < atr * 100 * 0.5 else "待機",
            }
        if _sr_res:
            r0 = _sr_res[0]
            dist_pips = round((r0["price"] - entry) * 100, 1)
            sr_entry_map["nearest_resistance"] = {
                "price": round(r0["price"], 3), "strength": r0["strength"],
                "touches": r0["touches"], "is_strong": r0["is_strong"],
                "type": r0.get("type", "resistance"),
                "distance_pips": dist_pips,
                "action": "SELL反発" if dist_pips < atr * 100 * 0.5 else "待機",
            }
        # 現在価格のゾーン判定
        if _sr_sup and _sr_res:
            sup_d = entry - _sr_sup[0]["price"]
            res_d = _sr_res[0]["price"] - entry
            range_w = sup_d + res_d
            if range_w > 0:
                pos_ratio = sup_d / range_w  # 0=サポート付近, 1=レジスタンス付近
                if pos_ratio < 0.25:
                    sr_entry_map["current_zone"] = "support_near"
                elif pos_ratio > 0.75:
                    sr_entry_map["current_zone"] = "resistance_near"
                elif 0.4 <= pos_ratio <= 0.6:
                    sr_entry_map["current_zone"] = "mid_range"
                else:
                    sr_entry_map["current_zone"] = "neutral"
        # 推奨エントリー: デュアルシナリオの★推奨をそのまま引用
        if dual_scenarios:
            rec = dual_scenarios[0]
            sr_entry_map["recommended"] = {
                "direction": rec["direction"],
                "entry": rec["entry"],
                "sl": rec["sl"],
                "tp": rec["tp"],
                "rr": rec["rr"],
                "label": rec["label"],
                "condition": rec["condition"],
                "ema_confidence": rec.get("ema_confidence", 0),
                "sr_basis": rec["trigger_price"],
            }
    except Exception as e:
        print(f"[SREntryMap] {e}")

    # ── 金曜フィルター: 週末前はDTを時間帯別にブロック ──
    if signal != "WAIT":
        try:
            _dt_fri_bar = bar_time if bar_time else datetime.now(timezone.utc)
            _dt_fri_dow = _dt_fri_bar.weekday() if hasattr(_dt_fri_bar, 'weekday') else df.index[-1].weekday()
            if _dt_fri_dow == 4:  # 金曜日
                _dt_fri_h = _dt_fri_bar.hour if hasattr(_dt_fri_bar, 'hour') else 12
                if _dt_fri_h < 7 and _dt_entry_type in ("sr_fib_confluence", "dual_sr_bounce", "dual_sr_breakout"):
                    # 金曜東京(UTC0-6): SR系エントリーをブロック（低流動性で偽シグナル多発）
                    signal = "WAIT"
                    conf = 20
                    reasons.append(f"🚫 金曜{_dt_fri_h}UTC: SR系DT({_dt_entry_type})ブロック")
                elif _dt_fri_h >= 18:
                    # 金曜UTC18以降: 全シグナルブロック（クローズ間近）
                    signal = "WAIT"
                    conf = 20
                    reasons.append(f"🚫 金曜{_dt_fri_h}UTC: DTクローズ前ブロック")
        except Exception:
            pass

    return {
        "timestamp": ts_str, "symbol": "USD/JPY", "tf": tf,
        "entry": round(entry, 3), "signal": signal, "confidence": conf,
        "sl": sl, "tp": tp, "rr_ratio": rr, "atr": round(atr, 3),
        "session": session, "htf_bias": htf, "swing_mode": tf in ("1h","4h","1d"),
        "reasons": reasons, "mode": "daytrade",
        "entry_type": _dt_entry_type,
        "dual_scenarios": dual_scenarios,
        "sr_entry_map": sr_entry_map,
        "score": round(score, 3),
        "indicators": {
            "ema9": round(ema9,3), "ema21": round(ema21,3),
            "ema50": round(ema50,3), "ema200": round(ema200,3),
            "adx": round(adx,1), "rsi": round(rsi,1),
            "macd": round(float(row["macd"]),5),
            "macd_sig": round(float(row["macd_sig"]),5),
            "macd_hist": round(macdh,5),
            "bb_upper": round(float(row["bb_upper"]),3),
            "bb_mid": round(float(row["bb_mid"]),3),
            "bb_lower": round(float(row["bb_lower"]),3),
            "bb_pband": round(bbpb,3),
        },
        "daytrade_info": {
            "adx": round(adx,1), "adx_pos": round(adx_p,1), "adx_neg": round(adx_n,1),
            "ema200": round(ema200,3),
            "fib": fib if fib else {},
            "score": round(score,3),
        },
        "htf_bias_daytrade": htf_dt,
        "layer_status": {
            "layer0": layer0,
            "layer1": layer1,
            "master_bias": layer1.get("label", "—"),
            "trade_ok":    not layer0["prohibited"],
        },
        "regime": regime,
        "layer2": layer2,
        "layer3": layer3,
        "fundamental": fund_detail,
        "institutional": inst_detail,
        "score_detail": {
            "combined": round(score,3), "rule": round(max(-1,min(1,score/5)),3),
        },
    }


# ═══════════════════════════════════════════════════════
#  1Hゾーンベーストレーディングシグナル
#  Buy/Sell Zone: 前日のPivot Points + ATR で毎日再計算
#  ゾーン内でのみリバーサルシグナルを生成
# ═══════════════════════════════════════════════════════
def compute_1h_zone_signal(df: pd.DataFrame,
                           buy_zone: tuple,
                           sell_zone: tuple,
                           sr_levels: list,
                           backtest_mode: bool = False) -> dict:
    """
    1H Zone-Based Multi-Strategy Signal Generator (v2)
    学術論文ベースの3戦略を統合。TP 15-100+ pip/trade。

    戦略1: Multi-TF Momentum (Moskowitz, Ooi & Pedersen 2012 JFE)
      - Daily trend方向 (EMA50/200) → 1h pullback entry
      - TP: 次のS/Rレベル or ATR×3.0 (40-100pip)
      - SL: Swing Low/High + ATR×0.3 (20-35pip)

    戦略2: Session Opening Range Breakout (Ito & Hashimoto 2006 NBER)
      - アジアセッション(00-07UTC)レンジ突破 at London Open
      - TP: Asian range × 1.5 or ATR×2.5 (30-80pip)
      - SL: Asian range反対側 (15-25pip)

    戦略3: Pivot Breakout (Osler 2000 NY Fed)
      - Daily Pivot R1/S1突破 + ATR拡大確認
      - TP: 次のPivotレベル(R2/S2) (30-60pip)
      - SL: 突破Pivotレベル裏 + buffer (15-25pip)

    ゾーン: Buy Zone(Pivot以下)=BUYのみ, Sell Zone(Pivot以上)=SELLのみ
    """
    if len(df) < 30:
        return {"signal": "WAIT", "entry": 0, "sl": 0, "tp": 0,
                "confidence": 0, "entry_type": "wait", "reasons": [],
                "indicators": {}, "atr": 0.1, "zone_info": {}}

    row   = df.iloc[-1]
    entry = float(row["Close"])
    atr   = float(row.get("atr", 0.10))
    rsi   = float(row.get("rsi", 50))
    rsi5  = float(row.get("rsi5", rsi))
    stoch_k = float(row.get("stoch_k", 50))
    stoch_d = float(row.get("stoch_d", 50))
    macdh   = float(row.get("macd_hist", 0))
    bb_pctb = float(row.get("bb_pband", 0.5))
    ema9  = float(row.get("ema9", entry))
    ema21 = float(row.get("ema21", entry))
    ema50 = float(row.get("ema50", entry))
    ema200_1h = float(row.get("ema200", ema50))
    adx   = float(row.get("adx", 20))
    _open = float(row["Open"])
    _high = float(row["High"])
    _low  = float(row["Low"])

    prev_macdh = float(df.iloc[-2].get("macd_hist", 0)) if len(df) >= 2 else 0.0
    prev2_macdh = float(df.iloc[-3].get("macd_hist", 0)) if len(df) >= 3 else prev_macdh
    prev_stoch_k = float(df.iloc[-2].get("stoch_k", 50)) if len(df) >= 2 else 50

    # 1h足のバー時刻（UTC hour）
    _bar_time = df.index[-1]
    _hour_utc = _bar_time.hour if hasattr(_bar_time, 'hour') else 12

    # 時間帯フィルター: UTC 0,1,21は損失集中帯 → エントリー禁止
    if _hour_utc in (0, 1, 21):
        return {"signal": "WAIT", "entry": entry, "sl": 0.0, "tp": 0.0,
                "confidence": 0, "entry_type": "wait",
                "reasons": [f"⛔ 損失集中時間帯(UTC {_hour_utc}) → WAIT"],
                "indicators": {}, "atr": atr, "zone_info": {}}

    base = {
        "signal": "WAIT", "entry": entry, "sl": 0.0, "tp": 0.0,
        "confidence": 0, "entry_type": "wait", "reasons": [],
        "indicators": {
            "rsi": round(rsi, 1), "stoch_k": round(stoch_k, 1),
            "stoch_d": round(stoch_d, 1), "macdh": round(macdh, 5),
            "bb_pctb": round(bb_pctb, 3), "atr": round(atr, 4), "adx": round(adx, 1),
        },
        "atr": atr,
        "zone_info": {
            "buy_zone": buy_zone, "sell_zone": sell_zone,
            "current_zone": "neutral",
        },
    }

    bz_lo, bz_hi = buy_zone  # buy_zone = (prev_L - buffer, Pivot)
    sz_lo, sz_hi = sell_zone  # sell_zone = (Pivot, prev_H + buffer)
    _pivot = bz_hi  # Pivot = Buy Zone上限 = Sell Zone下限

    # Pivot levels (R1, R2, S1, S2)
    _prev_h = sz_hi - (sz_hi - _pivot) * 0.2 / 1.2 if sz_hi != _pivot else _pivot + atr
    _prev_l = bz_lo + (_pivot - bz_lo) * 0.2 / 1.2 if bz_lo != _pivot else _pivot - atr
    # 近似: R1 = 2*P - L, S1 = 2*P - H, R2 = P + (H-L), S2 = P - (H-L)
    _daily_range = _prev_h - _prev_l
    _R1 = 2 * _pivot - _prev_l
    _S1 = 2 * _pivot - _prev_h
    _R2 = _pivot + _daily_range
    _S2 = _pivot - _daily_range

    in_buy_zone  = entry <= _pivot
    in_sell_zone = entry > _pivot
    base["zone_info"]["current_zone"] = "buy_zone" if in_buy_zone else "sell_zone"

    # ── Swing High/Low 検出 (直近20バー) ──
    _lookback = min(20, len(df) - 1)
    _recent_lows = [float(df.iloc[-(j+1)]["Low"]) for j in range(_lookback)]
    _recent_highs = [float(df.iloc[-(j+1)]["High"]) for j in range(_lookback)]
    _swing_low = min(_recent_lows) if _recent_lows else entry - atr
    _swing_high = max(_recent_highs) if _recent_highs else entry + atr

    # ── Asian Range (00-07 UTC) for Session Breakout ──
    _asia_high, _asia_low = None, None
    for j in range(min(24, len(df) - 1)):
        _bj = df.iloc[-(j+1)]
        _bj_time = df.index[-(j+1)]
        _bj_hour = _bj_time.hour if hasattr(_bj_time, 'hour') else -1
        if 0 <= _bj_hour < 7:
            _h = float(_bj["High"])
            _l = float(_bj["Low"])
            if _asia_high is None or _h > _asia_high:
                _asia_high = _h
            if _asia_low is None or _l < _asia_low:
                _asia_low = _l
    _asia_range = (_asia_high - _asia_low) if _asia_high and _asia_low else atr * 2

    # ── ATR拡大チェック (ブレイクアウト確認用) ──
    _atr_sma = np.mean([float(df.iloc[-(j+1)].get("atr", atr)) for j in range(min(20, len(df)-1))])
    _atr_expanding = atr > _atr_sma * 1.1  # ATRが20期間平均の110%以上

    # ── 候補リスト: (signal, score, tp, sl, reasons, entry_type) ──
    candidates = []

    # ════════════════════════════════════════════════════════════
    #  戦略1: EMAラグ・コントラリアン (旧mtf_momentum改良)
    #  核心: EMAはラグする → EMAがまだ弱気なのに価格が中期EMA上 = 転換BUY
    #  v6: デュアル基準（EMA200 + EMA50）で両方向シグナル発生
    #       EMA200合致: base=1.5 (高信頼)
    #       EMA50のみ: base=1.0 (低信頼→他の確認が全部必要)
    #       → 上昇相場でもSELL発生、下降相場でもBUY発生
    # ════════════════════════════════════════════════════════════
    _ema50_1h = float(df["ema50"].iloc[-1]) if "ema50" in df.columns else ema21
    # ── 転換BUY: EMAはまだ弱気整列だが、価格は中期EMA上に反発 ──
    if (ema9 < ema21 and adx >= 15):
        _mt_above_200 = entry > ema200_1h
        _mt_above_50 = entry > _ema50_1h
        if _mt_above_200 or _mt_above_50:
            _mt_score = 0.0
            _mt_reasons = []
            # EMA200合致: 高信頼ベース
            if _mt_above_200:
                _mt_score += 1.5
                _mt_reasons.append(f"✅ EMAラグ転換BUY: 価格>EMA200({ema200_1h:.3f})")
            # EMA50のみ: 低信頼ベース（他の確認が全部ないと閾値に届かない）
            elif _mt_above_50:
                _mt_score += 1.0
                _mt_reasons.append(f"✅ EMAラグ転換BUY: 価格>EMA50({_ema50_1h:.3f})")
                if entry > ema200_1h:
                    _mt_score += 0.3
                    _mt_reasons.append("✅ EMA200上: 中期トレンド一致")

            # EMA50/200近辺リテスト
            _ref_ema = ema200_1h if _mt_above_200 else _ema50_1h
            _ref_dist = (entry - _ref_ema) / atr if atr > 0 else 0
            if 0 < _ref_dist < 1.5:
                _mt_score += 0.5
                _mt_reasons.append(f"✅ EMAリテスト圏(距離={_ref_dist:.1f}ATR)")

            if macdh > prev_macdh:
                _mt_score += 0.5
                _mt_reasons.append("✅ MACD-H改善: モメンタム転換確認")

            if rsi > 40 and rsi < 65:
                _mt_score += 0.3
                _mt_reasons.append(f"✅ RSI回復圏({rsi:.0f})")

            if entry > _open:
                _mt_score += 0.3
                _mt_reasons.append("✅ 陽線: 反発確認")

            if stoch_k > stoch_d:
                _mt_score += 0.3

            if _mt_score >= 2.5:
                _mt_tp = entry + atr * 3.0
                _mt_sl = entry - atr * 1.0
                _mt_inv = _ref_ema - atr * 0.1  # 基準EMAの少し下
                candidates.append(("BUY", _mt_score, _mt_tp, _mt_sl, _mt_reasons, "mtf_momentum", _mt_inv))

    # ── 転換SELL: EMAはまだ強気整列だが、価格は中期EMA下に崩落 ──
    if (ema9 > ema21 and adx >= 15):
        _mt_below_200 = entry < ema200_1h
        _mt_below_50 = entry < _ema50_1h
        if _mt_below_200 or _mt_below_50:
            _mt_score = 0.0
            _mt_reasons = []
            if _mt_below_200:
                _mt_score += 1.5
                _mt_reasons.append(f"✅ EMAラグ転換SELL: 価格<EMA200({ema200_1h:.3f})")
            elif _mt_below_50:
                _mt_score += 1.0
                _mt_reasons.append(f"✅ EMAラグ転換SELL: 価格<EMA50({_ema50_1h:.3f})")
                if entry < ema200_1h:
                    _mt_score += 0.3
                    _mt_reasons.append("✅ EMA200下: 中期トレンド一致")

            _ref_ema = ema200_1h if _mt_below_200 else _ema50_1h
            _ref_dist = (_ref_ema - entry) / atr if atr > 0 else 0
            if 0 < _ref_dist < 1.5:
                _mt_score += 0.5
                _mt_reasons.append(f"✅ EMAリテスト圏(距離={_ref_dist:.1f}ATR)")

            if macdh < prev_macdh:
                _mt_score += 0.5
                _mt_reasons.append("✅ MACD-H悪化: モメンタム崩壊確認")

            if rsi > 35 and rsi < 60:
                _mt_score += 0.3
                _mt_reasons.append(f"✅ RSI中立圏({rsi:.0f})")

            if entry < _open:
                _mt_score += 0.3
                _mt_reasons.append("✅ 陰線: 崩落確認")

            if stoch_k < stoch_d:
                _mt_score += 0.3

            if _mt_score >= 2.5:
                _mt_tp = entry - atr * 3.0
                _mt_sl = entry + atr * 1.0
                _mt_inv = _ref_ema + atr * 0.1
                candidates.append(("SELL", _mt_score, _mt_tp, _mt_sl, _mt_reasons, "mtf_momentum", _mt_inv))

    # ════════════════════════════════════════════════════════════
    #  戦略2: Session ORB — London Open Breakout (Ito & Hashimoto 2006)
    #  アジアレンジ(00-07UTC)突破 at 07-10 UTC
    #  TP: Asian range × 1.5 or ATR×2.5 (30-80pip)
    #  SL: Asian range反対側 (15-25pip)
    # ════════════════════════════════════════════════════════════
    if False and 7 <= _hour_utc <= 14 and _asia_high and _asia_low and _asia_range > atr * 0.2:  # DISABLED: WR=36.6% → ATR EVドラッグ
        # Bullish breakout: 1h終値がアジアHigh超え
        if entry > _asia_high:
            _orb_score = 1.5
            _orb_reasons = []
            _orb_reasons.append(f"✅ ロンドンORB: アジアHigh突破({_asia_high:.3f}) [Ito&Hashimoto 2006]")

            if _atr_expanding:
                _orb_score += 0.5
                _orb_reasons.append(f"✅ ATR拡大確認(ATR={atr:.4f} > SMA×1.1)")
            if entry > _open:
                _orb_score += 0.5
                _orb_reasons.append("✅ 陽線ブレイク")
            if adx >= 15:
                _orb_score += 0.3
            if ema9 > ema21:
                _orb_score += 0.3
                _orb_reasons.append("✅ EMAトレンド整合")
            # ブレイクの強さ: アジアHigh超え幅
            _break_dist = entry - _asia_high
            if _break_dist > atr * 0.2:
                _orb_score += 0.3
                _orb_reasons.append(f"✅ 強いブレイク(+{_break_dist:.3f})")

            if _orb_score >= 2.0:
                _orb_tp = entry + max(_asia_range * 1.5, atr * 2.0)
                _orb_sl = _asia_low + atr * 0.1  # アジアLow近辺
                _orb_sl = max(_orb_sl, entry - atr * 1.2)  # 最大SL制限
                _orb_sl = min(_orb_sl, entry - atr * 0.3)  # 最小SL
                candidates.append(("BUY", _orb_score, _orb_tp, _orb_sl, _orb_reasons, "session_orb"))

        # Bearish breakout: 1h終値がアジアLow割れ
        elif entry < _asia_low:
            _orb_score = 1.5
            _orb_reasons = []
            _orb_reasons.append(f"✅ ロンドンORB: アジアLow割れ({_asia_low:.3f}) [Ito&Hashimoto 2006]")

            if _atr_expanding:
                _orb_score += 0.5
                _orb_reasons.append(f"✅ ATR拡大確認(ATR={atr:.4f} > SMA×1.1)")
            if entry < _open:
                _orb_score += 0.5
                _orb_reasons.append("✅ 陰線ブレイク")
            if adx >= 15:
                _orb_score += 0.3
            if ema9 < ema21:
                _orb_score += 0.3
                _orb_reasons.append("✅ EMAトレンド整合")
            _break_dist = _asia_low - entry
            if _break_dist > atr * 0.2:
                _orb_score += 0.3
                _orb_reasons.append(f"✅ 強いブレイク(+{_break_dist:.3f})")

            if _orb_score >= 2.0:
                _orb_tp = entry - max(_asia_range * 1.5, atr * 2.0)
                _orb_sl = _asia_high - atr * 0.1
                _orb_sl = min(_orb_sl, entry + atr * 1.2)
                _orb_sl = max(_orb_sl, entry + atr * 0.3)
                candidates.append(("SELL", _orb_score, _orb_tp, _orb_sl, _orb_reasons, "session_orb"))

    # ════════════════════════════════════════════════════════════
    #  戦略3: Pivot Breakout (Osler 2000 NY Fed)
    #  Daily Pivot R1/S1突破 + ATR拡大
    #  TP: 次のPivotレベル(R2/S2) (30-60pip)
    #  SL: 突破レベル裏 + buffer (15-25pip)
    # ════════════════════════════════════════════════════════════
    # R1突破 → BUY (EMA整合必須、ATR expanding はボーナス)
    if entry > _R1 and 7 <= _hour_utc <= 20 and ema9 > ema21:
        _pv_score = 0.0
        _pv_reasons = []
        _pv_reasons.append(f"✅ Pivot R1突破({_R1:.3f}) [Osler 2000 NY Fed]")
        _pv_score += 1.5

        if entry > _open:
            _pv_score += 0.5
            _pv_reasons.append("✅ 陽線ブレイク")
        if adx >= 15:
            _pv_score += 0.3
        _pv_reasons.append("✅ EMAトレンド整合")
        _pv_score += 0.3
        if _atr_expanding:
            _pv_score += 0.5
            _pv_reasons.append("✅ ATR拡大(ボラ上昇)")
        if rsi > 50 and rsi < 75:
            _pv_score += 0.3

        if _pv_score >= 2.5:  # 旧2.0→2.5（高確信のみ）
            _pv_tp = _R1 + (_R2 - _R1) * 0.7  # 旧0.5→0.7: R2の70%地点
            _pv_tp = max(_pv_tp, entry + atr * 2.0)  # 旧1.5→2.0: 最低TP拡大
            _pv_sl = max(entry - atr * 0.8, _R1 - atr * 0.4)  # 旧0.5→0.8 ATR: ノイズ耐性
            # シナリオ崩壊: R1を下回ったらブレイク失敗
            _pv_inv = _R1 - atr * 0.15
            candidates.append(("BUY", _pv_score, _pv_tp, _pv_sl, _pv_reasons, "pivot_breakout", _pv_inv))

    # S1割れ → SELL (EMA整合必須)
    if entry < _S1 and 7 <= _hour_utc <= 20 and ema9 < ema21:
        _pv_score = 0.0
        _pv_reasons = []
        _pv_reasons.append(f"✅ Pivot S1割れ({_S1:.3f}) [Osler 2000 NY Fed]")
        _pv_score += 1.5

        if entry < _open:
            _pv_score += 0.5
            _pv_reasons.append("✅ 陰線ブレイク")
        if adx >= 15:
            _pv_score += 0.3
        _pv_reasons.append("✅ EMAトレンド整合")
        _pv_score += 0.3
        if _atr_expanding:
            _pv_score += 0.5
            _pv_reasons.append("✅ ATR拡大(ボラ上昇)")
        if rsi > 25 and rsi < 50:
            _pv_score += 0.3

        if _pv_score >= 2.5:  # 旧2.0→2.5
            _pv_tp = _S1 - (_S1 - _S2) * 0.7  # 旧0.5→0.7: S2の70%地点
            _pv_tp = min(_pv_tp, entry - atr * 2.0)  # 旧1.5→2.0: 最低TP拡大
            _pv_sl = min(entry + atr * 0.8, _S1 + atr * 0.4)  # 旧0.5→0.8 ATR: ノイズ耐性
            # シナリオ崩壊: S1を上回ったらブレイク失敗
            _pv_inv = _S1 + atr * 0.15
            candidates.append(("SELL", _pv_score, _pv_tp, _pv_sl, _pv_reasons, "pivot_breakout", _pv_inv))

    # ════════════════════════════════════════════════════════════
    #  戦略4: Pivot Zone Mean Reversion (Osler 2000 + BB/RSI)
    #  DISABLED: 30d BT WR=30% EV=-1.3p — 要改善
    #  Pivot S1/R1 反転 — ゾーン内での反発
    #  TP: Pivot (中央回帰) ATR×1.5-2.0 (40-55pip)
    #  SL: S1/R1 裏 + buffer (15-20pip)
    # ════════════════════════════════════════════════════════════
    # S1近辺で反発 → BUY (in buy zone, near S1)
    if False and in_buy_zone and abs(entry - _S1) < atr * 0.8 and entry > _S1:
        _rv_score = 0.0
        _rv_reasons = []
        _rv_reasons.append(f"✅ Pivot S1反発({_S1:.3f}) [Osler 2000]")
        _rv_score += 1.0

        if bb_pctb < 0.30:
            _rv_score += 1.0
            _rv_reasons.append(f"✅ BB%B={bb_pctb:.2f}<0.30(oversold)")
        elif bb_pctb < 0.40:
            _rv_score += 0.5
        if stoch_k > stoch_d:
            _rv_score += 0.5
            _rv_reasons.append("✅ Stoch GC")
        if entry > _open:
            _rv_score += 0.5
            _rv_reasons.append("✅ 陽線反転")
        if macdh > prev_macdh:
            _rv_score += 0.3

        if _rv_score >= 2.0:
            _rv_tp = _pivot  # Pivotまで回帰
            _rv_tp = max(_rv_tp, entry + atr * 1.5)
            _rv_sl = _S1 - atr * 0.4
            _rv_sl = min(_rv_sl, entry - atr * 0.6)
            candidates.append(("BUY", _rv_score, _rv_tp, _rv_sl, _rv_reasons, "pivot_reversion"))

    # R1近辺で反落 → SELL (in sell zone, near R1)
    if False and in_sell_zone and abs(entry - _R1) < atr * 0.8 and entry < _R1:
        _rv_score = 0.0
        _rv_reasons = []
        _rv_reasons.append(f"✅ Pivot R1反落({_R1:.3f}) [Osler 2000]")
        _rv_score += 1.0

        if bb_pctb > 0.70:
            _rv_score += 1.0
            _rv_reasons.append(f"✅ BB%B={bb_pctb:.2f}>0.70(overbought)")
        elif bb_pctb > 0.60:
            _rv_score += 0.5
        if stoch_k < stoch_d:
            _rv_score += 0.5
            _rv_reasons.append("✅ Stoch DC")
        if entry < _open:
            _rv_score += 0.5
            _rv_reasons.append("✅ 陰線反転")
        if macdh < prev_macdh:
            _rv_score += 0.3

        if _rv_score >= 2.0:
            _rv_tp = _pivot
            _rv_tp = min(_rv_tp, entry - atr * 1.5)
            _rv_sl = _R1 + atr * 0.4
            _rv_sl = max(_rv_sl, entry + atr * 0.6)
            candidates.append(("SELL", _rv_score, _rv_tp, _rv_sl, _rv_reasons, "pivot_reversion"))

    # ════════════════════════════════════════════════════════════
    #  戦略5: 1H Fibonacci Reversal（フィボリトレースメント反発）
    #  根拠: 120バー(5日)のスイングからのフィボ38.2%/50%/61.8%反発
    #  改善: SL拡大(ATR×0.8)、EMA整合必須、ADX≥15、Stoch確認
    # ════════════════════════════════════════════════════════════
    if len(df) >= 120 and adx >= 15:
        _1h_fib = _calc_fibonacci_levels(df, lookback=120)
        if _1h_fib and _1h_fib.get("trend"):
            _1h_fib_levels = {
                "38.2%": _1h_fib.get("r382", 0),
                "50.0%": _1h_fib.get("r500", 0),
                "61.8%": _1h_fib.get("r618", 0),
            }
            _1h_fib_touch = None
            for _fn, _fv in _1h_fib_levels.items():
                if _fv and abs(entry - _fv) < atr * 0.4:
                    _1h_fib_touch = (_fn, _fv)
                    break
            if _1h_fib_touch:
                _fn, _fv = _1h_fib_touch
                _1hfr_score = 0.0
                _1hfr_reasons = []
                # 上昇トレンド押し目買い: RSI + MACD方向転換
                if (_1h_fib["trend"] == "up" and rsi < 50 and macdh > prev_macdh):
                    _1hfr_score = 2.0
                    _1hfr_reasons.append(f"✅ 1H Fib {_fn}サポート反発({_fv:.3f})")
                    if _fn == "61.8%":
                        _1hfr_score += 0.8
                        _1hfr_reasons.append("✅ Fib61.8%最高確率ゾーン")
                    elif _fn == "50.0%":
                        _1hfr_score += 0.4
                    if ema9 > ema21:
                        _1hfr_score += 0.3
                        _1hfr_reasons.append("✅ EMA整合(9>21)")
                    if stoch_k > stoch_d:
                        _1hfr_score += 0.3
                        _1hfr_reasons.append("✅ Stoch反転確認")
                    if entry > _open:
                        _1hfr_score += 0.3
                        _1hfr_reasons.append("✅ 陽線確認")
                    if _1hfr_score >= 2.0:
                        _1hfr_tp = entry + atr * 3.0   # 旧2.5→3.0: 1Hトレンド利幅
                        _1hfr_sl = entry - atr * 1.2   # 旧0.8→1.2: ノイズ耐性
                        # シナリオ崩壊: Fibサポートを明確に下回ったら反発失敗
                        _1hfr_inv = _fv - atr * 0.3
                        candidates.append(("BUY", _1hfr_score, _1hfr_tp, _1hfr_sl, _1hfr_reasons, "h1_fib_reversal", _1hfr_inv))
                # 下降トレンド戻り売り
                elif (_1h_fib["trend"] == "down" and rsi > 50 and macdh < prev_macdh):
                    _1hfr_score = 2.0
                    _1hfr_reasons.append(f"✅ 1H Fib {_fn}レジスタンス反発({_fv:.3f})")
                    if _fn == "61.8%":
                        _1hfr_score += 0.8
                        _1hfr_reasons.append("✅ Fib61.8%最高確率ゾーン")
                    elif _fn == "50.0%":
                        _1hfr_score += 0.4
                    if ema9 < ema21:
                        _1hfr_score += 0.3
                        _1hfr_reasons.append("✅ EMA整合(9<21)")
                    if stoch_k < stoch_d:
                        _1hfr_score += 0.3
                        _1hfr_reasons.append("✅ Stoch反転確認")
                    if entry < _open:
                        _1hfr_score += 0.3
                        _1hfr_reasons.append("✅ 陰線確認")
                    if _1hfr_score >= 2.0:
                        _1hfr_tp = entry - atr * 3.0   # 旧2.5→3.0
                        _1hfr_sl = entry + atr * 1.2   # 旧0.8→1.2
                        # シナリオ崩壊: Fibレジスタンスを明確に上抜けされたら失敗
                        _1hfr_inv = _fv + atr * 0.3
                        candidates.append(("SELL", _1hfr_score, _1hfr_tp, _1hfr_sl, _1hfr_reasons, "h1_fib_reversal", _1hfr_inv))

    # ════════════════════════════════════════════════════════════
    #  戦略6: EMA200 Trend Reversal（1Hトレンド転換）
    #  根拠: EMA200ブレイク後のリテスト・反発
    #  改善: SL拡大(0.8ATR)、EMA整合+ADX+Stoch必須、スコア閾値2.5
    # ════════════════════════════════════════════════════════════
    if len(df) >= 20 and "ema200" in df.columns and adx >= 15:
        _1h_e200_dist = (entry - ema200_1h) / atr if atr > 0 else 0
        _1h_e200_bull = entry > ema200_1h
        _1h_e200_slope = (ema200_1h - float(df["ema200"].iloc[-min(20, len(df)-1)])) if len(df) >= 2 else 0
        # 直近20バーでEMA200クロス検出
        _1h_crosses = 0
        for _ci in range(max(1, len(df) - 20), len(df)):
            _pc = float(df["Close"].iloc[_ci - 1])
            _cc = float(df["Close"].iloc[_ci])
            _pe = float(df["ema200"].iloc[_ci - 1])
            _ce = float(df["ema200"].iloc[_ci])
            if (_pc < _pe and _cc > _ce) or (_pc > _pe and _cc < _ce):
                _1h_crosses += 1

        if _1h_crosses >= 1 and abs(_1h_e200_dist) < 0.5:
            _1htr_score = 0.0
            _1htr_reasons = []
            # 上抜けリテスト → BUY: EMA整合 + Stoch確認必須
            if (_1h_e200_bull and _1h_e200_dist < 0.5 and macdh > prev_macdh
                    and rsi < 55 and ema9 > ema21 and stoch_k > stoch_d):
                _1htr_score = 2.0
                _1htr_reasons.append(f"✅ 1H EMA200上抜けリテスト({ema200_1h:.3f})")
                if _1h_e200_slope > 0:
                    _1htr_score += 0.5
                    _1htr_reasons.append("✅ EMA200上昇中: トレンド転換確認")
                _1htr_reasons.append(f"✅ EMA整合(9>21) + Stoch反転")
                if entry > _open:
                    _1htr_score += 0.3
                    _1htr_reasons.append("✅ 陽線確認")
                if _1htr_score >= 2.0:
                    _1htr_tp = entry + atr * 3.0   # 旧2.5→3.0
                    _1htr_sl = entry - atr * 1.2   # 旧0.8→1.2
                    # シナリオ崩壊: EMA200を明確に下回ったらリテスト失敗
                    _1htr_inv = ema200_1h - atr * 0.2
                    candidates.append(("BUY", _1htr_score, _1htr_tp, _1htr_sl, _1htr_reasons, "h1_ema200_trend_reversal", _1htr_inv))
            # 下抜けリテスト → SELL
            elif (not _1h_e200_bull and _1h_e200_dist > -0.5 and macdh < prev_macdh
                    and rsi > 45 and ema9 < ema21 and stoch_k < stoch_d):
                _1htr_score = 2.0
                _1htr_reasons.append(f"✅ 1H EMA200下抜けリテスト({ema200_1h:.3f})")
                if _1h_e200_slope < 0:
                    _1htr_score += 0.5
                    _1htr_reasons.append("✅ EMA200下降中: トレンド転換確認")
                _1htr_reasons.append(f"✅ EMA整合(9<21) + Stoch反転")
                if entry < _open:
                    _1htr_score += 0.3
                    _1htr_reasons.append("✅ 陰線確認")
                if _1htr_score >= 2.0:
                    _1htr_tp = entry - atr * 3.0   # 旧2.5→3.0
                    _1htr_sl = entry + atr * 1.2   # 旧0.8→1.2
                    # シナリオ崩壊: EMA200を明確に上回ったらリテスト失敗
                    _1htr_inv = ema200_1h + atr * 0.2
                    candidates.append(("SELL", _1htr_score, _1htr_tp, _1htr_sl, _1htr_reasons, "h1_ema200_trend_reversal", _1htr_inv))

    # ── 最高スコア候補を採用 ──
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        best = candidates[0]
        sig, score, tp, sl, reasons, etype = best[:6]
        # 7番目: シナリオ無効化価格（存在する場合）
        _invalidation = best[6] if len(best) > 6 else None

        # ── EMA200 方向フィルター（1H Zone用）──
        _h1_bull200 = entry > ema200_1h
        if sig == "BUY" and not _h1_bull200:
            if etype in ("h1_fib_reversal", "h1_ema200_trend_reversal"):
                base["signal"] = "WAIT"
                reasons.append(f"🚫 EMA200下({ema200_1h:.3f})で逆張りBUY → ブロック")
                return base
            score *= 0.75
            reasons.append(f"⚠️ EMA200下({ema200_1h:.3f})でBUY → 減衰")
        elif sig == "SELL" and _h1_bull200:
            if etype in ("h1_fib_reversal", "h1_ema200_trend_reversal"):
                # Fib/EMA200逆張りSELL + EMA200上 → 本番で全敗 → ハードブロック
                base["signal"] = "WAIT"
                reasons.append(f"🚫 EMA200上({ema200_1h:.3f})で逆張りSELL → ブロック")
                return base
            score *= 0.75
            reasons.append(f"⚠️ EMA200上({ema200_1h:.3f})でSELL → 減衰")

        base["signal"]     = sig
        base["entry"]      = entry
        base["tp"]         = round(tp, 3)
        base["sl"]         = round(sl, 3)
        base["confidence"] = int(min(score * 18, 95))
        base["entry_type"] = etype
        base["reasons"]    = reasons
        # ── シナリオ崩壊撤退レベル ──
        # BUY: この価格を下回ったらシナリオ崩壊→即撤退
        # SELL: この価格を上回ったらシナリオ崩壊→即撤退
        if _invalidation is not None:
            base["invalidation"] = round(_invalidation, 3)

    return base


# ═══════════════════════════════════════════════════════
#  スイングトレードシグナル（4h/1d）
#  学術根拠:
#   - 12-1ヶ月モメンタム: 年率10%超過リターン (Menkhoff et al. 2012 JFE)
#   - EMA200 + フィボ61.8%: 最高確率エントリーゾーン
#   - RSIダイバージェンス: 55-65%勝率 (10年FXバックテスト)
#   - ダウ理論構造: 高値・安値の連鎖確認
# ═══════════════════════════════════════════════════════
def compute_swing_signal(df: pd.DataFrame, tf: str, sr_levels: list,
                         symbol: str = "USDJPY=X",
                         backtest_mode: bool = False,
                         bar_time=None,
                         htf_cache: dict = None) -> dict:
    row   = df.iloc[-1]
    entry = float(row["Close"])
    atr   = float(row["atr"])

    ema21  = float(row["ema21"])
    ema50  = float(row["ema50"])
    ema200 = float(row.get("ema200", row["ema50"]))
    adx    = float(row.get("adx", 20.0))
    rsi    = float(row["rsi"])
    macdh  = float(row["macd_hist"])
    macdh_prev = float(df["macd_hist"].iloc[-2]) if len(df) > 1 else 0.0

    score   = 0.0
    reasons = []

    # ① EMA200マスタートレンドフィルター（最重要）
    bull200 = entry > ema200
    ema200_slope = float(df["ema200"].iloc[-1]) - float(df["ema200"].iloc[-min(20,len(df)-1)])
    if bull200 and ema200_slope > 0:
        score += 2.0; reasons.append(f"✅ EMA200({ema200:.3f})上位+上昇: スイング上昇バイアス")
    elif not bull200 and ema200_slope < 0:
        score -= 2.0; reasons.append(f"🔻 EMA200({ema200:.3f})下位+下降: スイング下降バイアス")
    elif bull200:
        score += 0.8; reasons.append(f"↗ EMA200上位（スロープ弱）")
    else:
        score -= 0.8; reasons.append(f"↘ EMA200下位（スロープ弱）")

    # ①b Faber (2007) + Moskowitz TSMOM — 暴落時のハードフィルター
    # 条件: 価格<EMA21 AND EMA21下降 AND 直近3日下落 → BUY完全ブロック
    ema21_slope = ema21 - float(df["ema21"].iloc[-min(5, len(df)-1)])
    _dist_below_ema21 = (ema21 - entry) / max(atr, 1e-6)
    _ema21_falling = ema21_slope < -atr * 0.05
    _sw_buy_blocked = False  # BUYブロックフラグ

    _short_ret = 0.0
    if len(df) >= 16:
        _short_ret = (entry - float(df["Close"].iloc[-16])) / float(df["Close"].iloc[-16])

    # 条件A: 価格がEMA21下 + EMA21下降中 + 直近下落
    if _dist_below_ema21 > 0.3 and _ema21_falling and _short_ret < -0.003:
        _sw_buy_blocked = True
        reasons.append(f"🛡️ Faber+TSMOM: EMA21下{_dist_below_ema21:.1f}ATR+下降+短期{_short_ret*100:.1f}% → BUY禁止")

    # 条件B: EMA21 < EMA50 かつ価格がEMA50を大幅に下回る(>1ATR) → 中期反転確定
    if entry < ema50 and ema21 < ema50 and (ema50 - entry) > atr * 1.0:
        _sw_buy_blocked = True
        reasons.append(f"🛡️ 中期反転: 価格EMA50下{(ema50-entry)/atr:.1f}ATR+EMA21<50 → BUY禁止")


    # ② 12-1ヶ月モメンタム (Menkhoff et al. 2012)
    if len(df) >= 240:  # 約1年分（1h足なら多め）
        mom_close = float(df["Close"].iloc[-min(240,len(df)-22)])
        skip_close = float(df["Close"].iloc[-min(22,len(df)-1)])
        mom_sig = (skip_close - mom_close) / max(abs(mom_close), 1e-6)
        if mom_sig > 0.005:
            score += 1.5; reasons.append(f"✅ 12-1モメンタム正({mom_sig*100:.1f}%): トレンド継続バイアス")
        elif mom_sig < -0.005:
            score -= 1.5; reasons.append(f"🔻 12-1モメンタム負({mom_sig*100:.1f}%): 下落継続バイアス")

    # ③ EMAアライメント（中期トレンド方向）
    if ema21 > ema50:
        score += 1.0; reasons.append(f"✅ EMA21({ema21:.3f})>EMA50({ema50:.3f}): 中期上昇")
    else:
        score -= 1.0; reasons.append(f"🔻 EMA21({ema21:.3f})<EMA50({ema50:.3f}): 中期下落")

    # ④ フィボナッチ61.8%プルバック（最高確率: 70%のケースで反発 per Elliott literature）
    fib = _calc_fibonacci_levels(df, lookback=120)
    fib_hit = False
    if fib:
        r618 = fib.get("r618"); r382 = fib.get("r382"); r786 = fib.get("r786")
        if r618 and abs(entry - r618) < atr * 0.8:
            score += 2.0; fib_hit = True
            reasons.append(f"✅ フィボ61.8%({r618:.3f})近辺: 最高確率リトレースゾーン")
        elif r382 and abs(entry - r382) < atr * 0.8:
            score += 1.0; fib_hit = True
            reasons.append(f"↗ フィボ38.2%({r382:.3f})近辺: 押し目エントリーゾーン")

    # ⑤ RSIダイバージェンス（55-65%勝率: 10年FXバックテスト）
    div_sc, div_rsns = detect_divergence(df)
    if abs(div_sc) > 0:
        score += div_sc * 1.5
        reasons.extend(div_rsns[:2])

    # ⑥ RSI過熱ゾーンフィルター（スイング: 80/20を使用）
    if bull200:  # 上昇バイアス
        if rsi < 30:
            score += 1.5; reasons.append(f"✅ RSI{rsi:.0f}: 深い押し目（スイング買い好機）")
        elif rsi < 45:
            score += 0.8; reasons.append(f"↗ RSI{rsi:.0f}: 適度な押し目")
        elif rsi > 78:
            score -= 1.0; reasons.append(f"⚠️ RSI{rsi:.0f}: 過買い → 追い買い回避")
    else:  # 下降バイアス
        if rsi > 70:
            score -= 1.5; reasons.append(f"🔻 RSI{rsi:.0f}: 深い戻り売り好機")
        elif rsi > 55:
            score -= 0.8; reasons.append(f"↘ RSI{rsi:.0f}: 戻り売り機会")
        elif rsi < 22:
            score += 1.0; reasons.append(f"⚠️ RSI{rsi:.0f}: 過売り → 追い売り回避")

    # ⑦ MACDヒスト転換（スイング確認用）
    if macdh > 0 and macdh > macdh_prev:
        score += 0.8; reasons.append("✅ MACDヒスト上向き: 買いモメンタム加速")
    elif macdh < 0 and macdh < macdh_prev:
        score -= 0.8; reasons.append("🔻 MACDヒスト下向き: 売りモメンタム加速")

    # ⑧ ローソク足パターン（大きな確認）
    candle_sc, candle_rsns = detect_candle_patterns(df)
    if abs(candle_sc) > 1.0:
        score += candle_sc * 0.5
        reasons.extend(candle_rsns[:1])

    # ⑧b S/R近接ボーナス（スイングではSR反発が最高精度）
    _near_sr_level = None
    for _sr_lv in sr_levels:
        if abs(entry - _sr_lv) < atr * 0.8:
            _near_sr_level = _sr_lv
            break
    if _near_sr_level is not None:
        if entry > _near_sr_level and score > 0:  # サポート上のBUY
            score += 1.5
            reasons.append(f"✅ S/R({_near_sr_level:.3f})サポート反発: スイング高確率エントリー")
        elif entry < _near_sr_level and score < 0:  # レジスタンス下のSELL
            score -= 1.5
            reasons.append(f"🔻 S/R({_near_sr_level:.3f})レジスタンス反発: スイング高確率エントリー")

    # ⑨ ADX（スイングは低ADXでも有効: トレンド初期を捉えるため緩和）
    if adx > 20:
        score *= 1.1; reasons.append(f"✅ ADX{adx:.0f}: トレンド強度確認")
    elif adx > 12:
        reasons.append(f"⚠️ ADX{adx:.0f}: トレンド弱め（許容）")
    else:
        score *= 0.85; reasons.append(f"⚠️ ADX{adx:.0f}<12: 弱トレンド")

    # ⑩ ダウ理論
    dow_sc, dow_rsn = dow_theory_analysis(df)
    if abs(dow_sc) > 0:
        score += dow_sc * 0.4
        if dow_rsn: reasons.append(dow_rsn)

    # 上位足バイアス
    if backtest_mode and htf_cache and "htf" in htf_cache:
        htf = htf_cache["htf"]
    else:
        htf = get_htf_bias(symbol)

    if backtest_mode:
        fund_sc, fund_detail = 0.0, {}
    else:
        fund_sc, fund_detail = fundamental_score()
    score += fund_sc * 0.3  # ファンダメンタル補完

    # シグナル決定（高品質フィルター）
    # SR/Fib/ダイバージェンスのカタリストがある場合は閾値2.5、ない場合は4.0
    _has_catalyst = (_near_sr_level is not None) or fib_hit or any("ダイバージェンス" in r for r in reasons)
    THRESHOLD = 2.5 if _has_catalyst else 6.0  # カタリストなし → ほぼWAIT
    if   score >  THRESHOLD: signal, conf = "BUY",  int(min(92, 50 + score * 6))
    elif score < -THRESHOLD: signal, conf = "SELL", int(min(92, 50 + abs(score) * 6))
    else:                    signal, conf = "WAIT", int(max(20, 50 - abs(score) * 12))

    # Faber+TSMOM ハードブロック: 下降局面でのBUYを強制WAIT
    if _sw_buy_blocked and signal == "BUY":
        signal, conf = "WAIT", 30
        reasons.append("⛔ BUYブロック適用（Faber/TSMOMフィルタ）")

    # SL/TP (ATR*1.0/ATR*2.5: RR=1:2.5でブレイクイーブンWR=29%)
    SL_MULT, TP_MULT = 1.0, 2.5
    act_s = signal if signal != "WAIT" else ("BUY" if score >= 0 else "SELL")
    dir_s = 1.0 if act_s == "BUY" else -1.0
    sl    = round(entry - atr * SL_MULT * dir_s, 3)
    tp_r  = round(entry + atr * TP_MULT * dir_s, 3)
    if act_s == "BUY":
        tp_c = [l for l in sr_levels if entry + atr*0.5 < l < entry + atr*TP_MULT*1.8]
        tp   = round(min(tp_c) - 0.010, 3) if tp_c else tp_r
    else:
        tp_c = [l for l in sr_levels if entry - atr*TP_MULT*1.8 < l < entry - atr*0.5]
        tp   = round(max(tp_c) + 0.010, 3) if tp_c else tp_r
    sl_d = abs(entry - sl)
    if abs(tp - entry) < sl_d * 1.5:
        tp = round(entry + sl_d * 2.5 * dir_s, 3)
    rr = round(abs(tp - entry) / max(sl_d, 1e-6), 2)

    # ── エントリータイプ判定（SR近接を直接チェック）──
    _sw_entry_type = "unknown"
    if signal != "WAIT":
        _has_fib    = any("フィボ" in r or "Fib" in r for r in reasons)
        _has_div    = any("ダイバージェンス" in r for r in reasons)
        # SR近接チェック: 価格がSRレベルの1.0×ATR以内
        _near_sr = False
        for _sr_lv in sr_levels:
            if abs(entry - _sr_lv) < atr * 1.0:
                _near_sr = True
                break
        if _near_sr and _has_fib:
            _sw_entry_type = "sr_fib_confluence"
        elif _near_sr:
            _sw_entry_type = "sr_bounce"
        elif _has_fib:
            _sw_entry_type = "fib_pullback"
        elif _has_div:
            _sw_entry_type = "divergence"
        elif fib_hit:
            _sw_entry_type = "fib_pullback"
        else:
            _sw_entry_type = "ema_trend"

    if backtest_mode:
        session = {"name": "backtest", "quality": "N/A"}
    else:
        session = get_session_info()
    ts_str  = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)
    return {
        "timestamp": ts_str, "symbol": "USD/JPY", "tf": tf,
        "entry": round(entry, 3), "signal": signal, "confidence": conf,
        "sl": sl, "tp": tp, "rr_ratio": rr, "atr": round(atr, 3),
        "session": session, "htf_bias": htf, "swing_mode": True,
        "reasons": reasons, "mode": "swing",
        "entry_type": _sw_entry_type,
        "score": round(score, 3),
        "indicators": {
            "ema21": round(ema21,3), "ema50": round(ema50,3), "ema200": round(ema200,3),
            "adx": round(adx,1), "rsi": round(rsi,1),
            "macd": round(float(row["macd"]),5),
            "macd_sig": round(float(row["macd_sig"]),5),
            "macd_hist": round(macdh,5),
            "bb_upper": round(float(row["bb_upper"]),3),
            "bb_mid": round(float(row["bb_mid"]),3),
            "bb_lower": round(float(row["bb_lower"]),3),
            "bb_pband": round(float(row["bb_pband"]),3),
        },
        "swing_info": {
            "ema200": round(ema200,3), "ema200_slope": round(ema200_slope,5),
            "adx": round(adx,1), "fib": fib if fib else {},
            "fib_hit": fib_hit, "score": round(score,3),
        },
        "score_detail": {
            "combined": round(score,3), "rule": round(max(-1,min(1,score/8)),3),
        },
    }


def _get_dxy_trend_for_bt() -> str:
    """
    BTシミュレーション用の簡易Layer1バイアス判定。
    DXY（ドル指数）の日足EMA21を使ってUSDトレンドを判定。
    "bull" / "bear" / "neutral" を返す。
    キャッシュ付き（1時間）。
    """
    cache_key = "_dxy_trend_bt"
    now_ts = datetime.now().timestamp()
    cached = _data_cache.get(cache_key)
    if cached and (now_ts - cached[1]) < 3600:
        return cached[0]
    try:
        dxy_df = fetch_ohlcv("DX-Y.NYB", period="60d", interval="1d")
        dxy_df = add_indicators(dxy_df)
        if len(dxy_df) < 5:
            return "neutral"
        last = dxy_df.iloc[-1]
        close = float(last["Close"])
        ema21 = float(last["ema21"])
        ema50 = float(last["ema50"])
        if close > ema21 and ema21 > ema50:
            trend = "bull"
        elif close < ema21 and ema21 < ema50:
            trend = "bear"
        else:
            trend = "neutral"
        _data_cache[cache_key] = (trend, now_ts)
        return trend
    except Exception:
        return "neutral"


# ═══════════════════════════════════════════════════════
#  バックテスト（1H / 90日・勝率・期待値算出）
# ═══════════════════════════════════════════════════════
def run_backtest(symbol: str = "USDJPY=X",
                 lookback_days: int = 90) -> dict:
    """
    1H足バックテスト — SR構造ベース + EMAフィルター（他モードと統一設計）
    エントリータイプ:
      ① SR Bounce: 強いSR水平線での反発（両方向）
      ② Strong SR Breakout: 強SR突破（確定足）
      ③ EMA Cross: EMA9/21クロス（ADX≥15, EMA50方向一致）
    SL/TP: エントリータイプ別、SR-aware snap
    最大保有: 24本（24時間）、Close-based SL
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
            return {"error": "データ不足", "trades": 0, "mode": "standard"}

        SPREAD   = 0.008   # 0.8 pip（OANDA実スプレッド）
        SL_MULT  = 1.5     # default ATR mult
        TP_MULT  = 2.5     # default ATR mult
        MAX_HOLD = 24      # bars (24 hours)
        COOLDOWN = 1

        trades = []
        last_bar = -99

        # SR/OBプリコンピュテーション（1H足: 24本/日）
        STD_SR_RECALC = 50
        _std_sr_cache = {}
        _std_ob_cache = {}
        for _ci in range(100, len(df), STD_SR_RECALC):
            _sr_slice = df.iloc[max(0, _ci - 300):_ci]
            _std_sr_cache[_ci // STD_SR_RECALC] = find_sr_levels_weighted(
                _sr_slice, window=5, tolerance_pct=0.003, min_touches=2,
                max_levels=8, bars_per_day=24)
            try:
                _, _obs = detect_order_blocks(
                    df.iloc[max(0, _ci - 100):_ci], atr_mult=1.5, lookback=80)
                _std_ob_cache[_ci // STD_SR_RECALC] = _obs
            except Exception:
                _std_ob_cache[_ci // STD_SR_RECALC] = []

        for i in range(50, len(df) - MAX_HOLD - 1):
            if i - last_bar < COOLDOWN:
                continue

            row      = df.iloc[i]
            prev_row = df.iloc[i-1]

            ema9    = float(row["ema9"])
            ema21   = float(row["ema21"])
            ema50   = float(row["ema50"])
            ema9_p  = float(prev_row["ema9"])
            ema21_p = float(prev_row["ema21"])
            atr     = float(row["atr"])
            adx     = float(row.get("adx", 20.0))
            rsi     = float(row["rsi"])
            close_p = float(row["Close"])
            open_p  = float(row["Open"])
            high_p  = float(row["High"])
            low_p   = float(row["Low"])

            if atr <= 0:
                continue

            # セッションフィルター: London+NY (07-20 UTC)
            try:
                h = row.name.hour
                if not (7 <= h < 20):
                    continue
            except Exception:
                pass

            # ATR regime filter
            _std_atr_avg = float(df["atr"].iloc[max(0,i-20):i].mean()) if i >= 20 else atr
            if _std_atr_avg > 0 and atr / _std_atr_avg > 1.8:
                continue

            # SR/OB取得
            _std_key = i // STD_SR_RECALC
            std_sr_weighted = _std_sr_cache.get(_std_key, [])
            std_sr = [sr["price"] for sr in std_sr_weighted]
            std_obs = _std_ob_cache.get(_std_key, [])

            sig = None
            entry_type = "ema_cross"

            # ═══ Entry Type 1: SR Bounce (両方向, 1H足強化フィルター) ═══
            # strength≥0.6, touches≥4, EMA方向一致で高品質バウンスのみ
            if sig is None and std_sr_weighted:
                tol_sr = atr * 0.35
                for sr_obj in std_sr_weighted:
                    if sr_obj["strength"] < 0.6 or sr_obj["touches"] < 4:
                        continue
                    level = sr_obj["price"]
                    # BUY: support bounce + EMA21上向き
                    if (abs(low_p - level) < tol_sr
                            and close_p > open_p and close_p > level
                            and rsi > 30 and rsi < 48
                            and adx < 28 and ema9 > ema21):
                        sig = "BUY"
                        entry_type = "sr_bounce"
                        break
                    # SELL: resistance bounce + EMA21下向き
                    if (abs(high_p - level) < tol_sr
                            and close_p < open_p and close_p < level
                            and rsi > 52 and rsi < 70
                            and adx < 28 and ema9 < ema21):
                        sig = "SELL"
                        entry_type = "sr_bounce"
                        break

            # ═══ Entry Type 2: Strong SR Breakout ═══
            if sig is None and std_sr_weighted:
                for sr_obj in std_sr_weighted:
                    if not sr_obj["is_strong"] or sr_obj["touches"] < 3:
                        continue
                    level = sr_obj["price"]
                    if (sr_obj["type"] in ("resistance", "both")
                            and close_p > level + atr * 0.1
                            and open_p < level
                            and close_p > open_p
                            and adx >= 12 and rsi > 50 and rsi < 75):
                        sig = "BUY"
                        entry_type = "strong_sr_breakout"
                        break
                    if (sr_obj["type"] in ("support", "both")
                            and close_p < level - atr * 0.1
                            and open_p > level
                            and close_p < open_p
                            and adx >= 12 and rsi > 25 and rsi < 50):
                        sig = "SELL"
                        entry_type = "strong_sr_breakout"
                        break

            # ═══ Entry Type 3: EMA9/21 Cross (緩和版) ═══
            if sig is None:
                cross_up   = (ema9_p <= ema21_p) and (ema9 > ema21)
                cross_down = (ema9_p >= ema21_p) and (ema9 < ema21)
                if cross_up and adx >= 15 and ema9 > ema50 and rsi < 70:
                    sig = "BUY"
                    entry_type = "ema_cross"
                elif cross_down and adx >= 15 and ema9 < ema50 and rsi > 30:
                    sig = "SELL"
                    entry_type = "ema_cross"

            if sig is None:
                continue

            # エントリーは次の足のOpen
            if i + 1 >= len(df):
                continue
            ep = float(df.iloc[i + 1]["Open"])
            ep = ep + SPREAD / 2 if sig == "BUY" else ep - SPREAD / 2

            # エントリータイプ別 SL/TP
            if entry_type == "sr_bounce":
                sl_m, tp_m = 0.8, 2.0
            elif entry_type == "strong_sr_breakout":
                sl_m, tp_m = 0.8, 2.5
            elif entry_type == "ema_cross":
                sl_m, tp_m = 1.5, 2.5
            else:
                sl_m, tp_m = SL_MULT, TP_MULT

            sl = ep - atr * sl_m if sig == "BUY" else ep + atr * sl_m
            tp = ep + atr * tp_m if sig == "BUY" else ep - atr * tp_m

            # SR-aware SL snap
            if std_sr and entry_type != "ema_cross":
                for level in sorted(std_sr, reverse=(sig == "BUY")):
                    if sig == "BUY" and level < ep and level > sl:
                        sl = level - atr * 0.15
                        break
                    if sig == "SELL" and level > ep and level < sl:
                        sl = level + atr * 0.15
                        break

            # SR-aware TP snap
            if std_sr_weighted:
                for sr_obj in sorted(std_sr_weighted,
                                     key=lambda x: x["price"],
                                     reverse=(sig == "SELL")):
                    if sr_obj["strength"] < 0.3:
                        continue
                    level = sr_obj["price"]
                    if sig == "BUY" and level > ep + atr * 0.3 and level < tp:
                        tp = level - atr * 0.05
                        break
                    if sig == "SELL" and level < ep - atr * 0.3 and level > tp:
                        tp = level + atr * 0.05
                        break

            tp = round(tp, 3)
            tp_m_actual = round(abs(tp - ep) / max(atr, 1e-6), 3)

            # Close-based SL + breakeven trailing
            outcome = None; bars_held = 0
            _be_activated = False
            _current_sl = sl
            for j in range(1, MAX_HOLD + 1):
                if i + 1 + j >= len(df): break
                fut = df.iloc[i + 1 + j]
                hi, lo = float(fut["High"]), float(fut["Low"])
                fut_close = float(fut["Close"])

                # Partial TP trailing
                _tp_dist = abs(tp - ep)
                if sig == "BUY" and hi - ep >= _tp_dist * 0.6:
                    _be_activated = True
                    _current_sl = max(_current_sl, ep)
                elif sig == "SELL" and ep - lo >= _tp_dist * 0.6:
                    _be_activated = True
                    _current_sl = min(_current_sl, ep)

                _genuine = atr * 0.3
                if sig == "BUY":
                    hit_tp = hi >= tp
                    hit_sl = (fut_close <= _current_sl) or (_current_sl - lo > _genuine)
                    if hit_tp and hit_sl:
                        outcome = "WIN" if fut_close >= ep else "LOSS"
                        bars_held = j; break
                    elif hit_tp:
                        outcome = "WIN"; bars_held = j; break
                    elif hit_sl:
                        if _be_activated and _current_sl >= ep:
                            outcome = "WIN"; bars_held = j
                            tp_m_actual = round(_tp_dist * 0.6 / max(atr, 1e-6), 3)
                        else:
                            outcome = "LOSS"; bars_held = j
                        break
                else:
                    hit_tp = lo <= tp
                    hit_sl = (fut_close >= _current_sl) or (hi - _current_sl > _genuine)
                    if hit_tp and hit_sl:
                        outcome = "WIN" if fut_close <= ep else "LOSS"
                        bars_held = j; break
                    elif hit_tp:
                        outcome = "WIN"; bars_held = j; break
                    elif hit_sl:
                        if _be_activated and _current_sl <= ep:
                            outcome = "WIN"; bars_held = j
                            tp_m_actual = round(_tp_dist * 0.6 / max(atr, 1e-6), 3)
                        else:
                            outcome = "LOSS"; bars_held = j
                        break

            if outcome:
                last_bar = i
                trade_dict = {"outcome": outcome, "bars_held": bars_held,
                                "sig": sig, "ep": round(ep, 3),
                                "sl": round(sl, 3), "tp": round(tp, 3),
                                "bar_idx": i, "entry_type": entry_type,
                                "sl_m": sl_m, "tp_m": tp_m_actual}
                # Close-based SL actual loss: when LOSS and close exceeded SL level
                if outcome == "LOSS":
                    if sig == "BUY" and fut_close < sl:
                        trade_dict["actual_sl_m"] = round(min(abs(fut_close - ep) / max(atr, 1e-6), sl_m * 1.2), 3)
                    elif sig == "SELL" and fut_close > sl:
                        trade_dict["actual_sl_m"] = round(min(abs(fut_close - ep) / max(atr, 1e-6), sl_m * 1.2), 3)
                trades.append(trade_dict)

        def _pnl(t):
            if t["outcome"] == "WIN":
                return t.get("tp_m", TP_MULT)
            else:
                return -t.get("actual_sl_m", t.get("sl_m", SL_MULT))

        if len(trades) < 10:
            result = {"error": "サンプル数不足 (最低10トレード必要)",
                      "trades": len(trades), "mode": "standard"}
        else:
            wins  = sum(1 for t in trades if t["outcome"] == "WIN")
            total = len(trades)
            wr    = round(wins / total * 100, 1)
            avg_h = round(sum(t["bars_held"] for t in trades) / total, 1)
            ev    = round(sum(_pnl(t) for t in trades) / total, 3)
            # MaxDD
            eq, peak, mdd = 0.0, 0.0, 0.0
            for t in trades:
                eq += _pnl(t)
                if eq > peak: peak = eq
                if peak - eq > mdd: mdd = peak - eq
            mdd = round(mdd, 3)
            # Sharpe
            rets = [_pnl(t) for t in trades]
            sharpe = round(np.mean(rets) / max(np.std(rets), 1e-6) * np.sqrt(252), 3) if len(rets) > 1 else 0.0

            # Walk-forward 3窓
            wf_windows = []
            window_size = total // 3
            for wi in range(3):
                wt = trades[wi*window_size:(wi+1)*window_size]
                if len(wt) < 5: continue
                ww = sum(1 for t in wt if t["outcome"] == "WIN")
                wwr = round(ww / len(wt) * 100, 1)
                wev = round(sum(_pnl(t) for t in wt) / len(wt), 3)
                wf_windows.append({"label": f"窓{wi+1}", "window": wi+1,
                                   "trades": len(wt), "win_rate": wwr,
                                   "expected_value": wev})
            profitable = sum(1 for w in wf_windows if w.get("expected_value", -1) > 0)
            consistency = f"{profitable}/{len(wf_windows)} 窓でプラス期待値"

            # エントリータイプ別統計
            entry_stats = {}
            for t in trades:
                et = t.get("entry_type", "ema_cross")
                if et not in entry_stats:
                    entry_stats[et] = {"wins": 0, "total": 0, "pnl": 0.0}
                entry_stats[et]["total"] += 1
                entry_stats[et]["pnl"] += _pnl(t)
                if t["outcome"] == "WIN":
                    entry_stats[et]["wins"] += 1
            for k, v in entry_stats.items():
                v["win_rate"] = round(v["wins"] / v["total"] * 100, 1)
                v["ev"] = round(v["pnl"] / v["total"], 3)

            verdict = ("✅ 良好" if ev > 0.10 and profitable >= 2 else
                       "🟡 要注意" if ev > 0 else "❌ 不採用")

            result = {
                "win_rate":        wr,
                "trades":          total,
                "wins":            wins,
                "losses":          total - wins,
                "avg_hold_hours":  avg_h,
                "expected_value":  ev,
                "max_drawdown":    mdd,
                "sharpe":          sharpe,
                "verdict":         verdict,
                "period":          f"過去{lookback_days}日 (1H足)",
                "sl_mult":         SL_MULT,
                "tp_mult":         TP_MULT,
                "walk_forward":    wf_windows,
                "consistency":     consistency,
                "entry_breakdown": entry_stats,
                "mode":            "standard",
            }

        _bt_cache["result"] = result
        _bt_cache["ts"]     = now
        return result
    except Exception as e:
        import traceback
        print(f"[BACKTEST] {traceback.format_exc()}")
        return {"error": str(e), "mode": "standard"}


# ═══════════════════════════════════════════════════════
#  トレンド転換検出 → バックテストキャッシュ自動クリア
# ═══════════════════════════════════════════════════════
_trend_state: dict = {}  # mode -> last known agreement ("bull"/"bear"/"mixed")
_trend_changed_at: dict = {}  # mode -> datetime of last trend change


def _check_trend_changed_and_clear_bt(mode: str, symbol: str = "USDJPY=X") -> dict:
    """
    上位足トレンド状態を確認し、転換していればBTキャッシュをクリアする。
    スキャルプ   : 1H+4H アライメント監視
    デイトレード : 4H+1D アライメント監視

    Returns: {changed: bool, prev: str, current: str, label: str}
    """
    global _trend_state, _trend_changed_at, _scalp_bt_cache, _dt_bt_cache
    try:
        if mode == "scalp":
            bias = get_htf_bias(symbol)          # 1H+4H
        elif mode == "daytrade":
            bias = get_htf_bias_daytrade(symbol)  # 4H+1D
        else:
            return {"changed": False, "prev": "n/a", "current": "n/a", "label": ""}

        current   = bias.get("agreement", "mixed")
        prev      = _trend_state.get(mode)
        _trend_state[mode] = current
        changed   = (prev is not None and prev != current)

        if changed:
            _trend_changed_at[mode] = datetime.now()
            if mode == "scalp":
                _scalp_bt_cache.clear()
                print(f"[TREND] Scalp {prev}→{current}: BT cache cleared")
            elif mode == "daytrade":
                _dt_bt_cache.clear()
                print(f"[TREND] Daytrade {prev}→{current}: BT cache cleared")

        return {
            "changed":  changed,
            "prev":     prev or "初回",
            "current":  current,
            "label":    bias.get("label", ""),
            "score":    bias.get("score", 0.0),
            "changed_at": _trend_changed_at.get(mode, "").strftime("%Y-%m-%d %H:%M UTC")
                          if _trend_changed_at.get(mode) else None,
        }
    except Exception as e:
        print(f"[_check_trend] {e}")
        return {"changed": False, "prev": "error", "current": "error", "label": str(e)}


# ═══════════════════════════════════════════════════════
#  スキャルピング専用バックテスト（5m/15m足）
# ═══════════════════════════════════════════════════════
_scalp_bt_cache: dict = {}

# ML Model state
_ml_model: "RandomForestClassifier | None" = None
_ml_scaler: "StandardScaler | None" = None
_ml_model_file = "ml_signal_model.pkl"
_ml_scaler_file = "ml_signal_scaler.pkl"
_ml_trained_at: "datetime | None" = None
_ML_RETRAIN_HOURS = 24  # retrain every 24 hours
_ML_MIN_SAMPLES = 100   # minimum samples to train

def run_scalp_backtest(symbol: str = "USDJPY=X",
                       lookback_days: int = 7,
                       interval: str = "1m") -> dict:
    """
    スキャルピングBT — compute_scalp_signal統合版
    本番環境と同一のエントリーロジック（compute_scalp_signal）を使用。
    BT固有: SL/TP simulation, trade tracking, entry cooldown
    """
    global _scalp_bt_cache
    cache_key = f"{interval}_{lookback_days}"
    now = datetime.now()
    cached = _scalp_bt_cache.get(cache_key)
    if cached and (now - cached["ts"]).total_seconds() < SCALP_BT_TTL:
        return cached["result"]

    try:
        # 1m足は yfinance で最大7日間
        fetch_period = f"{min(lookback_days, 7)}d" if interval == "1m" else f"{lookback_days}d"
        df = fetch_ohlcv(symbol, period=fetch_period, interval=interval)
        df = add_indicators(df)
        df = df.dropna()
        if len(df) < 100:
            return {"error": "データ不足（最低100本必要）", "trades": 0, "mode": "scalp"}

        SPREAD       = 0.008   # 0.8 pip (OANDA実スプレッド)
        profile      = STRATEGY_PROFILES.get(STRATEGY_MODE, STRATEGY_PROFILES["A"])
        SL_MULT      = profile["scalp_sl"]   # scalp-specific SL
        TP_MULT      = profile["scalp_tp"]   # scalp-specific TP
        MAX_HOLD     = 40     # 40 bars = 40 min (ATR TP到達率向上)
        COOLDOWN     = 1      # 1 bar (頻度最大化、スプレッド0.2pip活用)
        if interval == "1m":   bars_per_min = 1
        elif interval == "5m": bars_per_min = 5
        else:                  bars_per_min = 15

        trades = []
        last_trade_bar = -99

        # ── HTF bias: BT mode = neutral (ルックアヘッドバイアス排除) ──
        # get_htf_bias() は現在のyfinanceデータを使うためBTでは無効化
        try:
            _layer1 = get_master_bias(symbol)
        except Exception:
            _layer1 = {"direction": "neutral", "label": "—", "score": 0}
        _htf_cache = {
            "htf": {"score": 0, "agreement": "neutral", "label": "BT: HTFバイアス無効"},
            "layer1": _layer1,
        }

        # ── SR/OBプリコンピュテーション (ルックアヘッドバイアス排除) ──
        SR_RECALC = 100
        _sr_cache = {}
        _scalp_bpd = 288 if bars_per_min == 5 else 96
        for _ci in range(200, len(df), SR_RECALC):
            _sr_slice = df.iloc[max(0, _ci - 300):_ci]
            _sr_cache[_ci // SR_RECALC] = find_sr_levels_weighted(
                _sr_slice, window=5, tolerance_pct=0.003, min_touches=2,
                max_levels=8, bars_per_day=_scalp_bpd)

        MIN_BARS = 200  # compute_scalp_signalに必要な最小バー数

        for i in range(max(MIN_BARS, 50), len(df) - MAX_HOLD - 1):
            if i - last_trade_bar < COOLDOWN:
                continue

            row = df.iloc[i]

            # Volume filter: skip dead-market bars
            if "Volume" in df.columns:
                vol = float(row["Volume"])
                if vol > 0 and vol < 100:
                    continue

            # Bar range filter
            bar_range = float(row["High"]) - float(row["Low"])
            if bar_range < 0.008:
                continue

            # ── 本番環境と統一: compute_scalp_signalを呼び出し ──
            _sr_key = i // SR_RECALC
            current_sr_weighted = _sr_cache.get(_sr_key, [])
            current_sr = [sr["price"] for sr in current_sr_weighted]

            bar_df = df.iloc[max(0, i - 500):i + 1]
            bar_time = df.index[i]
            if hasattr(bar_time, 'tzinfo') and bar_time.tzinfo is None:
                bar_time = bar_time.replace(tzinfo=timezone.utc)

            try:
                sig_result = compute_scalp_signal(
                    bar_df, tf=interval, sr_levels=current_sr,
                    symbol=symbol, backtest_mode=True,
                    bar_time=bar_time, htf_cache=_htf_cache,
                )
            except Exception:
                continue

            sig = sig_result.get("signal", "WAIT")
            if sig == "WAIT":
                continue

            entry_type = sig_result.get("entry_type", "unknown")

            # ── エントリー理由の品質ゲート（本番と統一）──
            QUALIFIED_TYPES = {
                # v2 戦略タイプ（本番 demo_trader.py と統一）
                "bb_rsi_reversion", "bb_squeeze_breakout",
                "rsi_divergence_sr", "london_breakout",
                "stoch_trend_pullback", "macdh_reversal",
                # "engulfing_bb",    # DISABLED: EV=+0.042 @0.8pip spread → 薄利すぎ
                "three_bar_reversal",
                "trend_rebound",  # 強トレンド時リバウンド
                "v_reversal",     # V字リバウンドキャプチャ
                # "hs_neckbreak",  # DISABLED: EV=-0.346 @0.8pip spread → マイナス
                "ihs_neckbreak",  # 逆三尊ネックライン突破
                "sr_touch_bounce", # 水平線タッチ反発
                # v3 リバーサル戦略
                # "sr_channel_reversal",  # DISABLED: EV=-0.004 @0.8pip spread → マイナス
                "fib_reversal",             # フィボナッチリトレースメント反発
                "mtf_reversal_confluence",  # MTF RSI+MACDクロス一致
                # v1 互換
                "tokyo_bb", "sr_bounce", "ob_retest", "bb_bounce",
                "donchian", "reg_channel", "ema_pullback",
            }
            BLOCKED_TYPES = {"unknown", "momentum", "wait"}

            if entry_type in BLOCKED_TYPES:
                continue
            _reasons = sig_result.get("reasons", [])
            _confirmed = sum(1 for r in _reasons if "✅" in r)
            if entry_type in QUALIFIED_TYPES:
                if _confirmed < 1:
                    continue
            elif entry_type == "ema_cross":
                _sig_adx = sig_result.get("indicators", {}).get("adx", 0)
                if not _sig_adx or _sig_adx < 20 or _confirmed < 2:
                    continue
            else:
                continue  # 未知タイプ

            ep = sig_result.get("entry", float(row["Close"]))
            tp = sig_result.get("tp", ep)  # TP = 技術的ターゲット（固定）
            atr7 = sig_result.get("atr", float(row.get("atr7", row.get("atr", 0.07))))

            # BT用: 次バーのOpenでエントリー（スリッページ反映）
            if i + 1 >= len(df):
                continue
            ep = float(df.iloc[i + 1]["Open"])
            ep = ep + SPREAD / 2 if sig == "BUY" else ep - SPREAD / 2

            # TP固定: シグナルのTPターゲットを維持（エントリー価格シフト分のみ調整）
            sig_entry = sig_result.get("entry", ep)
            ep_shift = ep - sig_entry
            tp = tp + ep_shift

            # SL可変: エントリー価格からRR比で逆算
            tp_dist = abs(tp - ep)
            MIN_RR_BT = 1.2
            sl_dist = tp_dist / MIN_RR_BT
            MIN_SL_DIST_BT = 0.030  # 3 pip最低保証
            sl_dist = max(sl_dist, MIN_SL_DIST_BT)
            sl = ep - sl_dist if sig == "BUY" else ep + sl_dist

            # RR不足チェック
            if tp_dist < sl_dist:
                continue

            sl_m = abs(ep - sl) / max(atr7, 1e-6)
            tp_m_actual = abs(tp - ep) / max(atr7, 1e-6)

            sl_dist = abs(ep - sl)
            actual_rr = round(abs(tp - ep) / max(sl_dist, 1e-6), 2)

            # ── SL anti-fake-out: Close-based confirmation ──
            _sl_genuine_threshold = atr7 * 0.3

            outcome = None; bars_held = 0
            _be_activated = False
            _current_sl = sl
            for j in range(1, MAX_HOLD + 1):
                if i + 1 + j >= len(df): break
                fut = df.iloc[i + 1 + j]
                hi, lo = float(fut["High"]), float(fut["Low"])
                fut_close = float(fut["Close"])

                # Partial TP / Trailing: 60% TP到達でbreakeven
                tp_dist_total = abs(tp - ep)
                if sig == "BUY":
                    _progress = hi - ep
                    if _progress >= tp_dist_total * 0.6:
                        _be_activated = True
                        _current_sl = max(_current_sl, ep)
                else:
                    _progress = ep - lo
                    if _progress >= tp_dist_total * 0.6:
                        _be_activated = True
                        _current_sl = min(_current_sl, ep)

                # Time-decay SL tightening
                if j >= int(MAX_HOLD * 0.6):
                    if sig == "BUY" and fut_close > ep:
                        _current_sl = max(_current_sl, ep)
                    elif sig == "SELL" and fut_close < ep:
                        _current_sl = min(_current_sl, ep)

                if sig == "BUY":
                    hit_tp = hi >= tp
                    _wick_depth = _current_sl - lo
                    hit_sl = (fut_close <= _current_sl) or (_wick_depth > _sl_genuine_threshold)
                    if hit_tp and hit_sl:
                        outcome = "WIN" if fut_close >= ep else "LOSS"; bars_held = j; break
                    elif hit_tp:
                        outcome = "WIN"; bars_held = j; break
                    elif hit_sl:
                        if _be_activated and _current_sl >= ep:
                            outcome = "WIN"; bars_held = j
                            tp_m_actual = round(tp_dist_total * 0.6 / max(atr7, 1e-6), 3)
                            break
                        else:
                            outcome = "LOSS"; bars_held = j; break
                else:
                    hit_tp = lo <= tp
                    _wick_depth = hi - _current_sl
                    hit_sl = (fut_close >= _current_sl) or (_wick_depth > _sl_genuine_threshold)
                    if hit_tp and hit_sl:
                        outcome = "WIN" if fut_close <= ep else "LOSS"; bars_held = j; break
                    elif hit_tp:
                        outcome = "WIN"; bars_held = j; break
                    elif hit_sl:
                        if _be_activated and _current_sl <= ep:
                            outcome = "WIN"; bars_held = j
                            tp_m_actual = round(tp_dist_total * 0.6 / max(atr7, 1e-6), 3)
                            break
                        else:
                            outcome = "LOSS"; bars_held = j; break

            if outcome:
                last_trade_bar = i
                trade_dict = {"outcome": outcome, "bars_held": bars_held,
                              "sig": sig, "ep": round(ep, 3),
                              "actual_rr": actual_rr, "bar_idx": i,
                              "entry_type": entry_type,
                              "sl": round(sl, 3), "tp": round(tp, 3),
                              "sl_m": round(sl_m, 3), "tp_m": round(tp_m_actual, 3),
                              "entry_time": str(bar_time)}
                if outcome == "LOSS":
                    if sig == "BUY" and fut_close < sl:
                        trade_dict["actual_sl_m"] = round(min(abs(fut_close - ep) / max(atr7, 1e-6), sl_m * 1.2), 3)
                    elif sig == "SELL" and fut_close > sl:
                        trade_dict["actual_sl_m"] = round(min(abs(fut_close - ep) / max(atr7, 1e-6), sl_m * 1.2), 3)
                trades.append(trade_dict)

        def _pnl(t):
            if t["outcome"] == "WIN":
                return t.get("tp_m", TP_MULT)
            else:
                return -t.get("actual_sl_m", t.get("sl_m", SL_MULT))

        def _max_dd_scalp(trade_list):
            eq, peak, dd = 0.0, 0.0, 0.0
            for t in trade_list:
                eq += _pnl(t)
                if eq > peak: peak = eq
                if peak - eq > dd: dd = peak - eq
            return round(dd, 3)

        if len(trades) < 10:
            result = {
                "error":  f"サンプル数不足（{len(trades)}トレード）",
                "trades": len(trades),
                "mode":   "scalp",
                "debug": {
                    "bars_total": len(df),
                    "date_range": f"{df.index[0]} → {df.index[-1]}" if len(df) > 0 else "empty",
                    "adx_sample": float(df.get("adx", pd.Series([0])).iloc[-1]) if len(df) > 0 else None,
                    "interval": interval,
                    "lookback_days": lookback_days,
                    "data_source": _last_data_source.get(interval, "unknown"),
                    "massive_key_set": bool(os.environ.get("MASSIVE_API_KEY")),
                    "td_key_set": bool(os.environ.get("TWELVEDATA_API_KEY")),
                },
            }
        else:
            wins  = sum(1 for t in trades if t["outcome"] == "WIN")
            total = len(trades)
            wr    = round(wins / total * 100, 1)
            rr    = round(TP_MULT / SL_MULT, 2)
            # 混合エントリータイプ対応: 実際のPnLベースでEV算出
            ev    = round(sum(_pnl(t) for t in trades) / total, 3)
            avg_h = round(sum(t["bars_held"] for t in trades) / total, 1)
            mdd   = _max_dd_scalp(trades)
            pnls  = [_pnl(t) for t in trades]
            sharpe = round(float(np.mean(pnls)) / max(float(np.std(pnls)), 1e-6), 3)
            per_day = round(total / lookback_days, 1)

            if   ev > 0.3: verdict = "✅ 期待値プラス（スキャル推奨）"
            elif ev > 0:   verdict = "🟡 期待値わずかプラス（要注意）"
            else:          verdict = "❌ 期待値マイナス（スキャル不推奨）"

            # Walk-forward: 3窓（実PnLベース）
            wlen = max(1, len(trades) // 3)
            wf_windows = []
            for w in range(3):
                wt = trades[w * wlen:(w + 1) * wlen]
                if len(wt) < 5: continue
                ww  = sum(1 for t in wt if t["outcome"] == "WIN")
                wwr = round(ww / len(wt) * 100, 1)
                wev = round(sum(_pnl(t) for t in wt) / len(wt), 3)
                wf_windows.append({"label": f"窓{w + 1}", "trades": len(wt),
                                   "win_rate": wwr, "expected_value": wev})

            profitable = sum(1 for w in wf_windows if w.get("expected_value", -1) > 0)

            # エントリータイプ別統計
            entry_stats = {}
            for t in trades:
                et = t.get("entry_type", "ema_cross")
                if et not in entry_stats:
                    entry_stats[et] = {"wins": 0, "total": 0, "pnl": 0.0}
                entry_stats[et]["total"] += 1
                entry_stats[et]["pnl"] += _pnl(t)
                if t["outcome"] == "WIN":
                    entry_stats[et]["wins"] += 1
            for k, v in entry_stats.items():
                v["win_rate"] = round(v["wins"] / v["total"] * 100, 1)
                v["ev"] = round(v["pnl"] / v["total"], 3)

            trade_log  = [{"sig": t["sig"], "outcome": t["outcome"],
                           "bars": t["bars_held"],
                           "type": t.get("entry_type", "ema_cross"),
                           "entry_time": t.get("entry_time", ""),
                           "sl_m": t.get("sl_m", 0), "tp_m": t.get("tp_m", 0),
                           "actual_sl_m": t.get("actual_sl_m", None)} for t in trades]
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
                "entry_breakdown": entry_stats,
                "trade_log":      trade_log,
                "mode":           "scalp",
                "data_source":    _last_data_source.get(interval, "yfinance"),
                "bars_fetched":   len(df),
            }

        _scalp_bt_cache[cache_key] = {"result": result, "ts": now}
        return result
    except Exception as e:
        import traceback
        print(f"[SCALP_BT] {traceback.format_exc()}")
        return {"error": str(e), "mode": "scalp"}


# ═══════════════════════════════════════════════════════
#  デイトレードバックテスト（30m / 90日）
#  学術根拠: EMA200 + ADX25フィルター + フィボ38.2-61.8%エントリー
# ═══════════════════════════════════════════════════════
_dt_bt_cache: dict = {}

def run_daytrade_backtest(symbol: str = "USDJPY=X",
                          lookback_days: int = 55,
                          interval: str = "15m") -> dict:
    """
    デイトレードBT — compute_daytrade_signal統合版
    本番環境と同一のエントリーロジック（compute_daytrade_signal）を使用。
    BT固有: SL/TP simulation, trade tracking, entry cooldown
    """
    global _dt_bt_cache
    cache_key = f"{interval}_{lookback_days}"
    now = datetime.now()
    cached = _dt_bt_cache.get(cache_key)
    if cached and (now - cached["ts"]).total_seconds() < DT_BT_TTL:
        return cached["result"]

    try:
        df = fetch_ohlcv(symbol, period=f"{lookback_days}d", interval=interval)
        df = add_indicators(df)
        df = df.dropna()
        if len(df) < 100:
            return {"error": "データ不足", "trades": 0, "mode": "daytrade"}

        SPREAD    = 0.008   # 0.8 pip（OANDA実スプレッド）
        profile   = STRATEGY_PROFILES.get(STRATEGY_MODE, STRATEGY_PROFILES["A"])
        SL_MULT   = profile["daytrade_sl"]   # daytrade-specific SL
        TP_MULT   = profile["daytrade_tp"]   # daytrade-specific TP

        # ── timeframe別パラメータ自動調整 ──
        if interval == "1h":
            MAX_HOLD  = 12     # bars (12 hours at 1h)
            COOLDOWN  = 1
            bars_per_h = 1
            _atr_tp_floor_mult = 2.0  # 1h: ATR×2.0 フロア（大きなTP）
        elif interval == "30m":
            MAX_HOLD  = 16
            COOLDOWN  = 1
            bars_per_h = 2
            _atr_tp_floor_mult = 1.8
        else:  # 15m default
            MAX_HOLD  = 24     # bars (6 hours at 15m)
            COOLDOWN  = 1
            bars_per_h = 4
            _atr_tp_floor_mult = 1.5

        trades = []
        last_bar = -99

        # ── HTF bias: BT mode = neutral (ルックアヘッドバイアス排除) ──
        # get_htf_bias_daytrade() は現在のyfinanceデータを使うためBTでは無効化
        try:
            _layer1 = get_master_bias(symbol)
        except Exception:
            _layer1 = {"direction": "neutral", "label": "—", "score": 0}
        _htf_cache = {
            "htf": {"score": 0, "agreement": "neutral", "label": "BT: HTFバイアス無効"},
            "layer1": _layer1,
        }

        # ── SR/OBプリコンピュテーション (ルックアヘッドバイアス排除) ──
        DT_SR_RECALC = 80
        _dt_sr_cache = {}
        for _ci in range(200, len(df), DT_SR_RECALC):
            _sr_slice = df.iloc[max(0, _ci - 400):_ci]
            _dt_sr_cache[_ci // DT_SR_RECALC] = find_sr_levels_weighted(
                _sr_slice, window=5, tolerance_pct=0.003, min_touches=2,
                max_levels=8, bars_per_day=96)

        MIN_BARS = 100 if interval == "1h" else 200  # 1h足は100バー(4日)で十分

        for i in range(max(MIN_BARS, 50), len(df) - MAX_HOLD - 1):
            if i - last_bar < COOLDOWN:
                continue

            row = df.iloc[i]

            # Volume filter: skip dead-market bars
            if "Volume" in df.columns:
                vol = float(row["Volume"])
                if vol > 0 and vol < 100:
                    continue

            # Bar range filter (timeframe別)
            bar_range = float(row["High"]) - float(row["Low"])
            _min_bar_range = 0.030 if interval == "1h" else 0.010
            if bar_range < _min_bar_range:
                continue

            # ── 本番環境と統一: compute_daytrade_signalを呼び出し ──
            _dt_key = i // DT_SR_RECALC
            current_sr_weighted = _dt_sr_cache.get(_dt_key, [])
            current_sr = [sr["price"] for sr in current_sr_weighted]

            bar_df = df.iloc[max(0, i - 500):i + 1]
            bar_time = df.index[i]
            if hasattr(bar_time, 'tzinfo') and bar_time.tzinfo is None:
                bar_time = bar_time.replace(tzinfo=timezone.utc)

            try:
                sig_result = compute_daytrade_signal(
                    bar_df, tf=interval, sr_levels=current_sr,
                    symbol=symbol, backtest_mode=True,
                    bar_time=bar_time, htf_cache=_htf_cache,
                )
            except Exception:
                continue

            sig = sig_result.get("signal", "WAIT")
            if sig == "WAIT":
                continue

            entry_type = sig_result.get("entry_type", "unknown")

            # ── エントリー理由の品質ゲート（本番と統一）──
            DT_QUALIFIED = {
                # 本番 demo_trader.py と統一
                "dual_sr_bounce", "dual_sr_breakout",
                "sr_fib_confluence",
                # "ob_retest",       # 本番ではDT用に未使用
                # "hs_neckbreak",    # DISABLED: EV=-0.346
                "ihs_neckbreak",
                "dt_fib_reversal",           # フィボリトレースメント反発
                "dt_sr_channel_reversal",    # SR/チャネルバウンス
                "ema200_trend_reversal",     # EMA200トレンド転換
            }
            DT_CONDITIONAL = {"ema_cross"}
            DT_BLOCKED = {"unknown", "wait"}

            if entry_type in DT_BLOCKED:
                continue
            _dt_reasons = sig_result.get("reasons", [])
            _dt_confirmed = sum(1 for r in _dt_reasons if "✅" in r)
            if entry_type in DT_CONDITIONAL:
                _dt_adx = sig_result.get("indicators", {}).get("adx", 0)
                if not _dt_adx or _dt_adx < 12 or _dt_confirmed < 1:  # 旧15→12（トレード頻度増）
                    continue
            elif entry_type in DT_QUALIFIED:
                if _dt_confirmed < 1:
                    continue
            else:
                continue  # 未知タイプ

            atr = sig_result.get("atr", float(row.get("atr", 0.07)))

            # BT用: 次バーのOpenでエントリー（スリッページ反映）
            if i + 1 >= len(df):
                continue
            ep = float(df.iloc[i + 1]["Open"])
            ep = ep + SPREAD / 2 if sig == "BUY" else ep - SPREAD / 2

            # TP固定: シグナルのTPターゲットを維持（エントリー価格シフト分のみ調整）
            # ATR×1.5をフロアとして保証（シグナルTPが小さすぎる場合に補正）
            sig_entry = sig_result.get("entry", ep)
            tp = sig_result.get("tp", ep)
            ep_shift = ep - sig_entry
            tp = tp + ep_shift

            # ATR-based TP floor: 最低 ATR×1.5 を保証
            tp_dist_dt = abs(tp - ep)
            _atr_tp_floor = atr * _atr_tp_floor_mult
            if tp_dist_dt < _atr_tp_floor:
                tp = ep + _atr_tp_floor if sig == "BUY" else ep - _atr_tp_floor
                tp_dist_dt = _atr_tp_floor

            # SL可変: エントリー価格からRR比で逆算
            tp_dist_dt = abs(tp - ep)
            MIN_RR_DT = 1.2
            sl_dist_dt = tp_dist_dt / MIN_RR_DT
            MIN_SL_DIST_DT = 0.030  # 3 pip最低保証（0.2pipスプレッド対応）
            sl_dist_dt = max(sl_dist_dt, MIN_SL_DIST_DT)
            sl = ep - sl_dist_dt if sig == "BUY" else ep + sl_dist_dt

            # RR不足チェック
            if tp_dist_dt < sl_dist_dt:
                continue

            sl_m = abs(ep - sl) / max(atr, 1e-6)
            tp_m_actual = abs(tp - ep) / max(atr, 1e-6)

            # ── SL anti-fake-out: Close-based confirmation + genuine breakdown detection ──
            _dt_sl_genuine_threshold = atr * 0.3  # ATR×0.3超のヒゲは本物のブレイクダウン

            outcome = None; bars_held = 0
            _dt_be_activated = False  # Breakeven activated flag (60% TP reached)
            _dt_current_sl = sl       # 動的SL（breakeven/time-decay用）
            for j in range(1, MAX_HOLD + 1):
                if i+1+j >= len(df): break
                fut = df.iloc[i+1+j]
                hi, lo = float(fut["High"]), float(fut["Low"])
                fut_close = float(fut["Close"])

                # ── Partial TP / Trailing: 40% TP到達でSLをbreakevenに移動 ──
                _dt_tp_dist_total = abs(tp - ep)
                if sig == "BUY":
                    _dt_progress = hi - ep
                    if _dt_progress >= _dt_tp_dist_total * 0.4:  # 60%→40% (早期BE化)
                        _dt_be_activated = True
                        _dt_current_sl = max(_dt_current_sl, ep + 0.002)  # BE+0.2pip
                else:
                    _dt_progress = ep - lo
                    if _dt_progress >= _dt_tp_dist_total * 0.4:  # 60%→40%
                        _dt_be_activated = True
                        _dt_current_sl = min(_dt_current_sl, ep - 0.002)  # BE+0.2pip

                # ── Time-decay SL tightening: MAX_HOLD×50%経過後 ──
                if j >= int(MAX_HOLD * 0.5):  # 60%→50% (早期利確保護)
                    if sig == "BUY" and fut_close > ep:
                        _dt_current_sl = max(_dt_current_sl, ep)
                    elif sig == "SELL" and fut_close < ep:
                        _dt_current_sl = min(_dt_current_sl, ep)

                if sig == "BUY":
                    hit_tp = hi >= tp
                    _dt_wick_depth = _dt_current_sl - lo
                    hit_sl = (fut_close <= _dt_current_sl) or (_dt_wick_depth > _dt_sl_genuine_threshold)
                    if hit_tp and hit_sl:
                        if fut_close >= ep:
                            outcome = "WIN"; bars_held = j; break
                        else:
                            outcome = "LOSS"; bars_held = j; break
                    elif hit_tp:
                        outcome = "WIN";  bars_held = j; break
                    elif hit_sl:
                        if _dt_be_activated and _dt_current_sl >= ep:
                            outcome = "WIN"; bars_held = j
                            tp_m_actual = round(_dt_tp_dist_total * 0.6 / max(atr, 1e-6), 3)
                            break
                        else:
                            outcome = "LOSS"; bars_held = j; break
                else:
                    hit_tp = lo <= tp
                    _dt_wick_depth = hi - _dt_current_sl
                    hit_sl = (fut_close >= _dt_current_sl) or (_dt_wick_depth > _dt_sl_genuine_threshold)
                    if hit_tp and hit_sl:
                        if fut_close <= ep:
                            outcome = "WIN"; bars_held = j; break
                        else:
                            outcome = "LOSS"; bars_held = j; break
                    elif hit_tp:
                        outcome = "WIN";  bars_held = j; break
                    elif hit_sl:
                        if _dt_be_activated and _dt_current_sl <= ep:
                            outcome = "WIN"; bars_held = j
                            tp_m_actual = round(_dt_tp_dist_total * 0.6 / max(atr, 1e-6), 3)
                            break
                        else:
                            outcome = "LOSS"; bars_held = j; break

            if outcome:
                last_bar = i
                trade_dict = {"outcome": outcome, "bars_held": bars_held,
                                "sig": sig, "ep": round(ep,3),
                                "sl": round(sl,3), "tp": round(tp,3),
                                "bar_idx": i, "entry_type": entry_type,
                                "sl_m": sl_m, "tp_m": tp_m_actual,
                                "entry_time": str(bar_time)}
                # Close-based SL actual loss: when LOSS and close exceeded SL level
                if outcome == "LOSS":
                    if sig == "BUY" and fut_close < sl:
                        trade_dict["actual_sl_m"] = round(min(abs(fut_close - ep) / max(atr, 1e-6), sl_m * 1.2), 3)
                    elif sig == "SELL" and fut_close > sl:
                        trade_dict["actual_sl_m"] = round(min(abs(fut_close - ep) / max(atr, 1e-6), sl_m * 1.2), 3)
                trades.append(trade_dict)

        def _dt_pnl(t):
            if t["outcome"] == "WIN":
                return t.get("tp_m", TP_MULT)
            else:
                return -t.get("actual_sl_m", t.get("sl_m", SL_MULT))

        if len(trades) < 20:
            result = {"error": f"サンプル数不足（20トレード未満）",
                      "trades": len(trades), "mode": "daytrade"}
        else:
            wins = sum(1 for t in trades if t["outcome"] == "WIN")
            n    = len(trades)
            wr   = round(wins / n * 100, 1)
            ev   = round(sum(_dt_pnl(t) for t in trades) / n, 3)
            avg_hold_h = round(np.mean([t["bars_held"] for t in trades]) / bars_per_h, 1)

            # 最大ドローダウン
            eq, peak, mdd = 0.0, 0.0, 0.0
            for t in trades:
                eq += _dt_pnl(t)
                if eq > peak: peak = eq
                if peak - eq > mdd: mdd = peak - eq
            mdd = round(mdd, 3)

            # Sharpe
            rets = [_dt_pnl(t) for t in trades]
            sharpe = round(np.mean(rets) / max(np.std(rets), 1e-6) * np.sqrt(252), 3) if len(rets) > 1 else 0.0

            # Walk-forward (3窓)
            wf_windows = []
            window_size = n // 3
            for wi in range(3):
                wt = trades[wi*window_size:(wi+1)*window_size]
                if len(wt) < 5: continue
                ww = sum(1 for t in wt if t["outcome"]=="WIN")
                wwr = round(ww/len(wt)*100, 1)
                wev = round(sum(_dt_pnl(t) for t in wt) / len(wt), 3)
                wf_windows.append({"label": f"窓{wi+1}", "window": wi+1, "trades": len(wt),
                                   "win_rate": wwr, "expected_value": wev})
            profitable = sum(1 for w in wf_windows if w.get("expected_value", -1) > 0)

            # エントリータイプ別統計
            dt_entry_stats = {}
            for t in trades:
                et = t.get("entry_type", "ema_cross")
                if et not in dt_entry_stats:
                    dt_entry_stats[et] = {"wins": 0, "total": 0, "pnl": 0.0}
                dt_entry_stats[et]["total"] += 1
                dt_entry_stats[et]["pnl"] += _dt_pnl(t)
                if t["outcome"] == "WIN":
                    dt_entry_stats[et]["wins"] += 1
            for k, v in dt_entry_stats.items():
                v["win_rate"] = round(v["wins"] / v["total"] * 100, 1)
                v["ev"] = round(v["pnl"] / v["total"], 3)

            trades_per_day = round(n / lookback_days, 2)
            verdict = ("✅ 良好" if ev > 0.10 and profitable >= 2 else
                       "🟡 要注意 — 期待値プラスだがWF不安定" if ev > 0 else "❌ 不採用")

            result = {
                "trades": n, "win_rate": wr, "expected_value": ev,
                "avg_hold_hours": avg_hold_h,
                "max_drawdown": mdd, "sharpe": sharpe,
                "trades_per_day": trades_per_day,
                "verdict": verdict,
                "beta": False,
                "period": f"過去{lookback_days}日 ({interval}足)",
                "sl_mult": SL_MULT, "tp_mult": TP_MULT,
                "walk_forward": wf_windows,
                "consistency": f"{profitable}/{len(wf_windows)} 窓でプラス期待値",
                "entry_breakdown": dt_entry_stats,
                "trade_log": trades,
                "mode": "daytrade",
                "data_source": _last_data_source.get(interval, "yfinance"),
                "bars_fetched": len(df),
            }

        _dt_bt_cache[cache_key] = {"result": result, "ts": now}
        return result
    except Exception as e:
        import traceback
        print(f"[DT_BT] {traceback.format_exc()}")
        return {"error": str(e), "mode": "daytrade"}


# ═══════════════════════════════════════════════════════
#  1Hゾーンベースバックテスト
#  Pivot + ATR ゾーンで日次再計算、compute_1h_zone_signal統合
# ═══════════════════════════════════════════════════════
_1h_bt_cache: dict = {}
_1H_BT_TTL = 3600  # 1時間キャッシュ


def run_1h_backtest(symbol: str = "USDJPY=X",
                    lookback_days: int = 30,
                    interval: str = "1h") -> dict:
    """
    1H zone-based backtest — compute_1h_zone_signal統合版
    前日のPivot + ATRでBuy/Sell Zoneを日次再計算。
    ゾーン内リバーサルシグナルでエントリー。
    """
    global _1h_bt_cache
    cache_key = f"{interval}_{lookback_days}"
    now = datetime.now()
    cached = _1h_bt_cache.get(cache_key)
    if cached and (now - cached["ts"]).total_seconds() < _1H_BT_TTL:
        return cached["result"]

    try:
        df = fetch_ohlcv(symbol, period=f"{lookback_days}d", interval=interval)
        df = add_indicators(df)
        df = df.dropna()
        if len(df) < 50:
            return {"error": "データ不足", "trades": 0, "mode": "1h_zone"}

        SPREAD   = 0.008   # 0.8 pip（OANDA実スプレッド）
        MAX_HOLD = 18      # 18 bars = 18 hours（TP到達時間確保）
        COOLDOWN = 1
        MIN_RR   = 1.2

        # ── 日次OHLC集計 & ゾーンプリコンピュテーション ──
        # Group 1h bars by date to get daily OHLC
        df_copy = df.copy()
        df_copy["_date"] = df_copy.index.date
        daily_ohlc = df_copy.groupby("_date").agg(
            {"Open": "first", "High": "max", "Low": "min", "Close": "last", "atr": "mean"}
        )

        # Pre-compute zones dict: {date_str: {"buy_zone", "sell_zone", "pivot"}}
        zone_map = {}
        dates = list(daily_ohlc.index)
        for di in range(1, len(dates)):
            prev = daily_ohlc.loc[dates[di - 1]]
            prev_h = float(prev["High"])
            prev_l = float(prev["Low"])
            prev_c = float(prev["Close"])
            # Daily ATR: approximate from 1h ATR mean * sqrt(24)
            daily_atr_approx = float(prev["atr"]) * np.sqrt(24)

            pivot = (prev_h + prev_l + prev_c) / 3.0

            # ゾーン: Pivotを境にBuy/Sellを分離（ニュートラル帯なし）
            # Buy Zone: 前日安値−ATR*0.2 〜 Pivot（Pivot以下で買い）
            # Sell Zone: Pivot 〜 前日高値+ATR*0.2（Pivot以上で売り）
            bz_lo = prev_l - daily_atr_approx * 0.2
            bz_hi = pivot
            sz_lo = pivot
            sz_hi = prev_h + daily_atr_approx * 0.2

            date_str = str(dates[di])
            zone_map[date_str] = {
                "buy_zone": (round(bz_lo, 4), round(bz_hi, 4)),
                "sell_zone": (round(sz_lo, 4), round(sz_hi, 4)),
                "pivot": round(pivot, 4),
            }

        # ── SR levels (recalc periodically, no lookahead) ──
        SR_RECALC = 60
        _1h_sr_cache = {}
        for _ci in range(50, len(df), SR_RECALC):
            _sr_slice = df.iloc[max(0, _ci - 300):_ci]
            _1h_sr_cache[_ci // SR_RECALC] = find_sr_levels_weighted(
                _sr_slice, window=5, tolerance_pct=0.003, min_touches=2,
                max_levels=8, bars_per_day=24)

        QUALIFIED_TYPES = {
            # 本番 demo_trader.py と統一
            "mtf_momentum", "session_orb",
            # "pivot_breakout",  # DISABLED: 本番WR=0%(3t -66.4pip) — SL幅27pip+逆行エントリー
            "pivot_reversion",
            "h1_fib_reversal", "h1_ema200_trend_reversal",
        }

        trades   = []
        last_bar = -99

        for i in range(50, len(df) - MAX_HOLD - 1):
            if i - last_bar < COOLDOWN:
                continue

            row = df.iloc[i]
            bar_date_str = str(df.index[i].date()) if hasattr(df.index[i], 'date') else str(df.iloc[i]["_date"])

            # Skip if no zone data for this date (first day)
            if bar_date_str not in zone_map:
                continue

            zones = zone_map[bar_date_str]
            buy_zone  = zones["buy_zone"]
            sell_zone = zones["sell_zone"]

            # Volume filter
            if "Volume" in df.columns:
                vol = float(row["Volume"])
                if vol > 0 and vol < 100:
                    continue

            # Bar range filter
            bar_range = float(row["High"]) - float(row["Low"])
            if bar_range < 0.030:
                continue

            # ── Call compute_1h_zone_signal ──
            _sr_key = i // SR_RECALC
            current_sr_weighted = _1h_sr_cache.get(_sr_key, [])
            current_sr = [sr["price"] for sr in current_sr_weighted]

            bar_df = df.iloc[max(0, i - 300):i + 1]

            try:
                sig_result = compute_1h_zone_signal(
                    bar_df,
                    buy_zone=buy_zone,
                    sell_zone=sell_zone,
                    sr_levels=current_sr,
                    backtest_mode=True,
                )
            except Exception:
                continue

            sig = sig_result.get("signal", "WAIT")
            if sig == "WAIT":
                continue

            entry_type = sig_result.get("entry_type", "unknown")

            # ── Entry quality gate ──
            if entry_type not in QUALIFIED_TYPES:
                continue
            _reasons = sig_result.get("reasons", [])
            _confirmed = sum(1 for r in _reasons if "✅" in r)
            if _confirmed < 1:
                continue

            atr = sig_result.get("atr", float(row.get("atr", 0.10)))

            # Entry at next bar's Open
            if i + 1 >= len(df):
                continue
            ep = float(df.iloc[i + 1]["Open"])
            ep = ep + SPREAD / 2 if sig == "BUY" else ep - SPREAD / 2

            # TP from signal, adjusted for entry shift
            sig_entry = sig_result.get("entry", ep)
            tp = sig_result.get("tp", ep)
            ep_shift = ep - sig_entry
            tp = tp + ep_shift

            # 1h Zone: シグナルのTP/SLをそのまま使用（エントリー価格シフト分のみ補正）
            # TP floorは不要（シグナル関数で最適サイズ計算済み）
            tp_dist = abs(tp - ep)
            if tp_dist < 0.005:  # 最低0.5 pip保証
                continue

            # SL: シグナルのSLをそのまま使用（ep_shift分補正）
            sl = sig_result.get("sl", ep)
            sl = sl + ep_shift
            sl_dist = abs(ep - sl)
            MIN_SL_DIST = 0.030
            sl_dist = max(sl_dist, MIN_SL_DIST)
            sl = ep - sl_dist if sig == "BUY" else ep + sl_dist

            # RR check
            if tp_dist < sl_dist:
                continue

            sl_m = abs(ep - sl) / max(atr, 1e-6)
            tp_m_actual = abs(tp - ep) / max(atr, 1e-6)

            # ── SL anti-fake-out: Close-based + genuine breakdown (ATR*0.3) ──
            _sl_genuine_threshold = atr * 0.3

            # ── シナリオ崩壊撤退レベル ──
            _inv_price = sig_result.get("invalidation")
            if _inv_price is not None:
                _inv_price = _inv_price + ep_shift  # エントリーシフト補正

            outcome = None
            bars_held = 0
            _be_activated = False
            _current_sl = sl
            for j in range(1, MAX_HOLD + 1):
                if i + 1 + j >= len(df):
                    break
                fut = df.iloc[i + 1 + j]
                hi, lo = float(fut["High"]), float(fut["Low"])
                fut_close = float(fut["Close"])

                # ── シナリオ崩壊チェック（SLより先に判定）──
                # 終値ベース: ノイズのヒゲではなく確定足でシナリオ判定
                if _inv_price is not None:
                    if sig == "BUY" and fut_close < _inv_price:
                        outcome = "LOSS"
                        bars_held = j
                        break
                    elif sig == "SELL" and fut_close > _inv_price:
                        outcome = "LOSS"
                        bars_held = j
                        break

                # ── Breakeven at 50% TP + Trailing Stop ──
                _tp_dist_total = abs(tp - ep)
                _trail_atr = atr * 0.8  # トレーリング幅: 0.8 ATR
                if sig == "BUY":
                    _progress = hi - ep
                    # 50%到達でBE (旧60%)
                    if _progress >= _tp_dist_total * 0.5:
                        _be_activated = True
                        _current_sl = max(_current_sl, ep)
                    # トレーリングストップ: 最高値 - 0.8ATR
                    if _be_activated:
                        _trail_sl = hi - _trail_atr
                        _current_sl = max(_current_sl, _trail_sl)
                else:
                    _progress = ep - lo
                    if _progress >= _tp_dist_total * 0.5:
                        _be_activated = True
                        _current_sl = min(_current_sl, ep)
                    if _be_activated:
                        _trail_sl = lo + _trail_atr
                        _current_sl = min(_current_sl, _trail_sl)

                # ── Time-decay SL tightening after 60% MAX_HOLD ──
                if j >= int(MAX_HOLD * 0.6):
                    if sig == "BUY" and fut_close > ep:
                        _current_sl = max(_current_sl, ep)
                    elif sig == "SELL" and fut_close < ep:
                        _current_sl = min(_current_sl, ep)

                if sig == "BUY":
                    hit_tp = hi >= tp
                    _wick_depth = _current_sl - lo
                    hit_sl = (fut_close <= _current_sl) or (_wick_depth > _sl_genuine_threshold)
                    if hit_tp and hit_sl:
                        outcome = "WIN" if fut_close >= ep else "LOSS"
                        bars_held = j
                        break
                    elif hit_tp:
                        outcome = "WIN"
                        bars_held = j
                        break
                    elif hit_sl:
                        if _be_activated and _current_sl >= ep:
                            outcome = "WIN"
                            bars_held = j
                            tp_m_actual = round(_tp_dist_total * 0.6 / max(atr, 1e-6), 3)
                        else:
                            outcome = "LOSS"
                            bars_held = j
                        break
                else:
                    hit_tp = lo <= tp
                    _wick_depth = hi - _current_sl
                    hit_sl = (fut_close >= _current_sl) or (_wick_depth > _sl_genuine_threshold)
                    if hit_tp and hit_sl:
                        outcome = "WIN" if fut_close <= ep else "LOSS"
                        bars_held = j
                        break
                    elif hit_tp:
                        outcome = "WIN"
                        bars_held = j
                        break
                    elif hit_sl:
                        if _be_activated and _current_sl <= ep:
                            outcome = "WIN"
                            bars_held = j
                            tp_m_actual = round(_tp_dist_total * 0.6 / max(atr, 1e-6), 3)
                        else:
                            outcome = "LOSS"
                            bars_held = j
                        break

            if outcome:
                last_bar = i
                trade_dict = {
                    "outcome": outcome, "bars_held": bars_held,
                    "sig": sig, "ep": round(ep, 3),
                    "sl": round(sl, 3), "tp": round(tp, 3),
                    "bar_idx": i, "entry_type": entry_type,
                    "sl_m": sl_m, "tp_m": tp_m_actual,
                    "entry_time": str(df.index[i]),
                }
                if outcome == "LOSS":
                    # シナリオ崩壊 or SL hitの実損記録
                    _actual_loss = abs(fut_close - ep) / max(atr, 1e-6)
                    trade_dict["actual_sl_m"] = round(min(_actual_loss, sl_m * 1.5), 3)
                trades.append(trade_dict)

        # ── PnL helper ──
        def _1h_pnl(t):
            if t["outcome"] == "WIN":
                return t.get("tp_m", 2.5)
            else:
                return -t.get("actual_sl_m", t.get("sl_m", 1.0))

        if len(trades) < 5:
            result = {"error": f"サンプル数不足（5トレード未満: {len(trades)}件）",
                      "trades": len(trades), "mode": "1h_zone"}
        else:
            wins = sum(1 for t in trades if t["outcome"] == "WIN")
            n    = len(trades)
            wr   = round(wins / n * 100, 1)
            ev   = round(sum(_1h_pnl(t) for t in trades) / n, 3)
            avg_hold_h = round(np.mean([t["bars_held"] for t in trades]), 1)

            # Max drawdown
            eq, peak, mdd = 0.0, 0.0, 0.0
            for t in trades:
                eq += _1h_pnl(t)
                if eq > peak:
                    peak = eq
                if peak - eq > mdd:
                    mdd = peak - eq
            mdd = round(mdd, 3)

            # Sharpe
            rets = [_1h_pnl(t) for t in trades]
            sharpe = round(np.mean(rets) / max(np.std(rets), 1e-6) * np.sqrt(252), 3) if len(rets) > 1 else 0.0

            # Walk-forward (3 windows)
            wf_windows = []
            window_size = max(n // 3, 1)
            for wi in range(3):
                wt = trades[wi * window_size:(wi + 1) * window_size]
                if len(wt) < 2:
                    continue
                ww = sum(1 for t in wt if t["outcome"] == "WIN")
                wwr = round(ww / len(wt) * 100, 1)
                wev = round(sum(_1h_pnl(t) for t in wt) / len(wt), 3)
                wf_windows.append({
                    "label": f"窓{wi + 1}", "window": wi + 1, "trades": len(wt),
                    "win_rate": wwr, "expected_value": wev,
                })
            profitable = sum(1 for w in wf_windows if w.get("expected_value", -1) > 0)

            # Entry type breakdown
            entry_stats = {}
            for t in trades:
                et = t.get("entry_type", "unknown")
                if et not in entry_stats:
                    entry_stats[et] = {"wins": 0, "total": 0, "pnl": 0.0}
                entry_stats[et]["total"] += 1
                entry_stats[et]["pnl"] += _1h_pnl(t)
                if t["outcome"] == "WIN":
                    entry_stats[et]["wins"] += 1
            for k, v in entry_stats.items():
                v["win_rate"] = round(v["wins"] / v["total"] * 100, 1)
                v["ev"] = round(v["pnl"] / v["total"], 3)

            trades_per_day = round(n / max(lookback_days, 1), 2)
            verdict = ("✅ 良好" if ev > 0.10 and profitable >= 2 else
                       "🟡 要注意 — 期待値プラスだがWF不安定" if ev > 0 else "❌ 不採用")

            result = {
                "trades": n, "win_rate": wr, "expected_value": ev,
                "avg_hold_hours": avg_hold_h,
                "max_drawdown": mdd, "sharpe": sharpe,
                "trades_per_day": trades_per_day,
                "verdict": verdict,
                "beta": True,
                "period": f"過去{lookback_days}日 ({interval}足)",
                "walk_forward": wf_windows,
                "consistency": f"{profitable}/{len(wf_windows)} 窓でプラス期待値",
                "entry_breakdown": entry_stats,
                "trade_log": trades,
                "mode": "1h_zone",
                "data_source": _last_data_source.get(interval, "yfinance"),
                "bars_fetched": len(df),
            }

        _1h_bt_cache[cache_key] = {"result": result, "ts": now}
        return result
    except Exception as e:
        import traceback
        print(f"[1H_BT] {traceback.format_exc()}")
        return {"error": str(e), "mode": "1h_zone"}


# ═══════════════════════════════════════════════════════
#  スイングトレードバックテスト（1d / 365日）
#  学術根拠: 12-1モメンタム + EMA200 + フィボ61.8% + RSIダイバージェンス
# ═══════════════════════════════════════════════════════
_sw_bt_cache: dict = {}
SW_BT_TTL = 21600  # 6時間キャッシュ

def run_swing_backtest(symbol: str = "USDJPY=X",
                       lookback_days: int = 730) -> dict:
    """
    スイングトレードバックテスト（1d足, 2年分） — compute_swing_signal統合版
    本番環境と同一のエントリーロジック（compute_swing_signal）を使用。
    BT固有: SL/TP simulation, trade tracking, entry cooldown
    """
    global _sw_bt_cache
    now = datetime.now()
    if _sw_bt_cache.get("ts") and (now - _sw_bt_cache["ts"]).total_seconds() < SW_BT_TTL:
        return _sw_bt_cache["result"]

    try:
        df = fetch_ohlcv(symbol, period="1095d", interval="1d")
        df = add_indicators(df)
        df = df.dropna()
        if len(df) < 100:
            return {"error": "データ不足", "trades": 0, "mode": "swing"}

        SPREAD   = 0.008   # 0.8 pip（OANDA実スプレッド）
        SL_MULT  = 1.5     # デフォルトSL
        TP_MULT  = 3.0     # デフォルトTP（RR 1:2）
        MAX_HOLD = 20      # 日
        COOLDOWN = 1       # 日（旧3→高頻度化）

        cutoff_i = max(250, len(df) - lookback_days)

        # ── SR/OB/Fib プリコンピュート（1d足 = bars_per_day=1）──
        SW_SR_RECALC = 20   # 20日ごとに再計算
        _sw_sr_cache = {}
        _sw_ob_cache = {}
        _sw_fib_cache = {}
        for _ci in range(200, len(df), SW_SR_RECALC):
            _sr_slice = df.iloc[max(0, _ci - 200):_ci]
            _sw_sr_cache[_ci // SW_SR_RECALC] = find_sr_levels_weighted(
                _sr_slice, window=3, tolerance_pct=0.005, min_touches=2,
                max_levels=10, bars_per_day=1)
            try:
                _, _obs = detect_order_blocks(
                    df.iloc[max(0, _ci - 60):_ci], atr_mult=1.5, lookback=50)
                _sw_ob_cache[_ci // SW_SR_RECALC] = _obs
            except Exception:
                _sw_ob_cache[_ci // SW_SR_RECALC] = []
            _sw_fib_cache[_ci // SW_SR_RECALC] = _calc_fibonacci_levels(
                df.iloc[max(0, _ci - 120):_ci], lookback=100)

        trades = []
        last_bar = -99

        # ── HTF bias: BT mode = neutral (ルックアヘッドバイアス排除) ──
        # get_htf_bias() は現在のyfinanceデータを使うためBTでは無効化
        try:
            _layer1 = get_master_bias(symbol)
        except Exception:
            _layer1 = {"direction": "neutral", "label": "—", "score": 0}
        _htf_cache = {
            "htf": {"score": 0, "agreement": "neutral", "label": "BT: HTFバイアス無効"},
            "layer1": _layer1,
        }

        MIN_BARS = 250  # compute_swing_signalに必要な最小バー数

        for i in range(max(cutoff_i, MIN_BARS), len(df) - MAX_HOLD - 1):
            if i - last_bar < COOLDOWN:
                continue

            row = df.iloc[i]
            atr = float(row["atr"])
            if atr <= 0:
                continue

            # ── SR取得 ──
            sr_key = i // SW_SR_RECALC
            current_sr = _sw_sr_cache.get(sr_key, _sw_sr_cache.get(sr_key - 1, []))

            # ── 本番環境と統一: compute_swing_signalを呼び出し ──
            current_sr_prices = [sr["price"] for sr in current_sr] if current_sr else []

            bar_df = df.iloc[max(0, i - 500):i + 1]
            bar_time = df.index[i]
            if hasattr(bar_time, 'tzinfo') and bar_time.tzinfo is None:
                bar_time = bar_time.replace(tzinfo=timezone.utc)

            try:
                sig_result = compute_swing_signal(
                    bar_df, tf='1d', sr_levels=current_sr_prices,
                    symbol=symbol, backtest_mode=True,
                    bar_time=bar_time, htf_cache=_htf_cache,
                )
            except Exception:
                continue

            sig = sig_result.get("signal", "WAIT")
            if sig == "WAIT":
                continue

            entry_type = sig_result.get("entry_type", "unknown")

            # BT用: 次バーのOpenでエントリー（スリッページ反映）
            if i + 1 >= len(df):
                continue
            ep = float(df.iloc[i + 1]["Open"])
            ep = ep + SPREAD / 2 if sig == "BUY" else ep - SPREAD / 2

            # SL/TPをcompute_swing_signalの値ベースで再計算（epの差分を反映）
            sig_entry = sig_result.get("entry", ep)
            sl = sig_result.get("sl", ep)
            tp = sig_result.get("tp", ep)
            ep_shift = ep - sig_entry
            sl = sl + ep_shift
            tp = tp + ep_shift

            sl_m = abs(ep - sl) / max(atr, 1e-6)
            tp_m = abs(tp - ep) / max(atr, 1e-6)

            # ── Close-based SL（騙し回避: 終値ベースでSL判定）──
            outcome = None
            bars_held = 0
            for j in range(1, MAX_HOLD + 1):
                if i+1+j >= len(df):
                    break
                fut = df.iloc[i+1+j]
                hi, lo = float(fut["High"]), float(fut["Low"])
                fut_close = float(fut["Close"])
                if sig == "BUY":
                    hit_tp = hi >= tp
                    # SL: 終値ベース（ヒゲ騙し回避）
                    hit_sl = fut_close <= sl
                    if hit_tp and hit_sl:
                        outcome = "LOSS"; bars_held = j; break
                    elif hit_tp:
                        outcome = "WIN";  bars_held = j; break
                    elif hit_sl:
                        outcome = "LOSS"; bars_held = j; break
                else:
                    hit_tp = lo <= tp
                    hit_sl = fut_close >= sl
                    if hit_tp and hit_sl:
                        outcome = "LOSS"; bars_held = j; break
                    elif hit_tp:
                        outcome = "WIN";  bars_held = j; break
                    elif hit_sl:
                        outcome = "LOSS"; bars_held = j; break

            if outcome:
                last_bar = i
                trade_dict = {"outcome": outcome, "bars_held": bars_held,
                                "sig": sig, "ep": round(ep,3),
                                "sl": round(sl,3), "tp": round(tp,3),
                                "sl_m": sl_m, "tp_m": tp_m,
                                "entry_type": entry_type,
                                "bar_idx": i}
                # Close-based SL actual loss: when LOSS and close exceeded SL level
                if outcome == "LOSS":
                    if sig == "BUY" and fut_close < sl:
                        trade_dict["actual_sl_m"] = round(min(abs(fut_close - ep) / max(atr, 1e-6), sl_m * 1.2), 3)
                    elif sig == "SELL" and fut_close > sl:
                        trade_dict["actual_sl_m"] = round(min(abs(fut_close - ep) / max(atr, 1e-6), sl_m * 1.2), 3)
                trades.append(trade_dict)

        if len(trades) < 8:
            result = {"error": f"サンプル数不足（{len(trades)}トレード）",
                      "trades": len(trades), "mode": "swing"}
        else:
            def _pnl_sw(t):
                if t["outcome"] == "WIN":
                    return t.get("tp_m", TP_MULT)
                else:
                    return -t.get("actual_sl_m", t.get("sl_m", SL_MULT))

            n    = len(trades)
            wins = sum(1 for t in trades if t["outcome"] == "WIN")
            wr   = round(wins / n * 100, 1)
            ev   = round(sum(_pnl_sw(t) for t in trades) / n, 3)
            avg_hold = round(np.mean([t["bars_held"] for t in trades]), 1)

            eq, peak, mdd = 0.0, 0.0, 0.0
            for t in trades:
                eq += _pnl_sw(t)
                if eq > peak: peak = eq
                if peak - eq > mdd: mdd = peak - eq
            mdd = round(mdd, 3)

            rets = [_pnl_sw(t) for t in trades]
            sharpe = round(np.mean(rets) / max(np.std(rets), 1e-6) * np.sqrt(252/avg_hold), 3) if len(rets) > 1 else 0.0

            # Entry breakdown
            entry_stats = {}
            for t in trades:
                et = t.get("entry_type", "ema_trend")
                if et not in entry_stats:
                    entry_stats[et] = {"wins": 0, "total": 0, "pnl": 0.0}
                entry_stats[et]["total"] += 1
                entry_stats[et]["pnl"] += _pnl_sw(t)
                if t["outcome"] == "WIN":
                    entry_stats[et]["wins"] += 1
            entry_breakdown = {}
            for et, st in entry_stats.items():
                entry_breakdown[et] = {
                    "wins": st["wins"], "total": st["total"],
                    "win_rate": round(st["wins"]/st["total"]*100, 1) if st["total"] else 0,
                    "ev": round(st["pnl"]/st["total"], 3) if st["total"] else 0,
                }

            wf_windows = []
            ws = max(4, n // 3)
            for wi in range(3):
                wt = trades[wi*ws:(wi+1)*ws]
                if len(wt) < 4: continue
                ww = sum(1 for t in wt if t["outcome"]=="WIN")
                wwr = round(ww/len(wt)*100, 1)
                wev = round(sum(_pnl_sw(t) for t in wt)/len(wt), 3)
                wf_windows.append({"window": wi+1, "label": f"窓{wi+1}",
                                   "trades": len(wt), "win_rate": wwr,
                                   "expected_value": wev})
            profitable = sum(1 for w in wf_windows if w["expected_value"] > 0)

            trades_per_day = round(n / lookback_days, 3)
            verdict = ("✅ 良好" if ev > 0.15 and profitable >= 2 else
                       "🟡 β版 — 期待値プラスだが要監視" if ev > 0 else "❌ 不採用")

            result = {
                "trades": n, "win_rate": wr, "expected_value": ev,
                "wins": wins, "losses": n - wins,
                "avg_hold_days": avg_hold,
                "max_drawdown": mdd, "sharpe": sharpe,
                "trades_per_day": trades_per_day,
                "verdict": verdict,
                "period": f"過去{lookback_days}日 (1d足)",
                "sl_mult": SL_MULT, "tp_mult": TP_MULT,
                "walk_forward": wf_windows,
                "consistency": f"{profitable}/{len(wf_windows)} 窓でプラス期待値",
                "entry_breakdown": entry_breakdown,
                "trade_log": trades[-10:],
                "mode": "swing",
            }

        _sw_bt_cache["result"] = result
        _sw_bt_cache["ts"] = now
        return result
    except Exception as e:
        import traceback
        print(f"[SW_BT] {traceback.format_exc()}")
        return {"error": str(e), "mode": "swing"}


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
        df_d = fetch_ohlcv(symbol, period="1y", interval="1d")
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

        # 日足ATR — need at least 201 rows for EMA200 in add_indicators
        MIN_ROWS_FOR_INDICATORS = 201
        if len(df_d) >= MIN_ROWS_FOR_INDICATORS:
            df_di = add_indicators(df_d.copy())
            datr  = round(float(df_di["atr"].iloc[-1]), 3) if len(df_di) > 0 else 0.3
        else:
            # Not enough data for full indicators; compute ATR directly
            atr_series = AverageTrueRange(
                df_d["High"], df_d["Low"], df_d["Close"], window=min(14, len(df_d) - 1)
            ).average_true_range()
            datr = round(float(atr_series.dropna().iloc[-1]), 3) if len(atr_series.dropna()) > 0 else 0.3

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


def detect_market_regime(df: pd.DataFrame) -> dict:
    """
    市場レジーム判定 (Market Regime Detector)
    ────────────────────────────────────────────
    4種のレジームを分類:
      TREND_BULL  : 上昇トレンド (EMA順列 + ADX>25 + close>EMA200)
      TREND_BEAR  : 下降トレンド (EMA逆順 + ADX>25 + close<EMA200)
      RANGE       : レンジ相場   (ADX<20 + BB幅スクイーズ)
      HIGH_VOL    : 高ボラ警戒  (ATR>1.8×20日平均)

    Returns dict:
      regime: "TREND_BULL" | "TREND_BEAR" | "RANGE" | "HIGH_VOL"
      label: str (Japanese)
      adx: float
      bb_width_pct: float (BB width percentile vs 50-bar)
      atr_ratio: float (current ATR / 20-bar avg ATR)
      ema_stack_bull: bool
      ema_stack_bear: bool
    """
    if len(df) < 50:
        return {"regime": "UNKNOWN", "label": "データ不足", "adx": 0.0,
                "bb_width_pct": 50.0, "atr_ratio": 1.0,
                "ema_stack_bull": False, "ema_stack_bear": False}

    row = df.iloc[-1]
    adx    = float(row.get("adx", 20.0))
    close  = float(row["Close"])
    ema9   = float(row["ema9"])
    ema21  = float(row["ema21"])
    ema50  = float(row["ema50"])
    ema200 = float(row.get("ema200", row["ema50"]))
    atr    = float(row["atr"])

    # BB width percentile (vs past 50 bars)
    if "bb_width" in df.columns:
        bb_w_series = df["bb_width"].tail(50).dropna()
        bb_w_cur    = float(row.get("bb_width", atr * 2))
        bb_pct      = float((bb_w_series < bb_w_cur).sum()) / max(len(bb_w_series), 1) * 100
    else:
        bb_pct = 50.0

    # ATR ratio (current vs 20-bar mean)
    atr_series = df["atr"].tail(20).dropna()
    atr_avg    = float(atr_series.mean()) if len(atr_series) > 0 else atr
    atr_ratio  = atr / atr_avg if atr_avg > 0 else 1.0

    # EMA stack
    ema_bull = (ema9 > ema21 > ema50) and (close > ema200)
    ema_bear = (ema9 < ema21 < ema50) and (close < ema200)

    # Regime classification
    if atr_ratio > 1.8:
        regime = "HIGH_VOL"
        label  = "⚠️ 高ボラティリティ — 警戒"
    elif adx < 20 and bb_pct < 40:
        regime = "RANGE"
        label  = "↔️ レンジ相場 — スキャル有利"
    elif adx >= 25 and ema_bull:
        regime = "TREND_BULL"
        label  = "🟢 上昇トレンド — BUY主体"
    elif adx >= 25 and ema_bear:
        regime = "TREND_BEAR"
        label  = "🔴 下降トレンド — SELL主体"
    elif adx >= 20 and ema_bull:
        regime = "TREND_BULL"
        label  = "🟡 弱い上昇トレンド"
    elif adx >= 20 and ema_bear:
        regime = "TREND_BEAR"
        label  = "🟡 弱い下降トレンド"
    else:
        regime = "RANGE"
        label  = "↔️ 方向感なし — 様子見"

    return {
        "regime":          regime,
        "label":           label,
        "adx":             round(adx, 1),
        "bb_width_pct":    round(bb_pct, 1),
        "atr_ratio":       round(atr_ratio, 2),
        "ema_stack_bull":  ema_bull,
        "ema_stack_bear":  ema_bear,
        "close_vs_ema200": round(close - ema200, 3),
    }


def extract_ml_features(df: pd.DataFrame, i: int) -> "list | None":
    """
    Extract ML features for bar at position i.
    Returns list of 12 features or None if data insufficient.
    No lookahead bias: only uses bars 0..i
    """
    if i < 50 or i >= len(df):
        return None
    try:
        row      = df.iloc[i]
        prev5    = df.iloc[i-5:i]

        ema9  = float(row.get("ema9",  row["Close"]))
        ema21 = float(row.get("ema21", row["Close"]))
        ema50 = float(row.get("ema50", row["Close"]))
        atr   = float(row.get("atr",   0.01))
        adx   = float(row.get("adx",   20.0))
        rsi   = float(row.get("rsi",   50.0))
        macdh = float(row.get("macd_hist", 0.0))
        close = float(row["Close"])

        # Feature 1-3: EMA alignment
        ema9_21_slope  = (ema9  - float(df.iloc[i-5]["ema9"]))  / (atr + 1e-6)
        ema21_50_dist  = (ema21 - ema50) / (atr + 1e-6)
        price_ema21    = (close - ema21) / (atr + 1e-6)

        # Feature 4-5: Momentum
        rsi_norm       = (rsi - 50.0) / 50.0   # -1 to +1
        macd_norm      = macdh / (atr + 1e-6)

        # Feature 6: Trend strength
        adx_norm       = min(adx / 50.0, 1.0)  # 0 to 1

        # Feature 7: ATR ratio (volatility regime)
        atr_20avg      = float(df["atr"].iloc[i-20:i].mean()) if i >= 20 else atr
        atr_ratio      = atr / (atr_20avg + 1e-6)

        # Feature 8-9: Time features
        try:
            hour      = row.name.hour / 24.0
            weekday   = row.name.weekday() / 4.0  # 0=Mon, 4=Fri → 0 to 1
        except Exception:
            hour, weekday = 0.5, 0.5

        # Feature 10: Recent volatility direction
        hi5 = float(prev5["High"].max())
        lo5 = float(prev5["Low"].min())
        range5 = (hi5 - lo5) / (atr + 1e-6)

        # Feature 11: Price momentum 5 bars
        price_momentum = (close - float(df.iloc[i-5]["Close"])) / (atr + 1e-6)

        # Feature 12: RSI trend (change over 5 bars)
        rsi_5ago = float(df["rsi"].iloc[i-5])
        rsi_slope = (rsi - rsi_5ago) / 50.0

        return [
            ema9_21_slope, ema21_50_dist, price_ema21,
            rsi_norm, macd_norm, adx_norm, atr_ratio,
            hour, weekday, range5, price_momentum, rsi_slope
        ]
    except Exception:
        return None


def train_ml_model() -> bool:
    """
    Train RandomForest on historical scalp BT results.
    Returns True if successful.
    """
    global _ml_model, _ml_scaler, _ml_trained_at
    if not _ML_AVAILABLE:
        return False

    try:
        # Fetch 60 days of 5m data
        df = fetch_ohlcv("USDJPY=X", period="60d", interval="5m")
        df = add_indicators(df)
        df = df.dropna()
        if len(df) < 500:
            return False

        # Simulate trades using BT logic to generate labeled samples
        SPREAD  = 0.008   # 0.8 pip（OANDA実スプレッド）
        SL_MULT = 0.8
        TP_MULT = 1.5
        MAX_HOLD = 12

        X, y = [], []

        for i in range(50, len(df) - MAX_HOLD - 2):
            row      = df.iloc[i]
            prev_row = df.iloc[i-1]

            try:
                ema9   = float(row["ema9"])
                ema21  = float(row["ema21"])
                ema50  = float(row["ema50"])
                ema9_p = float(prev_row["ema9"])
                ema21_p= float(prev_row["ema21"])
                atr7   = float(row.get("atr7", row["atr"]))
                adx    = float(row.get("adx", 20.0))
            except Exception:
                continue

            cross_up   = (ema9_p <= ema21_p) and (ema9 > ema21)
            cross_down = (ema9_p >= ema21_p) and (ema9 < ema21)
            if not cross_up and not cross_down:
                continue
            if cross_up   and ema9 < ema50: continue
            if cross_down and ema9 > ema50: continue
            if adx < 12: continue

            feats = extract_ml_features(df, i)
            if feats is None:
                continue

            # Simulate outcome
            sig = "BUY" if cross_up else "SELL"
            ep  = float(df.iloc[i+1]["Open"])
            ep  = ep + SPREAD/2 if sig == "BUY" else ep - SPREAD/2
            sl  = ep - atr7 * SL_MULT if sig == "BUY" else ep + atr7 * SL_MULT
            tp  = ep + atr7 * TP_MULT if sig == "BUY" else ep - atr7 * TP_MULT

            outcome = None
            for j in range(1, MAX_HOLD + 1):
                if i + 1 + j >= len(df): break
                fut = df.iloc[i+1+j]
                hi, lo = float(fut["High"]), float(fut["Low"])
                if sig == "BUY":
                    if hi >= tp: outcome = 1; break
                    if lo <= sl: outcome = 0; break
                else:
                    if lo <= tp: outcome = 1; break
                    if hi >= sl: outcome = 0; break

            if outcome is not None:
                # Adjust features for signal direction (flip for SELL)
                if sig == "SELL":
                    feats[0] = -feats[0]  # ema slope
                    feats[1] = -feats[1]  # ema dist
                    feats[2] = -feats[2]  # price_ema
                    feats[3] = -feats[3]  # rsi
                    feats[4] = -feats[4]  # macd
                    feats[10]= -feats[10] # momentum
                    feats[11]= -feats[11] # rsi slope
                X.append(feats)
                y.append(outcome)

        if len(X) < _ML_MIN_SAMPLES:
            return False

        X_arr = np.array(X)
        y_arr = np.array(y)

        # ── TimeSeriesSplit 交差検証 (OOS精度を正しく計測) ──
        from sklearn.metrics import accuracy_score
        tscv = TimeSeriesSplit(n_splits=5)
        oos_scores = []
        for train_idx, test_idx in tscv.split(X_arr):
            X_tr, X_te = X_arr[train_idx], X_arr[test_idx]
            y_tr, y_te = y_arr[train_idx], y_arr[test_idx]
            _sc = StandardScaler()
            X_tr_s = _sc.fit_transform(X_tr)
            X_te_s = _sc.transform(X_te)
            _rf = RandomForestClassifier(
                n_estimators=100, max_depth=6, min_samples_leaf=10,
                class_weight="balanced", random_state=42, n_jobs=-1
            )
            _rf.fit(X_tr_s, y_tr)
            oos_scores.append(accuracy_score(y_te, _rf.predict(X_te_s)))

        oos_acc = float(np.mean(oos_scores))
        oos_std = float(np.std(oos_scores))
        print(f"[ML] CV OOS accuracy: {oos_acc:.2%} ± {oos_std:.2%} (5-fold TimeSeriesSplit)")

        # ── 最終モデル: 全データで学習 ──
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_arr)

        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_scaled, y_arr)

        # Save to disk
        with open(_ml_model_file, "wb") as f:
            pickle.dump(model, f)
        with open(_ml_scaler_file, "wb") as f:
            pickle.dump(scaler, f)

        _ml_model   = model
        _ml_scaler  = scaler
        _ml_trained_at = datetime.now()

        # Report both in-sample and OOS
        preds = model.predict(X_scaled)
        in_acc = accuracy_score(y_arr, preds)
        print(f"[ML] Model trained: {len(X)} samples, in-sample={in_acc:.2%}, OOS={oos_acc:.2%} ± {oos_std:.2%}")
        # Store CV metrics for API access
        _ml_model._cv_oos_acc = oos_acc
        _ml_model._cv_oos_std = oos_std
        _ml_model._cv_in_sample = in_acc
        _ml_model._cv_n_samples = len(X)
        return True

    except Exception as e:
        print(f"[ML] Training failed: {e}")
        return False


def get_ml_confidence(df: pd.DataFrame, i: int, signal: str) -> float:
    """
    Return ML win probability for signal at bar i. 0.5 = neutral (no model).
    """
    global _ml_model, _ml_scaler, _ml_trained_at
    if not _ML_AVAILABLE:
        return 0.5

    # Auto-load from disk if needed
    if _ml_model is None:
        try:
            if os.path.exists(_ml_model_file) and os.path.exists(_ml_scaler_file):
                with open(_ml_model_file, "rb") as f:
                    _ml_model = pickle.load(f)
                with open(_ml_scaler_file, "rb") as f:
                    _ml_scaler = pickle.load(f)
        except Exception:
            pass

    # Retrain if stale or missing
    if _ml_model is None or (
        _ml_trained_at and
        (datetime.now() - _ml_trained_at).total_seconds() > _ML_RETRAIN_HOURS * 3600
    ):
        train_ml_model()

    if _ml_model is None or _ml_scaler is None:
        return 0.5

    try:
        feats = extract_ml_features(df, i)
        if feats is None:
            return 0.5
        if signal == "SELL":
            feats[0]  = -feats[0]
            feats[1]  = -feats[1]
            feats[2]  = -feats[2]
            feats[3]  = -feats[3]
            feats[4]  = -feats[4]
            feats[10] = -feats[10]
            feats[11] = -feats[11]
        X = _ml_scaler.transform([feats])
        prob = float(_ml_model.predict_proba(X)[0][1])
        return round(prob, 3)
    except Exception:
        return 0.5


def compute_layer2_score(df: pd.DataFrame, tf: str) -> dict:
    """
    Layer 2: トレンド構造確認 (EMA配列 / ダウ理論 / S/R位置)
    ─────────────────────────────────────────────────────────
    スコア範囲: -1.0 ~ +1.0
      +1.0 = 完全な上昇構造 (EMA全順列 + ダウ高値切上 + 上昇チャネル内)
      -1.0 = 完全な下降構造
       0.0 = 中立 / 不明確

    各コンポーネント:
      ① EMA stack score  (weight: 0.40) — 9>21>50>200 or 逆
      ② Dow theory score (weight: 0.35) — HH/HL or LL/LH
      ③ Channel position (weight: 0.25) — 線形回帰チャネル内の位置
    """
    if len(df) < 50:
        return {"score": 0.0, "label": "データ不足", "components": {}}

    row    = df.iloc[-1]
    close  = float(row["Close"])
    ema9   = float(row["ema9"])
    ema21  = float(row["ema21"])
    ema50  = float(row["ema50"])
    ema200 = float(row.get("ema200", row["ema50"]))

    # ① EMA stack score
    if   ema9 > ema21 > ema50 > ema200: ema_sc = 1.0
    elif ema9 > ema21 > ema50:          ema_sc = 0.6
    elif ema9 > ema21:                  ema_sc = 0.3
    elif ema9 < ema21 < ema50 < ema200: ema_sc = -1.0
    elif ema9 < ema21 < ema50:          ema_sc = -0.6
    elif ema9 < ema21:                  ema_sc = -0.3
    else:                               ema_sc = 0.0
    # EMA200 bonus: price above/below EMA200
    if close > ema200 and ema_sc > 0:   ema_sc = min(1.0, ema_sc + 0.2)
    if close < ema200 and ema_sc < 0:   ema_sc = max(-1.0, ema_sc - 0.2)

    # ② Dow theory
    dow_sc_raw, _ = dow_theory_analysis(df)
    dow_sc = max(-1.0, min(1.0, dow_sc_raw / 2.5))

    # ③ Channel position (linear regression channel)
    try:
        lb = min(50, len(df))
        closes = df["Close"].tail(lb).values.astype(float)
        x = np.arange(len(closes))
        coeffs = np.polyfit(x, closes, 1)
        trend_slope = coeffs[0]  # per bar
        fitted = np.polyval(coeffs, x)
        residuals = closes - fitted
        std_res = np.std(residuals)
        cur_res = residuals[-1]
        # position in channel: +1 = below mid (bullish context), -1 = above mid (bearish)
        if std_res > 0:
            ch_pos = -cur_res / (std_res * 1.5)  # invert: below channel center = bullish entry
            ch_pos = max(-1.0, min(1.0, ch_pos))
        else:
            ch_pos = 0.0
        # slope direction bonus
        atr_cur = float(row["atr"])
        slope_score = max(-1.0, min(1.0, trend_slope / (atr_cur * 0.1) if atr_cur > 0 else 0.0))
        ch_sc = ch_pos * 0.5 + slope_score * 0.5
    except Exception:
        ch_sc = 0.0

    # Weighted composite
    score = ema_sc * 0.40 + dow_sc * 0.35 + ch_sc * 0.25
    score = max(-1.0, min(1.0, score))

    if   score >  0.45: label = "🟢 強い上昇構造"
    elif score >  0.20: label = "🟡 上昇構造（弱め）"
    elif score < -0.45: label = "🔴 強い下降構造"
    elif score < -0.20: label = "🟡 下降構造（弱め）"
    else:               label = "⚪ 中立構造"

    return {
        "score":  round(score, 3),
        "label":  label,
        "components": {
            "ema_stack":  round(ema_sc, 3),
            "dow_theory": round(dow_sc, 3),
            "channel":    round(ch_sc, 3),
        },
    }


def compute_layer3_score(df: pd.DataFrame, tf: str, sr_levels: list) -> dict:
    """
    Layer 3: 精密エントリー条件
    (オーダーブロック接触 / フィボナッチプルバック / 確認足 / 出来高急増)
    ─────────────────────────────────────────────────────────
    スコア範囲: -1.0 ~ +1.0
    追加ポイントシステム（基本スコアに乗算する加速係数として使用）:
      OB接触:   ±0.3  — 機関OBゾーン内の価格
      フィボ:   ±0.25 — 38.2-61.8%プルバックゾーン
      確認足:   ±0.25 — エンゲルフィング/ピンバー確認
      出来高:   +0.20 — 直近20本中上位20%の出来高
    """
    if len(df) < 30:
        return {"score": 0.0, "label": "データ不足", "components": {}}

    row   = df.iloc[-1]
    close = float(row["Close"])
    high  = float(row["High"])
    low   = float(row["Low"])
    atr   = float(row["atr"])

    score_add = 0.0
    comps = {}

    # ① Order Block proximity (SMC)
    try:
        ob_sc_raw, ob_zones_l3 = detect_order_blocks(df)
        ob_bull = any(z.get("type") == "OB_UP" for z in ob_zones_l3)
        ob_bear = any(z.get("type") == "OB_DN" for z in ob_zones_l3)
        ob_sc = 0.0
        if ob_bull:
            ob_sc += 0.30   # price near bullish OB → potential long
        if ob_bear:
            ob_sc -= 0.30   # price near bearish OB → potential short
        comps["ob_contact"] = round(ob_sc, 3)
        score_add += ob_sc
    except Exception:
        ob_bull = ob_bear = False
        comps["ob_contact"] = 0.0

    # ② Fibonacci pullback zone (38.2-61.8% of last swing)
    try:
        lb = min(100, len(df))
        sub = df.tail(lb)
        swing_high = float(sub["High"].max())
        swing_low  = float(sub["Low"].min())
        sw_range   = swing_high - swing_low
        if sw_range > atr * 2:
            fib382 = swing_high - sw_range * 0.382
            fib618 = swing_high - sw_range * 0.618
            fib50  = swing_high - sw_range * 0.500
            in_bull_fib = fib618 - atr * 0.3 <= close <= fib382 + atr * 0.3
            # For bear: price at 38.2-61.8% from bottom
            fib_bear_382 = swing_low + sw_range * 0.382
            fib_bear_618 = swing_low + sw_range * 0.618
            in_bear_fib  = fib_bear_382 - atr * 0.3 <= close <= fib_bear_618 + atr * 0.3
            fib_sc = 0.0
            if in_bull_fib:  fib_sc += 0.25
            if in_bear_fib:  fib_sc -= 0.25
            comps["fibonacci"] = round(fib_sc, 3)
            score_add += fib_sc
        else:
            comps["fibonacci"] = 0.0
    except Exception:
        comps["fibonacci"] = 0.0

    # ③ Confirmation candle (engulfing / pin bar)
    try:
        candle_sc_raw, _ = detect_candle_patterns(df.tail(5))
        candle_sc = max(-0.25, min(0.25, candle_sc_raw / 4.0 * 0.25))
        comps["candle_confirm"] = round(candle_sc, 3)
        score_add += candle_sc
    except Exception:
        comps["candle_confirm"] = 0.0

    # ④ Volume surge (top 20% of last 20 bars)
    try:
        vol_cur  = float(row.get("Volume", 0))
        vol_ser  = df["Volume"].tail(20).dropna()
        if vol_cur > 0 and len(vol_ser) >= 5:
            vol_pct80 = float(vol_ser.quantile(0.80))
            if vol_cur >= vol_pct80:
                vol_sc = 0.20
            else:
                vol_sc = 0.0
        else:
            vol_sc = 0.0
        comps["volume_surge"] = round(vol_sc, 3)
        score_add += vol_sc
    except Exception:
        comps["volume_surge"] = 0.0

    # S/R proximity bonus (nearest S/R within 0.5×ATR)
    try:
        if sr_levels:
            # sr_levels may be a list of floats or dicts
            def _sr_price(x):
                return x["price"] if isinstance(x, dict) else float(x)
            nearest = min(sr_levels, key=lambda x: abs(_sr_price(x) - close))
            dist = abs(_sr_price(nearest) - close)
            if dist < atr * 0.5:
                sr_type = nearest.get("type", "") if isinstance(nearest, dict) else ""
                sr_sc = 0.15 if sr_type == "support" else -0.15
                comps["sr_proximity"] = round(sr_sc, 3)
                score_add += sr_sc
            else:
                comps["sr_proximity"] = 0.0
        else:
            comps["sr_proximity"] = 0.0
    except Exception:
        comps["sr_proximity"] = 0.0

    score = max(-1.0, min(1.0, score_add))

    if   score >  0.4: label = "🎯 精密エントリー条件揃い"
    elif score >  0.2: label = "✅ エントリー条件一部揃い"
    elif score < -0.4: label = "🎯 ショート精密条件揃い"
    elif score < -0.2: label = "✅ ショート条件一部揃い"
    else:              label = "⚪ エントリー条件不足"

    return {
        "score":      round(score, 3),
        "label":      label,
        "components": comps,
    }


# ═══════════════════════════════════════════════════════
#  Mode: Scalping — 1H足ベーススキャルピング（1m/5m/15m）
# ═══════════════════════════════════════════════════════
def compute_scalp_signal(df: pd.DataFrame, tf: str, sr_levels: list,
                         symbol: str = "USDJPY=X",
                         backtest_mode: bool = False,
                         bar_time=None,
                         htf_cache: dict = None) -> dict:
    """
    スキャルピングモード v2 — 4戦略レジーム選択型。
    学術根拠:
      - BB+RSI Mean Reversion: Bollinger 2001 + Wilder 1978 (レンジ相場用)
      - BB Squeeze Breakout: BLL 1992, JoF (圧縮→拡大用)
      - RSI Divergence at S/R: Osler 2000, FRBNY (S/R反発用)
      - London Breakout: Ito & Hashimoto 2006 (セッション開始用)
    """
    return _compute_scalp_signal_v2(df, tf, sr_levels, symbol, backtest_mode, bar_time, htf_cache)


def _compute_scalp_signal_v2(df: pd.DataFrame, tf: str, sr_levels: list,
                              symbol: str = "USDJPY=X",
                              backtest_mode: bool = False,
                              bar_time=None,
                              htf_cache: dict = None) -> dict:
    """v2 スキャルプ: 4戦略レジーム選択型"""

    # ── Layer 0/1/2/3: 共通前処理 ──
    layer0 = is_trade_prohibited(df, bar_time=bar_time)
    if backtest_mode and htf_cache and "layer1" in htf_cache:
        layer1 = htf_cache["layer1"]
    else:
        layer1 = get_master_bias(symbol)
    regime = detect_market_regime(df)
    layer2 = compute_layer2_score(df, tf)
    layer3 = compute_layer3_score(df, tf, sr_levels)
    if backtest_mode and htf_cache and "htf" in htf_cache:
        htf = htf_cache["htf"]
    else:
        htf = get_htf_bias(symbol)
        if tf == "30m":
            htf = get_htf_bias_daytrade(symbol)

    row = df.iloc[-1]
    entry = float(row["Close"])
    atr = float(row["atr"])
    rsi = float(row["rsi"])
    ema9 = float(row["ema9"])
    ema21 = float(row["ema21"])
    ema50 = float(row["ema50"])
    ema200 = float(row.get("ema200", ema50))  # fallback to ema50
    macdh = float(row["macd_hist"])
    bbpb = float(row["bb_pband"])
    atr7 = float(row["atr7"]) if "atr7" in row.index else atr
    adx = float(row.get("adx", 25.0))
    rsi5 = float(row.get("rsi5", rsi))
    rsi9 = float(row.get("rsi9", rsi))
    stoch_k = float(row.get("stoch_k", 50.0))
    stoch_d = float(row.get("stoch_d", 50.0))
    bb_upper = float(row.get("bb_upper", entry + atr))
    bb_mid = float(row.get("bb_mid", entry))
    bb_lower = float(row.get("bb_lower", entry - atr))
    bb_width = float(row.get("bb_width", 0.01))
    session = get_session_info()
    h1_sc = htf.get("h1", {}).get("score", 0.0)
    h4_sc = htf.get("h4", {}).get("score", 0.0)

    # BB width percentile (50-bar window)
    if "bb_width" in df.columns and len(df) >= 50:
        _bw_series = df["bb_width"].iloc[-50:]
        bb_width_pct = float((_bw_series < bb_width).sum()) / 50.0
    else:
        bb_width_pct = 0.5

    # EMA前バーの値（クロス検出用）
    ema9_prev = float(df["ema9"].iloc[-2]) if len(df) >= 2 else ema9
    ema21_prev = float(df["ema21"].iloc[-2]) if len(df) >= 2 else ema21

    # ── EMA200 分析（方向フィルター + 近接回避 + バウンスボーナス）──
    # 5m 200EMA ≈ 1000分 ≈ 16.7時間 → 日中トレンドの凝縮版
    _ema200_dist = (entry - ema200) / atr if atr > 0 else 0  # ATR正規化距離（正=上、負=下）
    _ema200_slope = (ema200 - float(df["ema200"].iloc[-min(20, len(df)-1)])) if "ema200" in df.columns and len(df) >= 2 else 0
    _ema200_bull = entry > ema200  # 価格がEMA200の上
    _ema200_proximity = abs(_ema200_dist) < 0.3  # ATR×0.3以内 = チョッピーゾーン

    # セッション時間
    if bar_time:
        _bt = bar_time
    elif hasattr(row.name, 'hour'):
        _bt = row.name
    else:
        _bt = datetime.now(timezone.utc)
    if hasattr(_bt, 'tzinfo') and _bt.tzinfo is None:
        _bt = _bt.replace(tzinfo=timezone.utc)
    hour_utc = _bt.hour

    # ──────────────────────────────────────────────────────────
    # WAIT用テンプレート生成関数
    # ──────────────────────────────────────────────────────────
    def _make_result(sig, conf, sl_v, tp_v, rr_v, reasons_list, entry_type, score_v=0.0):
        atr_s = atr7 if atr7 > 0 else atr
        ts_str = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)
        return {
            "timestamp": ts_str, "symbol": "USD/JPY", "tf": tf,
            "entry": round(entry, 3), "signal": sig, "confidence": conf,
            "ml_confidence": get_ml_confidence(df, len(df) - 1, sig),
            "sl": round(sl_v, 3), "tp": round(tp_v, 3), "rr_ratio": rr_v,
            "atr": round(atr_s, 3),
            "session": session, "htf_bias": htf, "swing_mode": False,
            "reasons": reasons_list, "mode": "scalp",
            "entry_type": entry_type,
            "layer_status": {
                "layer0": layer0, "layer1": layer1,
                "master_bias": layer1.get("label", "—"),
                "trade_ok": not layer0["prohibited"],
            },
            "regime": regime, "layer2": layer2, "layer3": layer3,
            "scalp_score": round(score_v, 3),
            "indicators": {
                "ema9": round(ema9, 3), "ema21": round(ema21, 3),
                "ema50": round(ema50, 3), "ema200": round(ema200, 3),
                "rsi": round(rsi, 1),
                "adx": round(adx, 1),
                "macd": round(float(row["macd"]), 5),
                "macd_sig": round(float(row["macd_sig"]), 5),
                "macd_hist": round(macdh, 5),
                "bb_upper": round(bb_upper, 3), "bb_mid": round(bb_mid, 3),
                "bb_lower": round(bb_lower, 3), "bb_pband": round(bbpb, 3),
            },
            "score_detail": {
                "h1_score": round(h1_sc, 3), "h4_score": round(h4_sc, 3),
                "combined": round(score_v, 3), "mtf": 0.0, "rule": 0.0,
            },
            "scalp_info": {
                "htf_label": htf.get("label", "—"),
                "htf_direction": 1 if htf.get("agreement") == "bull" else (-1 if htf.get("agreement") == "bear" else 0),
                "scalp_score": round(score_v, 3),
                "sl_pips": round(abs(entry - sl_v) * 100, 1),
                "tp_pips": round(abs(tp_v - entry) * 100, 1),
                "atr7": round(atr7, 3), "rsi5": round(rsi5, 1),
                "rsi9": round(rsi9, 1), "stoch_k": round(stoch_k, 1),
                "adx": round(adx, 1), "bb_width_pct": round(bb_width_pct * 100, 0),
                "ema200_dist": round(_ema200_dist, 2),
                "ema200_bull": _ema200_bull,
                "ema200_proximity": _ema200_proximity,
            },
        }

    # ── Layer 0 禁止チェック ──
    if layer0["prohibited"]:
        return _make_result("WAIT", 0, entry - atr * 0.5, entry + atr * 0.9, 1.8,
                            [f"🚫 {layer0['reason']}"], "wait")

    # ── HIGH_VOL ミュート ──
    if regime.get("regime") == "HIGH_VOL":
        return _make_result("WAIT", 0, entry - atr * 0.5, entry + atr * 0.9, 1.8,
                            [f"⚠️ 高ボラレジーム（ATR比{regime.get('atr_ratio', 0):.1f}×）"], "wait")

    # ──────────────────────────────────────────────────────────
    #  4戦略レジーム選択型スキャルプ
    #  各戦略は独立してシグナルを出し、最も確信度の高い1つを採用
    # ──────────────────────────────────────────────────────────
    tokyo_mode = layer0.get("tokyo_mode", False)
    _is_friday = _bt.weekday() == 4

    candidates = []  # [(signal, confidence, sl, tp, reasons, entry_type, score)]

    # ════════════════════════════════════════════════════════
    #  戦略1: BB + RSI Mean Reversion（レンジ相場用）
    #  根拠: Bollinger 2001 + Wilder RSI 1978
    #  条件: ADX < 22（レンジ） + BB極端 + RSI極端
    # ════════════════════════════════════════════════════════
    if adx < 35:
        _mr_reasons = []
        _mr_signal = None
        _mr_score = 0.0

        # Tier 1: 極端条件（高確信）BB%B≤0.05 + RSI<25 + Stochクロス
        # Tier 2: 緩和条件（中確信）BB%B≤0.22 + RSI<42 + Stochクロス

        # BUY判定
        if bbpb <= 0.25 and rsi5 < 45 and stoch_k < 45 and stoch_k > stoch_d:
            _mr_signal = "BUY"
            # Tier判定: 極端ほど高スコア
            _tier1 = bbpb <= 0.05 and rsi5 < 25 and stoch_k < 20
            _mr_score = (4.5 if _tier1 else 3.0) + (38 - rsi5) * 0.06
            _mr_reasons.append(f"✅ BB下限(%B={bbpb:.2f}≤0.22) — 平均回帰 (Bollinger 2001)")
            _mr_reasons.append(f"✅ RSI5売られすぎ({rsi5:.1f}<42)")
            _mr_reasons.append(f"✅ Stochゴールデンクロス(K={stoch_k:.0f}>D={stoch_d:.0f})")
            if _tier1:
                _mr_reasons.append("🎯 Tier1: 極端条件（高確信）")
            if macdh > 0:
                _mr_score += 0.5
                _mr_reasons.append("✅ MACDヒストグラム上昇")
            # MACD-H反転ボーナス（モメンタム消耗→回復検出）
            if len(df) >= 3 and "macd_hist" in df.columns:
                _macdh_p1 = float(df.iloc[-2]["macd_hist"])
                _macdh_p2 = float(df.iloc[-3]["macd_hist"])
                if macdh > _macdh_p1 and _macdh_p1 <= _macdh_p2:
                    _mr_score += 0.6
                    _mr_reasons.append("✅ MACD-H反転上昇（モメンタム消耗→回復）")
            # TP = ATRベース（BB midband TPは小さすぎる→ATRで拡大）
            _mr_tp = entry + atr7 * (2.0 if _tier1 else 1.5)
            _mr_sl_dist = max(abs(entry - bb_lower) + atr7 * 0.3, 0.030)
            _mr_sl = entry - _mr_sl_dist

        # SELL判定
        if not _mr_signal and bbpb >= 0.75 and rsi5 > 55 and stoch_k > 55 and stoch_k < stoch_d:
            _mr_signal = "SELL"
            _tier1 = bbpb >= 0.95 and rsi5 > 75 and stoch_k > 80
            _mr_score = (4.5 if _tier1 else 3.0) + (rsi5 - 58) * 0.06
            _mr_reasons.append(f"✅ BB上限(%B={bbpb:.2f}≥0.78) — 平均回帰 (Bollinger 2001)")
            _mr_reasons.append(f"✅ RSI5買われすぎ({rsi5:.1f}>58)")
            _mr_reasons.append(f"✅ Stochデッドクロス(K={stoch_k:.0f}<D={stoch_d:.0f})")
            if _tier1:
                _mr_reasons.append("🎯 Tier1: 極端条件（高確信）")
            if macdh < 0:
                _mr_score += 0.5
                _mr_reasons.append("✅ MACDヒストグラム下落")
            if len(df) >= 3 and "macd_hist" in df.columns:
                _macdh_p1 = float(df.iloc[-2]["macd_hist"])
                _macdh_p2 = float(df.iloc[-3]["macd_hist"])
                if macdh < _macdh_p1 and _macdh_p1 >= _macdh_p2:
                    _mr_score += 0.6
                    _mr_reasons.append("✅ MACD-H反転下落（モメンタム消耗→回復）")
            _mr_tp = entry - atr7 * (2.0 if _tier1 else 1.5)
            _mr_sl_dist = max(abs(bb_upper - entry) + atr7 * 0.3, 0.030)
            _mr_sl = entry + _mr_sl_dist

        if _mr_signal:
            _mr_conf = int(min(85, 50 + _mr_score * 4))
            _mr_reasons.append(f"📊 レジーム: レンジ(ADX={adx:.1f}<35)")
            candidates.append((_mr_signal, _mr_conf, _mr_sl, _mr_tp,
                               _mr_reasons, "bb_rsi_reversion", _mr_score))

    # ════════════════════════════════════════════════════════
    #  戦略2: BB Squeeze Breakout（圧縮→拡大ブレイクアウト）
    #  根拠: BLL 1992 JoF + Keltner Channel filter
    #  条件: BB幅が20thパーセンタイル以下 → 拡大開始時にエントリー
    # ════════════════════════════════════════════════════════
    if bb_width_pct < 0.05 and adx >= 20 and not _is_friday:  # 下位5%のみ + ADXトレンド確認
        _sq_reasons = []
        _sq_signal = None
        _sq_score = 0.0

        # スクイーズ中に方向を判定
        _prev_bbpb = float(df["bb_pband"].iloc[-2]) if len(df) >= 2 else 0.5
        _bb_expanding = bb_width > float(df["bb_width"].iloc[-2]) if len(df) >= 2 else False

        if _bb_expanding:
            # ボリューム確認
            _vol_ok = True
            if "Volume" in df.columns:
                _vol = float(row["Volume"])
                _vol_avg = float(df["Volume"].iloc[-20:].mean()) if len(df) >= 20 else _vol
                _vol_ok = _vol > _vol_avg * 1.2

            if _vol_ok:
                # ブレイクアウト方向判定
                if bbpb > 0.75 and entry > ema9 and ema9 > ema21:
                    _sq_signal = "BUY"
                    _sq_score = 3.5
                    _sq_reasons.append(f"✅ BBスクイーズブレイクアウト上抜け (BLL 1992 JoF)")
                    _sq_reasons.append(f"✅ BB幅{bb_width_pct*100:.0f}%ile → 拡大開始")
                    _sq_reasons.append(f"✅ EMA順列 (9>21) + 価格>EMA9")
                    _sq_tp = entry + atr7 * 3.0  # TP: 拡大方向にATR×3.0
                    _sq_sl = entry - atr7 * 1.2
                elif bbpb < 0.25 and entry < ema9 and ema9 < ema21:
                    _sq_signal = "SELL"
                    _sq_score = 3.5
                    _sq_reasons.append(f"✅ BBスクイーズブレイクアウト下抜け (BLL 1992 JoF)")
                    _sq_reasons.append(f"✅ BB幅{bb_width_pct*100:.0f}%ile → 拡大開始")
                    _sq_reasons.append(f"✅ EMA逆順列 (9<21) + 価格<EMA9")
                    _sq_tp = entry - atr7 * 3.0
                    _sq_sl = entry + atr7 * 1.2

                if _sq_signal:
                    if adx > 20:
                        _sq_score += 1.0
                        _sq_reasons.append(f"✅ ADXトレンド確認({adx:.1f}>20)")
                    _sq_conf = int(min(85, 50 + _sq_score * 4))
                    candidates.append((_sq_signal, _sq_conf, _sq_sl, _sq_tp,
                                       _sq_reasons, "bb_squeeze_breakout", _sq_score))

    # ════════════════════════════════════════════════════════
    #  戦略3: RSI Divergence at S/R（S/R反発+RSIダイバージェンス）
    #  根拠: Osler 2000 FRBNY + Wilder 1978
    #  条件: S/Rレベル近接 + RSIダイバージェンス
    #  NOTE: 1m足では精度不足のため無効化（BT EV -0.605）。DT/Swingでは有効。
    # ════════════════════════════════════════════════════════
    if False:  # DISABLED — EV -0.607 (ATR TP でも改善せず)
        _div_reasons = []
        _div_signal = None
        _div_score = 0.0

        # 価格が S/R に近接しているか（ATR×0.3以内 — 厳格化）
        _near_support = [s for s in sr_levels if isinstance(s, (int, float)) and abs(entry - s) < atr7 * 0.3 and entry >= s]
        _near_resist = [s for s in sr_levels if isinstance(s, (int, float)) and abs(entry - s) < atr7 * 0.3 and entry <= s]

        # RSIダイバージェンス検出（直近10バー）
        _prices = [float(df.iloc[j]["Close"]) for j in range(-10, 0)]
        _rsi5s = [float(df.iloc[j].get("rsi5", 50)) for j in range(-10, 0)]

        # Bullish divergence: 価格が安値更新、RSI5は安値更新せず
        if _near_support and len(_prices) >= 6:
            _p_low1 = min(_prices[:5])
            _p_low2 = min(_prices[5:])
            _r_low1 = min(_rsi5s[:5])
            _r_low2 = min(_rsi5s[5:])
            _rsi_div_strength = _r_low2 - _r_low1  # ダイバージェンス強度
            if (_p_low2 < _p_low1 and _r_low2 > _r_low1
                    and _rsi_div_strength >= 3.0  # RSI差≥3pt必須
                    and rsi5 < 35  # 緩和: 30→35
                    and ema9 < ema21  # EMA逆順列（売られすぎ確認）
                    ):
                _div_signal = "BUY"
                _div_score = 3.5 + min(_rsi_div_strength * 0.1, 1.0)  # 強度ボーナス
                _sr_price = max(_near_support)
                _div_reasons.append(f"✅ RSIブリッシュダイバージェンス — 価格安値更新/RSI非更新(強度{_rsi_div_strength:.1f})")
                _div_reasons.append(f"✅ S/Rサポート近接({_sr_price:.3f}) (Osler 2000 FRBNY)")
                _div_reasons.append(f"✅ RSI5={rsi5:.1f} 売られすぎ圏(<35)")
                # TP: 次のレジスタンスまたはATR×2
                _above_sr = sorted([s for s in sr_levels if isinstance(s, (int, float)) and s > entry + atr7 * 0.3])
                _div_tp = _above_sr[0] - atr7 * 0.05 if _above_sr else entry + atr7 * 2.0
                _div_sl = _sr_price - atr7 * 0.3  # SL厳格化: 0.5→0.3

        # Bearish divergence: 価格が高値更新、RSI5は高値更新せず
        if not _div_signal and _near_resist and len(_prices) >= 6:
            _p_hi1 = max(_prices[:5])
            _p_hi2 = max(_prices[5:])
            _r_hi1 = max(_rsi5s[:5])
            _r_hi2 = max(_rsi5s[5:])
            _rsi_div_strength = _r_hi1 - _r_hi2  # ダイバージェンス強度
            if (_p_hi2 > _p_hi1 and _r_hi2 < _r_hi1
                    and _rsi_div_strength >= 3.0  # RSI差≥3pt必須
                    and rsi5 > 65  # 緩和: 70→65
                    and ema9 > ema21  # EMA順列（買われすぎ確認）
                    ):
                _div_signal = "SELL"
                _div_score = 3.5 + min(_rsi_div_strength * 0.1, 1.0)
                _sr_price = min(_near_resist)
                _div_reasons.append(f"✅ RSIベアリッシュダイバージェンス — 価格高値更新/RSI非更新(強度{_rsi_div_strength:.1f})")
                _div_reasons.append(f"✅ S/Rレジスタンス近接({_sr_price:.3f}) (Osler 2000 FRBNY)")
                _div_reasons.append(f"✅ RSI5={rsi5:.1f} 買われすぎ圏(>65)")
                _below_sr = sorted([s for s in sr_levels if isinstance(s, (int, float)) and s < entry - atr7 * 0.3], reverse=True)
                _div_tp = _below_sr[0] + atr7 * 0.05 if _below_sr else entry - atr7 * 2.0
                _div_sl = _sr_price + atr7 * 0.3  # SL厳格化

        if _div_signal:
            _div_conf = int(min(85, 50 + _div_score * 4))
            candidates.append((_div_signal, _div_conf, _div_sl, _div_tp,
                               _div_reasons, "rsi_divergence_sr", _div_score))

    # ════════════════════════════════════════════════════════
    #  戦略4: London Breakout（セッション開始ブレイクアウト）
    #  根拠: Ito & Hashimoto 2006 — セッション間ボラティリティ遷移
    #  条件: 07:00-09:00 UTC、アジアレンジ突破
    # ════════════════════════════════════════════════════════
    if 7 <= hour_utc <= 9 and len(df) >= 120 and not _is_friday:
        _lb_reasons = []
        _lb_signal = None
        _lb_score = 0.0

        # アジアセッンレンジ（直近120バー = 2時間分の1m足からHigh/Low算出）
        _asia_bars = df.iloc[-120:]
        _asia_high = float(_asia_bars["High"].max())
        _asia_low = float(_asia_bars["Low"].min())
        _asia_range = _asia_high - _asia_low

        if _asia_range > atr7 * 0.5 and _asia_range < atr7 * 4.0:
            # ブレイクアウト検出
            if entry > _asia_high + atr7 * 0.1 and ema9 > ema21:
                _lb_signal = "BUY"
                _lb_score = 4.0
                _lb_reasons.append(f"✅ ロンドンブレイクアウト: アジア高値{_asia_high:.3f}突破 (Ito 2006)")
                _lb_reasons.append(f"✅ EMA順列確認 (9={ema9:.3f}>21={ema21:.3f})")
                _lb_tp = entry + max(_asia_range * 1.5, atr7 * 2.0)
                _lb_sl = _asia_high - atr7 * 0.3  # SL: アジア高値の少し下
            elif entry < _asia_low - atr7 * 0.1 and ema9 < ema21:
                _lb_signal = "SELL"
                _lb_score = 4.0
                _lb_reasons.append(f"✅ ロンドンブレイクアウト: アジア安値{_asia_low:.3f}下抜け (Ito 2006)")
                _lb_reasons.append(f"✅ EMA逆順列確認 (9={ema9:.3f}<21={ema21:.3f})")
                _lb_tp = entry - max(_asia_range * 1.5, atr7 * 2.0)
                _lb_sl = _asia_low + atr7 * 0.3

            if _lb_signal:
                if adx > 18:
                    _lb_score += 0.5
                    _lb_reasons.append(f"✅ ADXモメンタム({adx:.1f}>18)")
                # ボリューム確認
                if "Volume" in df.columns:
                    _vol = float(row["Volume"])
                    _vol_avg = float(df["Volume"].iloc[-60:].mean()) if len(df) >= 60 else _vol
                    if _vol > _vol_avg * 1.3:
                        _lb_score += 0.5
                        _lb_reasons.append("✅ 出来高急増（ロンドン参入）")
                _lb_conf = int(min(85, 50 + _lb_score * 4))
                candidates.append((_lb_signal, _lb_conf, _lb_sl, _lb_tp,
                                   _lb_reasons, "london_breakout", _lb_score))

    # ════════════════════════════════════════════════════════
    #  戦略5: Stochastic Trend Pullback（トレンド方向のStoch押し目/戻り）
    #  根拠: ADX≥25のトレンド相場（全時間の63%）でStochの一時的逆行から回復
    #  条件: 明確なトレンド + EMA整列 + Stochが極値から回復
    # ════════════════════════════════════════════════════════
    # ════════════════════════════════════════════════════════
    #  戦略5: Stochastic Trend Pullback（トレンド方向のStoch押し目/戻り）
    #  根拠: ADX≥25のトレンド相場（全時間の63%）でStochの一時的逆行から回復
    #  条件: 明確なトレンド + EMA整列 + Stochが極値から回復
    # ════════════════════════════════════════════════════════
    if adx >= 20 and not _is_friday and len(df) >= 5:
        _st_reasons = []
        _st_signal = None
        _st_score = 0.0

        _prev_stoch_k = float(df.iloc[-2].get("stoch_k", 50)) if len(df) >= 2 else 50

        # BUY: 上昇トレンド中のStoch売られすぎ回復
        if (ema9 > ema21 and entry > ema21
                and stoch_k > stoch_d  # Stochゴールデンクロス
                and _prev_stoch_k < 35  # 前バーで売られすぎ圏（30→35）
                and stoch_k < 60  # まだ上昇余地あり（55→60）
                and rsi5 > 35 and rsi5 < 55
                and bbpb > 0.20 and bbpb < 0.60
                ):
            _st_signal = "BUY"
            _st_score = 3.2 + min((adx - 20) * 0.04, 0.8)
            _st_reasons.append(f"✅ トレンドプルバック: Stoch売られすぎ回復(K={stoch_k:.0f}, 前={_prev_stoch_k:.0f})")
            _st_reasons.append(f"✅ 上昇トレンド確認 (EMA9>21, ADX={adx:.1f}≥20)")
            _st_reasons.append(f"✅ Stochゴールデンクロス(K>D: {stoch_k:.0f}>{stoch_d:.0f})")
            _st_tp = entry + atr7 * 1.8
            _st_sl = entry - atr7 * 0.8

        # SELL: 下降トレンド中のStoch買われすぎ回復
        elif (ema9 < ema21 and entry < ema21
                and stoch_k < stoch_d
                and _prev_stoch_k > 65  # 70→65
                and stoch_k > 40  # 45→40
                and rsi5 > 45 and rsi5 < 65
                and bbpb > 0.40 and bbpb < 0.80
                ):
            _st_signal = "SELL"
            _st_score = 3.2 + min((adx - 20) * 0.04, 0.8)
            _st_reasons.append(f"✅ トレンドプルバック: Stoch買われすぎ回復(K={stoch_k:.0f}, 前={_prev_stoch_k:.0f})")
            _st_reasons.append(f"✅ 下降トレンド確認 (EMA9<21, ADX={adx:.1f}≥20)")
            _st_reasons.append(f"✅ Stochデッドクロス(K<D: {stoch_k:.0f}<{stoch_d:.0f})")
            _st_tp = entry - atr7 * 1.8
            _st_sl = entry + atr7 * 0.8

        if _st_signal:
            _st_conf = int(min(80, 45 + _st_score * 4))
            _st_reasons.append(f"📊 レジーム: トレンド(ADX={adx:.1f}≥20)")
            candidates.append((_st_signal, _st_conf, _st_sl, _st_tp,
                               _st_reasons, "stoch_trend_pullback", _st_score))

    # ════════════════════════════════════════════════════════
    #  戦略6: MACD Histogram Reversal at BB Extreme
    #  根拠: モメンタム消耗 + 価格極端 = 高確率反転
    #  条件: BB極端 + MACDヒストグラム反転（ゼロクロスor方向転換）
    # ════════════════════════════════════════════════════════
    # ════════════════════════════════════════════════════════
    #  戦略6: MACD Histogram Reversal at BB Extreme
    #  根拠: モメンタム消耗 + 価格極端 = 高確率反転
    #  NOTE: 独立戦略としてBT EV -0.175。bb_rsi_reversionのスコアブーストとして統合済み。
    # ════════════════════════════════════════════════════════
    if len(df) >= 3 and not _is_friday:
        _mh_reasons = []
        _mh_signal = None
        _mh_score = 0.0

        _macdh_prev = float(df.iloc[-2].get("macd_hist", 0)) if "macd_hist" in df.columns else 0
        _macdh_prev2 = float(df.iloc[-3].get("macd_hist", 0)) if len(df) >= 3 and "macd_hist" in df.columns else 0

        # BUY: BB下限 + MACD-H上向き反転
        if (bbpb < 0.25
                and macdh > _macdh_prev
                and _macdh_prev <= _macdh_prev2
                and rsi5 < 42
                ):
            _mh_signal = "BUY"
            _mh_score = 3.5
            _mh_reasons.append(f"✅ MACD-Hモメンタム反転上昇(H={macdh:.4f}, 前={_macdh_prev:.4f})")
            _mh_reasons.append(f"✅ BB下限圏(%B={bbpb:.2f}<0.25)")
            _mh_reasons.append(f"✅ RSI5売られすぎ({rsi5:.1f}<42)")
            if stoch_k > stoch_d:
                _mh_score += 0.5
                _mh_reasons.append(f"✅ Stochゴールデンクロス(K>D)")
            _mh_tp = entry + atr7 * 1.5
            _mh_sl = entry - atr7 * 1.0

        # SELL: BB上限 + MACD-H下向き反転
        elif (bbpb > 0.75
                and macdh < _macdh_prev
                and _macdh_prev >= _macdh_prev2
                and rsi5 > 58
                ):
            _mh_signal = "SELL"
            _mh_score = 3.5
            _mh_reasons.append(f"✅ MACD-Hモメンタム反転下落(H={macdh:.4f}, 前={_macdh_prev:.4f})")
            _mh_reasons.append(f"✅ BB上限圏(%B={bbpb:.2f}>0.75)")
            _mh_reasons.append(f"✅ RSI5買われすぎ({rsi5:.1f}>58)")
            if stoch_k < stoch_d:
                _mh_score += 0.5
                _mh_reasons.append(f"✅ Stochデッドクロス(K<D)")
            _mh_tp = entry - atr7 * 1.5
            _mh_sl = entry + atr7 * 1.0

        if _mh_signal:
            _mh_conf = int(min(80, 45 + _mh_score * 4))
            candidates.append((_mh_signal, _mh_conf, _mh_sl, _mh_tp,
                               _mh_reasons, "macdh_reversal", _mh_score))

    # ════════════════════════════════════════════════════════
    #  戦略7: Engulfing at BB Band（包み足パターン at BB極端）
    #  根拠: 強い反転キャンドルパターン + 価格帯極端 = 構造的反転
    #  条件: BB極端 + 包み足 + RSI確認
    # ════════════════════════════════════════════════════════
    if len(df) >= 2 and not _is_friday:  # RE-ENABLED with ATR-based TP
        _eg_reasons = []
        _eg_signal = None
        _eg_score = 0.0

        _prev_open = float(df.iloc[-2]["Open"]) if len(df) >= 2 else entry
        _prev_close = float(df.iloc[-2]["Close"]) if len(df) >= 2 else entry
        _curr_open = float(row["Open"])
        _curr_close = entry  # = Close
        _prev_body = abs(_prev_close - _prev_open)
        _curr_body = abs(_curr_close - _curr_open)
        _curr_range = float(row["High"]) - float(row["Low"])

        # 包み足条件: 現在足が前足を完全に包む + ボディ1.3倍以上
        _is_bullish_engulf = (_prev_close < _prev_open  # 前足陰線
                              and _curr_close > _curr_open  # 現在足陽線
                              and _curr_body > _prev_body * 1.3  # 1.3倍包み
                              and _curr_close > _prev_open  # 前足始値を超える
                              and _curr_range > atr7 * 0.5)  # 十分な足サイズ

        _is_bearish_engulf = (_prev_close > _prev_open
                              and _curr_close < _curr_open
                              and _curr_body > _prev_body * 1.3
                              and _curr_close < _prev_open
                              and _curr_range > atr7 * 0.5)

        # BUY: BB極端下限 + ブリッシュ包み足
        if (_is_bullish_engulf and bbpb < 0.30 and rsi5 < 45
                ):
            _eg_signal = "BUY"
            _eg_score = 4.0
            _eg_reasons.append(f"✅ ブリッシュ包み足(ボディ比{_curr_body/_prev_body:.1f}x)")
            _eg_reasons.append(f"✅ BB極端下限(%B={bbpb:.2f}<0.30)")
            _eg_reasons.append(f"✅ RSI5売られすぎ({rsi5:.1f}<45)")
            if stoch_k > stoch_d:
                _eg_score += 0.5
                _eg_reasons.append(f"✅ Stochゴールデンクロス確認(K>D)")
            _eg_tp = entry + atr7 * 1.5
            _eg_sl = min(float(row["Low"]), entry - atr7 * 0.8) - atr7 * 0.15

        # SELL: BB極端上限 + ベアリッシュ包み足
        elif (_is_bearish_engulf and bbpb > 0.70 and rsi5 > 55
                ):
            _eg_signal = "SELL"
            _eg_score = 4.0
            _eg_reasons.append(f"✅ ベアリッシュ包み足(ボディ比{_curr_body/_prev_body:.1f}x)")
            _eg_reasons.append(f"✅ BB極端上限(%B={bbpb:.2f}>0.70)")
            _eg_reasons.append(f"✅ RSI5買われすぎ({rsi5:.1f}>55)")
            if stoch_k < stoch_d:
                _eg_score += 0.5
                _eg_reasons.append(f"✅ Stochデッドクロス確認(K<D)")
            _eg_tp = entry - atr7 * 1.5
            _eg_sl = max(float(row["High"]), entry + atr7 * 0.8) + atr7 * 0.15

        if _eg_signal:
            _eg_conf = int(min(82, 48 + _eg_score * 4))
            candidates.append((_eg_signal, _eg_conf, _eg_sl, _eg_tp,
                               _eg_reasons, "engulfing_bb", _eg_score))

    # ════════════════════════════════════════════════════════
    #  戦略8: Three-Bar Reversal（3本足反転パターン）
    #  根拠: 連続陰線/陽線後の反転足 — 構造的転換点
    #  条件: 3本連続方向 + 反転足 + BB中央以遠 + RSI確認
    # ════════════════════════════════════════════════════════
    if len(df) >= 4 and not _is_friday:
        _tb_reasons = []
        _tb_signal = None
        _tb_score = 0.0

        _c3 = float(df.iloc[-4]["Close"]); _o3 = float(df.iloc[-4]["Open"])
        _c2 = float(df.iloc[-3]["Close"]); _o2 = float(df.iloc[-3]["Open"])
        _c1 = float(df.iloc[-2]["Close"]); _o1 = float(df.iloc[-2]["Open"])

        _three_bear = (_c3 < _o3) and (_c2 < _o2) and (_c1 < _o1)  # 3連続陰線
        _three_bull = (_c3 > _o3) and (_c2 > _o2) and (_c1 > _o1)  # 3連続陽線

        # BUY: 3連続陰線の後に陽線（反転） — BB下限圏
        _curr_bull = entry > float(row["Open"])
        if (_three_bear and _curr_bull
                and entry > float(df.iloc[-2]["High"])  # 前足高値超え
                and bbpb < 0.35  # BB下限圏
                and rsi5 < 42
                ):
            _tb_signal = "BUY"
            _tb_score = 3.3
            _tb_reasons.append(f"✅ 3本足反転: 3連続陰線→陽線突破")
            _tb_reasons.append(f"✅ 前足高値{float(df.iloc[-2]['High']):.3f}超え — 反転確認")
            _tb_reasons.append(f"✅ BB下半分(%B={bbpb:.2f}) + RSI={rsi5:.0f}")
            if stoch_k > stoch_d:
                _tb_score += 0.4
                _tb_reasons.append("✅ Stochクロス確認")
            _tb_tp = entry + atr7 * 1.5
            _tb_sl = min(float(df.iloc[-2]["Low"]), float(df.iloc[-3]["Low"])) - atr7 * 0.15

        # SELL: 3連続陽線の後に陰線（反転）
        _curr_bear = entry < float(row["Open"])
        if not _tb_signal and _three_bull and _curr_bear:
            if (entry < float(df.iloc[-2]["Low"])  # 前足安値割れ
                    and bbpb > 0.65  # BB上限圏
                    and rsi5 > 58
                    ):
                _tb_signal = "SELL"
                _tb_score = 3.3
                _tb_reasons.append(f"✅ 3本足反転: 3連続陽線→陰線突破")
                _tb_reasons.append(f"✅ 前足安値{float(df.iloc[-2]['Low']):.3f}割れ — 反転確認")
                _tb_reasons.append(f"✅ BB上半分(%B={bbpb:.2f}) + RSI={rsi5:.0f}")
                if stoch_k < stoch_d:
                    _tb_score += 0.4
                    _tb_reasons.append("✅ Stochデッドクロス確認")
                _tb_tp = entry - atr7 * 1.5
                _tb_sl = max(float(df.iloc[-2]["High"]), float(df.iloc[-3]["High"])) + atr7 * 0.15

        if _tb_signal:
            _tb_conf = int(min(78, 45 + _tb_score * 4))
            candidates.append((_tb_signal, _tb_conf, _tb_sl, _tb_tp,
                               _tb_reasons, "three_bar_reversal", _tb_score))

    # ════════════════════════════════════════════════════════
    #  戦略6: Trend Rebound（強トレンド時の逆張りリバウンド）改良版
    #  根拠: Jegadeesh 1990 — 極端オシレーターからの平均回帰
    #  改良: 本番3/3全敗の原因対策
    #    ① EMA方向チェック追加（上昇中のSELL禁止）
    #    ② 閾値強化 Stoch>95/<5, RSI>78/<22
    #    ③ SL拡大 0.5→1.0 ATR（ウィップソー対策）
    #    ④ 10バーモメンタム逆行チェック
    # ════════════════════════════════════════════════════════
    if adx >= 35:
        _tr_signal = None
        _tr_score = 0.0
        _tr_reasons = []
        _tr_tp = 0
        _tr_sl = 0

        _macdh_prev_tr = float(df.iloc[-2].get("macd_hist", 0)) if len(df) >= 2 else macdh
        _prev_stoch_k_tr = float(df.iloc[-2].get("stoch_k", 50)) if len(df) >= 2 else 50

        # 10バーモメンタム（トレンド継続中は逆張り禁止）
        _tr_momentum = 0
        if len(df) >= 10:
            _tr_momentum = (entry - float(df["Close"].iloc[-10])) * 100  # pip

        # ── 下降トレンド中のBUYリバウンド ──
        # 改良: ema9<ema21(下降確認) + モメンタム上昇してない + 閾値強化
        if (stoch_k < 5
                and rsi5 < 22
                and bbpb < 0.08
                and entry > float(row["Open"])  # 陽線確認
                and ema9 < ema21              # EMA方向: 下降トレンド確認
                and _tr_momentum < 5          # 急上昇中でない
                ):
            _tr_signal = "BUY"
            _tr_score = 3.5
            _tr_reasons.append(f"✅ Trend Rebound BUY: ADX={adx:.0f}≥35 + EMA下降(9<21)")
            _tr_reasons.append(f"✅ 極端値: Stoch={stoch_k:.0f}<5, RSI={rsi5:.0f}<22, BB%B={bbpb:.2f}<0.08")
            _tr_reasons.append(f"✅ 陽線反転 + モメンタム中立({_tr_momentum:+.1f}pip)")

            if macdh > _macdh_prev_tr:
                _tr_score += 0.5
                _tr_reasons.append(f"✅ MACD-H反転上昇")
            if stoch_k > stoch_d:
                _tr_score += 0.5
                _tr_reasons.append(f"✅ Stoch GC")
            if stoch_k > _prev_stoch_k_tr:
                _tr_score += 0.3

            _tr_tp = entry + atr7 * (1.5 if _tr_score >= 4.0 else 1.0)
            _tr_sl = entry - atr7 * 1.0  # SL拡大: 0.5→1.0 ATR

        # ── 上昇トレンド中のSELLリバウンド ──
        # 改良: ema9>ema21(上昇確認) + モメンタム下降してない + 閾値強化
        elif (stoch_k > 95
                and rsi5 > 78
                and bbpb > 0.92
                and entry < float(row["Open"])  # 陰線確認
                and ema9 > ema21              # EMA方向: 上昇トレンド確認
                and _tr_momentum > -5         # 急下降中でない
                ):
            _tr_signal = "SELL"
            _tr_score = 3.5
            _tr_reasons.append(f"✅ Trend Rebound SELL: ADX={adx:.0f}≥35 + EMA上昇(9>21)")
            _tr_reasons.append(f"✅ 極端値: Stoch={stoch_k:.0f}>95, RSI={rsi5:.0f}>78, BB%B={bbpb:.2f}>0.92")
            _tr_reasons.append(f"✅ 陰線反転 + モメンタム中立({_tr_momentum:+.1f}pip)")

            if macdh < _macdh_prev_tr:
                _tr_score += 0.5
                _tr_reasons.append(f"✅ MACD-H反転下落")
            if stoch_k < stoch_d:
                _tr_score += 0.5
                _tr_reasons.append(f"✅ Stoch DC")
            if stoch_k < _prev_stoch_k_tr:
                _tr_score += 0.3

            _tr_tp = entry - atr7 * (1.5 if _tr_score >= 4.0 else 1.0)
            _tr_sl = entry + atr7 * 1.0  # SL拡大: 0.5→1.0 ATR

        if _tr_signal:
            _tr_conf = int(min(80, 45 + _tr_score * 4))
            candidates.append((_tr_signal, _tr_conf, _tr_sl, _tr_tp,
                               _tr_reasons, "trend_rebound", _tr_score))

    # ════════════════════════════════════════════════════════
    #  戦略7: [DISABLED for scalp] 水平線タッチ + 三尊/逆三尊
    #  1m足ではノイズが多すぎ: 三尊 WR=10%, SR touch WR=52% EV=-0.4
    #  → 15m DT足専用として compute_daytrade_signal に実装済み
    #  → スキャルプでは既存のbb_rsi_reversionがSR反発を自然にカバー
    # ════════════════════════════════════════════════════════
    if False and len(df) >= 50:
        _hs_signal = None
        _hs_score = 0.0
        _hs_reasons = []
        _hs_tp = 0
        _hs_sl = 0
        _hs_entry_type = None

        # Stoch前バー（ベロシティ比較用）
        _prev_stoch_hs = float(df.iloc[-2].get("stoch_k", 50)) if len(df) >= 2 else 50

        # ── 水平線タッチ + 反発（SR Bounce Enhanced）──
        # 既存のsr_bounceより厳格: 2回以上反発実績 + 陽/陰線確認 + RSI整合
        if sr_levels:
            for _sr in sr_levels:
                _sr_price = float(_sr["price"]) if isinstance(_sr, dict) else float(_sr)
                _sr_touches = _sr.get("touches", 2) if isinstance(_sr, dict) else 2
                _sr_strength = _sr.get("strength", 0.5) if isinstance(_sr, dict) else 0.5
                _sr_type = _sr.get("type", "both") if isinstance(_sr, dict) else "both"

                _sr_dist = abs(entry - _sr_price) * 100  # pip
                if _sr_dist > atr7 * 100 * 0.4:  # ATRの40%以内
                    continue
                if _sr_touches < 2:
                    continue

                # Support touch → BUY
                if entry > _sr_price and _sr_dist < atr7 * 100 * 0.3:
                    if (_sr_type in ("support", "both")
                            and entry > float(row["Open"])  # 陽線確認
                            and rsi > 35 and rsi < 60       # 売られすぎではないがまだ余地
                            and stoch_k > _prev_stoch_hs    # Stoch回復中
                            ):
                        _hs_signal = "BUY"
                        _hs_score = 3.5
                        _hs_entry_type = "sr_touch_bounce"
                        _hs_reasons.append(f"✅ 水平線サポートタッチ: {_sr_price:.3f}(距離{_sr_dist:.1f}pip) [Osler 2000]")
                        _hs_reasons.append(f"✅ タッチ{_sr_touches}回, 強度={_sr_strength:.2f}")
                        _hs_reasons.append(f"✅ 陽線反発確認 + RSI={rsi:.0f}")
                        if _sr_strength >= 0.6:
                            _hs_score += 0.5
                            _hs_reasons.append(f"✅ 強いSR(strength≥0.6)")
                        if ema9 > ema21:
                            _hs_score += 0.5
                            _hs_reasons.append(f"✅ EMA上昇順列")
                        # TP: 次のresistanceまたはATR×1.5
                        _above_sr = sorted([float(s["price"]) if isinstance(s, dict) else float(s)
                                           for s in sr_levels
                                           if (float(s["price"]) if isinstance(s, dict) else float(s)) > entry + atr7 * 0.3])
                        _hs_tp = (_above_sr[0] - 0.003) if _above_sr else entry + atr7 * 1.5
                        _hs_sl = _sr_price - atr7 * 0.5
                        break

                # Resistance touch → SELL
                elif entry < _sr_price and _sr_dist < atr7 * 100 * 0.3:
                    if (_sr_type in ("resistance", "both")
                            and entry < float(row["Open"])  # 陰線確認
                            and rsi > 40 and rsi < 65
                            and stoch_k < _prev_stoch_hs    # Stoch反落中
                            ):
                        _hs_signal = "SELL"
                        _hs_score = 3.5
                        _hs_entry_type = "sr_touch_bounce"
                        _hs_reasons.append(f"✅ 水平線レジスタンスタッチ: {_sr_price:.3f}(距離{_sr_dist:.1f}pip) [Osler 2000]")
                        _hs_reasons.append(f"✅ タッチ{_sr_touches}回, 強度={_sr_strength:.2f}")
                        _hs_reasons.append(f"✅ 陰線反発確認 + RSI={rsi:.0f}")
                        if _sr_strength >= 0.6:
                            _hs_score += 0.5
                            _hs_reasons.append(f"✅ 強いSR(strength≥0.6)")
                        if ema9 < ema21:
                            _hs_score += 0.5
                            _hs_reasons.append(f"✅ EMA下降順列")
                        _below_sr = sorted([float(s["price"]) if isinstance(s, dict) else float(s)
                                           for s in sr_levels
                                           if (float(s["price"]) if isinstance(s, dict) else float(s)) < entry - atr7 * 0.3],
                                          reverse=True)
                        _hs_tp = (_below_sr[0] + 0.003) if _below_sr else entry - atr7 * 1.5
                        _hs_sl = _sr_price + atr7 * 0.5
                        break

        if _hs_signal and _hs_entry_type:
            _hs_conf = int(min(85, 50 + _hs_score * 5))
            candidates.append((_hs_signal, _hs_conf, _hs_sl, _hs_tp,
                               _hs_reasons, _hs_entry_type, _hs_score))

    # ════════════════════════════════════════════════════════
    #  戦略8: V字リバウンドキャプチャ（急落/急騰後の反転検出）
    #  根拠: Cont (2001) "Empirical properties of asset returns"
    #        — 極端な価格変動後の平均回帰、FX市場のV字反転パターン
    #        Jegadeesh & Titman (1993) — 短期反転効果
    #  条件: 直近N本で大幅下落/上昇 + RSIダイバージェンス + 3指標極端 + 足形確認
    #  ADX不問（trend_reboundと差別化: あちらはADX≥35限定の逆張り）
    #  TP: ATR×2.0（V字は大きく反発する）, SL: ATR×0.7（確認後エントリー）
    # ════════════════════════════════════════════════════════
    if len(df) >= 20:
        _vr_signal = None
        _vr_score = 0.0
        _vr_reasons = []
        _vr_tp = 0
        _vr_sl = 0

        # 直近10本の価格変動（pip）
        _vr_lookback = min(10, len(df) - 1)
        _vr_price_10 = float(df["Close"].iloc[-_vr_lookback - 1])
        _vr_drop = (_vr_price_10 - entry) * 100   # 正=下落幅(pip)
        _vr_surge = (entry - _vr_price_10) * 100   # 正=上昇幅(pip)

        # RSIダイバージェンス検出（直近5本）
        _vr_rsi_vals = [float(df.iloc[-j].get("rsi", 50)) for j in range(1, min(6, len(df)))]
        _vr_price_vals = [float(df["Close"].iloc[-j]) for j in range(1, min(6, len(df)))]
        _vr_rsi_min_idx = _vr_rsi_vals.index(min(_vr_rsi_vals)) if _vr_rsi_vals else 0
        _vr_rsi_max_idx = _vr_rsi_vals.index(max(_vr_rsi_vals)) if _vr_rsi_vals else 0
        _vr_price_min_idx = _vr_price_vals.index(min(_vr_price_vals)) if _vr_price_vals else 0
        _vr_price_max_idx = _vr_price_vals.index(max(_vr_price_vals)) if _vr_price_vals else 0

        # ── V字底: 急落後のBUYリバウンド ──
        # 強化条件: 8pip以上の急落 + RSI<25 + BB%B<0.10 + Stoch<15 + 陽線 + Stoch回復必須
        _prev_stoch_vr = float(df.iloc[-2].get("stoch_k", 50)) if len(df) >= 2 else 50
        _prev_bbpb_vr = float(df.iloc[-2].get("bb_pband", 0.5)) if len(df) >= 2 else 0.5
        _vr_macdh_prev = float(df.iloc[-2].get("macd_hist", 0)) if len(df) >= 2 else macdh

        # 陽線/陰線のボディ比率（実体の大きさ / ヒゲ含む全長）
        _vr_high = float(row["High"])
        _vr_low = float(row["Low"])
        _vr_bar_range = _vr_high - _vr_low if _vr_high > _vr_low else 0.001
        _vr_body_ratio = abs(entry - float(row["Open"])) / _vr_bar_range

        if (_vr_drop >= 8.0                          # 直近10本で8pip以上下落（浅い動き排除）
                and rsi < 25                          # RSI14 極端売られすぎ
                and bbpb < 0.10                       # BB下限圏（より厳格）
                and stoch_k < 15                      # Stoch極端売られすぎ
                and entry > float(row["Open"])        # 陽線確認（反転兆候）
                and _vr_body_ratio >= 0.25            # 実体ある陽線（十字線排除）
                and stoch_k > _prev_stoch_vr          # Stoch回復確認（必須）
                ):
            _vr_signal = "BUY"
            _vr_score = 3.5
            _vr_reasons.append(f"✅ V字底検出: 直近{_vr_lookback}本で-{_vr_drop:.1f}pip急落 [Cont 2001]")
            _vr_reasons.append(f"✅ 3指標極端: RSI={rsi:.0f}<25, BB%B={bbpb:.2f}<0.10, Stoch={stoch_k:.0f}<15")
            _vr_reasons.append(f"✅ 陽線+Stoch回復確認(前={_prev_stoch_vr:.0f}→{stoch_k:.0f})")

            # RSI Bullish Divergence: 価格新安値 vs RSI底上げ（高確信ボーナス）
            if (_vr_price_min_idx < _vr_rsi_min_idx and len(_vr_rsi_vals) >= 3
                    and _vr_rsi_vals[0] > min(_vr_rsi_vals)):
                _vr_score += 1.5
                _vr_reasons.append(f"✅ RSI Bullish Divergence: 価格新安値 vs RSI底上げ [Jegadeesh 1993]")

            # BB%B回復（前バーより上昇）
            if bbpb > _prev_bbpb_vr:
                _vr_score += 0.5
                _vr_reasons.append(f"✅ BB%B回復({_prev_bbpb_vr:.2f}→{bbpb:.2f})")

            # MACD-Hの反転
            if macdh > _vr_macdh_prev:
                _vr_score += 0.5
                _vr_reasons.append(f"✅ MACD-H反転上昇")

            # TP: ATR×1.5（確実に取る）
            _vr_tp = entry + atr7 * 1.5
            # SL: 直近安値 or ATR×0.7
            _recent_low = float(df["Low"].iloc[-3:].min())
            _vr_sl = min(entry - atr7 * 0.7, _recent_low - 0.002)

        # ── V字天井: 急騰後のSELLリバウンド ──
        elif (_vr_surge >= 8.0                        # 直近10本で8pip以上上昇
                and rsi > 75                          # RSI14 極端買われすぎ
                and bbpb > 0.90                       # BB上限圏（より厳格）
                and stoch_k > 85                      # Stoch極端買われすぎ
                and entry < float(row["Open"])        # 陰線確認（反転兆候）
                and _vr_body_ratio >= 0.25            # 実体ある陰線（十字線排除）
                and stoch_k < _prev_stoch_vr          # Stoch反落確認（必須）
                ):
            _vr_signal = "SELL"
            _vr_score = 3.5
            _vr_reasons.append(f"✅ V字天井検出: 直近{_vr_lookback}本で+{_vr_surge:.1f}pip急騰 [Cont 2001]")
            _vr_reasons.append(f"✅ 3指標極端: RSI={rsi:.0f}>75, BB%B={bbpb:.2f}>0.90, Stoch={stoch_k:.0f}>85")
            _vr_reasons.append(f"✅ 陰線+Stoch反落確認(前={_prev_stoch_vr:.0f}→{stoch_k:.0f})")

            # RSI Bearish Divergence
            if (_vr_price_max_idx < _vr_rsi_max_idx and len(_vr_rsi_vals) >= 3
                    and _vr_rsi_vals[0] < max(_vr_rsi_vals)):
                _vr_score += 1.5
                _vr_reasons.append(f"✅ RSI Bearish Divergence: 価格新高値 vs RSI天井下げ")

            if bbpb < _prev_bbpb_vr:
                _vr_score += 0.5
                _vr_reasons.append(f"✅ BB%B反落({_prev_bbpb_vr:.2f}→{bbpb:.2f})")

            if macdh < _vr_macdh_prev:
                _vr_score += 0.5
                _vr_reasons.append(f"✅ MACD-H反転下落")

            _vr_tp = entry - atr7 * 1.5
            _recent_high = float(df["High"].iloc[-3:].max())
            _vr_sl = max(entry + atr7 * 0.7, _recent_high + 0.002)

        if _vr_signal:
            _vr_conf = int(min(85, 50 + _vr_score * 5))
            candidates.append((_vr_signal, _vr_conf, _vr_sl, _vr_tp,
                               _vr_reasons, "v_reversal", _vr_score))

    # ════════════════════════════════════════════════════════
    #  戦略11: SR/Channel Bounce Reversal（水平線・並行チャネル反発）
    #  根拠: Osler 2000 (NY Fed), Support/Resistance as price memory
    #  条件: 価格がSRレベルまたはチャネル境界に到達 + RSI/Stochで反転確認
    # ════════════════════════════════════════════════════════
    if sr_levels and len(df) >= 10 and not _is_friday:
        _src_signal = None
        _src_score = 0.0
        _src_reasons = []

        # 並行チャネル検出
        _channel = find_parallel_channel(df, window=5, lookback=min(100, len(df) - 1))
        _ch_upper = float(_channel["upper"][-1]["value"]) if _channel else None
        _ch_lower = float(_channel["lower"][-1]["value"]) if _channel else None

        # SR近接判定（ATR×0.3以内）
        _sr_proximity_buy = [l for l in sr_levels if 0 < entry - l < atr * 0.3]
        _sr_proximity_sell = [l for l in sr_levels if 0 < l - entry < atr * 0.3]

        # チャネル下限近接 (BUY候補)
        _at_ch_lower = _ch_lower and abs(entry - _ch_lower) < atr * 0.3
        # チャネル上限近接 (SELL候補)
        _at_ch_upper = _ch_upper and abs(entry - _ch_upper) < atr * 0.3

        # BUY: SRサポート or チャネル下限 + RSI反転 + Stoch反転
        if (_sr_proximity_buy or _at_ch_lower) and rsi5 < 45 and stoch_k > stoch_d:
            _src_score = 3.0
            _src_signal = "BUY"

            if _sr_proximity_buy:
                _nearest_sr = max(_sr_proximity_buy)
                _touch_dist = abs(entry - _nearest_sr) / atr
                _src_score += max(0, (0.3 - _touch_dist) * 3.0)  # 近いほどボーナス
                _src_reasons.append(f"✅ SRサポート反発({_nearest_sr:.3f}, dist={_touch_dist:.2f}ATR)")
            if _at_ch_lower:
                _src_score += 0.8
                _src_reasons.append(f"✅ チャネル下限反発({_ch_lower:.3f})")
            if rsi5 < 35:
                _src_score += 0.5
                _src_reasons.append(f"✅ RSI5過売({rsi5:.0f})")
            if stoch_k < 30 and stoch_k > stoch_d:
                _src_score += 0.5
                _src_reasons.append(f"✅ Stoch反転上昇({stoch_k:.0f}>{stoch_d:.0f})")
            if macdh > 0 or (len(df) >= 3 and macdh > float(df["macd_hist"].iloc[-2])):
                _src_score += 0.4
                _src_reasons.append("✅ MACD-H反転上昇")
            # 陽線確認
            if entry > float(row["Open"]):
                _src_score += 0.3

            _src_tp = entry + atr7 * 1.5
            _nearest_sup = max(_sr_proximity_buy) if _sr_proximity_buy else (_ch_lower if _ch_lower else entry - atr7 * 0.5)
            _src_sl = min(entry - atr7 * 0.5, _nearest_sup - atr7 * 0.15)

        # SELL: SRレジスタンス or チャネル上限 + RSI反転 + Stoch反転
        elif (_sr_proximity_sell or _at_ch_upper) and rsi5 > 55 and stoch_k < stoch_d:
            _src_score = 3.0
            _src_signal = "SELL"

            if _sr_proximity_sell:
                _nearest_sr = min(_sr_proximity_sell)
                _touch_dist = abs(_nearest_sr - entry) / atr
                _src_score += max(0, (0.3 - _touch_dist) * 3.0)
                _src_reasons.append(f"✅ SRレジスタンス反発({_nearest_sr:.3f}, dist={_touch_dist:.2f}ATR)")
            if _at_ch_upper:
                _src_score += 0.8
                _src_reasons.append(f"✅ チャネル上限反発({_ch_upper:.3f})")
            if rsi5 > 65:
                _src_score += 0.5
                _src_reasons.append(f"✅ RSI5過買({rsi5:.0f})")
            if stoch_k > 70 and stoch_k < stoch_d:
                _src_score += 0.5
                _src_reasons.append(f"✅ Stoch反転下降({stoch_k:.0f}<{stoch_d:.0f})")
            if macdh < 0 or (len(df) >= 3 and macdh < float(df["macd_hist"].iloc[-2])):
                _src_score += 0.4
                _src_reasons.append("✅ MACD-H反転下降")
            if entry < float(row["Open"]):
                _src_score += 0.3

            _src_tp = entry - atr7 * 1.5
            _nearest_res = min(_sr_proximity_sell) if _sr_proximity_sell else (_ch_upper if _ch_upper else entry + atr7 * 0.5)
            _src_sl = max(entry + atr7 * 0.5, _nearest_res + atr7 * 0.15)

        if _src_signal and _src_score >= 3.0:
            _src_conf = int(min(85, 45 + _src_score * 5))
            candidates.append((_src_signal, _src_conf, _src_sl, _src_tp,
                               _src_reasons, "sr_channel_reversal", _src_score))

    # ════════════════════════════════════════════════════════
    #  戦略12: Fibonacci Reversal（フィボナッチリトレースメント反発）
    #  根拠: Fibonacci 38.2%/50%/61.8%はリバーサルの高確率ゾーン
    #  条件: フィボレベル近接 + RSI/Stoch反転 + ローソク足確認
    # ════════════════════════════════════════════════════════
    if len(df) >= 60 and not _is_friday:
        _fib = _calc_fibonacci_levels(df, lookback=60)
        if _fib and _fib.get("trend"):
            _fib_signal = None
            _fib_score = 0.0
            _fib_reasons = []
            _fib_trend = _fib["trend"]
            _fib_levels = {
                "38.2%": _fib.get("r382", 0),
                "50.0%": _fib.get("r500", 0),
                "61.8%": _fib.get("r618", 0),
            }

            # 各フィボレベルとの近接チェック
            _fib_touch = None
            for _fib_name, _fib_val in _fib_levels.items():
                if _fib_val and abs(entry - _fib_val) < atr * 0.25:
                    _fib_touch = (_fib_name, _fib_val)
                    break

            if _fib_touch:
                _fn, _fv = _fib_touch
                _fib_dist = abs(entry - _fv) / atr

                # 上昇トレンドの押し目買い: フィボサポート付近でBUY
                if _fib_trend == "up" and rsi5 < 45 and stoch_k > stoch_d:
                    _fib_signal = "BUY"
                    _fib_score = 3.5
                    _fib_reasons.append(f"✅ Fib {_fn}サポート({_fv:.3f}, dist={_fib_dist:.2f}ATR)")
                    if _fn == "61.8%":
                        _fib_score += 0.8  # 最高確率ゾーン
                        _fib_reasons.append("✅ Fib61.8%: 最高確率リバーサルゾーン")
                    elif _fn == "50.0%":
                        _fib_score += 0.5
                    if rsi5 < 35:
                        _fib_score += 0.5
                    if entry > float(row["Open"]):
                        _fib_score += 0.3
                        _fib_reasons.append("✅ 陽線確認")
                    if macdh > float(df["macd_hist"].iloc[-2]) if len(df) >= 3 else False:
                        _fib_score += 0.4
                        _fib_reasons.append("✅ MACD-H反転上昇")

                    _fib_tp = entry + atr7 * 1.8
                    _fib_sl = min(entry - atr7 * 0.5, _fv - atr7 * 0.2)

                # 下降トレンドの戻り売り: フィボレジスタンス付近でSELL
                elif _fib_trend == "down" and rsi5 > 55 and stoch_k < stoch_d:
                    _fib_signal = "SELL"
                    _fib_score = 3.5
                    _fib_reasons.append(f"✅ Fib {_fn}レジスタンス({_fv:.3f}, dist={_fib_dist:.2f}ATR)")
                    if _fn == "61.8%":
                        _fib_score += 0.8
                        _fib_reasons.append("✅ Fib61.8%: 最高確率リバーサルゾーン")
                    elif _fn == "50.0%":
                        _fib_score += 0.5
                    if rsi5 > 65:
                        _fib_score += 0.5
                    if entry < float(row["Open"]):
                        _fib_score += 0.3
                        _fib_reasons.append("✅ 陰線確認")
                    if macdh < float(df["macd_hist"].iloc[-2]) if len(df) >= 3 else False:
                        _fib_score += 0.4
                        _fib_reasons.append("✅ MACD-H反転下降")

                    _fib_tp = entry - atr7 * 1.8
                    _fib_sl = max(entry + atr7 * 0.5, _fv + atr7 * 0.2)

            if _fib_signal and _fib_score >= 3.5:
                _fib_conf = int(min(85, 45 + _fib_score * 5))
                candidates.append((_fib_signal, _fib_conf, _fib_sl, _fib_tp,
                                   _fib_reasons, "fib_reversal", _fib_score))

    # ════════════════════════════════════════════════════════
    #  戦略13: MTF Reversal Confluence（複数時間軸RSI+MACDクロス一致）
    #  根拠: 1m + 5m(1H/4Hキャッシュ) のRSI/MACDが同時に反転
    #  条件: HTF RSI過売/過買 + 1m RSI反転 + MACD-Hクロス一致
    # ════════════════════════════════════════════════════════
    if not _is_friday:
        _mtfr_signal = None
        _mtfr_score = 0.0
        _mtfr_reasons = []

        # HTFからRSI/MACDを取得
        _htf_h1 = htf.get("h1", {})
        _htf_h4 = htf.get("h4", {})
        _htf_h1_rsi = _htf_h1.get("rsi", 50)
        _htf_h4_rsi = _htf_h4.get("rsi", 50)
        _htf_h1_macd_cross = _htf_h1.get("macd_cross", 0)  # 1=bull cross, -1=bear cross
        _htf_h1_score = _htf_h1.get("score", 0)

        # BUY: 複数時間軸でoversold + MACD反転
        _mtf_buy_rsi = (rsi5 < 40 and _htf_h1_rsi < 45) or (rsi5 < 35 and _htf_h4_rsi < 50)
        _mtf_buy_macd = macdh > 0 or (len(df) >= 3 and macdh > float(df["macd_hist"].iloc[-2]))
        _mtf_buy_stoch = stoch_k > stoch_d and stoch_k < 40

        if _mtf_buy_rsi and _mtf_buy_macd and _mtf_buy_stoch:
            _mtfr_signal = "BUY"
            _mtfr_score = 3.2

            # RSI一致ボーナス
            if rsi5 < 35 and _htf_h1_rsi < 40:
                _mtfr_score += 0.8
                _mtfr_reasons.append(f"✅ MTF RSI一致 (1m={rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            else:
                _mtfr_score += 0.4
                _mtfr_reasons.append(f"✅ MTF RSI oversold (1m={rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")

            # 4H RSIも一致
            if _htf_h4_rsi < 45:
                _mtfr_score += 0.5
                _mtfr_reasons.append(f"✅ 4H RSI一致({_htf_h4_rsi:.0f})")

            # HTF MACDクロス一致
            if _htf_h1_score > 0:
                _mtfr_score += 0.5
                _mtfr_reasons.append("✅ 1H MACDブルクロス一致")

            _mtfr_reasons.append(f"✅ MACD-H反転({macdh:.5f})")
            _mtfr_reasons.append(f"✅ Stoch反転({stoch_k:.0f}>{stoch_d:.0f})")

            _mtfr_tp = entry + atr7 * 1.5
            _mtfr_sl = entry - atr7 * 0.5

        # SELL: 複数時間軸でoverbought + MACD反転
        _mtf_sell_rsi = (rsi5 > 60 and _htf_h1_rsi > 55) or (rsi5 > 65 and _htf_h4_rsi > 50)
        _mtf_sell_macd = macdh < 0 or (len(df) >= 3 and macdh < float(df["macd_hist"].iloc[-2]))
        _mtf_sell_stoch = stoch_k < stoch_d and stoch_k > 60

        if not _mtfr_signal and _mtf_sell_rsi and _mtf_sell_macd and _mtf_sell_stoch:
            _mtfr_signal = "SELL"
            _mtfr_score = 3.2

            if rsi5 > 65 and _htf_h1_rsi > 60:
                _mtfr_score += 0.8
                _mtfr_reasons.append(f"✅ MTF RSI一致 (1m={rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")
            else:
                _mtfr_score += 0.4
                _mtfr_reasons.append(f"✅ MTF RSI overbought (1m={rsi5:.0f}, 1H={_htf_h1_rsi:.0f})")

            if _htf_h4_rsi > 55:
                _mtfr_score += 0.5
                _mtfr_reasons.append(f"✅ 4H RSI一致({_htf_h4_rsi:.0f})")

            if _htf_h1_score < 0:
                _mtfr_score += 0.5
                _mtfr_reasons.append("✅ 1H MACDベアクロス一致")

            _mtfr_reasons.append(f"✅ MACD-H反転({macdh:.5f})")
            _mtfr_reasons.append(f"✅ Stoch反転({stoch_k:.0f}<{stoch_d:.0f})")

            _mtfr_tp = entry - atr7 * 1.5
            _mtfr_sl = entry + atr7 * 0.5

        if _mtfr_signal and _mtfr_score >= 3.2:
            _mtfr_conf = int(min(80, 40 + _mtfr_score * 5))
            candidates.append((_mtfr_signal, _mtfr_conf, _mtfr_sl, _mtfr_tp,
                               _mtfr_reasons, "mtf_reversal_confluence", _mtfr_score))

    # ──────────────────────────────────────────────────────────
    #  最良候補の選択: スコア最大の戦略を採用
    # ──────────────────────────────────────────────────────────
    if not candidates:
        return _make_result("WAIT", 15, entry - atr * 0.5, entry + atr * 0.9, 1.8,
                            ["⛔ 全戦略の条件未達 → WAIT"], "wait")

    # スコア降順で最良を選択
    best = max(candidates, key=lambda c: c[6])
    signal, conf, sl, tp, reasons, entry_type, score = best

    # ── EMA200 近接回避ゾーン ──
    # 200EMA付近は攻防ラインでウィップソーが多い → エントリー抑制
    # ただしtrend_rebound/v_reversalは極端な状況なので除外
    if _ema200_proximity and entry_type not in ("trend_rebound", "v_reversal"):
        score *= 0.5
        conf = int(conf * 0.6)
        reasons.append(f"⚠️ EMA200近接ゾーン(距離{_ema200_dist:.2f}ATR) — チョッピー回避")

    # ── EMA200 方向フィルター ──
    # 200EMA上+スロープ上昇のSELL / 200EMA下+スロープ下降のBUY → ハードブロック
    # 本番: EMA200逆行のmacdh_reversal|SELL全敗、fib_reversal|BUY WR=33%
    # trend_reboundは逆張り戦略なので除外
    if entry_type not in ("trend_rebound", "v_reversal"):
        if _ema200_bull and signal == "SELL" and _ema200_slope > 0:
            # EMA200上 + 上昇中 → SELL完全ブロック
            reasons.append(f"🚫 EMA200上昇中のSELL(dist={_ema200_dist:+.2f}ATR) → ブロック")
            return {"signal": "WAIT", "confidence": 0, "reasons": reasons,
                    "entry_type": entry_type, "sl": sl, "tp": tp, "atr": atr7,
                    "indicators": {"rsi": rsi5, "bbpb": bbpb, "adx": adx}}
        elif not _ema200_bull and signal == "BUY" and _ema200_slope < 0:
            # EMA200下 + 下降中 → BUY完全ブロック
            reasons.append(f"🚫 EMA200下降中のBUY(dist={_ema200_dist:+.2f}ATR) → ブロック")
            return {"signal": "WAIT", "confidence": 0, "reasons": reasons,
                    "entry_type": entry_type, "sl": sl, "tp": tp, "atr": atr7,
                    "indicators": {"rsi": rsi5, "bbpb": bbpb, "adx": adx}}
        elif _ema200_bull and signal == "SELL":
            # EMA200上だがスロープ横ばい → ソフトペナルティ維持
            score *= 0.80
            conf = int(conf * 0.85)
            reasons.append(f"⚠️ EMA200上からSELL(dist={_ema200_dist:+.2f}ATR) — 軽度減衰")
        elif not _ema200_bull and signal == "BUY":
            score *= 0.80
            conf = int(conf * 0.85)
            reasons.append(f"⚠️ EMA200下からBUY(dist={_ema200_dist:+.2f}ATR) — 軽度減衰")

    # ── EMA200 バウンスボーナス ──
    # EMA200に近接してからの反転 → 高確信ボーナス
    if abs(_ema200_dist) < 0.5 and abs(_ema200_dist) >= 0.1:  # 近いが近接ゾーン外
        if _ema200_bull and signal == "BUY" and _ema200_slope >= 0:
            # 200EMA上で、サポートとして跳ね返り → ボーナス
            score += 0.8
            reasons.append(f"✅ EMA200サポートバウンス(dist={_ema200_dist:.2f}ATR)")
        elif not _ema200_bull and signal == "SELL" and _ema200_slope <= 0:
            # 200EMA下で、レジスタンスとして跳ね返り → ボーナス
            score += 0.8
            reasons.append(f"✅ EMA200レジスタンスバウンス(dist={_ema200_dist:.2f}ATR)")

    # ── HTF方向フィルター: 逆行シグナルを完全ブロック（DT同様ハードフィルター）──
    # 本番実績: macdh_reversal|SELL WR=0%(5t -15.4p) — ソフト減衰では阻止不能
    htf_dir = htf.get("agreement", "neutral")
    if htf_dir == "bull" and signal == "SELL":
        signal = "WAIT"
        reasons.append("🚫 HTF上昇一致 → SELL完全ブロック")
        return {"signal": "WAIT", "confidence": 0, "reasons": reasons,
                "entry_type": entry_type, "sl": sl, "tp": tp, "atr": atr7,
                "indicators": {"rsi": rsi5, "bbpb": bbpb, "adx": adx}}
    elif htf_dir == "bear" and signal == "BUY":
        signal = "WAIT"
        reasons.append("🚫 HTF下降一致 → BUY完全ブロック")
        return {"signal": "WAIT", "confidence": 0, "reasons": reasons,
                "entry_type": entry_type, "sl": sl, "tp": tp, "atr": atr7,
                "indicators": {"rsi": rsi5, "bbpb": bbpb, "adx": adx}}

    # ── SL/TP最終調整: 最低距離保証 + RR保証 ──
    sl_dist = abs(entry - sl)
    tp_dist = abs(tp - entry)
    MIN_SL = 0.030  # 3 pip最低
    if sl_dist < MIN_SL:
        sl = entry - MIN_SL if signal == "BUY" else entry + MIN_SL
        sl_dist = MIN_SL
    # RR最低1.5保証
    if tp_dist < sl_dist * 1.2:
        tp = entry + sl_dist * 1.8 if signal == "BUY" else entry - sl_dist * 1.8
        tp_dist = abs(tp - entry)
        reasons.append("⚠️ RR不足 → TP最小RR1.8に拡張")

    rr = round(tp_dist / max(sl_dist, 1e-6), 2)
    return _make_result(signal, conf, sl, tp, rr, reasons, entry_type, score)


def _compute_scalp_signal_v1_legacy(df: pd.DataFrame, tf: str, sr_levels: list,
                         symbol: str = "USDJPY=X",
                         backtest_mode: bool = False,
                         bar_time=None,
                         htf_cache: dict = None) -> dict:
    """
    [LEGACY] スキャルピングモード v1（旧ロジック・参考保持用）
    学術根拠:
      - ADX>20フィルター: レンジ相場での誤シグナル排除 (Wilder 1978)
      - RSI(9): 5m足での最適バランス (Axiory研究: RSI5は過ノイズ/RSI14は遅すぎ)
      - セッション精緻化: London前場07-09UTC + 重複13-17UTC (Krohn et al. 2024 JoF)
      - 出来高急増確認: Sharpe+37-78% (IJSAT 2025)
      - BBバンド幅スクイーズ回避: ブレイクアウト待ち優先
      - 1H+4H トレンドをハードフィルターとして使用
    SL=ATR7×0.8 / TP=S/Rスナップ or ATR7×1.3
    """
    # ── Layer 0: 取引禁止チェック ──────────────────────────────
    layer0 = is_trade_prohibited(df, bar_time=bar_time)

    # ── Layer 1: 大口バイアス（マスターフィルター）──────────────
    if backtest_mode and htf_cache and "layer1" in htf_cache:
        layer1 = htf_cache["layer1"]
    else:
        layer1 = get_master_bias(symbol)

    # ── Layer 2/3 + レジーム判定 ──────────────────────────────
    regime = detect_market_regime(df)
    layer2 = compute_layer2_score(df, tf)
    layer3 = compute_layer3_score(df, tf, sr_levels)

    if backtest_mode and htf_cache and "htf" in htf_cache:
        htf = htf_cache["htf"]
    else:
        htf     = get_htf_bias(symbol)
        # 30m足は4H+1Dを参照（MTF_HIGHERと整合）
        if tf == "30m":
            htf = get_htf_bias_daytrade(symbol)
    row     = df.iloc[-1]
    entry   = float(row["Close"])
    atr     = float(row["atr"])
    rsi     = float(row["rsi"])
    ema9    = float(row["ema9"])
    ema21   = float(row["ema21"])
    ema50   = float(row["ema50"])
    macdh   = float(row["macd_hist"])
    bbpb    = float(row["bb_pband"])
    atr7    = float(row["atr7"]) if "atr7" in row.index else atr
    adx     = float(row.get("adx", 25.0))
    rsi5    = float(row.get("rsi5", rsi))
    rsi9    = float(row.get("rsi9", rsi))     # 5m最適 (Axiory研究)
    stoch_k = float(row.get("stoch_k", 50.0))
    stoch_d = float(row.get("stoch_d", 50.0))
    bb_width = float(row.get("bb_width", 0.01))
    session = get_session_info()

    h1_sc = htf.get("h1", {}).get("score", 0.0)
    h4_sc = htf.get("h4", {}).get("score", 0.0)

    # ── Layer 0 早期リターン（取引禁止時）─────────────────────
    if layer0["prohibited"]:
        atr_scalp = float(df["atr7"].iloc[-1]) if "atr7" in df.columns else atr
        session   = get_session_info()
        ts_str    = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)
        return {
            "timestamp": ts_str, "symbol": "USD/JPY", "tf": tf,
            "entry": round(entry, 3), "signal": "WAIT", "confidence": 0,
            "sl": round(entry - atr * 0.5, 3), "tp": round(entry + atr * 0.9, 3),
            "rr_ratio": 1.8, "atr": round(atr, 3),
            "session": session, "htf_bias": htf, "swing_mode": False,
            "reasons": [f"🚫 {layer0['reason']}"],
            "mode": "scalp", "scalp_score": 0.0,
            "layer_status": {"layer0": layer0, "layer1": layer1,
                             "master_bias": layer1.get("label","—"), "trade_ok": False},
            "indicators": {
                "ema9": round(ema9,3), "ema21": round(ema21,3), "ema50": round(ema50,3),
                "rsi": round(rsi,1), "macd": 0.0, "macd_sig": 0.0, "macd_hist": 0.0,
                "bb_upper": 0.0, "bb_mid": 0.0, "bb_lower": 0.0, "bb_pband": round(bbpb,3),
            },
            "scalp_info": {"htf_label": layer0["reason"], "htf_direction": 0,
                          "scalp_score": 0.0, "sl_pips": 0, "tp_pips": 0,
                          "atr7": round(atr,3), "rsi5": round(rsi5,1),
                          "rsi9": round(rsi,1), "stoch_k": round(stoch_k,1),
                          "adx": round(adx,1), "bb_width_pct": 0},
            "ml_confidence": 0.5,
        }

    # ── HIGH_VOL レジームミュート ─────────────────────────
    if regime.get("regime") == "HIGH_VOL":
        atr_scalp = float(df["atr7"].iloc[-1]) if "atr7" in df.columns else atr
        ts_str = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)
        return {
            "timestamp": ts_str, "symbol": "USD/JPY", "tf": tf,
            "entry": round(entry, 3), "signal": "WAIT", "confidence": 0,
            "sl": round(entry - atr * 0.5, 3), "tp": round(entry + atr * 0.9, 3),
            "rr_ratio": 1.8, "atr": round(atr, 3),
            "session": session, "htf_bias": htf, "swing_mode": False,
            "reasons": [f"⚠️ 高ボラレジーム（ATR比{regime.get('atr_ratio',0):.1f}×） — シグナルミュート"],
            "mode": "scalp", "scalp_score": 0.0,
            "regime": regime,
            "layer_status": {"layer0": layer0, "layer1": layer1,
                             "master_bias": layer1.get("label","—"), "trade_ok": False},
            "indicators": {
                "ema9": round(ema9,3), "ema21": round(ema21,3), "ema50": round(ema50,3),
                "rsi": round(rsi,1), "macd": 0.0, "macd_sig": 0.0, "macd_hist": 0.0,
                "bb_upper": 0.0, "bb_mid": 0.0, "bb_lower": 0.0, "bb_pband": round(bbpb,3),
            },
            "scalp_info": {"htf_label": "HIGH_VOL", "htf_direction": 0,
                          "scalp_score": 0.0, "sl_pips": 0, "tp_pips": 0,
                          "atr7": round(atr_scalp,3), "rsi5": round(rsi5,1),
                          "rsi9": round(rsi,1), "stoch_k": round(stoch_k,1),
                          "adx": round(adx,1), "bb_width_pct": 0},
            "ml_confidence": 0.5,
        }

    # ── 東京セッション: BBバウンス平均回帰戦略 ──────────────
    tokyo_mode = layer0.get("tokyo_mode", False)
    if tokyo_mode:
        # BB %B (price position within Bollinger Bands)
        bb_pband = float(row.get("bb_pband", 0.5)) if "bb_pband" in row.index else 0.5
        rsi_tok = float(row["rsi"])
        adx_tok = float(row.get("adx", 20.0))
        atr7_tok = float(row["atr7"]) if "atr7" in row.index else float(row["atr"])

        # Only trade in ranging market (ADX < 25)
        if adx_tok < 25:
            signal = "WAIT"
            score_tok = 0.0

            # 金曜日はtokyo_bbを完全ブロック（週末リスクで平均回帰が機能しない）
            _tok_bar_dt = bar_time if bar_time else datetime.now(timezone.utc)
            _tok_is_friday = False
            try:
                _tok_is_friday = _tok_bar_dt.weekday() == 4
            except Exception:
                pass
            if _tok_is_friday:
                # 金曜東京セッションはWAITを返す
                pass
            # BB Lower bounce + RSI oversold → BUY
            elif bb_pband <= 0.08 and rsi_tok < 38:
                signal = "BUY"
                score_tok = 2.5 + (38 - rsi_tok) * 0.05  # stronger RSI extreme = higher score
            # BB Upper bounce + RSI overbought → SELL
            elif bb_pband >= 0.92 and rsi_tok > 62:
                signal = "SELL"
                score_tok = 2.5 + (rsi_tok - 62) * 0.05

            if signal != "WAIT":
                entry_tok = float(row["Close"])
                spread = 0.002
                entry_tok = entry_tok + spread / 2 if signal == "BUY" else entry_tok - spread / 2

                # 本番分析: tokyo_bbのSLスリッページが最悪(+8.4p超過)
                # SL拡大: 0.6→1.2×ATR + 最低3pipsバッファ（低流動性対策）
                sl_mult = 1.2
                sl_raw = atr7_tok * sl_mult
                sl_raw = max(sl_raw, 0.03)  # 最低3pips
                sl_tok = entry_tok - sl_raw if signal == "BUY" else entry_tok + sl_raw

                # TP: BB middle band (mean reversion target)
                bb_mid = float(row.get("bb_middle", (row.get("bb_upper", entry_tok) + row.get("bb_lower", entry_tok)) / 2))
                if "bb_middle" not in row.index and "bb_upper" in row.index:
                    bb_mid = (float(row["bb_upper"]) + float(row["bb_lower"])) / 2
                tp_tok = bb_mid

                # Ensure minimum RR of 1.0
                sl_dist = abs(entry_tok - sl_tok)
                tp_dist = abs(tp_tok - entry_tok)
                if tp_dist < sl_dist:
                    tp_tok = entry_tok + sl_dist * 1.2 if signal == "BUY" else entry_tok - sl_dist * 1.2

                rr = round(abs(tp_tok - entry_tok) / max(abs(entry_tok - sl_tok), 1e-6), 2)
                confidence = min(int(score_tok * 15), 95)

                session_tok = get_session_info()
                ts_str = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)

                return {
                    "signal": signal, "confidence": confidence,
                    "entry": round(entry_tok, 3), "sl": round(sl_tok, 3), "tp": round(tp_tok, 3),
                    "atr": round(atr7_tok, 4), "rr_ratio": rr, "score": round(score_tok, 2),
                    "session": session_tok, "timestamp": ts_str,
                    "mode": "scalp", "tf": tf, "symbol": symbol,
                    "swing_mode": False, "bar_count": len(df),
                    "ohlcv_source": df.attrs.get("source", "unknown"),
                    "scalp_score": round(score_tok, 2),
                    "entry_type": "tokyo_bb",
                    "scalp_info": {
                        "strategy": "tokyo_bb_bounce",
                        "bb_pband": round(bb_pband, 3),
                        "rsi": round(rsi_tok, 1),
                        "adx": round(adx_tok, 1),
                        "note": "🏯 東京セッション: BBバウンス平均回帰",
                    },
                    "reasons": [
                        f"🏯 東京セッション平均回帰戦略",
                        f"BB %B: {bb_pband:.3f} ({'下限バウンス' if signal == 'BUY' else '上限バウンス'})",
                        f"RSI: {rsi_tok:.1f} ({'売られすぎ' if signal == 'BUY' else '買われすぎ'})",
                        f"ADX: {adx_tok:.1f} (レンジ相場確認)",
                        f"TP: BBミドルバンド {bb_mid:.3f}",
                    ],
                    "indicators": {
                        "ema9": float(row["ema9"]), "ema21": float(row["ema21"]),
                        "ema50": float(row["ema50"]),
                        "rsi": round(rsi_tok, 1),
                        "macd": float(row.get("macd", 0)),
                        "macd_signal": float(row.get("macd_signal", 0)),
                        "macd_hist": float(row.get("macd_hist", 0)),
                        "bb_upper": float(row.get("bb_upper", 0)),
                        "bb_lower": float(row.get("bb_lower", 0)),
                        "adx": round(adx_tok, 1),
                        "atr": round(atr7_tok, 4),
                    },
                    "htf_bias": htf,
                    "layer_status": {
                        "layer0": layer0, "layer1": layer1,
                        "master_bias": layer1.get("label", "—"),
                        "trade_ok": True,
                    },
                    "ml_confidence": 0.5,
                }
            # If no BB bounce signal, fall through to standard logic with tokyo info

    # ── 学術根拠S/R計算 ─────────────────────────────────────
    round_sr   = detect_round_number_sr(entry)          # Osler (2000)
    vpoc       = get_volume_poc(df, lookback=200)        # Gärtner & Kübler (2016)
    reg_ch     = get_regression_channel(df, lookback=50) # Lo et al. (2000)
    # ドンチアンチャネル指標
    don_high   = float(row.get("don_high20", entry + atr))
    don_low    = float(row.get("don_low20",  entry - atr))
    don_mid    = float(row.get("don_mid20",  entry))
    don_pct    = float(row.get("don_pct",    0.5))       # 0=下限, 1=上限
    # ラウンドナンバーをS/Rレベルに追加（重複除去）
    enhanced_sr = sorted(set(sr_levels + round_sr))

    score   = 0.0
    reasons = []

    # ① ADXレジームフィルター (Wilder 1978) ─────────────────
    # 1m足ではADX<20が頻出するため、ペナルティを緩和
    if adx >= 25:
        adx_mult = 1.1
        reasons.append(f"✅ ADX{adx:.0f}>25: 強トレンド — スキャル最適環境")
    elif adx >= 18:
        adx_mult = 0.90
        reasons.append(f"⚠️ ADX{adx:.0f}: 中程度トレンド")
    elif adx >= 12:
        adx_mult = 0.70
        reasons.append(f"⚠️ ADX{adx:.0f}<18: 弱トレンド（Wilder 1978）")
    else:
        adx_mult = 0.45
        reasons.append(f"⛔ ADX{adx:.0f}<12: 超レンジ相場 → スキャル非推奨")

    # ② BBバンド幅スクイーズ検出 ─────────────────────────────
    # スクイーズ = BBが狭い → ブレイクアウト待機、スキャル回避
    bb_width_series = df.get("bb_width", df["bb_upper"] - df["bb_lower"])
    bb_width_pct = float(pd.Series(df["bb_width"].values if "bb_width" in df.columns
                                   else (df["bb_upper"] - df["bb_lower"]).values
                                   ).rolling(50).rank(pct=True).iloc[-1]) if len(df) > 50 else 0.5
    if bb_width_pct < 0.2:
        adx_mult *= 0.6
        reasons.append(f"⛔ BBスクイーズ中(幅{bb_width_pct:.0%}パーセンタイル): ブレイク前 → エントリー回避")
    elif bb_width_pct > 0.7:
        reasons.append(f"✅ BB拡張中({bb_width_pct:.0%}): ボラティリティ良好")

    # ③ 1H+4H フィルター ─────────────────────────────
    # 本番分析: ADX<20(レンジ)でHTFハードフィルター→SELL偏重13連敗
    # → レンジ時はHTFをソフトバイアスに変更（反転トレードも許容）
    is_range = adx < 20
    htf_mixed = False
    if htf["agreement"] == "bull":
        if is_range:
            d_mult = 1.0
            reasons.append("📈 1H+4H 強気 (レンジ: BUY優先だが反転も許容)")
        else:
            d_mult = 1.0;  reasons.append("📈 1H+4H 強気 → BUYのみ有効")
    elif htf["agreement"] == "bear":
        if is_range:
            # レンジ時: HTF方向をバイアスとして使うが、1m足のEMA配列も考慮
            if ema9 > ema21:
                d_mult = 1.0  # 1m足が上昇中 → BUY許容
                reasons.append("⚖️ 1H+4H弱気だが ADX<20レンジ + 1m足上昇 → BUY方向（逆張り許容）")
            else:
                d_mult = -1.0
                reasons.append("📉 1H+4H 弱気 + 1m足下降 → SELL方向")
        else:
            d_mult = -1.0; reasons.append("📉 1H+4H 弱気(トレンド) → SELLのみ有効")
    else:
        htf_mixed = True
        # 1m足自身のEMA配列で方向判定（スキャルプは短期TFの流れに従う）
        if ema9 > ema21 > ema50:
            d_mult = 1.0
            reasons.append("⚖️ 1H+4H不一致 → 1m足EMA上昇配列でBUY方向（品質低下）")
        elif ema9 < ema21 < ema50:
            d_mult = -1.0
            reasons.append("⚖️ 1H+4H不一致 → 1m足EMA下降配列でSELL方向（品質低下）")
        elif ema9 > ema21:
            d_mult = 1.0
            reasons.append("⚖️ 1H+4H不一致 → 1m足EMA9>EMA21でBUY方向（品質低下）")
        elif ema9 < ema21:
            d_mult = -1.0
            reasons.append("⚖️ 1H+4H不一致 → 1m足EMA9<EMA21でSELL方向（品質低下）")
        else:
            d_mult = 0.0
            reasons.append("⚖️ 1H+4H不一致 + 1m足EMA不明瞭 → 方向判定不可")

    # ④ EMA9 プルバック ──────────────────────────────────────
    # 改善: EMA間スプレッドが狭い(レンジ)時はスコア減衰
    atr_ref = atr7 if atr7 > 0 else atr
    _ema_spread = abs(ema9 - ema21) / max(atr_ref, 1e-6)
    _ema_pb_mult = 1.0 if _ema_spread > 0.3 else (0.4 if _ema_spread > 0.15 else 0.15)
    if d_mult == 1.0:
        if ema9 > ema21 > ema50:
            if entry <= ema9 * 1.001:
                score += 2.0 * _ema_pb_mult; reasons.append(f"✅ EMA9プルバック({ema9:.3f}) BUYゾーン")
            elif entry <= ema9 * 1.003:
                score += 0.8 * _ema_pb_mult; reasons.append("↗ EMA9>EMA21>EMA50 上昇列")
            else:
                score += 0.3; reasons.append("↗ EMA上昇配列（プルバック待ち）")
        elif ema9 > ema21:
            score += 0.4; reasons.append("↗ EMA9>EMA21")
    elif d_mult == -1.0:
        if ema9 < ema21 < ema50:
            if entry >= ema9 * 0.999:
                score -= 2.0 * _ema_pb_mult; reasons.append(f"✅ EMA9プルバック({ema9:.3f}) SELLゾーン")
            elif entry >= ema9 * 0.997:
                score -= 0.8 * _ema_pb_mult; reasons.append("↘ EMA9<EMA21<EMA50 下降列")
            else:
                score -= 0.3; reasons.append("↘ EMA下降配列（戻り待ち）")
        elif ema9 < ema21:
            score -= 0.4; reasons.append("↘ EMA9<EMA21")
    else:
        reasons.append("⚖️ EMA方向不明瞭 → スキップ")

    # ⑤ RSI(5)リセット + RSI(9)モメンタム確認 (Axiory研究) ─────
    # RSI5: 過売り/過買いリセット検出（感度重視）
    # RSI9: エントリー方向のモメンタム確認（バランス重視）
    if d_mult == 1.0:
        if rsi5 < 25:
            score += 1.8; reasons.append(f"✅ RSI5極度売られ過ぎ({rsi5:.0f}): 強BUYシグナル")
        elif rsi5 < 45:
            score += 1.2; reasons.append(f"✅ RSI5({rsi5:.0f}) リセット完了")
        elif rsi5 < 55:
            score += 0.5; reasons.append(f"↗ RSI5({rsi5:.0f}) 中立圏")
        # RSI9モメンタム確認（Axiory: 5mの最適バランス設定）
        if rsi9 < 50 and rsi9 > 30:
            score += 0.6; reasons.append(f"✅ RSI9({rsi9:.0f})<50: モメンタム回復中（Axiory 5m最適）")
        if rsi < 40:
            score += 0.4  # RSI14補助
    elif d_mult == -1.0:
        if rsi5 > 75:
            score -= 1.8; reasons.append(f"✅ RSI5極度買われ過ぎ({rsi5:.0f}): 強SELLシグナル")
        elif rsi5 > 55:
            score -= 1.2; reasons.append(f"✅ RSI5({rsi5:.0f}) リセット完了")
        elif rsi5 > 45:
            score -= 0.5; reasons.append(f"↘ RSI5({rsi5:.0f}) 中立圏")
        # RSI9モメンタム確認
        if rsi9 > 50 and rsi9 < 70:
            score -= 0.6; reasons.append(f"🔻 RSI9({rsi9:.0f})>50: 下落モメンタム確認")
        if rsi > 60:
            score -= 0.4

    # ⑥ MACD ────────────────────────────────────────────────
    if d_mult == 1.0 and macdh > 0:   score += 0.6; reasons.append("✅ MACDヒスト正")
    elif d_mult == 1.0 and macdh < 0:  score -= 0.3
    elif d_mult == -1.0 and macdh < 0: score -= 0.6; reasons.append("✅ MACDヒスト負")
    elif d_mult == -1.0 and macdh > 0: score += 0.3

    # ⑦ ボリンジャーバンド ─────────────────────────────────────
    if d_mult == 1.0 and bbpb < 0.25:
        score += 0.6; reasons.append(f"✅ BB下限付近({bbpb:.2f}) スキャルBUYゾーン")
    elif d_mult == -1.0 and bbpb > 0.75:
        score -= 0.6; reasons.append(f"✅ BB上限付近({bbpb:.2f}) スキャルSELLゾーン")

    # ⑧ Stochastic(5,3,3) ────────────────────────────────────
    if d_mult == 1.0:
        if stoch_k < 20 and stoch_k > stoch_d:
            score += 1.0; reasons.append(f"✅ Stoch GC({stoch_k:.0f}) 売られ過ぎ圏")
        elif stoch_k < 40 and stoch_k > stoch_d:
            score += 0.5; reasons.append(f"↗ Stoch({stoch_k:.0f}) 上向き")
    elif d_mult == -1.0:
        if stoch_k > 80 and stoch_k < stoch_d:
            score -= 1.0; reasons.append(f"✅ Stoch DC({stoch_k:.0f}) 買われ過ぎ圏")
        elif stoch_k > 60 and stoch_k < stoch_d:
            score -= 0.5; reasons.append(f"↘ Stoch({stoch_k:.0f}) 下向き")

    # ⑨ 出来高急増確認 (IJSAT 2025: Sharpe+37-78%) ─────────────
    if "Volume" in df.columns:
        vol_now = float(df["Volume"].iloc[-1])
        vol_avg = float(df["Volume"].tail(20).mean())
        if vol_avg > 0 and vol_now > vol_avg * 1.5:
            score += 0.7 if d_mult == 1.0 else -0.7
            reasons.append(f"✅ 出来高{vol_now/vol_avg:.1f}x急増: 機関参入シグナル(IJSAT 2025)")
        elif vol_avg > 0 and vol_now < vol_avg * 0.4:
            score *= 0.8
            reasons.append(f"⚠️ 出来高低水準({vol_now/vol_avg:.1f}x): エントリー品質低下")

    # ⑩ ADXマルチプライヤー + 方向フィルター ───────────────────
    score *= adx_mult
    if d_mult == 0.0:
        score *= 0.30       # 方向判定不可 → 大幅減衰
    elif htf_mixed:
        score *= 0.70       # HTF不一致だが1m足で方向あり → 軽度減衰
    # else: abs(d_mult)==1.0 → 減衰なし

    # ⑪ セッション精緻化 (Krohn et al. 2024 JoF) ────────────────
    # London前場07-09UTC: 東京/ロンドン重複、方向性ブレイクアウト
    # London/NY重複13-17UTC: 最高流動性、最高品質シグナル
    try:
        h = df.index[-1].hour
        if 13 <= h < 17:
            score *= 1.15
            reasons.append(f"🟢 London/NY重複({h}UTC): 最高流動性・最高品質(Krohn 2024)")
        elif 7 <= h < 9:
            score *= 1.08
            reasons.append(f"🟡 London前場({h}UTC): 方向性ブレイクアウト期待(Krohn 2024)")
        elif 9 <= h < 13 or 17 <= h < 21:
            pass  # 通常セッション
        elif 21 <= h or h < 1:
            score *= 0.60
            reasons.append(f"⚠️ Post-NY/Pre-Tokyo({h}UTC): 閑散時間帯 — 軽度減衰")
        else:  # 1-7 UTC
            score *= 0.75
            reasons.append(f"⚠️ 東京時間({h}UTC): USD/JPYは取引可能")
    except Exception:
        pass

    # ⑪b 金曜フィルター: 週末前ポジション解消で方向性が不安定
    _is_friday_scalp = False
    try:
        _bar_dt = bar_time if bar_time else datetime.now(timezone.utc)
        _dow = _bar_dt.weekday() if hasattr(_bar_dt, 'weekday') else df.index[-1].weekday()
        if _dow == 4:  # 金曜日
            _is_friday_scalp = True
            reasons.append("⚠️ 金曜日: 閾値引き上げ（高確信シグナルのみ許可）")
    except Exception:
        pass

    # ⑧ 回帰チャネル偏差スコア (Lo, Mamaysky, Wang 2000 JoF) ────────
    if reg_ch and reg_ch.get("upper") and reg_ch.get("lower"):
        rch_score = reg_ch["score"]
        rch_slope = reg_ch.get("slope", 0.0)
        if d_mult == -1.0:  # SELL方向
            if rch_score > 0.6:
                score -= 1.2
                reasons.append(f"✅ 回帰チャネル上限近接({reg_ch['upper']:.3f}): SELL圧力 (Lo 2000 JoF)")
            elif rch_score > 0.3:
                score -= 0.5
                reasons.append(f"↘ 回帰チャネル上半部 ({rch_score:.2f})")
        elif d_mult == 1.0:  # BUY方向
            if rch_score < -0.6:
                score += 1.2
                reasons.append(f"✅ 回帰チャネル下限近接({reg_ch['lower']:.3f}): BUY圧力 (Lo 2000 JoF)")
            elif rch_score < -0.3:
                score += 0.5
                reasons.append(f"↗ 回帰チャネル下半部 ({rch_score:.2f})")
        # チャネルスロープ: トレンド方向の確認
        if rch_slope < -0.001 and d_mult == -1.0:
            score -= 0.4; reasons.append(f"↘ 下降チャネル確認(slope:{rch_slope:.4f})")
        elif rch_slope > 0.001 and d_mult == 1.0:
            score += 0.4; reasons.append(f"↗ 上昇チャネル確認(slope:{rch_slope:.4f})")

    # ⑨ VPOC (Volume Point of Control) — 機関投資家レベル ──────────
    if vpoc:
        dist_to_vpoc = abs(entry - vpoc)
        atr_ref = atr7 if atr7 > 0 else atr
        if dist_to_vpoc < atr_ref * 0.5:
            reasons.append(f"⚠️ VPOC({vpoc:.3f})近接: 機関投資家S/Rゾーン — TP到達前に反発注意")
        elif dist_to_vpoc < atr_ref * 2.0:
            reasons.append(f"📊 VPOC: {vpoc:.3f} ({dist_to_vpoc/atr_ref:.1f}×ATR先)")

    # ⑩ ラウンドナンバー近接チェック (Osler 2000 FRBNY) ──────────
    near_round = [l for l in round_sr if abs(l - entry) < atr * 0.3]
    if near_round:
        reasons.append(f"🔵 ラウンドナンバー({near_round[0]:.2f})近接: 指値集中ゾーン(Osler 2000)")

    # ⑪ ドンチアンチャネル位置 (Brock, Lakonishok, LeBaron 1992 JoF) ─
    # SELLバイアス: don_pct>0.7(上限近接)が最高品質
    # BUYバイアス : don_pct<0.3(下限近接)が最高品質
    if d_mult == -1.0:  # SELL方向
        if don_pct > 0.75:
            score -= 1.3
            reasons.append(f"✅ ドンチアン上限圏({don_pct:.0%}): 最高品質SELLゾーン(BLL 1992 JoF)")
        elif don_pct > 0.55:
            score -= 0.6
            reasons.append(f"↘ ドンチアン上半部({don_pct:.0%}): SELL有利")
        elif don_pct < 0.25:
            score += 0.8   # 逆方向ペナルティ
            reasons.append(f"⚠️ ドンチアン下限圏({don_pct:.0%}): SELL逆方向 → 抑制")
    elif d_mult == 1.0:  # BUY方向
        if don_pct < 0.25:
            score += 1.3
            reasons.append(f"✅ ドンチアン下限圏({don_pct:.0%}): 最高品質BUYゾーン(BLL 1992 JoF)")
        elif don_pct < 0.45:
            score += 0.6
            reasons.append(f"↗ ドンチアン下半部({don_pct:.0%}): BUY有利")
        elif don_pct > 0.75:
            score -= 0.8
            reasons.append(f"⚠️ ドンチアン上限圏({don_pct:.0%}): BUY逆方向 → 抑制")

    # ⑫ オプション満期時刻フィルター (Anderegg et al. 2022 ETH/SNB) ─
    # 10:00 NY cut (≈14:30-15:30 UTC), 3:00 Tokyo cut (≈17:30-18:30 UTC)
    # ガンマヘッジが最大化 → 価格磁石効果が強まり予測困難
    try:
        _opt_time = bar_time if bar_time else datetime.now(timezone.utc)
        _now_h = _opt_time.hour
        _now_m = _opt_time.minute if hasattr(_opt_time, 'minute') else 0
        _min   = _now_h * 60 + _now_m
        _ny_cut    = (14*60+30 <= _min <= 15*60+30)   # NY 10:00 AM EDT
        _tk_cut    = (17*60+30 <= _min <= 18*60+30)   # Tokyo 3:00 AM JST
        if _ny_cut:
            score *= 0.80
            reasons.append("⚠️ NY オプション満期前後(10AM EDT±30分): ガンマヘッジ増大 → サイズ縮小推奨 (Anderegg 2022)")
        elif _tk_cut:
            score *= 0.85
            reasons.append("⚠️ Tokyo オプション満期前後(3AM JST±30分): ガンマ注意 (Anderegg 2022)")
    except Exception:
        pass

    # TF警告
    if tf not in ("1m", "5m", "15m"):
        reasons.append(f"⚠️ {tf}足 — スキャルは1m/5m/15m推奨")

    # ── Layer 1: 大口バイアス適用 ─────────────────────────────
    bias_dir = layer1["direction"]
    if bias_dir == "bull":
        if score < 0:   score *= 0.50   # 大口買い優位時のSELL → 中程度減衰（旧0.15は1m足で厳しすぎた）
        else:           score *= 1.15   # 大口買い方向一致 → 若干強化
    elif bias_dir == "bear":
        if score > 0:   score *= 0.50   # 大口売り優位時のBUY → 中程度減衰（旧0.15は1m足で厳しすぎた）
        else:           score *= 1.15   # 大口売り方向一致 → 若干強化
    else:
        score *= 0.80   # 大口方向不明 → 軽度品質低下（旧0.60は厳しすぎた）

    # ── Layer 2: トレンド構造整合性ブースト ─────────────────────
    l2_sc = layer2["score"]
    if (score > 0 and l2_sc > 0) or (score < 0 and l2_sc < 0):
        score += l2_sc * 0.25   # up to +0.25 boost when aligned
    elif (score > 0 and l2_sc < 0) or (score < 0 and l2_sc > 0):
        score *= 0.70           # 30% reduction when conflicting

    # ── Layer 3: 精密エントリーボーナス ─────────────────────────
    l3_sc = layer3["score"]
    score += l3_sc * 0.15       # up to +0.15 precision bonus
    # EMAクロスオーバー確認（BTとの整合性）
    # 本番データ分析: ema_cross WR26.7% EV-1.0 → ADX<20のレンジでは無効化
    if len(df) >= 2:
        ema9_prev  = float(df["ema9"].iloc[-2])
        ema21_prev = float(df["ema21"].iloc[-2])
        ema9_cross_up   = (ema9_prev <= ema21_prev) and (ema9 > ema21)
        ema9_cross_down = (ema9_prev >= ema21_prev) and (ema9 < ema21)
        # ADX>=15の場合のみフルボーナス（旧20→15に緩和:ロンドン/NY帯確保）
        cross_bonus = 1.5 if adx >= 15 else 0.3
        if ema9_cross_up:
            score += cross_bonus
            if adx >= 20:
                reasons.append(f"✅ EMA9/21ゴールデンクロス(ADX{adx:.0f}≥20)")
        elif ema9_cross_down:
            score -= cross_bonus
            if adx >= 20:
                reasons.append(f"✅ EMA9/21デッドクロス(ADX{adx:.0f}≥20)")
    score = max(-8.0, min(8.0, score))  # clamp before normalization

    # ── SL / TP ── 本番分析反映: SL拡大でノイズ耐性UP
    # 旧0.5/1.3 → SL_HIT率が85%で平均スリッページ+0.6pのため SL拡大
    SCALP_SL, SCALP_TP = 1.2, 2.0
    # 必須条件チェック（緩和版: 取引頻度重視、100pips/日目標）
    has_pb        = any("EMA9プルバック" in r and ("BUYゾーン" in r or "SELLゾーン" in r) for r in reasons)
    has_rsi_reset = any("RSI5" in r and ("売られ過ぎ" in r or "リセット完了" in r or "買われ過ぎ" in r or "中立圏" in r) for r in reasons)
    has_ema_cross = any("クロス" in r and ("ゴールデン" in r or "デッド" in r or "クロスオーバー" in r) for r in reasons)
    # EMAプルバック・RSIリセット・ドンチアンも有効な条件として追加
    has_don       = any("ドンチアン" in r and ("最高品質" in r or "有利" in r) for r in reasons)
    has_bb_zone   = any("BB" in r and ("BUYゾーン" in r or "SELLゾーン" in r) for r in reasons)
    has_stoch     = any("Stoch" in r and ("GC" in r or "DC" in r) for r in reasons)
    has_any_entry = has_pb or has_rsi_reset or has_ema_cross or has_don or has_bb_zone or has_stoch
    # スコア閾値: 0.6（旧0.8→ロンドン/NY帯の取引頻度確保）
    SCALP_SCORE_THRESHOLD = 0.6
    # 金曜日は閾値引き上げ: 高確信シグナルのみ通す（ema_pullback等の低品質除外）
    if _is_friday_scalp:
        SCALP_SCORE_THRESHOLD = 3.5  # 通常0.6 → 金曜3.5（超高確信のみ）
    # 条件が全くない場合のみWAIT（1つでもあればスコアで判定）
    if not has_any_entry and abs(score) < SCALP_SCORE_THRESHOLD * 2:
        reasons.append("⛔ エントリー条件未達 → WAIT")
        signal, conf = "WAIT", int(max(15, 50 - abs(score) * 5))
    elif abs(score) < SCALP_SCORE_THRESHOLD:
        reasons.append(f"⛔ スコア不足({score:.1f}<{SCALP_SCORE_THRESHOLD}) → WAIT")
        signal, conf = "WAIT", int(max(15, 50 - abs(score) * 5))
    elif score >  0: signal, conf = "BUY",  int(min(90, 50 + score * 5))
    elif score <  0: signal, conf = "SELL", int(min(90, 50 + abs(score) * 5))
    else:            signal, conf = "WAIT", 20

    act = signal if signal != "WAIT" else ("BUY" if score >= 0 else "SELL")
    atr_scalp = atr7 if atr7 > 0 else atr

    # SL: ATR7ベース + 最低距離保証
    sl = round(entry - atr_scalp * SCALP_SL, 3) if act == "BUY" else round(entry + atr_scalp * SCALP_SL, 3)
    # 最低SL距離: 3.0pips（スプレッド1.0-2.0pip + ノイズ余裕）
    MIN_SL_PIPS = 0.030  # 3.0 pips for JPY pairs
    sl_dist_raw = abs(entry - sl)
    if sl_dist_raw < MIN_SL_PIPS:
        sl = round(entry - MIN_SL_PIPS, 3) if act == "BUY" else round(entry + MIN_SL_PIPS, 3)
        reasons.append(f"⚠️ SL距離拡大: {sl_dist_raw*100:.1f}p → {MIN_SL_PIPS*100:.1f}p（最低保証）")

    # ② TP: S/Rレベルを考慮した動的調整（最大ATR7×2.0）
    SCALP_TP_MAX = 2.5
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

    # 最小RR保証（1.5以上: SL拡大に合わせてTPも十分確保）
    sl_dist = abs(entry - sl)
    if abs(tp - entry) < sl_dist * 1.5:
        tp = round(entry + sl_dist * 1.8, 3) if act == "BUY" else round(entry - sl_dist * 1.8, 3)
        reasons.append("⚠️ RR不足 → TP最小RR1.8に拡張")

    rr  = round(abs(tp - entry) / max(abs(sl - entry), 1e-6), 2)

    # ── エントリータイプ判定（BT戦略と整合）──
    _entry_type = "unknown"
    if tokyo_mode and signal != "WAIT":
        _entry_type = "tokyo_bb"
    elif signal != "WAIT":
        # EMAクロスが発火したかどうか直接判定（reasonsに依存しない）
        _had_ema_cross = False
        if len(df) >= 2:
            _ep = float(df["ema9"].iloc[-2])
            _e2p = float(df["ema21"].iloc[-2])
            if (_ep <= _e2p and ema9 > ema21) or (_ep >= _e2p and ema9 < ema21):
                _had_ema_cross = True
        _has_sr_bounce = any("S/R" in r and ("バウンス" in r or "近接" in r or "反発" in r) for r in reasons)
        _has_ema_pb    = any("EMA9プルバック" in r and ("BUY" in r or "SELL" in r) for r in reasons)
        _has_ob        = any("OB" in r or "オーダーブロック" in r for r in reasons)
        _has_don       = any("ドンチアン" in r and ("最高品質" in r or "有利" in r) for r in reasons)
        _has_bb        = any("BB" in r and ("BUYゾーン" in r or "SELLゾーン" in r) for r in reasons)
        _has_reg_ch    = any("回帰チャネル" in r and ("圧力" in r or "近接" in r) for r in reasons)
        if _has_ob:
            _entry_type = "ob_retest"
        elif _has_sr_bounce:
            _entry_type = "sr_bounce"
        elif _had_ema_cross:
            _entry_type = "ema_cross"
        elif _has_ema_pb:
            _entry_type = "ema_pullback"
        elif _has_don:
            _entry_type = "donchian"
        elif _has_bb:
            _entry_type = "bb_bounce"
        elif _has_reg_ch:
            _entry_type = "reg_channel"
        else:
            _entry_type = "momentum"

    ts_str = row.name.strftime("%Y-%m-%d %H:%M UTC") if hasattr(row.name, "strftime") else str(row.name)
    return {
        "timestamp": ts_str, "symbol": "USD/JPY", "tf": tf,
        "entry": round(entry, 3), "signal": signal, "confidence": conf,
        "ml_confidence": get_ml_confidence(df, len(df)-1, signal),
        "sl": sl, "tp": tp, "rr_ratio": rr, "atr": round(atr, 3),
        "session": session, "htf_bias": htf, "swing_mode": False,
        "reasons": reasons, "mode": "scalp",
        "entry_type": _entry_type,
        "layer_status": {
            "layer0": layer0,
            "layer1": layer1,
            "master_bias": layer1.get("label", "—"),
            "trade_ok":    not layer0["prohibited"],
        },
        "regime": regime,
        "layer2": layer2,
        "layer3": layer3,
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
            "rsi9":          round(rsi9, 1),
            "stoch_k":       round(float(row.get("stoch_k", 50)), 1),
            "adx":           round(adx, 1),
            "bb_width_pct":  round(bb_width_pct * 100, 0),
        },
        # 学術根拠S/R情報
        "academic_sr": {
            "round_sr":    round_sr,                          # Osler 2000
            "vpoc":        vpoc,                              # 機関投資家S/R
            "reg_channel": reg_ch,                            # Lo et al. 2000
            "enhanced_sr": enhanced_sr[:12],                  # 強化S/Rレベル
            "donchian": {                                     # BLL 1992 JoF
                "high": round(don_high, 3),
                "low":  round(don_low,  3),
                "mid":  round(don_mid,  3),
                "pct":  round(don_pct,  3),                  # 0=下限, 1=上限
            },
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


@app.route("/demo-analysis")
def demo_analysis_page():
    return render_template("demo_analysis.html")


@app.route("/api/performance")
def api_performance():
    """
    パフォーマンスモニター — KPI状態を返す
    ?last=100  最新N件でKPI計算 (default: 全件)
    ?mode=scalp  モード別フィルタ
    """
    try:
        records = list(_perf_records)  # copy

        mode = request.args.get("mode", "")
        if mode:
            records = [r for r in records if r.get("mode") == mode]

        last = request.args.get("last", "")
        if last.isdigit():
            records = records[-int(last):]

        kpi = compute_kpi(records)

        # モード別内訳
        scalp_recs = [r for r in _perf_records if r.get("mode") == "scalp"]
        dt_recs    = [r for r in _perf_records if r.get("mode") == "daytrade"]

        return jsonify({
            "kpi":            kpi,
            "kpi_target":     AGENT_MISSION["kpi"],
            "scalp_kpi":      compute_kpi(scalp_recs[-50:]) if scalp_recs else {},
            "daytrade_kpi":   compute_kpi(dt_recs[-30:])   if dt_recs   else {},
            "recent_trades":  _perf_records[-10:],          # last 10 records
            "total_recorded": len(_perf_records),
            "checked_at":     datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/performance/record", methods=["POST"])
def api_record_performance():
    """
    トレード結果を手動記録する。
    POST JSON body:
    {
        "signal":     "BUY",
        "mode":       "scalp",
        "tf":         "5m",
        "outcome":    "WIN",        // WIN | LOSS | BREAKEVEN
        "rr_ratio":   1.5,
        "entry":      150.123,
        "exit_price": 150.456,
        "sl":         150.000,
        "tp":         150.600,
        "confidence": 72
    }
    """
    try:
        data = request.get_json(force=True) or {}
        required = ["signal", "mode", "tf", "outcome", "rr_ratio", "entry", "exit_price", "sl", "tp"]
        missing  = [k for k in required if k not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        record = record_trade_result(
            signal     = data["signal"],
            mode       = data["mode"],
            tf         = data["tf"],
            outcome    = data["outcome"],
            rr_ratio   = float(data["rr_ratio"]),
            entry      = float(data["entry"]),
            exit_price = float(data["exit_price"]),
            sl         = float(data["sl"]),
            tp         = float(data["tp"]),
            confidence = int(data.get("confidence", 50)),
            layer1_dir = data.get("layer1_dir", "neutral"),
            regime     = data.get("regime", "UNKNOWN"),
        )
        kpi = compute_kpi(_perf_records[-50:])  # last 50 for rolling KPI
        return jsonify({"ok": True, "record": record, "rolling_kpi": kpi})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 400


@app.route("/api/layer-status")
def api_layer_status():
    """
    Layer 0-1 のリアルタイム状態を返す。
    UIのレイヤーステータスバナーに使用。
    """
    try:
        layer0 = is_trade_prohibited()
        layer1 = get_master_bias("USDJPY=X")
        calendar_events = get_economic_calendar()
        now_utc = datetime.now(timezone.utc)

        # 直近・次の高インパクト指標を抽出
        upcoming = []
        for ev in calendar_events:
            try:
                ev_dt = datetime.fromisoformat(
                    ev["date"].replace("Z", "+00:00")
                ).astimezone(timezone.utc)
                diff_min = (ev_dt - now_utc).total_seconds() / 60
                if -60 <= diff_min <= 240:
                    upcoming.append({**ev, "diff_min": round(diff_min, 0)})
            except Exception:
                continue
        upcoming.sort(key=lambda x: x["diff_min"])

        return jsonify({
            "layer0": layer0,
            "layer1": layer1,
            "upcoming_events": upcoming[:5],
            "checked_at": now_utc.isoformat(),
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/regime-status")
def api_regime_status():
    """市場レジーム判定 + Layer 2/3 状態を返す"""
    try:
        tf = request.args.get("tf", "1h")
        cfg = TF_CFG.get(tf, TF_CFG["1h"])
        df = fetch_ohlcv("USDJPY=X", period=cfg["period"], interval=cfg["interval"])
        df = add_indicators(df)
        sr_levels = find_sr_levels(df, window=cfg["sr_w"], tolerance_pct=cfg["sr_tol"])
        regime = detect_market_regime(df)
        layer2 = compute_layer2_score(df, tf)
        layer3 = compute_layer3_score(df, tf, sr_levels)
        return jsonify({
            "tf": tf,
            "regime": regime,
            "layer2": layer2,
            "layer3": layer3,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/signal")
def api_signal():
    tf   = request.args.get("tf", "1m")
    mode = request.args.get("mode", "standard")
    cfg  = TF_CFG.get(tf, TF_CFG["1m"])
    try:
        # ─ トレンド転換チェック（スキャルプ/デイトレ）─────────────
        # 上位足トレンドが転換していればBTキャッシュを自動クリア
        trend_info = None
        if mode in ("scalp", "daytrade"):
            trend_info = _check_trend_changed_and_clear_bt(mode)

        df = fetch_ohlcv("USDJPY=X", period=cfg["period"], interval=cfg["interval"])
        if cfg["resample"]: df = resample_df(df, cfg["resample"])
        df = add_indicators(df)
        sr = find_sr_levels(df, window=cfg["sr_w"], tolerance_pct=cfg["sr_tol"])
        if mode == "scalp":
            result = compute_scalp_signal(df, tf, sr, "USDJPY=X")
        elif mode == "daytrade":
            result = compute_daytrade_signal(df, tf, sr, "USDJPY=X")
        elif mode == "swing":
            result = compute_swing_signal(df, tf, sr, "USDJPY=X")
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
        # トレンド転換情報を付加（スキャルプ/デイトレのみ）
        if trend_info:
            result["trend_check"] = trend_info
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
        # SR: 強度スコアリング版（チャート描画用）
        bars_per_day_map = {"1m": 1440, "5m": 288, "15m": 96, "30m": 48,
                            "1h": 24, "4h": 6, "1d": 1, "1w": 0.143}
        bpd = bars_per_day_map.get(cfg["interval"], 24)
        sr_weighted = find_sr_levels_weighted(
            df, window=cfg["sr_w"], tolerance_pct=cfg["sr_tol"],
            min_touches=2, max_levels=12, bars_per_day=bpd)
        # 後方互換: floatリストも返す
        sr = [s["price"] for s in sr_weighted]
        ch = find_parallel_channel(df_chart, window=cfg["sr_w"], lookback=cfg["ch_lb"])

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
        return jsonify({"candles": candles, "sr_levels": sr,
                        "sr_weighted": sr_weighted, "channel": ch,
                        "lp_markers": markers, "ob_zones": ob_zns,
                        "liq_zones": liq_zns,
                        "ohlcv_source": src, "bar_count": len(df_chart)})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


def run_strategy_evaluation(symbol: str = "USDJPY=X",
                             interval: str = "5m",
                             lookback_days: int = 45) -> dict:
    """
    第三者評価フレームワーク:
    - ① ランダムエントリーベースラインとの比較
    - ② バイ・アンド・ホールドとの比較
    - ③ モンテカルロ信頼区間（1000シミュレーション）
    - ④ 統計的優位性検定（z検定）
    """
    import random as _random
    import math

    try:
        df = fetch_ohlcv(symbol, period=f"{lookback_days}d", interval=interval)
        df = add_indicators(df)
        df = df.dropna()
        if len(df) < 200:
            return {"error": "データ不足"}

        SPREAD  = 0.008   # 0.8 pip（OANDA実スプレッド）
        SL_MULT = 0.5    # BT と同じ RR3:1 設定に統一
        TP_MULT = 1.5
        MAX_HOLD = 20

        # ── A. Run our actual strategy BT ──
        our_result = run_scalp_backtest(symbol, lookback_days=lookback_days, interval=interval)
        our_wr = our_result.get("win_rate") or 0.0
        our_trades = our_result.get("trades") or our_result.get("total_trades") or 0

        # ── B. Random Entry Baseline ──
        _random.seed(42)
        rand_wins, rand_losses = 0, 0
        eligible_bars = list(range(50, len(df) - MAX_HOLD - 2))
        sample_size = max(our_trades, 30)
        sample_bars = _random.sample(eligible_bars, min(sample_size * 3, len(eligible_bars)))

        for bar_i in sample_bars:
            if rand_wins + rand_losses >= sample_size:
                break
            row = df.iloc[bar_i]
            atr = float(row.get("atr", 0.01))
            if atr <= 0:
                continue
            sig = "BUY" if _random.random() > 0.5 else "SELL"
            ep  = float(df.iloc[bar_i + 1]["Open"])
            ep  = ep + SPREAD/2 if sig == "BUY" else ep - SPREAD/2
            sl  = ep - atr * SL_MULT if sig == "BUY" else ep + atr * SL_MULT
            tp  = ep + atr * TP_MULT if sig == "BUY" else ep - atr * TP_MULT

            outcome = None
            for j in range(1, MAX_HOLD + 1):
                if bar_i + 1 + j >= len(df): break
                fut = df.iloc[bar_i + 1 + j]
                hi, lo = float(fut["High"]), float(fut["Low"])
                if sig == "BUY":
                    if hi >= tp: outcome = "WIN"; break
                    if lo <= sl: outcome = "LOSS"; break
                else:
                    if lo <= tp: outcome = "WIN"; break
                    if hi >= sl: outcome = "LOSS"; break
            if outcome == "WIN":   rand_wins += 1
            elif outcome == "LOSS": rand_losses += 1

        rand_total = rand_wins + rand_losses
        rand_wr = round(rand_wins / rand_total * 100, 1) if rand_total > 0 else 50.0

        # ── C. Buy-and-Hold Return ──
        bah_entry = float(df.iloc[50]["Close"])
        bah_exit  = float(df.iloc[-1]["Close"])
        bah_return_pct = round((bah_exit - bah_entry) / bah_entry * 100, 2)

        # ── D. Monte Carlo confidence interval for our strategy ──
        n = our_trades
        p = our_wr / 100.0 if our_trades > 0 else 0.5
        mc_iterations = 1000
        mc_wrs = []
        for _ in range(mc_iterations):
            mc_wins = sum(1 for _ in range(n) if _random.random() < p)
            mc_wrs.append(mc_wins / n * 100 if n > 0 else 50.0)
        mc_wrs.sort()
        ci_lo = round(mc_wrs[25], 1)   # 2.5th percentile
        ci_hi = round(mc_wrs[975], 1)  # 97.5th percentile

        # ── E. Statistical significance tests ──
        # E1: Z-test vs random baseline (NOT 50%, but actual random WR)
        rand_p = rand_wr / 100.0 if rand_total > 0 else 0.5
        if n > 0 and 0 < p < 1:
            # Standard error of edge (pooled)
            se_edge = math.sqrt(p * (1 - p) / n + rand_p * (1 - rand_p) / max(rand_total, 1))
            z_vs_random = (p - rand_p) / se_edge if se_edge > 0 else 0.0
            p_val_random = 2 * (1 - 0.5 * (1 + math.erf(abs(z_vs_random) / math.sqrt(2))))

            # E2: Z-test vs breakeven WR
            profile = STRATEGY_PROFILES.get(STRATEGY_MODE, STRATEGY_PROFILES["A"])
            be_wr = profile["breakeven_wr"]
            se_be = math.sqrt(p * (1 - p) / n)
            z_vs_be = (p - be_wr) / se_be if se_be > 0 else 0.0
            p_val_be = 2 * (1 - 0.5 * (1 + math.erf(abs(z_vs_be) / math.sqrt(2))))

            # E3: Confidence interval for strategy WR (Wilson score interval)
            z_ci = 1.96
            denom = 1 + z_ci**2 / n
            center = (p + z_ci**2 / (2 * n)) / denom
            margin = z_ci * math.sqrt((p * (1 - p) + z_ci**2 / (4 * n)) / n) / denom
            ci_wr_lo = round(max(0, center - margin) * 100, 1)
            ci_wr_hi = round(min(1, center + margin) * 100, 1)

            significant = p_val_random < 0.05
            sig_vs_be = p_val_be < 0.05 and p > be_wr
        else:
            z_vs_random, p_val_random = 0.0, 1.0
            z_vs_be, p_val_be = 0.0, 1.0
            ci_wr_lo, ci_wr_hi = 0.0, 100.0
            significant, sig_vs_be = False, False

        # ── F. Edge over random with standard error ──
        edge_vs_random = round(our_wr - rand_wr, 1)
        edge_se = round(se_edge * 100, 2) if n > 0 else 0.0

        # ── G. Effect size (Cohen's h) ──
        cohen_h = 0.0
        if n > 0 and rand_total > 0:
            cohen_h = round(2 * (math.asin(math.sqrt(p)) - math.asin(math.sqrt(rand_p))), 3)

        # ── H. EV confidence interval (bootstrap) ──
        our_ev = our_result.get("expected_value") or our_result.get("ev_per_trade") or 0
        ev_ci_lo, ev_ci_hi = our_ev, our_ev
        if our_trades > 30:
            _random.seed(123)
            boot_evs = []
            for _ in range(500):
                boot_sample = [_random.choice([our_ev + _random.gauss(0, 0.1)]) for _ in range(our_trades)]
                boot_evs.append(sum(boot_sample) / len(boot_sample))
            boot_evs.sort()
            ev_ci_lo = round(boot_evs[12], 3)
            ev_ci_hi = round(boot_evs[487], 3)

        return {
            "strategy": {
                "win_rate":    round(our_wr, 1),
                "win_rate_ci": [ci_wr_lo, ci_wr_hi],
                "total_trades": our_trades,
                "ev_per_trade": our_ev,
                "ev_ci_95":    [ev_ci_lo, ev_ci_hi],
                "sharpe":      our_result.get("sharpe"),
                "max_dd_pct":  our_result.get("max_drawdown") or our_result.get("max_dd_pct"),
                "entry_breakdown": our_result.get("entry_breakdown"),
            },
            "baseline_random": {
                "win_rate":    rand_wr,
                "total_trades": rand_total,
                "note": "同じSL/TP構造でランダムエントリー（seed=42）",
            },
            "baseline_bah": {
                "return_pct": bah_return_pct,
                "note": f"バイ・アンド・ホールド {lookback_days}日間",
            },
            "monte_carlo": {
                "ci_95_low":  ci_lo,
                "ci_95_high": ci_hi,
                "note": "1000回シミュレーション 95%信頼区間",
            },
            "significance": {
                "vs_random": {
                    "z_stat": round(z_vs_random, 3),
                    "p_value": round(p_val_random, 4),
                    "significant": significant,
                    "edge_pp": edge_vs_random,
                    "edge_se": edge_se,
                    "cohen_h": cohen_h,
                },
                "vs_breakeven": {
                    "breakeven_wr": round(be_wr * 100, 1) if n > 0 else 0,
                    "z_stat": round(z_vs_be, 3),
                    "p_value": round(p_val_be, 4),
                    "significant": sig_vs_be,
                },
                "verdict": (
                    "✅ ランダム＆BEの両方に対して統計的に有意（p<0.05）" if significant and sig_vs_be else
                    "🟡 ランダムに対して有意だがBE未達" if significant else
                    "⚠️ 統計的に有意でない（サンプル不足またはエッジ不十分）"
                ),
            },
            "kpi_targets": {
                "wr_target_pass": our_wr >= AGENT_MISSION["kpi"]["win_rate_min"],
                "beats_random":   our_wr > rand_wr,
                "stat_sig_random": significant,
                "stat_sig_be":    sig_vs_be,
            },
            "interval": interval,
            "lookback_days": lookback_days,
        }

    except Exception as e:
        return {"error": str(e)}


@app.route("/api/evaluation")
def api_evaluation():
    """第三者評価エンドポイント: ランダム比較 + モンテカルロ + 統計検定"""
    interval     = request.args.get("interval", "5m")
    lookback     = int(request.args.get("days", "45"))
    result = run_strategy_evaluation("USDJPY=X", interval=interval, lookback_days=lookback)
    return jsonify(result)


# ─────────────────────────────────────────────────────────────────
# FX ANALYST AGENT — 常駐学習型アナリスト（Claude API + MD記憶）
# ─────────────────────────────────────────────────────────────────
_ANALYST_MEMORY_FILE = "fxanalyst_memory.md"
_ANALYST_LOG_MAX     = 50   # MDに記録するアナリストノートの最大行数

def _read_analyst_memory() -> str:
    """MDファイルから記憶を読み込む。なければ空文字。"""
    try:
        path = os.path.join(os.path.dirname(__file__), _ANALYST_MEMORY_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return ""

def _append_analyst_note(note: str) -> None:
    """アナリストノートをMDに追記する。"""
    try:
        path = os.path.join(os.path.dirname(__file__), _ANALYST_MEMORY_FILE)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n### {ts}\n{note}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        print(f"[Analyst] append failed: {e}")

def _append_bt_result_to_memory(bt_result: dict, mode: str) -> None:
    """BT結果をMDの戦略評価ログに追記する。"""
    try:
        wr  = bt_result.get("win_rate", "?")
        ev  = bt_result.get("ev_per_trade", "?")
        tpd = bt_result.get("trades_per_day", "?")
        err = bt_result.get("error")
        if err:
            return  # エラー結果は記録しない
        ts = datetime.now().strftime("%Y-%m-%d")
        verdict = "✅" if (ev or 0) >= 0.10 else ("⚠️" if (ev or 0) >= 0 else "❌")
        row = f"| {ts} | {mode} | — | {wr}% | {ev}R | {verdict} | {tpd}件/日 |\n"
        path = os.path.join(os.path.dirname(__file__), _ANALYST_MEMORY_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            # 評価ログテーブルの後に挿入
            marker = "| 日付 | 戦略 | タイムフレーム | WR |"
            if marker in content:
                # 次の行（---|---行）を探してその後に追記
                idx = content.index(marker)
                next_nl = content.index("\n", idx + len(marker))
                sep_line_end = content.index("\n", next_nl + 1)
                content = content[:sep_line_end+1] + row + content[sep_line_end+1:]
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
    except Exception as e:
        print(f"[Analyst] bt_log failed: {e}")

def get_analyst_opinion(question: str, market_context: dict = None) -> dict:
    """
    FXアナリストエージェントに意見を求める。
    - fxanalyst_memory.md の知見を記憶として参照
    - 学術的知見（効率市場仮説・テクニカル分析の限界など）を内蔵
    - Claude API で分析・回答
    """
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {"error": "ANTHROPIC_API_KEY not set", "opinion": None}

        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=api_key)

        memory = _read_analyst_memory()

        # 学術的知見ライブラリ（内蔵）
        academic_context = """
## 学術的知見ライブラリ（FXアナリスト参照用）

### 効率市場仮説（EMH）と技術分析
- **弱形効率性**: 過去価格パターンは現在価格に織り込み済み（Fama 1970）
- **実証研究**: Lo & MacKinlay (1988) — 短期的な自己相関が存在し弱形効率性に疑義
- **FX市場の非効率**: Neely & Weller (2003) — テクニカルフィルターがランダムウォークを凌駕する期間が存在
- **マーケットマイクロストラクチャー**: Lyons (2001) — ディーラー間フローが短期価格を動かす（情報の非対称性）

### EMAクロスオーバー戦略
- **Brock et al. (1992)**: DJIA1897-1986で移動平均ルールが有意な超過リターン（取引コスト前）
- **メタ分析（Park & Irwin 2007）**: 95論文中56が正のリターン、ただし近年は効果が薄れる傾向
- **FXへの適用**: Schulmeister (2009) — 外国為替での技術ルールは正EV（特に1990-2000年代）
- **崩壊の兆候**: Zafeiriou (2018) — アルゴトレーダーの参加増加でEMAクロスの収益性低下

### リスク・リターンと最適RR比
- **ケリー基準**: f = (WR × RR - (1-WR)) / RR → 最適フラクション
  - WR=35%, RR=3: f = (0.35×3 - 0.65) / 3 = 0.383 → 資金の38%がケリー推奨
- **プロスペクト理論 (Kahneman & Tversky 1979)**: 損失は利益の2.25倍に感じられる → 高RR戦略は心理的に継続困難
- **シャープレシオの限界**: 非正規分布リターンでは不適切（FXはファットテール）

### USDJPY固有の特性
- **キャリートレード影響**: Brunnermeier et al. (2009) — JPYは「クラッシュリスク通貨」。円高急騰は非線形
- **BOJ介入**: Ito & Yabu (2007) — 介入は短期的に価格を動かすが長期効果は限定的
- **セッション効果**: Dacorogna et al. (1993) — 東京セッション中は値動きが小さく、ロンドン/NYオープン時に拡大
- **月曜日効果**: Berument & Kiymaz (2001) — FXでは月曜の流動性が低く、スプレッドが広がりやすい

### バックテストの落とし穴
- **過学習（Pézier 2008）**: パラメーター数が多いほどBT結果は楽観的 → 独立データでの検証必須
- **生存バイアス**: 過去に有効だった戦略のみが研究対象になる傾向
- **市場体制変化 (Lo 2004)**: Adaptive Market Hypothesis — 有効な戦略は市場参加者が模倣して収益性が低下
"""

        # 市場コンテキスト
        ctx_str = ""
        if market_context:
            ctx_str = f"\n## 現在の市場データ\n```json\n{str(market_context)[:1000]}\n```\n"

        system_prompt = f"""あなたはUSDP FX市場（特にUSD/JPY）の経験豊富なFXアナリストです。
以下の3つの情報源を統合して、具体的・実践的な意見を日本語で提供してください：

1. **蓄積された知見（Memory）** — このシステムの過去BT結果と学習内容
2. **学術的知見** — FX市場に関する査読済み研究の知見
3. **現在の市場データ** — 直近のシグナルとBT結果

回答の原則:
- 具体的な数値や根拠を示す
- 「わからない」場合は正直に言う
- 改善提案は優先度と期待効果を付けて提示
- 学術的根拠があれば論文名/著者を引用
- 200-400字程度で簡潔に

## システム蓄積Knowledge (Memory)
{memory[:3000] if memory else "（まだ記録なし）"}

{academic_context}
{ctx_str}"""

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": question}]
        )

        opinion = response.content[0].text if response.content else ""

        # アナリストノートに記録
        _append_analyst_note(f"**質問**: {question[:100]}\n\n**回答**: {opinion[:500]}")

        return {
            "opinion":      opinion,
            "model":        "claude-opus-4-5",
            "memory_used":  bool(memory),
            "question":     question,
        }

    except Exception as e:
        return {"error": str(e), "opinion": None}


def run_historical_pattern_analysis(
    symbol: str = "USDJPY=X",
    interval: str = "1h",
    lookback_days: int = 730,   # 2 years
) -> dict:
    """
    Massive APIの過去データを使った勝ちパターン分析エンジン。

    分析軸:
      ① 時間帯別WR   (東京/ロンドン/NY/ディープナイト)
      ② 曜日別WR     (月〜金)
      ③ ADXレベル別  (デッドゾーン/弱トレンド/中トレンド/強トレンド)
      ④ ATRレジーム  (低ボラ/通常/高ボラ)
      ⑤ EMAアライン  (弱/中/強アライメント)

    各パターンについてZ検定で有意性を検証し、
    p < 0.05 のものだけを「発見パターン」として記録する。
    """
    import math

    try:
        # ── 1. データ取得 ──
        # Massive API経由（長期データ）、失敗したらyfinanceフォールバック
        df = fetch_ohlcv(symbol, period=f"{lookback_days}d", interval=interval)
        # インデックスを UTC DatetimeIndex に正規化（Massive/yfinance どちらでも動作）
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)
        elif df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
        df = add_indicators(df)
        df = df.dropna()

        if len(df) < 200:
            return {"error": "データ不足 (200本以上必要)", "bars": len(df)}

        # ── 2. BTシミュレーション（EMAクロスオーバー戦略、RR=3:1）──
        SPREAD  = 0.008   # 0.8 pip（OANDA実スプレッド）
        SL_MULT = 0.5
        TP_MULT = 1.5
        MAX_HOLD = 20
        COOLDOWN = 2

        trades = []
        last_bar = -99

        for i in range(50, len(df) - MAX_HOLD - 2):
            if i - last_bar < COOLDOWN:
                continue

            row      = df.iloc[i]
            prev_row = df.iloc[i - 1]

            try:
                ema9   = float(row["ema9"])
                ema21  = float(row["ema21"])
                ema50  = float(row["ema50"])
                ema9_p = float(prev_row["ema9"])
                ema21_p= float(prev_row["ema21"])
                atr    = float(row.get("atr", 0.01))
                adx    = float(row.get("adx", 20.0))
                rsi    = float(row["rsi"])
            except Exception:
                continue

            if atr <= 0:
                continue

            cross_up   = (ema9_p <= ema21_p) and (ema9 > ema21)
            cross_down = (ema9_p >= ema21_p) and (ema9 < ema21)

            if not cross_up and not cross_down:
                continue
            if cross_up   and ema9 < ema50: continue
            if cross_down and ema9 > ema50: continue
            if adx < 12: continue

            # ATRスパイクフィルター
            atr_avg = float(df["atr"].iloc[max(0, i-20):i].mean())
            if atr_avg > 0 and atr > atr_avg * 2.5:
                continue

            sig = "BUY" if cross_up else "SELL"

            # 特徴量を記録（パターン分析用）
            try:
                hour    = row.name.hour
                weekday = row.name.weekday()  # 0=Mon, 4=Fri
            except Exception:
                hour, weekday = 12, 2

            # セッション分類
            if 0 <= hour < 7:
                session = "TOKYO_EARLY"
            elif 7 <= hour < 9:
                session = "LONDON_OPEN"
            elif 9 <= hour < 13:
                session = "LONDON"
            elif 13 <= hour < 17:
                session = "NY_OPEN"
            elif 17 <= hour < 20:
                session = "NY"
            else:
                session = "DEEP_NIGHT"

            # ADXバケット
            if adx < 15:
                adx_bucket = "DEAD"
            elif adx < 20:
                adx_bucket = "WEAK"
            elif adx < 30:
                adx_bucket = "MED"
            else:
                adx_bucket = "STRONG"

            # ATRレジーム
            atr_ratio = atr / (atr_avg + 1e-6)
            if atr_ratio < 0.7:
                atr_regime = "LOW_VOL"
            elif atr_ratio < 1.5:
                atr_regime = "NORMAL"
            else:
                atr_regime = "HIGH_VOL"

            # EMAアライメント強度
            ema_align = abs(ema9 - ema21) / (atr + 1e-6)
            if ema_align < 0.3:
                ema_strength = "WEAK"
            elif ema_align < 0.8:
                ema_strength = "MED"
            else:
                ema_strength = "STRONG"

            # エントリー実行
            if i + 1 >= len(df):
                continue
            ep = float(df.iloc[i + 1]["Open"])
            ep = ep + SPREAD / 2 if sig == "BUY" else ep - SPREAD / 2
            sl = ep - atr * SL_MULT if sig == "BUY" else ep + atr * SL_MULT
            tp = ep + atr * TP_MULT if sig == "BUY" else ep - atr * TP_MULT

            outcome = None
            for j in range(1, MAX_HOLD + 1):
                if i + 1 + j >= len(df):
                    break
                fut = df.iloc[i + 1 + j]
                hi2, lo2 = float(fut["High"]), float(fut["Low"])
                if sig == "BUY":
                    if hi2 >= tp: outcome = 1; break
                    if lo2 <= sl: outcome = 0; break
                else:
                    if lo2 <= tp: outcome = 1; break
                    if hi2 >= sl: outcome = 0; break

            if outcome is not None:
                last_bar = i
                trades.append({
                    "outcome":      outcome,
                    "hour":         hour,
                    "weekday":      weekday,
                    "session":      session,
                    "adx_bucket":   adx_bucket,
                    "atr_regime":   atr_regime,
                    "ema_strength": ema_strength,
                    "sig":          sig,
                    "adx":          round(adx, 1),
                })

        if len(trades) < 30:
            return {"error": f"シグナルサンプル不足 ({len(trades)}件)", "bars": len(df)}

        import pandas as _pd_local
        df_trades = _pd_local.DataFrame(trades)
        total_wr   = df_trades["outcome"].mean()
        total_n    = len(df_trades)

        # ── 3. パターン別WR計算 + Z検定 ──
        def z_test(group_wins, group_n, baseline_p):
            """H0: このグループのWR = ベースラインWR に対してZ検定"""
            if group_n < 5:
                return 0.0, 1.0, False
            p_hat = group_wins / group_n
            se = math.sqrt(baseline_p * (1 - baseline_p) / group_n)
            if se == 0:
                return 0.0, 1.0, False
            z = (p_hat - baseline_p) / se
            p_val = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
            return round(z, 3), round(p_val, 4), p_val < 0.05

        patterns = {}

        # ─ A. 時間帯別 ─
        hour_patterns = {}
        for h in range(24):
            g = df_trades[df_trades["hour"] == h]
            if len(g) < 3:
                continue
            wins = g["outcome"].sum()
            n    = len(g)
            wr   = wins / n
            z, pv, sig_flag = z_test(wins, n, total_wr)
            hour_patterns[h] = {
                "wr": round(wr * 100, 1),
                "n":  n,
                "z":  z,
                "p":  pv,
                "significant": sig_flag,
                "edge": round((wr - total_wr) * 100, 1),
            }
        patterns["by_hour"] = hour_patterns

        # ─ B. 曜日別 ─
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        weekday_patterns = {}
        for d in range(5):
            g = df_trades[df_trades["weekday"] == d]
            if len(g) < 3:
                continue
            wins = g["outcome"].sum()
            n    = len(g)
            wr   = wins / n
            z, pv, sig_flag = z_test(wins, n, total_wr)
            weekday_patterns[day_names[d]] = {
                "wr": round(wr * 100, 1),
                "n":  n,
                "z":  z,
                "p":  pv,
                "significant": sig_flag,
                "edge": round((wr - total_wr) * 100, 1),
            }
        patterns["by_weekday"] = weekday_patterns

        # ─ C. セッション別 ─
        session_patterns = {}
        for s in df_trades["session"].unique():
            g = df_trades[df_trades["session"] == s]
            wins = g["outcome"].sum()
            n    = len(g)
            wr   = wins / n
            z, pv, sig_flag = z_test(wins, n, total_wr)
            session_patterns[s] = {
                "wr": round(wr * 100, 1),
                "n":  n,
                "z":  z,
                "p":  pv,
                "significant": sig_flag,
                "edge": round((wr - total_wr) * 100, 1),
            }
        patterns["by_session"] = session_patterns

        # ─ D. ADXバケット別 ─
        adx_patterns = {}
        for bucket in ["DEAD", "WEAK", "MED", "STRONG"]:
            g = df_trades[df_trades["adx_bucket"] == bucket]
            if len(g) < 3:
                continue
            wins = g["outcome"].sum()
            n    = len(g)
            wr   = wins / n
            z, pv, sig_flag = z_test(wins, n, total_wr)
            adx_patterns[bucket] = {
                "wr": round(wr * 100, 1),
                "n":  n,
                "z":  z,
                "p":  pv,
                "significant": sig_flag,
                "edge": round((wr - total_wr) * 100, 1),
            }
        patterns["by_adx"] = adx_patterns

        # ─ E. ATRレジーム別 ─
        atr_patterns = {}
        for regime in ["LOW_VOL", "NORMAL", "HIGH_VOL"]:
            g = df_trades[df_trades["atr_regime"] == regime]
            if len(g) < 3:
                continue
            wins = g["outcome"].sum()
            n    = len(g)
            wr   = wins / n
            z, pv, sig_flag = z_test(wins, n, total_wr)
            atr_patterns[regime] = {
                "wr": round(wr * 100, 1),
                "n":  n,
                "z":  z,
                "p":  pv,
                "significant": sig_flag,
                "edge": round((wr - total_wr) * 100, 1),
            }
        patterns["by_atr_regime"] = atr_patterns

        # ─ F. EMAアライメント強度別 ─
        ema_patterns = {}
        for strength in ["WEAK", "MED", "STRONG"]:
            g = df_trades[df_trades["ema_strength"] == strength]
            if len(g) < 3:
                continue
            wins = g["outcome"].sum()
            n    = len(g)
            wr   = wins / n
            z, pv, sig_flag = z_test(wins, n, total_wr)
            ema_patterns[strength] = {
                "wr": round(wr * 100, 1),
                "n":  n,
                "z":  z,
                "p":  pv,
                "significant": sig_flag,
                "edge": round((wr - total_wr) * 100, 1),
            }
        patterns["by_ema_strength"] = ema_patterns

        # ── 4. 有意パターン抽出（p < 0.05）──
        significant_findings = []
        for axis, axis_data in patterns.items():
            for label, data in axis_data.items():
                if data.get("significant"):
                    edge = data["edge"]
                    direction = "HIGH_WR" if edge > 0 else "LOW_WR"
                    significant_findings.append({
                        "axis":      axis.replace("by_", ""),
                        "condition": str(label),
                        "wr":        data["wr"],
                        "edge_pp":   edge,
                        "n":         data["n"],
                        "z":         data["z"],
                        "p":         data["p"],
                        "direction": direction,
                    })
        # edge絶対値でソート
        significant_findings.sort(key=lambda x: abs(x["edge_pp"]), reverse=True)

        # ── 5. fxanalyst_memory.md に記録 ──
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        finding_lines = []
        for f in significant_findings[:15]:  # 上位15件
            sign = "✅高WR" if f["direction"] == "HIGH_WR" else "❌低WR"
            finding_lines.append(
                f"  - {sign} [{f['axis']}={f['condition']}]: "
                f"WR={f['wr']}% (edge={f['edge_pp']:+.1f}pp, n={f['n']}, p={f['p']})"
            )

        memory_entry = f"""
## 過去パターン分析結果 ({ts})

- 分析期間: {lookback_days}日 / 足種: {interval}
- 総シグナル数: {total_n}件
- 全体WR: {round(total_wr*100,1)}%

### 統計的有意パターン (p < 0.05)
{chr(10).join(finding_lines) if finding_lines else "  - 有意パターンなし（サンプル不足の可能性）"}

"""
        _append_analyst_note(memory_entry)

        return {
            "total_trades":   total_n,
            "overall_wr":     round(total_wr * 100, 1),
            "interval":       interval,
            "lookback_days":  lookback_days,
            "patterns":       patterns,
            "significant_findings": significant_findings,
            "bars_analyzed":  len(df),
        }

    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()[-500:]}


@app.route("/api/pattern-analysis")
def api_pattern_analysis():
    """
    過去データの勝ちパターン分析
    ?interval=1h&days=730 (デフォルト: 1h足 / 730日=2年)
    """
    interval = request.args.get("interval", "1h")
    days     = int(request.args.get("days", "730"))
    result   = run_historical_pattern_analysis("USDJPY=X", interval=interval, lookback_days=days)
    return jsonify(result)


@app.route("/api/analyst-opinion", methods=["GET", "POST"])
def api_analyst_opinion():
    """
    FXアナリストエージェントへの問い合わせ
    GET: ?q=質問文
    POST: {"question": "質問文", "context": {...}}
    """
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        question = data.get("question", "現在の戦略を評価してください")
        context  = data.get("context")
    else:
        question = request.args.get("q", "現在の戦略の強みと弱みを分析してください")
        context  = None

    result = get_analyst_opinion(question, context)
    return jsonify(result)


@app.route("/api/ml-train")
def api_ml_train():
    """Trigger ML model training."""
    success = train_ml_model()
    if success:
        acc_info = f"Trained at {_ml_trained_at.strftime('%Y-%m-%d %H:%M')}" if _ml_trained_at else "OK"
        return jsonify({"status": "ok", "message": acc_info})
    else:
        return jsonify({"status": "error", "message": "Training failed or insufficient data"})


@app.route("/api/backtest")
def api_backtest():
    """バックテスト結果（モード別キャッシュ）
    ?mode=scalp&tf=5m / ?mode=daytrade / ?mode=swing / ?mode=standard
    ?force=1 でキャッシュを無視して即時再計算
    """
    try:
        mode  = request.args.get("mode", "standard")
        force = request.args.get("force", "0") == "1"

        # force=1: 対象モードのキャッシュをクリアして再計算
        if force:
            if mode == "scalp":      _scalp_bt_cache.clear()
            elif mode == "daytrade": _dt_bt_cache.clear()
            elif mode == "swing":    _sw_bt_cache.clear()
            else:                    _bt_cache.clear()

        if mode == "scalp":
            tf = request.args.get("tf", "5m")
            # 5m=180日（半年・統計的有意性確保）/ 1m=7日（実験的・高ノイズ）/ 15m=90日
            if tf == "1m":
                interval, lookback = "1m", 7
            elif tf == "15m":
                interval, lookback = "15m", 55  # Yahoo 15m上限60日
            else:  # 5m がデフォルト
                interval, lookback = "5m", 55   # Yahoo 5m上限60日
            result = run_scalp_backtest("USDJPY=X", lookback_days=lookback, interval=interval)
        elif mode == "daytrade":
            result = run_daytrade_backtest("USDJPY=X", lookback_days=55, interval="15m")
        elif mode == "swing":
            result   = run_swing_backtest("USDJPY=X", lookback_days=365)
        else:
            result = run_backtest("USDJPY=X", lookback_days=90)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/strategy-mode", methods=["GET", "POST"])
def api_strategy_mode():
    """Get or set the active strategy mode (A=Trend Following, B=Mean Reversion)."""
    global STRATEGY_MODE
    if request.method == "POST":
        mode = request.json.get("mode", "A").upper()
        if mode in STRATEGY_PROFILES:
            STRATEGY_MODE = mode
            # Clear BT caches to force re-run with new params
            _scalp_bt_cache.clear()
            _dt_bt_cache.clear()
            return jsonify({"status": "ok", "mode": mode, "profile": STRATEGY_PROFILES[mode]})
        return jsonify({"error": f"Invalid mode: {mode}"}), 400
    return jsonify({"mode": STRATEGY_MODE, "profile": STRATEGY_PROFILES[STRATEGY_MODE]})


@app.route("/api/trend-status")
def api_trend_status():
    """
    スキャルプ(1H+4H)・デイトレード(4H+1D)のトレンド状態を返す。
    UI上でリアルタイムトレンド確認・BTキャッシュ状態確認に使用。
    """
    try:
        scalp_bias = get_htf_bias("USDJPY=X")
        dt_bias    = get_htf_bias_daytrade("USDJPY=X")
        now_utc    = datetime.now(timezone.utc).isoformat()

        return jsonify({
            "checked_at": now_utc,
            "scalp": {
                "mode":       "scalp",
                "tfs":        "1H+4H",
                "agreement":  scalp_bias.get("agreement"),
                "label":      scalp_bias.get("label"),
                "score":      scalp_bias.get("score"),
                "h1":         scalp_bias.get("h1", {}),
                "h4":         scalp_bias.get("h4", {}),
                "last_trend_state": _trend_state.get("scalp", "未チェック"),
                "trend_changed_at": _trend_changed_at.get("scalp", ""),
                "bt_cached":  bool(_scalp_bt_cache),
            },
            "daytrade": {
                "mode":       "daytrade",
                "tfs":        "4H+1D",
                "agreement":  dt_bias.get("agreement"),
                "label":      dt_bias.get("label"),
                "score":      dt_bias.get("score"),
                "h4":         dt_bias.get("h4", {}),
                "d1":         dt_bias.get("d1", {}),
                "last_trend_state": _trend_state.get("daytrade", "未チェック"),
                "trend_changed_at": _trend_changed_at.get("daytrade", ""),
                "bt_cached":  bool(_dt_bt_cache),
            },
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/cron")
def api_cron():
    """
    外部cronサービスから定期的に呼ばれるトレンド確認エンドポイント。
    スキャルプ  : 1H毎に呼ぶ  (/api/cron?mode=scalp)
    デイトレード: 4H毎に呼ぶ  (/api/cron?mode=daytrade)

    トレンド転換検出時: バックテストキャッシュをクリア → 次回BT要求時に自動再計算。
    外部cron設定例: cron-job.org でURL登録 → 間隔設定
    """
    mode = request.args.get("mode", "scalp")
    try:
        trend_result = _check_trend_changed_and_clear_bt(mode)
        return jsonify({
            "mode":         mode,
            "ok":           True,
            "trend_changed": trend_result.get("changed", False),
            "prev":         trend_result.get("prev"),
            "current":      trend_result.get("current"),
            "label":        trend_result.get("label"),
            "score":        trend_result.get("score"),
            "bt_cache_cleared": trend_result.get("changed", False),
            "changed_at":   trend_result.get("changed_at"),
            "checked_at":   datetime.now(timezone.utc).isoformat(),
            "schedule_recommendation": {
                "scalp":    "1H毎 (1H足ローソク足クローズに合わせて)",
                "daytrade": "4H毎 (4H足ローソク足クローズに合わせて)",
            }.get(mode, ""),
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/money-management")
def api_money_management():
    """
    資金管理・ポジションサイジング計算
    ?capital=250000  現在資産（円）
    ?risk_pct=1.0    1トレード当たりリスク（%）
    ?mode=scalp|daytrade

    バックテスト実証値を使用:
      スキャルピング5m: EV=+0.052, WR=39.4%, 80.7件/日, SL=ATR×0.5
      デイトレード15m : EV=+0.096, WR=32.0%, 1.76件/日, SL=ATR×0.8
    """
    try:
        capital   = float(request.args.get("capital",  250_000))
        risk_pct  = float(request.args.get("risk_pct", 1.0))
        mode      = request.args.get("mode", "scalp")
        goal      = float(request.args.get("goal",    1_000_000))
        months    = float(request.args.get("months",  3))
        # 現在の USD/JPY レート（フロントから渡す、デフォルト150円）
        usdjpy    = float(request.args.get("rate",     150.0))

        # ── バックテスト実証パラメータ ────────────────────
        BT = {
            "scalp": {
                "ev":         0.052,   # 期待値 R/トレード
                "win_rate":   39.4,    # 勝率 %
                "sl_mult":    0.5,     # SL = ATR×0.5
                "tp_mult":    0.9,     # TP = ATR×0.9
                "bep":        35.7,    # 損益分岐勝率 %
                "trades_day": 80.7,    # 1日あたり取引数
                "sharpe":     0.075,
                "max_dd_r":   17.4,    # 最大DD (R)
                "interval":   "5m",
                "label":      "スキャルピング 5m足",
            },
            "daytrade": {
                "ev":         0.096,
                "win_rate":   32.0,
                "sl_mult":    0.8,
                "tp_mult":    2.0,
                "bep":        28.6,
                "trades_day": 1.76,
                "sharpe":     1.153,
                "max_dd_r":   10.0,
                "interval":   "15m",
                "label":      "デイトレード 15m足",
            },
        }
        p = BT.get(mode, BT["scalp"])

        risk_amount  = round(capital * risk_pct / 100, 0)   # 1トレードリスク額（円）

        # USD/JPY: ATR参考値 (5m≈0.06円, 15m≈0.12円)
        atr_ref_jpy  = 0.06 if mode == "scalp" else 0.12
        sl_pips_ref  = round(atr_ref_jpy * p["sl_mult"] * 100, 1)  # pips

        # ── ポジションサイズ計算（SBI FX 25倍レバレッジ）─────────────
        # 1pip = 0.01円/通貨 (USD/JPY)
        # SBI最小単位 = 1,000通貨（1口）
        LEVERAGE = 25
        # ① リスク額ベースの理想口数
        raw_units     = risk_amount / (sl_pips_ref * 0.01) if sl_pips_ref > 0 else 0
        lot_sbi_risk  = max(1, int(raw_units / 1_000))

        # ② 証拠金キャップ: 資本の50%まで（SBI維持率200%=ロスカット50%の4倍余裕）
        # 推奨は余裕係数を変えられるように margin_cap_pct で管理
        margin_cap_pct = 50.0   # 資本の何%まで証拠金に使うか（安全上限）
        max_margin_ok  = capital * margin_cap_pct / 100
        lot_sbi_margin = max(1, int(max_margin_ok * LEVERAGE / (1_000 * usdjpy)))

        # 実際の推奨口数 = 両者の小さい方
        lot_sbi       = min(lot_sbi_risk, lot_sbi_margin)
        margin_limited = (lot_sbi < lot_sbi_risk)   # 証拠金上限で口数が絞られた
        lot_units     = lot_sbi * 1_000              # 実取引通貨数（1,000単位）

        # 最大取引可能口数（資本100%使用した場合の理論上限）
        max_lot_sbi = max(0, int(capital * LEVERAGE / (1_000 * usdjpy)))

        # 必要証拠金 = 取引通貨数 × USD/JPYレート / レバレッジ
        required_margin  = round(lot_units * usdjpy / LEVERAGE, 0)
        margin_ratio_pct = round(required_margin / capital * 100, 1)
        margin_surplus   = round(capital - required_margin, 0)

        # 証拠金維持率 = 資本 / 必要証拠金 × 100（SBIロスカット閾値: 50%）
        maint_ratio = round(capital / required_margin * 100, 0) if required_margin > 0 else 9999

        # 証拠金安全ラベル
        if margin_ratio_pct < 30:
            margin_safety = "✅ 余裕"
        elif margin_ratio_pct < 50:
            margin_safety = "⚠️ 注意"
        else:
            margin_safety = "🚨 危険（追証リスク）"

        # 実際のSLリスク額（口数確定後）
        actual_sl_jpy   = round(lot_units * sl_pips_ref * 0.01, 0)
        actual_risk_pct = round(actual_sl_jpy / capital * 100, 2)

        lot_standard = round(lot_units / 100_000, 2)   # 標準ロット（参考）

        # ── 日次期待PL計算 ────────────────────────────────
        # 期待R/日 = ev × trades_day
        ev_r_per_day  = round(p["ev"] * p["trades_day"], 3)
        # 期待円/日 = ev_R/日 × リスク額
        ev_jpy_per_day = round(ev_r_per_day * risk_amount, 0)
        # 月次期待円 (22営業日)
        trading_days  = 22
        ev_jpy_month  = round(ev_jpy_per_day * trading_days, 0)
        monthly_return_pct = round(ev_jpy_month / capital * 100, 1)

        # ── 目標到達シミュレーション ───────────────────────
        # 複利: capital × (1 + monthly_pct/100)^n = goal を解く
        if monthly_return_pct > 0:
            months_needed = round(
                (goal / capital) ** (1 / (monthly_return_pct / 100 + 1) * 0) or 0,
                1
            ) if False else round(
                np.log(goal / capital) / np.log(1 + monthly_return_pct / 100),
                1
            )
        else:
            months_needed = None

        # 指定月後の資産（複利）
        projected = round(capital * (1 + monthly_return_pct / 100) ** months, 0)

        # 最大ドローダウン
        max_dd_jpy = round(p["max_dd_r"] * risk_amount, 0)
        max_dd_pct = round(max_dd_jpy / capital * 100, 1)

        # 目標達成チェック
        remaining_pct = round((goal - capital) / capital * 100, 1)
        progress_pct  = round((capital - 250_000) / (goal - 250_000) * 100, 1) if goal > 250_000 else 0
        progress_pct  = max(0, min(100, progress_pct))

        return jsonify({
            "mode":              mode,
            "label":             p["label"],
            "capital":           capital,
            "goal":              goal,
            "months_target":     months,
            "risk_pct":          risk_pct,
            "risk_amount_jpy":   risk_amount,
            "backtest": {
                "ev_per_trade":  p["ev"],
                "win_rate":      p["win_rate"],
                "bep":           p["bep"],
                "sl_mult":       p["sl_mult"],
                "tp_mult":       p["tp_mult"],
                "trades_per_day":p["trades_day"],
                "sharpe":        p["sharpe"],
                "max_dd_r":      p["max_dd_r"],
            },
            "position": {
                "sl_pips":          sl_pips_ref,
                "lot_units":        lot_units,          # 取引通貨数
                "lot_sbi":          lot_sbi,            # SBI口数 (1口=1,000通貨)
                "lot_sbi_risk":     lot_sbi_risk,       # リスク額ベースの理想口数
                "lot_sbi_margin":   lot_sbi_margin,     # 証拠金上限ベースの最大口数
                "margin_limited":   margin_limited,     # 証拠金上限で絞られたか
                "required_margin":  required_margin,    # 必要証拠金（円）
                "margin_ratio_pct": margin_ratio_pct,   # 証拠金占有率（%）
                "maint_ratio":      maint_ratio,        # 証拠金維持率（%）SBI閾値50%
                "margin_surplus":   margin_surplus,     # 証拠金余力（円）
                "margin_safety":    margin_safety,      # 安全度ラベル
                "margin_cap_pct":   margin_cap_pct,     # 使用した証拠金上限設定
                "max_lot_sbi":      max_lot_sbi,        # 資本で取れる理論最大口数
                "actual_sl_jpy":    actual_sl_jpy,      # 実効SLリスク額（円）
                "actual_risk_pct":  actual_risk_pct,    # 実効リスク率（%）
                "usdjpy_rate":      usdjpy,             # 使用レート
                "leverage":         LEVERAGE,
                # 後方互換
                "lot_standard":     lot_standard,
                "lot_mini":         round(lot_units / 10_000, 2),
                "lot_micro":        lot_sbi,
            },
            "expected_pl": {
                "ev_r_per_day":    ev_r_per_day,
                "jpy_per_day":     ev_jpy_per_day,
                "jpy_per_month":   ev_jpy_month,
                "monthly_return_pct": monthly_return_pct,
                "projected_capital": projected,
            },
            "risk": {
                "max_dd_jpy":    max_dd_jpy,
                "max_dd_pct":    max_dd_pct,
                "ruin_risk":     "低" if max_dd_pct < 20 else ("中" if max_dd_pct < 40 else "高"),
            },
            "goal_tracker": {
                "months_needed": months_needed,
                "progress_pct":  progress_pct,
                "remaining_pct": remaining_pct,
                "on_track":      (months_needed is not None and months_needed <= months),
            },
        })
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
PRICE_TTL = 8  # 8秒キャッシュ（Basic枠: 8req/min）

@app.route("/api/price")
def api_price():
    """
    TwelveDataからUSD/JPYリアルタイム価格を取得。
    TWELVEDATA_API_KEY 環境変数が未設定の場合はyfinanceにフォールバック。
    """
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
            _price_cache.clear(); _price_cache.update({"data": data, "ts": now})
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
        _price_cache.clear(); _price_cache.update({"data": data, "ts": now})
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════
#  Demo Trader — 自動デモトレードシステム
# ═══════════════════════════════════════════════════════
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader

# Render Disk: /var/data が存在すれば永続ストレージを使用、なければローカル（開発用）
_render_disk = "/var/data"
if os.path.isdir(_render_disk):
    _db_path = os.path.join(_render_disk, "demo_trades.db")
else:
    _db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "demo_trades.db"))
_demo_db = DemoDB(db_path=_db_path)

# ── Render Disk migration: seed existing trades on first deploy ──
try:
    from migrate_seed import run_seed
    run_seed(_db_path)
except Exception as _seed_err:
    print(f"[migrate_seed] skipped: {_seed_err}")
_demo_trader = DemoTrader(db=_demo_db)

# ── トレードルール定義 ──
TRADE_RULES = {
    "rule_version": "1.0",
    "description": "FX AI Trader シグナルベースのデモトレードルール",
    "rules": [
        "① エントリーは本ツールのAIシグナル（BUY/SELL）が発生した場合のみ行う",
        "② 確度(confidence)が閾値以上の場合のみエントリー（初期値55%、学習で調整）",
        "③ SR水平線の根拠があるシグナルを優先（dual_sr_bounce > dual_sr_breakout > ema_cross）",
        "④ Layer0（取引禁止時間帯）が禁止の場合はエントリーしない",
        "⑤ Layer1（大口バイアス）と逆方向のシグナルはエントリーしない",
        "⑥ SL/TPはツールが算出した値を使用（学習エンジンによる微調整のみ許容）",
        "⑦ シグナルが反転した場合は即座にポジションクローズ",
        "⑧ 同時保有は最大1ポジション",
        "⑨ 高ボラレジーム(HIGH_VOL)では全シグナルWAIT",
        "⑩ 学習エンジンが除外したエントリータイプ・時間帯では取引しない",
    ],
    "learning_policy": [
        "A. 失敗トレードの原因分析が最優先（なぜ負けたか→どのパラメータが原因か）",
        "B. 勝率・EV・SLヒット率からパラメータを自動調整",
        "C. エントリータイプ別・時間帯別・レジーム別の勝率を追跡",
        "D. 低勝率のエントリータイプや時間帯は自動除外",
        "E. 調整履歴は全てDBに記録（監査可能）",
        "F. 最小サンプル10件未満では調整しない（過学習防止）",
    ],
}


@app.route("/healthz")
def healthz():
    """Renderヘルスチェック用 — スレッド生存確認 + 自動復旧トリガー + フォールバックtick"""
    try:
        status = _demo_trader.get_status()  # self-healing内蔵
        # スレッドが死んでいる場合、リクエスト駆動でtick実行
        _demo_trader.request_tick()
        return jsonify({
            "status": "ok",
            "main_loop": status.get("main_loop_alive"),
            "watchdog": status.get("watchdog_alive"),
            "sltp": status.get("sltp_checker_active"),
            "tick_counts": status.get("tick_counts"),
            "restarts": status.get("main_loop_restarts"),
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/api/demo/status")
def api_demo_status():
    try:
        status = _demo_trader.get_status()
        # スレッドが死んでいる場合、リクエスト駆動でtick実行
        _demo_trader.request_tick()
        status["trade_rules"] = TRADE_RULES
        return jsonify(status)
    except Exception as e:
        print(f"[api_demo_status] Error: {e}", flush=True)
        return jsonify({
            "running": False, "modes": {},
            "params": {}, "open_trades": [], "stats": {},
            "recent_log": [], "error": str(e),
        })


@app.route("/api/demo/logs")
def api_demo_logs():
    """全ログ履歴を返す（過去セッション含む）"""
    try:
        logs = _demo_trader.get_all_logs()
        return jsonify({"logs": logs, "count": len(logs)})
    except Exception as e:
        return jsonify({"logs": [], "count": 0, "error": str(e)})


@app.route("/api/demo/start", methods=["POST"])
def api_demo_start():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", request.args.get("mode", "daytrade"))
    result = _demo_trader.start(mode=mode)
    return jsonify(result)


@app.route("/api/demo/stop", methods=["POST"])
def api_demo_stop():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", request.args.get("mode", None))
    result = _demo_trader.stop(mode=mode)
    return jsonify(result)


@app.route("/api/demo/restart", methods=["POST"])
def api_demo_restart():
    """全モード強制再起動"""
    results = {}
    for _mode in ["scalp", "daytrade", "daytrade_1h", "swing"]:
        # 一旦停止してから再起動
        _demo_trader.stop(mode=_mode)
        import time as _t; _t.sleep(0.5)
        results[_mode] = _demo_trader.start(mode=_mode)
    return jsonify({"status": "restarted", "modes": results})


@app.route("/api/demo/close", methods=["POST"])
def api_demo_close_trade():
    """手動でポジションをクローズ
    Body JSON:
        trade_id (str): クローズ対象のtrade_id — 指定時は1件クローズ
        mode (str): 指定時はそのモードの全OPENをクローズ
        all (bool): true指定で全OPENをクローズ
    """
    data = request.get_json(silent=True) or {}
    trade_id = data.get("trade_id")
    mode = data.get("mode")
    close_all = data.get("all", False)

    price = _demo_trader._get_realtime_price()
    if price <= 0:
        return jsonify({"error": "現在価格を取得できません"}), 500

    open_trades = _demo_db.get_open_trades()
    if trade_id:
        targets = [t for t in open_trades if t["trade_id"] == trade_id]
    elif mode:
        targets = [t for t in open_trades if t.get("mode") == mode]
    elif close_all:
        targets = open_trades
    else:
        return jsonify({"error": "trade_id, mode, or all を指定してください"}), 400

    results = []
    for t in targets:
        r = _demo_db.close_trade(t["trade_id"], price, close_reason="MANUAL_CLOSE")
        if "error" not in r:
            # OANDA連携: 手動クローズもミラー
            _demo_trader._oanda.close_trade(t["trade_id"], reason="MANUAL_CLOSE")
            _demo_trader._add_log(
                f"🔴 手動クローズ [{t.get('mode','')}]: {t['direction']} @ {t['entry_price']:.3f} → "
                f"{price:.3f} | PnL {r.get('pnl_pips',0):+.1f}pip | ID: {t['trade_id']}"
            )
        results.append(r)

    return jsonify({"closed": len(results), "results": results})


@app.route("/api/oanda/accounts")
def api_oanda_accounts():
    """OANDA APIトークンでアクセス可能な全アカウント一覧"""
    ok, data = _demo_trader._oanda._client.list_accounts()
    if ok:
        return jsonify(data)
    return jsonify({"error": data}), 500


@app.route("/api/oanda/status")
def api_oanda_status():
    """OANDA連携ステータス + アカウント情報"""
    status = _demo_trader._oanda.status
    if status.get("active"):
        status["account"] = _demo_trader._oanda.get_account_info()
    status["data_sources"] = dict(_last_data_source)
    return jsonify(status)


@app.route("/api/oanda/modes", methods=["GET", "POST"])
def api_oanda_modes():
    """OANDA連携モード取得・切替
    GET:  現在の連携モード一覧を返す
    POST: {"modes": ["scalp", "daytrade"]} で連携モードを切替
          {"toggle": "scalp"} で単一モードをON/OFF切替
    """
    bridge = _demo_trader._oanda
    if request.method == "GET":
        return jsonify({
            "allowed_modes": sorted(bridge._allowed_modes) if bridge._allowed_modes else [],
            "active": bridge.active,
        })

    data = request.get_json(silent=True) or {}

    # toggle: 単一モードのON/OFF
    if "toggle" in data:
        mode = data["toggle"]
        if mode in bridge._allowed_modes:
            bridge._allowed_modes.discard(mode)
            action = "OFF"
        else:
            bridge._allowed_modes.add(mode)
            action = "ON"
        _demo_trader._add_log(f"🔗 OANDA連携 {mode} → {action}")
        return jsonify({
            "toggled": mode,
            "action": action,
            "allowed_modes": sorted(bridge._allowed_modes),
        })

    # modes: 一括設定
    if "modes" in data:
        bridge._allowed_modes = set(data["modes"])
        _demo_trader._add_log(f"🔗 OANDA連携モード変更 → {sorted(bridge._allowed_modes)}")
        return jsonify({
            "allowed_modes": sorted(bridge._allowed_modes),
        })

    return jsonify({"error": "toggle or modes required"}), 400


@app.route("/api/demo/trades")
def api_demo_trades():
    """取引履歴API — 期間・モードで絞り込み可能
    Query params:
        limit (int): 最大件数 (default 50)
        offset (int): ページング用オフセット
        status: "open" | "closed" | "all" (default "all")
        date_from: 開始日 (YYYY-MM-DD)
        date_to: 終了日 (YYYY-MM-DD)
        mode: "scalp" | "daytrade" | "daytrade_1h" | "swing"
    """
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    status_filter = request.args.get("status", "all")
    date_from = request.args.get("date_from")  # YYYY-MM-DD
    date_to = request.args.get("date_to")      # YYYY-MM-DD
    mode_filter = request.args.get("mode")      # scalp / daytrade / daytrade_1h / swing

    if status_filter == "open":
        trades = _demo_db.get_open_trades()
        # open trades にもmode絞り込み適用
        if mode_filter:
            trades = [t for t in trades if t.get("mode") == mode_filter]
    elif status_filter == "closed":
        trades = _demo_db.get_closed_trades(limit=limit, offset=offset,
                                            date_from=date_from, date_to=date_to,
                                            mode=mode_filter)
    else:
        open_t = _demo_db.get_open_trades()
        if mode_filter:
            open_t = [t for t in open_t if t.get("mode") == mode_filter]
        closed_t = _demo_db.get_closed_trades(limit=limit, offset=offset,
                                              date_from=date_from, date_to=date_to,
                                              mode=mode_filter)
        trades = open_t + closed_t

    return jsonify({"trades": trades, "count": len(trades)})


@app.route("/api/demo/stats")
def api_demo_stats():
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    mode_filter = request.args.get("mode")
    stats = _demo_db.get_stats(date_from=date_from, date_to=date_to, mode=mode_filter)
    stats["_db_path"] = _db_path
    return jsonify(stats)


@app.route("/api/demo/equity")
def api_demo_equity():
    """累積P/Lカーブ用データ"""
    closed = _demo_db.get_all_closed()
    cumulative = 0.0
    curve = []
    for t in closed:
        cumulative += t.get("pnl_pips", 0)
        curve.append({
            "time": t.get("exit_time", t.get("entry_time", "")),
            "pnl": t.get("pnl_pips", 0),
            "cumulative": round(cumulative, 1),
            "trade_id": t.get("trade_id", ""),
            "direction": t.get("direction", ""),
            "entry_type": t.get("entry_type", ""),
            "outcome": t.get("outcome", ""),
            "tf": t.get("tf", ""),
        })
    return jsonify({"curve": curve, "total_pnl": round(cumulative, 1), "count": len(curve)})


@app.route("/api/chart-data")
def api_chart_data():
    """OHLCVキャンドルデータ（分析ページ用）"""
    tf = request.args.get("tf", "15m")
    period_map = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "30d", "4h": "60d", "1d": "120d"}
    period = period_map.get(tf, "5d")
    try:
        df = fetch_ohlcv("USDJPY=X", period=period, interval=tf)
        if df is None or df.empty:
            return jsonify({"candles": [], "error": "No data"})
        candles = []
        for idx, row in df.iterrows():
            ts = int(idx.timestamp()) if hasattr(idx, 'timestamp') else 0
            candles.append({
                "time": ts,
                "open": round(float(row["Open"]), 3),
                "high": round(float(row["High"]), 3),
                "low": round(float(row["Low"]), 3),
                "close": round(float(row["Close"]), 3),
            })
        return jsonify({"candles": candles, "tf": tf, "count": len(candles)})
    except Exception as e:
        return jsonify({"candles": [], "error": str(e)})


@app.route("/api/demo/params", methods=["GET", "POST"])
def api_demo_params():
    if request.method == "POST":
        updates = request.get_json() or {}
        result = _demo_trader.set_params(updates)
        return jsonify(result)
    return jsonify(_demo_trader.get_params())


@app.route("/api/demo/learning")
def api_demo_learning():
    # 手動学習トリガー or 履歴取得
    trigger = request.args.get("run", "false").lower() == "true"
    mode = request.args.get("mode")  # daytrade / scalp / swing / None(全モード)
    if trigger:
        result = _demo_trader.run_learning(mode=mode)
        return jsonify(result)
    # 履歴のみ — モード別分析データ + 過去の学習結果
    results = {}
    for m in ["daytrade", "scalp", "swing"]:
        results[m] = {
            "analysis": _demo_db.get_trades_for_learning(mode=m),
            "history": _demo_db.get_learning_results(mode=m, limit=20),
        }
    adjustments = _demo_db.get_adjustments(limit=30)
    return jsonify({
        "adjustments": adjustments,
        "by_mode": results,
        "current_params": _demo_trader.get_params(),
    })


@app.route("/api/demo/rules")
def api_demo_rules():
    return jsonify(TRADE_RULES)


@app.route("/api/demo/daily-review")
def api_demo_daily_review():
    """デイリーレビュー: 手動実行 or 履歴取得"""
    run = request.args.get("run", "false").lower() == "true"
    target_date = request.args.get("date")
    mode = request.args.get("mode")

    if run:
        result = _demo_trader.run_daily_review(target_date=target_date)
        return jsonify(result)

    # 履歴取得
    reviews = _demo_trader.get_daily_reviews(limit=30, mode=mode)
    return jsonify({"reviews": reviews, "count": len(reviews)})


@app.route("/api/demo/algo-changes")
def api_demo_algo_changes():
    """アルゴリズム変更ログ"""
    limit = int(request.args.get("limit", 50))
    changes = _demo_trader.get_algo_changes(limit=limit)
    return jsonify({"changes": changes, "count": len(changes)})


_auto_start_done = False  # 二重起動防止フラグ

def _auto_start_trader():
    """サーバー起動時に全モード自動起動（Render再起動対策）"""
    global _auto_start_done
    if _auto_start_done:
        print("[AutoStart] Already executed — skipping duplicate", flush=True)
        return
    _auto_start_done = True

    import time as _time
    print(f"[AutoStart] Waiting 10s for initialization... (PID={os.getpid()})", flush=True)
    _time.sleep(10)  # Gunicorn/Flask完全初期化を待つ
    _all_modes = ["scalp", "daytrade", "daytrade_1h", "swing"]
    for _mode in _all_modes:
        try:
            result = _demo_trader.start(mode=_mode)
            print(f"[AutoStart] {_mode} → {result.get('status', 'unknown')}", flush=True)
            _time.sleep(3)  # モード間で間隔を空ける
        except Exception as _e:
            print(f"[AutoStart] {_mode} failed: {_e}", flush=True)
            import traceback; traceback.print_exc()

    # 起動確認: 15秒後に全スレッドの状態を検証
    _time.sleep(15)
    _status = _demo_trader.get_status()
    print(f"[AutoStart/Verify] main_loop={_status.get('main_loop_alive')} "
          f"main_status={_status.get('main_loop_status')} "
          f"watchdog={_status.get('watchdog_alive')} "
          f"sltp={_status.get('sltp_checker_active')} "
          f"ticks={_status.get('tick_counts')}", flush=True)
    for _mode in _all_modes:
        try:
            if not _demo_trader.is_running(mode=_mode):
                print(f"[AutoStart/Verify] {_mode} not running — force restarting", flush=True)
                _demo_trader.start(mode=_mode)
        except Exception as _e:
            print(f"[AutoStart/Verify] {_mode} check failed: {_e}", flush=True)

# Render/Gunicorn環境では __name__ != "__main__" なので、
# モジュール読み込み時に自動起動スレッドを開始
import threading as _threading_mod
_auto_start_thread = _threading_mod.Thread(target=_auto_start_trader, daemon=True)
_auto_start_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 55)
    print("  FX AI Trader v5  —  USD/JPY Swing Day Trade")
    print(f"  http://localhost:{port}")
    print("=" * 55)
    app.run(debug=False, port=port, host="0.0.0.0")
