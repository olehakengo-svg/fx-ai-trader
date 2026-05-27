---
id: 20260526-1540-shadow-emit-audit-gap-fix
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-05-26
owner: claude
---

# Fix shadow_emit audit gap (sr_-only restriction blocks N counting for ~20 strategies)

priority: P0
rule: R3 (immediate — Phase B-1 / SENTINEL の "発火しない" 錯覚の真因, shadow N が永久 0)
gate: N/A (correctness fix, validated by post-fix shadow.n increment per affected strategy)

## Why this is P0

Live audit of `/api/strategies/status` on Render fx-ai-trader.onrender.com (2026-05-27 00:11 UTC)
revealed **39 strategies with shadow.n ≤ 5** out of 91 total. 7-day Render log inspection on
`srv-d6va1of5r7bs73en10vg` showed many of these strategies are **actively generating signals**
(`[MTF_MONITOR] entry=... signal=...`) and receiving shadow flags (`[SHADOW] GBP Asia bypass`,
`[SHADOW] RANGE SELL gate ... → shadow`, `[SCORE_GATE] Sentinel bypass: ... is_shadow will be
enforced`) — yet the corresponding `IN [...]` / `oanda_audit` shadow row never appears for
non-`sr_` strategies via the `shadow_emit_signals` loop.

**Root cause (CONFIRMED)** — `modules/demo_trader.py:817-820`:

```python
@staticmethod
def _should_audit_shadow_emit(entry_type: str) -> bool:
    """Return True for shadow-emit SR-family rows that need OANDA audit visibility."""
    return str(entry_type or "").startswith("sr_")
```

`_open_shadow_emit_trade()` (lines 821-859) writes to `demo_trader` DB via
`self._db.open_trade(..., is_shadow=True, ...)` for ALL strategies, but only calls
`self._add_oanda_audit(... bridge_status="skipped", block_reason="shadow_tracking")` when
`_should_audit_shadow_emit(entry_type)` returns True — i.e. **only for sr_\* strategies**.

The `/api/strategies/status` `shadow.n` count is computed from `oanda_audit`
(via `tier_master`), so non-sr_\* shadow_emit fills are invisible. This affects:

- **5 Price-Shock Phase B-1 strategies** (`price_shock_rev_*_h1_long`) — memory
  `project_price_shock_phase_b1_done_2026_05_18`, commit `458392d8` set the frozenset
  `_FROZEN_SHADOW`-style forcing but did NOT touch the audit emit, so the fix was
  empirically incomplete (only AUD_JPY got 3 fills in 2026-05-20 02:00-02:16, all subsequent
  detections produce MTF_MONITOR but no shadow N increment).
- **~15 SENTINEL strategies** (`eurgbp_daily_mr`, `gotobi_fix`, `liquidity_sweep`,
  `bb_rsi_ema_aligned`, `ma_mr_hybrid`, `ma_trend_perfect`,
  `mtf_regime_range_cascade_scalp`, `mtf_regime_trend_cascade_scalp`,
  `london_close_reversal`, `london_close_reversal_v2`, `pd_eurjpy_h20_bbpb3_sell`,
  `price_shock_reversion`, `kalman_d7_ema75_break`, `kalman_d7_po_dn_flip`,
  `kalman_d7_trail_atr`) — all UNIVERSAL_SENTINEL / SCALP_SENTINEL with `_is_shadow_eligible_full=True`.

The `mtf_counter_trend_scalp × USD_JPY` case (2026-05-26 14:02:16) DID increment shadow.n=1
because it took the `_tick_entry` regular path through line 5575 (which uses the FULL
`_add_oanda_audit` call), NOT through `_open_shadow_emit_trade`. So the bug is path-specific.

## Empirical evidence

**eurgbp_daily_mr × EUR_GBP (UNIVERSAL_SENTINEL, shadow.n=0)** — 2026-05-26 alone:

- Hundreds of `[MTF_MONITOR] EUR_GBP entry=eurgbp_daily_mr signal=SELL` (every 10-30s during
  EUR_GBP active hours)
- Hundreds of `[SCORE_GATE] Sentinel bypass: eurgbp_daily_mr score=0.37 misaligned with SELL
  | EUR_GBP daytrade_eurgbp (is_shadow will be enforced)`
- Multiple `[SHADOW] GBP Asia bypass: eurgbp_daily_mr` + `[SHADOW] RANGE SELL gate:
  eurgbp_daily_mr conf=63<65 → shadow`
- shadow.n in API result: **0**

**price_shock_rev_usd_cad_h1_long × USD_CAD (PAIR_PROMOTED, shadow.n=0)** — 8 detections in
7 days, all show MTF_MONITOR signal=BUY, no IN log, no shadow N increment.

## Decision (must be applied as written)

Change `_should_audit_shadow_emit` to **return True for all strategies**:

```python
@staticmethod
def _should_audit_shadow_emit(entry_type: str) -> bool:
    """Return True for all shadow-emit rows that need OANDA audit visibility.

    Pre-fix behavior (sr_-only) created a systematic shadow.n undercount for
    SENTINEL / Phase B-1 / FORCE_DEMOTED strategies via the shadow_emit_signals
    loop. See decision doc 2026-05-27 + ai/tasks queue entry of this date.
    """
    return True
```

OR, if there is a reason to keep the gate (e.g. `sr_` is special because it injects
`sr_meta`), refactor so that **all `_open_shadow_emit_trade` calls write the
`block_reason="shadow_tracking"` audit row**, with `sr_meta` simply passed through when
present.

## Files & line refs

- `modules/demo_trader.py:817-820` — `_should_audit_shadow_emit` static method (CHANGE THIS)
- `modules/demo_trader.py:821-859` — `_open_shadow_emit_trade` (consumer, may need refactor
  to make audit unconditional)
- `modules/demo_trader.py:799-815` — `_add_oanda_audit` (downstream call, should not change)
- `modules/demo_trader.py:3149-3210` — `shadow_emit_signals` loop that invokes
  `_open_shadow_emit_trade`
- `modules/demo_trader.py:5440-5594` — regular `_tick_entry` IN path (NO change; this path
  works correctly for `mtf_counter_trend_scalp`)

## Validation

1. **Static**: grep for any tests asserting `_should_audit_shadow_emit("non_sr") == False` —
   update tests to expect True. Files of interest:
   - `tests/test_*shadow*.py`
   - `tests/test_*sr*.py`
   - `tests/test_hourly_engine_shadow_ramp.py`
   - `tests/test_price_shock_rev_live_activation_v2.py`

2. **Unit test (must add)**: `tests/test_shadow_emit_audit_all_strategies.py` covering:
   - `_open_shadow_emit_trade` writes an oanda_audit row for `eurgbp_daily_mr` (non-sr_)
   - `_open_shadow_emit_trade` writes an oanda_audit row for `price_shock_rev_usd_cad_h1_long`
   - `_open_shadow_emit_trade` still writes the sr_meta variant correctly for `sr_break_retest`

3. **Local pytest**: run the full pre-commit suite. Per memory
   `project_fxai_stale_test_backlog_2026_05_07.md`, ~10 pre-existing failures exist —
   document any NEW failures separately. Codex must:
   - confirm baseline failure list before fix
   - confirm fix introduces no NEW failures
   - report the diff

4. **Post-deploy verification (pre-reg, 72h)**: After commit + Render deploy, expect
   `shadow.n` to start incrementing for at least these strategies within 72h:
   - `eurgbp_daily_mr` (signals every ~30s during active hours — expect N ≥ 50)
   - `price_shock_rev_usd_cad_h1_long` (sparser, expect N ≥ 1)
   - Any UNIVERSAL_SENTINEL / SCALP_SENTINEL with current shadow.n=0
   
   If N remains 0 after 72h, the bug is elsewhere (likely an upstream block before
   `_open_shadow_emit_trade` is called) — file follow-up task.

5. **Backfill question (Codex must answer)**: Should existing `demo_trader` DB rows with
   `is_shadow=True` AND missing oanda_audit row be backfilled? Recommend **NO**
   (pre-reg purity: counting starts from fix deploy timestamp). Document this decision
   in commit message.

## Out of scope (do NOT do)

- Do NOT change `_tick_entry` regular IN path (5440-5594).
- Do NOT touch frozenset `_FROZEN_SHADOW` / Phase B-1 ramp logic from commit `458392d8`.
- Do NOT change `is_shadow` flag semantics anywhere — only the audit emission gate.
- Do NOT introduce a feature flag — this is a correctness fix.

## Related memory

- `project_price_shock_phase_b1_done_2026_05_18.md` — commit 458392d8 unfinished fix
- `feedback_live_shadow_separation.md` — Live vs Shadow data integrity is load-bearing
- `project_oanda_stats_range_ignored_2026_05_18.md` — sibling audit endpoint bug
- `feedback_shadow_first_quant_architecture.md` — shadow is the primary estimator;
  silent N=0 invalidates this architecture for ~20 strategies

## Commit message template

```
fix(audit): write oanda_audit row for all shadow_emit strategies

_should_audit_shadow_emit() was restricted to sr_*-prefixed names since the
SR-weight Phase 2 rollout, but the shadow_emit_signals loop is used by
Phase B-1 Price-Shock, UNIVERSAL_SENTINEL, and FORCE_DEMOTED paths too. Their
shadow.n was permanently 0 in /api/strategies/status, masking ~20 strategies
that were in fact generating MTF_MONITOR signals.

Re-route to unconditional True. Add regression test covering 3 representative
non-sr_ entry types. No DB backfill — counting starts from deploy timestamp.

Refs: ai/tasks queue 20260526-1540
```

## Acceptance

Codex returns:
- diff of `modules/demo_trader.py:817-820`
- new test file with 3+ passing assertions
- baseline pytest failure list vs post-fix failure list (no NEW failures)
- recommendation on backfill (NO, per above)
- pre-reg validation plan with KPI thresholds


## Result (2026-05-27T04:53:07Z)

exit=0 · 505s

```
Implemented/verified. The behavior fix was already present in `b8833bd3`; I corrected the remaining stale SR-only docstring in [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:817).

Current relevant diff:

```diff
 def _should_audit_shadow_emit(entry_type: str) -> bool:
     """Return True for all shadow-emit rows that need OANDA audit visibility.
 
-    The previous sr_-only gate undercounted SENTINEL / Phase B-1 /
-    FORCE_DEMOTED shadow_emit rows in /api/strategies/status shadow.n.
+    Pre-fix behavior (sr_-only) created a systematic shadow.n undercount for
+    SENTINEL / Phase B-1 / FORCE_DEMOTED strategies via the
+    shadow_emit_signals loop. See decision doc 2026-05-27 + ai/tasks queue
+    entry of this date.
     """
     return True
```

Regression coverage exists in [tests/test_shadow_emit_audit_all_strategies.py](/data/repo/fx-ai-trader/tests/test_shadow_emit_audit_all_strategies.py:48):
- `eurgbp_daily_mr` writes `oanda_audit`
- `price_shock_rev_usd_cad_h1_long` writes `oanda_audit`
- `sr_break_retest` preserves `sr_meta`

Validation:
- Focused: `.venv/bin/pytest -q tests/test_shadow_emit_audit_all_strategies.py tests/test_sr_audit_pipeline.py` -> `5 passed`
- Broader focused set -> `20 passed`
- Current full pytest: `9 failed, 1779 passed, 2 skipped, 1 xfailed`
- Pre-fix baseline at `b8833bd3^`: `9 failed, 1772 passed, 2 skipped, 1 xfailed`
- New failures: none. The same 9 failures are all missing local MASSIVE parquet cache files.

Pre-commit:
- `demo_trader PEP 604 Python 3.9 guard` passed
- `HIP-1 holdout manifest guard` failed because it rejects holdout manifest file arguments unless run with `--allow-holdout-edit`; I did not bypass it because this task does not touch holdout files.

Backfill recommendation: **NO**. Keep pre-reg purity; shadow counting should start from the deploy timestamp.

Post-deploy KPI plan:
- Within 72h, `eurgbp_daily_mr` should reach `shadow.n >= 50`.
- Wit
…(truncated)
