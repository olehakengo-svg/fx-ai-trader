"""rule:R3 2026-10-16 — scalp M15/M5 precompute cache key must be content-based.

Registry `bt-scalp-mtf-cache-key-id-reuse-r3`: the old key
`(id(df), len, index[0], index[-1])` let a *different* DataFrame with the same
shape and index range (another pair in a multi-pair BT loop, or a re-fetched
window with vendor-corrected bars) hit the previous frame's features after the
id was recycled. These pins fix the new contract:

1. same content, different object  -> same key, no rebuild (cache reuse)
2. same shape/index, different Close -> different key, rebuild
3. a single corrected bar            -> different key
4. the fingerprint is computed once per live object (O(1) re-reads)
5. a recycled id never returns the stale fingerprint (weakref validation)
6. frames without OHLC columns do not raise
"""
import gc

import numpy as np
import pandas as pd

import app
from app import _bt_scalp_mtf_cache_key, _compute_bt_htf_bias


def _sample_1m_ohlcv(n: int = 2400, seed_shift: float = 0.0) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="min", tz="UTC")
    base = 150.0 + np.linspace(0.0, 1.8, n) + seed_shift
    wave_fast = 0.08 * np.sin(np.arange(n) / 9.0)
    wave_slow = 0.18 * np.sin(np.arange(n) / 55.0)
    close = base + wave_fast + wave_slow
    open_ = close - 0.03 * np.cos(np.arange(n) / 7.0)
    high = np.maximum(open_, close) + 0.05
    low = np.minimum(open_, close) - 0.05
    volume = 100 + (np.arange(n) % 17) * 3
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


def _reset_caches():
    app._bt_scalp_mtf_precompute_cache.clear()
    app._bt_scalp_mtf_fp_memo.clear()


def test_key_has_no_object_id_component():
    df = _sample_1m_ohlcv()
    key = _bt_scalp_mtf_cache_key(df)
    assert id(df) not in key
    assert key[0] == app._BT_SCALP_MTF_FP_VERSION
    assert key[1] == len(df)
    assert key[2] == df.index[0] and key[3] == df.index[-1]


def test_identical_content_different_object_shares_key():
    df_a = _sample_1m_ohlcv()
    df_b = df_a.copy(deep=True)
    assert df_a is not df_b
    assert _bt_scalp_mtf_cache_key(df_a) == _bt_scalp_mtf_cache_key(df_b)


def test_same_shape_and_index_but_different_close_gets_distinct_key():
    df_a = _sample_1m_ohlcv()
    df_b = _sample_1m_ohlcv(seed_shift=0.25)  # same len / same index, shifted prices
    assert len(df_a) == len(df_b)
    assert df_a.index.equals(df_b.index)
    assert _bt_scalp_mtf_cache_key(df_a) != _bt_scalp_mtf_cache_key(df_b)


def test_single_corrected_bar_changes_key():
    df_a = _sample_1m_ohlcv()
    df_b = df_a.copy(deep=True)
    mid = len(df_b) // 2
    df_b.iloc[mid, df_b.columns.get_loc("Close")] += 0.013  # one vendor-corrected close
    assert _bt_scalp_mtf_cache_key(df_a) != _bt_scalp_mtf_cache_key(df_b)


def test_fingerprint_is_computed_once_per_live_object(monkeypatch):
    _reset_caches()
    df = _sample_1m_ohlcv()
    calls = {"n": 0}
    original = app._bt_scalp_mtf_content_fingerprint

    def counted(frame):
        calls["n"] += 1
        return original(frame)

    monkeypatch.setattr(app, "_bt_scalp_mtf_content_fingerprint", counted)
    k1 = _bt_scalp_mtf_cache_key(df)
    k2 = _bt_scalp_mtf_cache_key(df)
    k3 = _bt_scalp_mtf_cache_key(df)
    assert k1 == k2 == k3
    assert calls["n"] == 1


def test_recycled_id_never_returns_stale_fingerprint(monkeypatch):
    """Simulate CPython id reuse: plant a memo entry under df_b's id whose
    weakref points at a *different* (dead or foreign) object. The memo must be
    ignored and the real fingerprint of df_b returned."""
    _reset_caches()
    df_a = _sample_1m_ohlcv()
    key_a = _bt_scalp_mtf_cache_key(df_a)
    df_b = _sample_1m_ohlcv(seed_shift=0.25)
    # Forge the hazard deterministically: memo says "id(df_b) -> key_a" but the
    # weakref is to df_a, i.e. the id belonged to another object.
    import weakref

    app._bt_scalp_mtf_fp_memo[id(df_b)] = (weakref.ref(df_a), key_a)
    key_b = _bt_scalp_mtf_cache_key(df_b)
    assert key_b != key_a
    assert key_b == app._bt_scalp_mtf_content_fingerprint(df_b)
    # and the memo now holds df_b's own entry
    ref, memo_key = app._bt_scalp_mtf_fp_memo[id(df_b)]
    assert ref() is df_b and memo_key == key_b
    # dead-ref variant: original object collected, id reused by a fresh frame
    del df_a
    gc.collect()
    app._bt_scalp_mtf_fp_memo[id(df_b)] = (lambda: None, key_a)
    assert _bt_scalp_mtf_cache_key(df_b) == key_b


def test_compute_bt_htf_bias_rebuilds_for_different_content_same_shape(monkeypatch):
    """End-to-end: two same-shape frames in one process must each build their
    own M15/M5 precompute (the multi-pair BT loop hazard)."""
    _reset_caches()
    df_a = _sample_1m_ohlcv()
    df_b = _sample_1m_ohlcv(seed_shift=0.25)
    counter = {"calls": 0}
    original = app._build_bt_scalp_mtf_cache

    def counted(frame):
        counter["calls"] += 1
        return original(frame)

    monkeypatch.setattr(app, "_build_bt_scalp_mtf_cache", counted)
    got_a = _compute_bt_htf_bias(df_a, 900, mode="scalp")
    got_b = _compute_bt_htf_bias(df_b, 900, mode="scalp")
    assert counter["calls"] == 2
    assert got_a["m5"]["close"] != got_b["m5"]["close"]
    # a byte-identical copy of df_a reuses df_a's entry (no third build)
    _compute_bt_htf_bias(df_a.copy(deep=True), 960, mode="scalp")
    assert counter["calls"] == 2


def test_fingerprint_tolerates_missing_ohlc_columns():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0]},
                      index=pd.date_range("2026-01-01", periods=3, freq="min", tz="UTC"))
    key = _bt_scalp_mtf_cache_key(df)
    assert key[1] == 3
    assert key[4:] == (None, None, None)


def test_memo_prunes_dead_refs_and_caps_size():
    _reset_caches()
    frames = [_sample_1m_ohlcv(n=120, seed_shift=i * 0.01) for i in range(app._BT_SCALP_MTF_FP_MEMO_MAX + 4)]
    for f in frames:
        _bt_scalp_mtf_cache_key(f)
    assert len(app._bt_scalp_mtf_fp_memo) <= app._BT_SCALP_MTF_FP_MEMO_MAX
    del frames
    gc.collect()
    # next insert prunes dead refs rather than growing
    _bt_scalp_mtf_cache_key(_sample_1m_ohlcv(n=120, seed_shift=9.0))
    assert len(app._bt_scalp_mtf_fp_memo) <= app._BT_SCALP_MTF_FP_MEMO_MAX
