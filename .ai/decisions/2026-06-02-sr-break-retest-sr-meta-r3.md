---
id: 2026-06-02-sr-break-retest-sr-meta-r3
title: sr_break_retest SR metadata gap - candidate wiring fix
verdict: CONFIRMED_STRATEGY_METADATA_WIRING_FIXED
rule: R3
audit_at: 2026-06-02T18:10:00Z
related_artifact: raw/audits/sr-family-structural-audit-2026-06-02.md
---

# Evidence

- Fresh production API audit: `sr_break_retest` has 251 audit rows, with 250
  `sr_strength` NULL and 1 populated.
- Other SR strategies populate the same audit columns, so the DB and bridge
  write path are functional.
- `OandaBridge._add_audit()` already writes `sr_strength`, `sr_touches`,
  `sr_days_span`, `sr_is_strong`, and `sr_distance_atr` from `candidate.sr_meta`.
- The local `SrBreakRetest.evaluate()` returned a `Candidate` without
  `sr_meta`.

# Code Action

`strategies/daytrade/sr_break_retest.py` now passes:

```python
sr_meta=Candidate.sr_meta_from_price(
    (ctx.layer3 or {}).get("sr_weighted_levels", []),
    sr_level,
    signal_close,
    ctx.atr,
)
```

`tests/test_sr_break_retest_shadow_redesign_v2.py` verifies the emitted
metadata dictionary, including `strength`, `touches`, `days_span`, `is_strong`,
and `distance_atr`.

# Decision

Deploy the feature branch, then verify new `sr_break_retest` rows after one
hour of market activity have non-NULL `sr_strength`.
