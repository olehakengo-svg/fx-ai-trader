"""
BT Data Cache — Massive API データの Parquet キャッシュ管理

設計:
- 初回: Massive APIから全量取得 → Parquet保存
- 2回目以降: Parquet読込 → 最終バー以降のみAPI差分取得 → マージ保存
- 更新判定: ファイルの最終更新時刻が閾値を超えたら差分更新

保存先: data/cache/massive/{PAIR}_{TF}.parquet
例: data/cache/massive/USDJPY_1h.parquet

Usage:
    from tools.bt_data_cache import BTDataCache
    cache = BTDataCache()
    df = cache.get("USD_JPY", "15m", days=365)  # キャッシュ有→即時、無→API取得+保存
    cache.refresh_all()  # 全ペア×全TFの差分更新
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path

# プロジェクトルートをsys.pathに追加（CLIから実行時にmodulesをimport可能にする）
_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# .env読込
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
except ImportError:
    pass

# ── Config ──
CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "data" / "cache" / "massive"

# ペア定義 (OANDA形式 → yFinance形式)
PAIRS = {
    "USD_JPY": "USDJPY=X",
    "EUR_USD": "EURUSD=X",
    "GBP_USD": "GBPUSD=X",
    "EUR_JPY": "EURJPY=X",
    "EUR_GBP": "EURGBP=X",
    "GBP_JPY": "GBPJPY=X",
}

# TF別の最大取得日数とキャッシュ更新間隔
TF_CONFIG = {
    "1m":  {"max_days": 60,  "refresh_hours": 1},
    "5m":  {"max_days": 60,  "refresh_hours": 4},
    "15m": {"max_days": 365, "refresh_hours": 6},
    "30m": {"max_days": 365, "refresh_hours": 12},
    "1h":  {"max_days": 500, "refresh_hours": 12},
    "4h":  {"max_days": 730, "refresh_hours": 24},
    "1d":  {"max_days": 730, "refresh_hours": 24},
}


class BTDataCache:
    def __init__(self, cache_dir: str = None):
        self._dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, pair: str, tf: str) -> Path:
        return self._dir / f"{pair}_{tf}.parquet"

    def _needs_refresh(self, pair: str, tf: str) -> bool:
        """キャッシュが古いか存在しない場合True"""
        p = self._path(pair, tf)
        if not p.exists():
            return True
        age_hours = (time.time() - p.stat().st_mtime) / 3600
        max_hours = TF_CONFIG.get(tf, {}).get("refresh_hours", 12)
        return age_hours > max_hours

    def get(self, pair: str, tf: str, days: int = None, force_refresh: bool = False) -> pd.DataFrame:
        """キャッシュからデータ取得。必要なら差分更新。

        Args:
            pair: OANDA形式 (e.g., "USD_JPY")
            tf: タイムフレーム (e.g., "15m", "1h")
            days: 取得日数 (None=TF_CONFIGのmax_days)
            force_refresh: True=強制的にAPI再取得
        Returns:
            pd.DataFrame with OHLCV columns and UTC DatetimeIndex
        """
        if days is None:
            days = TF_CONFIG.get(tf, {}).get("max_days", 120)

        p = self._path(pair, tf)

        if not force_refresh and p.exists() and not self._needs_refresh(pair, tf):
            # キャッシュ読込
            df = pd.read_parquet(p)
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            # 要求日数分をフィルター
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            df = df[df.index >= cutoff]
            if len(df) > 100:
                return df

        # API取得 (全量 or 差分)
        df = self._fetch_and_save(pair, tf, days, p)
        return df

    def _fetch_and_save(self, pair: str, tf: str, days: int, path: Path) -> pd.DataFrame:
        """Massive APIからデータ取得してParquet保存"""
        from modules.data import fetch_ohlcv_massive

        yf_symbol = PAIRS.get(pair, f"{pair.replace('_', '')}=X")

        # 既存キャッシュがあれば差分更新
        existing = None
        if path.exists():
            try:
                existing = pd.read_parquet(path)
                if existing.index.tz is None:
                    existing.index = existing.index.tz_localize("UTC")
            except Exception:
                existing = None

        if existing is not None and len(existing) > 0:
            # 差分: 最終バーから現在まで
            last_ts = existing.index[-1]
            delta_days = max(2, (datetime.now(timezone.utc) - last_ts).days + 1)
            try:
                delta = fetch_ohlcv_massive(yf_symbol, tf, delta_days)
                # マージ + 重複排除
                df = pd.concat([existing, delta])
                df = df[~df.index.duplicated(keep="last")]
                df = df.sort_index()
                print(f"[Cache] {pair}/{tf}: +{len(delta)} bars (delta), total={len(df)}")
            except Exception as e:
                print(f"[Cache] {pair}/{tf}: delta failed ({e}), using existing {len(existing)} bars")
                df = existing
        else:
            # 全量取得
            try:
                df = fetch_ohlcv_massive(yf_symbol, tf, days)
                print(f"[Cache] {pair}/{tf}: {len(df)} bars (full fetch)")
            except Exception as e:
                raise ValueError(f"Failed to fetch {pair}/{tf}: {e}")

        # 保存
        df.to_parquet(path, engine="pyarrow")
        return df

    def refresh_all(self, pairs: list = None, timeframes: list = None):
        """全ペア×全TFのキャッシュを更新"""
        pairs = pairs or list(PAIRS.keys())
        timeframes = timeframes or list(TF_CONFIG.keys())
        results = {}

        for pair in pairs:
            for tf in timeframes:
                key = f"{pair}/{tf}"
                try:
                    df = self.get(pair, tf, force_refresh=True)
                    results[key] = {"bars": len(df), "from": str(df.index[0].date()), "to": str(df.index[-1].date())}
                except Exception as e:
                    results[key] = {"error": str(e)}
                time.sleep(0.2)  # rate limit対策

        return results

    def status(self) -> dict:
        """全キャッシュファイルの状態を返す"""
        result = {}
        for f in sorted(self._dir.glob("*.parquet")):
            name = f.stem  # e.g., "USDJPY_1h"
            age_hours = (time.time() - f.stat().st_mtime) / 3600
            size_mb = f.stat().st_size / 1024 / 1024
            try:
                df = pd.read_parquet(f)
                bars = len(df)
                date_from = str(df.index[0])[:10]
                date_to = str(df.index[-1])[:10]
            except Exception:
                bars, date_from, date_to = 0, "?", "?"
            result[name] = {
                "bars": bars, "from": date_from, "to": date_to,
                "size_mb": round(size_mb, 2), "age_hours": round(age_hours, 1),
            }
        return result


if __name__ == "__main__":
    """CLI: python3 tools/bt_data_cache.py [refresh|status]"""
    import sys
    cache = BTDataCache()

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        for k, v in cache.status().items():
            print(f"  {k:20s} {v.get('bars', 0):>6d} bars | {v.get('from', '?')} ~ {v.get('to', '?')} | {v.get('size_mb', 0):.1f}MB | {v.get('age_hours', 0):.0f}h ago")
    elif len(sys.argv) > 1 and sys.argv[1] == "refresh":
        # BT用のTFのみ取得（1m,5m,15m,1h）
        tfs = sys.argv[2].split(",") if len(sys.argv) > 2 else ["1m", "5m", "15m", "1h"]
        pairs = sys.argv[3].split(",") if len(sys.argv) > 3 else None
        results = cache.refresh_all(pairs=pairs, timeframes=tfs)
        for k, v in results.items():
            if "error" in v:
                print(f"  {k:20s} ERROR: {v['error'][:60]}")
            else:
                print(f"  {k:20s} {v['bars']:>6d} bars | {v['from']} ~ {v['to']}")
    else:
        print("Usage: python3 tools/bt_data_cache.py [refresh|status]")
        print("  refresh [tfs] [pairs]  — Refresh cache (e.g., refresh 1m,15m USD_JPY,EUR_USD)")
        print("  status                 — Show cache status")
