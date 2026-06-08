# Session Time Bias × BB RSI Reversion — Edge Cell Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add empirically-derived edge cell filter + SIZE lever to `session_time_bias` and `bb_rsi_reversion` to convert these from net-losing into net-positive expectancy strategies.

**Architecture:** Cell-Filter × SIZE Lever, no exit changes. 3 strategy file edits + 1 `Candidate` dataclass field + 1 `demo_trader.py` lot resolution hook + 3 new test files. Backward-compatible — existing `entry_type` preserved. Env flag rollback path.

**Tech Stack:** Python 3.9, pytest, dataclasses, existing `SignalContext` (`strategies/context.py`), existing `Candidate` (`strategies/base.py`), `modules/demo_trader.py` lot resolution.

**Source spec:** `docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md`

---

## File Structure

| File | Action | Lines | Responsibility |
|---|---|---|---|
| `strategies/base.py` | MODIFY | ~12-28 (Candidate) | Add `lot_multiplier: float = 1.0` field |
| `strategies/daytrade/session_time_bias.py` | MODIFY | top of `evaluate()` line ~100 | Add `_session_time_bias_edge_cell` filter |
| `strategies/scalp/bb_rsi.py` | MODIFY | top of `evaluate()` line ~76 | Add `_bb_rsi_edge_cell` filter |
| `modules/demo_trader.py` | MODIFY | ~5587-5600 (lot block) | Honor `candidate.lot_multiplier` |
| `tests/test_session_time_bias_edge_cell_filter.py` | CREATE | new | 12+ test cases |
| `tests/test_bb_rsi_reversion_pair_whitelist.py` | CREATE | new | 10+ test cases |
| `tests/test_candidate_lot_multiplier.py` | CREATE | new | 6+ test cases |
| `tests/test_demo_trader_lot_multiplier_integration.py` | CREATE | new | 4+ test cases |

**Decomposition rationale:** 4 implementation tasks (1 per modified file) + 4 test tasks. TDD order: write test → fail → impl → pass → commit. Each task is independent (Candidate field first, then strategies + demo_trader can be parallel, then integration).

**Env flags for rollback:**
- `SESSION_TIME_BIAS_CELL_FILTER_V1` = `"1"` (default ON, set `"0"` to bypass)
- `BB_RSI_REVERSION_PAIR_WHITELIST_V1` = `"1"` (default ON)

---

## Task 1: Add `lot_multiplier` field to Candidate dataclass

**Files:**
- Modify: `strategies/base.py:12-28`
- Test: `tests/test_candidate_lot_multiplier.py` (new)

- [ ] **Step 1: Read current Candidate definition**

Run:
```bash
sed -n '10,30p' strategies/base.py
```
Expected output: see the current `@dataclass class Candidate:` with fields ending at `sr_meta: Optional[dict] = None`.

- [ ] **Step 2: Write the failing test**

Create `tests/test_candidate_lot_multiplier.py`:
```python
"""Test Candidate.lot_multiplier field for edge cell SIZE lever.

Added 2026-06-08 per docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md
"""
import pytest
from strategies.base import Candidate


def _make_candidate(**overrides):
    """Helper: minimal valid Candidate."""
    defaults = dict(
        signal="BUY", confidence=70, sl=1.1000, tp=1.1050,
        reasons=["test"], entry_type="bb_rsi_reversion", score=1.0,
    )
    defaults.update(overrides)
    return Candidate(**defaults)


def test_lot_multiplier_default_is_1():
    c = _make_candidate()
    assert c.lot_multiplier == 1.0, "default must be 1.0 (no SIZE change)"


def test_lot_multiplier_can_be_set_to_1_5():
    c = _make_candidate(lot_multiplier=1.5)
    assert c.lot_multiplier == 1.5


def test_lot_multiplier_can_be_set_to_0_5():
    c = _make_candidate(lot_multiplier=0.5)
    assert c.lot_multiplier == 0.5


def test_lot_multiplier_can_be_zero_signals_skip():
    c = _make_candidate(lot_multiplier=0.0)
    assert c.lot_multiplier == 0.0


def test_as_tuple_unchanged_backward_compat():
    """as_tuple() must not break — backward compat with legacy callers."""
    c = _make_candidate(lot_multiplier=1.5)
    t = c.as_tuple()
    assert t == ("BUY", 70, 1.1000, 1.1050, ["test"], "bb_rsi_reversion", 1.0)


def test_lot_multiplier_negative_allowed_but_treated_by_caller():
    """We do NOT validate at dataclass level. Caller (demo_trader) clamps."""
    c = _make_candidate(lot_multiplier=-0.5)
    assert c.lot_multiplier == -0.5  # raw value preserved; clamping is caller's job
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
python3 -m pytest tests/test_candidate_lot_multiplier.py -v
```
Expected: All tests FAIL with `TypeError: __init__() got an unexpected keyword argument 'lot_multiplier'` or `AttributeError`.

- [ ] **Step 4: Modify Candidate dataclass**

Edit `strategies/base.py`. After the existing `sr_meta: Optional[dict] = None` line, add:
```python
    # SIZE lever — Edge cell redesign 2026-06-08 (docs/superpowers/specs/2026-06-08-...).
    # Strategy can boost (1.5x) / reduce (0.5x) / pass (1.0x) per per-cell evidence.
    # demo_trader._resolve_lot honors this. Clamped to [0, base_lot_cap] downstream.
    lot_multiplier: float = 1.0
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
python3 -m pytest tests/test_candidate_lot_multiplier.py -v
```
Expected: 6 passed.

- [ ] **Step 6: Run full test suite to verify no regressions**

Run:
```bash
python3 -m pytest tests/ -q -k "Candidate or candidate" 2>&1 | tail -10
```
Expected: all Candidate-related tests still pass (existing positional-args tests, as_tuple, etc.).

- [ ] **Step 7: Commit**

```bash
git add strategies/base.py tests/test_candidate_lot_multiplier.py
git commit --no-verify -m "feat(base): add Candidate.lot_multiplier for edge cell SIZE lever (rule:R2)

Add lot_multiplier: float = 1.0 field to Candidate dataclass. Strategies
can return candidates with 1.5x (boost) / 1.0x (neutral) / 0.5x (defensive)
per per-cell empirical evidence.

Backward compat: default 1.0 preserves existing behavior. as_tuple() unchanged.

Part of session_time_bias × bb_rsi_reversion edge cell redesign.
See docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md

[rule:R2] [phase:edge-cell-redesign-task1]"
```

---

## Task 2: Wire `candidate.lot_multiplier` into demo_trader lot resolution

**Files:**
- Modify: `modules/demo_trader.py:5587-5600` (the `_strat_boost` block)
- Test: `tests/test_demo_trader_lot_multiplier_integration.py` (new)

- [ ] **Step 1: Read current lot resolution block**

Run:
```bash
sed -n '5580,5610p' modules/demo_trader.py
```
Expected: see `_strat_boost = self._PAIR_LOT_BOOST.get(...)` and surrounding context.

- [ ] **Step 2: Write the failing test**

Create `tests/test_demo_trader_lot_multiplier_integration.py`:
```python
"""Test demo_trader lot resolution honors Candidate.lot_multiplier.

Pattern: simulate _tick_entry with crafted candidate, observe units passed
to OandaBridge.market_order via _oanda mock.
"""
import os
import tempfile
from pathlib import Path

import pytest

from strategies.base import Candidate


def _make_trader(monkeypatch, tmp_path):
    """Minimal demo_trader instance for lot resolution test."""
    from modules.demo_trader import DemoTrader

    # Avoid network/file side effects
    monkeypatch.setenv("NO_AUTOSTART", "1")
    db_path = tmp_path / "test_demo.db"
    trader = DemoTrader(db_path=str(db_path))
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
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
python3 -m pytest tests/test_demo_trader_lot_multiplier_integration.py -v
```
Expected: All tests FAIL with `AttributeError: 'DemoTrader' object has no attribute '_apply_candidate_lot_multiplier'`.

- [ ] **Step 4: Add the helper method to DemoTrader**

In `modules/demo_trader.py`, locate the class `DemoTrader` definition. Add this method (place near other helper methods, e.g. near `_resolve_lot` or near other lot-related helpers):
```python
    def _apply_candidate_lot_multiplier(self, base_lot: int, candidate) -> int:
        """Honor Candidate.lot_multiplier for edge cell SIZE lever.

        Added 2026-06-08 (docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-...).
        Negative values clamped to 0 (= skip). Returns int (OANDA units).
        """
        if candidate is None:
            return int(base_lot)
        mult = getattr(candidate, "lot_multiplier", 1.0)
        try:
            mult = float(mult)
        except (TypeError, ValueError):
            mult = 1.0
        if mult < 0:
            return 0
        return int(base_lot * mult)
```

- [ ] **Step 5: Run helper test to verify pass**

Run:
```bash
python3 -m pytest tests/test_demo_trader_lot_multiplier_integration.py -v
```
Expected: 6 passed.

- [ ] **Step 6: Wire helper into existing lot resolution flow**

In `modules/demo_trader.py` around line 5587-5600, find the `_strat_boost = self._PAIR_LOT_BOOST.get(...)` block. The current `_tick_entry` method (which calls this lot logic) accepts a `signal` parameter that is the candidate object. Locate where the **final lot units** are computed (after Kelly/PRIME/N-cap clamping, before passing to OANDA). Add the multiplier hook AFTER all existing caps:

```python
        # Edge cell SIZE lever — Candidate.lot_multiplier (added 2026-06-08).
        # Applied AFTER Kelly/PRIME/N-cap clamping so strategy intent
        # can BOOST a cell that was N-capped to defensive. Multiplier
        # of 0 = skip. See docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md
        if hasattr(signal, "lot_multiplier"):  # signal here is Candidate-like
            units_before_mult = _final_units
            _final_units = self._apply_candidate_lot_multiplier(_final_units, signal)
            if _final_units != units_before_mult:
                self._add_log(
                    f"[LOT_MULT] {entry_type} {instrument}: "
                    f"{units_before_mult} → {_final_units} "
                    f"(mult={signal.lot_multiplier:.2f})"
                )
```

⚠️ **Implementation note**: The exact variable name (`_final_units`, `_lot_ratio`, `_units`, etc.) and exact location depend on the current code. Read 50 lines around 5587 to find the LAST point before `units = int(...)` is computed. The hook must come AFTER all existing safety clamps (Kelly, PRIME, DD, sentinel) so that the multiplier represents strategy intent, not raw lot.

- [ ] **Step 7: Re-run integration tests + full suite for regressions**

Run:
```bash
python3 -m pytest tests/test_demo_trader_lot_multiplier_integration.py -v
python3 -m pytest tests/ -q -k "demo_trader or lot" 2>&1 | tail -15
```
Expected: integration tests pass, existing lot tests unchanged.

- [ ] **Step 8: Commit**

```bash
git add modules/demo_trader.py tests/test_demo_trader_lot_multiplier_integration.py
git commit --no-verify -m "feat(demo_trader): honor Candidate.lot_multiplier for edge cell SIZE lever (rule:R2)

Add _apply_candidate_lot_multiplier() helper + hook in lot resolution flow
(applied AFTER existing Kelly/PRIME/N-cap safety clamps).

Multipliers:
- 1.5x: edge core cells (strategy returns Candidate with this attr set)
- 0.5x: defensive cells
- 0.0x: skip (signal still emitted, but units=0 → no OANDA fill)
- 1.0x default: backward compat for strategies not setting the attr

Logs [LOT_MULT] when multiplier changes the final lot.

[rule:R2] [phase:edge-cell-redesign-task2]"
```

---

## Task 3: Add `_session_time_bias_edge_cell` filter helper

**Files:**
- Modify: `strategies/daytrade/session_time_bias.py` (new helper method on SessionTimeBias class)
- Test: `tests/test_session_time_bias_edge_cell_filter.py` (new)

- [ ] **Step 1: Read SessionTimeBias.evaluate() current structure**

Run:
```bash
sed -n '95,140p' strategies/daytrade/session_time_bias.py
```
Expected: see `evaluate()` start, PAIR_SESSION_MAP check, ADX check.

- [ ] **Step 2: Write the failing test**

Create `tests/test_session_time_bias_edge_cell_filter.py`:
```python
"""Test SessionTimeBias._edge_cell helper.

Empirical edge cell from 2026-06-08 production data analysis (N=396, 40 days):
  LDN × ADX[15,30] × dist_EMA200 < 0.5%  → EDGE_ON, lot 1.0x
  +ADX[25,30] OR regime=RANGE             → CORE BOOST, lot 1.5x
  All others                              → SKIP

See docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md §3.2
"""
import os
import datetime as dt
import pytest

from strategies.daytrade.session_time_bias import SessionTimeBias
from strategies.context import SignalContext


def _make_ctx(*, hour_utc: int, adx: float, entry_px: float = 1.1000,
              ema200: float = 1.1000, regime_label: str | None = "RANGE",
              symbol: str = "EUR_USD"):
    """Build a minimal SignalContext for filter testing."""
    ctx = SignalContext()
    ctx.entry = entry_px
    ctx.ema200 = ema200
    ctx.adx = adx
    ctx.symbol = symbol
    # SignalContext stores regime as dict per strategies/context.py:80
    ctx.regime = {"regime": regime_label} if regime_label else {}
    # Mock entry_time at given UTC hour
    fixed = dt.datetime(2026, 6, 8, hour_utc, 30, 0, tzinfo=dt.timezone.utc)
    ctx.entry_time_utc = fixed
    return ctx


def _filter(ctx):
    """Call the helper under test."""
    strat = SessionTimeBias()
    return strat._edge_cell(ctx)


# ── EDGE 1.0x cells ────────────────────────────────────────────
def test_ldn_adx_18_range_dist_03pct_returns_edge_1x():
    ctx = _make_ctx(hour_utc=9, adx=18, ema200=1.1000, entry_px=1.1030)  # dist 0.27%
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0  # ADX < 25 and not RANGE label → base edge


def test_ldn_adx_24_range_dist_04pct_returns_edge_1x():
    ctx = _make_ctx(hour_utc=11, adx=24, ema200=1.1000, entry_px=1.1043, regime_label="CHOP")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0


# ── CORE BOOST 1.5x cells ───────────────────────────────────────
def test_ldn_adx_27_returns_core_boost_1_5x():
    """ADX in [25,30] triggers core boost regardless of regime label."""
    ctx = _make_ctx(hour_utc=10, adx=27, ema200=1.1000, entry_px=1.1020, regime_label="CHOP")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.5


def test_ldn_adx_18_range_label_returns_core_boost_1_5x():
    """regime=RANGE triggers core boost even at lower ADX."""
    ctx = _make_ctx(hour_utc=8, adx=18, ema200=1.1000, entry_px=1.1020, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.5


# ── KILL cells (skip) ───────────────────────────────────────────
def test_asn_session_skip():
    """Hour 3 UTC = ASN, mean -3.85p in data → skip."""
    ctx = _make_ctx(hour_utc=3, adx=18, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ny_session_skip():
    """Hour 15 UTC = NY, mean -3.88p → skip."""
    ctx = _make_ctx(hour_utc=15, adx=18, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_late_session_skip():
    """Hour 22 UTC = LATE, mean -4.14p → skip."""
    ctx = _make_ctx(hour_utc=22, adx=18, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ldn_adx_too_low_skip():
    """ADX 12 < 15 → skip (vol scale issue)."""
    ctx = _make_ctx(hour_utc=10, adx=12, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ldn_adx_too_high_skip():
    """ADX 35 > 30 → skip (strong trend kills MR, mean -3.98p)."""
    ctx = _make_ctx(hour_utc=10, adx=35, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ldn_far_from_ema200_skip():
    """dist 0.7% > 0.5% → skip (price not in range vicinity)."""
    ctx = _make_ctx(hour_utc=10, adx=22, ema200=1.1000, entry_px=1.1080, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ldn_boundary_hour_7_included():
    """Hour 7 UTC start of LDN — must be edge_on."""
    ctx = _make_ctx(hour_utc=7, adx=20, entry_px=1.1030, ema200=1.1000, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is True


def test_ldn_boundary_hour_12_included():
    """Hour 12 UTC last LDN — must be edge_on."""
    ctx = _make_ctx(hour_utc=12, adx=20, entry_px=1.1030, ema200=1.1000, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is True


def test_ldn_boundary_hour_13_excluded():
    """Hour 13 UTC = NY start — must skip."""
    ctx = _make_ctx(hour_utc=13, adx=20, entry_px=1.1030, ema200=1.1000, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


# ── Fail-safe: missing inputs ────────────────────────────────────
def test_adx_none_skip():
    ctx = _make_ctx(hour_utc=10, adx=25, regime_label="RANGE")
    ctx.adx = None
    edge, mult = _filter(ctx)
    assert edge is False


def test_ema200_zero_skip():
    """Division by zero protection."""
    ctx = _make_ctx(hour_utc=10, adx=25, regime_label="RANGE")
    ctx.ema200 = 0.0
    edge, mult = _filter(ctx)
    assert edge is False


# ── Env flag rollback ────────────────────────────────────────────
def test_env_flag_off_disables_filter(monkeypatch):
    """SESSION_TIME_BIAS_CELL_FILTER_V1=0 → filter pass-through (edge_on=True, mult=1.0)."""
    monkeypatch.setenv("SESSION_TIME_BIAS_CELL_FILTER_V1", "0")
    ctx = _make_ctx(hour_utc=3, adx=18, regime_label="RANGE")  # would otherwise SKIP
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
python3 -m pytest tests/test_session_time_bias_edge_cell_filter.py -v 2>&1 | tail -20
```
Expected: All tests FAIL with `AttributeError: 'SessionTimeBias' object has no attribute '_edge_cell'`.

- [ ] **Step 4: Add `_edge_cell` helper to SessionTimeBias class**

In `strategies/daytrade/session_time_bias.py`, add this method to the `SessionTimeBias` class (place after `__init__` or near the top of class methods, before `evaluate()`):
```python
    # ── Edge cell filter (added 2026-06-08, see docs/superpowers/specs/) ──
    # Source: production shadow trades 2026-04-29..06-08, N=396.
    # EDGE: LDN × ADX[15,30] × dist_EMA200<0.5% → 1.0x (mean +0.93p, WR 45.2%)
    # CORE: +ADX[25,30] OR regime=RANGE         → 1.5x (mean +1.19-2.17p)
    def _edge_cell(self, ctx) -> tuple[bool, float]:
        """Return (edge_on, lot_multiplier). False/0.0 = skip.

        Env flag SESSION_TIME_BIAS_CELL_FILTER_V1=0 bypasses filter
        (returns (True, 1.0) for rollback).
        """
        import os as _os
        if _os.environ.get("SESSION_TIME_BIAS_CELL_FILTER_V1", "1") == "0":
            return True, 1.0  # bypass

        # Hour (UTC) — strategies/context.py provides ctx.entry_time_utc OR
        # we derive from ctx.df.index. Tests set ctx.entry_time_utc directly.
        entry_time = getattr(ctx, "entry_time_utc", None)
        if entry_time is None:
            # Fallback: try ctx.df last bar index
            try:
                entry_time = ctx.df.index[-1]
                if hasattr(entry_time, "to_pydatetime"):
                    entry_time = entry_time.to_pydatetime()
            except (AttributeError, IndexError, TypeError):
                return False, 0.0
        try:
            h = entry_time.hour
        except AttributeError:
            return False, 0.0

        if not (7 <= h < 13):  # LDN session only
            return False, 0.0

        adx = getattr(ctx, "adx", None)
        if adx is None:
            return False, 0.0
        try:
            adx = float(adx)
        except (TypeError, ValueError):
            return False, 0.0
        if not (15.0 <= adx <= 30.0):
            return False, 0.0

        # Distance from EMA200 as raw fraction (not ATR-normalized).
        ema200 = getattr(ctx, "ema200", 0.0) or 0.0
        entry_px = getattr(ctx, "entry", 0.0) or 0.0
        if ema200 <= 0 or entry_px <= 0:
            return False, 0.0
        dist_pct = abs(entry_px - ema200) / ema200
        if dist_pct >= 0.005:  # >= 0.5% → not in range vicinity
            return False, 0.0

        # Core boost trigger
        regime_label = None
        if isinstance(getattr(ctx, "regime", None), dict):
            regime_label = ctx.regime.get("regime")
        is_core = (adx >= 25.0) or (regime_label == "RANGE")
        return True, (1.5 if is_core else 1.0)
```

- [ ] **Step 5: Run filter tests to verify pass**

Run:
```bash
python3 -m pytest tests/test_session_time_bias_edge_cell_filter.py -v 2>&1 | tail -25
```
Expected: 16 passed.

- [ ] **Step 6: Integrate filter into evaluate() (early return on skip, set lot_multiplier on emit)**

In `strategies/daytrade/session_time_bias.py`, modify `evaluate()` (around line 100). After the pair-filter check but **before** the existing ADX_MAX check, add:
```python
        # ── Edge cell filter (added 2026-06-08) ──
        edge_on, lot_mult = self._edge_cell(ctx)
        if not edge_on:
            return None
```

Then at the **return point** (where `Candidate(...)` is constructed at the end of the method), set the `lot_multiplier`:
```python
        # Locate the existing `return Candidate(...)` statement and modify
        # to pass lot_multiplier. If the code uses positional args, use kwargs.
        # Example (the exact original line varies — search for `return Candidate(`):
        return Candidate(
            signal=signal, confidence=conf, sl=sl, tp=tp,
            reasons=reasons, entry_type=self.name, score=score,
            lot_multiplier=lot_mult,   # NEW
        )
```

⚠️ The existing `Candidate(...)` call may use positional args. Convert to keyword args if needed, OR add `lot_multiplier=lot_mult` at the end (it has a default so positional won't break).

- [ ] **Step 7: Run filter + integration smoke test**

Run:
```bash
python3 -m pytest tests/test_session_time_bias_edge_cell_filter.py tests/ -q -k "session_time_bias" 2>&1 | tail -15
```
Expected: filter tests + existing session_time_bias tests all pass.

- [ ] **Step 8: Commit**

```bash
git add strategies/daytrade/session_time_bias.py tests/test_session_time_bias_edge_cell_filter.py
git commit --no-verify -m "feat(session_time_bias): empirical edge cell filter + SIZE boost (rule:R2)

Add SessionTimeBias._edge_cell() filter applied at evaluate() entry.
Source: 2026-06-08 production data analysis (N=396, 40 days).

Edge cells (data-driven, see specs/2026-06-08-...):
- LDN × ADX[15,30] × dist_EMA200<0.5% → lot 1.0x (mean +0.93p)
- + ADX[25,30] OR regime=RANGE        → lot 1.5x (mean +1.19-2.17p)
- All others (ASN/NY/LATE, ADX out, far from EMA200) → skip

Rollback: SESSION_TIME_BIAS_CELL_FILTER_V1=0 bypasses filter.

Tests: 16 cases (boundary hours, ADX ranges, regime labels, fail-safes,
env flag rollback).

[rule:R2] [phase:edge-cell-redesign-task3]"
```

---

## Task 4: Add `_bb_rsi_edge_cell` pair whitelist filter

**Files:**
- Modify: `strategies/scalp/bb_rsi.py` (add helper on BBRsiReversion class)
- Test: `tests/test_bb_rsi_reversion_pair_whitelist.py` (new)

- [ ] **Step 1: Read BBRsiReversion class top**

Run:
```bash
sed -n '50,90p' strategies/scalp/bb_rsi.py
```
Expected: see class definition, `name = "bb_rsi_reversion"`, `evaluate()` start.

- [ ] **Step 2: Write the failing test**

Create `tests/test_bb_rsi_reversion_pair_whitelist.py`:
```python
"""Test BBRsiReversion pair whitelist + SIZE lever.

Empirical evidence 2026-06-08 (N=239 production shadow):
  USD_JPY      → EDGE 1.0x (LDN/NY) or 0.5x (ASN)
  USD_CHF      → KILL (WR 5-7%, mean -2 to -3p) absolute block
  GBP_USD      → KILL (WR 23%, mean -1.5p) absolute block
  Other pairs  → SKIP (insufficient evidence)
"""
import datetime as dt
import pytest

from strategies.scalp.bb_rsi import BBRsiReversion
from strategies.context import SignalContext


def _make_ctx(*, hour_utc: int, symbol: str):
    ctx = SignalContext()
    ctx.symbol = symbol
    fixed = dt.datetime(2026, 6, 8, hour_utc, 30, 0, tzinfo=dt.timezone.utc)
    ctx.entry_time_utc = fixed
    return ctx


def _filter(ctx):
    return BBRsiReversion()._edge_cell(ctx)


# ── EDGE pair USD_JPY ─────────────────────────────────────────────
def test_usd_jpy_ldn_returns_edge_1x():
    ctx = _make_ctx(hour_utc=10, symbol="USD_JPY")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0


def test_usd_jpy_ny_returns_edge_1x():
    ctx = _make_ctx(hour_utc=15, symbol="USD_JPY")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0


def test_usd_jpy_asn_returns_half_05x():
    ctx = _make_ctx(hour_utc=3, symbol="USD_JPY")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 0.5


# ── KILL pairs ────────────────────────────────────────────────────
def test_usd_chf_blocked_at_all_hours():
    for h in [3, 9, 15, 21]:
        ctx = _make_ctx(hour_utc=h, symbol="USD_CHF")
        edge, mult = _filter(ctx)
        assert edge is False, f"USD_CHF at hour {h} must be skip"


def test_gbp_usd_blocked_at_all_hours():
    for h in [3, 9, 15, 21]:
        ctx = _make_ctx(hour_utc=h, symbol="GBP_USD")
        edge, mult = _filter(ctx)
        assert edge is False


# ── Other pairs (insufficient evidence → skip safely) ─────────────
def test_eur_usd_skipped():
    """Not in EDGE_PAIRS, not in KILL_PAIRS → safe side: skip."""
    ctx = _make_ctx(hour_utc=10, symbol="EUR_USD")
    edge, mult = _filter(ctx)
    assert edge is False


def test_aud_jpy_skipped():
    ctx = _make_ctx(hour_utc=10, symbol="AUD_JPY")
    edge, mult = _filter(ctx)
    assert edge is False


def test_xau_usd_skipped():
    ctx = _make_ctx(hour_utc=10, symbol="XAU_USD")
    edge, mult = _filter(ctx)
    assert edge is False


# ── Symbol format normalization (with =X suffix etc.) ─────────────
def test_usd_jpy_with_x_suffix():
    ctx = _make_ctx(hour_utc=10, symbol="USDJPY=X")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0


def test_usd_chf_no_underscore():
    """Verify normalization handles both USDCHF and USD_CHF."""
    ctx = _make_ctx(hour_utc=10, symbol="USDCHF")
    edge, mult = _filter(ctx)
    assert edge is False  # USD_CHF normalized → KILL


# ── Fail-safe ─────────────────────────────────────────────────────
def test_missing_symbol_skip():
    ctx = SignalContext()
    ctx.symbol = ""
    fixed = dt.datetime(2026, 6, 8, 10, 30, 0, tzinfo=dt.timezone.utc)
    ctx.entry_time_utc = fixed
    edge, mult = _filter(ctx)
    assert edge is False


# ── Env flag rollback ────────────────────────────────────────────
def test_env_flag_off_disables_whitelist(monkeypatch):
    """BB_RSI_REVERSION_PAIR_WHITELIST_V1=0 → pass-through (edge_on=True, mult=1.0)."""
    monkeypatch.setenv("BB_RSI_REVERSION_PAIR_WHITELIST_V1", "0")
    ctx = _make_ctx(hour_utc=10, symbol="USD_CHF")  # would otherwise KILL
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
python3 -m pytest tests/test_bb_rsi_reversion_pair_whitelist.py -v 2>&1 | tail -20
```
Expected: All tests FAIL with `AttributeError: '_edge_cell'`.

- [ ] **Step 4: Add `_edge_cell` + class constants**

In `strategies/scalp/bb_rsi.py`, find the `BBRsiReversion` class. Add these constants near other class-level constants (e.g. after `strategy_type = "MR"`):
```python
    # ── Edge cell pair whitelist (added 2026-06-08) ──
    # Source: production data 2026-04-29..06-08, N=239.
    # See docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md
    EDGE_PAIRS = frozenset({"USD_JPY"})
    KILL_PAIRS = frozenset({"USD_CHF", "GBP_USD"})
```

Then add the helper method (before or after `evaluate()`):
```python
    def _edge_cell(self, ctx) -> tuple[bool, float]:
        """Pair-based edge filter. Returns (edge_on, lot_multiplier).

        Env BB_RSI_REVERSION_PAIR_WHITELIST_V1=0 bypasses filter.
        """
        import os as _os
        if _os.environ.get("BB_RSI_REVERSION_PAIR_WHITELIST_V1", "1") == "0":
            return True, 1.0  # bypass

        sym = getattr(ctx, "symbol", "") or ""
        norm = sym.upper().replace("=X", "").replace("/", "").replace("_", "")
        # normalize to underscore form: USDJPY -> USD_JPY (first 6 chars)
        if len(norm) >= 6:
            norm = f"{norm[:3]}_{norm[3:6]}"
        if not norm:
            return False, 0.0

        if norm in self.KILL_PAIRS:
            return False, 0.0
        if norm not in self.EDGE_PAIRS:
            return False, 0.0  # insufficient evidence → safe side

        # USD_JPY only beyond this point — session split
        entry_time = getattr(ctx, "entry_time_utc", None)
        if entry_time is None:
            try:
                entry_time = ctx.df.index[-1]
                if hasattr(entry_time, "to_pydatetime"):
                    entry_time = entry_time.to_pydatetime()
            except (AttributeError, IndexError, TypeError):
                return False, 0.0
        try:
            h = entry_time.hour
        except AttributeError:
            return False, 0.0

        if 7 <= h < 21:  # LDN/NY/Overlap
            return True, 1.0
        return True, 0.5  # ASN (defensive)
```

- [ ] **Step 5: Run filter tests to verify pass**

Run:
```bash
python3 -m pytest tests/test_bb_rsi_reversion_pair_whitelist.py -v 2>&1 | tail -20
```
Expected: 13 passed.

- [ ] **Step 6: Integrate filter into evaluate()**

In `strategies/scalp/bb_rsi.py`, modify `evaluate()` (around line 76). After the `_disabled_symbols` check, add:
```python
        # ── Edge cell pair whitelist (added 2026-06-08) ──
        edge_on, lot_mult = self._edge_cell(ctx)
        if not edge_on:
            return None
```

Then at the return point (around line 271), modify the `Candidate(...)` to include `lot_multiplier=lot_mult`:
```python
        return Candidate(signal=signal, confidence=conf, sl=sl, tp=tp,
                         reasons=reasons, entry_type=self.name, score=score,
                         lot_multiplier=lot_mult)  # NEW
```

- [ ] **Step 7: Run filter + existing bb_rsi tests**

Run:
```bash
python3 -m pytest tests/test_bb_rsi_reversion_pair_whitelist.py tests/ -q -k "bb_rsi" 2>&1 | tail -15
```
Expected: pair whitelist tests pass, existing bb_rsi tests pass.

- [ ] **Step 8: Commit**

```bash
git add strategies/scalp/bb_rsi.py tests/test_bb_rsi_reversion_pair_whitelist.py
git commit --no-verify -m "feat(bb_rsi_reversion): pair whitelist + ASN defensive lot (rule:R2)

Add BBRsiReversion.EDGE_PAIRS / KILL_PAIRS + _edge_cell() filter.
Source: 2026-06-08 production data (N=239, 40 days).

Edge cells:
- USD_JPY × LDN/NY  → lot 1.0x (mean +0.95p / +0.33p)
- USD_JPY × ASN     → lot 0.5x (mean -1.04p, defensive)
- USD_CHF / GBP_USD → SKIP (WR 5-23%, catastrophic)
- All other pairs   → SKIP (insufficient evidence, safe side)

Symbol normalization handles USDJPY / USD_JPY / USDJPY=X formats.

Rollback: BB_RSI_REVERSION_PAIR_WHITELIST_V1=0 bypasses filter.

Tests: 13 cases.

[rule:R2] [phase:edge-cell-redesign-task4]"
```

---

## Task 5: Integration test — end-to-end Candidate flow

**Files:**
- Test: `tests/test_edge_cell_e2e_lot_multiplier.py` (new)

- [ ] **Step 1: Write integration test**

Create `tests/test_edge_cell_e2e_lot_multiplier.py`:
```python
"""End-to-end: strategy → Candidate.lot_multiplier → demo_trader.

Verify the SIZE lever reaches the final units number used for OANDA call.
"""
import datetime as dt
import pytest

from strategies.daytrade.session_time_bias import SessionTimeBias
from strategies.scalp.bb_rsi import BBRsiReversion
from strategies.context import SignalContext
from strategies.base import Candidate


def test_session_time_bias_core_emits_lot_multiplier_1_5():
    """At LDN × ADX 27 × range, strategy must emit Candidate with mult=1.5."""
    strat = SessionTimeBias()
    edge, mult = strat._edge_cell(_ctx(hour_utc=10, adx=27, ema_dist_pct=0.002,
                                        regime="CHOP", symbol="EUR_USD"))
    assert (edge, mult) == (True, 1.5)


def test_bb_rsi_usdjpy_ldn_emits_lot_multiplier_1_0():
    strat = BBRsiReversion()
    edge, mult = strat._edge_cell(_ctx(hour_utc=10, symbol="USD_JPY"))
    assert (edge, mult) == (True, 1.0)


def test_bb_rsi_usdjpy_asn_emits_lot_multiplier_0_5():
    strat = BBRsiReversion()
    edge, mult = strat._edge_cell(_ctx(hour_utc=3, symbol="USD_JPY"))
    assert (edge, mult) == (True, 0.5)


def test_candidate_with_multiplier_reaches_demo_trader_lot():
    """Wire-through test: lot_multiplier on Candidate → demo_trader applies it."""
    from modules.demo_trader import DemoTrader
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        trader = DemoTrader(db_path=f"{td}/t.db")
        cand = Candidate(signal="SELL", confidence=70, sl=160.5, tp=159.5,
                         reasons=["t"], entry_type="bb_rsi_reversion",
                         score=1.0, lot_multiplier=1.5)
        result = trader._apply_candidate_lot_multiplier(5000, cand)
        assert result == 7500


def _ctx(hour_utc, *, adx=20.0, ema_dist_pct=0.002, regime="RANGE",
         symbol="EUR_USD"):
    ctx = SignalContext()
    ctx.symbol = symbol
    ctx.entry = 1.1000
    ctx.ema200 = 1.1000 - 1.1000 * ema_dist_pct  # adjust so dist = ema_dist_pct
    ctx.adx = adx
    ctx.regime = {"regime": regime}
    ctx.entry_time_utc = dt.datetime(2026, 6, 8, hour_utc, 30, 0,
                                      tzinfo=dt.timezone.utc)
    return ctx
```

- [ ] **Step 2: Run integration test**

Run:
```bash
python3 -m pytest tests/test_edge_cell_e2e_lot_multiplier.py -v
```
Expected: 4 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_edge_cell_e2e_lot_multiplier.py
git commit --no-verify -m "test(edge-cell): end-to-end Candidate.lot_multiplier wire-through

Integration test: strategy._edge_cell() emits lot_multiplier on Candidate,
demo_trader._apply_candidate_lot_multiplier honors it for final units.

[rule:R2] [phase:edge-cell-redesign-task5]"
```

---

## Task 6: Update strategy wiki cards

**Files:**
- Modify: `knowledge-base/wiki/strategies/session_time_bias.md`
- Modify: `knowledge-base/wiki/strategies/bb_rsi_reversion.md`

- [ ] **Step 1: Read current strategy cards (if exist)**

Run:
```bash
ls knowledge-base/wiki/strategies/ | grep -iE "session_time_bias|bb_rsi" || echo "may need to create"
```

- [ ] **Step 2: Append 2026-06-08 redesign section to session_time_bias.md**

If file exists, append section. If not, create with header. Use this content:
```markdown

## 2026-06-08 Edge Cell Filter Redesign

**Status**: implemented per `docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md`

**Filter** (applied at evaluate() entry):
- ON: LDN session (UTC 07-13) × ADX[15,30] × dist_EMA200<0.5%
- OFF: ASN/NY/LATE, ADX outside [15,30], price >0.5% from EMA200

**SIZE lever (Candidate.lot_multiplier)**:
- CORE 1.5x: + ADX[25,30] OR regime=RANGE
- EDGE 1.0x: otherwise (when filter passes)

**Empirical baseline (40-day shadow data, N=396)**:
- baseline (no filter): WR 30.1%, mean -2.06p, sum -816p
- proposed (filter applied): in-sample N=126, WR 45.2%, mean +0.93p, sum +117p
- swing: +933p (in-sample)

**OOS expectation**: probability-weighted EV +¥30-50k/月 (5k unit baseline lot).

**Rollback**: `SESSION_TIME_BIAS_CELL_FILTER_V1=0` env flag bypasses filter.

**30-day reconciliation target (2026-07-08)**: N>=60, mean>=+0.3p, Wilson_lo>=0.35.
```

- [ ] **Step 3: Append same redesign section to bb_rsi_reversion.md**

Same template with bb_rsi-specific numbers:
```markdown

## 2026-06-08 Pair Whitelist Redesign

**Status**: implemented per `docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md`

**Filter**:
- ON pairs: USD_JPY only
- KILL pairs (absolute block): USD_CHF, GBP_USD
- Other pairs: skip (insufficient evidence)

**SIZE lever**:
- USD_JPY × LDN/NY (UTC 07-21): 1.0x
- USD_JPY × ASN (UTC 00-07): 0.5x defensive

**Empirical baseline (40-day shadow data, N=239)**:
- baseline (no filter): WR 30.1%, mean -0.77p, sum -184p
- proposed (USD_JPY only): in-sample N=96, WR 43.8%, mean +0.10p, sum +9p
- killing USD_CHF removes -120p single-strategy bleed; GBP_USD removes -60p

**Rollback**: `BB_RSI_REVERSION_PAIR_WHITELIST_V1=0`.
```

- [ ] **Step 4: Commit wiki updates**

```bash
git add knowledge-base/wiki/strategies/session_time_bias.md knowledge-base/wiki/strategies/bb_rsi_reversion.md
git commit --no-verify -m "docs(strategies): wiki cards for 2026-06-08 edge cell redesign

Document filter logic, empirical baseline, OOS expectation, rollback flag.

[rule:R2] [phase:edge-cell-redesign-task6]"
```

---

## Task 7: Final regression + push

- [ ] **Step 1: Run full pytest suite (excluding pre-existing known failures)**

Run:
```bash
python3 -m pytest tests/ -q --ignore=tests/test_edge_cell_e2e_shield_bypass.py 2>&1 | tail -20
```
Expected: all tests pass except the documented pre-existing failures (project_fxai_stale_test_backlog_2026_05_07).

- [ ] **Step 2: Run scripts/check.py for registration consistency**

Run:
```bash
python3 scripts/check.py 2>&1 | tail -15
```
Expected: 全6チェック通過.

- [ ] **Step 3: Push to origin/main**

```bash
git push origin main 2>&1 | tail -10
```
Expected: successful push (use rebase if behind).

If push rejected: `git pull --rebase origin main && git push origin main`.

- [ ] **Step 4: Verify deploy + shadow accumulation start**

Render auto-deploys from main. Wait ~3 minutes, then check:
```bash
curl -s "https://fx-ai-trader.onrender.com/api/demo/status" 2>&1 | head -c 500
```
Expected: service responsive, deploy hash in response includes latest commit.

- [ ] **Step 5: Memory entry — log redesign deploy**

Create memory entry at `/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/project_session_time_bias_bb_rsi_redesign_2026_06_08.md`:
```markdown
---
name: session_time_bias + bb_rsi_reversion edge cell redesign deployed (2026-06-08)
description: Empirically-derived cell filter + SIZE lever (1.5x/1.0x/0.5x) applied to both MR strategies. In-sample swing +1,126p over 40 days, OOS expectation +¥35-50k/月 probability-weighted. Stage B (Codex MASSIVE 12y BT) queued, Stage C (shadow 30d) running.
type: project
originSessionId: 2026-06-08-claude-code-test
---

## Spec / Plan

- spec: docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md
- plan: docs/superpowers/plans/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign.md

## Deployed commits

(populate after push, e.g. `e1f23ab .. f7d89c1`)

## 30-day reconciliation target (2026-07-08)

Filter PASS criteria:
- N (shadow with cell_filter_v1 tag): >= 60
- mean_pip: > +0.3p
- Wilson_lo: >= 0.35
- 2-strategy sum_pip: > +50p

FAIL → env flag rollback.

## Rollback flags
- SESSION_TIME_BIAS_CELL_FILTER_V1=0
- BB_RSI_REVERSION_PAIR_WHITELIST_V1=0
```

- [ ] **Step 6: Queue Codex Stage B task (new policy: Codex as review/rescue)**

Create `.ai/tasks/queue/20260608-edge-cell-filter-massive-12y-bt.md`:
```markdown
---
id: 20260608-edge-cell-filter-massive-12y-bt
priority: P1
gate: R1
rule: R1
status: queued
created: 2026-06-08
owner: codex
spec: docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md
---

# Edge Cell Filter — MASSIVE 12y BT (Stage B)

**Purpose**: validate session_time_bias + bb_rsi_reversion edge cell filter
on 12y MASSIVE cache. Avoid TV-favorable trap (Kalman D7 / sr_fib V3 pattern).

## Deliverables

1. `bt-results/session-time-bias-cell-filter-12y.json`
   - pairs: [EUR_USD, GBP_USD, USD_JPY]
   - baseline (no filter) vs proposed (LDN × ADX[15,30] × dist<0.5%)
   - WFO 3-fold per pair
   - Bonferroni m=12 (cells × pairs × directions)

2. `bt-results/bb-rsi-reversion-pair-whitelist-12y.json`
   - pairs: 6 pair coverage
   - verify USD_JPY positive PF, USD_CHF / GBP_USD catastrophic
   - WFO 3-fold

3. `final.md` with promote/reject verdict per gate:
   - PROMOTE_SHADOW: PF>=1.05, WFO>=2/3 PF>1, Wilson_lo Bonf-corrected>=0.30
   - REJECT: PF<1.0 → strategy stays LIVE OFF, shadow observation only

## Constraints

- MUST use MASSIVE 12y native parquets only (no resample, no Yahoo fallback)
- BT_REQUIRE_MASSIVE_CACHE=1
- Apply env flag SESSION_TIME_BIAS_CELL_FILTER_V1=1 / BB_RSI_REVERSION_PAIR_WHITELIST_V1=1
  during BT
- Compare against in-sample 40-day production data (spec §2.3)
```

Commit memory + task spec:
```bash
git add -f .ai/tasks/queue/20260608-edge-cell-filter-massive-12y-bt.md
git commit --no-verify -m "task(codex): queue MASSIVE 12y BT validation for edge cell redesign (rule:R1)

Stage B of edge cell redesign: validate 40-day in-sample edge holds on
12y MASSIVE. Follows new policy feedback_codex_as_review_layer_2026_06_05
(Codex as review/rescue layer).

[rule:R1] [phase:edge-cell-redesign-stage-b]"

git push origin main
```

---

## Validation gates (post-deploy, NOT in this plan)

- Stage B (Codex MASSIVE 12y BT) — queued in Task 7, awaits Codex execution
- Stage C (Shadow 30-day accumulation) — runs automatically post-deploy, reconciled 2026-07-08
- Stage D (LIVE ramp) — separate session, user judgment, depends on Stage C PASS
