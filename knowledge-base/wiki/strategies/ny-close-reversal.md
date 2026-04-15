# NY Close Reversal

## Overview
- **Entry Type**: `ny_close_reversal`
- **Category**: Session / MR
- **Timeframe**: DT 15m
- **Status**: SHADOW (implemented from massive alpha scan)
- **Active Pairs**: Shadow on all pairs

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
| UTC 20-22 | N | W | L | WR | PnL |
|---|---|---|---|---|---|
| All pairs | 5 | 0 | 5 | 0.0% | -7.0p |

## Signal Logic
NY session close (UTC 20:00-22:00) directional bias reversal. Enters counter-trend positions at NY close based on the day's directional movement, expecting overnight mean reversion. Implemented from massive alpha scan H20/H21 session bias findings.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
