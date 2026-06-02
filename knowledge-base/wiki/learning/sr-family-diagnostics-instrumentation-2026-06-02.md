---
id: sr-family-diagnostics-instrumentation-2026-06-02
title: SR Family Diagnostics Instrumentation
status: READY_COUNTS_PENDING
created_at: 2026-06-02T18:10:00Z
---

# Scope

Instrumentation was added for the SR family structural diagnosis without
changing strategy thresholds or entry logic.

# Enable Flags

```sh
SR_LIQUIDITY_GRAB_DIAG_LOG=1
SR_WEIGHTED_BOUNCE_DIAG_LOG=1
SR_WEIGHTED_BREAK_DIAG_LOG=1
```

# Buckets

`sr_liquidity_grab`:

- `called`
- `reject_no_sr_levels`
- `reject_sr_proximity`
- `reject_no_hunt`
- `reject_resistance_reversal`
- `reject_support_reversal`
- `reject_bad_risk_reward`
- `reject_rr`
- `reject_dedup`
- `candidate`

`sr_weighted_bounce`:

- `weight_gate_seen`
- `weighted_levels_empty`
- `weighted_levels_invalid`
- `weight_abs_reject`
- `weight_percentile_reject`
- `weight_proximity_reject`
- `weight_gate_pass`
- `post_weight_reject_reversal_bar`
- `post_weight_reject_confirmation`
- `post_weight_reject_sltp`
- `post_weight_reject_bad_risk_reward`
- `post_weight_reject_rr`
- `post_weight_reject_dedup`
- `candidate`

`sr_weighted_break`:

- `weight_gate_seen`
- `weighted_levels_empty`
- `weighted_levels_invalid`
- `weight_abs_reject`
- `weight_percentile_reject`
- `weight_gate_pass`
- `post_weight_reject_break_retest`
- `post_weight_reject_htf`
- `post_weight_reject_bad_risk_reward`
- `post_weight_reject_rr`
- `post_weight_reject_dedup`
- `candidate`

# Counts

Pending. This Codex run did not execute a 1h/24h paper replay because no
confirmed harness for production-equivalent closed-bar `layer3.sr_weighted_levels`
state was identified in the allotted turn. Do not substitute a synthetic harness
for the decision counts.

# Next Run

Use production-equivalent paper replay over USD_JPY M15 for 2026-05-30 through
2026-06-02, then paste the resulting bucket counts into this note or a dated
successor in `knowledge-base/wiki/learning/`.
