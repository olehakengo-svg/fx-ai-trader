"""ZN=F バーキャッシュの union-merge 不変条件 (rule:R3, 2026-08-14)

背景: `fetch_zn_intraday` は `df.to_parquet(cache_path)` で無条件 overwrite していた。
yfinance の intraday 窓は rolling (1h=730d / sub-hour=60d) なので、窓外に出た
歴史バーは**キャッシュファイルにしか存在しない**。overwrite 実装では 1 回の
リフレッシュで不可逆にその歴史を失う (実測: cache 左端 2024-02-18 に対し
当日の yfinance 730d 左端は 2024-03-21 = 約 1 ヶ月がファイル固有)。

本テストは merge が「行数単調非減少 + 古いバー保存 + 重複は fresh 採用」を
満たすことを pin する。
"""
import pandas as pd
import pytest

from modules.yield_data import merge_bar_cache

COLS = ["Open", "High", "Low", "Close", "Volume"]


def _frame(start: str, periods: int, base: float = 100.0) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="1h", tz="UTC")
    return pd.DataFrame(
        {c: [base + i for i in range(periods)] for c in COLS}, index=idx
    )


def test_merge_preserves_history_outside_fetch_window(tmp_path):
    """fetch 窓より古いバーが保存される (回帰の本丸)。"""
    old = _frame("2024-02-18", 100, base=100.0)
    cache = tmp_path / "ZN_F_1h.parquet"
    old.to_parquet(cache)

    # fresh は窓が右にずれており、old の左端を含まない
    fresh = _frame("2024-06-01", 50, base=200.0)
    merged = merge_bar_cache(cache, fresh)

    assert merged.index.min() == old.index.min(), "窓外の古いバーが失われた"
    assert merged.index.max() == fresh.index.max()
    assert len(merged) == len(old) + len(fresh)


def test_merge_is_monotonic_non_decreasing(tmp_path):
    """行数は単調非減少 — 短い窓を fetch しても縮まない。"""
    old = _frame("2024-02-18", 500)
    cache = tmp_path / "ZN_F_1h.parquet"
    old.to_parquet(cache)

    fresh = _frame("2024-02-18", 10, base=999.0)  # 極端に短い窓
    merged = merge_bar_cache(cache, fresh)

    assert len(merged) >= len(old)
    assert len(merged) == len(old)  # fresh は old の部分集合


def test_merge_prefers_fresh_on_duplicate_timestamps(tmp_path):
    """重複タイムスタンプはベンダー訂正を反映して fresh を採用。"""
    old = _frame("2024-02-18", 10, base=100.0)
    cache = tmp_path / "ZN_F_1h.parquet"
    old.to_parquet(cache)

    fresh = _frame("2024-02-18", 10, base=500.0)
    merged = merge_bar_cache(cache, fresh)

    assert len(merged) == 10
    assert merged["Close"].iloc[0] == 500.0


def test_merge_sorted_and_unique(tmp_path):
    old = _frame("2024-03-01", 20)
    cache = tmp_path / "ZN_F_1h.parquet"
    old.to_parquet(cache)

    fresh = _frame("2024-02-18", 20, base=300.0)  # fresh の方が古い
    merged = merge_bar_cache(cache, fresh)

    assert merged.index.is_monotonic_increasing
    assert merged.index.is_unique


def test_merge_without_existing_cache_returns_fresh(tmp_path):
    fresh = _frame("2024-02-18", 5)
    merged = merge_bar_cache(tmp_path / "missing.parquet", fresh)
    pd.testing.assert_frame_equal(merged, fresh)


def test_merge_with_corrupt_cache_does_not_raise(tmp_path):
    cache = tmp_path / "ZN_F_1h.parquet"
    cache.write_bytes(b"not a parquet file")
    fresh = _frame("2024-02-18", 5)
    merged = merge_bar_cache(cache, fresh)
    pd.testing.assert_frame_equal(merged, fresh)


def test_merge_handles_tz_naive_cache(tmp_path):
    """古いキャッシュが tz-naive でも UTC 化して merge できる。"""
    idx = pd.date_range("2024-02-18", periods=10, freq="1h")
    old = pd.DataFrame({c: [1.0] * 10 for c in COLS}, index=idx)
    cache = tmp_path / "ZN_F_1h.parquet"
    old.to_parquet(cache)

    fresh = _frame("2024-03-01", 5)
    merged = merge_bar_cache(cache, fresh)

    assert str(merged.index.tz) == "UTC"
    assert len(merged) == 15
