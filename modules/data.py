"""
FX AI Trader — Data fetching module
=====================================
OHLCV data retrieval from multiple sources:
  - OANDA v20 API (primary — lowest latency)
  - Massive Market Data API (secondary)
  - TwelveData API (tertiary)
  - yfinance (fallback)
"""

import os
import threading
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone, timedelta

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
# (2026-04-05 perf) TTL延長: ネットワーク負荷40%削減
# 旧: 1m=10s(40%hit) 5m=15s 15m=45s(33%hit) → 新: 80%+ヒット率達成
_TF_CACHE_TTL = {
    "1m": 20, "5m": 30, "15m": 60, "30m": 90,
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
    "EURUSD=X": "EUR/USD",
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
# ── yfinance Ticker キャッシュ (2026-04-05 perf) ──
# 旧: 毎回 yf.Ticker() 生成 → 新: シンボル別キャッシュで HTTP セッション再利用
_yf_ticker_cache: dict = {}

def _fetch_raw(symbol: str, period: str, interval: str) -> pd.DataFrame:
    # yfinance用シンボル変換: XAU/USD → GC=F (COMEX金先物, スポットの良好な代替)
    _yf_symbol = symbol
    if "XAU" in symbol.upper():
        _yf_symbol = "GC=F"
    if _yf_symbol not in _yf_ticker_cache:
        _yf_ticker_cache[_yf_symbol] = yf.Ticker(_yf_symbol)
    ticker = _yf_ticker_cache[_yf_symbol]
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
        "EURUSD=X": "C:EURUSD",
        "EURJPY=X": "C:EURJPY",
        "GBPJPY=X": "C:GBPJPY",
        "GBPUSD=X": "C:GBPUSD",
        "EURGBP=X": "C:EURGBP",
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
#  OANDA v20 candle fetch
# ═══════════════════════════════════════════════════════
# yfinance interval → OANDA granularity
_OANDA_GRANULARITY = {
    "1m": "M1", "5m": "M5", "15m": "M15", "30m": "M30",
    "1h": "H1", "4h": "H4", "1d": "D", "1wk": "W", "1mo": "M",
}
_OANDA_SYMBOLS = {
    "USDJPY=X": "USD_JPY", "JPY=X": "USD_JPY",
    "EURUSD=X": "EUR_USD", "EURJPY=X": "EUR_JPY",
    "GBPJPY=X": "GBP_JPY", "GBPUSD=X": "GBP_USD",
    "EURGBP=X": "EUR_GBP",
    "XAUUSD=X": "XAU_USD",  # Gold
}

# OANDA共有クライアント (遅延初期化)
_oanda_client = None
_oanda_client_lock = threading.Lock()


def _get_oanda_client():
    """遅延初期化: OANDA_TOKEN設定時のみクライアント生成"""
    global _oanda_client
    if _oanda_client is not None:
        return _oanda_client
    with _oanda_client_lock:
        if _oanda_client is not None:
            return _oanda_client
        if os.environ.get("OANDA_TOKEN"):
            from modules.oanda_client import OandaClient
            _oanda_client = OandaClient()
        return _oanda_client


def fetch_ohlcv_oanda(symbol: str, interval: str, days: int) -> pd.DataFrame:
    """
    OANDA v20 Candles APIからOHLCVデータを取得。
    USD/JPYのみ対応。5000本/リクエスト上限をページネーションで対応。
    1m/30日なら約23000本 → 5リクエストで取得。
    """
    client = _get_oanda_client()
    if not client or not client.configured:
        raise ValueError("OANDA client not configured")

    instrument = _OANDA_SYMBOLS.get(symbol)
    if not instrument:
        raise ValueError(f"Symbol {symbol} not in OANDA map")

    granularity = _OANDA_GRANULARITY.get(interval)
    if not granularity:
        raise ValueError(f"Interval {interval} not supported by OANDA")

    # 必要なバー数を計算
    _bars_per_day = {"1m": 1440, "5m": 288, "15m": 96, "30m": 48,
                     "1h": 24, "4h": 6, "1d": 1, "1wk": 1, "1mo": 1}
    needed = int(days * _bars_per_day.get(interval, 24) * 0.6)

    all_candles = []

    if needed <= 5000:
        # 1リクエストで足りる場合
        count = min(max(needed, 200), 5000)
        ok, data = client.get_candles(
            instrument=instrument, granularity=granularity,
            count=count, price="M",
        )
        if not ok:
            raise ValueError(f"OANDA candles: {data.get('message', 'unknown')}")
        all_candles = data.get("candles", [])
    else:
        # ページネーション: from_time/to_time で分割取得
        from datetime import timedelta as _td
        _now = datetime.now(timezone.utc)
        _start = _now - _td(days=days)
        _chunk_bars = 5000
        _secs_per_bar = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800,
                         "1h": 3600, "4h": 14400, "1d": 86400}.get(interval, 60)
        _chunk_secs = _chunk_bars * _secs_per_bar
        _cursor = _start
        _max_pages = 20  # 安全上限

        for _page in range(_max_pages):
            _from = _cursor.strftime("%Y-%m-%dT%H:%M:%SZ")
            _to_dt = min(_cursor + _td(seconds=_chunk_secs), _now)
            _to = _to_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            ok, data = client.get_candles(
                instrument=instrument, granularity=granularity,
                price="M", from_time=_from, to_time=_to,
            )
            if ok:
                chunk = data.get("candles", [])
                all_candles.extend(chunk)
                print(f"[OANDA/{interval}] page {_page+1}: {len(chunk)} bars ({_from[:10]}~{_to[:10]})")
            else:
                print(f"[OANDA/{interval}] page {_page+1} failed: {data.get('message','?')}")

            _cursor = _to_dt
            if _cursor >= _now:
                break

    if not all_candles:
        raise ValueError("OANDA candles: empty response")

    rows = []
    times = []
    for c in all_candles:
        mid = c.get("mid", {})
        if not mid:
            continue
        rows.append({
            "Open":   float(mid["o"]),
            "High":   float(mid["h"]),
            "Low":    float(mid["l"]),
            "Close":  float(mid["c"]),
            "Volume": float(c.get("volume", 0)),
        })
        times.append(pd.Timestamp(c["time"]))

    if not rows:
        raise ValueError("OANDA candles: no valid candle data")

    idx = pd.DatetimeIndex(times)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")

    df = pd.DataFrame(rows, index=idx)
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()
    print(f"[OANDA/{interval}] Total: {len(df)} bars for {days}d")
    return df.dropna()


def fetch_ohlcv_range(symbol: str, from_time: str, to_time: str,
                      interval: str = "1m") -> pd.DataFrame:
    """OANDA APIで期間指定のOHLCVデータを取得（チャンクBT用）"""
    client = _get_oanda_client()
    if not client or not client.configured:
        raise ValueError("OANDA client not configured")

    instrument = _OANDA_SYMBOLS.get(symbol)
    if not instrument:
        raise ValueError(f"Symbol {symbol} not in OANDA map")

    granularity = _OANDA_GRANULARITY.get(interval)
    if not granularity:
        raise ValueError(f"Interval {interval} not supported by OANDA")

    _secs_per_bar = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800,
                     "1h": 3600, "4h": 14400, "1d": 86400}.get(interval, 60)
    _chunk_secs = 5000 * _secs_per_bar

    _from_dt = datetime.fromisoformat(from_time.replace("Z", "+00:00"))
    _to_dt = datetime.fromisoformat(to_time.replace("Z", "+00:00"))

    all_candles = []
    _cursor = _from_dt
    for _page in range(20):
        _f = _cursor.strftime("%Y-%m-%dT%H:%M:%SZ")
        _t_dt = min(_cursor + timedelta(seconds=_chunk_secs), _to_dt)
        _t = _t_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        ok, data = client.get_candles(
            instrument=instrument, granularity=granularity,
            price="M", from_time=_f, to_time=_t,
        )
        if ok:
            chunk = data.get("candles", [])
            all_candles.extend(chunk)

        _cursor = _t_dt
        if _cursor >= _to_dt:
            break

    if not all_candles:
        raise ValueError("OANDA range: empty")

    rows, times = [], []
    for c in all_candles:
        mid = c.get("mid", {})
        if not mid: continue
        rows.append({
            "Open": float(mid["o"]), "High": float(mid["h"]),
            "Low": float(mid["l"]), "Close": float(mid["c"]),
            "Volume": float(c.get("volume", 0)),
        })
        times.append(pd.Timestamp(c["time"]))

    if not rows:
        raise ValueError("OANDA range: no valid data")

    idx = pd.DatetimeIndex(times)
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")

    df = pd.DataFrame(rows, index=idx)
    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()
    print(f"[OANDA/range/{interval}] {len(df)} bars ({from_time[:10]}~{to_time[:10]})")
    return df.dropna()


def fetch_oanda_price(instrument: str = "USD_JPY") -> float:
    """OANDAからリアルタイム価格(mid)を取得。失敗時は0を返す。"""
    client = _get_oanda_client()
    if not client or not client.configured:
        return 0
    try:
        ok, data = client.get_price(instrument)
        if ok:
            prices = data.get("prices", [])
            if prices:
                bid = float(prices[0].get("bids", [{}])[0].get("price", 0))
                ask = float(prices[0].get("asks", [{}])[0].get("price", 0))
                if bid > 0 and ask > 0:
                    # JPYペア/Gold(XAU)は3桁、それ以外は5桁
                    decimals = 3 if ("JPY" in instrument or "XAU" in instrument) else 5
                    return round((bid + ask) / 2, decimals)
    except Exception:
        pass
    return 0


def fetch_oanda_bid_ask(instrument: str = "USD_JPY") -> dict:
    """OANDAからリアルタイムbid/askを取得。スプレッド計算用。
    Returns: {"bid": float, "ask": float, "spread": float(pips), "mid": float}
             失敗時は空dict。
    """
    client = _get_oanda_client()
    if not client or not client.configured:
        return {}
    try:
        ok, data = client.get_price(instrument)
        if ok:
            prices = data.get("prices", [])
            if prices:
                bid = float(prices[0].get("bids", [{}])[0].get("price", 0))
                ask = float(prices[0].get("asks", [{}])[0].get("price", 0))
                if bid > 0 and ask > 0:
                    decimals = 3 if ("JPY" in instrument or "XAU" in instrument) else 5
                    pip_mult = 100 if ("JPY" in instrument or "XAU" in instrument) else 10000
                    spread_pips = round((ask - bid) * pip_mult, 2)
                    return {
                        "bid": round(bid, decimals),
                        "ask": round(ask, decimals),
                        "spread": spread_pips,
                        "mid": round((bid + ask) / 2, decimals),
                    }
    except Exception:
        pass
    return {}


# ═══════════════════════════════════════════════════════
#  Realtime price patch
# ═══════════════════════════════════════════════════════
def _rt_patch(df: pd.DataFrame, symbol: str, interval: str) -> pd.DataFrame:
    """
    価格キャッシュ(_price_cache)が新鮮なら、最終足のClose/High/Lowをリアルタイム更新。
    OHLCVを再取得せずに現在足を常に最新化するため、足型ズレを大幅に削減する。
    USD/JPY の 1m/5m のみ対象。
    """
    if interval not in ("1m", "5m") or symbol not in _OANDA_SYMBOLS:
        return df
    if len(df) == 0:
        return df

    price = None

    # (1) 既存の _price_cache (TwelveData等) を確認
    with _cache_lock:
        pc = dict(_price_cache)
    if pc.get("ts"):
        ts = pc["ts"]
        now = datetime.now(timezone.utc) if ts.tzinfo else datetime.now()
        age = (now - ts).total_seconds()
        if age <= 10:
            try:
                price = float(pc["data"]["price"])
            except (KeyError, TypeError, ValueError):
                pass

    # (2) _price_cache が古い場合、OANDAからリアルタイム価格取得
    if price is None and symbol in _OANDA_SYMBOLS:
        oanda_instrument = _OANDA_SYMBOLS[symbol]
        oanda_price = fetch_oanda_price(oanda_instrument)
        if oanda_price > 0:
            price = oanda_price

    if price is None:
        return df

    last = df.index[-1]
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
    # スレッドセーフなキャッシュ読取り (2026-04-05 audit fix)
    with _cache_lock:
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

    # -- (0) OANDA v20 最優先: USD/JPY, EUR/USD 全TF (最低レイテンシ) --
    if (df is None and
            os.environ.get("OANDA_TOKEN") and
            symbol in _OANDA_SYMBOLS and
            interval in _OANDA_GRANULARITY):
        try:
            df = fetch_ohlcv_oanda(symbol, interval, days)
            if df is not None and len(df) >= min_bars:
                _last_data_source[interval] = "oanda"
                print(f"[OANDA/{interval}] {len(df)}本取得 (期待{int(expected)})")
            else:
                actual = len(df) if df is not None else 0
                print(f"[OANDA/{interval}] {actual}本 < 最低{int(min_bars)}本 → フォールバック")
                df = None
        except Exception as e:
            print(f"[OANDA/{interval}] {e} → フォールバック")
            df = None

    # -- (1) Massive API: USDJPY/EURUSD の全TF --
    _MASSIVE_SYMBOLS = {"USDJPY=X", "JPY=X", "EURUSD=X"}
    _MASSIVE_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
    if (df is None and
            os.environ.get("MASSIVE_API_KEY") and
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
        try:
            df = _fetch_raw(symbol, period, interval)
            if df is not None and len(df) >= min_bars:
                _last_data_source[interval] = "yfinance"
            else:
                _actual = len(df) if df is not None else 0
                print(f"[yfinance/{interval}] {_actual}本 < {int(min_bars)}本 → 不十分")
                df = None
        except Exception as e:
            print(f"[yfinance/{interval}] fetch error: {e}")
            df = None

    # 全ソース失敗時: staleキャッシュがあれば返す (2026-04-05 audit fix)
    if df is None:
        with _cache_lock:
            if key in _data_cache:
                print(f"[fetch_ohlcv] ALL sources failed for {symbol}/{interval} → returning stale cache")
                return _data_cache[key][0].copy()
        raise ValueError(f"All data sources failed for {symbol}/{interval}")

    with _cache_lock:
        _data_cache[key] = (df, now)
        # キャッシュサイズ制限: 50エントリ超で最古を削除 (2026-04-05 audit fix)
        if len(_data_cache) > 50:
            _oldest = min(_data_cache, key=lambda k: _data_cache[k][1])
            del _data_cache[_oldest]
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
