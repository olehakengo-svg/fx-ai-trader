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
