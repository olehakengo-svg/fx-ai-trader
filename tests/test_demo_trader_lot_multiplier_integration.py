"""Test demo_trader lot resolution honors Candidate.lot_multiplier.

Pattern: simulate _tick_entry with crafted candidate, observe units passed
to OandaBridge.market_order via _oanda mock.
"""
import os
import tempfile
from pathlib import Path

from strategies.base import Candidate
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


def _make_trader(monkeypatch, tmp_path):
    """Minimal demo_trader instance for lot resolution test."""
    db_path = tmp_path / "test_demo.db"
    trader = DemoTrader(DemoDB(str(db_path)))
    trader._strategy_n_cache = {"bb_rsi_reversion": 100}  # Above all N tiers
    return trader


def _make_candidate(lot_multiplier=1.0):
    return Candidate(
        signal="SELL", confidence=70, sl=1.1050, tp=1.0950,
        reasons=["test"], entry_type="bb_rsi_reversion",
        score=1.0, lot_multiplier=lot_multiplier,
    )


def test_lot_multiplier_1_5_boosts_lot(monkeypatch, tmp_path):
    """candidate.lot_multiplier=1.5 → final lot = base * 1.5 (within caps)."""
    trader = _make_trader(monkeypatch, tmp_path)
    cand = _make_candidate(lot_multiplier=1.5)
    base_lot = 5000
    multiplied = trader._apply_candidate_lot_multiplier(base_lot, cand)
    assert multiplied == 7500, f"expected 7500, got {multiplied}"


def test_lot_multiplier_0_5_reduces_lot(monkeypatch, tmp_path):
    trader = _make_trader(monkeypatch, tmp_path)
    cand = _make_candidate(lot_multiplier=0.5)
    assert trader._apply_candidate_lot_multiplier(5000, cand) == 2500


def test_lot_multiplier_1_0_unchanged(monkeypatch, tmp_path):
    trader = _make_trader(monkeypatch, tmp_path)
    cand = _make_candidate(lot_multiplier=1.0)
    assert trader._apply_candidate_lot_multiplier(5000, cand) == 5000


def test_lot_multiplier_none_candidate_unchanged(monkeypatch, tmp_path):
    """None candidate (e.g. legacy code path) → base lot unchanged."""
    trader = _make_trader(monkeypatch, tmp_path)
    assert trader._apply_candidate_lot_multiplier(5000, None) == 5000


def test_lot_multiplier_negative_clamped_to_zero(monkeypatch, tmp_path):
    trader = _make_trader(monkeypatch, tmp_path)
    cand = _make_candidate(lot_multiplier=-0.3)
    assert trader._apply_candidate_lot_multiplier(5000, cand) == 0


def test_lot_multiplier_returns_int(monkeypatch, tmp_path):
    """OANDA units must be integer."""
    trader = _make_trader(monkeypatch, tmp_path)
    cand = _make_candidate(lot_multiplier=1.33)
    result = trader._apply_candidate_lot_multiplier(5000, cand)
    assert isinstance(result, int)
    assert result == 6650  # int(5000 * 1.33)


# ── Hook integration tests (_resolve_units_with_multiplier) ──────────────────
# These exercise the full hook logic extracted into _resolve_units_with_multiplier,
# covering branches that the helper-only tests above cannot reach.

def _make_sig(lot_multiplier=1.0):
    """Minimal sig dict as produced by _tick_entry."""
    return {"lot_multiplier": lot_multiplier}


def test_hook_sentinel_skip(monkeypatch, tmp_path):
    """_is_sentinel=True → multiplier ignored, lot unchanged (sentinel 1000u preserved)."""
    trader = _make_trader(monkeypatch, tmp_path)
    sig = _make_sig(lot_multiplier=1.5)
    result = trader._resolve_units_with_multiplier(
        base_units=1000, sig=sig, is_sentinel=True,
        edge_cell_force_live=False, is_xau_inst=False
    )
    assert result == 1000, f"sentinel must preserve 1000u, got {result}"


def test_hook_edge_cell_force_live_skip(monkeypatch, tmp_path):
    """_edge_cell_force_live=True → multiplier ignored, pre-reg lot preserved."""
    trader = _make_trader(monkeypatch, tmp_path)
    sig = _make_sig(lot_multiplier=1.5)
    result = trader._resolve_units_with_multiplier(
        base_units=3000, sig=sig, is_sentinel=False,
        edge_cell_force_live=True, is_xau_inst=False
    )
    assert result == 3000, f"edge_cell_force_live must preserve 3000u, got {result}"


def test_hook_cap_reapplied_after_multiplier(monkeypatch, tmp_path):
    """base 5000 * 5.0 = 25000, but _OANDA_LOT_CAP=10000 → result 10000."""
    trader = _make_trader(monkeypatch, tmp_path)
    assert trader._OANDA_LOT_CAP == 10000, "precondition: default cap is 10000"
    sig = _make_sig(lot_multiplier=5.0)
    result = trader._resolve_units_with_multiplier(
        base_units=5000, sig=sig, is_sentinel=False,
        edge_cell_force_live=False, is_xau_inst=False
    )
    assert result == 10000, f"expected cap=10000, got {result}"


def test_hook_fx_1000u_rounding(monkeypatch, tmp_path):
    """FX 1000u rounding: 5000 * 1.4 = 7000 (clean), 5000 * 0.55 = 2750 → rounds DOWN to 2000."""
    trader = _make_trader(monkeypatch, tmp_path)

    # 7000 is already a clean multiple of 1000 — no change
    result_clean = trader._resolve_units_with_multiplier(
        base_units=5000, sig=_make_sig(lot_multiplier=1.4), is_sentinel=False,
        edge_cell_force_live=False, is_xau_inst=False
    )
    assert result_clean == 7000, f"expected 7000, got {result_clean}"

    # 2750 → floor(2750 / 1000) * 1000 = 2000
    result_round = trader._resolve_units_with_multiplier(
        base_units=5000, sig=_make_sig(lot_multiplier=0.55), is_sentinel=False,
        edge_cell_force_live=False, is_xau_inst=False
    )
    assert result_round == 2000, f"expected 2000 (rounded down from 2750), got {result_round}"


def test_hook_xau_exempt_from_1000u_rounding(monkeypatch, tmp_path):
    """XAU: base 100oz * 0.5 = 50oz — no 1000u rounding applied."""
    trader = _make_trader(monkeypatch, tmp_path)
    result = trader._resolve_units_with_multiplier(
        base_units=100, sig=_make_sig(lot_multiplier=0.5), is_sentinel=False,
        edge_cell_force_live=False, is_xau_inst=True
    )
    assert result == 50, f"XAU should not round to 1000u, got {result}"
