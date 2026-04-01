"""
FX AI Trader — Data fetching module
=====================================
OHLCV data retrieval from multiple sources:
  - Massive Market Data API (primary)
  - TwelveData API (secondary)
  - yfinance (fallback)
"""

import os
import threading
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone

from modules.config import CACHE_TTL

# スレッドセーフティ用ロック
_cache_lock = threading.Lock()

# ═══════════════════════════════════════════════════════
#  Module-level caches and state
# ═══════════════════════════════════════════════════════
_data_cache:  dict = {}   # (symbol,interval,period) -> (df, timestamp)
_price_cache: dict = {}   # TwelveData realtime price cache
_last_data_source: dict = {}  # interval -> source name

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
    "1m": 500, "5m": 600, "15m": 600, "30m": 800, "1h": 900,
}


# ═══════════════════════════════════════════════════════
#  Raw fetch (yfinance)
# ═══════════════════════════════════════════════════════
def _fetch_raw(symbol: str, period: str, interval: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=True, timeout=30)
    # DatetimeIndex であることを保証してからtz操作
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    elif getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_convert("UTC")
    return df.dropna()


# ═══════════════════════════════════════════════════════
#  TwelveData fetch
# ═══════════════════════════════════════════════════════
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
                f"&outputsize={size}&dp=5&timezone=UTC&format=JSON")

    req = _ur.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Authorization": f"apikey {api_key}",
    })
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


# ═══════════════════════════════════════════════════════
#  Massive Market Data fetch
# ═══════════════════════════════════════════════════════
def fetch_ohlcv_massive(symbol: str, interval: str, days: int) -> pd.DataFrame:
    """
    Massive Market Data APIからOHLCVデータを取得。
    USDJPYのみ対応 (C:USDJPY形式)。
    ページネーション対応で指定日数分を確実に取得。

    interval: "1m","5m","15m","30m","1h","4h","1d"
    days: 取得日数
    """
    import urllib.request as _ur, json as _js, time as _time

    api_key = os.environ.get("MASSIVE_API_KEY", "")
    if not api_key:
        raise ValueError("MASSIVE_API_KEY not set")

    # Massive ticker format
    _SYMBOL_MAP = {
        "USDJPY=X": "C:USDJPY",
        "JPY=X":    "C:USDJPY",
    }
    massive_ticker = _SYMBOL_MAP.get(symbol)
    if not massive_ticker:
        raise ValueError(f"Symbol {symbol} not supported by Massive API")

    # interval -> (multiplier, timespan)
    _IV_MAP = {
        "1m":  (1,  "minute"),
        "5m":  (5,  "minute"),
        "15m": (15, "minute"),
        "30m": (30, "minute"),
        "1h":  (1,  "hour"),
        "4h":  (4,  "hour"),
        "1d":  (1,  "day"),
    }
    if interval not in _IV_MAP:
        raise ValueError(f"Interval {interval} not supported")
    mult, timespan = _IV_MAP[interval]

    # Date range
    from datetime import timedelta
    end_dt   = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days + 3)  # +3日バッファ
    date_from = start_dt.strftime("%Y-%m-%d")
    date_to   = end_dt.strftime("%Y-%m-%d")

    base_url = (f"https://api.massive.com/v2/aggs/ticker/{massive_ticker}"
                f"/range/{mult}/{timespan}/{date_from}/{date_to}")

    all_rows = []
    url = base_url
    params = "?adjusted=true&sort=asc&limit=50000"
    _headers = {"User-Agent": "Mozilla/5.0", "Authorization": f"Bearer {api_key}"}
    max_pages = 10  # 最大ページ数（無限ループ防止）

    for page in range(max_pages):
        req = _ur.Request(url + params, headers=_headers)
        try:
            with _ur.urlopen(req, timeout=45) as r:
                data = _js.load(r)
        except Exception as e:
            if page == 0:
                raise
            break  # ページネーション中のエラーは中断

        results = data.get("results", [])
        if not results:
            break
        all_rows.extend(results)

        # ページネーション
        next_url = data.get("next_url")
        if not next_url:
            break
        # next_urlにはパラメータが含まれている場合がある
        url = next_url
        params = ""  # next_urlに既にパラメータが含まれる（APIキーはヘッダーで送信）
        _time.sleep(0.1)  # レート制限対策

    if not all_rows:
        raise ValueError(f"Massive API: no data returned for {massive_ticker} {interval}")

    # DataFrame変換 (Massive -> pandas OHLCV形式)
    rows = [{
        "Open":   float(r["o"]),
        "High":   float(r["h"]),
        "Low":    float(r["l"]),
        "Close":  float(r["c"]),
        "Volume": float(r.get("v", 0)),
        "vwap":   float(r.get("vw", r["c"])),
    } for r in all_rows]

    idx = pd.DatetimeIndex(
        pd.to_datetime([r["t"] for r in all_rows], unit="ms", utc=True)
    )
    df = pd.DataFrame(rows, index=idx)
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()
    return df.dropna()


# ═══════════════════════════════════════════════════════
#  Realtime price patch
# ═══════════════════════════════════════════════════════
def _rt_patch(df: pd.DataFrame, symbol: str, interval: str) -> pd.DataFrame:
    """
    価格キャッシュ(_price_cache)が新鮮なら、最終足のClose/High/Lowをリアルタイム更新。
    OHLCVを再取得せずに現在足を常に最新化するため、足型ズレを大幅に削減する。
    USD/JPY の 1m/5m のみ対象。
    """
    if interval not in ("1m", "5m") or symbol not in _TD_SYMBOL_MAP:
        return df
    if len(df) == 0:
        return df
    with _cache_lock:
        pc = dict(_price_cache)  # スナップショットをコピー
    if not pc.get("ts"):
        return df
    ts = pc["ts"]
    # naive/aware統一: tsがawareならnowもaware、naiveならnaive
    now = datetime.now(timezone.utc) if ts.tzinfo else datetime.now()
    age = (now - ts).total_seconds()
    if age > 10:
        return df
    try:
        price = float(pc["data"]["price"])
    except (KeyError, TypeError, ValueError):
        return df
    last  = df.index[-1]
    df.at[last, "Close"] = price
    df.at[last, "High"]  = max(float(df.at[last, "High"]), price)
    df.at[last, "Low"]   = min(float(df.at[last, "Low"]),  price)
    return df


# ═══════════════════════════════════════════════════════
#  Main OHLCV fetch (with multi-source fallback)
# ═══════════════════════════════════════════════════════
def fetch_ohlcv(symbol="USDJPY=X", period="5d", interval="1m") -> pd.DataFrame:
    key = (symbol, interval, period)
    now = datetime.now(timezone.utc)
    ttl = _TF_CACHE_TTL.get(interval, CACHE_TTL)
    if key in _data_cache:
        cached_df, ts = _data_cache[key]
        # naive/aware統一
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if (now - ts).total_seconds() < ttl:
            return _rt_patch(cached_df.copy(), symbol, interval)

    df = None

    # period文字列から日数を計算
    def _period_to_days(p: str) -> int:
        p = p.strip()
        if p.endswith("d"):   return int(p[:-1])
        if p.endswith("mo"):  return int(p[:-2]) * 30
        if p.endswith("y"):   return int(p[:-1]) * 365
        if p == "max":        return 365 * 8
        return 90

    days = _period_to_days(period)

    # -- データ十分性の閾値計算（全ソース共通）--
    _bars_per_day = {"1m": 1440, "5m": 288, "15m": 96, "30m": 48,
                     "1h": 24, "4h": 6, "1d": 1}
    expected = days * _bars_per_day.get(interval, 24) * 0.55  # FX=24h x 55%稼働
    min_bars = max(100, expected * 0.30)

    # -- (1) Massive API優先: USDJPY の全TF --
    _MASSIVE_SYMBOLS = {"USDJPY=X", "JPY=X"}
    _MASSIVE_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
    if (os.environ.get("MASSIVE_API_KEY") and
            symbol in _MASSIVE_SYMBOLS and
            interval in _MASSIVE_INTERVALS):
        try:
            df = fetch_ohlcv_massive(symbol, interval, days)
            if df is not None and len(df) >= min_bars:
                _last_data_source[interval] = "massive"
                print(f"[Massive/{interval}] {len(df)}本取得 (期待{int(expected)})")
            else:
                actual = len(df) if df is not None else 0
                print(f"[Massive/{interval}] {actual}本 < 最低{int(min_bars)}本 → フォールバック")
                df = None
        except Exception as e:
            print(f"[Massive/{interval}] {e} → フォールバック")
            df = None

    # -- (2) TwelveData: USD/JPY の短期TFのみ --
    if (df is None and
            os.environ.get("TWELVEDATA_API_KEY") and
            symbol in _TD_SYMBOL_MAP and
            interval in _TD_INTERVALS):
        try:
            df = fetch_ohlcv_twelvedata(symbol, interval)
            # TwelveDataも期待バー数の30%未満なら不足扱い
            if df is not None and len(df) >= min_bars:
                _last_data_source[interval] = "twelvedata"
                print(f"[TD/{interval}] {len(df)}本取得 (十分)")
            else:
                actual = len(df) if df is not None else 0
                print(f"[TD/{interval}] {actual}本 < {int(min_bars)}本 → yfinanceにフォールバック")
                df = None
        except Exception as e:
            print(f"[TD/{interval}] {e} → yfinanceにフォールバック")
            df = None

    # -- (3) フォールバック: yfinance --
    if df is None:
        df = _fetch_raw(symbol, period, interval)
        _last_data_source[interval] = "yfinance"

    _data_cache[key] = (df, now)
    return df.copy()


# ═══════════════════════════════════════════════════════
#  Resample
# ═══════════════════════════════════════════════════════
def resample_df(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return df.resample(rule).agg(
        Open=("Open","first"), High=("High","max"),
        Low=("Low","min"),    Close=("Close","last"),
        Volume=("Volume","sum")
    ).dropna()
