"""HTF (Higher Time Frame) Data Source — OANDA native H4/D1 fetcher

目的:
  従来 app.py で行っていた M5→H4/D1 の resample 生成を排除し、
  OANDA API から native H4/D1 candles を直接取得する。

背景 (2026-04-26 Edge Reset Phase 1):
  MTF gate が単一 TF ADX 判定 (η²<0.005) と resample 生成 H4/D1 で動いており、
  microstructure 喪失 + look-ahead 潜在リスクで「判定が出来ない」状態だった。
  本モジュールは OANDA native data を提供し、Phase 1.5 (MTF gate 復活) の
  前提となるクリーンなデータソースを整備する。

設計原則:
  - look-ahead protection: complete=False のバーは必ず drop
  - fail-graceful: OANDA 未設定や 429 時は None を返し、上位で fallback 可
  - 軽量キャッシュ: H4 は 5min TTL, D1 は 30min TTL (重複 fetch 防止)
  - 副作用なし: モジュール import 時点では何もしない

Out of scope (Phase 1.5 以降):
  - app.py:1195 get_htf_bias() / 1259 get_htf_bias_daytrade() への注入
  - mtf_regime_engine.py との接続
  - resample 由来 vs OANDA native の比較検証
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pandas as pd  # type: ignore
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

# ─── Cache (TTL ベース、process scope) ────────────────────────────────
_CACHE: dict[tuple[str, str, int], tuple[float, "pd.DataFrame"]] = {}
_CACHE_LOCK = threading.Lock()

# Granularity → cache TTL (秒)
_TTL = {
    "H4": 5 * 60,    # 4h bars: 5 min cache
    "D":  30 * 60,   # daily bars: 30 min cache
    "H1": 2 * 60,    # 1h bars: 2 min cache
    "M30": 60,       # 30m bars: 1 min cache
    "M15": 90,       # 15m bars: 90s cache (mtf cascade scalp)
    "M5":  60,       # 5m bars: 60s cache (mtf cascade scalp)
}

# OANDA 公式サポート granularity (一部抜粋)
_VALID_GRANULARITY = {"M1", "M5", "M15", "M30", "H1", "H4", "D", "W", "M"}


def _make_client():
    """Lazy-import OandaClient to avoid hard dependency at import time."""
    try:
        from modules.oanda_client import OandaClient
        return OandaClient()
    except Exception as e:
        logger.warning(f"[htf_data_source] OandaClient unavailable: {e}")
        return None


def _normalize_instrument(symbol: str) -> str:
    """yfinance 形式 ('USDJPY=X') を OANDA 形式 ('USD_JPY') に正規化.

    既に '_' 区切りなら大文字化のみ。
    """
    if not symbol:
        return symbol
    # upper 化を先に行うことで lowercase 入力 ('usdjpy=x') も処理可能
    s = symbol.upper().replace("=X", "")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    if len(s) == 7 and s[3] == "/":
        return f"{s[:3]}_{s[4:]}"
    return s


def _candles_to_df(candles: list, instrument: str, granularity: str) -> "Optional[pd.DataFrame]":
    """OANDA candles レスポンスを pandas DataFrame に変換.

    look-ahead 対策:
      - complete=False のバーは必ず drop (進行中 bar)
      - インデックスは UTC tz-aware
    """
    if not _HAS_PANDAS:
        return None
    if not candles:
        return None

    rows = []
    for c in candles:
        if not c.get("complete", False):
            continue  # 進行中バーは look-ahead リスクで除外
        try:
            t = c["time"]
            mid = c.get("mid") or {}
            row = {
                "time": t,
                "open": float(mid.get("o", 0)),
                "high": float(mid.get("h", 0)),
                "low":  float(mid.get("l", 0)),
                "close": float(mid.get("c", 0)),
                "volume": float(c.get("volume", 0)),
            }
            if row["open"] <= 0 or row["close"] <= 0:
                continue
            rows.append(row)
        except (KeyError, TypeError, ValueError) as e:
            logger.debug(f"[htf_data_source] skip malformed candle: {e}")
            continue

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time").sort_index()

    # Capitalized 列名も用意 (massive_signals.py 互換)
    df["Open"]   = df["open"]
    df["High"]   = df["high"]
    df["Low"]    = df["low"]
    df["Close"]  = df["close"]
    df["Volume"] = df["volume"]

    df.attrs["instrument"]  = instrument
    df.attrs["granularity"] = granularity
    df.attrs["fetched_at"]  = datetime.now(timezone.utc).isoformat()
    df.attrs["source"]      = "oanda_native"
    return df


def fetch_htf_candles(
    symbol: str,
    granularity: str = "H4",
    count: int = 100,
    *,
    use_cache: bool = True,
    client=None,
) -> "Optional[pd.DataFrame]":
    """OANDA から native H4/D1 candles を取得し DataFrame で返す.

    Parameters
    ----------
    symbol : str
        通貨ペア。'USDJPY=X' or 'USD_JPY' どちらも可。
    granularity : str
        OANDA granularity ('H4', 'D', 'H1', 'M30' 等)
    count : int
        取得本数 (1-5000、look-ahead 対策で完了バーのみ返るので実際は count-1 本前後)
    use_cache : bool
        TTL キャッシュを使用するか。テスト時 False。
    client : OandaClient or None
        DI 用 (テストで mock を渡すため)。None なら新規作成。

    Returns
    -------
    pd.DataFrame or None
        index: tz-aware UTC datetime
        columns: open/high/low/close/volume + capitalized aliases
        失敗時 None (上位で resample fallback など)
    """
    if not _HAS_PANDAS:
        logger.warning("[htf_data_source] pandas unavailable")
        return None

    if granularity not in _VALID_GRANULARITY:
        logger.error(f"[htf_data_source] invalid granularity: {granularity}")
        return None

    instrument = _normalize_instrument(symbol)
    cache_key = (instrument, granularity, count)
    ttl = _TTL.get(granularity, 5 * 60)

    # ─── Cache hit ─────────────────────────────────────────────────
    if use_cache:
        with _CACHE_LOCK:
            entry = _CACHE.get(cache_key)
        if entry is not None:
            ts, cached_df = entry
            if time.time() - ts < ttl:
                return cached_df

    # ─── Fetch ────────────────────────────────────────────────────
    cli = client if client is not None else _make_client()
    if cli is None or not getattr(cli, "configured", False):
        logger.info(f"[htf_data_source] OandaClient not configured, skipping {instrument} {granularity}")
        return None

    try:
        ok, payload = cli.get_candles(
            instrument=instrument,
            granularity=granularity,
            count=count,
            price="M",
        )
    except Exception as e:
        logger.error(f"[htf_data_source] fetch error {instrument} {granularity}: {e}")
        return None

    if not ok:
        logger.warning(f"[htf_data_source] OANDA returned error for {instrument} {granularity}: {payload}")
        return None

    candles = payload.get("candles") if isinstance(payload, dict) else None
    if not candles:
        logger.warning(f"[htf_data_source] empty candles for {instrument} {granularity}")
        return None

    df = _candles_to_df(candles, instrument, granularity)
    if df is None or df.empty:
        return None

    if use_cache:
        with _CACHE_LOCK:
            _CACHE[cache_key] = (time.time(), df)

    return df


def clear_cache() -> None:
    """テスト/手動再読込用。"""
    with _CACHE_LOCK:
        _CACHE.clear()


def cache_stats() -> dict:
    """診断用 (キー数と age)."""
    now = time.time()
    with _CACHE_LOCK:
        items = list(_CACHE.items())
    return {
        "size": len(items),
        "entries": [
            {
                "instrument": k[0],
                "granularity": k[1],
                "count": k[2],
                "age_s": round(now - ts, 1),
                "rows": len(df) if df is not None else 0,
            }
            for k, (ts, df) in items
        ],
    }


# ─── MTF Cascade features (15m + 5m) ─────────────────────────────────
# 用途: mtf_trend_follow_scalp / mtf_counter_trend_scalp
# 教科書的 MTF 階層を実装するため、M15(トレンド) + M5(方向) を
# OANDA native fetch + ta-lib indicators で前計算し、戦略から参照する。

def _compute_m15_features(df) -> Optional[dict]:
    """M15 candles から trend identification 用の features を抽出。

    Returns dict or None.
    """
    if df is None or len(df) < 30:
        return None
    try:
        from modules.indicators import add_indicators  # type: ignore
    except Exception as e:
        logger.warning(f"[htf_data_source] add_indicators import failed: {e}")
        return None
    try:
        df_i = add_indicators(df.copy())
    except Exception as e:
        logger.warning(f"[htf_data_source] M15 add_indicators failed: {e}")
        return None

    if len(df_i) < 5:
        return None

    last = df_i.iloc[-1]
    ema21_now = float(last.get("ema21", 0.0) or 0.0)
    ema21_3ago = float(df_i["ema21"].iloc[-4]) if "ema21" in df_i.columns and len(df_i) >= 4 else ema21_now
    ema_slope = ema21_now - ema21_3ago

    return {
        "close": float(last["Close"]),
        "ema9": float(last.get("ema9", 0.0) or 0.0),
        "ema21": ema21_now,
        "ema50": float(last.get("ema50", 0.0) or 0.0),
        "ema_slope": ema_slope,            # ema21 の 3 バー差分
        "adx": float(last.get("adx", 0.0) or 0.0),
        "rsi14": float(last.get("rsi", 50.0) or 50.0),
        "atr": float(last.get("atr", 0.0) or 0.0),
    }


def _compute_m5_features(df) -> Optional[dict]:
    """M5 candles から direction & exhaustion features を抽出。

    Returns dict or None.
    """
    if df is None or len(df) < 25:
        return None
    try:
        from modules.indicators import add_indicators  # type: ignore
    except Exception as e:
        logger.warning(f"[htf_data_source] add_indicators import failed: {e}")
        return None
    try:
        df_i = add_indicators(df.copy())
    except Exception as e:
        logger.warning(f"[htf_data_source] M5 add_indicators failed: {e}")
        return None

    if len(df_i) < 22:
        return None

    last = df_i.iloc[-1]
    prev = df_i.iloc[-2]
    sma21 = float(df_i["Close"].iloc[-21:].mean())

    # 直前 5m バーが SMA21 をタッチ/下抜けして当バーが反発したか
    prev_low = float(prev["Low"])
    prev_close = float(prev["Close"])
    cur_close = float(last["Close"])

    # スイング high/low (直近 20 本)
    swing_high = float(df_i["High"].iloc[-20:].max())
    swing_low = float(df_i["Low"].iloc[-20:].min())

    # RSI ダイバージェンス: 直近 5 本で close 新高値 vs RSI 新高値の不一致
    rsi_div_bear = False
    rsi_div_bull = False
    if "rsi" in df_i.columns and len(df_i) >= 6:
        recent = df_i.iloc[-5:]
        idx_high_close = recent["Close"].idxmax()
        idx_high_rsi = recent["rsi"].idxmax()
        idx_low_close = recent["Close"].idxmin()
        idx_low_rsi = recent["rsi"].idxmin()
        # bearish div: 直近で close が新高値だが RSI は新高値でない
        if idx_high_close != idx_high_rsi and idx_high_close == recent.index[-1]:
            rsi_div_bear = True
        # bullish div: close 新安値だが RSI は新安値でない
        if idx_low_close != idx_low_rsi and idx_low_close == recent.index[-1]:
            rsi_div_bull = True

    return {
        "close": cur_close,
        "high": float(last["High"]),
        "low": float(last["Low"]),
        "prev_close": prev_close,
        "prev_low": prev_low,
        "prev_high": float(prev["High"]),
        "sma21": sma21,
        "atr": float(last.get("atr", 0.0) or 0.0),
        "bbpb": float(last.get("bb_pband", 0.5) or 0.5),
        "rsi14": float(last.get("rsi", 50.0) or 50.0),
        "stoch_k": float(last.get("stoch_k", 50.0) or 50.0),
        "stoch_d": float(last.get("stoch_d", 50.0) or 50.0),
        "ema9": float(last.get("ema9", 0.0) or 0.0),
        "ema21": float(last.get("ema21", 0.0) or 0.0),
        "swing_high": swing_high,
        "swing_low": swing_low,
        "rsi_div_bear": rsi_div_bear,
        "rsi_div_bull": rsi_div_bull,
    }


def compute_mtf_features(symbol: str) -> dict:
    """Fetch M15 + M5 OANDA candles and return features for MTF cascade scalps.

    Returns
    -------
    {"m15": {...} or None, "m5": {...} or None}
        features are None when OANDA unavailable or compute fails — strategy
        must guard for this.
    """
    out: dict = {"m15": None, "m5": None}
    try:
        df_m15 = fetch_htf_candles(symbol, granularity="M15", count=80)
        out["m15"] = _compute_m15_features(df_m15)
    except Exception as e:
        logger.debug(f"[htf_data_source] M15 features failed for {symbol}: {e}")
    try:
        df_m5 = fetch_htf_candles(symbol, granularity="M5", count=80)
        out["m5"] = _compute_m5_features(df_m5)
    except Exception as e:
        logger.debug(f"[htf_data_source] M5 features failed for {symbol}: {e}")
    return out
