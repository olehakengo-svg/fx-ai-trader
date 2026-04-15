# Inducement OB

## Overview
- **Entry Type**: `inducement_ob`
- **Category**: SMC (Smart Money Concepts)
- **Timeframe**: DT 15m
- **Status**: FORCE_DEMOTED
- **Active Pairs**: None (FORCE_DEMOTED)

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Smart Money Concepts inducement + order block strategy. Identifies inducement levels where retail stops are clustered, waits for a sweep of those levels, then enters at the resulting order block (OB). Targets the imbalance fill after the stop hunt.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
