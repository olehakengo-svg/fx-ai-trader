# London Close Reversal

## Overview
- **Entry Type**: `london_close_reversal`
- **Category**: Session / MR
- **Timeframe**: DT 15m
- **Status**: UNIVERSAL_SENTINEL (EV approx 0, Sentinel re-verification)
- **Active Pairs**: Sentinel on all pairs

## BT Performance (365d, 15m)
BT data not available for this entry_type

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Reversal strategy targeting the London session close (UTC 15:30-16:30). Enters counter-trend positions as London institutional flows unwind, expecting mean reversion of intraday moves. Filters by intraday range extension and RSI divergence.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
