# SENTINEL Block Diagnosis Instrumentation (2026-05-27)

Task: `.ai/tasks/queue/20260527-0230-sentinel-silent-block-instrumentation.md`

## Endpoint

`GET /api/demo/block-counts`

Returns the runtime `_demo_trader._block_counts` dictionary from `_tick_entry()`,
plus `_block_counts_per_strategy` for SENTINEL silent-block diagnosis.

Fields:

- `counts`: existing mode-level block counters, keyed as `mode:reason`.
- `per_strategy_counts`: strategy-level block counters, keyed as `entry_type:reason`.
- `total`: sum of `counts`.
- `per_strategy_total`: sum of `per_strategy_counts` after optional filtering.
- `strategy`: requested strategy filter, or `null`.

Filter:

`GET /api/demo/block-counts?strategy=eurgbp_daily_mr`

Returns all mode-level `counts` and filters `per_strategy_counts` to keys starting
with `eurgbp_daily_mr:`.

## Temporary Log

`modules/demo_trader.py` emits:

`[SENTINEL_BLOCK_DIAG] <entry_type> blocked at: <reason>`

Only strategies in `_UNIVERSAL_SENTINEL` or `_SCALP_SENTINEL` trigger this log.
The log is observation-only and does not change any gate behavior.

## Rollback

After diagnosis, remove:

- `/api/demo/block-counts` from `app.py`
- `_block_counts_per_strategy` updates in `_block()`
- `[SENTINEL_BLOCK_DIAG]` logging in `_block()`
- `tests/test_sentinel_block_instrumentation.py`
