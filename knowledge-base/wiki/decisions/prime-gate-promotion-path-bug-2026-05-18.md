# PRIME Gate Promotion Path Bug (2026-05-18)

## Finding

Render 30d audit found PRIME predicates firing in shadow, but no PRIME-tagged
LIVE trades. The production order classified PRIME before lot sizing, then later
gates could force shadow before the existing PRIME override ran.

The critical blockers were:

- `BB_RSI_OANDA_TRIP` killed `bb_rsi_reversion_NY_ATRQ2`.
- Q4 gate killed PRIME A/B cells before they could promote.
- fallback shadow ran before the PRIME override and made the override unreachable.

## Binding Fix

PRIME A/B must receive a live-lock immediately after classification. Later gates
must respect that lock:

- emergency trip exempt: PRIME A/B only
- Q4 exempt: PRIME A/B only
- fallback shadow exempt: PRIME A/B only
- Phase0 exempt: PRIME A/B only
- Tier C remains never-promote

`PRIME_OVERRIDE_ENABLED=0` disables the lock and restores pre-hot-fix behavior.

## Codex Implementation Complete ✓

2026-05-18 implementation:

- `modules/demo_trader.py`: moved PRIME classification before `open_trade`, added `_prime_live_lock`, added `PRIME_OVERRIDE_ENABLED` kill-switch, and made emergency trip / Q4 / fallback / Phase0 respect the lock.
- `modules/demo_trader.py`: added `alpha_snapshot.prime = {name, tier, lot_mult}` persistence for PRIME-tagged trades.
- `tests/test_prime_gate_order.py`: added 7 unit regressions for PRIME A/B bypasses, Tier C never-promote, non-PRIME regressions, and kill-switch behavior.
- `tools/prime_gate_order_dry_run.py`: added Render 30d replay tool for real API validation.
- KB updated with strategy-card notes and the lesson [[lesson-prime-gate-order-bug-2026-05-18]].

## Verification Notes

2026-05-18 Codex retry verification:

- `.venv/bin/python -m pytest tests/test_prime_gate_order.py -v`: 7 passed.
- `python3 tools/prime_gate_order_dry_run.py`: PRIME A/B LIVE fires est=75, NEW LIVE fires est=70, adjusted PnL est=+5.6p, Wilson_lo est=0.333.
- `.venv/bin/python scripts/check.py`: ERROR=0 / all 6 checks passed.
- `.venv/bin/python -m pytest tests/ -x -q`: stopped on pre-existing unrelated registration failure `tests/test_ob_retest_h1.py::test_hourly_engine_includes_ob_retest_h1` after 634 passed, 1 skipped.

## Codex Re-eval Complete

2026-05-18 full PRIME re-evaluation completed with `tools/prime_reeval_sanity.py`.

- Render API rows fetched: 6449 (shadow=5637, WIN/LOSS shadow non-XAU=5115)
- Observed API coverage: 2026-04-02 to 2026-05-18
- Task A verdicts: stoch_trend_pullback_PRIME=DEMOTE, stoch_trend_pullback_LONDON_LOWVOL=DEMOTE, fib_reversal_PRIME=DEMOTE, bb_rsi_reversion_NY_ATRQ2=DEMOTE, engulfing_bb_TOKYO_EARLY=KEEP, sr_fib_confluence_GBP_ADXQ2=DEMOTE
- Task B grid: 4608 cells tested; selected new PRIME cells=0; FDR q=0.10 pass cells=0
- Hot-fix dry-run replay: 71 PRIME A/B LIVE fires; proposed v2 verdict replay: 0
- Draft proposal: `research/prime_gate_v2_proposal.py`
- Session report: `knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md`
- Full Task B cell table: `research/prime_reeval_task_b_cells.csv`

## PRIME v2 Apply Complete ✓

2026-05-18 v2 verdicts applied to `modules/prime_gate.py`.

- EDGES replaced with the P1 recomputation from `research/prime_gate_v2_proposal.py`.
- 5 entries demoted to Tier C with `lot_multiplier=0.0`: `stoch_trend_pullback_PRIME`, `stoch_trend_pullback_LONDON_LOWVOL`, `fib_reversal_PRIME`, `bb_rsi_reversion_NY_ATRQ2`, `sr_fib_confluence_GBP_ADXQ2`.
- `engulfing_bb_TOKYO_EARLY` remains Tier C with `lot_multiplier=0.0`.
- PRIME A/B live-lock structure remains intact for future v3 candidates, but current v2 PRIME matches remain Shadow-only.

## B' Forward-Fix Complete ✓

2026-05-18 forward-fix B' corrected the grade mismatch in the v2 apply.

- LIVE promotion grade remains strict (`Wilson_lo>=0.40`, `WF>=2/3`).
- Micro LIVE exploration grade is separate: `Wilson_lo>=0.20`, `WF>=1/3`, and `lot_multiplier=0.05`.
- Revived 2 entries for measurement only: `fib_reversal_PRIME` and `sr_fib_confluence_GBP_ADXQ2`.
- Kept 4 entries Tier C: `stoch_trend_pullback_PRIME`, `stoch_trend_pullback_LONDON_LOWVOL`, `bb_rsi_reversion_NY_ATRQ2`, `engulfing_bb_TOKYO_EARLY`.
- Rationale: shadow EV includes signal-price vs entry-price spread-basis bias; Micro LIVE fill data is needed before treating EV as ground truth.
- Existing R2 safety net remains binding: `tools/volume_live_promotion_watchdog.py` auto-demotes at Live `N>=10` and `EV<0`.
- Lesson recorded: [[lesson-prime-b-grade-mismatch-2026-05-18]].

## v2 Shadow Audit Complete ✓

2026-05-18 design-driven PRIME v2 shadow audit completed with `tools/prime_v2_shadow_audit.py`.

- Hypothesis space: m_total=9 (<=30), Bonferroni alpha=0.005556
- Render rows fetched: 6456 (shadow=5644, WIN/LOSS shadow non-XAU=5121)
- Target strategy rows: 307 across 6 locked strategies
- Selected PRIME v2 candidates: 0
- Report: `research/prime_v2_audit_2026_05_18.md`
- Cells CSV: `research/prime_v2_audit_cells.csv`
- KB session: `knowledge-base/wiki/sessions/prime-v2-shadow-audit-2026-05-18.md`
