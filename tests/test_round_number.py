"""Tests for modules/round_number.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from modules.round_number import (
    nearest_round,
    distance_to_round,
    is_near_round,
    shift_tp_inside,
    expand_sl_for_round,
    round_confluence_boost,
    pip_size,
)


class TestPipSize:
    def test_jpy_pair(self):
        assert pip_size("USDJPY") == 0.01
        assert pip_size("USD_JPY") == 0.01

    def test_non_jpy(self):
        assert pip_size("EURUSD") == 0.0001
        assert pip_size("GBPUSD") == 0.0001

    def test_pass_through_float(self):
        assert pip_size(0.001) == 0.001


class TestNearestRound:
    def test_jpy_at_whole_number(self):
        # 150.000 is a whole-number magnet
        rn, rt, dist = nearest_round(150.001, pip=0.01, scope="major")
        assert rt == "00"
        assert dist == pytest.approx(0.1, abs=0.01)  # 0.1 pip
        assert abs(rn - 150.000) < 1e-9

    def test_jpy_at_half_number(self):
        rn, rt, dist = nearest_round(150.502, pip=0.01, scope="major")
        # 150.500 is exactly halfway
        assert rt == "50"
        assert dist == pytest.approx(0.2, abs=0.01)
        assert abs(rn - 150.500) < 1e-9

    def test_eur_at_round(self):
        rn, rt, dist = nearest_round(1.10003, pip=0.0001, scope="major")
        assert rt == "00"
        assert dist == pytest.approx(0.3, abs=0.05)


class TestDistanceToRound:
    def test_far_from_round(self):
        # 150.273 is mid-way between 150.250 and 150.300, neither major
        d = distance_to_round(150.273, pip=0.01, scope="major")
        assert d > 5.0  # > 5 pip from .000 / .500


class TestIsNearRound:
    def test_threshold(self):
        assert is_near_round(150.001, pip=0.01, threshold_pips=5.0)
        assert not is_near_round(150.250, pip=0.01, threshold_pips=5.0)


class TestShiftTpInside:
    def test_buy_tp_above_round_pulled_back(self):
        # BUY targeting 150.001 (just above round 150.000)
        # Should be pulled to 149.997 (3 pip below round)
        tp_adj = shift_tp_inside(150.001, "BUY", pip=0.01, shift_pips=3.0)
        assert tp_adj < 150.000
        assert abs(tp_adj - (150.000 - 0.03)) < 1e-9

    def test_sell_tp_below_round_pulled_back(self):
        # SELL targeting 149.999 (just below round 150.000)
        # Should be pushed to 150.003 (3 pip above round)
        tp_adj = shift_tp_inside(149.999, "SELL", pip=0.01, shift_pips=3.0)
        assert tp_adj > 150.000
        assert abs(tp_adj - (150.000 + 0.03)) < 1e-9

    def test_far_tp_unchanged(self):
        # 150.250 is far from any major round
        tp_adj = shift_tp_inside(150.250, "BUY", pip=0.01, shift_pips=3.0)
        assert tp_adj == 150.250


class TestExpandSlForRound:
    def test_sl_expanded_when_level_near_round(self):
        # Level at 150.002 (near round 150.000)
        # Original SL at 149.95 (5 pip below)
        sl_orig = 149.95
        level = 150.002
        sl_new = expand_sl_for_round(sl_orig, level, "BUY", pip=0.01,
                                      expand_factor=1.5)
        # Original distance: |149.95 - 150.002| = 5.2 pip
        # New distance: 5.2 * 1.5 = 7.8 pip
        # New SL: 150.002 - 7.8*0.01 = 149.924
        assert sl_new < sl_orig  # SL pushed further down

    def test_sl_unchanged_when_level_far_from_round(self):
        # Level at 150.270 — not near any round
        sl_new = expand_sl_for_round(149.95, 150.270, "BUY", pip=0.01,
                                      expand_factor=1.5)
        assert sl_new == 149.95


class TestRoundConfluenceBoost:
    def test_full_boost_at_round(self):
        boost = round_confluence_boost(150.000, pip=0.01, threshold_pips=3.0)
        assert boost == pytest.approx(1.0, abs=0.01)

    def test_no_boost_far_from_round(self):
        boost = round_confluence_boost(150.250, pip=0.01, threshold_pips=3.0)
        assert boost == 0.0

    def test_linear_decay(self):
        # 1.5 pip from round → boost = 0.5
        boost = round_confluence_boost(150.015, pip=0.01, threshold_pips=3.0)
        assert boost == pytest.approx(0.5, abs=0.05)
