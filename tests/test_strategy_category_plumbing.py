"""Integration tests for strategy_category.apply_policy() ↔ MassiveSignalEnhancer.

2026-04-26 Edge Reset Phase 1 plumbing verification:
  - apply_policy() が呼ばれていること
  - 現状 _POLICY 全 0.0 で behavior 変化ゼロ (中立維持)
  - entry_type が enhancer に貫通すること
  - Phase 1.5 で _POLICY 値を変更したときに振る舞いが正しく追従すること
"""
from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")

from modules import strategy_category as sc
from modules.massive_signals import MassiveSignalEnhancer


# ─── apply_policy() 単体 ──────────────────────────────────────────────

def test_apply_policy_neutral_by_default():
    """Phase 1: _POLICY 全 0.0 で raw_adj 関係なく 0 を返す."""
    for enhancer in ["vwap_zone", "vwap_slope", "volume_profile_hvn",
                     "volume_profile_lvn", "institutional_flow",
                     "mtf_alignment", "ema_alignment", "macd_alignment",
                     "vwap_deviation"]:
        for cat_strategy in ["ema_pullback", "bb_rsi_reversion",
                             "london_breakout", None]:
            for raw in [-5, 0, 3, 10]:
                got = sc.apply_policy(enhancer, cat_strategy, raw)
                assert got == 0.0, (
                    f"plumbing only: {enhancer=} {cat_strategy=} {raw=} → {got=}"
                )


def test_apply_policy_unknown_enhancer_returns_zero():
    assert sc.apply_policy("nonexistent", "ema_pullback", 5) == 0.0


def test_apply_policy_respects_custom_policy(monkeypatch):
    """Phase 1.5 をシミュレート: _POLICY 値を変えたら scale が反映される."""
    fake_policy = {
        "test_enhancer": {"TF": 1.0, "MR": -1.0, "BR": 0.5, "OTHER": 0.0},
    }
    monkeypatch.setattr(sc, "_POLICY", fake_policy)
    assert sc.apply_policy("test_enhancer", "ema_pullback", 4) == 4.0   # TF
    assert sc.apply_policy("test_enhancer", "bb_rsi_reversion", 4) == -4.0  # MR
    assert sc.apply_policy("test_enhancer", "orb_trap", 4) == 2.0  # BR
    assert sc.apply_policy("test_enhancer", "unknown_strat", 4) == 0.0   # OTHER
    assert sc.apply_policy("test_enhancer", None, 4) == 0.0              # OTHER


# ─── category_of() ──────────────────────────────────────────────────

@pytest.mark.parametrize("strat,expected_cat", [
    ("ema_pullback", "TF"),
    ("ema_trend_scalp", "TF"),
    ("bb_rsi_reversion", "MR"),
    ("engulfing_bb", "MR"),
    ("london_breakout", "TF"),  # actually TF in registry, BR is for orb_trap etc
    ("orb_trap", "BR"),
    ("liquidity_sweep", "BR"),
    ("nonexistent_strategy", "OTHER"),
    (None, "OTHER"),
    ("", "OTHER"),
])
def test_category_of(strat, expected_cat):
    assert sc.category_of(strat) == expected_cat


# ─── MassiveSignalEnhancer plumbing ──────────────────────────────────

def _make_df(n: int = 30) -> pd.DataFrame:
    """Synthetic df with vwap and OHLCV columns."""
    idx = pd.date_range("2026-04-26", periods=n, freq="5min", tz="UTC")
    rng = np.random.default_rng(42)
    close = 150.0 + rng.normal(0, 0.05, n).cumsum()
    return pd.DataFrame({
        "Open": close + rng.normal(0, 0.02, n),
        "High": close + np.abs(rng.normal(0, 0.05, n)),
        "Low":  close - np.abs(rng.normal(0, 0.05, n)),
        "Close": close,
        "Volume": rng.integers(1000, 5000, n).astype(float),
        "vwap": close + rng.normal(0, 0.01, n),
        "atr": np.full(n, 0.05),
    }, index=idx)


def test_enhance_neutral_when_policy_zero():
    """Plumbing が 0.0 multiplier で confidence が変わらないこと."""
    enhancer = MassiveSignalEnhancer()
    df = _make_df()
    base = {"signal": "BUY", "confidence": 50, "reasons": []}

    # entry_type 未指定
    out1 = enhancer.enhance(df, base.copy(), "USDJPY=X")
    # entry_type 指定 (TF / MR どちらでも)
    out2 = enhancer.enhance(df, base.copy(), "USDJPY=X", entry_type="ema_pullback")
    out3 = enhancer.enhance(df, base.copy(), "USDJPY=X", entry_type="bb_rsi_reversion")

    assert out1["confidence"] == 50, "policy 全 0 で entry_type なしでも変化しない"
    assert out2["confidence"] == 50, "TF entry_type でも変化しない (Phase 1)"
    assert out3["confidence"] == 50, "MR entry_type でも変化しない (Phase 1)"


def test_enhance_applies_policy_when_set(monkeypatch):
    """Phase 1.5 想定: _POLICY を変えたら enhance() の出力が追従する."""
    # 直接 strategy_category._POLICY を書き換える (テスト用)
    fake_policy = {
        "vwap_zone":          {"TF": 1.0, "MR": -1.0, "BR": 0.0, "OTHER": 0.0},
        "vwap_slope":         {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
        "institutional_flow": {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
        "volume_profile_hvn": {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
        "volume_profile_lvn": {"TF": 0.0, "MR": 0.0, "BR": 0.0, "OTHER": 0.0},
    }
    monkeypatch.setattr(sc, "_POLICY", fake_policy)

    # raw_adj はすべての enhancer で現在 0 のため、_POLICY を変えても
    # 結果は 0 のまま。これは「raw 値が 0 で固定されている」ことの
    # 確認テスト (Phase 1.5 で raw_adj 復活時にこのテストが期待値を変える前提)
    enhancer = MassiveSignalEnhancer()
    df = _make_df()
    base = {"signal": "BUY", "confidence": 50, "reasons": []}
    out = enhancer.enhance(df, base, "USDJPY=X", entry_type="ema_pullback")
    assert out["confidence"] == 50, (
        "Phase 1: raw_adj=0 のため _POLICY 設定に関係なく 0. "
        "Phase 1.5 で raw_adj 復活時に本テストの期待値も更新する."
    )


def test_enhance_entry_type_from_base_signal():
    """base_signal['entry_type'] が引数として渡されない場合の fallback."""
    enhancer = MassiveSignalEnhancer()
    df = _make_df()
    base = {
        "signal": "BUY",
        "confidence": 50,
        "reasons": [],
        "entry_type": "ema_pullback",
    }
    out = enhancer.enhance(df, base, "USDJPY=X")
    # _POLICY 全 0 なので confidence は変化しないが、エラーが出ないこと
    assert out["confidence"] == 50


def test_enhance_no_vwap_returns_unchanged():
    enhancer = MassiveSignalEnhancer()
    df = _make_df().drop(columns=["vwap"])
    base = {"signal": "BUY", "confidence": 50, "reasons": []}
    out = enhancer.enhance(df, base, "USDJPY=X")
    assert out is base or out == base, "vwap 無しで base_signal そのまま返る"


def test_enhance_short_df_returns_unchanged():
    enhancer = MassiveSignalEnhancer()
    df = _make_df(n=3)
    base = {"signal": "BUY", "confidence": 50, "reasons": []}
    out = enhancer.enhance(df, base, "USDJPY=X")
    assert out is base or out == base


# ─── enhancer 内部関数の entry_type 引数 ──────────────────────────

def test_enhancer_internals_accept_entry_type():
    enhancer = MassiveSignalEnhancer()
    df = _make_df()
    # 各 enhancer 関数が entry_type 引数を受け取ること (引数エラーが出ない)
    r1 = enhancer._vwap_zone_analysis(df, "BUY", entry_type="ema_pullback")
    r2 = enhancer._volume_profile_analysis(df, "BUY", entry_type="bb_rsi_reversion")
    r3 = enhancer._institutional_flow(df, "BUY", entry_type=None)

    # Phase 1: 全 0.0 multiplier なので conf_adj は必ず 0
    assert r1["conf_adj"] == 0
    assert r2["conf_adj"] == 0
    assert r3["conf_adj"] == 0
