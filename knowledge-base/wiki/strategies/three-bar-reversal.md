# Three Bar Reversal

## Overview
- **Entry Type**: `three_bar_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (BT未検証, Sentinel蓄積)
- **Active Pairs**: Sentinel on all pairs

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Classic three-bar reversal pattern. Identifies a three-candle reversal formation (middle bar makes new high/low, third bar closes beyond first bar's range), entering in the reversal direction. Simple price action pattern with no indicator dependency.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
