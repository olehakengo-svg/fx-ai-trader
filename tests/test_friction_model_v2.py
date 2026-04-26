"""Tests for modules.friction_model_v2."""
from __future__ import annotations

import math
import pytest

from modules.friction_model_v2 import (
    friction_for,
    is_scalp_dead,
    list_supported_pairs,
    integrity_check,
)


# ─── normalize ────────────────────────────────────────────────────────

@pytest.mark.parametrize("inp", ["USD_JPY", "USDJPY=X", "usdjpy=x", "USD/JPY"])
def test_friction_for_handles_pair_formats(inp):
    f = friction_for(inp)
    assert not f["unsupported"]
    assert f["pair"] == "USD_JPY"


# ─── basic numerical correctness ─────────────────────────────────────

def test_usd_jpy_baseline_matches_friction_analysis():
    """USD_JPY DT default session should match friction-analysis.md numbers."""
    f = friction_for("USD_JPY", mode="DT", session="default")
    assert f["spread_pips"] == pytest.approx(0.7)
    assert f["slippage_pips"] == pytest.approx(0.5)
    assert f["rt_friction_pips"] == pytest.approx(2.14)
    # default session multiplier is 1.10, mode DT is 1.0
    assert f["adjusted_rt_pips"] == pytest.approx(2.14 * 1.10)


def test_eur_usd_baseline():
    f = friction_for("EUR_USD", mode="DT", session="London")
    assert f["rt_friction_pips"] == pytest.approx(2.00)
    assert f["adjusted_rt_pips"] == pytest.approx(2.00 * 1.0 * 1.0)  # London=1.0, DT=1.0


def test_gbp_usd_highest_friction():
    """GBP_USD has the largest friction in the FX-only post-v8.4 set."""
    f = friction_for("GBP_USD", mode="DT", session="London")
    assert f["rt_friction_pips"] == pytest.approx(4.53)


# ─── unsupported pair ────────────────────────────────────────────────

def test_unsupported_pair_returns_nan_flagged():
    f = friction_for("XAU_USD")
    assert f["unsupported"] is True
    assert math.isnan(f["rt_friction_pips"])


def test_eur_gbp_unsupported():
    f = friction_for("EUR_GBP")
    # Stopped per friction-analysis.md (STRUCTURALLY IMPOSSIBLE)
    assert f["unsupported"] is True


# ─── mode multipliers ────────────────────────────────────────────────

def test_scalp_mode_slightly_higher_than_dt():
    dt = friction_for("USD_JPY", mode="DT", session="London")
    scalp = friction_for("USD_JPY", mode="Scalp", session="London")
    assert scalp["adjusted_rt_pips"] > dt["adjusted_rt_pips"]
    # 5% premium for Scalp
    assert scalp["adjusted_rt_pips"] == pytest.approx(dt["adjusted_rt_pips"] * 1.05)


def test_swing_mode_slightly_lower_than_dt():
    dt = friction_for("USD_JPY", mode="DT", session="London")
    swing = friction_for("USD_JPY", mode="Swing", session="London")
    assert swing["adjusted_rt_pips"] == pytest.approx(dt["adjusted_rt_pips"] * 0.95)


# ─── session multipliers ─────────────────────────────────────────────

def test_session_ordering():
    """Asia early > Tokyo > NY > London > overlap (best to worst friction order)."""
    base = friction_for("USD_JPY", mode="DT")
    london = friction_for("USD_JPY", mode="DT", session="London")["adjusted_rt_pips"]
    overlap = friction_for("USD_JPY", mode="DT", session="overlap_LN")["adjusted_rt_pips"]
    ny = friction_for("USD_JPY", mode="DT", session="NY")["adjusted_rt_pips"]
    tokyo = friction_for("USD_JPY", mode="DT", session="Tokyo")["adjusted_rt_pips"]
    sydney = friction_for("USD_JPY", mode="DT", session="Sydney")["adjusted_rt_pips"]
    asia_early = friction_for("USD_JPY", mode="DT", session="Asia_early")["adjusted_rt_pips"]

    # overlap < London < NY < Asia_early < Tokyo (from session multipliers)
    # Note: Tokyo (1.45) < Asia_early (1.55) < Sydney (1.60)
    assert overlap < london
    assert london < ny
    assert ny < tokyo
    # Asia_early between Tokyo and Sydney
    assert tokyo < asia_early
    assert asia_early < sydney


# ─── ATR ratio ───────────────────────────────────────────────────────

def test_atr_ratio_computed_when_atr_provided():
    f = friction_for("USD_JPY", mode="Scalp", session="Tokyo", atr_pips=5.0)
    assert f["friction_atr_ratio"] is not None
    # adjusted = 2.14 * 1.05 (scalp) * 1.45 (tokyo) = 3.258
    expected = 2.14 * 1.05 * 1.45 / 5.0
    assert f["friction_atr_ratio"] == pytest.approx(expected, rel=0.01)


def test_atr_ratio_none_when_not_provided():
    f = friction_for("USD_JPY", mode="DT")
    assert f["friction_atr_ratio"] is None


def test_atr_ratio_none_when_zero_atr():
    f = friction_for("USD_JPY", mode="DT", atr_pips=0.0)
    # zero/negative ATR → no ratio
    assert f["friction_atr_ratio"] is None


# ─── is_scalp_dead ───────────────────────────────────────────────────

def test_scalp_dead_when_atr_low():
    """Low ATR (high friction/ATR ratio) → DEAD."""
    # USD_JPY scalp Tokyo: 2.14 * 1.05 * 1.45 = 3.26 pip
    # ATR 5 → ratio 65.2% > 30% → DEAD
    assert is_scalp_dead("USD_JPY", atr_pips=5.0) is True


def test_scalp_alive_when_atr_high():
    """High ATR (low friction/ATR ratio) → not DEAD."""
    # USD_JPY scalp default: 2.14 * 1.05 * 1.10 = 2.47 pip
    # ATR 50 → ratio 4.9% < 30% → alive
    assert is_scalp_dead("USD_JPY", atr_pips=50.0) is False


def test_scalp_dead_unsupported_pair():
    assert is_scalp_dead("XAU_USD", atr_pips=100.0) is True


def test_scalp_dead_custom_threshold():
    # USD_JPY default: 2.47 pip, ATR 10 → ratio 24.7%
    # threshold 0.20 → DEAD (24.7 > 20)
    assert is_scalp_dead("USD_JPY", atr_pips=10.0, threshold=0.20) is True
    # threshold 0.30 → alive (24.7 < 30)
    assert is_scalp_dead("USD_JPY", atr_pips=10.0, threshold=0.30) is False


# ─── integrity check ────────────────────────────────────────────────

def test_integrity_check_passes():
    result = integrity_check()
    assert result["ok"] is True, f"Integrity errors: {result['errors']}"
    assert result["errors"] == []


def test_list_supported_pairs():
    pairs = list_supported_pairs()
    assert "USD_JPY" in pairs
    assert "EUR_USD" in pairs
    assert "GBP_USD" in pairs
    assert "EUR_JPY" in pairs
    # Stopped pairs should NOT appear
    assert "EUR_GBP" not in pairs
    assert "XAU_USD" not in pairs
