# ADX Trend Continuation

## Overview
- **Entry Type**: `adx_trend_continuation`
- **Category**: TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: SHADOW (not in ELITE_LIVE, PAIR_PROMOTED, or FORCE_DEMOTED)
- **Active Pairs**: Shadow on all pairs

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
ADX-based trend continuation entry. Enters in the direction of the prevailing trend when ADX confirms strong directional momentum (ADX > threshold with +DI/-DI alignment). Uses EMA alignment as trend filter.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
