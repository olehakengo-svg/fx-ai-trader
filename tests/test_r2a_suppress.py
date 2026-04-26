"""Tests for R2-A Suppress gate (modules.strategy_category, 2026-04-26 Wave 1).

Phase 4d-II Wilson upper < baseline 4 cells confidence ×0.5 抑制の検証。
詳細根拠: knowledge-base/wiki/analyses/phase4d-II-nature-pooling-result-2026-04-26.md

U18 fix 2026-04-27: 5-bin quintile → 4-bin quartile (Phase 4d-II 互換)、
production-derived cuts。compute_spread_quintile() は backward-compat alias。
"""
from __future__ import annotations

import pytest

from modules.strategy_category import (
    _R2A_SUPPRESS,
    _SPREAD_QUARTILE_CUTS,
    _normalize_session,
    apply_r2a_suppress_gate,
    compute_spread_quartile,
    compute_spread_quintile,  # backward-compat alias
)


# ─── _R2A_SUPPRESS dict 構造 ─────────────────────────────────────────

def test_r2a_suppress_has_4_cells():
    """Plan で固定された 4 cells が確実に登録されている。"""
    assert len(_R2A_SUPPRESS) == 4


def test_r2a_suppress_all_multipliers_are_half():
    """すべての cell が ×0.5 (loss prevention only)。"""
    for key, mult in _R2A_SUPPRESS.items():
        assert mult == 0.5, f"Cell {key} should be 0.5, got {mult}"


def test_r2a_suppress_canonical_cells_present():
    """4 cells 全て canonical session name で登録されている。"""
    expected = {
        ("stoch_trend_pullback", "Overlap", "q2"),
        ("sr_channel_reversal", "London", "q3"),
        ("ema_trend_scalp", "London", "q0"),
        ("vol_surge_detector", "Tokyo", "q3"),
    }
    assert set(_R2A_SUPPRESS.keys()) == expected


# ─── apply_r2a_suppress_gate() 動作 ─────────────────────────────────

@pytest.mark.parametrize("strategy,session,spread_q,expected_mult", [
    # R2-A 対象 cells (×0.5)
    ("stoch_trend_pullback", "Overlap", "q2", 0.5),
    ("sr_channel_reversal", "London", "q3", 0.5),
    ("ema_trend_scalp", "London", "q0", 0.5),
    ("vol_surge_detector", "Tokyo", "q3", 0.5),
    # 同戦略・別 session/spread (×1.0 = no-op)
    ("ema_trend_scalp", "Tokyo", "q2", 1.0),
    ("ema_trend_scalp", "London", "q1", 1.0),
    ("stoch_trend_pullback", "Overlap", "q3", 1.0),
    # 別戦略 (R2-B boost 候補は本 Wave では未実装、no-op で正常)
    ("bb_rsi_reversion", "Overlap", "q2", 1.0),
    ("fib_reversal", "Tokyo", "q3", 1.0),
    ("orb_trap", "London", "q1", 1.0),
])
def test_apply_r2a_suppress_gate_multipliers(strategy, session, spread_q, expected_mult):
    conf_raw = 80
    conf_after = apply_r2a_suppress_gate(strategy, session, spread_q, conf_raw)
    assert conf_after == int(round(conf_raw * expected_mult))


def test_apply_r2a_suppress_gate_with_app_session_name():
    """app.py の "NY × London" は "Overlap" に正規化される。"""
    conf_after = apply_r2a_suppress_gate(
        "stoch_trend_pullback", "NY × London", "q2", 80
    )
    assert conf_after == 40  # ×0.5 適用


def test_apply_r2a_suppress_gate_handles_none_entry_type():
    """entry_type=None は no-op (gate skip)。"""
    assert apply_r2a_suppress_gate(None, "Overlap", "q2", 80) == 80
    assert apply_r2a_suppress_gate("", "Overlap", "q2", 80) == 80


def test_apply_r2a_suppress_gate_returns_int():
    """戻り値は常に int (downstream の confidence は int 型)。"""
    result = apply_r2a_suppress_gate("ema_trend_scalp", "London", "q0", 75)
    assert isinstance(result, int)
    assert result == 38  # int(round(75 * 0.5)) = 38


def test_apply_r2a_suppress_gate_handles_float_input():
    """float の confidence でも動作。"""
    result = apply_r2a_suppress_gate("ema_trend_scalp", "London", "q0", 75.5)
    assert isinstance(result, int)
    # int(round(75.5 * 0.5)) = int(round(37.75)) = 38
    assert result == 38


def test_apply_r2a_suppress_gate_zero_conf():
    """conf=0 は ×0.5 でも 0。"""
    assert apply_r2a_suppress_gate("ema_trend_scalp", "London", "q0", 0) == 0


# ─── _normalize_session() 動作 ──────────────────────────────────────

@pytest.mark.parametrize("input_name,expected", [
    ("NY × London", "Overlap"),
    ("Overlap", "Overlap"),
    ("overlap_LN", "Overlap"),
    ("東京 × London", "Overlap_TK"),
    ("Overlap_TK", "Overlap_TK"),
    ("New York", "NewYork"),
    ("NewYork", "NewYork"),
    ("NY", "NewYork"),
    ("Tokyo", "Tokyo"),
    ("東京", "Tokyo"),
    ("London", "London"),
    ("ロンドン", "London"),
    ("Off-hours", "Off-hours"),  # 未定義 session は pass-through
    (None, ""),
    ("", ""),
])
def test_normalize_session(input_name, expected):
    assert _normalize_session(input_name) == expected


# ─── compute_spread_quartile() 動作 (U18 fix, 4-bin Phase 4d-II compatible) ──

@pytest.mark.parametrize("spread_pips,pair,expected_q", [
    # USD_JPY: cuts [0.8, 0.8, 0.8] — degenerate (75%+ trades = 0.8)
    (0.7, "USD_JPY", "q0"),  # spread <= cuts[0]
    (0.8, "USD_JPY", "q0"),  # boundary inclusive (q0 で吸収、majority)
    (0.9, "USD_JPY", "q3"),  # spread > cuts[2] (outlier)
    (1.0, "USD_JPY", "q3"),  # outlier
    (2.6, "USD_JPY", "q3"),  # 最大値も q3 (outlier tail)
    # EUR_USD: cuts [0.8, 0.8, 0.8] — completely degenerate (distinct=1)
    (0.7, "EUR_USD", "q0"),
    (0.8, "EUR_USD", "q0"),  # all 100% of trades
    (0.9, "EUR_USD", "q3"),  # never observed but still q3
    # GBP_USD: cuts [1.3, 1.3, 1.3] — degenerate
    (1.2, "GBP_USD", "q0"),
    (1.3, "GBP_USD", "q0"),  # majority
    (1.5, "GBP_USD", "q3"),  # outlier
    (2.0, "GBP_USD", "q3"),  # outlier tail
    # EUR_JPY: cuts [1.7, 1.9, 2.0] — 唯一 cuts に意味がある
    (1.5, "EUR_JPY", "q0"),
    (1.7, "EUR_JPY", "q0"),
    (1.8, "EUR_JPY", "q1"),
    (1.9, "EUR_JPY", "q1"),
    (1.95, "EUR_JPY", "q2"),
    (2.0, "EUR_JPY", "q2"),
    (2.5, "EUR_JPY", "q3"),
    # GBP_JPY: cuts [2.8, 2.8, 2.8] — degenerate
    (2.5, "GBP_JPY", "q0"),
    (2.8, "GBP_JPY", "q0"),
    (3.2, "GBP_JPY", "q3"),
    # 未登録 pair → default cuts [0.8, 1.0, 1.5]
    (0.5, "AUD_USD", "q0"),
    (0.8, "AUD_USD", "q0"),
    (0.9, "AUD_USD", "q1"),
    (1.0, "AUD_USD", "q1"),
    (1.3, "AUD_USD", "q2"),
    (1.5, "AUD_USD", "q2"),
    (2.0, "AUD_USD", "q3"),
])
def test_compute_spread_quartile_buckets(spread_pips, pair, expected_q):
    assert compute_spread_quartile(spread_pips, pair) == expected_q


def test_spread_quartile_cuts_table_structure():
    """U18 fix: 全 pair で cuts は 3 要素 (4-bin = 3 cuts)、ascending 順。"""
    for pair, cuts in _SPREAD_QUARTILE_CUTS.items():
        assert len(cuts) == 3, f"{pair} cuts length should be 3, got {len(cuts)}"
        assert all(cuts[i] <= cuts[i+1] for i in range(len(cuts)-1)), \
            f"{pair} cuts not ascending: {cuts}"


def test_compute_spread_quartile_handles_pair_format_variants():
    """pair format ("/" / "=X" / lowercase) でも正規化される。"""
    # USD_JPY cuts [0.8, 0.8, 0.8]: 0.8 → q0 (boundary inclusive)
    assert compute_spread_quartile(0.8, "USD/JPY") == "q0"
    assert compute_spread_quartile(0.8, "USDJPY=X") == "q0"
    assert compute_spread_quartile(0.8, "usd_jpy") == "q0"


def test_compute_spread_quartile_handles_invalid_input():
    """None / NaN / 負値 / 非数値 → fallback "q1" (4-bin median-ish)。"""
    assert compute_spread_quartile(None, "USD_JPY") == "q1"
    assert compute_spread_quartile(float("nan"), "USD_JPY") == "q1"
    assert compute_spread_quartile(-1.0, "USD_JPY") == "q1"
    assert compute_spread_quartile("abc", "USD_JPY") == "q1"


# ─── compute_spread_quintile (DEPRECATED alias) ────────────────────────

def test_compute_spread_quintile_is_alias_for_quartile():
    """U18 fix: compute_spread_quintile は compute_spread_quartile への alias。
    Backward compat だが、5-bin (q4) は使われず 4-bin (q0-q3) のみ。"""
    # USD_JPY 0.8 → q0 (quartile 結果と一致)
    assert compute_spread_quintile(0.8, "USD_JPY") == compute_spread_quartile(0.8, "USD_JPY")
    # alias は q4 を返さない (4-bin 仕様)
    assert compute_spread_quintile(2.6, "USD_JPY") in {"q0", "q1", "q2", "q3"}


# ─── 統合: 実シナリオ (U18 fix 4-bin) ────────────────────────────────

def test_integration_overlap_q0_majority_usd_jpy():
    """U18 fix 後: USD_JPY 0.8 (majority) → q0 となる (旧 q2 から変化)。
    Wave 1 R2-A の (Overlap, q2) は USD_JPY majority 値で発火しなくなり、
    高 spread outlier (>0.8) のみで q3 に分類される。
    """
    pair = "USD_JPY"
    spread_pips = 0.8
    spread_q = compute_spread_quartile(spread_pips, pair)
    assert spread_q == "q0"  # 旧仕様では q2、新仕様では q0

    # (Overlap, q2) suppress 対象だが spread_q=q0 なので発火しない (no-op)
    conf = apply_r2a_suppress_gate(
        "stoch_trend_pullback", "NY × London", spread_q, 80
    )
    assert conf == 80  # no suppress


def test_integration_overlap_q3_outlier_usd_jpy():
    """U18 fix 後: USD_JPY 1.0 (outlier) → q3。stoch_trend_pullback ×
    (Overlap, q2) は q2 cell ではないので suppress なし、
    ただし vol_surge_detector × (Tokyo, q3) は別 strategy なので無関係。"""
    pair = "USD_JPY"
    spread_pips = 1.0
    spread_q = compute_spread_quartile(spread_pips, pair)
    assert spread_q == "q3"

    # stoch_trend_pullback × Overlap × q3 は R2-A 対象外
    conf = apply_r2a_suppress_gate(
        "stoch_trend_pullback", "NY × London", spread_q, 80
    )
    assert conf == 80  # no suppress (q3 cell は対象外)


def test_integration_eur_jpy_q2_meaningful():
    """EUR_JPY のみ cuts [1.7, 1.9, 2.0] が意味のある分割を提供する。
    spread=1.95 → q2 で、もし R2-A 対象 cell があれば suppress 発火。"""
    pair = "EUR_JPY"
    spread_pips = 1.95
    spread_q = compute_spread_quartile(spread_pips, pair)
    assert spread_q == "q2"

    # 現 R2-A に EUR_JPY × Overlap × q2 等は登録されていない
    conf = apply_r2a_suppress_gate(
        "stoch_trend_pullback", "NY × London", spread_q, 80
    )
    # NY × London → Overlap、stoch×Overlap×q2 は R2-A 対象 → suppress 適用
    assert conf == 40


def test_integration_non_listed_cell_passthrough():
    """非対象 cell は confidence 維持 (no-op)。"""
    conf = apply_r2a_suppress_gate("orb_trap", "Tokyo", "q1", 75)
    assert conf == 75
