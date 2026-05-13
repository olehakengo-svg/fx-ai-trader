#!/usr/bin/env python3
"""Backfill demo_trades.v2_regime from the M15 v2 binary classifier.

Dry-run is the default. Use --apply only after reviewing the planned updates.
The classifier is reconstructed from repo-local 15m parquet cache as of each
trade entry_time; production databases are never required for normal tests.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.regime_classifier import classify_15m, hurst_rs  # noqa: E402


CACHE_DIR = ROOT / "data" / "cache" / "massive"
UPDATE_SQL = "UPDATE demo_trades SET v2_regime = ? WHERE trade_id = ?"


def _pair_cache_key(pair: str) -> str:
    key = str(pair or "").upper().replace("=X", "").replace("/", "_")
    if "_" in key:
        return key
    if len(key) == 6:
        return f"{key[:3]}_{key[3:]}"
    return key


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={c: c.lower() for c in df.columns})
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def _wilder_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = pd.concat(
        [(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _prepare_m15(pair: str, cache_dir: Path) -> pd.DataFrame:
    path = cache_dir / f"{_pair_cache_key(pair)}_15m.parquet"
    if not path.exists():
        raise FileNotFoundError(path)
    df = _normalize_ohlc(pd.read_parquet(path))
    close = df["close"].astype(float)
    df["adx"] = _wilder_adx(df, 14)
    df["ema21"] = close.ewm(span=21, adjust=False).mean()
    df["ema_slope"] = df["ema21"] - df["ema21"].shift(3)
    df["hurst_64"] = close.rolling(64).apply(lambda x: hurst_rs(x.tolist()), raw=False)
    return df


def _clean_float(value: Any, default: float) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    if not math.isfinite(out):
        return default
    return out


def _feature_at(
    cache: dict[str, pd.DataFrame],
    pair: str,
    ts: pd.Timestamp,
    cache_dir: Path,
) -> dict | None:
    if pair not in cache:
        cache[pair] = _prepare_m15(pair, cache_dir)
    df = cache[pair]
    window = df[df.index <= ts]
    if window.empty:
        return None
    row = window.iloc[-1]
    return {
        "adx": _clean_float(row.get("adx"), 0.0),
        "ema_slope": _clean_float(row.get("ema_slope"), 0.0),
        "hurst_64": _clean_float(row.get("hurst_64"), 0.5),
    }


def run_backfill(
    db_path: str,
    *,
    apply: bool = False,
    chunk_size: int = 1000,
    limit: int | None = None,
    cache_dir: str | Path = CACHE_DIR,
) -> dict:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    cache_path = Path(cache_dir)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(demo_trades)")}
        if "v2_regime" not in cols:
            raise RuntimeError("demo_trades.v2_regime column is missing")

        sql = (
            "SELECT trade_id, instrument, entry_time "
            "FROM demo_trades "
            "WHERE v2_regime IS NULL "
            "  AND instrument IS NOT NULL AND instrument != '' "
            "  AND entry_time IS NOT NULL AND entry_time != '' "
            "ORDER BY id"
        )
        params: list[Any] = []
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))

        rows = conn.execute(sql, params).fetchall()
        feature_cache: dict[str, pd.DataFrame] = {}
        updates: list[dict[str, str]] = []
        nulls = 0
        errors: list[dict[str, str]] = []

        for row in rows:
            trade_id = row["trade_id"]
            try:
                ts = pd.Timestamp(row["entry_time"])
                if ts.tzinfo is None:
                    ts = ts.tz_localize("UTC")
                else:
                    ts = ts.tz_convert("UTC")
                features = _feature_at(feature_cache, row["instrument"], ts, cache_path)
                if features is None:
                    nulls += 1
                    continue
                regime = classify_15m(features)
            except Exception as exc:
                nulls += 1
                errors.append({"trade_id": trade_id, "error": str(exc)})
                continue
            updates.append({"trade_id": trade_id, "v2_regime": regime})

        if apply and updates:
            for start in range(0, len(updates), chunk_size):
                chunk = updates[start:start + chunk_size]
                conn.executemany(
                    UPDATE_SQL,
                    [(u["v2_regime"], u["trade_id"]) for u in chunk],
                )
                conn.commit()

        return {
            "mode": "apply" if apply else "dry-run",
            "db_path": str(db_path),
            "cache_dir": str(cache_path),
            "rows_examined": len(rows),
            "classified": len(updates),
            "nulls": nulls,
            "would_update": len(updates),
            "updated": len(updates) if apply else 0,
            "update_sql": UPDATE_SQL,
            "errors": errors,
            "updates": updates,
        }
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="demo_trades.db", help="SQLite demo_trades DB path")
    parser.add_argument("--cache-dir", default=str(CACHE_DIR), help="15m parquet cache directory")
    parser.add_argument("--apply", action="store_true", help="write updates; default is dry-run")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    result = run_backfill(
        args.db,
        apply=bool(args.apply),
        chunk_size=args.chunk_size,
        limit=args.limit,
        cache_dir=args.cache_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
