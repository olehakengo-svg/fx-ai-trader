# Linear Regression Channel

## Overview
- **Entry Type**: `lin_reg_channel`
- **Category**: MR (Mean Reversion) / TF
- **Timeframe**: DT 15m
- **Status**: FORCE_DEMOTED
- **Active Pairs**: None (FORCE_DEMOTED)

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Linear regression channel mean reversion. Calculates a rolling linear regression line with standard deviation bands, entering reversal trades when price reaches the channel extremes. Expects regression to the mean (channel center) with slope-adjusted directional bias.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
