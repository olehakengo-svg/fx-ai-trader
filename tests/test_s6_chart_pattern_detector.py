import csv
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tools.s6_chart_pattern_detector import (
    PATTERNS,
    SL_BUFFER_ATR,
    compute_atr_wilder,
    detect_chart_patterns,
    find_swing_pivots,
    insert_signals,
    synthetic_pattern_df,
)


def test_swing_pivot_detection_k3_synthetic_ohlc():
    idx = pd.date_range("2026-01-01", periods=11, freq="5min", tz="UTC")
    vals = np.array([5, 4, 3, 1, 3, 4, 6, 4, 3, 2, 3], dtype=float)
    df = pd.DataFrame({"open": vals, "high": vals + 0.1, "low": vals - 0.1, "close": vals}, index=idx)
    pivots = find_swing_pivots(df, k=3)
    assert [(p.idx, p.kind) for p in pivots] == [(3, "L"), (6, "H")]
    assert [p.confirm_idx for p in pivots] == [6, 9]


def test_atr_wilder_matches_manual_recurrence():
    idx = pd.date_range("2026-01-01", periods=16, freq="5min", tz="UTC")
    close = np.arange(100, 116, dtype=float)
    df = pd.DataFrame(
        {"open": close - 0.2, "high": close + 1.0, "low": close - 1.0, "close": close},
        index=idx,
    )
    atr = compute_atr_wilder(df, period=14)
    tr = [2.0] + [2.0 for _ in range(1, 16)]
    expected_13 = sum(tr[:14]) / 14
    expected_14 = ((expected_13 * 13) + tr[14]) / 14
    expected_15 = ((expected_14 * 13) + tr[15]) / 14
    assert np.isnan(atr.iloc[12])
    assert atr.iloc[13] == pytest.approx(expected_13)
    assert atr.iloc[14] == pytest.approx(expected_14)
    assert atr.iloc[15] == pytest.approx(expected_15)


@pytest.mark.parametrize("pattern_id", range(1, 13))
def test_each_locked_pattern_has_synthetic_hit(pattern_id):
    signals = detect_chart_patterns(synthetic_pattern_df(pattern_id))
    hits = [s for s in signals if s.pattern_id == pattern_id]
    assert hits, PATTERNS[pattern_id][0]
    assert hits[0].pattern_name == PATTERNS[pattern_id][0]
    assert hits[0].direction == PATTERNS[pattern_id][1]


def test_bar_close_gate_excludes_wick_only_breakout():
    df = synthetic_pattern_df(1)
    baseline = [s for s in detect_chart_patterns(df) if s.pattern_id == 1][0]
    signal_loc = df.index.get_loc(pd.Timestamp(baseline.signal_ts))
    gated = df.copy()
    breakout_level = json.loads(baseline.raw_geometry_json)["breakout_level"]
    gated.iloc[signal_loc, gated.columns.get_loc("high")] = breakout_level + 0.8
    gated.iloc[signal_loc, gated.columns.get_loc("close")] = breakout_level
    hits = [s for s in detect_chart_patterns(gated) if s.pattern_id == 1]
    assert not any(s.signal_ts == baseline.signal_ts for s in hits)


def test_reentry_dedup_unique_pivot_tuple_sqlite_insert_or_ignore():
    signals = [s for s in detect_chart_patterns(synthetic_pattern_df(7)) if s.pattern_id == 7]
    assert signals
    with sqlite3.connect(":memory:") as conn:
        inserted_first = insert_signals(conn, [signals[0]])
        inserted_second = insert_signals(conn, [signals[0]])
        dupes = conn.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT pattern_id, pivot_anchor_ts, pivot_opposite_ts, COUNT(*) n
              FROM chart_pattern_signals
              GROUP BY 1,2,3
              HAVING n > 1
            )
            """
        ).fetchone()[0]
    assert inserted_first == 1
    assert inserted_second == 0
    assert dupes == 0


@pytest.mark.parametrize("pattern_id", range(1, 13))
def test_sl_tp_entry_calculation_matches_raw_geometry(pattern_id):
    signal = [s for s in detect_chart_patterns(synthetic_pattern_df(pattern_id)) if s.pattern_id == pattern_id][0]
    raw = json.loads(signal.raw_geometry_json)
    pivots = raw["pivots"]
    atr_signal = raw["atr_at_signal"]
    lows = [p["price"] for p in pivots if p["kind"] == "L"]
    highs = [p["price"] for p in pivots if p["kind"] == "H"]
    breakout = raw["breakout_level"]
    height = raw["pattern_height"]
    if signal.direction == "BUY":
        assert signal.sl_px == pytest.approx(min(lows) - SL_BUFFER_ATR * atr_signal, abs=1e-7)
        move = abs(breakout - min(lows)) if pattern_id in (7, 8, 9) else height
        assert signal.tp_px == pytest.approx(signal.entry_px + move, abs=1e-7)
    else:
        assert signal.sl_px == pytest.approx(max(highs) + SL_BUFFER_ATR * atr_signal, abs=1e-7)
        move = abs(max(highs) - breakout) if pattern_id in (10, 11, 12) else height
        assert signal.tp_px == pytest.approx(signal.entry_px - move, abs=1e-7)


def test_regression_fixture_has_30_fixed_labels_and_replays_first_hit():
    path = Path("tests/fixtures/manual_chart_pattern_labels.csv")
    rows = list(csv.DictReader(path.open()))
    assert len(rows) == 30
    assert {int(r["pattern_id"]) for r in rows} == set(range(1, 13))
    for row in rows[:12]:
        pid = int(row["pattern_id"])
        signal = [s for s in detect_chart_patterns(synthetic_pattern_df(pid)) if s.pattern_id == pid][0]
        assert signal.signal_ts == row["signal_ts"]
        assert signal.entry_px == pytest.approx(float(row["entry_px"]))
        assert signal.sl_px == pytest.approx(float(row["sl_px"]))
        assert signal.tp_px == pytest.approx(float(row["tp_px"]))
