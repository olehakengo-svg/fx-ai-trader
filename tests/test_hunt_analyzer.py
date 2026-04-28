"""Tests for research/edge_discovery/hunt_analyzer.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from modules.sr_detector import SRLevel
from research.edge_discovery.hunt_analyzer import (
    HuntStat, detect_hunt_events, analyze_hunts_for_level, is_hunt_bar,
)


def _make_bar(open_, high, low, close):
    return {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": 1000}


def _df_from_bars(bars, freq="15min", start="2024-01-01"):
    return pd.DataFrame(
        bars, index=pd.date_range(start, periods=len(bars), freq=freq)
    )


class TestIsHuntBar:
    def test_classic_resistance_hunt(self):
        bar = _make_bar(149.95, 150.30, 149.90, 149.92)
        atr = 0.20
        assert is_hunt_bar(bar, level=150.000, atr=atr,
                           side="resistance", k_atr=1.0)

    def test_classic_support_hunt(self):
        bar = _make_bar(150.05, 150.10, 149.70, 150.08)
        atr = 0.20
        assert is_hunt_bar(bar, level=150.000, atr=atr,
                           side="support", k_atr=1.0)

    def test_clean_breakout_is_not_hunt(self):
        bar = _make_bar(149.95, 150.30, 149.92, 150.25)
        atr = 0.20
        assert not is_hunt_bar(bar, level=150.000, atr=atr,
                               side="resistance", k_atr=1.0)

    def test_no_breach_is_not_hunt(self):
        bar = _make_bar(149.95, 149.99, 149.90, 149.97)
        atr = 0.20
        assert not is_hunt_bar(bar, level=150.000, atr=atr,
                               side="resistance", k_atr=1.0)

    def test_small_wick_below_threshold_is_not_hunt(self):
        bar = _make_bar(149.95, 150.02, 149.93, 149.94)
        atr = 0.20
        assert not is_hunt_bar(bar, level=150.000, atr=atr,
                               side="resistance", k_atr=1.0)


class TestDetectHuntEvents:
    def test_finds_resistance_hunt_at_level(self):
        bars = [_make_bar(149.95, 149.99, 149.92, 149.96)] * 5
        bars.append(_make_bar(149.95, 150.30, 149.90, 149.92))
        bars += [_make_bar(149.90, 149.95, 149.85, 149.88)] * 5
        df = _df_from_bars(bars)
        df["atr"] = 0.20
        events = detect_hunt_events(df, level=150.000, side="resistance", k_atr=1.0)
        assert len(events) == 1
        assert events[0]["bar_idx"] == 5
        assert events[0]["wick_excursion"] == pytest.approx(0.30, abs=0.01)


class TestAnalyzeHuntsForLevel:
    def test_returns_hunt_stat_with_required_fields(self):
        bars = [_make_bar(149.95, 149.99, 149.92, 149.96)] * 5
        bars.append(_make_bar(149.95, 150.30, 149.90, 149.92))
        bars += [_make_bar(149.85 - i*0.10, 149.90 - i*0.10,
                           149.60 - i*0.10, 149.65 - i*0.10) for i in range(5)]
        df = _df_from_bars(bars)
        df["atr"] = 0.20

        level = SRLevel(price=150.000, touch_count=3, age_bars=10,
                        obviousness=0.8, kde_density=5.0)
        stat = analyze_hunts_for_level(df, level, side="resistance",
                                       k_atr=1.0, reversal_lookahead=3)
        assert isinstance(stat, HuntStat)
        assert stat.n_hunts == 1
        assert "p90" in stat.wick_excursion_dist
        assert stat.post_hunt_reversal_wr == 1.0

    def test_zero_hunts_returns_empty_stat(self):
        bars = [_make_bar(149.95, 149.99, 149.90, 149.96)] * 30
        df = _df_from_bars(bars)
        df["atr"] = 0.20
        level = SRLevel(price=150.000, touch_count=3, age_bars=10,
                        obviousness=0.8, kde_density=5.0)
        stat = analyze_hunts_for_level(df, level, side="resistance", k_atr=1.0)
        assert stat.n_hunts == 0
