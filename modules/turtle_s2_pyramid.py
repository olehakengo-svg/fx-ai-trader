"""
Turtle System 2 — Pyramid Unit Manager (Shadow tier)

Manages anti-Martingale unit additions for the
:mod:`strategies.daytrade.turtle_s2_donchian` strategy. Each unit:

- carries its **own** independent 2N stop measured from its own entry,
- is added when the D1 close advances by ``+0.5N`` from the *previous unit's
  entry* (where N = entry-time ATR),
- is recorded as a separate Shadow row in ``trades``/``oanda_audit`` with
  ``entry_type = "turtle_s2_unit_<idx>"`` (idx ∈ 1..max_units).

The manager is **read-only** with respect to OANDA Live: every unit it opens
goes through ``demo_db.open_trade(..., is_shadow=True)``. There is no code
path that converts a unit into a live OANDA position. Live promotion is
enforced externally by the tier-master / promotion gate (live shadow N ≥ 80
+ Bonferroni p < 0.10) — see ``feedback_live_shadow_separation``.

Anti-Martingale guards
----------------------
- ``max_units`` is enforced as a hard ceiling on the number of unit rows.
- Each unit's stop is computed from that unit's own entry and the entry-time
  ATR, **not** from the prior unit's stop. This is critical: classical
  Turtle "risk-free pyramiding" (moving prior stops up to break-even) is
  what 2026-05-01's ``halt-pyramid`` audit removed; we keep stops independent
  to preserve unit-level loss budgets.
- An exit signal (D1 close < prior 20-day low) closes ALL units atomically.
- BoJ intervention day registry forces ``add_unit`` to no-op on flagged dates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence

import pandas as pd

from strategies.daytrade.turtle_s2_donchian import (
    ATR_LEN,
    EXIT_DON_LEN,
    PYRAMID_STEP_N,
    STOP_N_MULT,
    UNIT_ENTRY_TYPE_PREFIX,
    TurtleS2Signal,
    is_exit_signal,
    is_intervention_day,
)


@dataclass
class UnitState:
    """One open Shadow unit."""
    idx: int                # 1..max_units
    entry_price: float
    sl: float               # 2N below entry (long)
    atr_n_at_entry: float
    bar_time: pd.Timestamp
    entry_type: str         # "turtle_s2_unit_<idx>"
    db_trade_id: Optional[int] = None  # row id from demo_db.open_trade


@dataclass
class TurtleS2PyramidManager:
    """In-memory tracker for the active S2 trade (zero or one trade at a time).

    A "trade" is a sequence of 1..N units sharing a common entry breakout. On
    exit-signal the manager closes all units at the prior 20-day low (or at
    the current D1 close, depending on configuration).

    Wiring
    ------
    The owner (typically a daily cron / runner) injects two callables:

    - ``open_trade_fn(*, direction, entry_price, sl, tp, entry_type,
        confidence, tf, reasons, score, mode, instrument, is_shadow)``
        → returns the new trade id. Mirrors ``demo_db.open_trade`` signature.
    - ``close_trade_fn(trade_id, exit_price, ...)`` → close handler.

    Tests pass in mocks; production code passes ``demo_db`` bound methods.
    """
    pair: str
    open_trade_fn: Callable[..., int]
    close_trade_fn: Callable[..., None]
    mode: str = "daytrade"
    tf: str = "1d"
    intervention_days: Sequence[pd.Timestamp] = field(default_factory=tuple)
    units: List[UnitState] = field(default_factory=list)
    initial_signal: Optional[TurtleS2Signal] = None

    # ------------------------------------------------------------------ helpers
    @property
    def is_active(self) -> bool:
        """True iff at least one unit is currently open."""
        return bool(self.units)

    @property
    def n_units(self) -> int:
        return len(self.units)

    @property
    def max_units(self) -> int:
        if self.initial_signal is None:
            return 0
        return self.initial_signal.max_units

    @property
    def atr_n(self) -> float:
        if self.initial_signal is None:
            return 0.0
        return self.initial_signal.atr_n

    # ------------------------------------------------------------------- entry
    def open_initial(self, sig: TurtleS2Signal) -> UnitState:
        """Open unit #1 from the breakout signal. Idempotent on re-call:
        if a trade is already active, this raises a guarded ValueError so
        the caller can detect a duplicate entry attempt before it pollutes
        the audit log."""
        if self.is_active:
            raise ValueError(
                f"[turtle_s2] open_initial called while {self.n_units} unit(s) "
                f"already active for {self.pair}; refusing to double-enter."
            )
        if sig.signal != "BUY":
            raise ValueError(f"[turtle_s2] only BUY supported, got {sig.signal!r}")

        unit = UnitState(
            idx=1,
            entry_price=sig.entry,
            sl=sig.sl,
            atr_n_at_entry=sig.atr_n,
            bar_time=sig.bar_time,
            entry_type=f"{UNIT_ENTRY_TYPE_PREFIX}1",
        )
        unit.db_trade_id = self._persist_unit(unit, sig.tp, sig.reasons,
                                               sig.confidence, sig.score)
        self.units.append(unit)
        self.initial_signal = sig
        return unit

    # ----------------------------------------------------------------- pyramid
    def maybe_add_unit(self, df: pd.DataFrame) -> Optional[UnitState]:
        """Called on each D1 close. Returns the newly-added :class:`UnitState`
        if a unit was added on this bar, else ``None``.

        Conditions to add unit ``k+1`` (for active unit count k):
            1. ``k < max_units``
            2. last D1 close >= prev_unit.entry_price + 0.5 * atr_n_at_initial
            3. bar_time is NOT a flagged intervention day
            4. exit-signal not active (checked elsewhere — caller must call
               :meth:`maybe_close_all` first)
        """
        if not self.is_active or self.initial_signal is None:
            return None
        if self.n_units >= self.max_units:
            return None
        if df is None or len(df) == 0:
            return None

        last_idx = df.index[-1]
        if is_intervention_day(last_idx, self.intervention_days):
            return None

        last_close = float(df["Close"].iloc[-1])
        prev_unit = self.units[-1]
        threshold = prev_unit.entry_price + PYRAMID_STEP_N * self.atr_n
        if last_close < threshold:
            return None

        new_idx = self.n_units + 1
        sl = last_close - STOP_N_MULT * self.atr_n
        tp = last_close + 20.0 * self.atr_n  # soft TP, exit is rule-driven
        reasons = [
            f"✅ Turtle S2 PYRAMID +unit{new_idx}: D1 close={last_close:.3f} "
            f"≥ prev_unit_entry({prev_unit.entry_price:.3f}) + 0.5N",
            f"📊 N={self.atr_n:.4f}  unit SL={sl:.3f} (independent 2N)",
            f"⚠️ Shadow only — anti-Martingale, max_units={self.max_units}",
        ]
        unit = UnitState(
            idx=new_idx,
            entry_price=last_close,
            sl=sl,
            atr_n_at_entry=self.atr_n,
            bar_time=last_idx,
            entry_type=f"{UNIT_ENTRY_TYPE_PREFIX}{new_idx}",
        )
        unit.db_trade_id = self._persist_unit(unit, tp, reasons,
                                               confidence=50, score=4.5)
        self.units.append(unit)
        return unit

    # --------------------------------------------------------------------- exit
    def maybe_close_all(self, df: pd.DataFrame) -> List[UnitState]:
        """Close all active units if the D1 exit rule fires (close < prior
        20-day low). Returns the list of closed units (empty if no exit)."""
        if not self.is_active:
            return []
        if not is_exit_signal(df):
            return []
        last_close = float(df["Close"].iloc[-1])
        closed: List[UnitState] = []
        for unit in self.units:
            try:
                self.close_trade_fn(
                    trade_id=unit.db_trade_id,
                    exit_price=last_close,
                    reason=f"turtle_s2_exit_d1_close_lt_prior{EXIT_DON_LEN}low",
                )
            except Exception as err:  # pragma: no cover - defensive
                print(f"[turtle_s2] close error unit{unit.idx}: {err}", flush=True)
            closed.append(unit)
        self.units.clear()
        self.initial_signal = None
        return closed

    def force_stop_unit(self, idx: int, exit_price: float) -> Optional[UnitState]:
        """Close a single unit at its own stop (tested separately; production
        normally uses ``maybe_close_all`` since the 20-day exit closes all)."""
        for i, unit in enumerate(self.units):
            if unit.idx == idx:
                try:
                    self.close_trade_fn(
                        trade_id=unit.db_trade_id,
                        exit_price=exit_price,
                        reason="turtle_s2_unit_stop",
                    )
                except Exception as err:  # pragma: no cover - defensive
                    print(f"[turtle_s2] force_stop unit{idx}: {err}", flush=True)
                self.units.pop(i)
                if not self.units:
                    self.initial_signal = None
                return unit
        return None

    # -------------------------------------------------------------- internals
    def _persist_unit(self, unit: UnitState, tp: float, reasons: List[str],
                      confidence: int, score: float) -> int:
        """Record the unit in the trades DB as a Shadow row."""
        return self.open_trade_fn(
            direction="BUY",
            entry_price=unit.entry_price,
            sl=unit.sl,
            tp=tp,
            entry_type=unit.entry_type,
            confidence=confidence,
            tf=self.tf,
            reasons=list(reasons),
            score=score,
            mode=self.mode,
            instrument=self.pair,
            is_shadow=True,  # **HARD-CODED**: never live
        )
