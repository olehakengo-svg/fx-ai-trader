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

Unit verification passes locally. Render API dry-run is required before deploy;
if the API returns 502, rerun `tools/prime_gate_order_dry_run.py` when Render is healthy.
