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
