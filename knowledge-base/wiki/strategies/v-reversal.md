# V Reversal

## Overview
- **Entry Type**: `v_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: FORCE_DEMOTED (2026-05-01 audit P0-8; Live N=3 WR=0% PnL=-10.1p)
- **Active Pairs**: None (FORCE_DEMOTED; Shadow accumulation only)

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
- Status: **FORCE_DEMOTED**

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
