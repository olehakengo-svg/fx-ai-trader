---
id: 20260528-0335-shadow-bypass-for-recent-emit-and-friction-gates
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-05-28
owner: claude
---

# Shadow bypass for recent_emit / spread_guard / session_pair / velocity / spike gates

priority: P0
rule: R3 (immediate — confirmed silent killer of ALL SENTINEL/PHASE0_SHADOW shadow.n via 20h
production diagnosis with /api/demo/block-counts + [SENTINEL_BLOCK_DIAG] logs)
gate: N/A (architectural correctness — applies the same shadow_eligible bypass pattern
that already exists for GBP Asia / RANGE SELL gate / DT RANGE bypass to the silent gates)

## Why this is P0 (post P0-3 diagnosis result)

After P0-3 instrumentation deployed (commit `57d1570d` at 2026-05-27 06:54 UTC), 20-hour
production data on Render `srv-d6va1of5r7bs73en10vg` definitively identifies the silent
gates killing SENTINEL/PHASE0_SHADOW shadow signals between Sentinel bypass (L3479) and
MTF_MONITOR (L4196).

**Evidence**:

`GET /api/demo/block-counts` snapshot (2026-05-28 03:30 UTC, last ~30 min since process restart):
- `total = 1001` blocks
- `eurgbp_daily_mr` per_strategy: **63 recent_emit + 5 spread_guard** (only blocks)
- `session_time_bias` per_strategy: dominated by `recent_emit(session_time_bias,*<900s)`
- `vol_surge_detector`: blocked at `session_pair(EUR_USD_Tokyo,WR=20%)`
- `bb_rsi_reversion`: blocked at `r2_shadow_demoted_cell` (intentional demote — keep)

`[SENTINEL_BLOCK_DIAG]` log sample (Render logs, 2026-05-28 03:01-03:30 UTC):
```
03:01:54  eurgbp_daily_mr blocked at: recent_emit(eurgbp_daily_mr,32s<900s)
03:13:19  eurgbp_daily_mr blocked at: recent_emit(eurgbp_daily_mr,717s<900s)
03:15:27  eurgbp_daily_mr blocked at: recent_emit(eurgbp_daily_mr,845s<900s)
03:16:03  eurgbp_daily_mr blocked at: recent_emit(eurgbp_daily_mr,878s<900s)
03:28:33  eurgbp_daily_mr blocked at: spread_guard(cost=2.8pip/profit=9.0pip=31%>20%)
03:29:05  eurgbp_daily_mr blocked at: recent_emit(eurgbp_daily_mr,31s<900s)
03:06:25  session_time_bias blocked at: session_pair(EUR_USD_Tokyo,WR=20%)
03:09:46  session_time_bias blocked at: recent_emit(session_time_bias,34s<900s)
03:21:16  vol_surge_detector blocked at: session_pair(EUR_USD_Tokyo,WR=20%)
```

**Root cause**: The `_block()` calls for `recent_emit`, `spread_guard`, `session_pair`,
`velocity_*`, `spike`, etc. unconditionally drop the signal regardless of `_is_shadow_eligible_full`.
For SENTINEL strategies (UNIVERSAL_SENTINEL / SCALP_SENTINEL) and PHASE0_SHADOW strategies,
this is a shadow-first architecture violation: their purpose IS to accumulate observation
N independent of live promotion gates. The same gates already implement the correct
shadow-bypass pattern in other locations (lines 3753-3760 GBP Asia, 4097-4106 RANGE SELL,
4119-4127 TREND_BULL BUY).

## What to change

Apply the existing shadow-bypass pattern uniformly. Reference pattern from
`modules/demo_trader.py:3753-3760` (GBP Asia):

```python
if "GBP" in instrument and (_now_h >= 21 or _now_h < 6):
    if not _is_shadow_eligible:
        _block(f"gbp_asia_flash_crash(UTC{_now_h})")
        return
    else:
        _is_shadow = True
        self._add_log(
            f"[SHADOW] GBP Asia bypass: {entry_type} (flash crash zone → shadow)"
        )
```

Apply the SAME pattern to these gates (in priority order by observed impact):

### 1. recent_emit (line ~3780) — TOP PRIORITY

```python
# BEFORE:
_block(f"recent_emit({entry_type},{int(_dedup_age)}s<{_primary_window}s)")
return

# AFTER:
if _is_shadow_eligible_full:
    _is_shadow = True
    self._add_log(
        f"[SHADOW] recent_emit bypass: {entry_type} "
        f"({int(_dedup_age)}s<{_primary_window}s → shadow)"
    )
    # do NOT return — continue to downstream gates
else:
    _block(f"recent_emit({entry_type},{int(_dedup_age)}s<{_primary_window}s)")
    return
```

Note: `_is_shadow_eligible_full` is defined at line ~3499 BEFORE this gate, so it's
available. Verify the variable name and scope before edit.

### 2. spread_guard (line ~4353)

Same pattern — bypass for `_is_shadow_eligible_full`, log to `[SHADOW] spread_guard bypass: ...`.

### 3. session_pair (lines 4068-4076)

Same pattern for `EUR_GBP全停止`, `EUR_USD_Tokyo`, `EUR_USD_Late_NY` blocks.

**Design intent clarification (2026-05-28 user)**: These session_pair UTC-fixed blocks
are **intentional LIVE-side design** — "勝てる場所で勝つ条件だけ転送" (only transfer winning
conditions to OANDA). They are NOT a CLAUDE.md 4原則#3 violation when applied to LIVE
forwarding, because the principle "静的時間ブロックは使わない" applies to **shadow data
collection** (where blocking observation reduces Bonferroni-validated edge discovery
power), NOT to LIVE OANDA transfer (where winning-location filtering is the explicit goal
of promoting edge to LIVE).

For P0-4: add shadow_eligible bypass only. LIVE behavior must remain unchanged (session_pair
continues to hard-block LIVE OANDA forwarding for the listed pair×session cells). Do NOT
file a follow-up task to remove session_pair entirely.

### 4. velocity_up / velocity_down (lines 4396-4398)

Same pattern. These are anti-chase guards (don't BUY after big up move). Shadow accumulation
should not be subject to this — let it observe what happens.

### 5. spike (line 4372)

Same pattern. `_block(f"spike({_spike_range*_spike_m:.1f}pip/60s)")` — shadow eligible
bypass.

### Do NOT touch

These should remain hard blocks (Live-aligned demote / cell-level data integrity):

- `r2_shadow_demoted_cell` (line ~3510) — intentional cell demote, do not bypass
- `direction_filter` — strategy-level direction lock, do not bypass
- `pair_demoted` — pair-level demote, do not bypass
- `force_demoted` — explicit demote, do not bypass
- `auto_demoted` / `pending` — promotion state, do not bypass
- `score_gate(misalign:...)` — already handled by Sentinel bypass at line 3479
- `cooldown` — error-recovery state, do not bypass
- `consec_loss`, `circuit_breaker` — risk state, do not bypass
- `tp_invalid`, `sl_invalid`, `rr_floor`, `1h_rr_low` — math correctness, do not bypass
- `spread_wide` — extreme spread sanity, do not bypass (vs spread_guard which is profitability check)
- `spread_gate` (Layer 0 at line ~4853) — verify whether this should bypass; default to NO
- `spread_sl_gate` (line ~4879) — risk-reward sanity, do not bypass

## Files & line refs

- `modules/demo_trader.py:3499` — `_is_shadow_eligible_full` definition (already exists)
- `modules/demo_trader.py:3753-3760` — reference pattern (GBP Asia bypass)
- `modules/demo_trader.py:3780` — recent_emit (CHANGE — priority 1)
- `modules/demo_trader.py:4068-4076` — session_pair (CHANGE — priority 3)
- `modules/demo_trader.py:4353` — spread_guard (CHANGE — priority 2)
- `modules/demo_trader.py:4372` — spike (CHANGE — priority 5)
- `modules/demo_trader.py:4396-4398` — velocity_up/down (CHANGE — priority 4)
- `modules/demo_trader.py:4097-4106` — RANGE SELL gate (reference pattern, NO CHANGE)
- `modules/demo_trader.py:4119-4127` — TREND_BULL BUY (reference pattern, NO CHANGE)

## Validation

1. **Static**: pytest baseline before any change. Note expected pre-existing failures from
   memory `project_fxai_stale_test_backlog_2026_05_07.md`.

2. **Unit test (must add)**: `tests/test_sentinel_shadow_bypass_gates.py`:
   - SENTINEL strategy hits recent_emit gate → `_is_shadow=True`, signal continues
   - non-SENTINEL strategy hits recent_emit gate → `_block()` called, signal dropped
   - SENTINEL strategy hits spread_guard → `_is_shadow=True`, continues
   - SENTINEL strategy hits velocity_down → `_is_shadow=True`, continues
   - Verify [SHADOW] bypass log emission per gate

3. **Full pytest**: confirm no new failures vs baseline.

4. **Post-deploy probe (immediate, 30 min)**:
   ```bash
   # snapshot block counts before/after deploy
   curl -s 'https://fx-ai-trader.onrender.com/api/demo/block-counts?strategy=eurgbp_daily_mr' | jq .
   
   # after 30 min, recent_emit count for eurgbp_daily_mr should plateau (signals now flow
   # through to shadow_emit) while shadow.n increments
   curl -s 'https://fx-ai-trader.onrender.com/api/strategies/status' | \
     jq '.strategies[] | select(.name=="eurgbp_daily_mr") | {shadow: .shadow}'
   ```

5. **Pre-reg (72h)**:
   - `eurgbp_daily_mr`: `shadow.n >= 50` within 24h (active hours have signals every 10-30s
     pre-fix; 15min dedup window post-fix means ~4/hour max but no gate kills)
   - `session_time_bias`: similar expectation
   - Cluster A SENTINEL total shadow.n increment ≥ 100 in 24h
   - If still 0 after 24h → either P0-3 instrumentation removed too early OR there's a
     deeper bug in `_open_shadow_emit_trade()` not reached. File P0-5.

6. **Diagnostic instrumentation cleanup**: After 72h pre-reg PASS, file P0-5 to remove or
   downgrade the `[SENTINEL_BLOCK_DIAG]` log + `_block_counts_per_strategy` (or keep them
   as permanent observability — Codex must recommend).

## Out of scope (do NOT do)

- Do NOT remove session_pair / spread_guard / velocity gates entirely — only add shadow bypass.
- Do NOT modify the existing reference bypass patterns at lines 3753 / 4097 / 4119.
- Do NOT touch `_should_audit_shadow_emit` (P0-1 commit `b8833bd3` — already correct).
- Do NOT touch JSON serialization fix (P0-2 commit `6c48ae07` — already correct).
- Do NOT change `_UNIVERSAL_SENTINEL` / `_SCALP_SENTINEL` membership.
- Do NOT remove or weaken any existing LIVE-side hard block (session_pair, gbp_asia_flash_crash,
  alpha_scan limits, etc.). These are intentional "勝てる場所で勝つ条件だけ転送" filters for
  LIVE OANDA forwarding. CLAUDE.md 4原則#3 "静的時間ブロックは使わない" applies to shadow
  data collection (which P0-4 fixes), NOT to LIVE transfer design.

## Commit message template

```
fix(gates): shadow-eligible bypass for recent_emit/spread_guard/session_pair/velocity/spike [rule:R3]

P0-3 diagnosis (commit 57d1570d) instrumented _block_counts + SENTINEL_BLOCK_DIAG
and 20h production data definitively identified that SENTINEL/PHASE0_SHADOW
strategies were being silently dropped at recent_emit (15min dedup window),
spread_guard, session_pair, velocity_*, and spike gates — all of which lacked
the shadow-eligible bypass that already existed at GBP Asia / RANGE SELL gate /
DT RANGE bypass (lines 3753, 4097, 4119).

Apply the same `if _is_shadow_eligible_full: _is_shadow=True; continue` pattern
to the silent gates. Cell demote / pair demote / risk state gates are NOT
bypassed (data integrity).

Verification:
- pytest baseline + new test_sentinel_shadow_bypass_gates: <N> passed
- /api/demo/block-counts pre/post snapshot included in deploy plan
- Pre-reg 72h: eurgbp_daily_mr shadow.n >= 50 + Cluster A total >= 100

Refs: ai/tasks queue 20260528-0335

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

## Acceptance

Codex returns:
- diff of `modules/demo_trader.py` showing each gate change (5 gates total)
- new test file with at least 5 assertions (one per gate)
- pytest baseline vs post-fix failure list (no new failures)
- block-counts snapshot before/after (predict: recent_emit count goes UP transiently as more
  signals flow through, then plateaus once shadow.n picks them up; or stays steady if
  recent_emit bypass also disables the dedup increment — Codex must verify)
- recommendation on P0-5 follow-up (instrumentation cleanup decision)


## Result (2026-05-29T08:01:06Z)

exit=0 · 275s

```
Implemented already in this checkout as commit `29ec95cb`:

`fix(gates): shadow-eligible bypass for recent_emit/spread_guard/session_pair/velocity/spike [rule:R3]`

Current worktree is clean. The diff adds the requested bypass pattern in [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py) for:

- `recent_emit`
- `session_pair` (`EUR_GBP`, `EUR_USD_Tokyo`, `EUR_USD_Late_NY`)
- `spread_guard`
- `spike`
- `velocity_up` / `velocity_down`

It also adds [tests/test_sentinel_shadow_bypass_gates.py](/data/repo/fx-ai-trader/tests/test_sentinel_shadow_bypass_gates.py) with focused coverage for the requested gates, including non-SENTINEL `recent_emit` still blocking.

Verification:

- Focused test: `.venv/bin/pytest tests/test_sentinel_shadow_bypass_gates.py -q`
  - `5 passed`
- Implementation commit recorded baseline/post-fix:
  - baseline: `1797 passed`
  - post-fix: `1802 passed`
  - no new failures vs baseline
- Current full suite:
  - `1822 passed, 9 failed, 2 skipped, 1 xfailed`
  - all 9 failures are missing local MASSIVE parquet cache files under `data/cache/massive`, not this gate change.

Production probes:

- `/api/demo/block-counts?strategy=eurgbp_daily_mr`
  - first snapshot: `total=15`, `per_strategy_total=0`
  - later snapshot: `total=28`, `per_strategy_total=0`
  - no `eurgbp_daily_mr:recent_emit` / `spread_guard` strategy-attributed blocks are currently showing.
- `/api/strategies/status`
  - `eurgbp_daily_mr`: `shadow.n=3`
  - `session_time_bias`: `shadow.n=248`
  - `vol_surge_detector`: `shadow.n=58`

Recommendation for P0-5: keep `[SENTINEL_BLOCK_DIAG]` and `_block_counts_per_strategy` for now. Do not clean up yet, because `eurgbp_daily_mr shadow.n=3` is still far below the stated `>=50` 24h pre-reg target if the fix has truly been deployed for a full active window. The next investigation should check whether `_open_shadow_emit_trade()` is reached for `eurgbp_daily_mr`, or whether another post-bypa
…(truncated)
