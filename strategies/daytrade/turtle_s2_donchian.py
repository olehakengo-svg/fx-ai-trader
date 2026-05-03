"""
Turtle System 2 — 55-day Donchian D1 breakout (USDJPY long-only Shadow)

Source / lineage
================
- Dennis & Eckhardt (1983) Turtle Trading rules, "System 2" (55-day Donchian).
- Wave 1 BT report: ``wiki/learning/s2-turtle-55day-bt-2026-05-03.md``
  - USDJPY long-only (15.3y D1, N=50): EV +207p, PF 1.99, OOS PF 1.99,
    Wilson 95% lo +0.21, Bonferroni p=0.172 (Verdict B — Shadow promote).
  - USDJPY short-only / GBPJPY both directions: Reject (do NOT deploy).
- Catalogue §B-1 (`wiki/learning/global-retail-fx-edges-2026-05-03.md`).

Tier policy
===========
- **Shadow only** (`is_shadow=1`). Live promotion gate: live shadow N ≥ 80 AND
  Bonferroni p < 0.10 AND OOS PF maintained — handled by promotion governance,
  NOT by this strategy module.
- USDJPY long-only is the *only* deployable cell. SELL and other pairs return
  None; `evaluate()` is a no-op for them.

Strategy spec (Pre-reg LOCK 2026-05-03)
========================================
- TF: D1 (daily close, NY 17:00 ≈ 21:00 UTC).
- Entry (long): D1 close > prior 55-day high (Donchian uses ``shift(1)`` so
  the current bar is excluded).
- Stop: 2N below entry, where N = 20-day ATR.
- Pyramiding (anti-Martingale): each +0.5N favourable move adds 1 unit, max 4
  total units. Each unit carries its **own** independent 2N stop measured from
  its **own** entry. Pyramid logic lives in :mod:`modules.turtle_s2_pyramid`.
- Exit: D1 close < prior 20-day low → close all units (full exit).
- No System-1 "skip after winner" filter (this is System 2).
- No MA filter (per ``feedback_ma_filter_breaks_mr``).

Regime / size guards
====================
- BoJ intervention zone: USDJPY ≥ 158.0 → unit count halved (max_units 4 → 2);
  USDJPY ≥ 160.0 → entry skipped entirely.
- An external *intervention day* registry can flag a forced skip on the entry
  bar (the pyramid manager already prevents adding units on those days).

Units & audit logging
=====================
The strategy itself only emits the **unit-1** entry signal (the Donchian
breakout). Subsequent unit additions are emitted by
:class:`modules.turtle_s2_pyramid.TurtleS2PyramidManager` as separate Shadow
trades, each with ``entry_type='turtle_s2_unit_N'`` (N=1..4) so OANDA audit
joins can distinguish them from native pyramid (PYR) records that the system
deprecated 2026-05-01.

Module name policy
==================
- Family ``entry_type`` strings exposed to demo_db / oanda_audit:
  ``turtle_s2_unit_1`` ... ``turtle_s2_unit_4``.
- A non-unit *signal-only* identifier ``turtle_s2_donchian_d1`` is reserved
  for upstream filters / KB lookups (e.g. tier-master and confidence rules).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import pandas as pd


# -----------------------------------------------------------------------------
# Pre-reg LOCK parameters (2026-05-03). Do NOT tune without quant gate.
# -----------------------------------------------------------------------------
DONCHIAN_LEN: int = 55          # entry channel length
EXIT_DON_LEN: int = 20          # opposite-side exit channel length
ATR_LEN: int = 20               # N (true range) lookback
STOP_N_MULT: float = 2.0        # initial stop = 2N
PYRAMID_STEP_N: float = 0.5     # add unit every +0.5N favourable
MAX_UNITS_DEFAULT: int = 4
INTERVENTION_HALF_LEVEL: float = 158.0  # USDJPY mid-rate gate
INTERVENTION_BLOCK_LEVEL: float = 160.0  # absolute entry-skip
SUPPORTED_PAIRS: frozenset = frozenset({"USD_JPY"})  # long-only deploy whitelist
ENTRY_TYPE_FAMILY: str = "turtle_s2_donchian_d1"
UNIT_ENTRY_TYPE_PREFIX: str = "turtle_s2_unit_"


@dataclass(frozen=True)
class TurtleS2Signal:
    """Lightweight result struct for the D1 evaluator.

    Mirrors the subset of :class:`strategies.base.Candidate` that downstream
    Shadow-emit consumers need, plus per-unit metadata used by the pyramid
    manager and audit log.
    """

    signal: str                 # "BUY" only (long-only deploy)
    entry: float                # close at entry (BT) / next-open (live)
    sl: float                   # 2N below entry
    tp: float                   # placeholder; real exit is via 20-day low
    atr_n: float                # 20-day ATR snapshot at entry (used by pyramid manager)
    pyramid_step: float         # +ATR delta that triggers the next unit
    max_units: int
    pair: str
    bar_time: pd.Timestamp
    reasons: list
    entry_type: str = "turtle_s2_unit_1"
    unit_index: int = 1
    confidence: int = 50        # BT verdict B → conservative confidence
    score: float = 5.0
    is_shadow: bool = True      # FORCE: this strategy never emits live trades


def _atr_wilder(df: pd.DataFrame, length: int) -> pd.Series:
    """Wilder's smoothed Average True Range, returned aligned to ``df.index``.

    Uses the classical Wilder recurrence (``alpha = 1/length``) rather than
    pandas' default EMA so that BT and live agree to the last basis point.
    """
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    # Wilder smoothing == EMA with alpha=1/length, adjust=False
    return tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def _donchian_high(close_or_high: pd.Series, length: int) -> pd.Series:
    """Highest high over the **prior** ``length`` bars (current bar excluded)."""
    return close_or_high.shift(1).rolling(length, min_periods=length).max()


def _donchian_low(close_or_low: pd.Series, length: int) -> pd.Series:
    """Lowest low over the prior ``length`` bars (current bar excluded)."""
    return close_or_low.shift(1).rolling(length, min_periods=length).min()


def is_intervention_day(bar_time: pd.Timestamp,
                        intervention_days: Sequence[pd.Timestamp]) -> bool:
    """True iff ``bar_time`` (D1) falls within ±1 calendar day of a known
    BoJ intervention. The skip window is conservative: we exclude the
    intervention day itself plus the next bar to avoid re-entering into the
    central-bank fade."""
    if not intervention_days:
        return False
    bt_date = pd.Timestamp(bar_time).normalize()
    for d in intervention_days:
        d_norm = pd.Timestamp(d).normalize()
        if abs((bt_date - d_norm).days) <= 1:
            return True
    return False


def evaluate_d1(df: pd.DataFrame,
                pair: str,
                *,
                intervention_days: Optional[Sequence[pd.Timestamp]] = None,
                max_units: int = MAX_UNITS_DEFAULT) -> Optional[TurtleS2Signal]:
    """Evaluate the D1 Turtle System 2 entry on the **most recent** bar of ``df``.

    Args:
        df: D1 OHLCV with columns ``Open / High / Low / Close`` and a
            ``DatetimeIndex``.  Must contain at least
            ``DONCHIAN_LEN + 1`` rows (= 56) for the breakout to be defined.
        pair: instrument symbol; must be in :data:`SUPPORTED_PAIRS`
            (currently only ``USD_JPY``). All other pairs return ``None``.
        intervention_days: optional list of known BoJ intervention dates.
            Entries within ±1 day of an intervention are skipped (per Wave 1
            BT note 5.3 + spec note 3).
        max_units: hard cap on units, default 4. Halved automatically when
            the entry close is in the BoJ intervention zone (≥ 158.0).

    Returns:
        :class:`TurtleS2Signal` if the breakout fires, else ``None``.
    """
    if pair not in SUPPORTED_PAIRS:
        return None  # SELL side and non-USDJPY pairs are explicitly rejected
    if df is None or len(df) < DONCHIAN_LEN + 1:
        return None
    required_cols = {"Open", "High", "Low", "Close"}
    if not required_cols.issubset(df.columns):
        return None

    close = df["Close"].astype(float)
    don_high = _donchian_high(close, DONCHIAN_LEN)
    atr_series = _atr_wilder(df, ATR_LEN)

    last_idx = df.index[-1]
    last_close = float(close.iloc[-1])
    prior_high = don_high.iloc[-1]
    atr_n = atr_series.iloc[-1]

    if pd.isna(prior_high) or pd.isna(atr_n) or atr_n <= 0:
        return None

    # 1) Breakout gate
    if not (last_close > float(prior_high)):
        return None

    # 2) BoJ intervention regime guards
    if last_close >= INTERVENTION_BLOCK_LEVEL:
        return None  # 160+ — entry blocked outright
    effective_max_units = max_units
    if last_close >= INTERVENTION_HALF_LEVEL:
        # halve units (round down, but min 1) — preserves anti-Martingale design
        effective_max_units = max(1, max_units // 2)

    if is_intervention_day(last_idx, intervention_days or []):
        return None

    # 3) Build the signal
    entry = last_close
    sl = entry - STOP_N_MULT * float(atr_n)
    # Placeholder TP — real exit is the 20-day low rule, which the pyramid
    # manager evaluates each subsequent D1 close. We carry a "soft" TP at
    # +20N for monitoring/UI; trade closure is exit-driven, not TP-driven.
    tp = entry + 20.0 * float(atr_n)

    reasons = [
        f"✅ Turtle S2 BUY: D1 close={entry:.3f} > prior55High={float(prior_high):.3f}",
        f"📊 N(20d ATR)={float(atr_n):.4f}  initial SL={sl:.3f}  pyramid step=+{PYRAMID_STEP_N}N",
        f"⚠️ Shadow only — live promotion blocked until N≥80 + Bonferroni p<0.10",
    ]
    if last_close >= INTERVENTION_HALF_LEVEL:
        reasons.append(
            f"⚠️ BoJ intervention zone ({INTERVENTION_HALF_LEVEL}≤close<{INTERVENTION_BLOCK_LEVEL}) "
            f"— max_units halved {max_units}→{effective_max_units}"
        )

    return TurtleS2Signal(
        signal="BUY",
        entry=entry,
        sl=sl,
        tp=tp,
        atr_n=float(atr_n),
        pyramid_step=PYRAMID_STEP_N * float(atr_n),
        max_units=effective_max_units,
        pair=pair,
        bar_time=last_idx,
        reasons=reasons,
        entry_type=f"{UNIT_ENTRY_TYPE_PREFIX}1",
        unit_index=1,
    )


def is_exit_signal(df: pd.DataFrame) -> bool:
    """Return True iff the most recent D1 close < prior 20-day low.

    The pyramid manager calls this every D1 close; on True it closes ALL
    open units (exit is symmetric / full-position).
    """
    if df is None or len(df) < EXIT_DON_LEN + 1:
        return False
    if "Close" not in df.columns or "Low" not in df.columns:
        return False
    last_close = float(df["Close"].iloc[-1])
    prior_low = _donchian_low(df["Low"].astype(float), EXIT_DON_LEN).iloc[-1]
    if pd.isna(prior_low):
        return False
    return last_close < float(prior_low)


def signal_to_shadow_emit(sig: TurtleS2Signal) -> dict:
    """Convert the strategy signal into the dict shape expected by
    :func:`modules.demo_trader.DemoTrader._tick` shadow_emit_signals path.

    Mirrors the contract documented at modules/demo_trader.py L2779-2821.
    """
    return {
        "signal": sig.signal,
        "entry": sig.entry,
        "sl": sig.sl,
        "tp": sig.tp,
        "entry_type": sig.entry_type,
        "confidence": sig.confidence,
        "score": sig.score,
        "reasons": list(sig.reasons),
    }
