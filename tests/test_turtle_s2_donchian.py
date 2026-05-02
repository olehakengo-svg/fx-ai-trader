"""Tests for the S2 Turtle Donchian D1 strategy + pyramid manager.

Coverage:
    - Donchian breakout fires only when D1 close exceeds prior 55-day high.
    - SL is 2N below entry where N = Wilder ATR(20).
    - SUPPORTED_PAIRS gate rejects USDJPY-short / GBPJPY / others.
    - BoJ intervention regime: 158-160 zone halves units, ≥160 blocks entry.
    - 20-day low exit closes ALL active units.
    - Pyramid adds units at +0.5N, capped at max_units, with INDEPENDENT 2N stops.
    - shadow_emit dict shape matches modules/demo_trader.py contract.
    - Pyramid manager always opens trades with is_shadow=True.
"""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
import pytest

from modules.turtle_s2_pyramid import TurtleS2PyramidManager
from strategies.daytrade.turtle_s2_donchian import (
    ATR_LEN,
    DONCHIAN_LEN,
    EXIT_DON_LEN,
    INTERVENTION_BLOCK_LEVEL,
    INTERVENTION_HALF_LEVEL,
    PYRAMID_STEP_N,
    STOP_N_MULT,
    SUPPORTED_PAIRS,
    UNIT_ENTRY_TYPE_PREFIX,
    evaluate_d1,
    is_exit_signal,
    is_intervention_day,
    signal_to_shadow_emit,
)


# --------------------------------------------------------------------------
# Fixtures: synthetic D1 data engineered to fire / not fire the breakout
# --------------------------------------------------------------------------
def _build_flat_then_breakout(
    n_pre: int = 60,
    flat_price: float = 145.0,
    breakout_close: float = 147.5,
    daily_range: float = 0.4,
) -> pd.DataFrame:
    """``n_pre`` flat bars at ~``flat_price`` then a final bar that closes above
    the 55-day high. Close > prior 55-high triggers the breakout."""
    idx = pd.date_range("2024-01-01", periods=n_pre + 1, freq="D")
    rng = np.random.default_rng(42)
    closes = flat_price + rng.normal(0, 0.05, size=n_pre)
    highs = closes + daily_range / 2
    lows = closes - daily_range / 2
    opens = closes - rng.normal(0, 0.02, size=n_pre)

    # Final bar: high enough to be > prior 55-day high
    closes = np.append(closes, breakout_close)
    highs = np.append(highs, breakout_close + 0.1)
    lows = np.append(lows, breakout_close - 0.5)
    opens = np.append(opens, flat_price + 0.05)

    df = pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes},
        index=idx,
    )
    return df


def _df_no_breakout(n: int = 80, base: float = 145.0) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    rng = np.random.default_rng(7)
    closes = base + rng.normal(0, 0.10, size=n)
    return pd.DataFrame(
        {
            "Open": closes - 0.05,
            "High": closes + 0.20,
            "Low": closes - 0.20,
            "Close": closes,
        },
        index=idx,
    )


# --------------------------------------------------------------------------
# evaluate_d1 — entry logic
# --------------------------------------------------------------------------
class TestEvaluateD1:
    def test_breakout_long_fires(self):
        df = _build_flat_then_breakout()
        sig = evaluate_d1(df, pair="USD_JPY")
        assert sig is not None
        assert sig.signal == "BUY"
        assert sig.entry == pytest.approx(df["Close"].iloc[-1])
        assert sig.atr_n > 0
        assert sig.sl == pytest.approx(sig.entry - STOP_N_MULT * sig.atr_n)
        assert sig.unit_index == 1
        assert sig.entry_type == f"{UNIT_ENTRY_TYPE_PREFIX}1"
        assert sig.is_shadow is True

    def test_no_breakout_returns_none(self):
        df = _df_no_breakout()
        assert evaluate_d1(df, pair="USD_JPY") is None

    def test_short_pair_rejected(self):
        # SELL side / GBPJPY are explicitly outside SUPPORTED_PAIRS — we cannot
        # construct a SELL signal at all from this evaluator.
        df = _build_flat_then_breakout()
        assert evaluate_d1(df, pair="GBP_JPY") is None
        assert evaluate_d1(df, pair="EUR_USD") is None

    def test_supported_pairs_is_just_usdjpy(self):
        # Wave-1 BT verdict: only USD_JPY long-only deployable.
        assert SUPPORTED_PAIRS == frozenset({"USD_JPY"})

    def test_insufficient_history_returns_none(self):
        # < 56 bars → cannot compute prior-55-day high.
        df = _build_flat_then_breakout(n_pre=30)
        assert evaluate_d1(df, pair="USD_JPY") is None

    def test_intervention_block_level_skips_entry(self):
        # USDJPY ≥ 160 → no entry regardless of breakout.
        df = _build_flat_then_breakout(
            flat_price=155.0, breakout_close=INTERVENTION_BLOCK_LEVEL + 0.5
        )
        assert evaluate_d1(df, pair="USD_JPY") is None

    def test_intervention_half_zone_halves_units(self):
        # 158 ≤ close < 160 → max_units halved.
        df = _build_flat_then_breakout(
            flat_price=155.0, breakout_close=INTERVENTION_HALF_LEVEL + 0.5
        )
        sig = evaluate_d1(df, pair="USD_JPY", max_units=4)
        assert sig is not None
        assert sig.max_units == 2  # halved 4→2

    def test_intervention_day_skip(self):
        df = _build_flat_then_breakout()
        intervention = [df.index[-1]]  # mark today as intervention
        assert evaluate_d1(df, pair="USD_JPY",
                           intervention_days=intervention) is None

    def test_signal_to_shadow_emit_shape(self):
        df = _build_flat_then_breakout()
        sig = evaluate_d1(df, pair="USD_JPY")
        emit = signal_to_shadow_emit(sig)
        # demo_trader.py L2784-2807 contract
        assert emit["signal"] == "BUY"
        assert emit["entry"] == sig.entry
        assert emit["sl"] == sig.sl
        assert emit["tp"] == sig.tp
        assert emit["entry_type"] == sig.entry_type
        assert "confidence" in emit
        assert "reasons" in emit and isinstance(emit["reasons"], list)


# --------------------------------------------------------------------------
# is_exit_signal — 20-day low rule
# --------------------------------------------------------------------------
class TestExitSignal:
    def test_close_below_prior_20day_low_triggers(self):
        idx = pd.date_range("2024-01-01", periods=30, freq="D")
        # 20 bars at ~150, then drop the final close way below the prior 20-day low.
        closes = np.full(30, 150.0)
        closes[-1] = 145.0
        lows = closes - 0.3
        df = pd.DataFrame(
            {"Open": closes, "High": closes + 0.3, "Low": lows, "Close": closes},
            index=idx,
        )
        # Prior 20-day low ≈ 149.7 (20 bars before final, all ≈150, low ≈149.7).
        assert is_exit_signal(df) is True

    def test_close_above_does_not_trigger(self):
        idx = pd.date_range("2024-01-01", periods=30, freq="D")
        closes = np.full(30, 150.0)
        df = pd.DataFrame(
            {"Open": closes, "High": closes + 0.3, "Low": closes - 0.3, "Close": closes},
            index=idx,
        )
        assert is_exit_signal(df) is False


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def test_intervention_day_window_pm1():
    base = pd.Timestamp("2024-07-12")
    assert is_intervention_day(base, [base]) is True
    assert is_intervention_day(base + pd.Timedelta(days=1), [base]) is True
    assert is_intervention_day(base - pd.Timedelta(days=1), [base]) is True
    assert is_intervention_day(base + pd.Timedelta(days=2), [base]) is False
    assert is_intervention_day(base, []) is False


# --------------------------------------------------------------------------
# Pyramid manager — Anti-Martingale unit additions
# --------------------------------------------------------------------------
class _MockDB:
    """Minimal mock that captures open/close calls for unit-level audit assertions."""

    def __init__(self):
        self.opens: List[dict] = []
        self.closes: List[dict] = []
        self._next_id = 0

    def open_trade(self, **kwargs) -> int:
        self._next_id += 1
        kwargs["_id"] = self._next_id
        self.opens.append(kwargs)
        return self._next_id

    def close_trade(self, **kwargs) -> None:
        self.closes.append(kwargs)


class TestPyramidManager:
    def setup_method(self):
        self.db = _MockDB()
        self.mgr = TurtleS2PyramidManager(
            pair="USD_JPY",
            open_trade_fn=self.db.open_trade,
            close_trade_fn=self.db.close_trade,
        )

    def test_open_initial_persists_unit_1_as_shadow(self):
        df = _build_flat_then_breakout()
        sig = evaluate_d1(df, pair="USD_JPY")
        unit = self.mgr.open_initial(sig)

        assert unit.idx == 1
        assert unit.entry_type == f"{UNIT_ENTRY_TYPE_PREFIX}1"
        assert len(self.db.opens) == 1
        opened = self.db.opens[0]
        # **CRITICAL**: pyramid manager MUST open Shadow only.
        assert opened["is_shadow"] is True
        assert opened["instrument"] == "USD_JPY"
        assert opened["entry_type"] == f"{UNIT_ENTRY_TYPE_PREFIX}1"
        assert opened["direction"] == "BUY"

    def test_open_initial_rejects_double_entry(self):
        df = _build_flat_then_breakout()
        sig = evaluate_d1(df, pair="USD_JPY")
        self.mgr.open_initial(sig)
        with pytest.raises(ValueError, match="double-enter"):
            self.mgr.open_initial(sig)

    def test_pyramid_adds_unit_at_plus_half_n(self):
        df = _build_flat_then_breakout()
        sig = evaluate_d1(df, pair="USD_JPY")
        self.mgr.open_initial(sig)

        # Build a new tail bar at entry + 0.5N + tiny epsilon → triggers unit 2
        new_close = sig.entry + PYRAMID_STEP_N * sig.atr_n + 0.001
        new_idx = df.index[-1] + pd.Timedelta(days=1)
        df_next = pd.concat([
            df,
            pd.DataFrame(
                {
                    "Open": [sig.entry],
                    "High": [new_close + 0.1],
                    "Low": [sig.entry - 0.1],
                    "Close": [new_close],
                },
                index=[new_idx],
            ),
        ])

        added = self.mgr.maybe_add_unit(df_next)
        assert added is not None
        assert added.idx == 2
        assert added.entry_type == f"{UNIT_ENTRY_TYPE_PREFIX}2"

    def test_pyramid_unit_has_independent_2n_stop(self):
        """Anti-Martingale: each unit's stop is computed from ITS OWN entry,
        NOT trailed up from a prior unit's stop. Critical for unit-level
        loss-budget integrity (halt-pyramid 2026-05-01 audit)."""
        df = _build_flat_then_breakout()
        sig = evaluate_d1(df, pair="USD_JPY")
        self.mgr.open_initial(sig)

        unit2_close = sig.entry + 1.0  # well beyond +0.5N for typical N
        new_idx = df.index[-1] + pd.Timedelta(days=1)
        df_next = pd.concat([
            df,
            pd.DataFrame(
                {
                    "Open": [sig.entry],
                    "High": [unit2_close + 0.1],
                    "Low": [sig.entry],
                    "Close": [unit2_close],
                },
                index=[new_idx],
            ),
        ])
        unit2 = self.mgr.maybe_add_unit(df_next)
        assert unit2 is not None
        # Unit 2 SL = unit2_entry - 2N (NOT unit1.sl-shifted)
        expected_sl = unit2_close - STOP_N_MULT * sig.atr_n
        assert unit2.sl == pytest.approx(expected_sl)
        assert unit2.sl != pytest.approx(self.mgr.units[0].sl)

    def test_pyramid_caps_at_max_units(self):
        df = _build_flat_then_breakout()
        sig = evaluate_d1(df, pair="USD_JPY", max_units=4)
        self.mgr.open_initial(sig)

        # Walk price up by N each step → triggers many unit adds
        cur_df = df
        last_idx = df.index[-1]
        for i in range(1, 10):  # try 9 additions, only 3 should land
            last_idx = last_idx + pd.Timedelta(days=1)
            new_close = sig.entry + i * sig.atr_n  # >> +0.5N
            cur_df = pd.concat([
                cur_df,
                pd.DataFrame(
                    {
                        "Open": [new_close],
                        "High": [new_close + 0.1],
                        "Low": [new_close - 0.1],
                        "Close": [new_close],
                    },
                    index=[last_idx],
                ),
            ])
            self.mgr.maybe_add_unit(cur_df)

        assert self.mgr.n_units == 4  # unit1 + 3 pyramid additions = 4 total

    def test_exit_closes_all_units(self):
        df = _build_flat_then_breakout()
        sig = evaluate_d1(df, pair="USD_JPY")
        self.mgr.open_initial(sig)

        # Add a couple of pyramid units
        cur_df = df
        last_idx = df.index[-1]
        for _ in range(2):
            last_idx = last_idx + pd.Timedelta(days=1)
            new_close = self.mgr.units[-1].entry_price + sig.atr_n
            cur_df = pd.concat([
                cur_df,
                pd.DataFrame(
                    {
                        "Open": [new_close],
                        "High": [new_close + 0.1],
                        "Low": [new_close - 0.1],
                        "Close": [new_close],
                    },
                    index=[last_idx],
                ),
            ])
            self.mgr.maybe_add_unit(cur_df)
        assert self.mgr.n_units >= 2

        # Construct an exit bar: close < prior 20-day low.
        prior_low = float(cur_df["Low"].astype(float).tail(20).min())
        exit_idx = last_idx + pd.Timedelta(days=1)
        cur_df = pd.concat([
            cur_df,
            pd.DataFrame(
                {
                    "Open": [prior_low - 1.0],
                    "High": [prior_low - 0.5],
                    "Low": [prior_low - 1.5],
                    "Close": [prior_low - 1.0],
                },
                index=[exit_idx],
            ),
        ])

        closed = self.mgr.maybe_close_all(cur_df)
        assert len(closed) >= 2
        assert self.mgr.is_active is False
        # Each unit produced a close call
        assert len(self.db.closes) >= 2

    def test_intervention_day_blocks_pyramid_add(self):
        df = _build_flat_then_breakout()
        sig = evaluate_d1(df, pair="USD_JPY")
        self.mgr.open_initial(sig)

        new_idx = df.index[-1] + pd.Timedelta(days=1)
        new_close = sig.entry + sig.atr_n
        df_next = pd.concat([
            df,
            pd.DataFrame(
                {
                    "Open": [new_close],
                    "High": [new_close + 0.1],
                    "Low": [new_close - 0.1],
                    "Close": [new_close],
                },
                index=[new_idx],
            ),
        ])
        # Mark today as an intervention day → pyramid must skip
        self.mgr.intervention_days = (new_idx,)
        added = self.mgr.maybe_add_unit(df_next)
        assert added is None
        assert self.mgr.n_units == 1
