import numpy as np
import pandas as pd

import app
from app import _compute_bt_htf_bias


def _sample_1m_ohlcv(n: int = 2400) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="min", tz="UTC")
    base = 150.0 + np.linspace(0.0, 1.8, n)
    wave_fast = 0.08 * np.sin(np.arange(n) / 9.0)
    wave_slow = 0.18 * np.sin(np.arange(n) / 55.0)
    close = base + wave_fast + wave_slow
    open_ = close - 0.03 * np.cos(np.arange(n) / 7.0)
    high = np.maximum(open_, close) + 0.05
    low = np.minimum(open_, close) - 0.05
    volume = 100 + (np.arange(n) % 17) * 3
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=idx,
    )


def test_compute_bt_htf_bias_injects_m15_and_m5_for_scalp_mode():
    df = _sample_1m_ohlcv()

    got = _compute_bt_htf_bias(df, len(df) - 1, mode="scalp")

    assert isinstance(got.get("m15"), dict)
    assert isinstance(got.get("m5"), dict)
    for key in ("adx", "ema9", "ema21", "ema50", "ema_slope", "hurst_64", "range_20"):
        assert key in got["m15"], f"missing m15 key: {key}"
    for key in (
        "close",
        "high",
        "low",
        "prev_close",
        "prev_high",
        "prev_low",
        "sma21",
        "swing_high",
        "swing_low",
    ):
        assert key in got["m5"], f"missing m5 key: {key}"
    assert got["m15"]["hurst_64"] >= 0.0
    assert got["m5"]["prev_close"] > 0.0


def test_compute_bt_htf_bias_reuses_cached_scalp_mtf_precompute(monkeypatch):
    # 2026-10-15: 旧 key (id(df), len, index[0], index[-1]) は先行 test の同形 df が GC された後に
    # 同じ id が再利用されると偽ヒットし counted が 0 回で落ちた (PR #326 CI 2026-10-13 `assert 0 == 1`)。
    # 2026-10-16 rule:R3 で key は内容指紋 (len / index 端 / Close・High・Low nansum) になり id 非依存
    # (tests/test_bt_scalp_mtf_cache_key_fingerprint.py)。本 test の estimand は「同一 df の 2 回目以降は
    # 再計算しない」なので、先行 test が同一内容の df を cache 済みでも counted が 0 にならないよう
    # 開始時にモジュール cache を空にして前提を固定する (eviction 上限 4 とも独立)
    app._bt_scalp_mtf_precompute_cache.clear()
    app._bt_scalp_mtf_fp_memo.clear()
    df = _sample_1m_ohlcv()
    cache_counter = {"calls": 0}
    original = app._build_bt_scalp_mtf_cache

    def counted(frame):
        cache_counter["calls"] += 1
        return original(frame)

    monkeypatch.setattr(app, "_build_bt_scalp_mtf_cache", counted)

    for bar_idx in range(600, 1200, 60):
        got = _compute_bt_htf_bias(df, bar_idx, mode="scalp")
        assert got["m15"]
        assert got["m5"]

    assert cache_counter["calls"] == 1
