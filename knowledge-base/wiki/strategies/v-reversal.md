# V Reversal

## Overview
- **Entry Type**: `v_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (BT未検証, Sentinel蓄積)
- **Active Pairs**: Sentinel on all pairs

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Sharp V-shaped reversal pattern detection. Identifies rapid price drops/spikes followed by an equally sharp reversal, forming a V-bottom or inverted V-top. Enters on confirmation of the reversal leg, targeting a move back toward the pre-spike level.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
