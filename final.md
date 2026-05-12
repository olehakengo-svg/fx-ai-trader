# fix(sr-redesign): weight-gate audit v2 methodology repair + re-run

## PR Description

Repairs the SR weight-gate audit v2 methodology bug and reruns the KDE-path audit on 365d MASSIVE cache data for 5 majors x 5 strategies.

## v1 vs v2 Verdict Comparison

| Strategy | v1 verdict | v1 N total | v1 N heavy | v1 WR heavy | v1 EV heavy | v2 verdict | v2 N total | v2 N heavy | v2 WR heavy | v2 EV heavy | Wilson_lo (v2 Bonf) |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| sr_anti_hunt_bounce | DEAD | 1441 | 68 | 0.3676 | -4.1755 | DEAD | 335 | 329 | 0.4498 | -2.9272 | 0.3809 |
| sr_break_retest | DEAD | 294 | 54 | 0.3148 | -1.7896 | DEAD | 294 | 292 | 0.2945 | -0.8600 | 0.2310 |
| sr_fib_confluence | DEAD | 4748 | 708 | 0.3955 | -0.6166 | DEAD | 2037 | 2018 | 0.3726 | -0.8786 | 0.3454 |
| sr_liquidity_grab | DEAD | 6 | 0 | 0.0000 | 0.0000 | DEAD | 2 | 2 | 0.5000 | 25.7500 | 0.0617 |
| sr_channel_reversal | DEAD | 2612 | 876 | 0.2671 | -0.0001 | DEAD | 1249 | 1240 | 0.2516 | -0.3314 | 0.2212 |

## Commit-by-Commit Diff Summary

- `fix(sr-redesign): weight-gate audit v2 methodology repair + re-run`
  - Replaced `_nearest_level_meta` with global metadata passthrough, preserving globally computed own/D1/W1 touches and `composite_weight`.
  - Updated `RUN_STRIDES` to reduce adjacent setup oversampling.
  - Added post-hoc dedup in `run_strategy_bt` keyed by strategy, symbol, signal, level, and 2-hour bucket.
  - Added unit and integration regressions for HTF passthrough and dedup sanity.
  - Reran the KDE-path audit and generated `reports/sr_weight_gate_audit_v2_2026-05-12.md` plus `raw/audits/sr_weight_gate_v2_2026-05-12.parquet`.

## Verification

Commands run:

```text
.venv/bin/python tools/sr_weight_gate_audit_v2.py --unit-tests
[unit] PASS (incl. bug 1+2 regression)

.venv/bin/python tools/sr_weight_gate_audit_v2.py --integration-tests
[integration] PASS

.venv/bin/python tools/sr_weight_gate_audit_v2.py --all
[audit] wrote raw/audits/sr_weight_gate_v2_2026-05-12.parquet
[audit] wrote reports/sr_weight_gate_audit_v2_2026-05-12.md
```

Post-run parquet checks:

```text
rows 3917
sr_anti_hunt_bounce     335
sr_break_retest         294
sr_channel_reversal    1249
sr_fib_confluence      2037
sr_liquidity_grab         2
htf_ok 3881
dedup_ratio 1.0
duplicates 0
```

Final git verification to run after commit:

```text
git log --oneline -5
git stash list
git status --short
```

