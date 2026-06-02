---
id: 2026-06-02-sr-weighted-wave1-silence-r3
title: sr_weighted_bounce/break Wave 1 silence - detector gate diagnosis
verdict: NEEDS_MORE_DATA_DETECTOR_GATE
rule: R3
audit_at: 2026-06-02T18:10:00Z
related_artifact: raw/audits/sr-family-structural-audit-2026-06-02.md
---

# Evidence

- Render env flags are `1`; `H_ENV_OFF` is rejected.
- Fresh production API audit has historical rows, proving both gates can fire:
  `sr_weighted_bounce` n=9 latest `2026-05-29T03:46:45.695045+00:00`;
  `sr_weighted_break` n=13 latest `2026-05-29T08:47:01.044025+00:00`.
- No production rows after 2026-05-29 in the current API extract.
- Wave 1 lock remains in force: no sweep of `K_ABS_THRESHOLD`, percentile,
  ADX, or confirmation parameters.

# Code Action

Added bucketed diagnostics to:

- `strategies/daytrade/sr_weighted_bounce.py`
- `strategies/daytrade/sr_weighted_break.py`

Enable logs with:

```sh
SR_WEIGHTED_BOUNCE_DIAG_LOG=1
SR_WEIGHTED_BREAK_DIAG_LOG=1
```

The instrumentation separates `weighted_levels_empty`, `weight_abs_reject`,
`weight_percentile_reject`, `weight_proximity_reject` where applicable,
`weight_gate_pass`, and post-weight rejection buckets.

# Decision

Collect paper replay counts over USD_JPY M15 for 2026-05-30 through 2026-06-02
or 24h live paper observation before changing any strategy parameter.
