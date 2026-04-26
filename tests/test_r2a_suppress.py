"""Tests for R2-A Suppress gate (modules.strategy_category, 2026-04-26 Wave 1).

Phase 4d-II Wilson upper < baseline 4 cells confidence ×0.5 抑制の検証。
詳細根拠: knowledge-base/wiki/analyses/phase4d-II-nature-pooling-result-2026-04-26.md
"""
from __future__ import annotations

import pytest

from modules.strategy_category import (
    _R2A_SUPPRESS,
    _normalize_session,
    apply_r2a_suppress_gate,
    compute_spread_quintile,
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


# ─── compute_spread_quintile() 動作 ────────────────────────────────

@pytest.mark.parametrize("spread_pips,pair,expected_q", [
    # USD_JPY: cuts [0.4, 0.6, 0.8, 1.2]
    (0.3, "USD_JPY", "q0"),
    (0.4, "USD_JPY", "q0"),  # boundary inclusive
    (0.5, "USD_JPY", "q1"),
    (0.6, "USD_JPY", "q1"),
    (0.7, "USD_JPY", "q2"),
    (0.8, "USD_JPY", "q2"),
    (1.0, "USD_JPY", "q3"),
    (1.2, "USD_JPY", "q3"),
    (1.5, "USD_JPY", "q4"),
    # GBP_USD: cuts [0.8, 1.2, 1.6, 2.4]
    (0.5, "GBP_USD", "q0"),
    (1.0, "GBP_USD", "q1"),
    (1.5, "GBP_USD", "q2"),
    (2.0, "GBP_USD", "q3"),
    (3.0, "GBP_USD", "q4"),
    # EUR_JPY: cuts [0.6, 0.9, 1.2, 1.6]
    (0.5, "EUR_JPY", "q0"),
    (1.0, "EUR_JPY", "q2"),
    # 未登録 pair → default cuts [0.5, 1.0, 1.5, 2.0]
    (0.4, "AUD_USD", "q0"),
    (0.8, "AUD_USD", "q1"),
    (1.3, "AUD_USD", "q2"),
    (1.7, "AUD_USD", "q3"),
    (2.5, "AUD_USD", "q4"),
])
def test_compute_spread_quintile_buckets(spread_pips, pair, expected_q):
    assert compute_spread_quintile(spread_pips, pair) == expected_q


def test_compute_spread_quintile_handles_pair_format_variants():
    """pair format ("/" / "=X" / lowercase) でも正規化される。"""
    assert compute_spread_quintile(0.7, "USD/JPY") == "q2"
    assert compute_spread_quintile(0.7, "USDJPY=X") == "q2"
    assert compute_spread_quintile(0.7, "usd_jpy") == "q2"


def test_compute_spread_quintile_handles_invalid_input():
    """None / NaN / 負値 / 非数値 → fallback "q2" (median bucket)。"""
    assert compute_spread_quintile(None, "USD_JPY") == "q2"
    assert compute_spread_quintile(float("nan"), "USD_JPY") == "q2"
    assert compute_spread_quintile(-1.0, "USD_JPY") == "q2"
    assert compute_spread_quintile("abc", "USD_JPY") == "q2"


# ─── 統合: 実シナリオ ───────────────────────────────────────────────

def test_integration_overlap_q2_stoch_trend_pullback():
    """Phase 4d-II 主要 cell: stoch_trend_pullback × Overlap × q2 (WR 7.7%)
    USD_JPY で spread 0.7pip → q2 → ×0.5 確認。"""
    pair = "USD_JPY"
    spread_pips = 0.7
    spread_q = compute_spread_quintile(spread_pips, pair)
    assert spread_q == "q2"

    # app.py 由来 session name
    conf = apply_r2a_suppress_gate(
        "stoch_trend_pullback", "NY × London", spread_q, 80
    )
    assert conf == 40


def test_integration_non_listed_cell_passthrough():
    """非対象 cell は confidence 維持 (no-op)。"""
    conf = apply_r2a_suppress_gate("orb_trap", "Tokyo", "q1", 75)
    assert conf == 75
