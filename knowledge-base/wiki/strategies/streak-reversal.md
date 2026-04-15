# Streak Reversal

## Overview
- **Entry Type**: `streak_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: SHADOW (implemented from massive alpha scan)
- **Active Pairs**: Shadow on all pairs

## BT Performance (365d, 15m)
From massive alpha scan (Bonferroni significant):
| Edge | Pair | N | WR | p-value |
|---|---|---|---|---|
| 5streak BUY | USD_JPY | 586 | 58.7% | 1.3x10^-5 |

## Live Performance (post-cutoff)
Live data accumulating

## Signal Logic
Consecutive candle streak reversal (3-5 candle streak). Enters counter-direction after a series of consecutive same-direction candles, expecting mean reversion. Statistically significant reversal bias after extended unidirectional runs.

## Current Configuration
- Lot Boost: default (1.0x)
- PAIR_DEMOTED: none
- PAIR_PROMOTED: none

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
