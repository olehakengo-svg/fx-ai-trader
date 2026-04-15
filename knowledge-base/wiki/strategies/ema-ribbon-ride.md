# EMA Ribbon Ride

## Overview
- **Entry Type**: `ema_ribbon_ride`
- **Category**: TF (Trend Following)
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED
- **Active Pairs**: None (FORCE_DEMOTED)

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Rides momentum using an EMA ribbon (multiple EMAs of increasing period). Enters when all EMAs align in order (e.g., EMA9 > EMA21 > EMA50) and price pulls back to touch the ribbon. Exits when ribbon order breaks or price closes below the fastest EMA.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
