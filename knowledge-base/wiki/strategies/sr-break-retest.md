# SR Break Retest

## Overview
- **Entry Type**: `sr_break_retest`
- **Category**: Breakout / TF
- **Timeframe**: DT 15m
- **Status**: FORCE_DEMOTED (v7.0: N=2 EV=-21.4 PnL=-42.8)
- **Active Pairs**: None (FORCE_DEMOTED)

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
N=2 EV=-21.4 PnL=-42.8pip. Single trade capable of wiping all profits.

## Signal Logic
Support/resistance break and retest strategy. Enters after price breaks a key SR level, waits for a pullback retest of the broken level (now acting as new support/resistance), then enters in the breakout direction on confirmation of the retest holding.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
