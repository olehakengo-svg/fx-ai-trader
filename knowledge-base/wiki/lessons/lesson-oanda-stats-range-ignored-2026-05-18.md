# Lesson: OANDA stats range ignored (2026-05-18)

## Bug

`/api/oanda/stats` ignored the frontend `range` query parameter. The OANDA analysis UI could show old real OANDA executions as if they were recent LIVE firing activity because `range=today`, `range=7d`, `range=30d`, and `range=all` all returned the same aggregate.

## Root cause

The demo stats handler had explicit time-window handling (`rolling_days`, `all_time`, fidelity cutoff, `_filters`), but the OANDA stats handler only forwarded `date_from`, `date_to`, and `instrument` to `get_oanda_stats()`. This handler/query asymmetry meant the frontend sent a valid range that the backend silently dropped.

## Prevention

All stats endpoints used by UI dashboards should expose `_filters` with the effective query window and backing `_db_path`. When a stats endpoint supports a frontend window selector, tests must assert that at least two supported windows return different totals on fixture data and that the effective cutoff is visible in the response.
