"""Tests for tools/phase3_bt.py — Phase 3 BT Pre-reg LOCK Phase 1 実装。

Pre-reg LOCK commit: 34c404c
Test scope: Constants / Friction Mode context manager / Strategy loader /
            Statistical functions / Anchored WFA runner (mocked)
"""
from __future__ import annotations

import math
import pytest

from tools.phase3_bt import (
    ALPHA_BONFERRONI,
    EXPECTED_STRATEGY_CLASS_MODES,
    FDR_Q,
    FRICTION_MODE_A,
    FRICTION_MODE_B,
    HOLDOUT_START,
    K,
    MISSING_STRATEGIES,
    PHASE3_STRATEGIES,
    PRE_REG_COMMIT,
    STRATEGY_MODES,
    STRATEGY_PATHS,
    WFA_ANCHORED_IS_END,
    WFA_ANCHORED_IS_START,
    WFA_ANCHORED_OOS_END,
    WFA_ANCHORED_OOS_START,
    AnchoredWFAResult,
    StrategyHandle,
    WFAStats,
    bonferroni_test,
    load_strategy,
    patch_friction_model,
    run_anchored_wfa,
    verify_friction_patch_works,
    verify_strategy_modes,
    welch_t_test,
    wilson_lower,
)


# ─── Group A: LOCK Constants 整合性 ───────────────────────────────────

def test_K_equals_7():
    """LOCK: K=7 (Option-B)"""
    assert K == 7
    assert len(PHASE3_STRATEGIES) == 7


def test_alpha_bonferroni_lock_value():
    """LOCK: α/K = 0.05/7 ≈ 0.007143"""
    assert math.isclose(ALPHA_BONFERRONI, 0.05 / 7, rel_tol=1e-9)
    # Track ⑤ §5.4 と整合
    assert 0.0071 < ALPHA_BONFERRONI < 0.0072


def test_fdr_q():
    """LOCK: FDR q = 0.10 (exploratory)"""
    assert FDR_Q == 0.10


def test_wfa_anchored_dates_lock():
    """LOCK: IS 2025-01〜09 / OOS 2025-10〜2026-04"""
    assert WFA_ANCHORED_IS_START.year == 2025 and WFA_ANCHORED_IS_START.month == 1
    assert WFA_ANCHORED_IS_END.year == 2025 and WFA_ANCHORED_IS_END.month == 9
    assert WFA_ANCHORED_OOS_START.year == 2025 and WFA_ANCHORED_OOS_START.month == 10
    assert WFA_ANCHORED_OOS_END.year == 2026 and WFA_ANCHORED_OOS_END.month == 4
    # IS < OOS
    assert WFA_ANCHORED_IS_END < WFA_ANCHORED_OOS_START
    # Hold-out 2026-05-01
    assert HOLDOUT_START.year == 2026 and HOLDOUT_START.month == 5 and HOLDOUT_START.day == 1


def test_pre_reg_commit_anchor():
    """Pre-reg LOCK 文書 commit hash が定数として埋め込まれている。"""
    assert PRE_REG_COMMIT == "34c404c"


# ─── Group B: Friction Mode 構造 ─────────────────────────────────────

def test_friction_mode_a_structure():
    assert FRICTION_MODE_A["label"] == "status_quo"
    assert FRICTION_MODE_A["London"] == 1.00
    assert FRICTION_MODE_A["NY"] == 1.20
    assert FRICTION_MODE_A["Tokyo"] == 1.45
    assert FRICTION_MODE_A["overlap_LN"] == 0.85


def test_friction_mode_b_structure():
    assert FRICTION_MODE_B["label"] == "u13_u14_calibrated"
    assert FRICTION_MODE_B["Tokyo"] == 0.80  # U13/U14 critical halve
    assert FRICTION_MODE_B["London"] == 0.85
    assert FRICTION_MODE_B["NY"] == 1.20  # KEEP


def test_friction_mode_a_b_diverge_in_tokyo():
    """Mode A vs B の主要差は Tokyo (1.45 → 0.80) と London (1.00 → 0.85)。"""
    assert FRICTION_MODE_A["Tokyo"] != FRICTION_MODE_B["Tokyo"]
    assert FRICTION_MODE_A["London"] != FRICTION_MODE_B["London"]
    # NY と overlap_LN は KEEP
    assert FRICTION_MODE_A["NY"] == FRICTION_MODE_B["NY"]


# ─── Group C: patch_friction_model context manager ────────────────────

def test_patch_friction_model_applies_and_restores():
    """context manager で _SESSION_MULTIPLIER が一時上書き → restore される。"""
    from modules import friction_model_v2
    original = dict(friction_model_v2._SESSION_MULTIPLIER)

    with patch_friction_model(FRICTION_MODE_B):
        # Mode B が apply されている
        assert friction_model_v2._SESSION_MULTIPLIER["Tokyo"] == 0.80
        assert friction_model_v2._SESSION_MULTIPLIER["London"] == 0.85

    # restore 後
    assert friction_model_v2._SESSION_MULTIPLIER == original


def test_patch_friction_model_restores_on_exception():
    """例外発生時も finally で restore される。"""
    from modules import friction_model_v2
    original = dict(friction_model_v2._SESSION_MULTIPLIER)

    with pytest.raises(RuntimeError):
        with patch_friction_model(FRICTION_MODE_B):
            raise RuntimeError("test")

    assert friction_model_v2._SESSION_MULTIPLIER == original


def test_patch_friction_model_excludes_label_key():
    """label key (string) は _SESSION_MULTIPLIER に書き込まれない (数値 multiplier のみ)。"""
    from modules import friction_model_v2
    with patch_friction_model(FRICTION_MODE_A):
        assert "label" not in friction_model_v2._SESSION_MULTIPLIER


# ─── Group D: Statistical Functions ───────────────────────────────────

@pytest.mark.parametrize("wins,n,expected_lower_pct", [
    # 既知の Wilson lower 値
    (60, 100, 49.92),  # WR 60% N=100 → ~49.92%
    (50, 100, 40.32),  # WR 50% N=100
    (10, 100, 5.49),   # WR 10% N=100
    (0, 100, 0.00),    # 0 win → ~0%
    (100, 100, 96.38), # 100% win → ~96.38%
])
def test_wilson_lower_known_values(wins, n, expected_lower_pct):
    result = wilson_lower(wins, n)
    assert math.isclose(result, expected_lower_pct, abs_tol=0.5), \
        f"wilson_lower({wins}, {n}) = {result}, expected ~{expected_lower_pct}"


def test_wilson_lower_n_zero():
    """N=0 → 0.0 (no error)"""
    assert wilson_lower(0, 0) == 0.0


def test_wilson_lower_invalid_wins():
    """wins > n → ValueError"""
    with pytest.raises(ValueError):
        wilson_lower(10, 5)


def test_welch_t_test_significant_difference():
    """大幅 mean 差 → 有意 p < 0.05"""
    xs = [1, 2, 3, 4, 5]
    ys = [10, 11, 12, 13, 14]
    t, p = welch_t_test(xs, ys)
    assert p < 0.05
    assert t < 0  # ys が大きい → t-stat 負


def test_welch_t_test_empty_input():
    xs, ys = [], [1, 2, 3]
    t, p = welch_t_test(xs, ys)
    assert math.isnan(t)
    assert p == 1.0


def test_bonferroni_test_default_k():
    """default k=len(p_values) で α/K = 0.05/3 = 0.01667"""
    p_values = [0.001, 0.05, 0.0001]
    # K=3 → threshold = 0.01667
    result = bonferroni_test(p_values)
    assert result == [True, False, True]


def test_bonferroni_test_explicit_k():
    """explicit k で threshold を制御"""
    p_values = [0.005]
    # K=10 → threshold = 0.005 (boundary)
    result_k10 = bonferroni_test(p_values, k=10)
    assert result_k10 == [False]  # p < 0.005 が要件、0.005 = boundary
    # K=5 → threshold = 0.01
    result_k5 = bonferroni_test(p_values, k=5)
    assert result_k5 == [True]


def test_bonferroni_test_phase3_k7():
    """Phase 3 LOCK: K=7 で p < α/K = 0.05/7 ≈ 0.0071428571 を判定"""
    # 厳密に α/K = 0.0071428571... 未満かどうか
    p_values = [0.005, 0.008, 0.001, 0.00715, 0.0071428572]
    result = bonferroni_test(p_values, k=7)
    # 0.005 < 0.007143 → True
    # 0.008 < 0.007143 → False
    # 0.001 < 0.007143 → True
    # 0.00715 < 0.007143 → False (0.00715 > α/K)
    # 0.0071428572 < 0.0071428571... → False
    assert result == [True, False, True, False, False]


# ─── Group E: Strategy Loader ─────────────────────────────────────────

def test_load_strategy_known_implemented():
    """gbp_deep_pullback は実装済 → StrategyHandle 返却"""
    h = load_strategy("gbp_deep_pullback")
    assert h is not None
    assert h.name == "gbp_deep_pullback"
    assert h.mode == "DT"


def test_load_strategy_scalp_mode():
    """vol_momentum_scalp は Scalp mode"""
    h = load_strategy("vol_momentum_scalp")
    assert h is not None
    assert h.mode == "Scalp"


def test_load_strategy_missing_returns_none():
    """pullback_to_liquidity_v1 は MISSING → None + warn"""
    assert "pullback_to_liquidity_v1" in MISSING_STRATEGIES
    h = load_strategy("pullback_to_liquidity_v1")
    assert h is None


def test_load_strategy_invalid_raises():
    """K=7 LOCK 外の戦略名 → ValueError (LOCK 違反防止)"""
    with pytest.raises(ValueError, match="not in PHASE3_STRATEGIES"):
        load_strategy("some_random_strategy")


def test_load_all_phase3_strategies():
    """K=7 全戦略を load、5 LOADED + 2 MISSING を期待"""
    loaded = []
    skipped = []
    for name in PHASE3_STRATEGIES:
        h = load_strategy(name)
        if h is None:
            skipped.append(name)
        else:
            loaded.append(name)
    assert len(loaded) == 5
    assert len(skipped) == 2
    assert set(skipped) == MISSING_STRATEGIES


# ─── Group F: WFAStats / AnchoredWFAResult dataclass ─────────────────

def test_wfa_stats_from_empty_trades():
    s = WFAStats.from_trades([])
    assert s.n == 0 and s.wr == 0.0 and s.ev == 0.0


def test_wfa_stats_from_mixed_trades():
    """6 wins / 4 losses, EV calc 検証"""
    trades = [
        {"outcome": "WIN", "pnl_pips": 5.0},
        {"outcome": "WIN", "pnl_pips": 8.0},
        {"outcome": "WIN", "pnl_pips": 3.0},
        {"outcome": "WIN", "pnl_pips": 6.0},
        {"outcome": "WIN", "pnl_pips": 4.0},
        {"outcome": "WIN", "pnl_pips": 4.0},
        {"outcome": "LOSS", "pnl_pips": -3.0},
        {"outcome": "LOSS", "pnl_pips": -5.0},
        {"outcome": "LOSS", "pnl_pips": -2.0},
        {"outcome": "LOSS", "pnl_pips": -4.0},
    ]
    s = WFAStats.from_trades(trades)
    assert s.n == 10
    assert s.wins == 6
    assert s.wr == 0.6
    # EV = (5+8+3+6+4+4 - 3-5-2-4) / 10 = (30 - 14) / 10 = 1.6
    assert math.isclose(s.ev, 1.6, abs_tol=0.001)
    # PF = 30 / 14 ≈ 2.143
    assert math.isclose(s.pf, 30.0 / 14.0, abs_tol=0.001)
    # Wilson lower for 6/10 ≈ 31.4%
    assert 28 < s.wilson_lower < 35


# ─── Group G: Integration test (run_anchored_wfa with mock BT) ────────

def test_run_anchored_wfa_with_mock_runner():
    """mocked BT runner で Anchored WFA の流れ end-to-end 確認。"""

    # IS と OOS を半々に含む合成 trade_log
    def mock_bt_runner(symbol, lookback_days):
        trades = [
            # IS period (2025-06)
            {"entry_type": "vol_momentum_scalp", "entry_time": "2025-06-01T10:00:00Z",
             "outcome": "WIN", "pnl_pips": 5.0},
            {"entry_type": "vol_momentum_scalp", "entry_time": "2025-06-15T11:00:00Z",
             "outcome": "WIN", "pnl_pips": 6.0},
            {"entry_type": "vol_momentum_scalp", "entry_time": "2025-08-01T12:00:00Z",
             "outcome": "LOSS", "pnl_pips": -2.0},
            # OOS period (2025-12)
            {"entry_type": "vol_momentum_scalp", "entry_time": "2025-12-01T10:00:00Z",
             "outcome": "WIN", "pnl_pips": 4.0},
            {"entry_type": "vol_momentum_scalp", "entry_time": "2026-02-01T11:00:00Z",
             "outcome": "LOSS", "pnl_pips": -3.0},
            # Other strategy (filter out 確認用)
            {"entry_type": "other_strategy", "entry_time": "2025-06-01T13:00:00Z",
             "outcome": "WIN", "pnl_pips": 100.0},
        ]
        return {"trade_log": trades}

    handle = StrategyHandle(name="vol_momentum_scalp", mode="Scalp",
                            module_path="strategies.scalp.vol_momentum")
    result = run_anchored_wfa(handle, "USDJPY=X", FRICTION_MODE_A,
                              bt_runner=mock_bt_runner)

    assert result is not None
    assert isinstance(result, AnchoredWFAResult)
    assert result.strategy == "vol_momentum_scalp"
    assert result.mode_label == "status_quo"
    # IS: 3 trades (2 WIN, 1 LOSS) for vol_momentum_scalp
    assert result.is_stats.n == 3
    assert result.is_stats.wins == 2
    # OOS: 2 trades (1 WIN, 1 LOSS)
    assert result.oos_stats.n == 2
    assert result.oos_stats.wins == 1


def test_run_anchored_wfa_missing_handle_returns_none():
    """handle=None (missing strategy) → None"""
    result = run_anchored_wfa(None, "USDJPY=X", FRICTION_MODE_A)
    assert result is None


# ─── Group H: R4 verify_strategy_modes (Phase 3 BT pre-flight) ────────

def test_verify_strategy_modes_returns_all_strategies():
    """K=7 全戦略が verification 結果に含まれる。"""
    result = verify_strategy_modes()
    assert set(result.keys()) == set(PHASE3_STRATEGIES)


def test_verify_strategy_modes_implemented_strategies_match():
    """実装済 5 戦略は全て match=True (drift なし)。"""
    result = verify_strategy_modes()
    implemented = [n for n in PHASE3_STRATEGIES if n not in MISSING_STRATEGIES]
    for name in implemented:
        entry = result[name]
        assert entry["match"] is True, \
            f"Drift detected: {name} {entry}"
        # class_mode が EXPECTED と一致
        assert entry["class_mode"] == EXPECTED_STRATEGY_CLASS_MODES[name]


def test_verify_strategy_modes_missing_strategies_skip():
    """MISSING_STRATEGIES 2 戦略は match=False with MISSING error。"""
    result = verify_strategy_modes()
    for name in MISSING_STRATEGIES:
        entry = result[name]
        assert entry["match"] is False
        assert "MISSING" in (entry.get("error") or "")


# ─── Group I: R6 verify_friction_patch_works (Phase 3 BT pre-flight) ───

def test_verify_friction_patch_works_passes():
    """Mode A vs Mode B で実 friction value が顕著に異なることを確認。

    USD_JPY DT Tokyo:
      Mode A: 2.14 × 1.0 (DT) × 1.45 (Tokyo) = 3.103 pip
      Mode B: 2.14 × 1.0 (DT) × 0.80 (Tokyo) = 1.712 pip
      diff: 1.391 pip
    """
    result = verify_friction_patch_works()
    assert result["passed"] is True, f"Smoke test failed: {result}"
    assert result["diff"] >= 0.5


def test_verify_friction_patch_a_higher_than_b_on_tokyo():
    """Mode A Tokyo (1.45×) が Mode B Tokyo (0.80×) より高い friction を返す。"""
    result = verify_friction_patch_works()
    assert result["mode_a_tokyo"] > result["mode_b_tokyo"]
    # Approximate ratio: 1.45 / 0.80 = 1.8125
    ratio = result["mode_a_tokyo"] / result["mode_b_tokyo"]
    assert 1.7 < ratio < 1.9, f"Ratio {ratio} out of expected range [1.7, 1.9]"


def test_verify_friction_patch_works_smoke_no_lingering_state():
    """smoke test 実行後に _SESSION_MULTIPLIER が original 状態に restore されている。"""
    from modules import friction_model_v2
    original = dict(friction_model_v2._SESSION_MULTIPLIER)
    _ = verify_friction_patch_works()
    assert friction_model_v2._SESSION_MULTIPLIER == original
