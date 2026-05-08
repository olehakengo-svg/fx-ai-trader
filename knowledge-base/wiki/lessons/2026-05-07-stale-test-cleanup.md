# 2026-05-07 — Stale test cleanup (post-Phase-1c)

## Context

Phase 1c work (`feat(data): extend MASSIVE _SYMBOL_MAP to 14 OANDA Labs pairs`,
`feat(bt): expand Phase 1b to 14 pairs and history-source`) revealed that the
project pre-commit hook had been blocked since 6619afd (2026-05-05) by a
forward-looking test that referenced helpers that never landed in
`modules/data.py`.

Task 4 of the Phase 1c plan refactored `fetch_ohlcv_massive` into the chunked
architecture the test was written against:

- new module-level `_massive_utc_now()` (test injection point for "now")
- new module-level `_fetch_chunk(massive_ticker, mult, timespan, start, end, key)`
- public `fetch_ohlcv_massive` walks 630-day chunks, sleeps 0.5s between them,
  and dedups boundary timestamps (`keep="last"`)

That fixed the 3 `tests/test_fetch_ohlcv_massive_pagination.py` tests.

## Other failures observed but **explicitly out of scope**

After Task 4 fix, `python3 -m pytest tests/` still reports **10 failures** that
**pre-date** this work (verified by stashing the Task 4 diff and re-running on
HEAD: same 10 fail). Per the operator plan ("do not chase additional failures
into scope crawl — only fix the `_massive_utc_now` test plus anything that's a
genuine regression introduced by your fix"), these are documented here for a
follow-up session rather than fixed in-line.

| File | Failures | Likely root cause |
|---|---|---|
| `tests/test_strategies_drift_check.py` | `test_live_kb_passes_drift_check` | Real KB drift: `dt_bb_rsi_mr`, `sr_fib_confluence`, `trend_rebound` claim FORCE_DEMOTED on their wiki pages but are missing from `tier-master.json` `force_demoted` set. Either the strategy pages or the truth file is stale. |
| `tests/test_ma_mr_hybrid_shadow_redesign_v2.py` | 3 tests | W4-Shadow-Redesign v2 forward-looking (entry-gate / soft-score / shadow-promote). |
| `tests/test_ma_trend_perfect_shadow_redesign_v2.py` | 4 tests | W4-Shadow-Redesign v2 forward-looking. |
| `tests/test_r2_14cell_lock.py` | 2 tests | R2 14-cell lock list does not match current pair-demote/promote sets. |

## Why this matters

`pre-commit` runs `pytest tests/ -x -q`. While these 10 failures stand, every
non-test commit gets blocked, encouraging operators to develop the habit of
`--no-verify`. That habit is what masked the stale `_massive_utc_now` test for
two days.

## Recommended fix sequence (separate session)

1. Run the drift checker and reconcile `tier-master.json` ↔ `wiki/strategies/*.md`
   for the 3 strategies flagged. (`python3 tools/sync_kb_index.py --write`
   then `tools/tier_integrity_check.py --write`.) That likely fixes
   `test_live_kb_passes_drift_check`.
2. Inspect each `_v2` redesign test against current code; either the redesign
   is incomplete (the test is correct, the code lags) or the redesign was
   abandoned (delete the test). Don't paper over with `xfail`.
3. Update `r2_14cell_lock` fixture lists against the current pair-demote /
   pair-promote registry.

Once those 10 land, `pre-commit` is genuinely usable again and `--no-verify`
should be retired from the muscle-memory of this repo.

## Evidence

- HEAD before Task 4: `18343eb feat(bt): expand Phase 1b to 14 pairs and
  history-source` — 10 failures + 3 pagination = 13.
- HEAD after Task 4: **10 failures, all pre-existing.**
- Stash test: `git stash; pytest tests/...; git stash pop` — same 10.

## Closure (2026-05-08)

All 10 pre-existing failures cleared in a follow-up cleanup pass:

1. **Drift checker (1 test)** — `dt_bb_rsi_mr`, `sr_fib_confluence`, and
   `trend_rebound` were in `pair_promoted` per `modules/demo_trader.py` but
   their wiki strategy pages still claimed `FORCE_DEMOTED`. Updated the three
   pages (`dt-bb-rsi-mr.md`, `sr-fib-confluence.md`, `trend-rebound.md`) to
   reflect the 2026-05-07 volume-emergency promotes; a `## Previously` block
   preserves the prior `FORCE_DEMOTED` history. Truth source (`tier-master.json`)
   was already correct.
2. **`MA_MR_HYBRID_REDESIGN_V2` (3 tests)** — wired the redesign env-flag end
   to end. `strategies/scalp/__init__.py` got the matching `_SHADOW_PROMOTE`
   block (mirrors BB_RSI / SQUEEZE / etc); `strategies/scalp/ma_mr_hybrid.py`
   converts the M15 bias hard-gate into a soft score boost when the flag is
   set. Default-off is byte-identical to prior production behaviour.
3. **`MA_TREND_PERFECT_REDESIGN_V2` (4 tests)** — same pattern. v2 path uses
   the most-recent **closed** 1m bar (`df.iloc[-2]`) for the signal-bar
   confirmation, requires `m5.is_closed=True`, adds class-level per-bar
   dedup (`_v2_emitted_bars` + `reset_dedup_state()`), and emits the
   `closed 1m … signal_bar=… / 次バー以降で約定` reasons the test asserts on.
4. **R2 14-cell lock (2 tests)** — fixture was a stale snapshot. Two cells
   were intentionally re-promoted on 2026-05-07 (`vix_carry_unwind×USD_JPY`
   shadow N=58 EV=+9.54 PF=1.65; `trend_rebound×USD_JPY` shadow N=17 EV=+1.14
   PF=1.52). Both have an R2 live N>=10 EV<0 auto-demote guard. Renamed the
   constant `DEMOTE_LOCK_14 → DEMOTE_LOCK_12` (kept the old name as a
   backwards-compat alias) and dropped `vix_carry_unwind×USD_JPY` from
   `PROMOTED_CONFLICTS` since it is now a legitimate, audit-tracked promote
   rather than a conflict.

Verification: `python3 -m pytest tests/ -q` → **1372 PASS, 1 xfailed, 0 fail**.
Pre-commit hook is unblocked; subsequent commits in this repo should not need
`--no-verify`.
