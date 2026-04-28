# Pre-reg LOCK: Promotion Infrastructure Rewire (2026-04-28)

**Rule classification**: R1 (Slow & Strict) for KPI threshold component / R3 (Immediate) for audit log + passive scanners.
**Status**: LOCKED before merge. Live validation pending.
**Author**: Claude (master session, 5 spawned subtasks 2026-04-27/28).

## Scope of this LOCK

This document covers the promotion-infrastructure rewire bundled in
`feat(promotion): shadow-aware gate + auto-recovery + Kelly clean + WF recovery + KPI thresholds`.
Five interdependent changes ship together because they share method signatures
and test fixtures.

| # | Change | Rule | Active impact on production trades |
|---|---|---|---|
| 1 | `_evaluate_shadow_promotions` (Sentinel N=0 fix) | R3 | None — logs candidates only; tier-master.json untouched |
| 2 | `tools/auto_force_demoted_recovery.py` | R3 | Daily cron, dry-run shows **0** candidates (Bonferroni gate working) |
| 3 | Kelly-clean helper + pre-gate | R2 | More conservative — blocks Kelly<0 pre-promotion (was: post-block via SHIELD) |
| 4 | WF recovery pattern (H1≤0 & H2>0) | R2 | Adds `demoted → pending` path; FORCE_DEMOTED untouched; Mann-Whitney p<0.10 conservative |
| 5 | **STRATEGY_PROFILES KPI threshold wiring** | **R1** | **Changes promotion criteria for strategies with defined Mode A/B** |

Items 1-4 are observational or strictly tightening. Item 5 is the only one
that changes who gets promoted.

## R1 Pre-reg LOCK terms (item 5 only)

### Hypothesis

Replacing hardcoded `WR ≥ 60%` fast-track and `WR-agnostic + EV ≥ friction`
normal-track with `STRATEGY_PROFILES`-driven `kpi_wr` / `kpi_ev` per Mode
will:

- **Mode A (scalp / Trend Following)**: lower the WR bar from 60% → 30% but
  raise the EV bar to `max(friction_pip, kpi_ev × pip_unit)`. Net effect:
  more high-N low-WR but positive-EV scalp strategies become promotable.
- **Mode B (dt / Mean Reversion)**: lower WR bar to 55%, same EV gate. Net
  effect: dt strategies that would have failed the legacy 60% bar can now
  promote IF kpi_ev is met.

### Backwards-compatibility safety net

Strategies **without** a defined Mode in `STRATEGY_PROFILES` fall back to the
legacy hardcoded thresholds. Net effect on those strategies = 0.

Therefore the live impact is bounded to strategies whose `entry_type` appears
in `STRATEGY_PROFILES` (modules/config.py L30-49). Enumerate these in the
post-deploy first-day audit.

### Validation plan (pre-promotion)

1. **Dry-run shadow simulation**: run `_evaluate_promotions` against the
   current Live database with the new mode-aware gate, capturing the diff
   between legacy outcome and new outcome per strategy. Document expected
   promotions / demotions.
2. **Live N≥30 monitoring window**: after merge, monitor `algo_change_log`
   for 7 days. Any strategy that flips status under the new gate must
   accumulate N≥30 trades post-flip before lot-up consideration.
3. **Bonferroni check**: any new promotion under the mode-aware gate must
   independently satisfy Wilson_BF lower > 0.50 AND Bonferroni p < 0.05
   over the post-flip window. The promotion gate already enforces
   `_wilson_pass` so this is automatic, but the Pre-reg LOCK requires
   explicit re-verification at day 7.

### Rollback trigger

Any of:

- A strategy promoted under the new gate posts N≥10 with EV<0 in the first
  72h post-flip → revert that strategy to `pending` manually and disable
  Mode reference in `STRATEGY_PROFILES` for that entry_type.
- Aggregate Live PnL diverges from pre-deploy baseline by >2σ over 7 days.
- Any test in `tests/test_kpi_threshold_promotion.py` starts failing under
  schema drift.

### Out of scope for this LOCK

- BT_COST_PER_TRADE per-pair friction (`friction_model_v2` integration into
  promotion EV gate) — separate change, separate LOCK.
- tier-master.json dynamic regeneration (currently 2-day staleness window).
- per-pair-direction cell expansion for asymmetric strategies
  (`dt_bb_rsi_mr` BUY/SELL split).

## Test evidence at LOCK time

```
$ python3 -m pytest tests/test_shadow_promotion_gate.py \
    tests/test_kelly_promotion_gate.py \
    tests/test_kpi_threshold_promotion.py \
    tests/test_wf_recovery.py \
    tests/test_auto_force_demoted_recovery.py
67 passed in 0.73s

$ python3 -m pytest tests/ --ignore=tests/test_phase5_strategies.py \
    --ignore=tests/test_cpd_divergence.py
622 passed, 1 xfailed in 15.44s

$ python3 tools/auto_force_demoted_recovery.py --dry-run
[auto_force_demoted_recovery] checked 18 force_demoted strategies
  (N≥30, Z_BF=3.29, α_BF=0.05)
[auto_force_demoted_recovery] No strategies met the recovery gate.
```

## Audit links

- obs 252 — `_is_promoted()` 6-stage chain, cell3d stub
- obs 254 — original `_evaluate_promotions()` thresholds
- obs 257 — Sentinel N=0 structural bug + `get_shadow_trades_for_evaluation` fix
- obs 258 — cell_edge_audit.py v2 promotion criteria reused
- obs 259 — gate wiring gap analysis
- obs 267, 268 — FORCE_DEMOTED shadow-continue behavior
- obs 298 — KPI threshold + algo_change_log unwired (now resolved)

## Sign-off

LOCK takes effect at merge. Post-deploy day-7 review re-evaluates the
hypothesis and either ratifies or triggers rollback. KB entry to update
upon ratification: `wiki/lessons/lesson-promotion-rewire-2026-04-28.md`.
