import math

import pandas as pd

from tools import s6_chart_pattern_detector as s6


def _bars(rows):
    idx = pd.to_datetime([r[0] for r in rows], utc=True)
    return pd.DataFrame(
        {
            "open": [r[1] for r in rows],
            "high": [r[2] for r in rows],
            "low": [r[3] for r in rows],
            "close": [r[4] for r in rows],
            "volume": 100,
        },
        index=idx,
    )


def test_swing_pivot_detection_uses_strict_k3_window():
    rows = []
    highs = [10, 11, 12, 13, 20, 14, 13, 12, 11, 10, 9]
    lows = [9, 8, 7, 6, 5, 4, 3, 2, 6, 7, 8]
    for i, (h, l) in enumerate(zip(highs, lows)):
        rows.append((f"2026-01-01 00:{i * 5:02d}", (h + l) / 2, h, l, (h + l) / 2))
    pivots = s6.detect_swing_pivots(_bars(rows), k=3)
    assert [(p.kind, p.pos) for p in pivots] == [("H", 4), ("L", 7)]


def test_atr_wilder_matches_manual_recursive_values():
    df = _bars(
        [
            ("2026-01-01 00:00", 10, 12, 9, 11),
            ("2026-01-01 00:05", 11, 13, 10, 12),
            ("2026-01-01 00:10", 12, 14, 11, 13),
            ("2026-01-01 00:15", 13, 16, 12, 15),
            ("2026-01-01 00:20", 15, 17, 14, 16),
        ]
    )
    atr = s6.compute_atr_wilder(df, period=3)
    assert math.isnan(atr.iloc[0])
    assert math.isnan(atr.iloc[1])
    assert math.isclose(atr.iloc[2], 3.0)
    assert math.isclose(atr.iloc[3], (3.0 * 2 + 4.0) / 3)
    assert math.isclose(atr.iloc[4], (((3.0 * 2 + 4.0) / 3) * 2 + 3.0) / 3)


def test_bar_close_gate_rejects_wick_only_breakout():
    df = s6.synthetic_pattern_bars("ascending_triangle", wick_only=True)
    signals = s6.detect_chart_patterns(df)
    assert not [sig for sig in signals if sig.pattern_name == "ascending_triangle"]


def test_reentry_dedup_keeps_one_signal_per_pivot_tuple():
    df = s6.synthetic_pattern_bars("double_bottom", duplicate_breakout=True)
    signals = [sig for sig in s6.detect_chart_patterns(df) if sig.pattern_name == "double_bottom"]
    assert len(signals) == 1


def test_sqlite_schema_contains_locked_unique_tuple():
    assert "chart_pattern_signals" in s6.SQLITE_DDL
    assert "UNIQUE(pattern_id, pair, timeframe, pivot_anchor_ts, pivot_opposite_ts)" in s6.SQLITE_DDL


def test_pattern_catalog_locks_12_ids_and_directions():
    assert [p.pattern_id for p in s6.PATTERNS] == list(range(1, 13))
    assert sum(p.direction == "BUY" for p in s6.PATTERNS) == 6
    assert sum(p.direction == "SELL" for p in s6.PATTERNS) == 6


def test_detector_self_test_covers_all_12_patterns():
    results = s6.run_self_test()
    assert set(results) == {p.name for p in s6.PATTERNS}
    assert all(results.values())


def test_sl_tp_entry_are_analytic_for_each_pattern():
    for spec in s6.PATTERNS:
        df = s6.synthetic_pattern_bars(spec.name)
        signals = [sig for sig in s6.detect_chart_patterns(df) if sig.pattern_name == spec.name]
        assert signals, spec.name
        sig = signals[0]
        expected = s6.synthetic_expected_levels(spec.name)
        assert math.isclose(sig.entry_px, expected["entry_px"], abs_tol=1e-9), spec.name
        assert math.isclose(sig.sl_px, expected["sl_px"], abs_tol=1e-9), spec.name
        assert math.isclose(sig.tp_px, expected["tp_px"], abs_tol=1e-9), spec.name


def test_ascending_triangle_synthetic_hit():
    assert _hits("ascending_triangle")


def test_rising_wedge_synthetic_hit():
    assert _hits("rising_wedge")


def test_bull_flag_synthetic_hit():
    assert _hits("bull_flag")


def test_descending_triangle_synthetic_hit():
    assert _hits("descending_triangle")


def test_falling_wedge_synthetic_hit():
    assert _hits("falling_wedge")


def test_bear_flag_synthetic_hit():
    assert _hits("bear_flag")


def test_double_bottom_synthetic_hit():
    assert _hits("double_bottom")


def test_triple_bottom_synthetic_hit():
    assert _hits("triple_bottom")


def test_inverse_head_shoulders_synthetic_hit():
    assert _hits("inverse_head_shoulders")


def test_double_top_synthetic_hit():
    assert _hits("double_top")


def test_triple_top_synthetic_hit():
    assert _hits("triple_top")


def test_head_shoulders_synthetic_hit():
    assert _hits("head_shoulders")


def _hits(pattern_name):
    df = s6.synthetic_pattern_bars(pattern_name)
    signals = [sig for sig in s6.detect_chart_patterns(df) if sig.pattern_name == pattern_name]
    assert len(signals) >= 1
    assert signals[0].duration_bars >= s6.MIN_DURATION_BARS
    assert signals[0].pattern_height_atr >= 1.5
    return True
