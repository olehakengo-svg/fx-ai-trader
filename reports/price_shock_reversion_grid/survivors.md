# Price Shock Reversion Survivors

Generated: 2026-05-15T08:24:34.034053+00:00


No SHADOW_CANDIDATE cells passed G1-G6.


## Thesis
Price-shock percentiles test whether extreme own-price returns revert over fixed short horizons.


## Design Defects To Audit
Primary risk is sample truncation when MASSIVE history is shorter than the rolling lookback, especially H4.


## Redesign Ideas
Only commander-reviewed future work should consider wider extreme-decile screens or longer source history.
