# Lesson: PRIME B grade mismatch (2026-05-18)

## Observation

The PRIME v2 apply reused the LIVE promotion keep threshold for Micro LIVE
exploration. That demoted every current PRIME cell, including cells that were
too weak for LIVE-driver sizing but still strong enough to justify a tiny
measurement lot.

## Rule

Do not collapse promotion and exploration grades into one threshold.

- LIVE promotion grade: use the stricter keep criteria for profit-driving
  deployment.
- Micro LIVE exploration grade: allow smaller, pre-registered cells when the
  goal is measuring real fill spread, slippage, and live EV.
- The lot size must encode intent. `0.05x` is a measurement tool, not a profit
  driver.

For 2026-05-18 PRIME B', the exploration gate is `Wilson_lo>=0.20` and
`WF>=1/3`; LIVE promotion remains stricter.

## Review Checklist

Before applying a verdict table:

- Confirm the target grade: LIVE promotion, Micro LIVE exploration, or Shadow-only.
- Verify each threshold belongs to that grade.
- Keep entries that fail either exploration floor (`Wilson_lo` or WF) at Tier C.
- Document the automatic demotion safety net and the live sample size trigger.
